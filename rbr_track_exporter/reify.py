"""Resolving what feeds a shader node input, for reifying materials: sees
through reroutes, tint sets and plain node groups. Kept free of the native
core so it can be tested on its own."""

from typing import Iterable, NamedTuple, Optional, Tuple, Union

import bpy
from .blender_utils import NODE_PATH_SEPARATOR, group_output, socket
from .shaders.tint_set import ShaderNodeRBRTintSet


class ReifyMaterialError(Exception):
    def __init__(self, message: str, node_name: Optional[str]):
        self.message = message
        self.node_name = node_name

    def __str__(self) -> str:
        return f"{self.message}"


# The plain group nodes entered to reach a node, outermost first.
GroupPath = Tuple[bpy.types.ShaderNodeGroup, ...]


def node_ref(node: bpy.types.Node, path: GroupPath) -> str:
    return NODE_PATH_SEPARATOR.join([g.name for g in path] + [node.name])


class Upstream(NamedTuple):
    node: bpy.types.Node
    socket: bpy.types.NodeSocket
    path: GroupPath


TINT_SET_INPUTS = {"M": "Morning", "N": "Noon", "E": "Evening", "O": "Overcast"}


def follow(
    input: bpy.types.NodeSocket, path: GroupPath, tint_set: str
) -> Union[Upstream, bpy.types.NodeSocket]:
    """What feeds input, seeing through reroutes, tint sets and plain node
    groups as if the groups were dissolved: the upstream output, or the
    unlinked socket whose default value applies."""
    while True:
        if len(input.links) == 0:
            return input
        link = input.links[0]
        node = link.from_node
        if isinstance(node, bpy.types.NodeReroute):
            input = node.inputs[0]
            if len(input.links) == 0:
                raise ReifyMaterialError(
                    "Reroute has nothing connected", node_ref(node, path)
                )
        elif isinstance(node, ShaderNodeRBRTintSet) and tint_set in TINT_SET_INPUTS:
            input = socket(node.inputs, TINT_SET_INPUTS[tint_set])
            if len(input.links) == 0:
                raise ReifyMaterialError(
                    f"Missing node input for tint set '{TINT_SET_INPUTS[tint_set]}'",
                    node_ref(node, path),
                )
        elif isinstance(node, bpy.types.ShaderNodeGroup):
            try:
                if node.node_tree is None:
                    raise KeyError(node.name)
                output = group_output(node.node_tree)
            except KeyError:
                raise ReifyMaterialError(
                    "Group node has no group output", node_ref(node, path)
                )
            input = by_identifier(output.inputs, link.from_socket.identifier)
            path = path + (node,)
        elif isinstance(node, bpy.types.NodeGroupInput) and len(path) > 0:
            input = by_identifier(path[-1].inputs, link.from_socket.identifier)
            path = path[:-1]
        else:
            return Upstream(node, link.from_socket, path)


def by_identifier(
    sockets: Iterable[bpy.types.NodeSocket], identifier: str
) -> bpy.types.NodeSocket:
    return next(s for s in sockets if s.identifier == identifier)


def linked(
    input: bpy.types.NodeSocket, path: GroupPath, tint_set: str
) -> Optional[Upstream]:
    source = follow(input, path, tint_set)
    return source if isinstance(source, Upstream) else None
