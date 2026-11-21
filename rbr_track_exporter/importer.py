import bpy
from .types import OperatorReturn
from typing import Any, Set
from . import rbr_blender_track_io


class RBR_OT_import_track(bpy.types.Operator):
    """Import an RBR track"""

    bl_idname = "rbr.import_track"
    bl_label = "Import RBR Track"
    bl_description = "Import from native RBR track format (.dls, .lbs, ...)"
    bl_options = {"UNDO"}

    filepath: bpy.props.StringProperty(  # type: ignore
        name="input file",
        subtype="FILE_PATH",  # noqa: F821
    )

    filename_ext = ".trk"

    filter_glob: bpy.props.StringProperty(  # type: ignore
        default="*.trk",  # noqa: F821
        options={"HIDDEN"},  # noqa: F821
    )

    # TODO REMOVE
    join_colmesh: bpy.props.BoolProperty(  # type: ignore
        name="Join colmesh",
        default=True,
    )

    def invoke(
        self, context: bpy.types.Context, event: bpy.types.Event
    ) -> OperatorReturn:
        wm = context.window_manager
        if wm is None:
            return {"CANCELLED"}
        wm.fileselect_add(self)
        return {"RUNNING_MODAL"}

    def execute(self, context: bpy.types.Context) -> OperatorReturn:
        if "run_import" in dir(rbr_blender_track_io):
            rbr_blender_track_io.run_import(self.filepath, self.join_colmesh)
            frame_all_and_set_clip(context)
            self.report({"INFO"}, "Import complete")
            return {"FINISHED"}
        return {"CANCELLED"}

    @classmethod
    def poll(cls, context: bpy.types.Context) -> bool:
        return "run_import" in dir(rbr_blender_track_io)

    def draw(self, context: bpy.types.Context) -> None:
        ui = self.layout
        ui.prop(self, "join_colmesh")
        pass


def frame_all_and_set_clip(context: bpy.types.Context) -> None:
    view_layer = context.view_layer
    objects = list(view_layer.objects) if view_layer is not None else []
    for obj in objects:
        obj.select_set(True)
    screen = context.screen
    if screen is not None:
        for area in screen.areas:
            if area.type != "VIEW_3D":
                continue
            space = area.spaces.active
            if isinstance(space, bpy.types.SpaceView3D):
                space.clip_end = 10000.0
            for region in area.regions:
                if region.type == "WINDOW":
                    with context.temp_override(area=area, region=region):
                        bpy.ops.view3d.view_selected(use_all_regions=True)
                    break
    for obj in objects:
        obj.select_set(False)


def import_menu_func(self: Any, context: bpy.types.Context) -> None:
    self.layout.operator(
        RBR_OT_import_track.bl_idname,
        text="RBR Track (.trk, .lbs, ...)",
    )


def register() -> None:
    bpy.utils.register_class(RBR_OT_import_track)
    bpy.types.TOPBAR_MT_file_import.append(import_menu_func)


def unregister() -> None:
    bpy.utils.unregister_class(RBR_OT_import_track)
    bpy.types.TOPBAR_MT_file_import.remove(import_menu_func)
