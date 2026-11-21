from dataclasses import dataclass
from typing import Dict, List, Optional, Set

import bpy
from ..blender_utils import socket, socket_nth

from . import shader_node
from . import sky
from . import texture


@dataclass
class SavedLink:
    from_node: str
    from_socket: str
    from_nth: int
    to_node: str
    to_socket: str
    to_nth: int


def pop_links() -> Dict[str, List[SavedLink]]:
    materials_to_relink: Dict[str, List[SavedLink]] = dict()

    def node_is_rbr(node: Optional[bpy.types.Node]) -> bool:
        return isinstance(node, shader_node.ShaderNodeRBR) or isinstance(
            node, texture.ShaderNodeRBRTexture
        )

    for material in bpy.data.materials:
        if not material.use_nodes:
            continue
        if material.node_tree is None:
            continue
        materials_to_relink[material.name] = []
        for link in material.node_tree.links:
            if node_is_rbr(link.from_node) or node_is_rbr(link.to_node):
                materials_to_relink[material.name].append(
                    SavedLink(
                        link.from_node.name,
                        link.from_socket.name,
                        socket_nth(link.from_node.outputs, link.from_socket),
                        link.to_node.name,
                        link.to_socket.name,
                        socket_nth(link.to_node.inputs, link.to_socket),
                    )
                )
            else:
                continue
            # Unlink now we have recorded it
            material.node_tree.links.remove(link)

    return materials_to_relink


def push_links(links: Dict[str, List[SavedLink]]) -> None:
    for material_name, missing_links in links.items():
        node_tree = bpy.data.materials[material_name].node_tree
        if node_tree is None:
            continue
        for link in missing_links:
            from_node = node_tree.nodes[link.from_node]
            to_node = node_tree.nodes[link.to_node]
            node_tree.links.new(
                socket(from_node.outputs, link.from_socket, link.from_nth),
                socket(to_node.inputs, link.to_socket, link.to_nth),
            )


def texture_nodes() -> List[texture.ShaderNodeRBRTexture]:
    nodes = []
    for material in bpy.data.materials:
        if material.node_tree is None:
            continue
        for node in material.node_tree.nodes:
            if isinstance(node, texture.ShaderNodeRBRTexture):
                nodes.append(node)
    return nodes


def refresh_all_rbr_shaders(context: bpy.types.Context) -> None:
    links = pop_links()
    # Rebuilding the texture tree interface recreates the instance sockets,
    # so carry the per-material address flags across.
    addresses = {}
    for node in texture_nodes():
        try:
            addresses[node.as_pointer()] = texture.get_texture_address(node)
        except KeyError:
            pass
    sky.recreate_internals()
    shader_node.recreate_internals(context)
    for _, node_tree in texture.all_rbr_texture_node_trees_filename():
        if node_tree.library is None:
            texture.recreate_internals(context, node_tree)
    for node in texture_nodes():
        address = addresses.get(node.as_pointer())
        if address is not None:
            texture.set_texture_address(node, address)
    push_links(links)
    for obj in bpy.data.objects:
        # TODO
        # obj.rbr_object_type_value = RBRObjectType[obj.rbr_object_settings.type].value
        # Must also force an update here
        obj.update_tag()
    if context.scene is None:
        return
    context.scene.rbr_scene_settings.update_world_context(context)
