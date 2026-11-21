from typing import Optional

import bpy

from ..gnodes.fence import GNODES_FENCE_SUBDIVIDE, GNODES_FENCE_VCOL
from ..properties.fence import FenceTextureSource, RBRFenceSettings
from ..properties.object import RBRObjectSettings
from ..properties.collision import (
    RBRCollisionPhysics,
    ScmPhysics,
    ScmPhysicsBushDensity,
    ScmPhysicsSize,
)
from ..properties.mesh import RBRMeshSettings, RBRMeshType
from ..properties.curve import (
    RBR_OT_add_pacenote,
    RBR_OT_remove_pacenote,
    RBRCurveSettings,
    RBRCurveType,
    detect_zfar,
)
from ..properties.camera import RBRCameraSettings
from ..properties.scene import RBRSceneSettings
from ..types import PacenoteId
from ..blender_utils import *  # TODO move ?


def draw_object_tint_sets(
    ui: bpy.types.UILayout, obj_settings: RBRObjectSettings
) -> None:
    tint_sets = ui_split(ui, "Tint Sets").column()
    tint_sets.prop(obj_settings, "tint_set_morning")
    tint_sets.prop(obj_settings, "tint_set_noon")
    tint_sets.prop(obj_settings, "tint_set_evening")
    tint_sets.prop(obj_settings, "tint_set_overcast")


def draw_object_settings(
    context: bpy.types.Context,
    ui: bpy.types.UILayout,
    obj: Optional[bpy.types.Object],
) -> None:
    if obj is None:
        return
    if context.scene is None:
        return
    scene_settings: RBRSceneSettings = context.scene.rbr_scene_settings
    object_settings: RBRObjectSettings = obj.rbr_object_settings
    if obj == scene_settings.car_location:
        draw_car_location(ui)
    elif obj.parent is not None and obj.parent == scene_settings.driveline:
        draw_zfar(ui)
    elif obj == scene_settings.brake_wall:
        draw_brake_wall(ui)
    elif obj == scene_settings.registration_zone:
        draw_registration_zone(ui)
    elif isinstance(obj.data, bpy.types.Camera):
        draw_object_tint_sets(ui, object_settings)
        draw_camera_settings(context, ui, obj, obj.data)
    elif isinstance(obj.data, bpy.types.Curve):
        draw_curve_settings(context, ui, obj, obj.data)
    elif isinstance(obj.data, bpy.types.Mesh):
        draw_object_tint_sets(ui, object_settings)
        draw_mesh_settings(ui, obj, obj.data)
    elif obj.type == "EMPTY":
        draw_object_tint_sets(ui, object_settings)
        ui.prop(object_settings, "make_instances_real")
        ui.prop(object_settings, "soft_collision")
        if object_settings.soft_collision:
            if obj.empty_display_type not in ("CUBE", "SPHERE"):
                Checks(
                    errors=["Soft collision needs a Cube or Sphere display type"]
                ).draw(ui)
            draw_collision_physics(ui, object_settings.collision_physics)
    else:
        draw_object_tint_sets(ui, object_settings)
        ui.prop(object_settings, "make_instances_real")


def draw_car_location(
    ui: bpy.types.UILayout,
) -> None:
    box = ui.box()
    box.label(text="Car Location", icon="AUTO")


def draw_zfar(
    ui: bpy.types.UILayout,
) -> None:
    box = ui.box()
    box.label(text="Render Distance", icon="DRIVER_DISTANCE")


def draw_brake_wall(
    ui: bpy.types.UILayout,
) -> None:
    box = ui.box()
    box.label(text="Brake Wall", icon="MOD_OUTLINE")


def draw_registration_zone(
    ui: bpy.types.UILayout,
) -> None:
    box = ui.box()
    box.label(text="Registration Zone", icon="SPHERE")


def draw_camera_settings(
    context: bpy.types.Context,
    ui: bpy.types.UILayout,
    obj: bpy.types.Object,
    camera: bpy.types.Camera,
) -> None:
    # force users to set the driveline first
    if context.scene is None:
        return
    rbr_scene_settings: RBRSceneSettings = context.scene.rbr_scene_settings
    if rbr_scene_settings.driveline is None:
        ui.enabled = False
        Checks(errors=["Set the driveline in scene properties"]).draw(ui)
    camera_settings: RBRCameraSettings = camera.rbr_camera_settings
    box = supports_keyframe_animation(ui)
    col = box.column()
    ui_split(col, "Lens").prop(camera, "lens", text="")
    ui_split(col, "Field of View").prop(camera, "angle", text="")
    ui_split(ui, "Clip Start").prop(camera, "clip_start", text="")
    opts = ui_split(ui, "Options").column()
    opts.prop(camera_settings, "look_at_car")
    opts.prop(camera_settings, "helicam")
    if camera_settings.look_at_car:
        ui_split(ui, "Camera Shake").prop(
            camera_settings, "shake", slider=True, text=""
        )
    ui_split(ui, "Follow Spline").prop(camera_settings, "follow_path", text="")
    if camera_settings.follow_path is not None:
        follow_path = obj.constraints.get("Follow Path")
        if follow_path is not None:
            box = supports_keyframe_animation(ui)
            ui_split(box, "Offset").prop(
                follow_path, "offset_factor", slider=True, text=""
            )


