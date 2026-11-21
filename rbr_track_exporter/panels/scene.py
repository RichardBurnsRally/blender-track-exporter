from typing import Any, Callable, List

import blf
import bpy

from .world import draw_world_settings
from ..blender_utils import Checks, narrow, panel, ui_split
from ..types import *
from ..preferences import RBRAddonPreferences
from ..properties.curve import check_driveline_validity
from ..properties.scene import (
    RBRSceneSettings,
    RBRExportMessage,
    RBRWorldWeatherPtr,
    RBRContainerObject,
    RBR_OT_prepare_for_shadow_texture_bake,
    RBR_OT_prepare_for_shadow_vcol_bake,
)
from ..physical_material_editor.operator import RBR_OT_edit_material_maps
from .. import __package__ as base_package
from .. import migration


def draw_scene_settings(
    ui: bpy.types.UILayout,
    context: bpy.types.Context,
) -> None:
    migration.draw_scene_box(ui, context)
    panel(
        ui,
        "export_settings",
        "Export Settings",
        lambda ui: draw_export_settings(ui, context),
    )
    panel(
        ui, "track_objects", "Track Objects", lambda ui: draw_track_objects(ui, context)
    )
    panel(
        ui,
        "track_surfaces",
        "Track Surfaces",
        lambda ui: draw_track_surfaces(ui, context),
    )
    # TODO panel(ui, "container_objects", "Anim Container Objects", lambda ui: draw_container_objects(ui, context))
    panel(ui, "tint_sets", "Tint Sets", lambda ui: draw_tint_sets(ui, context))


def draw_export_settings(
    ui: bpy.types.UILayout,
    context: bpy.types.Context,
) -> None:
    if context.scene is None or context.preferences is None:
        return
    scene_settings: RBRSceneSettings = context.scene.rbr_scene_settings
    prefs = narrow(
        context.preferences.addons[base_package].preferences, RBRAddonPreferences
    )

    ui_split(ui, "Export To").prop_search(
        scene_settings,
        "export_to",
        prefs,
        "export_directories",
        text="",
    )
    ui_split(ui, "Track ID").prop(scene_settings, "track_id", text="")
    ui_split(ui, "Track Name").prop(scene_settings, "track_name", text="")
    ui_split(ui, "Author").prop(scene_settings, "author", text="")
    ui_split(ui, "Country Code").prop(scene_settings, "country_code", text="")
    ui_split(ui, "Particles").prop(scene_settings, "particles", text="")
    ui_split(ui, "Surface").prop(scene_settings, "surface", text="")
    box = ui.box()
    box.prop(scene_settings, "compress_textures")
    box.prop(scene_settings, "simplify_shadows")
    if scene_settings.simplify_shadows:
        ui_split(box, "Dedup Threshold").prop(
            scene_settings, "shadow_dedup_threshold", text=""
        )
        ui_split(box, "Gradient Threshold").prop(
            scene_settings, "shadow_gradient_threshold", text=""
        )
    box.operator("rbr.export_track", icon="EXPORT", text="Export")
    num_export_errors = len(scene_settings.export_errors)
    if num_export_errors > 0:
        export_errors_title = f"Errors ({num_export_errors})"
        panel(
            ui,
            "export_errors",
            export_errors_title,
            lambda ui: draw_export_messages(ui, context, scene_settings.export_errors),
        )
    num_export_warnings = len(scene_settings.export_warnings)
    if num_export_warnings > 0:
        export_warnings_title = f"Warnings ({num_export_warnings})"
        panel(
            ui,
            "export_warnings",
            export_warnings_title,
            lambda ui: draw_export_messages(
                ui, context, scene_settings.export_warnings
            ),
        )


# TODO consider moving to separate top-level panel
def wrap_to_px(text: str, max_px: float) -> List[str]:
    """Greedily wrap `text` to lines no wider than `max_px`, measuring the
    actual UI font (blf font 0 must already be sized). Over-long words are
    hard-broken so a single word can never overflow."""

    def fits(s: str) -> bool:
        return bool(blf.dimensions(0, s)[0] <= max_px)

    lines: List[str] = []
    current = ""
    for word in text.split():
        while not fits(word) and len(word) > 1:
            cut = len(word)
            while cut > 1 and not fits(word[:cut]):
                cut -= 1
            if current:
                lines.append(current)
                current = ""
            lines.append(word[:cut])
            word = word[cut:]
        candidate = word if not current else f"{current} {word}"
        if fits(candidate):
            current = candidate
        else:
            if current:
                lines.append(current)
            current = word
    if current:
        lines.append(current)
    return lines or [text]


