"""Shader nodes for RBR object types."""

from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Union
import math

from .texture import (
    ShaderNodeRBRTexture,
    tree_name_to_texture_name,
    RBR_TEXTURE_OUTPUT,
    TEXTURE_BUNDLE_ALPHA,
    TEXTURE_BUNDLE_COLOR,
    TEXTURE_BUNDLE_PRESENT,
)
from .utils import *
from . import sky

import bpy
from ..blender_utils import (
    group_input,
    group_output,
    local_node_group,
    narrow,
    new_node,
    socket,
)
from ..types import *

SHADER_PREFIX: str = ".ShaderNodeRBR."

SHADER_GB_TEXTURE_1 = "Texture 1"
SHADER_GB_TEXTURE_2 = "Texture 2"
SHADER_GB_SPECULAR_TEXTURE = "Specular Texture"
SHADER_GB_SHADOW_TEXTURE = "Shadow Texture"
SHADER_GB_COLOR = "Color"
SHADER_GB_BLEND = "Blend"
SHADER_GB_SPECULAR_STRENGTH = "Specular Strength"
SHADER_GB_COLLISION_SHADING = "Collision Shading"
SHADER_GB_OUTPUT_SURFACE = "Surface"
SHADER_GB_OUTPUT_COLOR = "Unlit Color"

SHADER_OB_TEXTURE_1 = "Texture"
SHADER_OB_COLOR = "Color"
SHADER_OB_ALPHA = "Alpha"
SHADER_OB_SWAY_FREQ = "Frequency"
SHADER_OB_SWAY_AMP = "Amplitude"
SHADER_OB_SWAY_PHASE = "Phase Offset"
SHADER_OB_OUTPUT_SURFACE = "Surface"
SHADER_OB_OUTPUT_DISPLACEMENT = "Displacement"
SHADER_OB_OUTPUT_COLOR = "Unlit Color"
SHADER_OB_OUTPUT_ALPHA = "Alpha"


@dataclass
class ObjectDataSockets:
    has_alpha: bool
    has_specular: bool

    def texture_1(self) -> str:
        return "Texture 1"

    def texture_2(self) -> str:
        return "Texture 2"

    def color(self) -> str:
        return "Color"

    def alpha_blend(self) -> str:
        if self.has_alpha:
            return "Alpha/Blend"
        else:
            return "Blend"

    def specular_texture(self) -> str:
        return "Specular Texture"

    def specular_strength(self) -> str:
        return "Specular Strength"

    def output_color(self) -> str:
        return "Unlit Color"

    def output_surface(self) -> str:
        return "Surface"


SHADER_RO_SOCKETS = ObjectDataSockets(has_alpha=True, has_specular=False)
SHADER_WO_SOCKETS = ObjectDataSockets(has_alpha=True, has_specular=True)
SHADER_SB_SOCKETS = ObjectDataSockets(has_alpha=False, has_specular=False)
SHADER_IO_SOCKETS = ObjectDataSockets(has_alpha=False, has_specular=False)


SHADER_BW_COLOR = "Color"
SHADER_BW_RESPAWN_COLOR = "Respawn Color"
SHADER_BW_OUTPUT_SURFACE = "Surface"
SHADER_CP_BACKFACE_CULL = "Backface Cull (don't connect)"
SHADER_CP_OUTPUT_SURFACE = "Surface"


def check_object_type(
    node_tree: bpy.types.NodeTree,
    object_type_socket: bpy.types.NodeSocket,
    object_type: int,
) -> bpy.types.NodeSocket:
    return make_math_node(
        node_tree,
        "COMPARE",
        object_type_socket,
        float(object_type),
        clamp=True,
    )


@dataclass
class TextureSockets:
    color: bpy.types.NodeSocket
    alpha: bpy.types.NodeSocket
    present: bpy.types.NodeSocket


def separate_texture(
    node_tree: bpy.types.NodeTree,
    bundle: bpy.types.NodeSocket,
    unconnected_color: List[float],
) -> TextureSockets:
    """A texture input's colour and alpha, and whether a texture is connected;
    where none is, the colour is unconnected_color and the alpha 1."""
    separate = new_node(node_tree.nodes, bpy.types.NodeSeparateBundle)
    separate.bundle_items.new("RGBA", TEXTURE_BUNDLE_COLOR)
    separate.bundle_items.new("FLOAT", TEXTURE_BUNDLE_ALPHA)
    separate.bundle_items.new("FLOAT", TEXTURE_BUNDLE_PRESENT)
    node_tree.links.new(bundle, socket(separate.inputs, "Bundle"))
    present = socket(separate.outputs, TEXTURE_BUNDLE_PRESENT)
    return TextureSockets(
        color=rgb_select(
            node_tree,
            present,
            unconnected_color,
            socket(separate.outputs, TEXTURE_BUNDLE_COLOR),
        ),
        alpha=float_select(
            node_tree, present, 1.0, socket(separate.outputs, TEXTURE_BUNDLE_ALPHA)
        ),
        present=present,
    )


WHITE = [1.0, 1.0, 1.0, 1.0]
BLACK = [0.0, 0.0, 0.0, 1.0]


