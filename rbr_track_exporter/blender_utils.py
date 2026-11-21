from __future__ import annotations
import dataclasses
from dataclasses import dataclass
from typing import Any, Callable, List, Optional, TypeVar, Union

import bpy

_Node = TypeVar("_Node", bound=bpy.types.Node)
_T = TypeVar("_T")


def new_node(nodes: bpy.types.Nodes, node_type: type[_Node]) -> _Node:
    """Create a node and narrow it to its concrete type (bl_idname == class name)."""
    node = nodes.new(node_type.__name__)
    assert isinstance(node, node_type)
    return node


def narrow(value: object, expected: type[_T]) -> _T:
    """Runtime-checked narrowing for bpy getters that return an over-wide base type."""
    assert isinstance(value, expected)
    return value


def socket(
    sockets: bpy.types.NodeInputs | bpy.types.NodeOutputs,
    name: str,
    nth: Optional[int] = None,
) -> bpy.types.NodeSocket:
    """An available socket by name. `nth` picks among same-named sockets (e.g.
    Math operands); without it the name must be unique."""
    matches = [s for s in sockets if s.enabled and s.name == name]
    if nth is None and len(matches) == 1:
        return matches[0]
    if nth is not None and nth < len(matches):
        return matches[nth]
    raise KeyError(f"{name!r} [{nth}]: {len(matches)} available sockets")


def socket_nth(
    sockets: bpy.types.NodeInputs | bpy.types.NodeOutputs, target: bpy.types.NodeSocket
) -> int:
    """The `nth` that `socket` needs to find `target` again."""
    return [s for s in sockets if s.enabled and s.name == target.name].index(target)


def group_input(node_tree: bpy.types.NodeTree) -> bpy.types.NodeGroupInput:
    """Found by type: default node names are translated."""
    for node in node_tree.nodes:
        if isinstance(node, bpy.types.NodeGroupInput):
            return node
    raise KeyError(f"{node_tree.name!r} has no group input node")


def group_output(node_tree: bpy.types.NodeTree) -> bpy.types.NodeGroupOutput:
    """Found by type: default node names are translated."""
    outputs = [n for n in node_tree.nodes if isinstance(n, bpy.types.NodeGroupOutput)]
    for node in outputs:
        if node.is_active_output:
            return node
    if outputs:
        return outputs[0]
    raise KeyError(f"{node_tree.name!r} has no group output node")


def local_node_group(name: str) -> Optional[bpy.types.NodeTree]:
    """The node group of this file with that name. A linked library can hold
    a group with the same name, and that one must never be used or rebuilt:
    changes to it are lost on reload and take every link with them."""
    for node_tree in bpy.data.node_groups:
        if node_tree.name == name and node_tree.library is None:
            return node_tree
    return None


def gnodes_input(modifier: bpy.types.Modifier, identifier: str) -> Any:
    """A geometry nodes modifier input by socket identifier: has `.value`,
    `.type` ("VALUE"/"ATTRIBUTE") and `.attribute_name`."""
    # Runtime-defined RNA, absent from the stubs.
    props: Any = getattr(modifier, "properties")
    return getattr(props.inputs, identifier)


def supports_keyframe_animation(
    ui: bpy.types.UILayout,
) -> bpy.types.UILayout:
    box = ui.box()
    box.label(icon="GRAPH", text="Supports keyframe animation")
    return box


@dataclass
class Checks:
    errors: List[str] = dataclasses.field(default_factory=list)

    def union(self, other: Checks) -> None:
        self.errors.extend(other.errors)

    def draw(self, ui: bpy.types.UILayout) -> None:
        if len(self.errors) > 0:
            col = ui.column()
            col.alert = True
            for err in self.errors:
                col.label(text=err, icon="ERROR")


def mk_label(attr: str) -> str:
    return " ".join(attr.split(sep="_")).title()


def panel(
    ui: bpy.types.UILayout,
    attr: str,
    title: Union[str, Callable[[bpy.types.UILayout], None]],
    draw_content: Callable[[bpy.types.UILayout], None],
    default_closed: bool = False,
) -> None:
    panel_header, panel_content = ui.panel("rbr_" + attr, default_closed=default_closed)
    if isinstance(title, str):
        panel_header.label(text=title)
    else:
        title(panel_header)
    if panel_content is not None:
        draw_content(panel_content)


def ui_split(
    ui: bpy.types.UILayout,
    label: str,
) -> bpy.types.UILayout:
    split = ui.split(factor=0.4)
    split.alignment = "RIGHT"
    split.label(text=label)
    return split
