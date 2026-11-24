"""Looking up a shader Attribute node's Instancer or Object value for an
evaluated instance, the way Blender's viewport does
(BKE_object_dupli_find_rgba_attribute), so the export can pick the same
switched material branch."""

from typing import Any, Dict, List, Optional, Sequence, Tuple

import bpy

RGBA = Tuple[float, float, float, float]

# BLI_noise_hash_uchar_512, which is these 256 bytes twice.
_HASH = bytes.fromhex(
    "a2a0193bf8ebaaeef31c67281ded00de952edc3f3a82354d6cba36d0f60c7932"
    "d159f4088b63892fb8b49783f28f18c751146587482042a880b54013b2227e57"
    "bc7f6b9d864cc8db7cd5254e5a557450cdb37abbc3cbb6e2e4ecfd980b96d39e"
    "5ca164f18161e1c42472498c904b843438ab78ca1f01d79311c158a931f9446d"
    "bf339c5f0994a38506c69a1e7b461530272b1b713c5bd66f62ac4fc2c00eb123"
    "a7df47b0776905e9e6e776730ffe6e9b56ef12a537fcaed9038edd10b9cec98d"
    "da2abd68179fbed40accd2e8433d70b7027d99d80d608a042c3e92e5af5307e0"
    "29a6c5e3f5f74a41266a165e522d21adf091ffea54fa661a4539cf75a488fb5d"
)

# Unused persistent_id entries.
_NO_ID = 0x7FFFFFFF


class _Rng:
    """Blender's RandomNumberGenerator (rand48) seeded with seed_random."""

    def __init__(self, seed: int) -> None:
        seed &= 0xFFFFFFFF
        for _ in range(2):
            self._seed((seed + _HASH[seed & 255]) & 0xFFFFFFFF)
            seed = self.int32()
        self._seed((seed + _HASH[seed & 255]) & 0xFFFFFFFF)

    def _seed(self, seed: int) -> None:
        self.x = (seed << 16) | 0x330E

    def int32(self) -> int:
        self.x = (0x5DEECE66D * self.x + 0xB) & 0xFFFFFFFFFFFF
        return self.x >> 17


def unique_instance_ids(ids: Sequence[int]) -> List[int]:
    """Blender's generate_unique_instance_ids: the instances' persistent ids
    when they have an id attribute."""
    unique = list(ids)
    used = set()
    collisions = []
    for index, id in enumerate(ids):
        if id in used:
            collisions.append(index)
        else:
            used.add(id)
    generators: Dict[int, _Rng] = {}
    for index in collisions:
        id = ids[index]
        rng = generators.setdefault(id, _Rng(id))
        for _ in range(101):
            candidate = rng.int32()
            if candidate not in used:
                break
        else:
            candidate = next(i for i in range(0x7FFFFFFF) if i not in used)
        used.add(candidate)
        unique[index] = candidate
    return unique


class UnsupportedInstanceAttribute(Exception):
    pass


def _to_rgba(value: Any) -> Optional[RGBA]:
    """A custom or RNA property value as Blender's find_property_rgba
    converts it: scalars spread over rgb, arrays of up to 4 numbers."""
    if isinstance(value, bool):
        v = 1.0 if value else 0.0
        return (v, v, v, 1.0)
    if isinstance(value, (int, float)):
        return (float(value), float(value), float(value), 1.0)
    try:
        items = list(value)
    except TypeError:
        return None
    if not 0 < len(items) <= 4:
        return None
    if any(isinstance(x, bool) or not isinstance(x, (int, float)) for x in items):
        return None
    out = [0.0, 0.0, 0.0, 1.0]
    for i, x in enumerate(items):
        out[i] = float(x)
    return (out[0], out[1], out[2], out[3])


def find_property_rgba(id: Optional[bpy.types.ID], name: str) -> Optional[RGBA]:
    if id is None:
        return None
    if name in id.keys():
        return _to_rgba(id[name])
    try:
        value = id.path_resolve(name)
    except ValueError:
        return None
    return _to_rgba(value)


# Instance attribute types and how Blender converts them to a colour.
_ATTRIBUTE_RGBA = {
    "FLOAT": ("value", 1),
    "INT": ("value", 1),
    "INT8": ("value", 1),
    "BOOLEAN": ("value", 1),
    "FLOAT2": ("vector", 2),
    "FLOAT_VECTOR": ("vector", 3),
    "FLOAT_COLOR": ("color", 4),
}