def make_geom_block(
    node_tree: bpy.types.NodeTree,
) -> None:
    inputs = group_input(node_tree).outputs
    texture_1 = separate_texture(node_tree, socket(inputs, SHADER_GB_TEXTURE_1), WHITE)
    texture_2 = separate_texture(node_tree, socket(inputs, SHADER_GB_TEXTURE_2), WHITE)
    specular_color = separate_texture(
        node_tree, socket(inputs, SHADER_GB_SPECULAR_TEXTURE), BLACK
    ).color
    shadow_texture = socket(inputs, SHADER_GB_SHADOW_TEXTURE)
    vcol_in = socket(inputs, SHADER_GB_COLOR)
    vcol_alpha = socket(inputs, SHADER_GB_BLEND)
    specular_strength = socket(inputs, SHADER_GB_SPECULAR_STRENGTH)

    output_sockets = group_output(node_tree).inputs
    [output_surface, output_color, *_] = list(output_sockets)

    light_dir = rbr_world_vector(node_tree, "light_direction")
    # Scattering, only for textures
    scattering_coefficients = sky.scattering(
        node_tree=node_tree,
        light_dir=light_dir,
        scale=1.0,
    )
    vcol = mix_rgb(
        node_tree,
        1.0,
        vcol_in,
        scattering_coefficients.mul_scattering,
        "MULTIPLY",
        True,
    )

    # Texture 2, where connected, is blended over texture 1 by the vertex
    # alpha, and the alpha is texture 1's alone.
    alpha = float_select(
        node_tree,
        texture_2.present,
        float_multiply(node_tree, vcol_alpha, texture_1.alpha, True),
        texture_1.alpha,
    )
    blend = float_multiply(node_tree, vcol_alpha, texture_2.alpha, True)
    texture = rgb_select(
        node_tree,
        texture_2.present,
        texture_1.color,
        mix_rgb(node_tree, blend, texture_1.color, texture_2.color, "MIX", True),
    )
    texture_vcol = mix_rgb(node_tree, 1.0, vcol, texture, "MULTIPLY", True)
    beckmann_glossiness = rbr_scene_vector(node_tree, "geom_block_specular_glossiness")
    specular = make_specular(
        node_tree, light_dir, beckmann_glossiness, specular_color, specular_strength
    )

    # Add all contributions together
    result = mix_rgb(node_tree, 1.0, texture_vcol, specular, "ADD", True)
    shadow: bpy.types.NodeSocket = rgb_to_value(node_tree, shadow_texture)
    shadow = float_clamp(node_tree, shadow)
    shadow = linear_to_srgb(node_tree, shadow)
    result = mix_rgb(node_tree, 1.0, result, shadow, "MULTIPLY", True)
    result = mix_rgb(
        node_tree, 1.0, result, scattering_coefficients.add_scattering, "ADD", True
    )
    result = sky.linear_fog(node_tree, result, is_superbowl=False)

    # Back to linear now we've done all of the (bad) sRGB multiplications.
    linear_result = srgb_to_linear(node_tree, result)
    linear_unlit = srgb_to_linear(node_tree, texture)
    linear_unlit = fixup_unlit(node_tree, linear_unlit)

    # TODO does this work for geom blocks?
    # no it doesn't
    output = make_alpha_shader(node_tree, linear_result, alpha)

    node_tree.links.new(output_surface, output)
    node_tree.links.new(output_color, linear_unlit)


def make_object_block(
    node_tree: bpy.types.NodeTree,
) -> None:
    inputs = group_input(node_tree).outputs
    texture = separate_texture(node_tree, socket(inputs, SHADER_OB_TEXTURE_1), WHITE)
    texture_color = texture.color
    texture_alpha = texture.alpha
    vcol_in = socket(inputs, SHADER_OB_COLOR)
    vcol_alpha = socket(inputs, SHADER_OB_ALPHA)
    sway_freq = socket(inputs, SHADER_OB_SWAY_FREQ)
    sway_amp = socket(inputs, SHADER_OB_SWAY_AMP)
    sway_phase = socket(inputs, SHADER_OB_SWAY_PHASE)

    output_sockets = group_output(node_tree).inputs
    [output_surface, output_displacement, output_color, output_alpha, *_] = list(
        output_sockets
    )

    light_dir = rbr_world_vector(node_tree, "light_direction")
    # Scattering, only for textures
    scattering_coefficients = sky.scattering(
        node_tree=node_tree,
        light_dir=light_dir,
        scale=1.0,
    )

    result = mix_rgb(
        node_tree,
        1.0,
        vcol_in,
        scattering_coefficients.mul_scattering,
        "MULTIPLY",
        True,
    )
    result = mix_rgb(node_tree, 1.0, result, texture_color, "MULTIPLY", True)
    result = mix_rgb(
        node_tree, 1.0, result, scattering_coefficients.add_scattering, "ADD", True
    )
    result = sky.linear_fog(node_tree, result, is_superbowl=False)
    linear_color = srgb_to_linear(node_tree, result)
    alpha = float_multiply(node_tree, vcol_alpha, texture_alpha, True)
    output = make_alpha_shader(node_tree, linear_color, alpha)

    # Sway / displacement
    time = scene_time_seconds(node_tree)
    sway = make_math_node(node_tree, "MULTIPLY_ADD", sway_freq, time, sway_phase)
    sway = make_math_node(node_tree, "SINE", sway)
    sway = float_multiply(node_tree, sway, sway_amp)
    # There is a wind strength coefficient hardcoded to 0.15.
    # I don't know why we need this to be half the expected value.
    sway = float_multiply(node_tree, sway, 0.15 * 0.5)
    # RBR only sways in X direction, it's hardcoded in the vertex shader.
    sway_displacement_node = new_node(node_tree.nodes, bpy.types.ShaderNodeCombineXYZ)
    node_tree.links.new(socket(sway_displacement_node.inputs, "X"), sway)
    displacement = socket(sway_displacement_node.outputs, "Vector")

    node_tree.links.new(output_surface, output)
    node_tree.links.new(output_displacement, displacement)
    node_tree.links.new(output_color, texture_color)
    node_tree.links.new(output_alpha, alpha)


