import bpy

from ..types import OperatorReturn
from . import legacy, optional

PENDING_PROP = "rbr_legacy_optional"


class RBR_OT_migrate_legacy(bpy.types.Operator):
    """Convert this file from the old (pre-1.0) RBR addon to the current data
    model. Back the file up first"""

    bl_idname = "rbr.migrate_legacy"
    bl_label = "Migrate old addon file"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context: bpy.types.Context) -> OperatorReturn:
        log = legacy.Log()
        try:
            legacy.migrate(context, log)
        except legacy.LibraryBlocked as blocked:
            self.report(
                {"ERROR"},
                "Open and migrate these library files first, then reopen this file: "
                + ", ".join(blocked.libraries),
            )
            return {"CANCELLED"}
        for scene in bpy.data.scenes:
            scene[PENDING_PROP] = True
        summary = f"Migrated: {len(log.done)} change(s), {len(log.todo)} item(s) need attention (see the console)"
        self.report({"WARNING"} if log.todo else {"INFO"}, summary)
        if context.window is not None:
            getattr(bpy.ops, "rbr").migrate_legacy_options("INVOKE_DEFAULT")
        return {"FINISHED"}


class RBR_OT_migrate_legacy_options(bpy.types.Operator):
    """Run the migrations that change geometry, animation or datablocks and
    are better checked one by one"""

    bl_idname = "rbr.migrate_legacy_options"
    bl_label = "Optional migrations"
    bl_options = {"REGISTER", "UNDO"}

    brake_wall: bpy.props.BoolProperty(  # type: ignore
        name="Brake wall mesh to curve",
        description="Rebuild the inner/outer vertex group mesh as the new brake wall curve with respawn areas, and hide the mesh",
        default=True,
    )
    follow_path: bpy.props.BoolProperty(  # type: ignore
        name="Camera follow path keyframes",
        description="Convert follow path constraint offsets in frames to the new offset factor animation",
        default=True,
    )
    texture_format: bpy.props.BoolProperty(  # type: ignore
        name="Texture formats from .dds headers",
        description="Read each texture's .dds file to pick DXT1, DXT3 or DXT5 instead of leaving everything as DXT1",
        default=True,
    )
    duplicate_shared: bpy.props.BoolProperty(  # type: ignore
        name="Split shared materials and meshes",
        description="Where objects sharing a material or collision mesh had different old settings, make a copy per setting",
        default=True,
    )
    unexported: bpy.props.BoolProperty(  # type: ignore
        name="Move unexported objects out of the export",
        description="Objects that had export unticked go into an excluded 'not-exported' collection",
        default=True,
    )
    node_maths: bpy.props.BoolProperty(  # type: ignore
        name="Move node maths into geometry nodes",
        description="Colour ramps, mixes and maths feeding an RBR shader input move into a geometry nodes modifier that stores the result as an attribute, which the material then reads",
        default=False,
    )

    def invoke(
        self, context: bpy.types.Context, event: bpy.types.Event
    ) -> OperatorReturn:
        if context.window_manager is None or context.window is None:
            return self.execute(context)
        return context.window_manager.invoke_props_dialog(self, width=420)

    def draw(self, context: bpy.types.Context) -> None:
        counts = optional.applicable()
        layout = self.layout
        layout.label(
            text="Tick the migrations to run now. They can be rerun later from the scene panel."
        )
        for key, label, _ in optional.STEPS:
            row = layout.row()
            count = counts.get(key, 0)
            row.enabled = count > 0
            suffix = "" if key == "texture_format" else f" ({count})"
            row.prop(self, key, text=label + suffix)

    def execute(self, context: bpy.types.Context) -> OperatorReturn:
        log = legacy.Log()
        ran = 0
        for key, _, _ in optional.STEPS:
            if getattr(self, key):
                optional.RUNNERS[key](log)
                ran += 1
        self.report(
            {"WARNING"} if log.todo else {"INFO"},
            f"Ran {ran} optional migration(s): {len(log.done)} change(s), {len(log.todo)} need attention (see the console)",
        )
        return {"FINISHED"}


class RBR_OT_migrate_legacy_dismiss(bpy.types.Operator):
    """Hide the optional migrations box"""

    bl_idname = "rbr.migrate_legacy_dismiss"
    bl_label = "Dismiss"

    def execute(self, context: bpy.types.Context) -> OperatorReturn:
        for scene in bpy.data.scenes:
            if PENDING_PROP in scene.keys():
                del scene[PENDING_PROP]
        return {"FINISHED"}


def draw_scene_box(ui: bpy.types.UILayout, context: bpy.types.Context) -> None:
    if legacy.is_legacy_file():
        box = ui.box()
        box.alert = True
        box.label(text="This file was made with the old RBR addon", icon="ERROR")
        box.label(
            text="Back up the file, then migrate it. Exporting before that will not work."
        )
        oldest = legacy.oldest_legacy_version()
        if oldest is not None and oldest <= (0, 2, 1):
            box.label(
                text="Saved with an addon older than v0.2.2: open and save it with v0.3.3 first"
            )
        box.operator(
            RBR_OT_migrate_legacy.bl_idname, icon="FILE_REFRESH", text="Migrate"
        )
        return
    scene = context.scene
    if scene is not None and scene.get(PENDING_PROP):
        box = ui.box()
        box.label(text="Optional migrations are available", icon="INFO")
        row = box.row()
        row.operator(RBR_OT_migrate_legacy_options.bl_idname, text="Choose...")
        row.operator(RBR_OT_migrate_legacy_dismiss.bl_idname, text="Dismiss")


def register() -> None:
    bpy.utils.register_class(RBR_OT_migrate_legacy)
    bpy.utils.register_class(RBR_OT_migrate_legacy_options)
    bpy.utils.register_class(RBR_OT_migrate_legacy_dismiss)


def unregister() -> None:
    bpy.utils.unregister_class(RBR_OT_migrate_legacy_dismiss)
    bpy.utils.unregister_class(RBR_OT_migrate_legacy_options)
    bpy.utils.unregister_class(RBR_OT_migrate_legacy)