class _Level:
    """One geometry nodes instancing level: its attributes and how its
    instances' persistent ids map to indices."""

    def __init__(
        self, geometry: Any, names: Sequence[str], key: Tuple[Any, ...]
    ) -> None:
        self.key = key
        cloud = geometry.instances_pointcloud()
        attributes = cloud.attributes
        self.references = list(geometry.instance_references())
        handles = attributes.get(".reference_index")
        self.reference_index = [d.value for d in handles.data] if handles else None
        ids = attributes.get("id")
        self.index_by_id: Optional[Dict[int, int]] = None
        if ids is not None:
            unique = unique_instance_ids([d.value for d in ids.data])
            self.index_by_id = {id: index for index, id in enumerate(unique)}
        self.values: Dict[str, List[RGBA]] = {}
        for name in names:
            attribute = attributes.get(name)
            if attribute is None:
                continue
            if attribute.data_type not in _ATTRIBUTE_RGBA:
                raise UnsupportedInstanceAttribute(
                    f"Instance attribute '{name}' has type {attribute.data_type}, "
                    "which a material switch can't read"
                )
            field, width = _ATTRIBUTE_RGBA[attribute.data_type]
            values = []
            for d in attribute.data:
                v = getattr(d, field)
                if width == 1:
                    f = float(v)
                    values.append((f, f, f, 1.0))
                else:
                    out = [0.0, 0.0, 0.0, 1.0]
                    for i in range(width):
                        out[i] = float(v[i])
                    values.append((out[0], out[1], out[2], out[3]))
            self.values[name] = values

    def index(self, persistent_id: int) -> int:
        if self.index_by_id is None:
            return persistent_id
        return self.index_by_id[persistent_id]

    def handle(self, index: int) -> int:
        return self.reference_index[index] if self.reference_index else 0


class InstanceAttributes:
    """Instance attribute lookups for one export, caching each instancing
    level's attributes."""

    def __init__(self, depsgraph: bpy.types.Depsgraph, names: Sequence[str]) -> None:
        self.depsgraph = depsgraph
        self.names = list(names)
        self.levels: Dict[Tuple[Any, ...], Optional[_Level]] = {}
        self.collections_with: Dict[Tuple[str, str], bool] = {}

    def _object_level(self, object: bpy.types.Object) -> Optional[_Level]:
        key: Tuple[Any, ...] = ("object", object.name)
        if key not in self.levels:
            evaluated = object.evaluated_get(self.depsgraph)
            level = None
            if evaluated.type != "EMPTY":
                geometry: Any = evaluated.evaluated_geometry()  # type: ignore[func-returns-value]
                if geometry.instances_pointcloud() is not None:
                    level = _Level(geometry, self.names, key)
            self.levels[key] = level
        return self.levels[key]

    def _child_level(self, parent: _Level, handle: int) -> Optional[_Level]:
        key = parent.key + (handle,)
        if key not in self.levels:
            geometry = parent.references[handle]
            level = None
            if geometry.instances_pointcloud() is not None:
                level = _Level(geometry, self.names, key)
            self.levels[key] = level
        return self.levels[key]

    def _levels_with(self, level: Optional[_Level], name: str) -> bool:
        """Whether name is an attribute on this level or any level it
        instances."""
        if level is None:
            return False
        if name in level.values:
            return True
        for handle, reference in enumerate(level.references):
            if isinstance(reference, bpy.types.Collection):
                if self._collection_with(reference, name):
                    return True
            elif isinstance(reference, bpy.types.Object):
                if self._levels_with(self._object_level(reference), name):
                    return True
            elif self._levels_with(self._child_level(level, handle), name):
                return True
        return False

    def _collection_with(self, collection: bpy.types.Collection, name: str) -> bool:
        key = (collection.name, name)
        if key not in self.collections_with:
            self.collections_with[key] = False
            self.collections_with[key] = any(
                self._levels_with(self._object_level(o), name)
                for o in collection.all_objects
            )
        return self.collections_with[key]

    def _geometry_nodes_levels(
        self, instancer: bpy.types.Object, persistent_id: Sequence[int]
    ) -> Tuple[List[Tuple[_Level, int]], Optional[bpy.types.Collection]]:
        """The geometry nodes levels an instance passes through, outermost
        first, with its index on each, and the collection it continued into,
        whose levels aren't followed."""
        ids = [i for i in persistent_id if i != _NO_ID][::-1]
        levels: List[Tuple[_Level, int]] = []
        if instancer.type == "EMPTY":
            return levels, instancer.instance_collection
        level = self._object_level(instancer)
        for id in ids:
            if level is None:
                break
            index = level.index(id)
            levels.append((level, index))
            handle = level.handle(index)
            reference = level.references[handle]
            if isinstance(reference, bpy.types.Collection):
                return levels, reference
            if isinstance(reference, bpy.types.Object):
                level = self._object_level(reference)
            else:
                level = self._child_level(level, handle)
        return levels, None

    def lookup(
        self,
        object: bpy.types.Object,
        instancer: Optional[bpy.types.Object],
        persistent_id: Sequence[int],
        from_particles: bool,
        name: str,
        use_instancer: bool,
    ) -> RGBA:
        """The value an Attribute node of type Instancer (use_instancer) or
        Object reads for this instance."""
        if use_instancer and instancer is not None:
            if from_particles:
                raise UnsupportedInstanceAttribute(
                    "Material switches don't support particle instances"
                )
            levels, collection = self._geometry_nodes_levels(instancer, persistent_id)
            if collection is not None and self._collection_with(collection, name):
                raise UnsupportedInstanceAttribute(
                    f"Instances inside collection '{collection.name}' store "
                    f"'{name}' themselves, which material switches don't support yet"
                )
            for level, index in reversed(levels):
                values = level.values.get(name)
                if values is not None:
                    return values[index]
            found = find_property_rgba(instancer, name)
            if found is not None:
                return found
        found = find_property_rgba(object, name)
        if found is None and object.data is not None:
            found = find_property_rgba(object.data, name)
        return found if found is not None else (0.0, 0.0, 0.0, 0.0)
