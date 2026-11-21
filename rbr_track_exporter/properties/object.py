from typing import Set

import bpy

from ..types import *
from .collision import RBRCollisionPhysics


class RBRObjectSettings(bpy.types.PropertyGroup):
    make_instances_real: bpy.props.BoolProperty(  # type: ignore
        name="Export real instances",
        description=(
            "Runs 'Make Instances Real' operator during export. "
            "Use if you need the instanced objects to differ via modifiers"
        ),
        default=False,
    )
    soft_collision: bpy.props.BoolProperty(  # type: ignore
        name="Soft Collision",
        description=(
            "This empty pushes the car away without a hard collision. "
            "A cube or sphere display type gives the shape and the scale gives the size"
        ),
        default=False,
    )
    collision_physics: bpy.props.PointerProperty(  # type: ignore
        type=RBRCollisionPhysics,
    )

    tint_set_morning: bpy.props.BoolProperty(  # type: ignore
        name="Morning",
        description="Export morning tint set",
        default=True,
    )
    tint_set_noon: bpy.props.BoolProperty(  # type: ignore
        name="Noon",
        description="Export noon tint set",
        default=True,
    )
    tint_set_evening: bpy.props.BoolProperty(  # type: ignore
        name="Evening",
        description="Export evening tint set",
        default=True,
    )
    tint_set_overcast: bpy.props.BoolProperty(  # type: ignore
        name="Overcast",
        description="Export overcast tint set",
        default=True,
    )


def register() -> None:
    bpy.utils.register_class(RBRObjectSettings)
    bpy.types.Object.rbr_object_settings = bpy.props.PointerProperty(
        type=RBRObjectSettings,
    )


def unregister() -> None:
    del bpy.types.Object.rbr_object_settings
    bpy.utils.unregister_class(RBRObjectSettings)
