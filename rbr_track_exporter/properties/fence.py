from typing import Dict, List, Optional, Tuple
import enum

from ..gnodes.fence import *
from ..shaders.fence import setup_fence_material_node_tree

import bpy
from ..blender_utils import gnodes_input, local_node_group, narrow


class FenceKind(enum.Enum):
    TAPE = 0x0
    NET = 0x1
    BARBED_WIRE = 0x2

    def pretty(self) -> str:
        return self.name.replace("_", " ").title()


class FenceTextureSource(enum.Enum):
    BUILTIN = 0x0
    CUSTOM = 0x1

    def pretty(self) -> str:
        if self is FenceTextureSource.BUILTIN:
            return "Built-in"
        return "Custom"

    def description(self) -> str:
        if self is FenceTextureSource.BUILTIN:
            return "A texture from the game's fence.dat"
        return "An image shipped with the stage"


FENCE_TEXTURE_SOURCE_ITEMS = [
    (t.name, t.pretty(), t.description(), t.value) for t in FenceTextureSource
]


# signs_road holds one pole stripe per colour, selected by the fence's pole type.
SIGNS_ROAD = "signs_road"
SIGNS_ROAD_POLES: Dict[str, Tuple[float, float]] = {
    "signs_road_grey": (0.951, 1.0),
    "signs_road_black": (0.805, 0.854),
    "signs_road_blue": (0.854, 0.902),
    "signs_road_red": (0.902, 0.951),
}
SIGNS_ROAD_POLE_V = (0.25, 1.0)

# The built-in textures offered per fence kind, by fence.dat name; the first is
# the default.
BUILTIN_FENCE_TILES: Dict[FenceKind, List[Tuple[str, str]]] = {
    FenceKind.TAPE: [
        ("br_fence_tile", "BR"),
        ("ar_fence_tile", "AR"),
        ("au_fence_tile", "AU"),
        ("ho_fence_tile", "HO"),
        ("mb_fence_tile", "MB"),
        ("rs_fence_tile", "RS"),
        ("us_fence_tile", "US"),
        ("fence_tile02", "Diagonal Stripe Red White"),
        ("fence_tile03", "Blue"),
        ("fence_tile04", "Yellow"),
        ("fence_tile06", "Orange"),
    ],
    FenceKind.NET: [
        ("fence_tile01", "Orange"),
        ("fence_tile05", "Blue"),
    ],
    FenceKind.BARBED_WIRE: [
        ("barbed_wire_tile", "Barbed Wire"),
    ],
}

BUILTIN_FENCE_POLES: Dict[FenceKind, List[Tuple[str, str]]] = {
    FenceKind.TAPE: [
        ("br_fencestolpe", "BR"),
        ("ar_fencestolpe", "AR"),
        ("au_fencestolpe", "AU"),
        ("ho_fencestolpe", "HO"),
        ("mb_fencestolpe", "MB"),
        ("rs_fencestolpe", "RS"),
        ("us_fencestolpe", "US"),
        ("signs_road_grey", "Grey"),
        ("signs_road_black", "Black"),
        ("signs_road_blue", "Blue"),
        ("signs_road_red", "Red"),
    ],
    FenceKind.NET: [
        ("fence_pole_grey", "Grey"),
        ("fence_pole_black", "Black"),
        ("fence_pole_blue", "Blue"),
        ("fence_pole_red", "Red"),
    ],
    FenceKind.BARBED_WIRE: [
        ("barbed_wire_stolpe", "Barbed Wire"),
    ],
}

# Blender needs dynamic enum items kept alive while they're displayed.
_builtin_items: Dict[Tuple[str, ...], List[Tuple[str, str, str, int]]] = {}


def _builtin_choices(
    options: List[Tuple[str, str]], current: str
) -> List[Tuple[str, str, str, int]]:
    names = [name for name, _ in options]
    if current != "" and current not in names:
        options = options + [(current, current)]
    key = tuple(name for name, _ in options)
    if key not in _builtin_items:
        _builtin_items[key] = [
            (name, label, name, i) for i, (name, label) in enumerate(options)
        ]
    return _builtin_items[key]


