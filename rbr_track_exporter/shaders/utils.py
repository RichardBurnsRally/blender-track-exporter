"""Shader node helper functions."""

from __future__ import annotations

from typing import TYPE_CHECKING, Optional, Sequence, Tuple, Union

import bpy
from ..blender_utils import narrow, new_node, socket

if TYPE_CHECKING:
    from bpy.stub_internal.rna_enums import (
        NodeMathItems,
        NodeVecMathItems,
        RampBlendItems,
    )


def magic_link(
    node_tree: bpy.types.NodeTree,
    source: Union[bpy.types.NodeSocket, float, Sequence[float]],
    target: bpy.types.NodeSocket,
) -> None:
    if isinstance(source, bpy.types.NodeSocket):
        node_tree.links.new(source, target)
    else:
        target.default_value = source


def scene_time_seconds(node_tree: bpy.types.NodeTree) -> bpy.types.NodeSocketFloat:
    frame = new_node(node_tree.nodes, bpy.types.ShaderNodeAttribute)
    frame.attribute_type = "VIEW_LAYER"
    frame.attribute_name = "frame_current"
    fps = new_node(node_tree.nodes, bpy.types.ShaderNodeAttribute)
    fps.attribute_type = "VIEW_LAYER"
    fps.attribute_name = "render.fps"
    return narrow(
        float_divide(
            node_tree, socket(frame.outputs, "Factor"), socket(fps.outputs, "Factor")
        ),
        bpy.types.NodeSocketFloat,
    )


def rbr_scene_attr(
    node_tree: bpy.types.NodeTree, name: str
) -> bpy.types.ShaderNodeAttribute:
    node = new_node(node_tree.nodes, bpy.types.ShaderNodeAttribute)
    node.attribute_type = "VIEW_LAYER"
    node.attribute_name = "rbr_scene_settings." + name
    return node


def rbr_world_attr(
    node_tree: bpy.types.NodeTree, name: str
) -> bpy.types.ShaderNodeAttribute:
    node = new_node(node_tree.nodes, bpy.types.ShaderNodeAttribute)
    node.attribute_type = "VIEW_LAYER"
    node.attribute_name = "world.rbr_world_settings." + name
    return node


def rbr_world_float(
    node_tree: bpy.types.NodeTree, name: str
) -> bpy.types.NodeSocketFloat:
    node = rbr_world_attr(node_tree, name)
    return narrow(socket(node.outputs, "Factor"), bpy.types.NodeSocketFloat)


def rbr_scene_float(
    node_tree: bpy.types.NodeTree, name: str
) -> bpy.types.NodeSocketFloat:
    node = rbr_scene_attr(node_tree, name)
    return narrow(socket(node.outputs, "Factor"), bpy.types.NodeSocketFloat)


def rbr_world_vector(
    node_tree: bpy.types.NodeTree, name: str
) -> bpy.types.NodeSocketVector:
    node = rbr_world_attr(node_tree, name)
    return narrow(socket(node.outputs, "Vector"), bpy.types.NodeSocketVector)


def rbr_scene_vector(
    node_tree: bpy.types.NodeTree, name: str
) -> bpy.types.NodeSocketVector:
    node = rbr_scene_attr(node_tree, name)
    return narrow(socket(node.outputs, "Vector"), bpy.types.NodeSocketVector)


def rbr_world_color(
    node_tree: bpy.types.NodeTree, name: str
) -> bpy.types.NodeSocketColor:
    node = rbr_world_attr(node_tree, name)
    return narrow(socket(node.outputs, "Color"), bpy.types.NodeSocketColor)


def rgb_to_bw(
    node_tree: bpy.types.NodeTree,
    input: bpy.types.NodeSocketColor,
) -> bpy.types.NodeSocketFloat:
    node = new_node(node_tree.nodes, bpy.types.ShaderNodeRGBToBW)
    node_tree.links.new(socket(node.inputs, "Color"), input)
    return narrow(socket(node.outputs, "Val"), bpy.types.NodeSocketFloat)


