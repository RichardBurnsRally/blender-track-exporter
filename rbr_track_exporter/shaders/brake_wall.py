import bpy
from ..blender_utils import new_node, socket

from .utils import mix_rgb


def setup_brake_wall_tree(
    node_tree: bpy.types.ShaderNodeTree,
) -> None:
    node_tree.nodes.clear()

    attribute = new_node(node_tree.nodes, bpy.types.ShaderNodeAttribute)
    attribute.attribute_name = "respawn"
    attribute.attribute_type = "GEOMETRY"

    output = mix_rgb(
        node_tree,
        socket(attribute.outputs, "Factor"),
        [1, 1, 1, 1],
        [1, 0, 0, 1],
    )

    bsdf = new_node(node_tree.nodes, bpy.types.ShaderNodeBsdfPrincipled)
    socket(bsdf.inputs, "Alpha").default_value = 0.5
    node_tree.links.new(output, socket(bsdf.inputs, "Base Color"))

    material_output = new_node(node_tree.nodes, bpy.types.ShaderNodeOutputMaterial)

    node_tree.links.new(
        socket(bsdf.outputs, "BSDF"), socket(material_output.inputs, "Surface")
    )