def make_super_bowl(
    node_tree: bpy.types.NodeTree,
) -> None:
    inputs = group_input(node_tree).outputs
    sockets = SHADER_SB_SOCKETS
    texture_1 = separate_texture(node_tree, socket(inputs, sockets.texture_1()), WHITE)
    texture_2 = separate_texture(node_tree, socket(inputs, sockets.texture_2()), WHITE)
    vcol_in = socket(inputs, sockets.color())
    vcol_alpha = socket(inputs, sockets.alpha_blend())

    output_sockets = group_output(node_tree).inputs
    [output_surface, output_color, *_] = list(output_sockets)

    light_dir = rbr_world_vector(node_tree, "light_direction")
    # Scattering, only for textures
    scattering_coefficients = sky.scattering(
        node_tree=node_tree,
        light_dir=light_dir,
        scale=rbr_world_float(node_tree, "superbowl_scale"),
    )
    vcol = mix_rgb(
        node_tree,
        1.0,
        vcol_in,
        scattering_coefficients.mul_scattering,
        "MULTIPLY",
        True,
    )

    # Texture 2, where connected, is blended over texture 1 by the vertex
    # alpha, and the alpha is texture 1's alone.
    alpha = float_select(
        node_tree,
        texture_2.present,
        float_multiply(node_tree, vcol_alpha, texture_1.alpha, True),
        texture_1.alpha,
    )
    blend = float_multiply(node_tree, vcol_alpha, texture_2.alpha, True)
    texture = rgb_select(
        node_tree,
        texture_2.present,
        texture_1.color,
        mix_rgb(node_tree, blend, texture_1.color, texture_2.color, "MIX", True),
    )
    result = mix_rgb(node_tree, 1.0, vcol, texture, "MULTIPLY", True)
    result = mix_rgb(
        node_tree, 1.0, result, scattering_coefficients.add_scattering, "ADD", True
    )
    result = sky.linear_fog(node_tree, result, is_superbowl=True)

    # Back to linear now we've done all of the (bad) sRGB multiplications.
    linear_result = srgb_to_linear(node_tree, result)
    linear_unlit = srgb_to_linear(node_tree, texture)
    linear_unlit = fixup_unlit(node_tree, linear_unlit)

    # TODO check 0.8 is the correct cutoff
    alpha_clip = binary_math(node_tree, "GREATER_THAN", alpha, 0.8)
    output = make_alpha_shader(node_tree, linear_result, alpha_clip)

    node_tree.links.new(output_surface, output)
    node_tree.links.new(output_color, linear_unlit)


def make_water_object(
    node_tree: bpy.types.NodeTree,
) -> None:
    inputs = group_input(node_tree).outputs
    sockets = SHADER_WO_SOCKETS
    texture_1 = separate_texture(node_tree, socket(inputs, sockets.texture_1()), WHITE)
    texture_2 = separate_texture(node_tree, socket(inputs, sockets.texture_2()), WHITE)
    specular_texture = separate_texture(
        node_tree, socket(inputs, sockets.specular_texture()), BLACK
    ).color
    vcol_in = socket(inputs, sockets.color())
    vcol_alpha = socket(inputs, sockets.alpha_blend())
    specular_strength = socket(inputs, sockets.specular_strength())

    output_sockets = group_output(node_tree).inputs
    [output_surface, output_color, *_] = list(output_sockets)

    light_dir = rbr_world_vector(node_tree, "light_direction")
    # Scattering, only for textures
    scattering_coefficients = sky.scattering(
        node_tree=node_tree,
        light_dir=light_dir,
        scale=1.0,
    )
    vcol = mix_rgb(
        node_tree,
        1.0,
        vcol_in,
        scattering_coefficients.mul_scattering,
        "MULTIPLY",
        True,
    )

    # TODO is this right?
    # Texture 2, where connected, is blended over texture 1 by the vertex
    # alpha, and the alpha is texture 1's alone.
    alpha = float_select(
        node_tree,
        texture_2.present,
        float_multiply(node_tree, vcol_alpha, texture_1.alpha, True),
        texture_1.alpha,
    )
    blend = float_multiply(node_tree, vcol_alpha, texture_2.alpha, True)
    texture = rgb_select(
        node_tree,
        texture_2.present,
        texture_1.color,
        mix_rgb(node_tree, blend, texture_1.color, texture_2.color, "MIX", True),
    )

    beckmann_glossiness = rbr_scene_vector(node_tree, "geom_block_specular_glossiness")
    specular = make_specular(
        node_tree, light_dir, beckmann_glossiness, specular_texture, specular_strength
    )

    result = mix_rgb(node_tree, 1.0, vcol, texture, "MULTIPLY", True)
    # Add all contributions together
    result = mix_rgb(node_tree, 1.0, result, specular, "ADD", True)
    result = mix_rgb(
        node_tree, 1.0, result, scattering_coefficients.add_scattering, "ADD", True
    )
    result = sky.linear_fog(node_tree, result, is_superbowl=False)

    # Back to linear now we've done all of the (bad) sRGB multiplications.
    linear_result = srgb_to_linear(node_tree, result)
    linear_unlit = srgb_to_linear(node_tree, texture)
    linear_unlit = fixup_unlit(node_tree, linear_unlit)

    output = make_alpha_shader(node_tree, linear_result, alpha)

    node_tree.links.new(output_surface, output)
    node_tree.links.new(output_color, linear_unlit)


