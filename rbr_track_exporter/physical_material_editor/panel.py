import bpy

from ..physical_material_editor.properties import RBRMaterialPicker
from ..physical_material_editor.operator import RBR_OT_edit_material_maps


class RBR_PT_material_picker_panel(bpy.types.Panel):
    bl_idname = "RBR_PT_material_picker_panel"
    bl_label = "RBR Material Picker"
    bl_category = "Tool"
    bl_space_type = "IMAGE_EDITOR"
    bl_region_type = "UI"

    material_picker: bpy.props.PointerProperty(  # type: ignore
        type=RBRMaterialPicker,
    )

    @classmethod
    def poll(cls, context: bpy.types.Context) -> bool:
        return RBR_OT_edit_material_maps.handle is not None

    def draw(self, context: bpy.types.Context) -> None:
        operator = RBR_OT_edit_material_maps.active_operator
        if operator is None:
            return
        picker: RBRMaterialPicker = operator.material_picker
        ui = self.layout
        ui.label(text="Material Map Transparency")
        ui.prop(picker, "alpha", slider=True)
        ui.label(text="Material Palette")
        picker.draw(context, ui)


def register() -> None:
    bpy.utils.register_class(RBR_PT_material_picker_panel)


def unregister() -> None:
    bpy.utils.unregister_class(RBR_PT_material_picker_panel)
