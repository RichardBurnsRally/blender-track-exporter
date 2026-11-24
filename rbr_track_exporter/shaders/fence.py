import bpy
from ..blender_utils import narrow, new_node, socket

from typing import Optional, Tuple

from .shader_node import ShaderNodeRBR
from .texture import (
    TEXTURE_BUNDLE_ALPHA,
    TEXTURE_BUNDLE_COLOR,
    TEXTURE_BUNDLE_PRESENT,
)
from ..types import RBRMeshMaterialType


def setup_fence_material_node_tree(
    node_tree: bpy.types.ShaderNodeTree,
    image: bpy.types.Image,
    stripe: Optional[Tuple[float, float, float, float]] = None,
) -> None:
    for node in node_tree.nodes:
        node_tree.nodes.remove(node)

    # initialize node_tree nodes
    # node Attribute
    attribute = new_node(node_tree.nodes, bpy.types.ShaderNodeAttribute)
    attribute.name = "Attribute"
    attribute.attribute_name = ".rbr.uv"
    attribute.attribute_type = "GEOMETRY"

    # node Image Texture
    image_texture = new_node(node_tree.nodes, bpy.types.ShaderNodeTexImage)
    image_texture.name = "Image Texture"
    image_texture.image = image
    image_texture.extension = "REPEAT"
    image_texture.image_user.frame_current = 0
    image_texture.image_user.frame_duration = 100
    image_texture.image_user.frame_offset = 0
    image_texture.image_user.frame_start = 1
    image_texture.image_user.tile = 0
    image_texture.image_user.use_auto_refresh = False
    image_texture.image_user.use_cyclic = False
    image_texture.interpolation = "Closest"
    image_texture.projection = "FLAT"
    image_texture.projection_blend = 0.0

    # node Material Output
    material_output = new_node(node_tree.nodes, bpy.types.ShaderNodeOutputMaterial)
    material_output.name = "Material Output"
    material_output.is_active_output = True
    material_output.target = "ALL"
    # Displacement
    socket(material_output.inputs, "Displacement").default_value = (0.0, 0.0, 0.0)
    # Thickness
    socket(material_output.inputs, "Thickness").default_value = 0.0

    # node Attribute.001
    attribute_001 = new_node(node_tree.nodes, bpy.types.ShaderNodeAttribute)
    attribute_001.name = "Attribute.001"
    attribute_001.attribute_name = ".rbr.color"
    attribute_001.attribute_type = "GEOMETRY"

    # node RBR Shader
    rbr_shader = narrow(node_tree.nodes.new("ShaderNodeRBR"), ShaderNodeRBR)
    rbr_shader.name = "RBR Shader"
    rbr_shader.mesh_type = RBRMeshMaterialType.INTERACTIVE_OBJECT_VISUAL.name
    # Socket_7
    socket(rbr_shader.inputs, "Blend").default_value = 1.0

    # node Gamma
    gamma = new_node(node_tree.nodes, bpy.types.ShaderNodeGamma)
    gamma.name = "Gamma"
    # Gamma
    socket(gamma.inputs, "Gamma").default_value = 0.4545454680919647

    # Set locations
    attribute.location = (-281.02752685546875, 376.70428466796875)
    image_texture.location = (-92.5113296508789, 576.4358520507812)
    material_output.location = (619.6921997070312, 632.3812255859375)
    attribute_001.location = (190.73666381835938, 395.78472900390625)
    rbr_shader.location = (374.845947265625, 607.8880615234375)
    gamma.location = (194.23373413085938, 635.8613891601562)

    # Set dimensions
    attribute.width, attribute.height = 140.0, 100.0
    image_texture.width, image_texture.height = 240.0, 100.0
    material_output.width, material_output.height = 140.0, 100.0
    attribute_001.width, attribute_001.height = 140.0, 100.0
    rbr_shader.width, rbr_shader.height = 200.0, 100.0
    gamma.width, gamma.height = 140.0, 100.0

    # initialize node_tree links
    if stripe is None:
        node_tree.links.new(
            socket(attribute.outputs, "Vector"), socket(image_texture.inputs, "Vector")
        )
    else:
        u0, u1, v0, v1 = stripe
        mapping = new_node(node_tree.nodes, bpy.types.ShaderNodeMapping)
        mapping.name = "Mapping"
        mapping.location = (-281.0, 576.0)
        socket(mapping.inputs, "Location").default_value = (u0, v0, 0.0)
        socket(mapping.inputs, "Scale").default_value = (u1 - u0, v1 - v0, 1.0)
        node_tree.links.new(
            socket(attribute.outputs, "Vector"), socket(mapping.inputs, "Vector")
        )
        node_tree.links.new(
            socket(mapping.outputs, "Vector"), socket(image_texture.inputs, "Vector")
        )
    # gamma.Color, image_texture.Alpha -> texture bundle -> rbr_shader.Texture 1
    bundle = new_node(node_tree.nodes, bpy.types.NodeCombineBundle)
    bundle.location = (374.0, 800.0)
    bundle.bundle_items.new("RGBA", TEXTURE_BUNDLE_COLOR)
    bundle.bundle_items.new("FLOAT", TEXTURE_BUNDLE_ALPHA)
    bundle.bundle_items.new("FLOAT", TEXTURE_BUNDLE_PRESENT)
    socket(bundle.inputs, TEXTURE_BUNDLE_PRESENT).default_value = 1.0
    node_tree.links.new(
        socket(gamma.outputs, "Color"), socket(bundle.inputs, TEXTURE_BUNDLE_COLOR)
    )
    node_tree.links.new(
        socket(image_texture.outputs, "Alpha"),
        socket(bundle.inputs, TEXTURE_BUNDLE_ALPHA),
    )
    node_tree.links.new(
        socket(bundle.outputs, "Bundle"), socket(rbr_shader.inputs, "Texture 1")
    )
    # attribute_001.Color -> rbr_shader.Color
    node_tree.links.new(
        socket(attribute_001.outputs, "Color"), socket(rbr_shader.inputs, "Color")
    )
    # image_texture.Color -> gamma.Color
    node_tree.links.new(
        socket(image_texture.outputs, "Color"), socket(gamma.inputs, "Color")
    )
    # rbr_shader.Surface -> material_output.Surface
    node_tree.links.new(
        socket(rbr_shader.outputs, "Surface"), socket(material_output.inputs, "Surface")
    )