class RBRFenceSettings(bpy.types.PropertyGroup):
    def _update_fence_prop(self, context: bpy.types.Context) -> None:
        objs = collect_objects(self.id_data)
        for obj in objs:
            get_or_create_fence_modifier(obj, self)

    def _update_fence_kind(self, context: bpy.types.Context) -> None:
        kind = FenceKind[self.fence_kind]
        tiles = [name for name, _ in BUILTIN_FENCE_TILES[kind]]
        poles = [name for name, _ in BUILTIN_FENCE_POLES[kind]]
        if self.fence_tile_builtin not in tiles:
            self.fence_tile_builtin = tiles[0]
        if self.fence_pole_builtin not in poles:
            self.fence_pole_builtin = poles[0]
        self._update_fence_prop(context)

    fence_kind: bpy.props.EnumProperty(  # type: ignore
        items=[(t.name, t.pretty(), t.pretty(), t.value) for t in FenceKind],
        name="Fence Kind",
        default=FenceKind.TAPE.name,
        update=_update_fence_kind,
    )

    fence_tile_source: bpy.props.EnumProperty(  # type: ignore
        items=FENCE_TEXTURE_SOURCE_ITEMS,
        name="Tile Texture Source",
        default=FenceTextureSource.BUILTIN.name,
        update=_update_fence_prop,
    )

    fence_tile_builtin: bpy.props.StringProperty(  # type: ignore
        name="Built-in Tile Texture",
        default=BUILTIN_FENCE_TILES[FenceKind.TAPE][0][0],
        update=_update_fence_prop,
    )

    def _tile_choices(
        self, context: Optional[bpy.types.Context]
    ) -> List[Tuple[str, str, str, int]]:
        return _builtin_choices(
            BUILTIN_FENCE_TILES[FenceKind[self.fence_kind]], self.fence_tile_builtin
        )

    def _get_tile_choice(self) -> int:
        names = [name for name, _, _, _ in self._tile_choices(None)]
        return (
            names.index(self.fence_tile_builtin)
            if self.fence_tile_builtin in names
            else 0
        )

    def _set_tile_choice(self, value: int) -> None:
        self.fence_tile_builtin = self._tile_choices(None)[value][0]

    fence_tile_builtin_choice: bpy.props.EnumProperty(  # type: ignore
        name="Built-in Tile Texture",
        items=_tile_choices,
        get=_get_tile_choice,
        set=_set_tile_choice,
        options={"SKIP_SAVE"},
    )

    fence_tile_texture: bpy.props.PointerProperty(  # type: ignore
        name="Tile Texture",
        type=bpy.types.Image,
        update=_update_fence_prop,
    )

    fence_pole_source: bpy.props.EnumProperty(  # type: ignore
        items=FENCE_TEXTURE_SOURCE_ITEMS,
        name="Pole Texture Source",
        default=FenceTextureSource.BUILTIN.name,
        update=_update_fence_prop,
    )

    fence_pole_builtin: bpy.props.StringProperty(  # type: ignore
        name="Built-in Pole Texture",
        default=BUILTIN_FENCE_POLES[FenceKind.TAPE][0][0],
        update=_update_fence_prop,
    )

    def _pole_choices(
        self, context: Optional[bpy.types.Context]
    ) -> List[Tuple[str, str, str, int]]:
        return _builtin_choices(
            BUILTIN_FENCE_POLES[FenceKind[self.fence_kind]], self.fence_pole_builtin
        )

    def _get_pole_choice(self) -> int:
        names = [name for name, _, _, _ in self._pole_choices(None)]
        return (
            names.index(self.fence_pole_builtin)
            if self.fence_pole_builtin in names
            else 0
        )

    def _set_pole_choice(self, value: int) -> None:
        self.fence_pole_builtin = self._pole_choices(None)[value][0]

    fence_pole_builtin_choice: bpy.props.EnumProperty(  # type: ignore
        name="Built-in Pole Texture",
        items=_pole_choices,
        get=_get_pole_choice,
        set=_set_pole_choice,
        options={"SKIP_SAVE"},
    )

    fence_pole_texture: bpy.props.PointerProperty(  # type: ignore
        name="Pole Texture",
        type=bpy.types.Image,
        update=_update_fence_prop,
    )

    def tile_image(self) -> Optional[bpy.types.Image]:
        if FenceTextureSource[self.fence_tile_source] is FenceTextureSource.BUILTIN:
            return builtin_fence_image(self.fence_tile_builtin)
        image: Optional[bpy.types.Image] = self.fence_tile_texture
        return image

    def pole_image(self) -> Optional[bpy.types.Image]:
        if FenceTextureSource[self.fence_pole_source] is FenceTextureSource.BUILTIN:
            name = self.fence_pole_builtin
            return builtin_fence_image(SIGNS_ROAD if name in SIGNS_ROAD_POLES else name)
        image: Optional[bpy.types.Image] = self.fence_pole_texture
        return image

    def pole_stripe(self) -> Optional[Tuple[float, float, float, float]]:
        if (
            FenceTextureSource[self.fence_pole_source] is FenceTextureSource.BUILTIN
            and self.fence_pole_builtin in SIGNS_ROAD_POLES
        ):
            u0, u1 = SIGNS_ROAD_POLES[self.fence_pole_builtin]
            v0, v1 = SIGNS_ROAD_POLE_V
            return (u0, u1, v0, v1)
        return None


