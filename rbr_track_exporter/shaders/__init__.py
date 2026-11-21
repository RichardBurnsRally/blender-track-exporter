from typing import Dict

import bpy

from . import tint_set
from . import uv_velocity
from . import shader_node
from . import sky
from . import texture
from . import utils  # noqa: F401


def add_node_type(
    layout: bpy.types.UILayout, node_type: str
) -> bpy.types.OperatorProperties:
    """Add a node type to a menu."""
    bl_rna = bpy.types.Node.bl_rna_get_subclass(node_type)
    label = bl_rna.name
    translation_context = bl_rna.translation_context
    props = layout.operator("node.add_node", text=label, text_ctxt=translation_context)
    props.type = node_type
    props.use_transform = True
    return props


class NODE_MT_category_RBR_SHADER(bpy.types.Menu):
    bl_idname = "NODE_MT_category_RBR_SHADER"
    bl_label = "RBR Nodes"

    def draw(self, context: bpy.types.Context) -> None:
        add_node_type(self.layout, shader_node.ShaderNodeRBR.bl_name)
        add_node_type(self.layout, texture.ShaderNodeRBRTexture.bl_name)
        add_node_type(self.layout, tint_set.ShaderNodeRBRTintSet.bl_name)
        add_node_type(self.layout, uv_velocity.ShaderNodeUVVelocity.bl_name)
        add_node_type(self.layout, sky.ShaderNodeRBRSky.bl_name)


def draw_rbr_shader_menu(self: bpy.types.Menu, context: bpy.types.Context) -> None:
    self.layout.menu(NODE_MT_category_RBR_SHADER.bl_idname)


def register() -> None:
    tint_set.register()
    uv_velocity.register()
    texture.register()
    shader_node.register()
    sky.register()
    bpy.utils.register_class(NODE_MT_category_RBR_SHADER)
    bpy.types.NODE_MT_shader_node_add_all.append(draw_rbr_shader_menu)


def unregister() -> None:
    bpy.types.NODE_MT_shader_node_add_all.remove(draw_rbr_shader_menu)
    bpy.utils.unregister_class(NODE_MT_category_RBR_SHADER)
    sky.unregister()
    shader_node.unregister()
    texture.unregister()
    uv_velocity.unregister()
    tint_set.unregister()
