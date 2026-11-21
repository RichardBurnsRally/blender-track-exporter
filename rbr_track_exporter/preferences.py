import enum
from typing import Optional, Set, Tuple, assert_never

import bpy
from .types import OperatorReturn
from .blender_utils import narrow

assert __package__ is not None
PACKAGE: str = __package__


class Language(enum.Enum):
    EN = enum.auto()

    def pretty(self) -> str:
        if self is Language.EN:
            return "English"
        assert_never(self)


class RBRExportDirectory(bpy.types.PropertyGroup):
    name: bpy.props.StringProperty(  # type: ignore
        name="Name",  # noqa: F821
    )
    directory: bpy.props.StringProperty(  # type: ignore
        name="RBR Maps Directory",  # noqa: F821
        subtype="DIR_PATH",  # noqa: F821
    )


class RBR_OT_add_export_directory(bpy.types.Operator):
    bl_idname = "rbr.add_export_directory"
    bl_label = "Add RBR export directory"
    bl_options = {"REGISTER", "UNDO"}

    def invoke(
        self, context: bpy.types.Context, event: bpy.types.Event
    ) -> OperatorReturn:
        if context.preferences is None:
            return {"CANCELLED"}
        prefs = narrow(
            context.preferences.addons[__package__].preferences, RBRAddonPreferences
        )
        prefs.export_directories.add()
        return {"FINISHED"}


class RBR_OT_remove_export_directory(bpy.types.Operator):
    bl_idname = "rbr.remove_export_directory"
    bl_label = "Remove RBR export directory"
    bl_options = {"REGISTER", "UNDO"}

    index: bpy.props.IntProperty()  # type: ignore

    def invoke(
        self, context: bpy.types.Context, event: bpy.types.Event
    ) -> OperatorReturn:
        if context.preferences is None:
            return {"CANCELLED"}
        prefs = narrow(
            context.preferences.addons[__package__].preferences, RBRAddonPreferences
        )
        prefs.export_directories.remove(self.index)
        return {"FINISHED"}


class RBRAddonPreferences(bpy.types.AddonPreferences):
    bl_idname = PACKAGE

    export_directories: bpy.props.CollectionProperty(  # type: ignore
        type=RBRExportDirectory,
    )

    def get_export_directory(self, name: str) -> Optional[str]:
        for export_directory in self.export_directories:
            if export_directory.name == name:
                directory: str = export_directory.directory
                return directory
        return None

    language: bpy.props.EnumProperty(  # type: ignore
        name="Language",
        items=[(x.name, x.pretty(), x.pretty(), x.value) for x in Language],
        default=Language.EN.name,
    )

    def get_language(self) -> Language:
        return Language[self.language]

    def draw(self, context: bpy.types.Context) -> None:
        self.layout.prop(self, "language")
        box = self.layout.box()
        box.operator(RBR_OT_add_export_directory.bl_idname)
        for i, export_directory in enumerate(self.export_directories):
            row = box.row()
            row.prop(export_directory, "name", text="")
            row.prop(export_directory, "directory", text="")
            remove = row.operator(
                RBR_OT_remove_export_directory.bl_idname, text="", icon="REMOVE"
            )
            remove.index = i


def register() -> None:
    bpy.utils.register_class(RBR_OT_remove_export_directory)
    bpy.utils.register_class(RBR_OT_add_export_directory)
    bpy.utils.register_class(RBRExportDirectory)
    bpy.utils.register_class(RBRAddonPreferences)


def unregister() -> None:
    bpy.utils.unregister_class(RBRAddonPreferences)
    bpy.utils.unregister_class(RBRExportDirectory)
    bpy.utils.unregister_class(RBR_OT_add_export_directory)
    bpy.utils.unregister_class(RBR_OT_remove_export_directory)
