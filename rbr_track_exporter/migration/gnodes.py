"""Move node maths the exporter cannot read (colour ramps, mixes, maths on
vertex colours) into a geometry nodes modifier that stores the result as a
named attribute, and read that attribute in the material instead."""

from typing import Dict, List, Tuple

import bpy

from ..blender_utils import narrow
from ..shaders.shader_node import ShaderNodeRBR
from . import tables
from .legacy import ALLOWED_VALUE_SOURCES, Log, _upstream, is_old_rbr_node

Candidate = Tuple[bpy.types.Material, ShaderNodeRBR, bpy.types.NodeSocket]

# Node properties that describe layout or identity rather than behaviour.
SKIP_PROPS = {
    "name",
    "label",
    "location",
    "location_absolute",
    "width",
    "height",
    "parent",
    "select",
    "hide",
    "mute",
    "color",
    "use_custom_color",
    "show_options",
    "show_preview",
    "show_texture",
    "warning_propagation",
}

STORE_TYPES = {"VALUE": "FLOAT", "RGBA": "FLOAT_COLOR", "VECTOR": "FLOAT_VECTOR"}
ATTRIBUTE_OUTPUTS = {
    "VALUE": ("Fac", "Factor"),
    "RGBA": ("Color",),
    "VECTOR": ("Vector",),
}


class Unsupported(Exception):
    pass


def candidates() -> List[Candidate]:
    found: List[Candidate] = []
    for material in bpy.data.materials:
        if material.library is not None or material.node_tree is None:
            continue
        for node in material.node_tree.nodes:
            if not isinstance(node, ShaderNodeRBR) or is_old_rbr_node(node):
                continue
            for socket in node.inputs:
                if not socket.links or socket.name in tables.TEXTURE_SOCKETS:
                    continue
                if socket.type not in STORE_TYPES:
                    continue
                source = _upstream(socket.links[0])
                if source.bl_idname in ALLOWED_VALUE_SOURCES:
                    continue
                found.append((material, node, socket))
    return found


def _upstream_nodes(start: bpy.types.Node) -> List[bpy.types.Node]:
    seen: Dict[str, bpy.types.Node] = {}
    stack = [start]
    while stack:
        node = stack.pop()
        if node.name in seen:
            continue
        seen[node.name] = node
        for socket in node.inputs:
            for link in socket.links:
                stack.append(link.from_node)
    return list(seen.values())


def _copy_ramp(old: bpy.types.ColorRamp, new: bpy.types.ColorRamp) -> None:
    new.color_mode = old.color_mode
    new.interpolation = old.interpolation
    new.hue_interpolation = old.hue_interpolation
    while len(new.elements) > 1:
        new.elements.remove(new.elements[-1])
    for i, element in enumerate(old.elements):
        target = new.elements[0] if i == 0 else new.elements.new(element.position)
        target.position = element.position
        target.color = element.color
        target.alpha = element.alpha


def _copy_curves(old: bpy.types.CurveMapping, new: bpy.types.CurveMapping) -> None:
    for name in ("use_clip", "clip_min_x", "clip_min_y", "clip_max_x", "clip_max_y"):
        setattr(new, name, getattr(old, name))
    for old_curve, new_curve in zip(old.curves, new.curves):
        while len(new_curve.points) > 2:
            new_curve.points.remove(new_curve.points[-1])
        for i, point in enumerate(old_curve.points):
            if i < 2:
                target = new_curve.points[i]
                target.location = point.location
            else:
                target = new_curve.points.new(point.location[0], point.location[1])
            target.handle_type = point.handle_type
    new.update()


def _copy_settings(old: bpy.types.Node, new: bpy.types.Node) -> None:
    for prop in old.bl_rna.properties:
        name = prop.identifier
        if (
            name in SKIP_PROPS
            or prop.is_readonly
            and name not in ("color_ramp", "mapping")
        ):
            continue
        if name == "color_ramp":
            _copy_ramp(getattr(old, name), getattr(new, name))
            continue
        if name == "mapping":
            _copy_curves(getattr(old, name), getattr(new, name))
            continue
        if prop.type == "COLLECTION" or not hasattr(new, name):
            continue
        try:
            setattr(new, name, getattr(old, name))
        except (AttributeError, TypeError, ValueError):
            pass
    for old_socket in old.inputs:
        new_socket = new.inputs.get(old_socket.identifier)
        if new_socket is None or not hasattr(old_socket, "default_value"):
            continue
        try:
            new_socket.default_value = old_socket.default_value
        except (AttributeError, TypeError, ValueError):
            pass


