"""Resolving what feeds a shader node input, for reifying materials: sees
through reroutes, tint sets and plain node groups. Kept free of the native
core so it can be tested on its own."""

from typing import Iterable, List, NamedTuple, Optional, Sequence, Tuple, Union

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
    return follow_hops(input, path, tint_set)[0]


# A link's (from, to) socket kinds, as Blender converts values along it, or
# TINT_SET_HOP where a value goes through a tint set's colour mixing.
Hop = Tuple[str, str]
TINT_SET_HOP: Hop = ("TINT_SET", "TINT_SET")


def follow_hops(
    input: bpy.types.NodeSocket, path: GroupPath, tint_set: str
) -> Tuple[Union[Upstream, bpy.types.NodeSocket], List[Hop]]:
    """follow, and the links passed on the way, nearest the source first."""
    hops: List[Hop] = []
    while True:
        if len(input.links) == 0:
            return input, hops
        link = input.links[0]
        hops.insert(0, (socket_kind(link.from_socket), socket_kind(link.to_socket)))
        node = link.from_node
        if isinstance(node, bpy.types.NodeReroute):
            input = node.inputs[0]
            if len(input.links) == 0:
                raise ReifyMaterialError(
                    "Reroute has nothing connected", node_ref(node, path)
                )
        elif isinstance(node, ShaderNodeRBRTintSet) and tint_set in TINT_SET_INPUTS:
            hops.insert(0, TINT_SET_HOP)
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
            return Upstream(node, link.from_socket, path), hops


def socket_kind(s: bpy.types.NodeSocket) -> str:
    """The value type Blender converts a socket's values to: FLOAT, INT, BOOL,
    COLOR, FLOAT2, FLOAT3 or FLOAT4 (vectors by their dimensions)."""
    if s.type == "VECTOR":
        default = getattr(s, "default_value", None)
        return f"FLOAT{len(default) if default is not None else 3}"
    return {
        "VALUE": "FLOAT",
        "INT": "INT",
        "BOOLEAN": "BOOL",
        "RGBA": "COLOR",
    }.get(s.type, s.type)


Value = Union[float, int, bool, Tuple[float, ...]]

# Blender's colour config (luma) weights, which don't follow the working space.
LUMINANCE = (0.2126, 0.7152, 0.0722)


def luminance(rgb: Sequence[float]) -> float:
    return sum(c * w for c, w in zip(rgb, LUMINANCE))


def _floats(value: Value, kind: str) -> Tuple[float, ...]:
    if kind in ("FLOAT", "INT", "BOOL"):
        return (float(value),)  # type: ignore[arg-type]
    return tuple(value)  # type: ignore[arg-type]


def _to_float(value: Value, kind: str) -> float:
    if kind == "COLOR":
        return luminance(_floats(value, kind)[:3])
    v = _floats(value, kind)
    return sum(v) / len(v)


def convert_constant(value: Value, from_kind: str, to_kind: str) -> Value:
    """An unlinked value converted between socket kinds the way Blender's
    implicit conversions (blenkernel type_conversions.cc) do."""
    if from_kind == to_kind:
        return value
    if to_kind == "FLOAT":
        return _to_float(value, from_kind)
    if to_kind == "INT":
        return int(_to_float(value, from_kind))
    if to_kind == "BOOL":
        if from_kind in ("FLOAT", "INT", "COLOR"):
            return _to_float(value, from_kind) > 0.0
        return any(c != 0.0 for c in _floats(value, from_kind))
    if from_kind in ("FLOAT", "INT", "BOOL"):
        f = float(value)  # type: ignore[arg-type]
        if to_kind == "COLOR":
            return (f, f, f, 1.0)
        return (f,) * int(to_kind[5:])
    v = _floats(value, from_kind)
    if to_kind == "COLOR":
        return (v + (0.0, 0.0, 0.0))[:3] + (v[3] if len(v) == 4 else 1.0,)
    if from_kind == "COLOR":
        return v[: int(to_kind[5:])]
    n = int(to_kind[5:])
    return (v + (0.0, 0.0, 0.0))[:n]


def convert_constant_hops(
    value: Value, kind: str, hops: List[Hop], to_kind: str
) -> Value:
    """An unlinked value carried along links, converted at each one. A tint
    set mixes it into a linked colour, which converts as linked values do."""
    for i, hop in enumerate(hops):
        if hop == TINT_SET_HOP:
            return convert_linked(value, kind, hops[i:], to_kind)
        from_kind, hop_to_kind = hop
        value = convert_constant(value, kind, from_kind)
        value = convert_constant(value, from_kind, hop_to_kind)
        kind = hop_to_kind
    return value


def link_conversions(hops: List[Hop]) -> List[str]:
    """What happens to a linked value on the way: Blender only converts it at
    boolean sockets (> 0, or a vector's length > 0) and in tint sets'
    colour mixing; the shader input does the rest."""
    conversions = []
    for hop in hops:
        if hop == TINT_SET_HOP:
            conversions.append("TO_COLOR")
        elif hop[1] == "BOOL" and hop[0] != "BOOL":
            is_vector = hop[0].startswith("FLOAT") and hop[0] != "FLOAT"
            conversions.append("LENGTH" if is_vector else "POSITIVE")
    return conversions


def convert_linked(value: Value, kind: str, hops: List[Hop], to_kind: str) -> Value:
    """A linked value (an RGB node's colour, or a constant past a tint set)
    through the link conversions and the shader input's own conversion."""
    for conversion in link_conversions(hops):
        if conversion == "TO_COLOR":
            value, kind = convert_constant(value, kind, "COLOR"), "COLOR"
            continue
        if conversion == "LENGTH":
            v = _floats(value, kind)
            test = any(c != 0.0 for c in (v[:3] if kind == "COLOR" else v))
        else:
            test = _to_float(value, kind) > 0.0
        value, kind = (1.0 if test else 0.0), "FLOAT"
    if to_kind == "FLOAT":
        return _to_float(value, kind)
    return convert_constant(value, kind, "COLOR")


def by_identifier(
    sockets: Iterable[bpy.types.NodeSocket], identifier: str
) -> bpy.types.NodeSocket:
    return next(s for s in sockets if s.identifier == identifier)


def linked(
    input: bpy.types.NodeSocket, path: GroupPath, tint_set: str
) -> Optional[Upstream]:
    source = follow(input, path, tint_set)
    return source if isinstance(source, Upstream) else None