BUILTIN_FENCE_IMAGE_PROP = "rbr_builtin_fence_texture"


def builtin_fence_image(name: str) -> Optional[bpy.types.Image]:
    """The packed preview image for a built-in fence texture, created from the
    bundled fence.dat on first use."""
    if name == "":
        return None
    for image in bpy.data.images:
        if image.get(BUILTIN_FENCE_IMAGE_PROP) == name:
            return image
    try:
        from .. import rbr_blender_track_io
    except ImportError:
        return None
    created: Optional[bpy.types.Image] = rbr_blender_track_io.fence_texture_image(name)
    if created is not None:
        created[BUILTIN_FENCE_IMAGE_PROP] = name
    return created


def collect_objects(id_data: Optional[bpy.types.ID]) -> List[bpy.types.Object]:
    objs = []
    for obj in bpy.data.objects:
        if obj.data == id_data:
            objs.append(obj)
    return objs


def get_or_create_fence_modifier(
    obj: bpy.types.Object, settings: RBRFenceSettings
) -> bpy.types.NodesModifier:
    gnodes = obj.modifiers.get(".rbr.fence")
    if gnodes is None:
        gnodes = narrow(
            obj.modifiers.new(".rbr.fence", "NODES"), bpy.types.NodesModifier
        )
        gnodes.node_group = get_or_create_fence_node_group()
        vcol = gnodes_input(gnodes, GNODES_FENCE_VCOL)
        if isinstance(obj.data, bpy.types.Mesh) and "vcol" in obj.data.attributes:
            vcol.type = "ATTRIBUTE"
            vcol.attribute_name = "vcol"
        else:
            vcol.value = [1, 1, 1, 1]
    gnodes_input(gnodes, GNODES_FENCE_KIND).value = FenceKind[settings.fence_kind].value
    gnodes_input(gnodes, GNODES_FENCE_TILE_TEXTURE).value = (
        get_or_create_fence_material(settings.tile_image())
    )
    stripe = settings.pole_stripe()
    gnodes_input(gnodes, GNODES_FENCE_POLE_TEXTURE).value = (
        get_or_create_fence_material(
            settings.pole_image(),
            stripe,
            (
                settings.fence_pole_builtin.removeprefix(SIGNS_ROAD + "_")
                if stripe
                else ""
            ),
        )
    )
    gnodes.show_expanded = False
    return narrow(gnodes, bpy.types.NodesModifier)


def recreate_fence_node_group() -> None:
    old = local_node_group(".rbr.fence")
    if old is not None:
        old.name = ".rbr.fence.old"
    new = get_or_create_fence_node_group()
    for obj in bpy.data.objects:
        gnodes = obj.modifiers.get(".rbr.fence")
        if isinstance(gnodes, bpy.types.NodesModifier):
            gnodes.node_group = new
    if old is not None:
        bpy.data.node_groups.remove(old)


def get_or_create_fence_node_group() -> bpy.types.GeometryNodeTree:
    name = ".rbr.fence"
    node_group = local_node_group(name)
    if node_group is None:
        node_group = make_fence_node_group()
    return narrow(node_group, bpy.types.GeometryNodeTree)


def get_or_create_fence_material(
    image: Optional[bpy.types.Image],
    stripe: Optional[Tuple[float, float, float, float]] = None,
    suffix: str = "",
) -> Optional[bpy.types.Material]:
    if image is None:
        return None
    name = f".rbr.fence.{image.name}" + (f".{suffix}" if suffix else "")
    material = bpy.data.materials.get(name)
    if material is None:
        material = bpy.data.materials.new(name)
        material.use_nodes = True
        setup_fence_material_node_tree(
            narrow(material.node_tree, bpy.types.ShaderNodeTree), image, stripe
        )
    return material


def register() -> None:
    bpy.utils.register_class(RBRFenceSettings)


def unregister() -> None:
    bpy.utils.unregister_class(RBRFenceSettings)