class _Builder:
    """Copies one upstream graph into a geometry node tree."""

    def __init__(self, tree: bpy.types.GeometryNodeTree):
        self.tree = tree
        self.nodes: Dict[str, bpy.types.Node] = {}
        # Outputs that need a different node than the main copy.
        self.outputs: Dict[Tuple[str, str], bpy.types.NodeSocket] = {}

    def named_attribute(self, name: str, data_type: str) -> bpy.types.Node:
        node = self.tree.nodes.new("GeometryNodeInputNamedAttribute")
        setattr(node, "data_type", data_type)
        node.inputs["Name"].default_value = name
        return node

    def separate_alpha(self, color: bpy.types.NodeSocket) -> bpy.types.NodeSocket:
        node = self.tree.nodes.new("FunctionNodeSeparateColor")
        self.tree.links.new(color, node.inputs["Color"])
        return node.outputs["Alpha"]

    def add(self, old: bpy.types.Node) -> None:
        kind = old.bl_idname
        if kind in ("ShaderNodeVertexColor", "ShaderNodeAttribute"):
            if kind == "ShaderNodeVertexColor":
                name = narrow(old, bpy.types.ShaderNodeVertexColor).layer_name
            else:
                attr = narrow(old, bpy.types.ShaderNodeAttribute)
                if attr.attribute_type != "GEOMETRY":
                    raise Unsupported(f"{old.name} reads a non-geometry attribute")
                name = attr.attribute_name
            if not name:
                raise Unsupported(f"{old.name} has no attribute name")
            color = self.named_attribute(name, "FLOAT_COLOR")
            self.nodes[old.name] = color
            color_out = color.outputs["Attribute"]
            self.outputs[(old.name, "Color")] = color_out
            self.outputs[(old.name, "Vector")] = color_out
            self.outputs[(old.name, "Alpha")] = self.separate_alpha(color_out)
            factor = self.named_attribute(name, "FLOAT").outputs["Attribute"]
            self.outputs[(old.name, "Fac")] = factor
            self.outputs[(old.name, "Factor")] = factor
            return
        if kind == "ShaderNodeNewGeometry":
            # Shader geometry is in world space, geometry nodes work in
            # object space, so go through the object's own transform.
            info = self.tree.nodes.new("GeometryNodeObjectInfo")
            setattr(info, "transform_space", "ORIGINAL")
            self.tree.links.new(
                self.tree.nodes.new("GeometryNodeSelfObject").outputs["Self Object"],
                info.inputs["Object"],
            )
            position = self.tree.nodes.new("FunctionNodeTransformPoint")
            self.tree.links.new(
                self.tree.nodes.new("GeometryNodeInputPosition").outputs["Position"],
                position.inputs["Vector"],
            )
            self.tree.links.new(info.outputs["Transform"], position.inputs["Transform"])
            normal = self.tree.nodes.new("FunctionNodeTransformDirection")
            self.tree.links.new(
                self.tree.nodes.new("GeometryNodeInputNormal").outputs["Normal"],
                normal.inputs["Direction"],
            )
            self.tree.links.new(info.outputs["Transform"], normal.inputs["Transform"])
            self.nodes[old.name] = position
            self.outputs[(old.name, "Position")] = position.outputs["Vector"]
            self.outputs[(old.name, "Normal")] = normal.outputs["Direction"]
            return
        if kind == "ShaderNodeRGB":
            node = self.tree.nodes.new("FunctionNodeInputColor")
            value = old.outputs["Color"].default_value
            for name in ("value", "color"):
                if hasattr(node, name):
                    setattr(node, name, value)
                    break
            self.nodes[old.name] = node
            self.outputs[(old.name, "Color")] = node.outputs[0]
            return
        if kind == "ShaderNodeUVMap":
            uv_map = narrow(old, bpy.types.ShaderNodeUVMap).uv_map
            if not uv_map:
                raise Unsupported(f"{old.name} uses the default UV map")
            node = self.named_attribute(uv_map, "FLOAT_VECTOR")
            self.nodes[old.name] = node
            self.outputs[(old.name, "UV")] = node.outputs["Attribute"]
            return
        if kind == "ShaderNodeTexImage":
            tex = narrow(old, bpy.types.ShaderNodeTexImage)
            if not tex.inputs["Vector"].links:
                raise Unsupported(f"{old.name} uses the default UV map")
            node = self.tree.nodes.new("GeometryNodeImageTexture")
            node.inputs["Image"].default_value = tex.image
            setattr(node, "interpolation", tex.interpolation)
            setattr(node, "extension", tex.extension)
            self.nodes[old.name] = node
            return
        if kind.startswith("ShaderNodeRBR") or kind == "ShaderNodeGroup":
            raise Unsupported(f"{old.name} cannot run in geometry nodes")
        try:
            node = self.tree.nodes.new(kind)
        except RuntimeError:
            raise Unsupported(f"{old.name} cannot run in geometry nodes")
        _copy_settings(old, node)
        self.nodes[old.name] = node

    def output(self, socket: bpy.types.NodeSocket) -> bpy.types.NodeSocket:
        node = socket.node
        assert node is not None
        special = self.outputs.get((node.name, socket.name))
        if special is not None:
            return special
        new = self.nodes[node.name]
        found = new.outputs.get(socket.identifier) or new.outputs.get(socket.name)
        if found is None:
            raise Unsupported(f"{node.name} has no '{socket.name}' output here")
        return found

    def link(self, old_link: bpy.types.NodeLink) -> None:
        to_node = self.nodes[old_link.to_node.name]
        to_socket = to_node.inputs.get(
            old_link.to_socket.identifier
        ) or to_node.inputs.get(old_link.to_socket.name)
        if to_socket is None:
            raise Unsupported(
                f"{old_link.to_node.name} has no '{old_link.to_socket.name}' input here"
            )
        self.tree.links.new(self.output(old_link.from_socket), to_socket)