def draw_fence_texture(
    ui: bpy.types.UILayout,
    fence: RBRFenceSettings,
    label: str,
    slot: str,
) -> None:
    ui_split(ui, label).prop(fence, f"fence_{slot}_source", expand=True)
    split = ui_split(ui, "")
    if (
        FenceTextureSource[getattr(fence, f"fence_{slot}_source")]
        is FenceTextureSource.BUILTIN
    ):
        split.prop(fence, f"fence_{slot}_builtin_choice", text="")
    else:
        split.template_ID(
            fence, f"fence_{slot}_texture", new="image.new", open="image.open"
        )


def draw_fence_settings(
    ui: bpy.types.UILayout,
    obj: bpy.types.Object,
    fence: RBRFenceSettings,
) -> None:
    ui_split(ui, "Fence Kind").prop(fence, "fence_kind", expand=True)
    gnodes = obj.modifiers.get(".rbr.fence")
    if isinstance(gnodes, bpy.types.NodesModifier) and gnodes.node_group is not None:
        split = ui_split(ui, "Vertex Color")
        vcol = split.row(align=True)
        vcol_input = gnodes_input(gnodes, GNODES_FENCE_VCOL)
        if vcol_input.type == "ATTRIBUTE":
            if hasattr(obj.data, "attributes"):
                vcol.prop_search(
                    vcol_input,
                    "attribute_name",
                    obj.data,
                    "attributes",
                    icon="COLOR",
                    text="",
                )
            else:
                vcol.prop(vcol_input, "attribute_name", text="")
        else:
            vcol.prop(vcol_input, "value", text="")
        options = vcol.operator(
            bpy.ops.object.geometry_nodes_input_attribute_toggle.idname(),
            text="",
            icon="SPREADSHEET",
        )
        options.input_name = GNODES_FENCE_VCOL
        options.modifier_name = ".rbr.fence"
        draw_fence_texture(ui, fence, "Tile Texture", "tile")
        draw_fence_texture(ui, fence, "Pole Texture", "pole")
        ui_split(ui, "Options").prop(
            gnodes_input(gnodes, GNODES_FENCE_SUBDIVIDE), "value", text="Subdivide"
        )


def draw_collision_physics(
    ui: bpy.types.UILayout,
    settings: RBRCollisionPhysics,
) -> None:
    ui_split(ui, "Physics Properties").prop(settings, "physics", text="")
    physics = ScmPhysics[settings.physics]
    bush_density = ScmPhysicsBushDensity[settings.bush_density]
    size = ScmPhysicsSize[settings.size]
    if physics is ScmPhysics.BUSH:
        ui_split(ui, "Bush Density").prop(settings, "bush_density", text="")
    if physics.is_sized(bush_density):
        ui_split(ui, "Size").prop(settings, "size", text="")
    bendable_info = physics.is_bendable(size)
    if bendable_info is not None:
        box = ui.box()
        box.label(text=bendable_info, icon="INFO")


def draw_mesh_settings(
    ui: bpy.types.UILayout,
    obj: bpy.types.Object,
    mesh: bpy.types.Mesh,
) -> None:
    object_settings: RBRObjectSettings = obj.rbr_object_settings
    mesh_settings: RBRMeshSettings = mesh.rbr_mesh_settings
    ui_split(ui, "Mesh Type").prop(mesh_settings, "mesh_type", text="")
    mesh_type = RBRMeshType[mesh_settings.mesh_type]
    if mesh_type is RBRMeshType.NONE:
        ui.prop(object_settings, "make_instances_real")
    elif mesh_type is RBRMeshType.INTERACTIVE_OBJECT:
        ui_split(ui, "Collision Mesh").prop(
            mesh_settings, "interactive_object_colmesh", text=""
        )
        ui_split(ui, "Physics Properties").prop(
            mesh_settings, "interactive_object_physics", text=""
        )
    elif mesh_type is RBRMeshType.STATIC_SHAPE_COLLISION:
        draw_collision_physics(ui, mesh_settings.collision_physics)
    elif mesh_type is RBRMeshType.FENCE:
        fence = mesh_settings.fence
        draw_fence_settings(ui, obj, fence)
    elif mesh_type is RBRMeshType.WATER_SPLASH:
        ui_split(ui, "Weathers").prop(
            mesh_settings, "water_splash_weather", expand=True
        )