def rgb_to_value(
    node_tree: bpy.types.NodeTree,
    input: bpy.types.NodeSocket,
) -> bpy.types.NodeSocketFloat:
    node = new_node(node_tree.nodes, bpy.types.ShaderNodeSeparateColor)
    node.mode = "HSV"
    node_tree.links.new(socket(node.inputs, "Color"), input)
    return narrow(socket(node.outputs, "Blue"), bpy.types.NodeSocketFloat)


def float_clamp(
    node_tree: bpy.types.NodeTree,
    value: Union[float, bpy.types.NodeSocket],
    min: Optional[Union[float, bpy.types.NodeSocket]] = None,
    max: Optional[Union[float, bpy.types.NodeSocket]] = None,
) -> bpy.types.NodeSocketFloat:
    node = new_node(node_tree.nodes, bpy.types.ShaderNodeClamp)
    magic_link(node_tree, value, socket(node.inputs, "Value"))
    if min is not None:
        magic_link(node_tree, min, socket(node.inputs, "Min"))
    if max is not None:
        magic_link(node_tree, max, socket(node.inputs, "Max"))
    return narrow(socket(node.outputs, "Result"), bpy.types.NodeSocketFloat)


def unary_math(
    node_tree: bpy.types.NodeTree,
    operation: NodeMathItems,
    in1: Union[float, bpy.types.NodeSocket],
    clamp: bool = False,
) -> bpy.types.NodeSocketFloat:
    node = new_node(node_tree.nodes, bpy.types.ShaderNodeMath)
    node.operation = operation
    node.use_clamp = clamp
    magic_link(node_tree, in1, socket(node.inputs, "Value", 0))
    return narrow(socket(node.outputs, "Value"), bpy.types.NodeSocketFloat)


def binary_math(
    node_tree: bpy.types.NodeTree,
    operation: NodeMathItems,
    in1: Union[float, bpy.types.NodeSocket],
    in2: Union[float, bpy.types.NodeSocket],
    clamp: bool = False,
) -> bpy.types.NodeSocketFloat:
    node = new_node(node_tree.nodes, bpy.types.ShaderNodeMath)
    node.operation = operation
    node.use_clamp = clamp
    magic_link(node_tree, in1, socket(node.inputs, "Value", 0))
    magic_link(node_tree, in2, socket(node.inputs, "Value", 1))
    return narrow(socket(node.outputs, "Value"), bpy.types.NodeSocketFloat)


def float_multiply(
    node_tree: bpy.types.NodeTree,
    in1: Union[float, bpy.types.NodeSocket],
    in2: Union[float, bpy.types.NodeSocket],
    clamp: bool = False,
) -> bpy.types.NodeSocketFloat:
    return binary_math(node_tree, "MULTIPLY", in1, in2, clamp)


def float_divide(
    node_tree: bpy.types.NodeTree,
    in1: Union[float, bpy.types.NodeSocket],
    in2: Union[float, bpy.types.NodeSocket],
    clamp: bool = False,
) -> bpy.types.NodeSocketFloat:
    return binary_math(node_tree, "DIVIDE", in1, in2, clamp)


def float_subtract(
    node_tree: bpy.types.NodeTree,
    in1: Union[float, bpy.types.NodeSocket],
    in2: Union[float, bpy.types.NodeSocket],
    clamp: bool = False,
) -> bpy.types.NodeSocketFloat:
    return binary_math(node_tree, "SUBTRACT", in1, in2, clamp)


def float_add(
    node_tree: bpy.types.NodeTree,
    in1: Union[float, bpy.types.NodeSocket],
    in2: Union[float, bpy.types.NodeSocket],
    clamp: bool = False,
) -> bpy.types.NodeSocketFloat:
    return binary_math(node_tree, "ADD", in1, in2, clamp)


