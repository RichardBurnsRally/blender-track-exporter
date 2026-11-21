import enum
from typing import assert_never

import bpy

from .collision import (
    RBRCollisionPhysics,
    ScmPhysics,
    ScmPhysicsBushDensity,
    ScmPhysicsSize,
)
from .fence import (
    RBRFenceSettings,
    collect_objects,
    get_or_create_fence_modifier,
)


class RBRMeshType(enum.Enum):
    NONE = 0x0
    INTERACTIVE_OBJECT = 0x1
    STATIC_SHAPE_COLLISION = 0x2
    FENCE = 0x3
    WATER_SPLASH = 0x4

    def pretty(self) -> str:
        if self is RBRMeshType.NONE:
            return "None"
        elif self is RBRMeshType.INTERACTIVE_OBJECT:
            return "Interactive Object"
        elif self is RBRMeshType.STATIC_SHAPE_COLLISION:
            return "Static Shape Collision"
        elif self is RBRMeshType.FENCE:
            return "Fence"
        elif self is RBRMeshType.WATER_SPLASH:
            return "Water Splash"
        assert_never(self)

    def description(self) -> str:
        if self is RBRMeshType.NONE:
            return ""
        elif self is RBRMeshType.INTERACTIVE_OBJECT:
            return "Instanced interactive object visual geometry"
        elif self is RBRMeshType.STATIC_SHAPE_COLLISION:
            return "Instanced invisible shape collision mesh"
        elif self is RBRMeshType.FENCE:
            return "Interactive tape fence"
        elif self is RBRMeshType.WATER_SPLASH:
            return "Water splash particle emitter"
        assert_never(self)


class InteractiveObjectPhysics(enum.Enum):
    TRAFFIC_CONE = 0x0
    TRAFFIC_PIG = 0x1
    STREET_SIGN = 0x2
    BANNER_FENCE = 0x3
    LOG = 0x4
    LOG_POLE = 0x5
    WOODEN_FENCE_BAR = 0x6
    WOODEN_FENCE_POLE = 0x7

    def pretty(self) -> str:
        if self is InteractiveObjectPhysics.TRAFFIC_CONE:
            return "Traffic Cone"
        elif self is InteractiveObjectPhysics.TRAFFIC_PIG:
            return "Heavy Concrete Block"
        elif self is InteractiveObjectPhysics.STREET_SIGN:
            return "Street Sign"
        elif self is InteractiveObjectPhysics.BANNER_FENCE:
            return "Banner Fence"
        elif self is InteractiveObjectPhysics.LOG:
            return "Log"
        elif self is InteractiveObjectPhysics.LOG_POLE:
            return "Log Pole"
        elif self is InteractiveObjectPhysics.WOODEN_FENCE_BAR:
            return "Wooden Fence Bar"
        elif self is InteractiveObjectPhysics.WOODEN_FENCE_POLE:
            return "Wooden Fence Pole"
        assert_never(self)

    def description(self) -> str:
        if self is InteractiveObjectPhysics.TRAFFIC_CONE:
            return "Very soft, can be used for small signs"
        elif self is InteractiveObjectPhysics.TRAFFIC_PIG:
            return "Very heavy object which can easily kill the car"
        elif self is InteractiveObjectPhysics.STREET_SIGN:
            return "Very soft"
        elif self is InteractiveObjectPhysics.BANNER_FENCE:
            return ""
        elif self is InteractiveObjectPhysics.LOG:
            return ""
        elif self is InteractiveObjectPhysics.LOG_POLE:
            return ""
        elif self is InteractiveObjectPhysics.WOODEN_FENCE_BAR:
            return ""
        elif self is InteractiveObjectPhysics.WOODEN_FENCE_POLE:
            return ""
        assert_never(self)


class WaterSplashWeather(enum.Enum):
    ALL_WEATHERS = 0x0
    WET_ONLY = 0x1

    def pretty(self) -> str:
        if self is WaterSplashWeather.ALL_WEATHERS:
            return "All weathers"
        elif self is WaterSplashWeather.WET_ONLY:
            return "Wet only"
        assert_never(self)

    def description(self) -> str:
        if self is WaterSplashWeather.ALL_WEATHERS:
            return "Active in every weather, for fords"
        elif self is WaterSplashWeather.WET_ONLY:
            return "Active only in wet weather, for puddles"
        assert_never(self)


class RBRMeshSettings(bpy.types.PropertyGroup):
    def _update_mesh_type(self, context: bpy.types.Context) -> None:
        mesh_type = RBRMeshType[self.mesh_type]
        if mesh_type is RBRMeshType.FENCE:
            objs = collect_objects(self.id_data)
            for obj in objs:
                get_or_create_fence_modifier(obj, self.fence)
        else:
            return

    mesh_type: bpy.props.EnumProperty(  # type: ignore
        items=[(t.name, t.pretty(), t.description(), t.value) for t in RBRMeshType],
        name="Mesh Type",
        default=RBRMeshType.NONE.name,
        update=_update_mesh_type,
    )

    interactive_object_colmesh: bpy.props.PointerProperty(  # type: ignore
        type=bpy.types.Object
    )
    interactive_object_physics: bpy.props.EnumProperty(  # type: ignore
        items=[
            (t.name, t.pretty(), t.description(), t.value)
            for t in InteractiveObjectPhysics
        ],
        name="Physics Properties",
        default=InteractiveObjectPhysics.TRAFFIC_CONE.name,
    )
    collision_physics: bpy.props.PointerProperty(  # type: ignore
        type=RBRCollisionPhysics,
    )

    fence: bpy.props.PointerProperty(  # type: ignore
        type=RBRFenceSettings,
    )

    # TODO think deeper about water splashes
    water_splash_weather: bpy.props.EnumProperty(  # type: ignore
        items=[(t.name, t.pretty(), t.pretty(), t.value) for t in WaterSplashWeather],
        name="Water Splash Weathers",
        default=WaterSplashWeather.ALL_WEATHERS.name,
    )


def register() -> None:
    bpy.utils.register_class(RBRMeshSettings)
    bpy.types.Mesh.rbr_mesh_settings = bpy.props.PointerProperty(type=RBRMeshSettings)


def unregister() -> None:
    del bpy.types.Mesh.rbr_mesh_settings
    bpy.utils.unregister_class(RBRMeshSettings)
