"""A shader node for switching based on tint set."""

from typing import Optional

import bpy
from ..blender_utils import (
    group_input,
    group_output,
    local_node_group,
    narrow,
    new_node,
    socket,
)

from .utils import rbr_scene_float

TINT_SET_NODE_TREE_NAME: str = ".RBRTintSetTreeV0"


def setup_tint_set_node_tree() -> bpy.types.NodeTree:
    node_tree = bpy.data.node_groups.new(TINT_SET_NODE_TREE_NAME, "ShaderNodeTree")
    # Create the internal group input and output nodes
    new_node(node_tree.nodes, bpy.types.NodeGroupInput)
    new_node(node_tree.nodes, bpy.types.NodeGroupOutput)

    # Add the input and output sockets (this also adjusts the group
    # inputs/outputs)
    def mk_input(name: str) -> bpy.types.NodeTreeInterfaceSocket:
        s = node_tree.interface.new_socket(
            name, in_out="INPUT", socket_type="NodeSocketColor"
        )
        s.hide_value = True
        return s

    mk_input("Morning")
    mk_input("Noon")
    mk_input("Evening")
    mk_input("Overcast")
    node_tree.interface.new_socket(
        "Color", in_out="OUTPUT", socket_type="NodeSocketColor"
    )
    switch = new_node(node_tree.nodes, bpy.types.GeometryNodeIndexSwitch)
    switch.data_type = "RGBA"
    switch.index_switch_items.new()
    switch.index_switch_items.new()
    node_tree.links.new(
        socket(switch.inputs, "Index"),
        rbr_scene_float(node_tree, "active_tint_set_int"),
    )
    for i, name in enumerate(["Morning", "Noon", "Evening", "Overcast"]):
        node_tree.links.new(
            socket(switch.inputs, str(i)), socket(group_input(node_tree).outputs, name)
        )
    node_tree.links.new(
        socket(group_output(node_tree).inputs, "Color"),
        socket(switch.outputs, "Output"),
    )
    return node_tree


class ShaderNodeRBRTintSet(bpy.types.ShaderNodeCustomGroup):
    """Choose a texture or attribute layer based on RBR tint set."""

    bl_name = "ShaderNodeRBRTintSet"
    bl_label = "RBR Tint Set"
    # This is a field of ShaderNodeCustomGroup
    node_tree: Optional[bpy.types.ShaderNodeTree] = None

    # Setup the node - setup the node tree and add the group Input and Output nodes
    def init(self, context: bpy.types.Context) -> None:
        # Try to use an existing tree (if one of these nodes was previously
        # created). This means we only have a single driven time node, and
        # thereby avoids the performance penalty of having N driven nodes
        # active at once. The downside to this is that we need to lift the
        # velocity input to a node socket, but we don't actually support the
        # user connecting things to the socket when exporting.
        existing_tree = local_node_group(TINT_SET_NODE_TREE_NAME)
        if isinstance(existing_tree, bpy.types.ShaderNodeTree):
            self.node_tree = existing_tree
        else:
            self.node_tree = narrow(
                setup_tint_set_node_tree(), bpy.types.ShaderNodeTree
            )
        for name in ["Morning", "Noon", "Evening", "Overcast"]:
            socket(self.inputs, name).default_value = [1, 1, 1, 1]

    # Free (when node is deleted)
    def free(self) -> None:
        # This leaves garbage - in the form of a single node tree - if this is
        # the last active node. But if a new node is created later, that tree
        # is reused, so this seems fine.
        return

    def draw_buttons(
        self, context: bpy.types.Context, layout: bpy.types.UILayout
    ) -> None:
        return


def register() -> None:
    bpy.utils.register_class(ShaderNodeRBRTintSet)


def unregister() -> None:
    bpy.utils.unregister_class(ShaderNodeRBRTintSet)