def float_max(
    node_tree: bpy.types.NodeTree,
    in1: Union[float, bpy.types.NodeSocket],
    in2: Union[float, bpy.types.NodeSocket],
    clamp: bool = False,
) -> bpy.types.NodeSocketFloat:
    return binary_math(node_tree, "MAXIMUM", in1, in2, clamp)


def float_min(
    node_tree: bpy.types.NodeTree,
    in1: Union[float, bpy.types.NodeSocket],
    in2: Union[float, bpy.types.NodeSocket],
    clamp: bool = False,
) -> bpy.types.NodeSocketFloat:
    return binary_math(node_tree, "MINIMUM", in1, in2, clamp)


def float_pow(
    node_tree: bpy.types.NodeTree,
    in1: Union[float, bpy.types.NodeSocket],
    in2: Union[float, bpy.types.NodeSocket],
    clamp: bool = False,
) -> bpy.types.NodeSocketFloat:
    return binary_math(node_tree, "POWER", in1, in2, clamp)


def make_math_node(
    node_tree: bpy.types.NodeTree,
    operation: NodeMathItems,
    in1: Union[float, bpy.types.NodeSocket],
    in2: Optional[Union[float, bpy.types.NodeSocket]] = None,
    in3: Optional[Union[float, bpy.types.NodeSocket]] = None,
    clamp: bool = False,
) -> bpy.types.NodeSocketFloat:
    node = new_node(node_tree.nodes, bpy.types.ShaderNodeMath)
    node.operation = operation
    node.use_clamp = clamp
    magic_link(node_tree, in1, socket(node.inputs, "Value", 0))
    if in2 is not None:
        magic_link(node_tree, in2, socket(node.inputs, "Value", 1))
    if in3 is not None:
        magic_link(node_tree, in3, socket(node.inputs, "Value", 2))
    return narrow(socket(node.outputs, "Value"), bpy.types.NodeSocketFloat)


def mix_rgb(
    node_tree: bpy.types.NodeTree,
    fac: Union[float, bpy.types.NodeSocket],
    a: Union[Sequence[float], bpy.types.NodeSocket],
    b: Union[Sequence[float], bpy.types.NodeSocket],
    blend_type: RampBlendItems = "MIX",
    clamp: bool = False,
) -> bpy.types.NodeSocketColor:
    """Linear interpolation between two colours according to some factor"""
    node = new_node(node_tree.nodes, bpy.types.ShaderNodeMix)
    node.data_type = "RGBA"
    node.blend_type = blend_type
    node.clamp_result = clamp
    magic_link(node_tree, fac, socket(node.inputs, "Factor"))
    magic_link(node_tree, a, socket(node.inputs, "A"))
    magic_link(node_tree, b, socket(node.inputs, "B"))
    return narrow(socket(node.outputs, "Result"), bpy.types.NodeSocketColor)


# We must clamp unlit to above 0, or cycles baking outputs black regardless of
# lighting
def fixup_unlit(
    node_tree: bpy.types.NodeTree,
    input: Union[Sequence[float], bpy.types.NodeSocket],
) -> bpy.types.NodeSocket:
    return mix_rgb(node_tree, fac=0.001, a=input, b=(1, 1, 1, 1), clamp=True)


def srgb_to_linear(
    node_tree: bpy.types.NodeTree,
    input: Union[str, bpy.types.NodeSocket],
) -> bpy.types.NodeSocket:
    # TODO this isn't perfect, it needs a where clause
    separate = new_node(node_tree.nodes, bpy.types.ShaderNodeSeparateColor)
    if isinstance(input, str):
        separate.name = input
    elif isinstance(input, bpy.types.NodeSocket):
        node_tree.links.new(input, socket(separate.inputs, "Color"))
    else:
        raise NotImplementedError
    combine = new_node(node_tree.nodes, bpy.types.ShaderNodeCombineColor)
    for channel in ["Red", "Green", "Blue"]:
        add = make_math_node(
            node_tree,
            "ADD",
            socket(separate.outputs, channel),
            0.055,
        )
        divide = make_math_node(
            node_tree,
            "DIVIDE",
            add,
            1.055,
        )
        power = make_math_node(
            node_tree,
            "POWER",
            divide,
            2.4,
        )
        node_tree.links.new(power, socket(combine.inputs, channel))
    return socket(combine.outputs, "Color")


