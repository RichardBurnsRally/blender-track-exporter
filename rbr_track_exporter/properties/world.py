import bpy
from mathutils import Vector

from ..types import *
from ..shaders import sky
from ..gpu.clouds import draw_clouds


# TODO some of these should be soft min/max
class RBRWorldSettings(bpy.types.PropertyGroup):
    weather: bpy.props.EnumProperty(  # type: ignore
        name="Weather",
        default=Weather.CRISP.name,
        items=[(w.name, w.pretty(), w.pretty(), w.id()) for w in Weather],
    )
    sky: bpy.props.EnumProperty(  # type: ignore
        name="Sky",
        default=Sky.CLEAR.name,
        items=[(s.name, s.pretty(), s.pretty(), s.id()) for s in Sky],
    )

    def __balance_terrain_reflectance(self, context: bpy.types.Context) -> None:
        if not self.auto_balance:
            return
        value = max(list(self.terrain_reflectance_color))
        value *= self.extinction
        value *= self.sun_intensity
        if value > 0:
            self.terrain_reflectance_multiplier = 1 / value

    auto_balance: bpy.props.BoolProperty(  # type: ignore
        name="Auto Balance",
        description="Automatically set terrain reflectance multiplier to balance vertex colors",
        default=True,
        update=__balance_terrain_reflectance,
    )

    def update_sun_direction(self) -> None:
        # Compute sun direction as a blender vector
        if self.sun is None:
            return
        _pos, quat, _scale = self.sun.matrix_world.decompose()
        v = Vector((0, 0, 1))
        v.rotate(quat)
        v.normalize()
        self.light_direction = v

    def poll_sun(self, object: bpy.types.Object) -> bool:
        return isinstance(object.data, bpy.types.SunLight)

    sun: bpy.props.PointerProperty(  # type: ignore
        name="Sun (Direction)",
        description="Sun light whose rotation sets the light direction. Only objects with a Sun light (not Point, Spot or Area) are listed",
        type=bpy.types.Object,
        update=lambda self, context: self.update_sun_direction(),
        poll=poll_sun,
    )
    # This exists for the shaders to access it
    # Points towards the sun
    light_direction: bpy.props.FloatVectorProperty(  # type: ignore
        name="Light Direction",  # noqa: F821
        default=(0.0, 0.0, 1.0),
        subtype="DIRECTION",  # noqa: F821
    )

    def _update_cloud_name(self, context: bpy.types.Context) -> None:
        cloud_name = CloudName[self.cloud_name]
        if context.scene is None:
            return
        if context.scene.world == self.id_data:
            surface_type = context.scene.rbr_scene_settings.get_active_surface_type()
            draw_clouds(surface_type, cloud_name)
            sky.set_clouds_images()

    cloud_name: bpy.props.EnumProperty(  # type: ignore
        name="Cloud Name",
        default=CloudName.CLEAR.name,
        items=[(s.name, s.pretty(), s.pretty(), s.id()) for s in CloudName],
        update=_update_cloud_name,
    )

    extinction: bpy.props.FloatProperty(  # type: ignore
        name="Extinction",  # noqa: F821
        default=0.5,
        min=0.0,
        max=1.0,
        step=1,
        update=__balance_terrain_reflectance,
    )
    terrain_reflectance_color: bpy.props.FloatVectorProperty(  # type: ignore
        name="Terrain Reflectance Color",
        default=(1.0, 1.0, 1.0),
        min=0.0,
        max=1.0,
        subtype="COLOR",  # noqa: F821
        update=__balance_terrain_reflectance,
    )
    terrain_reflectance_multiplier: bpy.props.FloatProperty(  # type: ignore
        name="Terrain Reflectance Multiplier",
        default=0.02,
        min=0.0,
        soft_max=0.4,
    )
    specular_glossiness: bpy.props.FloatProperty(  # type: ignore
        name="Specular Glossiness",
        default=4.0,
        min=1.0,
        max=14.0,
    )
    specular_alpha: bpy.props.FloatProperty(  # type: ignore
        name="Specular Alpha",
        default=0.4,
        min=0.1,
        max=1.0,
    )
    use_fog: bpy.props.BoolProperty(  # type: ignore
        name="Use Fog",
        default=False,
    )
    fog_color: bpy.props.FloatVectorProperty(  # type: ignore
        name="Fog Color",
        default=(0.8, 0.8, 0.8),
        min=0.0,
        max=1.0,
        subtype="COLOR",  # noqa: F821
    )
    fog_start: bpy.props.FloatProperty(  # type: ignore
        name="Fog Start",
        default=2.0,
        min=0.0,
        soft_min=2.0,
        max=1000.0,
    )
    fog_end: bpy.props.FloatProperty(  # type: ignore
        name="Fog End",
        default=1000.0,
        min=0.0,
        max=10000.0,
    )
    superbowl_fog_start: bpy.props.FloatProperty(  # type: ignore
        name="Superbowl Fog Start",
        default=0.0,
        min=0.0,
        max=1000.0,
    )
    superbowl_fog_end: bpy.props.FloatProperty(  # type: ignore
        name="Superbowl Fog End",
        default=1000.0,
        min=0.0,
        max=10000.0,
    )
    greenstein_value: bpy.props.FloatProperty(  # type: ignore
        name="Greenstein Value",
        default=1.0,
        min=-1.0,
        max=1.0,
        step=1,
    )
    inscattering: bpy.props.FloatProperty(  # type: ignore
        name="Inscattering",  # noqa: F821
        default=0.3,
        min=0.0,
        max=1.0,
        step=1,
    )
    mie_multiplier: bpy.props.FloatProperty(  # type: ignore
        name="Mie Multiplier",
        default=0.001,
        min=0.0,
        max=0.1,
        precision=6,
        step=1,
    )
    rayleigh_multiplier: bpy.props.FloatProperty(  # type: ignore
        name="Rayleigh Multiplier",
        default=0.04,
        min=0.0,
        max=1.0,
        precision=6,
        step=1,
    )
    skybox_saturation: bpy.props.FloatProperty(  # type: ignore
        name="Skybox Saturation",
        default=0.0,
        min=0.0,
        max=1.0,
        step=10,
    )
    skybox_scale: bpy.props.FloatProperty(  # type: ignore
        name="Skybox Scale",
        default=100.0,
        min=1.0,
        max=100.0,
        step=10,
    )
    superbowl_scale: bpy.props.FloatProperty(  # type: ignore
        name="Superbowl Scale",
        default=1.0,
        min=0.0,
        max=2.0,
    )
    sun_intensity: bpy.props.FloatProperty(  # type: ignore
        name="Sun Intensity",
        default=100.0,
        min=30.0,
        max=200.0,
        step=10,
        update=__balance_terrain_reflectance,
    )
    sun_offset: bpy.props.FloatProperty(  # type: ignore
        name="Sun Offset",
        default=0.0,
        min=-3.0,
        max=3.0,
        step=1,
    )
    turbidity: bpy.props.FloatProperty(  # type: ignore
        name="Turbidity",  # noqa: F821
        default=0.0,
        min=0.0,
        max=10.0,
        step=1,
    )

    # The following do not alter the sky shaders.
    ambient: bpy.props.FloatVectorProperty(  # type: ignore
        name="Ambient",  # noqa: F821
        default=(0.5, 0.5, 0.5),
        min=0.0,
        max=1.0,
        subtype="COLOR",  # noqa: F821
    )
    car_ambient_lighting: bpy.props.FloatProperty(  # type: ignore
        name="Car Ambient Lighting",  # noqa: F821
        default=1.74,
        min=0.2,
        max=4.0,
        step=1,
    )
    car_diffuse_lighting: bpy.props.FloatProperty(  # type: ignore
        name="Car Diffuse Lighting",  # noqa: F821
        default=1.9,
        min=0.5,
        max=2.0,
        step=1,
    )
    car_deep_shadow_alpha: bpy.props.FloatProperty(  # type: ignore
        name="Car Deep Shadow Alpha",  # noqa: F821
        default=1.0,
        min=0.0,
        max=1.0,
        step=1,
    )
    car_shadow_alpha: bpy.props.FloatProperty(  # type: ignore
        name="Car Shadow Alpha",  # noqa: F821
        default=0.24,
        min=0.0,
        max=1.5,
        step=1,
    )
    character_lighting: bpy.props.FloatProperty(  # type: ignore
        name="Character Lighting",  # noqa: F821
        default=1.0,
        min=1.0,
        max=2.0,
        step=1,
    )
    cloud_scale: bpy.props.FloatProperty(  # type: ignore
        name="Cloud Scale",  # noqa: F821
        default=10.0,
        min=0.0,
        max=250.0,
        step=1,
    )
    mipmapbias: bpy.props.FloatProperty(  # type: ignore
        name="Mipmap Bias",  # noqa: F821
        default=-3,
        min=-4,
        max=-2,
        step=1,
    )
    particle_lighting: bpy.props.FloatProperty(  # type: ignore
        name="Particle Lighting",  # noqa: F821
        default=1.0,
        min=0.5,
        max=2.0,
        step=1,
    )


def register() -> None:
    bpy.utils.register_class(RBRWorldSettings)
    bpy.types.World.rbr_world_settings = bpy.props.PointerProperty(
        type=RBRWorldSettings,
    )


def unregister() -> None:
    del bpy.types.World.rbr_world_settings
    bpy.utils.unregister_class(RBRWorldSettings)