def make_reflection_object(
    node_tree: bpy.types.NodeTree,
    sockets: ObjectDataSockets = SHADER_RO_SOCKETS,
) -> None:
    inputs = group_input(node_tree).outputs
    texture_1 = separate_texture(node_tree, socket(inputs, sockets.texture_1()), WHITE)
    texture_2 = separate_texture(node_tree, socket(inputs, sockets.texture_2()), WHITE)
    vcol_in = socket(inputs, sockets.color())
    vcol_alpha = socket(inputs, sockets.alpha_blend())

    output_sockets = group_output(node_tree).inputs
    [output_surface, output_color, *_] = list(output_sockets)

    light_dir = rbr_world_vector(node_tree, "light_direction")
    # Scattering, only for textures
    scattering_coefficients = sky.scattering(
        node_tree=node_tree,
        light_dir=light_dir,
        scale=1.0,
    )
    vcol = mix_rgb(
        node_tree,
        1.0,
        vcol_in,
        scattering_coefficients.mul_scattering,
        "MULTIPLY",
        True,
    )

    # TODO is this right?
    # Texture 2, where connected, is blended over texture 1 by the vertex
    # alpha, and the alpha is texture 1's alone.
    alpha = float_select(
        node_tree,
        texture_2.present,
        float_multiply(node_tree, vcol_alpha, texture_1.alpha, True),
        texture_1.alpha,
    )
    blend = float_multiply(node_tree, vcol_alpha, texture_2.alpha, True)
    texture = rgb_select(
        node_tree,
        texture_2.present,
        texture_1.color,
        mix_rgb(node_tree, blend, texture_1.color, texture_2.color, "MIX", True),
    )

    result = mix_rgb(node_tree, 1.0, vcol, texture, "MULTIPLY", True)
    result = mix_rgb(
        node_tree, 1.0, result, scattering_coefficients.add_scattering, "ADD", True
    )
    result = sky.linear_fog(node_tree, result, is_superbowl=False)

    # Back to linear now we've done all of the (bad) sRGB multiplications.
    linear_result = srgb_to_linear(node_tree, result)
    linear_unlit = srgb_to_linear(node_tree, texture)
    linear_unlit = fixup_unlit(node_tree, linear_unlit)

    output = make_alpha_shader(node_tree, linear_result, alpha)

    node_tree.links.new(output_surface, output)
    node_tree.links.new(output_color, linear_unlit)


def make_interactive_object(
    node_tree: bpy.types.NodeTree,
) -> None:
    inputs = group_input(node_tree).outputs
    sockets = SHADER_IO_SOCKETS
    texture_1 = separate_texture(node_tree, socket(inputs, sockets.texture_1()), WHITE)
    texture_2 = separate_texture(node_tree, socket(inputs, sockets.texture_2()), WHITE)
    vcol_in = socket(inputs, sockets.color())
    vcol_alpha = socket(inputs, sockets.alpha_blend())

    output_sockets = group_output(node_tree).inputs
    [output_surface, output_color, *_] = list(output_sockets)

    light_dir = rbr_world_vector(node_tree, "light_direction")
    # Scattering, only for textures
    scattering_coefficients = sky.scattering(
        node_tree=node_tree,
        light_dir=light_dir,
        scale=1.0,
    )
    vcol = mix_rgb(
        node_tree,
        1.0,
        vcol_in,
        scattering_coefficients.mul_scattering,
        "MULTIPLY",
        True,
    )

    # Texture 2, where connected, is blended over texture 1 by the vertex
    # alpha, and the alpha is texture 1's alone.
    alpha = float_select(
        node_tree,
        texture_2.present,
        float_multiply(node_tree, vcol_alpha, texture_1.alpha, True),
        texture_1.alpha,
    )
    blend = float_multiply(node_tree, vcol_alpha, texture_2.alpha, True)
    texture = rgb_select(
        node_tree,
        texture_2.present,
        texture_1.color,
        mix_rgb(node_tree, blend, texture_1.color, texture_2.color, "MIX", True),
    )
    result = mix_rgb(node_tree, 1.0, vcol, texture, "MULTIPLY", True)
    result = mix_rgb(
        node_tree, 1.0, result, scattering_coefficients.add_scattering, "ADD", True
    )
    result = sky.linear_fog(node_tree, result, is_superbowl=False)

    # Back to linear now we've done all of the (bad) sRGB multiplications.
    linear_result = srgb_to_linear(node_tree, result)
    linear_unlit = srgb_to_linear(node_tree, texture)
    linear_unlit = fixup_unlit(node_tree, linear_unlit)

    # TODO check 0.8 is the correct cutoff
    alpha_clip = binary_math(node_tree, "GREATER_THAN", alpha, 0.8)
    output = make_alpha_shader(node_tree, linear_result, alpha_clip)

    node_tree.links.new(output_surface, output)
    node_tree.links.new(output_color, linear_unlit)