def _store_value_socket(store: bpy.types.Node, data_type: str) -> bpy.types.NodeSocket:
    setattr(store, "data_type", data_type)
    for socket in store.inputs:
        if socket.name == "Value" and socket.enabled:
            return socket
    raise Unsupported("store node has no value input")


def _attribute_name(material: bpy.types.Material, socket: bpy.types.NodeSocket) -> str:
    return f"{material.name} {socket.name}"[:60]


def _users(material: bpy.types.Material) -> List[bpy.types.Object]:
    return [
        obj
        for obj in bpy.data.objects
        if obj.library is None
        and isinstance(obj.data, bpy.types.Mesh)
        and any(slot.material == material for slot in obj.material_slots)
    ]


def convert_one(
    material: bpy.types.Material, rbr: ShaderNodeRBR, socket: bpy.types.NodeSocket
) -> str:
    node_tree = material.node_tree
    assert node_tree is not None
    link = socket.links[0]
    attribute = _attribute_name(material, socket)
    old_nodes = _upstream_nodes(link.from_node)
    tree = narrow(
        bpy.data.node_groups.new(f"RBR {attribute}", "GeometryNodeTree"),
        bpy.types.GeometryNodeTree,
    )
    try:
        tree.is_modifier = True
        tree.interface.new_socket(
            "Geometry", in_out="INPUT", socket_type="NodeSocketGeometry"
        )
        tree.interface.new_socket(
            "Geometry", in_out="OUTPUT", socket_type="NodeSocketGeometry"
        )
        group_in = tree.nodes.new("NodeGroupInput")
        group_out = tree.nodes.new("NodeGroupOutput")
        store = tree.nodes.new("GeometryNodeStoreNamedAttribute")
        setattr(store, "domain", "CORNER")
        value = _store_value_socket(store, STORE_TYPES[socket.type])
        store.inputs["Name"].default_value = attribute
        tree.links.new(group_in.outputs["Geometry"], store.inputs["Geometry"])
        tree.links.new(store.outputs["Geometry"], group_out.inputs["Geometry"])
        builder = _Builder(tree)
        for old in old_nodes:
            builder.add(old)
            builder.nodes[old.name].location = old.location
        copied = {old.name for old in old_nodes}
        for old_link in node_tree.links:
            if old_link.from_node.name in copied and old_link.to_node.name in copied:
                builder.link(old_link)
        tree.links.new(builder.output(link.from_socket), value)
        store.location = (link.from_node.location.x + 300, link.from_node.location.y)
        group_out.location = (store.location.x + 300, store.location.y)
        group_in.location = (store.location.x - 200, store.location.y + 200)
    except Unsupported:
        bpy.data.node_groups.remove(tree)
        raise

    reader = narrow(
        node_tree.nodes.new("ShaderNodeAttribute"), bpy.types.ShaderNodeAttribute
    )
    reader.attribute_type = "GEOMETRY"
    reader.attribute_name = attribute
    reader.label = "from geometry nodes"
    reader.location = link.from_node.location
    output = next(
        out for out in reader.outputs if out.name in ATTRIBUTE_OUTPUTS[socket.type]
    )
    node_tree.links.remove(link)
    node_tree.links.new(output, socket)
    _remove_orphans(node_tree, old_nodes)

    for obj in _users(material):
        if any(
            isinstance(mod, bpy.types.NodesModifier) and mod.node_group == tree
            for mod in obj.modifiers
        ):
            continue
        modifier = narrow(
            obj.modifiers.new(tree.name, "NODES"), bpy.types.NodesModifier
        )
        modifier.node_group = tree
    return tree.name


def _remove_orphans(
    node_tree: bpy.types.NodeTree, old_nodes: List[bpy.types.Node]
) -> None:
    remaining = {node.name for node in old_nodes}
    changed = True
    while changed:
        changed = False
        for name in list(remaining):
            node = node_tree.nodes.get(name)
            if node is None:
                remaining.discard(name)
                continue
            if any(socket.links for socket in node.outputs):
                continue
            node_tree.nodes.remove(node)
            remaining.discard(name)
            changed = True


def move_node_maths(log: Log) -> int:
    count = 0
    for material, rbr, socket in candidates():
        if not socket.links:
            continue
        try:
            tree = convert_one(material, rbr, socket)
        except Unsupported as why:
            log.manual(
                f"material '{material.name}': input '{socket.name}' was left alone, {why}"
            )
            continue
        log.info(
            f"material '{material.name}': input '{socket.name}' now comes from the geometry nodes modifier '{tree}'"
        )
        count += 1
    return count