def draw_curve_settings(
    context: bpy.types.Context,
    ui: bpy.types.UILayout,
    obj: bpy.types.Object,
    curve: bpy.types.Curve,
) -> None:
    object_settings: RBRObjectSettings = obj.rbr_object_settings
    curve_settings: RBRCurveSettings = curve.rbr_curve_settings
    if context.scene is None:
        return
    scene_settings: RBRSceneSettings = context.scene.rbr_scene_settings
    if obj == scene_settings.driveline:
        box = ui.box()
        box.label(text="Driveline", icon="CON_FOLLOWTRACK")

        if len(obj.modifiers) > 0:
            Checks(errors=["Driveline must not have modifiers"]).draw(ui)

        def zfar_panel(ui: bpy.types.UILayout) -> None:
            zfar = detect_zfar(obj)
            if zfar is not None:
                box = supports_keyframe_animation(ui)
                box.prop(zfar, "empty_display_size", text="Render Distance")
            ui_split(ui, "Multiplier").prop(
                curve_settings, "render_distance_scale", text=""
            )

        panel(
            ui,
            "rbr_curve_render_distance_panel",
            title="Render Distance",
            draw_content=zfar_panel,
        )

        def events_panel(ui: bpy.types.UILayout) -> None:
            draw_curve_events(ui, curve_settings)

        panel(ui, "rbr_curve_events_panel", title="Events", draw_content=events_panel)

        def pacenotes_panel(ui: bpy.types.UILayout) -> None:
            draw_curve_pacenotes(ui, curve_settings)

        panel(
            ui,
            "rbr_curve_pacenotes_panel",
            title="Pacenotes",
            draw_content=pacenotes_panel,
        )
        return
    draw_object_tint_sets(ui, object_settings)
    ui_split(ui, "Curve Type").prop(curve_settings, "curve_type", text="")
    curve_type = RBRCurveType[curve_settings.curve_type]
    if curve_type is RBRCurveType.FENCE:
        fence = curve_settings.fence
        draw_fence_settings(ui, obj, fence)
    else:
        ui.prop(object_settings, "make_instances_real")


def draw_curve_events(
    ui: bpy.types.UILayout,
    curve_settings: RBRCurveSettings,
) -> None:
    ui_split(ui, "Viewport Distance").prop(
        curve_settings, "alpha_far", text="", slider=True
    )
    ui.separator()
    ui_split(ui, "Start").prop(curve_settings, "event_start", text="")
    ui_split(ui, "Split 1").prop(curve_settings, "event_split_1", text="")
    ui_split(ui, "Split 2").prop(curve_settings, "event_split_2", text="")
    ui_split(ui, "Finish").prop(curve_settings, "event_finish", text="")
    ui_split(ui, "End of Stage").prop(curve_settings, "event_end_of_stage", text="")


def draw_curve_pacenotes(
    ui: bpy.types.UILayout,
    curve_settings: RBRCurveSettings,
) -> None:
    ui.label(text="You should create pacenotes externally")
    for index in curve_settings.get_sorted_pacenote_indices():
        pacenote = curve_settings.pacenotes[index]
        row = ui.row()
        row.prop(pacenote, "location", text="")
        row.prop(pacenote, "pacenote_id", text="")
        row.prop(pacenote, "flags", text="")
        try:
            n = PacenoteId(pacenote.pacenote_id)
            row.label(text=n.pretty())
        except ValueError:
            row.label(text="Unknown")
        op = row.operator(
            RBR_OT_remove_pacenote.bl_idname,
            icon="REMOVE",
            text="",
        )
        op.index = index
    ui.operator(RBR_OT_add_pacenote.bl_idname)


class RBR_PT_object_settings(bpy.types.Panel):
    bl_idname = "RBR_PT_object_settings"
    bl_label = "RBR Object Settings"
    bl_space_type = "PROPERTIES"
    bl_region_type = "WINDOW"
    bl_context = "object"

    def draw(self, context: bpy.types.Context) -> None:
        draw_object_settings(
            context,
            self.layout,
            context.active_object,
        )


def register() -> None:
    bpy.utils.register_class(RBR_PT_object_settings)


def unregister() -> None:
    bpy.utils.unregister_class(RBR_PT_object_settings)