def make_clipping_plane(
    node_tree: bpy.types.NodeTree,
) -> None:
    input_sockets = group_input(node_tree).outputs
    [backface_cull, *_] = list(input_sockets)

    output_sockets = group_output(node_tree).inputs
    [output_surface, *_] = list(output_sockets)

    geometry = new_node(node_tree.nodes, bpy.types.ShaderNodeNewGeometry)
    backfacing = socket(geometry.outputs, "Backfacing")
    fac = float_multiply(node_tree, backfacing, backface_cull)
    fac = float_subtract(node_tree, 1, fac)
    node = new_node(node_tree.nodes, bpy.types.ShaderNodeBsdfDiffuse)
    result = make_alpha_shader(node_tree, socket(node.outputs, "BSDF"), fac)
    node_tree.links.new(output_surface, result)


def clip(
    node_tree: bpy.types.NodeTree,
    in_socket: Union[float, bpy.types.NodeSocket],
) -> bpy.types.NodeSocket:
    return binary_math(node_tree, "LESS_THAN", 0.8, in_socket)


def make_specular(
    node_tree: bpy.types.NodeTree,
    # vector pointing _towards_ the sun
    light_dir: bpy.types.NodeSocketVector,
    beckmann_glossiness: bpy.types.NodeSocket,
    specular_texture: bpy.types.NodeSocket,
    specular_strength: bpy.types.NodeSocket,
) -> bpy.types.NodeSocketFloat:
    # This implements SpecularVSFragment.hlsl and the use of it in
    # RLDoubleTextureSpecular.hlsl
    geometry = new_node(node_tree.nodes, bpy.types.ShaderNodeNewGeometry)
    # verified to match RBR
    view_vector = socket(geometry.outputs, "Incoming")
    # verified to match RBR
    normal = socket(geometry.outputs, "Normal")

    add_half = new_node(node_tree.nodes, bpy.types.ShaderNodeVectorMath)
    add_half.operation = "ADD"
    node_tree.links.new(socket(add_half.inputs, "Vector", 0), light_dir)
    node_tree.links.new(socket(add_half.inputs, "Vector", 1), view_vector)

    halfway_vector = new_node(node_tree.nodes, bpy.types.ShaderNodeVectorMath)
    halfway_vector.operation = "NORMALIZE"
    node_tree.links.new(
        socket(halfway_vector.inputs, "Vector", 0), socket(add_half.outputs, "Vector")
    )

    dot = new_node(node_tree.nodes, bpy.types.ShaderNodeVectorMath)
    dot.operation = "DOT_PRODUCT"
    node_tree.links.new(socket(dot.inputs, "Vector", 0), normal)
    node_tree.links.new(
        socket(dot.inputs, "Vector", 1), socket(halfway_vector.outputs, "Vector")
    )

    divide_dot = float_divide(node_tree, 1.0, socket(dot.outputs, "Value"))
    r1 = float_multiply(node_tree, divide_dot, divide_dot)
    subtract_beckmann = float_subtract(node_tree, 1.0, r1)
    beckmann_alpha = rbr_world_float(node_tree, "specular_alpha")
    mul_gloss = float_multiply(node_tree, subtract_beckmann, beckmann_glossiness)
    gloss_pow = float_pow(node_tree, 2.0, mul_gloss)
    gloss_pow_2 = float_multiply(node_tree, gloss_pow, r1)
    gloss_pow_3 = float_multiply(node_tree, gloss_pow_2, r1)
    mul_alpha = float_multiply(node_tree, gloss_pow_3, beckmann_alpha)
    mul_strength = float_multiply(node_tree, mul_alpha, specular_strength)
    mul_strength_4 = float_multiply(node_tree, mul_strength, 4.0)
    return narrow(
        float_multiply(node_tree, specular_texture, mul_strength_4),
        bpy.types.NodeSocketFloat,
    )


def make_alpha_shader(
    node_tree: bpy.types.NodeTree,
    color: bpy.types.NodeSocket,
    alpha: bpy.types.NodeSocket,
) -> bpy.types.NodeSocket:
    mix = new_node(node_tree.nodes, bpy.types.ShaderNodeMixShader)
    transparent = new_node(node_tree.nodes, bpy.types.ShaderNodeBsdfTransparent)
    # We must clamp the alpha to slightly greater than 0, or blender will
    # display the colour as black.
    alpha_clamp = float_max(node_tree, alpha, 0.000001)
    node_tree.links.new(socket(mix.inputs, "Factor"), alpha_clamp)
    node_tree.links.new(
        socket(mix.inputs, "Shader", 0), socket(transparent.outputs, "BSDF")
    )
    node_tree.links.new(socket(mix.inputs, "Shader", 1), color)
    return socket(mix.outputs, "Shader")


def mesh_type_to_shader_name(mesh_type: RBRMeshMaterialType) -> str:
    return SHADER_PREFIX + mesh_type.name.title().replace("_", "")


def use_rbr_shader_node_tree(mesh_type: RBRMeshMaterialType) -> bpy.types.NodeTree:
    name = mesh_type_to_shader_name(mesh_type)
    node_tree = local_node_group(name)
    if node_tree is None:
        node_tree = create_rbr_shader_node_tree(mesh_type)
    return node_tree