def draw_export_messages(
    ui: bpy.types.UILayout,
    context: bpy.types.Context,
    export_messages: List[RBRExportMessage],
) -> None:
    if context.region is None or context.preferences is None:
        return
    ui_scale = context.preferences.system.ui_scale
    try:
        points = context.preferences.ui_styles[0].widget.points
    except (AttributeError, IndexError):
        points = 11.0
    blf.size(0, points * ui_scale)
    # Available width for the label column: the region minus the jump button,
    # panel padding and the label's own inset (scaled). Bump the reserve if text
    # still touches the edge.
    max_px = max(context.region.width - 70 * ui_scale, 40 * ui_scale)
    for message in export_messages:
        row = ui.row()
        row.context_pointer_set(name="rbr_export_message", data=message)
        row.operator("rbr.jump_to_message_source", icon="VIEWZOOM", text="")
        column = row.column()
        for line in wrap_to_px(message.message, max_px):
            column.label(text=line)


def draw_track_objects(
    ui: bpy.types.UILayout,
    context: bpy.types.Context,
) -> None:
    if context.scene is None:
        return
    scene_settings: RBRSceneSettings = context.scene.rbr_scene_settings
    driveline_checks = (
        Checks()
        if scene_settings.driveline is None
        else check_driveline_validity(scene_settings.driveline)
    )
    driveline_ui = ui_split(ui, "Driveline").column()
    driveline_ui.alert = len(driveline_checks.errors) > 0
    driveline_ui.prop(scene_settings, "driveline", text="", placeholder="Curve")
    driveline_checks.draw(driveline_ui)
    ui_split(ui, "Car Location").prop(
        scene_settings, "car_location", text="", placeholder="Empty"
    )
    # TODO checks
    ui_split(ui, "Brake Wall").prop(scene_settings, "brake_wall", text="")
    ui_split(ui, "Registration Zone").prop(
        scene_settings, "registration_zone", text="", placeholder="Empty"
    )


def draw_track_surfaces(
    ui: bpy.types.UILayout,
    context: bpy.types.Context,
) -> None:
    if context.scene is None:
        return
    scene_settings: RBRSceneSettings = context.scene.rbr_scene_settings
    surfaces = ui_split(ui, "Surfaces").column()
    surfaces.prop(scene_settings, "surface_type_dry")
    surfaces.prop(scene_settings, "surface_type_damp")
    surfaces.prop(scene_settings, "surface_type_wet")
    if not any(
        [
            scene_settings.surface_type_dry,
            scene_settings.surface_type_damp,
            scene_settings.surface_type_wet,
        ]
    ):
        Checks(errors=["Must select at least one surface type"]).draw(ui)
    row = ui_split(ui, "Active Surface").row(align=True)
    row.prop(scene_settings, "active_surface_type", text="")
    row.prop(scene_settings, "active_surface_age", text="")


def draw_container_objects(
    ui: bpy.types.UILayout,
    context: bpy.types.Context,
) -> None:
    if context.scene is None:
        return
    scene_settings: RBRSceneSettings = context.scene.rbr_scene_settings

    # List the weather slots
    objs_list = ui.row()
    objs_list.template_list(
        listtype_name=RBR_UL_container_objects_list.bl_idname,
        list_id="",
        dataptr=scene_settings,
        propname="container_objects",
        active_dataptr=scene_settings,
        active_propname="active_container_object",
        rows=3,
    )
    # Buttons to add/remove container object slots
    right_buttons = objs_list.column(align=True)
    right_buttons.operator(
        "rbr.add_container_object",
        icon="ADD",
        text="",
    )
    remove_button = right_buttons.operator(
        "rbr.remove_container_object",
        icon="REMOVE",
        text="",
    )
    remove_button.index = scene_settings.active_container_object
    try:
        active_container_object = scene_settings.container_objects[
            scene_settings.active_container_object
        ]
        ui.prop(active_container_object, "container_name")
        ui.prop(active_container_object, "container_id")
        ui.prop(active_container_object, "flag")
        ui.prop(active_container_object, "random_upper_bound")
    except IndexError:
        pass