def linear_to_srgb(
    node_tree: bpy.types.NodeTree,
    input: Union[str, bpy.types.NodeSocket],
) -> bpy.types.NodeSocket:
    # TODO this isn't perfect, it needs a where clause
    separate = new_node(node_tree.nodes, bpy.types.ShaderNodeSeparateColor)
    if isinstance(input, str):
        separate.name = input
    elif isinstance(input, bpy.types.NodeSocket):
        node_tree.links.new(input, socket(separate.inputs, "Color"))
    else:
        raise NotImplementedError
    combine = new_node(node_tree.nodes, bpy.types.ShaderNodeCombineColor)
    for channel in ["Red", "Green", "Blue"]:
        power = make_math_node(
            node_tree,
            "POWER",
            socket(separate.outputs, channel),
            1 / 2.4,
        )
        mult = make_math_node(
            node_tree,
            "MULTIPLY",
            power,
            1.055,
        )
        subtract = make_math_node(
            node_tree,
            "SUBTRACT",
            mult,
            0.055,
        )
        node_tree.links.new(subtract, socket(combine.inputs, channel))
    return socket(combine.outputs, "Color")


def vector_exp(
    node_tree: bpy.types.NodeTree,
    vector: bpy.types.NodeSocketVector,
) -> bpy.types.NodeSocketVector:
    separate = new_node(node_tree.nodes, bpy.types.ShaderNodeSeparateXYZ)
    node_tree.links.new(vector, socket(separate.inputs, "Vector"))
    combine = new_node(node_tree.nodes, bpy.types.ShaderNodeCombineXYZ)
    for axis in ["X", "Y", "Z"]:
        math = make_math_node(node_tree, "EXPONENT", in1=socket(separate.outputs, axis))
        node_tree.links.new(math, socket(combine.inputs, axis))
    return narrow(socket(combine.outputs, "Vector"), bpy.types.NodeSocketVector)


def vector_power(
    node_tree: bpy.types.NodeTree,
    exponent: float,
    vector: bpy.types.NodeSocket,
) -> bpy.types.NodeSocketVector:
    return vector_math(node_tree, "POWER", vector, (exponent, exponent, exponent))


def vector_scale(
    node_tree: bpy.types.NodeTree,
    vector: Union[bpy.types.NodeSocket, Sequence[float]],
    scale: Union[bpy.types.NodeSocket, float],
) -> bpy.types.NodeSocketVector:
    scale_node = new_node(node_tree.nodes, bpy.types.ShaderNodeVectorMath)
    scale_node.operation = "SCALE"
    magic_link(node_tree, vector, socket(scale_node.inputs, "Vector", 0))
    magic_link(node_tree, scale, socket(scale_node.inputs, "Scale"))
    return narrow(socket(scale_node.outputs, "Vector"), bpy.types.NodeSocketVector)


def vector_multiply(
    node_tree: bpy.types.NodeTree,
    v1: Union[bpy.types.NodeSocket, Sequence[float]],
    v2: Union[bpy.types.NodeSocket, Sequence[float]],
) -> bpy.types.NodeSocketVector:
    return vector_math(node_tree, "MULTIPLY", v1, v2)


def vector_add(
    node_tree: bpy.types.NodeTree,
    v1: Union[bpy.types.NodeSocket, Sequence[float]],
    v2: Union[bpy.types.NodeSocket, Sequence[float]],
) -> bpy.types.NodeSocketVector:
    return vector_math(node_tree, "ADD", v1, v2)