def recreate_internals(context: bpy.types.Context) -> None:
    # Update the _trees_
    for node_tree in bpy.data.node_groups:
        if node_tree.library is not None or not node_tree.name.startswith(
            SHADER_PREFIX
        ):
            continue
        for mesh_type in RBRMeshMaterialType:
            # Deal with matches
            if node_tree.name == mesh_type_to_shader_name(mesh_type):
                break
            # Deal with duplicates (due to libraries) with names like
            # .ShaderNodeRBR.DoubleTexture.001
            if node_tree.name.startswith(mesh_type_to_shader_name(mesh_type) + "."):
                break
        else:
            continue
        node_tree.links.clear()
        # The group input and output go too: their sockets would otherwise
        # lag behind the rebuilt interface.
        node_tree.nodes.clear()
        node_tree.interface.clear()
        create_sockets(node_tree.interface, mesh_type)
        new_node(node_tree.nodes, bpy.types.NodeGroupInput)
        new_node(node_tree.nodes, bpy.types.NodeGroupOutput)

        create_shader(
            node_tree=node_tree,
            mesh_type=mesh_type,
        )

    # Update the _nodes_ (to reset color/alpha default values)
    for mat in bpy.data.materials:
        if not mat.use_nodes:
            continue
        if mat.node_tree is None:
            continue
        for node in mat.node_tree.nodes:
            if not isinstance(node, ShaderNodeRBR):
                continue
            node.select_node_tree(context)


def create_rbr_shader_node_tree(mesh_type: RBRMeshMaterialType) -> bpy.types.NodeTree:
    node_tree = bpy.data.node_groups.new(
        mesh_type_to_shader_name(mesh_type),
        "ShaderNodeTree",
    )
    new_node(node_tree.nodes, bpy.types.NodeGroupInput)
    new_node(node_tree.nodes, bpy.types.NodeGroupOutput)
    create_sockets(node_tree.interface, mesh_type)

    create_shader(
        node_tree=node_tree,
        mesh_type=mesh_type,
    )
    return node_tree


def create_sockets(
    interface: bpy.types.NodeTreeInterface,
    mesh_type: RBRMeshMaterialType,
) -> None:
    def input_vcol(
        name: str,
        node_type: str,
        parent: Optional[bpy.types.NodeTreeInterfacePanel] = None,
        min: Optional[Any] = None,
        max: Optional[Any] = None,
    ) -> bpy.types.NodeTreeInterfaceSocket:
        socket = interface.new_socket(
            name,
            in_out="INPUT",
            socket_type="NodeSocket" + node_type,
            parent=parent,
        )
        if min is not None:
            socket.min_value = min
        if max is not None:
            socket.max_value = max
        return socket

    def input_tex(
        name: str,
        node_type: str,
        parent: Optional[bpy.types.NodeTreeInterfacePanel] = None,
    ) -> bpy.types.NodeTreeInterfaceSocket:
        socket = input_vcol(name, node_type, parent)
        socket.hide_value = True
        return socket

    def add_output_socket(
        name: str,
        node_type: str,
        min: Optional[float] = None,
        max: Optional[float] = None,
    ) -> None:
        socket = interface.new_socket(name, in_out="OUTPUT", socket_type=node_type)
        if min is not None:
            socket.min_value = min
        if max is not None:
            socket.max_value = max

    od_sockets = None
    if mesh_type is RBRMeshMaterialType.GEOM_BLOCK:
        textures = interface.new_panel("Textures")
        input_tex(SHADER_GB_TEXTURE_1, "Bundle", textures)
        input_tex(SHADER_GB_TEXTURE_2, "Bundle", textures)
        input_tex(SHADER_GB_SPECULAR_TEXTURE, "Bundle", textures)
        input_tex(SHADER_GB_SHADOW_TEXTURE, "Color", textures)
        vertex_data = interface.new_panel("Vertex Data")
        input_vcol(SHADER_GB_COLOR, "Color", vertex_data)
        input_vcol(SHADER_GB_BLEND, "Float", vertex_data, 0, 1)
        input_vcol(SHADER_GB_SPECULAR_STRENGTH, "Float", vertex_data, 0, 1)
        collision_shading = input_vcol(
            SHADER_GB_COLLISION_SHADING, "Float", vertex_data, 0, 1
        )
        collision_shading.default_value = 0.5
        add_output_socket(SHADER_GB_OUTPUT_SURFACE, "NodeSocketShader")
        add_output_socket(SHADER_GB_OUTPUT_COLOR, "NodeSocketColor")
    elif mesh_type is RBRMeshMaterialType.OBJECT_BLOCK:
        textures = interface.new_panel("Textures")
        input_tex(SHADER_OB_TEXTURE_1, "Bundle", textures)
        vertex_data = interface.new_panel("Vertex Data")
        input_vcol(SHADER_OB_COLOR, "Color", vertex_data)
        input_vcol(SHADER_OB_ALPHA, "Float", vertex_data, 0, 1)
        vertex_sway = interface.new_panel("Vertex Sway")
        input_vcol(SHADER_OB_SWAY_FREQ, "Float", vertex_sway, -math.inf, math.inf)
        input_vcol(SHADER_OB_SWAY_AMP, "Float", vertex_sway, -math.inf, math.inf)
        input_vcol(SHADER_OB_SWAY_PHASE, "Float", vertex_sway, -math.inf, math.inf)
        add_output_socket(SHADER_OB_OUTPUT_SURFACE, "NodeSocketShader")
        add_output_socket(SHADER_OB_OUTPUT_DISPLACEMENT, "NodeSocketVector")
        add_output_socket(SHADER_OB_OUTPUT_COLOR, "NodeSocketColor")
        add_output_socket(SHADER_OB_OUTPUT_ALPHA, "NodeSocketFloat")
    elif mesh_type is RBRMeshMaterialType.REFLECTION_OBJECT:
        od_sockets = SHADER_RO_SOCKETS
    elif mesh_type is RBRMeshMaterialType.WATER_OBJECT:
        od_sockets = SHADER_WO_SOCKETS
    elif mesh_type is RBRMeshMaterialType.SUPER_BOWL:
        od_sockets = SHADER_SB_SOCKETS
    elif mesh_type is RBRMeshMaterialType.INTERACTIVE_OBJECT_VISUAL:
        od_sockets = SHADER_IO_SOCKETS
    elif mesh_type is RBRMeshMaterialType.CLIPPING_PLANE:
        interface.new_socket(
            SHADER_CP_BACKFACE_CULL,
            in_out="INPUT",
            socket_type="NodeSocketBool",
        )
        add_output_socket(SHADER_CP_OUTPUT_SURFACE, "NodeSocketShader")
    else:
        raise NotImplementedError("Missing RBRMeshMaterialType case for create_sockets")

    if od_sockets is not None:
        textures = interface.new_panel("Textures")
        input_tex(od_sockets.texture_1(), "Bundle", textures)
        input_tex(od_sockets.texture_2(), "Bundle", textures)
        if od_sockets.has_specular:
            input_tex(od_sockets.specular_texture(), "Bundle", textures)
        vertex_data = interface.new_panel("Vertex Data")
        input_vcol(od_sockets.color(), "Color", vertex_data)
        input_vcol(od_sockets.alpha_blend(), "Float", vertex_data, 0, 1)
        if od_sockets.has_specular:
            input_vcol(od_sockets.specular_strength(), "Float", vertex_data, 0, 1)
        add_output_socket(od_sockets.output_surface(), "NodeSocketShader")
        add_output_socket(od_sockets.output_color(), "NodeSocketColor")