def draw_tint_sets(
    ui: bpy.types.UILayout,
    context: bpy.types.Context,
) -> None:
    if context.scene is None:
        return
    scene_settings: RBRSceneSettings = context.scene.rbr_scene_settings
    tint_sets = ui_split(ui, "Tint Sets").column()
    tint_sets.prop(scene_settings, "tint_set_morning")
    tint_sets.prop(scene_settings, "tint_set_noon")
    tint_sets.prop(scene_settings, "tint_set_evening")
    tint_sets.prop(scene_settings, "tint_set_overcast")
    if not any(
        [
            scene_settings.tint_set_morning,
            scene_settings.tint_set_noon,
            scene_settings.tint_set_evening,
            scene_settings.tint_set_overcast,
        ]
    ):
        Checks(errors=["Must select at least one tint set"]).draw(ui)

    ui_split(ui, "Active Tint Set").prop(scene_settings, "active_tint_set", text="")

    def draw_baking_tools(ui: bpy.types.UILayout) -> None:
        textures = ui_split(ui, "Textures").row(align=True)
        textures.operator(
            RBR_OT_prepare_for_shadow_texture_bake.bl_idname, text="Prepare"
        )
        bake = textures.operator("object.bake", text="Bake")
        bake.type = "DIFFUSE"
        bake.pass_filter = {"DIRECT", "INDIRECT"}
        bake.use_selected_to_active = False
        bake.target = "IMAGE_TEXTURES"
        vcols = ui_split(ui, "Vertex Colors").row(align=True)
        vcols.operator(RBR_OT_prepare_for_shadow_vcol_bake.bl_idname, text="Prepare")
        bake = vcols.operator("object.bake", text="Bake")
        bake.type = "DIFFUSE"
        bake.pass_filter = {"DIRECT", "INDIRECT"}
        bake.use_selected_to_active = False
        bake.target = "VERTEX_COLORS"

    panel(ui, "baking_tools", "Baking Tools", draw_baking_tools)

    tint_set = scene_settings.get_active_tint_set()
    tint_set_str = tint_set.name.lower()
    tint_set_title = tint_set_str.title()

    def draw_weather(ui: bpy.types.UILayout) -> None:
        # List the weather slots
        world_list = ui.row()
        world_list.template_list(
            listtype_name=RBR_UL_world_weathers_list.bl_idname,
            list_id="",
            dataptr=scene_settings,
            propname=f"world_weathers_{tint_set_str}",
            active_dataptr=scene_settings,
            active_propname="active_world_weather",
            rows=3,
        )
        # Buttons to add/remove weather slots
        right_buttons = world_list.column(align=True)
        right_buttons.operator(
            "rbr.add_world_weather_sky",
            icon="ADD",
            text="",
        )
        remove_button = right_buttons.operator(
            "rbr.remove_world_weather_sky",
            icon="REMOVE",
            text="",
        )
        remove_button.index = scene_settings.active_world_weather
        # Display the template_ID like UI for selecting what is in the active
        # slot
        active_world_weather = scene_settings.get_active_weather()
        if active_world_weather is not None:
            ui.template_ID(active_world_weather, "world")
            if tint_set is TintSet.OVERCAST:
                ui_split(ui, "Time").prop(
                    active_world_weather, "overcast_time_of_day", text=""
                )

    panel(ui, "weather", f"{tint_set_title} Weathers", draw_weather)
    active_world_weather = scene_settings.get_active_weather()
    if active_world_weather is not None:
        world = active_world_weather.world
        if world is not None:
            panel(
                ui,
                "world",
                "Weather Settings",
                lambda ui: draw_world_settings(ui, world),
            )


class RBR_PT_scene_panel(bpy.types.Panel):
    bl_idname = "RBR_PT_scene_panel"
    bl_label = "RBR Scene Settings"
    bl_space_type = "PROPERTIES"
    bl_region_type = "WINDOW"
    bl_context = "scene"

    def draw(self, context: bpy.types.Context) -> None:
        draw_scene_settings(self.layout, context)


class RBR_UL_container_objects_list(bpy.types.UIList):
    bl_idname = "RBR_UL_container_objects_list"

    def draw_item(
        self,
        context: bpy.types.Context,
        layout: bpy.types.UILayout,
        data: Any,
        item: Any,
        icon: int | None,
        active_data: Any,
        active_property: str | None,
        index: int | None = 0,
        flt_flag: int | None = 0,
    ) -> None:
        if not isinstance(item, RBRContainerObject):
            return
        layout.label(text=item.container_name)


class RBR_UL_world_weathers_list(bpy.types.UIList):
    bl_idname = "RBR_UL_world_weathers_list"

    def draw_item(
        self,
        context: bpy.types.Context,
        layout: bpy.types.UILayout,
        data: Any,
        item: Any,
        icon: int | None,
        active_data: Any,
        active_property: str | None,
        index: int | None = 0,
        flt_flag: int | None = 0,
    ) -> None:
        if not isinstance(item, RBRWorldWeatherPtr):
            return
        if item.world is None:
            return
        settings = item.world.rbr_world_settings
        layout.label(text=Weather[settings.weather].pretty())
        layout.label(text=Sky[settings.sky].pretty())
        layout.label(text=item.world.name)


def register() -> None:
    bpy.utils.register_class(RBR_UL_container_objects_list)
    bpy.utils.register_class(RBR_UL_world_weathers_list)

    bpy.utils.register_class(RBR_PT_scene_panel)


def unregister() -> None:
    bpy.utils.unregister_class(RBR_PT_scene_panel)

    bpy.utils.unregister_class(RBR_UL_world_weathers_list)
    bpy.utils.unregister_class(RBR_UL_container_objects_list)
