"""RBR Texture nodes output one bundle (colour and alpha) instead of a colour
and an alpha socket, and RBR Shaders take one bundle input per texture.

Detected from the node trees rather than the file's version, so it runs once
on any file still built the old way."""

import dataclasses
from typing import Dict, List, Optional, Tuple

import bpy

from ..blender_utils import narrow, new_node, socket
from ..shaders.refresh import SavedLink, refresh_all_rbr_shaders
from ..shaders.shader_node import SHADER_PREFIX, ShaderNodeRBR
from ..shaders.texture import (
    RBR_TEXTURE_NODE_TREE_PREFIX,
    RBR_TEXTURE_OUTPUT,
    TEXTURE_BUNDLE_ALPHA,
    TEXTURE_BUNDLE_COLOR,
    TEXTURE_BUNDLE_PRESENT,
    ShaderNodeRBRTexture,
)

OLD_COLOR_OUTPUT = "RBR Texture Color"
OLD_ALPHA_OUTPUT = "RBR Texture Alpha"
# The old texture colour inputs and the alpha input each came with.
OLD_TEXTURE_INPUTS: Dict[str, Optional[str]] = {
    "Texture 1": "Texture 1 Alpha",
    "Texture 2": "Texture 2 Alpha",
    "Texture": "Texture Alpha",
    "Specular Texture": None,
}
OLD_ALPHA_INPUTS = {a for a in OLD_TEXTURE_INPUTS.values() if a is not None}


def _interface_names(tree: bpy.types.NodeTree, in_out: str) -> List[str]:
    return [
        item.name
        for item in tree.interface.items_tree
        if isinstance(item, bpy.types.NodeTreeInterfaceSocket) and item.in_out == in_out
    ]


def needs_migration() -> bool:
    for tree in bpy.data.node_groups:
        if tree.library is not None:
            continue
        if tree.name.startswith(RBR_TEXTURE_NODE_TREE_PREFIX):
            if OLD_COLOR_OUTPUT in _interface_names(tree, "OUTPUT"):
                return True
        elif tree.name.startswith(SHADER_PREFIX):
            if OLD_ALPHA_INPUTS & set(_interface_names(tree, "INPUT")):
                return True
    return False


def _origin(input: bpy.types.NodeSocket) -> Optional[bpy.types.NodeSocket]:
    """The output feeding input, through reroutes."""
    while input.is_linked:
        output = input.links[0].from_socket
        if not isinstance(output.node, bpy.types.NodeReroute):
            return output
        input = output.node.inputs[0]
    return None


@dataclasses.dataclass
class _Bundled:
    """An old texture input fed by something other than an RBR Texture (such
    as the fence preview's image), to feed through a new Combine Bundle."""

    shader: str
    input: str
    color: Tuple[str, str]
    alpha: Optional[Tuple[str, str]]


def _find_bundled(tree: bpy.types.NodeTree) -> List[_Bundled]:
    found = []
    for node in tree.nodes:
        if not isinstance(node, ShaderNodeRBR):
            continue
        for color_name, alpha_name in OLD_TEXTURE_INPUTS.items():
            color_input = node.inputs.get(color_name)
            if color_input is None or color_input.type != "RGBA":
                continue
            color = _origin(color_input)
            if color is None or color.node is None:
                continue
            if isinstance(color.node, ShaderNodeRBRTexture):
                continue
            alpha_input = node.inputs.get(alpha_name) if alpha_name else None
            alpha = _origin(alpha_input) if alpha_input is not None else None
            alpha_source = None
            if alpha is not None and alpha.node is not None:
                alpha_source = (alpha.node.name, alpha.identifier)
            found.append(
                _Bundled(
                    node.name,
                    color_name,
                    (color.node.name, color.identifier),
                    alpha_source,
                )
            )
    return found


def rewrite_links(
    material: bpy.types.Material, links: List[SavedLink]
) -> List[SavedLink]:
    """A texture's colour link becomes its bundle link; its alpha links, and
    links into an RBR Shader's old texture alpha inputs, go."""
    tree = material.node_tree
    if tree is None:
        return links
    out = []
    for link in links:
        if link.from_socket == OLD_ALPHA_OUTPUT:
            continue
        if link.to_socket in OLD_ALPHA_INPUTS and isinstance(
            tree.nodes.get(link.to_node), ShaderNodeRBR
        ):
            continue
        if link.from_socket == OLD_COLOR_OUTPUT:
            link = dataclasses.replace(link, from_socket=RBR_TEXTURE_OUTPUT, from_nth=0)
        out.append(link)
    return out


def combine_texture(
    tree: bpy.types.NodeTree,
    target: bpy.types.NodeSocket,
    color: bpy.types.NodeSocket,
    alpha: Optional[bpy.types.NodeSocket],
) -> None:
    """Feed target a new Combine Bundle of color and alpha."""
    for link in list(target.links):
        tree.links.remove(link)
    shader = narrow(target.node, bpy.types.Node)
    combine = new_node(tree.nodes, bpy.types.NodeCombineBundle)
    combine.location = (shader.location.x - 200, shader.location.y + 150)
    combine.bundle_items.new("RGBA", TEXTURE_BUNDLE_COLOR)
    combine.bundle_items.new("FLOAT", TEXTURE_BUNDLE_ALPHA)
    combine.bundle_items.new("FLOAT", TEXTURE_BUNDLE_PRESENT)
    socket(combine.inputs, TEXTURE_BUNDLE_ALPHA).default_value = 1.0
    socket(combine.inputs, TEXTURE_BUNDLE_PRESENT).default_value = 1.0
    tree.links.new(color, socket(combine.inputs, TEXTURE_BUNDLE_COLOR))
    if alpha is not None:
        tree.links.new(alpha, socket(combine.inputs, TEXTURE_BUNDLE_ALPHA))
    tree.links.new(socket(combine.outputs, "Bundle"), target)


def _output(tree: bpy.types.NodeTree, source: Tuple[str, str]) -> bpy.types.NodeSocket:
    node_name, identifier = source
    return next(o for o in tree.nodes[node_name].outputs if o.identifier == identifier)


def _combine(tree: bpy.types.NodeTree, bundled: _Bundled) -> None:
    shader = tree.nodes[bundled.shader]
    combine_texture(
        tree,
        socket(shader.inputs, bundled.input),
        _output(tree, bundled.color),
        _output(tree, bundled.alpha) if bundled.alpha is not None else None,
    )


def invalid_texture_links() -> List[str]:
    """Links from an RBR Texture into something that can't take its bundle."""
    found = []
    for material in bpy.data.materials:
        tree = material.node_tree
        if tree is None:
            continue
        for link in tree.links:
            if not link.is_valid and isinstance(link.from_node, ShaderNodeRBRTexture):
                found.append(
                    f"material '{material.name}': texture "
                    f"'{link.from_node.name}' fed '{link.to_node.name}', which "
                    "can't take a texture now; reconnect it"
                )
    return found


def migrate(context: bpy.types.Context) -> None:
    if not needs_migration():
        return
    bundled: Dict[str, List[_Bundled]] = {}
    for material in bpy.data.materials:
        if material.node_tree is not None and material.library is None:
            bundled[material.name] = _find_bundled(material.node_tree)
    refresh_all_rbr_shaders(context, rewrite_links)
    for name, found in bundled.items():
        tree = bpy.data.materials[name].node_tree
        if tree is None:
            continue
        for b in found:
            _combine(tree, b)
    for message in invalid_texture_links():
        print(f"RBR Addon: {message}")
    print("RBR Addon: migrated textures to bundles")