def vector_subtract(
    node_tree: bpy.types.NodeTree,
    v1: Union[bpy.types.NodeSocket, Sequence[float]],
    v2: Union[bpy.types.NodeSocket, Sequence[float]],
) -> bpy.types.NodeSocketVector:
    return vector_math(node_tree, "SUBTRACT", v1, v2)


def vector_abs(
    node_tree: bpy.types.NodeTree,
    v1: Union[bpy.types.NodeSocket, Sequence[float]],
) -> bpy.types.NodeSocketVector:
    return vector_unary_math(node_tree, "ABSOLUTE", v1)


def vector_unary_math(
    node_tree: bpy.types.NodeTree,
    operation: NodeVecMathItems,
    v1: Union[bpy.types.NodeSocket, Sequence[float]],
) -> bpy.types.NodeSocketVector:
    add = new_node(node_tree.nodes, bpy.types.ShaderNodeVectorMath)
    add.operation = operation
    magic_link(node_tree, v1, socket(add.inputs, "Vector", 0))
    return narrow(socket(add.outputs, "Vector"), bpy.types.NodeSocketVector)


def vector_math(
    node_tree: bpy.types.NodeTree,
    operation: NodeVecMathItems,
    v1: Union[bpy.types.NodeSocket, Sequence[float]],
    v2: Union[bpy.types.NodeSocket, Sequence[float]],
) -> bpy.types.NodeSocketVector:
    add = new_node(node_tree.nodes, bpy.types.ShaderNodeVectorMath)
    add.operation = operation
    magic_link(node_tree, v1, socket(add.inputs, "Vector", 0))
    magic_link(node_tree, v2, socket(add.inputs, "Vector", 1))
    return narrow(socket(add.outputs, "Vector"), bpy.types.NodeSocketVector)


def vector_math_float(
    node_tree: bpy.types.NodeTree,
    operation: NodeVecMathItems,
    v1: Union[bpy.types.NodeSocket, Sequence[float]],
    v2: Union[bpy.types.NodeSocket, Sequence[float]],
) -> bpy.types.NodeSocketFloat:
    add = new_node(node_tree.nodes, bpy.types.ShaderNodeVectorMath)
    add.operation = operation
    magic_link(node_tree, v1, socket(add.inputs, "Vector", 0))
    magic_link(node_tree, v2, socket(add.inputs, "Vector", 1))
    return narrow(socket(add.outputs, "Value"), bpy.types.NodeSocketFloat)


def float_select(
    node_tree: bpy.types.NodeTree,
    factor: Union[bpy.types.NodeSocket, float],
    if_0: Union[bpy.types.NodeSocket, float],
    if_1: Union[bpy.types.NodeSocket, float],
) -> bpy.types.NodeSocketFloat:
    """if_0 where factor is 0, if_1 where it's 1."""
    switch = new_node(node_tree.nodes, bpy.types.GeometryNodeSwitch)
    switch.input_type = "FLOAT"
    magic_link(node_tree, factor, socket(switch.inputs, "Switch"))
    magic_link(node_tree, if_0, socket(switch.inputs, "False"))
    magic_link(node_tree, if_1, socket(switch.inputs, "True"))
    return narrow(socket(switch.outputs, "Output"), bpy.types.NodeSocketFloat)


def rgb_select(
    node_tree: bpy.types.NodeTree,
    factor: Union[bpy.types.NodeSocket, float],
    if_0: Union[bpy.types.NodeSocket, Sequence[float]],
    if_1: Union[bpy.types.NodeSocket, Sequence[float]],
) -> bpy.types.NodeSocketColor:
    """if_0 where factor is 0, if_1 where it's 1."""
    switch = new_node(node_tree.nodes, bpy.types.GeometryNodeSwitch)
    switch.input_type = "RGBA"
    magic_link(node_tree, factor, socket(switch.inputs, "Switch"))
    magic_link(node_tree, if_0, socket(switch.inputs, "False"))
    magic_link(node_tree, if_1, socket(switch.inputs, "True"))
    return narrow(socket(switch.outputs, "Output"), bpy.types.NodeSocketColor)
