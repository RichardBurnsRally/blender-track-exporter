import enum
from typing import Optional

import bpy


class ScmPhysicsBushDensity(enum.Enum):
    VERY_SPARSE = 0x0
    SPARSE = 0x1
    LEAFY = 0x2  # LOV
    STRAGGLY = 0x3  # SPRET
    DENSE = 0x4
    VERY_DENSE = 0x5

    def pretty(self) -> str:
        return self.name.replace("_", " ").title()

    def description(self) -> str:
        return self.name.replace("_", " ").title()

    def is_sized(self) -> bool:
        if self is ScmPhysicsBushDensity.LEAFY:
            return True
        elif self is ScmPhysicsBushDensity.STRAGGLY:
            return True
        else:
            return False


class ScmPhysicsSize(enum.Enum):
    SMALL = 0x0
    MEDIUM = 0x1
    LARGE = 0x2

    def pretty(self) -> str:
        return self.name.replace("_", " ").title()

    def description(self) -> str:
        return self.name.replace("_", " ").title()


class ScmPhysics(enum.Enum):
    UNDEFINED = 0x0
    BUSH = 0x1
    BENDABLE_TREE = 0x2
    TREE = 0x3  # sized
    TREE_STUMP = 0x4
    TREE_TRUNK = 0x5  # sized
    METAL_BARRIER = 0x6
    METAL_POLE = 0x7
    ROCK = 0x8  # sized
    SPECTATOR = 0x9
    SNOW_WALL = 0xA

    def pretty(self) -> str:
        return self.name.replace("_", " ").title()

    def description(self) -> str:
        if self is ScmPhysics.SPECTATOR:
            return "Hitting it ends the stage as a spectator collision"
        return self.name.replace("_", " ").title()

    def is_sized(self, bush_density: ScmPhysicsBushDensity) -> bool:
        if self is ScmPhysics.BUSH:
            return bush_density.is_sized()
        elif self is ScmPhysics.TREE:
            return True
        elif self is ScmPhysics.TREE_TRUNK:
            return True
        elif self is ScmPhysics.ROCK:
            return True
        else:
            return False

    def is_bendable(self, size: ScmPhysicsSize) -> Optional[str]:
        if self is ScmPhysics.ROCK:
            if size is ScmPhysicsSize.SMALL:
                return "Very soft bendable collision"
        elif self is ScmPhysics.BENDABLE_TREE:
            return "Soft bendable collision"
        elif self is ScmPhysics.TREE_STUMP:
            return "Hard bendable collision"
        return None


class RBRCollisionPhysics(bpy.types.PropertyGroup):
    physics: bpy.props.EnumProperty(  # type: ignore
        items=[(t.name, t.pretty(), t.description(), t.value) for t in ScmPhysics],
        name="Physics Properties",
        default=ScmPhysics.UNDEFINED.name,
    )
    bush_density: bpy.props.EnumProperty(  # type: ignore
        items=[
            (t.name, t.pretty(), t.description(), t.value)
            for t in ScmPhysicsBushDensity
        ],
        name="Bush Density",
        default=ScmPhysicsBushDensity.LEAFY.name,
    )
    size: bpy.props.EnumProperty(  # type: ignore
        items=[(t.name, t.pretty(), t.description(), t.value) for t in ScmPhysicsSize],
        name="Size",
        default=ScmPhysicsSize.MEDIUM.name,
    )


def register() -> None:
    bpy.utils.register_class(RBRCollisionPhysics)


def unregister() -> None:
    bpy.utils.unregister_class(RBRCollisionPhysics)