def create_shader(
    node_tree: bpy.types.NodeTree,
    mesh_type: RBRMeshMaterialType,
) -> None:
    if mesh_type is RBRMeshMaterialType.CLIPPING_PLANE:
        make_clipping_plane(node_tree)
    elif mesh_type is RBRMeshMaterialType.GEOM_BLOCK:
        make_geom_block(node_tree)
    elif mesh_type is RBRMeshMaterialType.OBJECT_BLOCK:
        make_object_block(node_tree)
    elif mesh_type is RBRMeshMaterialType.SUPER_BOWL:
        make_super_bowl(node_tree)
    elif mesh_type is RBRMeshMaterialType.WATER_OBJECT:
        make_water_object(node_tree)
    elif mesh_type is RBRMeshMaterialType.REFLECTION_OBJECT:
        make_reflection_object(node_tree)
    elif mesh_type is RBRMeshMaterialType.INTERACTIVE_OBJECT_VISUAL:
        make_reflection_object(node_tree, SHADER_IO_SOCKETS)
    else:
        print("not implemented!", mesh_type.name)


def input_defaults(mesh_type: RBRMeshMaterialType) -> Dict[str, Any]:
    """The defaults of an RBR shader's value inputs; texture inputs take
    theirs from separate_texture."""
    if mesh_type is RBRMeshMaterialType.GEOM_BLOCK:
        return {
            SHADER_GB_SHADOW_TEXTURE: WHITE,
            SHADER_GB_COLOR: WHITE,
            SHADER_GB_BLEND: 1,
            SHADER_GB_SPECULAR_STRENGTH: 1,
            SHADER_GB_COLLISION_SHADING: 0.5,
        }
    if mesh_type is RBRMeshMaterialType.OBJECT_BLOCK:
        return {
            SHADER_OB_COLOR: WHITE,
            SHADER_OB_ALPHA: 1,
            SHADER_OB_SWAY_FREQ: 1,
            SHADER_OB_SWAY_AMP: 0,
            SHADER_OB_SWAY_PHASE: 0,
        }
    sockets = {
        RBRMeshMaterialType.SUPER_BOWL: SHADER_SB_SOCKETS,
        RBRMeshMaterialType.WATER_OBJECT: SHADER_WO_SOCKETS,
        RBRMeshMaterialType.REFLECTION_OBJECT: SHADER_RO_SOCKETS,
        RBRMeshMaterialType.INTERACTIVE_OBJECT_VISUAL: SHADER_IO_SOCKETS,
    }.get(mesh_type)
    if sockets is None:
        return {}
    defaults: Dict[str, Any] = {sockets.color(): WHITE, sockets.alpha_blend(): 1}
    if sockets.has_specular:
        defaults[sockets.specular_strength()] = 1
    return defaults


