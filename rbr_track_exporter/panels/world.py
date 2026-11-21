import bpy

from ..properties.scene import RBRSceneSettings
from ..properties.world import RBRWorldSettings
from ..blender_utils import panel, ui_split, Checks


class RBR_PT_world_settings(bpy.types.Panel):
    bl_idname = "RBR_PT_world_settings"
    bl_label = "RBR World Settings"
    bl_space_type = "PROPERTIES"
    bl_region_type = "WINDOW"
    bl_context = "world"

    def draw(self, context: bpy.types.Context) -> None:
        if context.world is None:
            return
        ui = self.layout
        draw_world_settings(ui, context.world)


def draw_world_settings(ui: bpy.types.UILayout, world: bpy.types.World) -> None:
    if bpy.context.scene is None:
        return
    scene_settings: RBRSceneSettings = bpy.context.scene.rbr_scene_settings
    world_settings: RBRWorldSettings = world.rbr_world_settings

    ui_split(ui, "Weather").prop(world_settings, "weather", text="")
    ui_split(ui, "Sky").prop(world_settings, "sky", text="")

    def fog_title(ui: bpy.types.UILayout) -> None:
        ui.prop(world_settings, "use_fog")

    def fog_panel(ui: bpy.types.UILayout) -> None:
        ui_split(ui, "Color").prop(world_settings, "fog_color", text="")
        ui_split(ui, "Start").prop(world_settings, "fog_start", slider=True, text="")
        ui_split(ui, "End").prop(world_settings, "fog_end", slider=True, text="")
        ui_split(ui, "Superbowl Start").prop(
            world_settings, "superbowl_fog_start", slider=True, text=""
        )
        ui_split(ui, "Superbowl End").prop(
            world_settings, "superbowl_fog_end", slider=True, text=""
        )
        ui_split(ui, "Skybox Saturation").prop(
            world_settings, "skybox_saturation", slider=True, text=""
        )

    panel(
        ui,
        "rbr_world_use_fog",
        title=fog_title,
        draw_content=fog_panel,
        default_closed=not world_settings.use_fog,
    )

    def ground(ui: bpy.types.UILayout) -> None:
        value = max(list(world_settings.terrain_reflectance_color))
        value *= world_settings.extinction
        value *= world_settings.sun_intensity
        value *= world_settings.terrain_reflectance_multiplier
        value = round(value, 2)
        balance = ui_split(ui, "Balance").column()
        balance.prop(world_settings, "auto_balance")
        balance.progress(text=f"Balance = {value}", factor=value - 0.5)
        box = ui.box()
        box.alert = abs(value - 1) > 0.2
        ui_split(box, "Extinction").prop(
            world_settings, "extinction", slider=True, text=""
        )
        trm = ui_split(box, "Reflectance Multiplier")
        trm.enabled = not world_settings.auto_balance
        trm.prop(world_settings, "terrain_reflectance_multiplier", slider=True, text="")
        ui_split(box, "Reflectance Color").prop(
            world_settings, "terrain_reflectance_color", text=""
        )
        ui.separator()
        ui_split(ui, "Specular Alpha").prop(
            world_settings, "specular_alpha", slider=True, text=""
        )
        ui_split(ui, "Specular Glossiness").prop(
            world_settings, "specular_glossiness", slider=True, text=""
        )
        gb = ui.box()
        gb.label(icon="WORLD", text="Global setting")
        ui_split(gb, "Geom Block Glossiness").prop(
            scene_settings, "geom_block_specular_glossiness", slider=True, text=""
        )
        ui_split(ui, "Superbowl Scale").prop(
            world_settings, "superbowl_scale", slider=True, text=""
        )

    def sky(ui: bpy.types.UILayout) -> None:
        ui_split(ui, "Greenstein Value").prop(
            world_settings, "greenstein_value", slider=True, text=""
        )
        ui_split(ui, "Inscattering").prop(
            world_settings, "inscattering", slider=True, text=""
        )
        ui_split(ui, "Mie Multiplier").prop(
            world_settings, "mie_multiplier", slider=True, text=""
        )
        ui_split(ui, "Rayleigh Multiplier").prop(
            world_settings, "rayleigh_multiplier", slider=True, text=""
        )
        ui_split(ui, "Cloud Scale").prop(
            world_settings, "cloud_scale", slider=True, text=""
        )
        ui_split(ui, "Skybox Scale").prop(
            world_settings, "skybox_scale", slider=True, text=""
        )
        ui_split(ui, "Turbidity").prop(
            world_settings, "turbidity", slider=True, text=""
        )
        ui_split(ui, "Sun Offset").prop(
            world_settings, "sun_offset", slider=True, text=""
        )

    def objects(ui: bpy.types.UILayout) -> None:
        ui_split(ui, "Ambient").prop(world_settings, "ambient", text="")
        ui_split(ui, "Car Ambient Lighting").prop(
            world_settings, "car_ambient_lighting", slider=True, text=""
        )
        ui_split(ui, "Car Diffuse Lighting").prop(
            world_settings, "car_diffuse_lighting", slider=True, text=""
        )
        ui_split(ui, "Car Deep Shadow Alpha").prop(
            world_settings, "car_deep_shadow_alpha", slider=True, text=""
        )
        ui_split(ui, "Car Shadow Alpha").prop(
            world_settings, "car_shadow_alpha", slider=True, text=""
        )
        ui_split(ui, "Character Lighting").prop(
            world_settings, "character_lighting", slider=True, text=""
        )
        ui_split(ui, "Mip Map Bias").prop(
            world_settings, "mipmapbias", slider=True, text=""
        )
        ui_split(ui, "Particle Lighting").prop(
            world_settings, "particle_lighting", slider=True, text=""
        )

    def track_panel(ui: bpy.types.UILayout) -> None:
        ui_split(ui, "Cloud Name").prop(world_settings, "cloud_name", text="")
        if bpy.context.scene is None:
            return
        if bpy.context.scene.rbr_scene_settings.export_to == "":
            Checks(errors=["Set export directory for cloud preview"]).draw(ui)
        ui_split(ui, "Sun").prop(world_settings, "sun", text="")
        ld = ui_split(ui, "Light Direction")
        ld.enabled = world_settings.sun is None
        ld.prop(world_settings, "light_direction", text="")
        ui_split(ui, "Sun Intensity").prop(
            world_settings, "sun_intensity", slider=True, text=""
        )
        panel(ui, "rbr_world_ground_panel", title="Ground", draw_content=ground)
        panel(ui, "rbr_world_sky_panel", title="Sky", draw_content=sky)
        panel(ui, "rbr_world_objects_panel", title="Other", draw_content=objects)

    panel(ui, "rbr_world_track_panel", title="Track Settings", draw_content=track_panel)


def register() -> None:
    bpy.utils.register_class(RBR_PT_world_settings)


def unregister() -> None:
    bpy.utils.unregister_class(RBR_PT_world_settings)