class ShaderNodeRBR(bpy.types.ShaderNodeCustomGroup):
    bl_name = "ShaderNodeRBR"
    bl_label = "RBR Shader"
    node_tree: Optional[bpy.types.ShaderNodeTree] = None

    def select_node_tree(self, context: bpy.types.Context) -> None:
        mesh_type = RBRMeshMaterialType[self.mesh_type]
        self.node_tree = narrow(
            use_rbr_shader_node_tree(mesh_type), bpy.types.ShaderNodeTree
        )
        for name, value in input_defaults(mesh_type).items():
            input = self.inputs.get(name)
            if input is not None:
                input.default_value = value
        self.update_collision_shading_socket(context)

    mesh_type: bpy.props.EnumProperty(  # type: ignore
        items=[
            (t.name, t.pretty(), t.description(), t.value) for t in RBRMeshMaterialType
        ],
        name="Type",  # noqa: F821
        default=RBRMeshMaterialType.GEOM_BLOCK.name,
        update=select_node_tree,
    )
    geom_block_type: bpy.props.EnumProperty(  # type: ignore
        items=[(t.name, t.pretty(), t.description(), t.value) for t in GeomBlockType],
        name="Geom Block Type",  # noqa: F821
        default=GeomBlockType.NEAR.name,
    )
    is_geom_block_collision: bpy.props.BoolProperty(  # type: ignore
        name="Generate Collision Mesh",
        description="Generate a static (ground) collision mesh for this mesh",
        update=lambda self, context: self.update_collision_shading_socket(context),
    )
    is_geom_block_invisible: bpy.props.BoolProperty(  # type: ignore
        name="Collision Mesh Only",
        description="Don't export the visual geometry",
    )
    object_block_type: bpy.props.EnumProperty(  # type: ignore
        items=[(t.name, t.pretty(), t.description(), t.value) for t in ObjectBlockType],
        name="Object Block Type",  # noqa: F821
        default=ObjectBlockType.BOTH.name,
    )

    def update_collision_shading_socket(
        self, context: Optional[bpy.types.Context]
    ) -> None:
        if self.mesh_type != RBRMeshMaterialType.GEOM_BLOCK.name:
            return
        shading = self.inputs.get(SHADER_GB_COLLISION_SHADING)
        if shading is not None:
            shading.hide = not self.is_geom_block_collision

    def init(self, context: Optional[bpy.types.Context]) -> None:
        # context appears to be 'None' here, not sure why
        self.width = 200
        self.select_node_tree(bpy.context)

    def draw_buttons(
        self, context: bpy.types.Context, layout: bpy.types.UILayout
    ) -> None:
        layout.use_property_decorate = False  # No animation stuff

        layout.prop(self, "mesh_type")
        if self.mesh_type == RBRMeshMaterialType.GEOM_BLOCK.name:
            layout.prop(self, "geom_block_type", expand=True)
            if self.geom_block_type == GeomBlockType.NEAR.name:
                layout.prop(self, "is_geom_block_collision")
                if self.is_geom_block_collision:
                    layout.prop(self, "is_geom_block_invisible")
        elif self.mesh_type == RBRMeshMaterialType.OBJECT_BLOCK.name:
            layout.prop(self, "object_block_type", expand=True)

    def copy(self, node: bpy.types.Node) -> None:
        pass

    def free(self) -> None:
        pass


def material_name(
    texture_1: Optional[bpy.types.NodeTree],
    texture_2: Optional[bpy.types.NodeTree],
    specular: Optional[bpy.types.NodeTree],
) -> str:
    def get_name(tree: Optional[bpy.types.NodeTree]) -> str:
        if tree is None:
            return ""
        name = tree_name_to_texture_name(tree)
        if name is None:
            return ""
        return name

    texture_1_name = get_name(texture_1)
    texture_2_name = get_name(texture_2)
    specular_name = get_name(specular)
    parts = [texture_1_name, texture_2_name, specular_name]
    return "_".join(filter(lambda x: x != "", parts))


def create_texture_and_uv(
    node_tree: bpy.types.NodeTree,
    tex_tree: bpy.types.ShaderNodeTree,
    uv_layer: str,
    texture_input: bpy.types.NodeSocket,
    uv_velocity: List[float],  # FloatVectorProperty
) -> None:
    tex_node = narrow(node_tree.nodes.new("ShaderNodeRBRTexture"), ShaderNodeRBRTexture)
    tex_node.node_tree = tex_tree
    node_tree.links.new(socket(tex_node.outputs, RBR_TEXTURE_OUTPUT), texture_input)
    uv_node = new_node(node_tree.nodes, bpy.types.ShaderNodeUVMap)
    uv_node.uv_map = uv_layer
    if uv_velocity[0] == 0 and uv_velocity[1] == 0:
        node_tree.links.new(
            socket(tex_node.inputs, "UV"),
            socket(uv_node.outputs, "UV"),
        )
    else:
        uv_velocity_node = node_tree.nodes.new("ShaderNodeUVVelocity")
        socket(uv_velocity_node.inputs, "UV Velocity").default_value = [
            uv_velocity[0],
            uv_velocity[1],
            0,
        ]
        node_tree.links.new(
            socket(uv_velocity_node.inputs, "UV"),
            socket(uv_node.outputs, "UV"),
        )
        node_tree.links.new(
            socket(tex_node.inputs, "UV"),
            socket(uv_velocity_node.outputs, "UV"),
        )


def register() -> None:
    bpy.utils.register_class(ShaderNodeRBR)


def unregister() -> None:
    bpy.utils.unregister_class(ShaderNodeRBR)
