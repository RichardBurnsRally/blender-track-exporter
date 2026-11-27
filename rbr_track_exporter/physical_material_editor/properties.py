import math
from typing import Any, List, Optional, Tuple

import bpy
from ..blender_utils import narrow
from mathutils import Vector

from ..types import (
    ConditionIdentifier,
    MaterialId,
    MaterialMap,
    SurfaceType,
    SurfaceAge,
)
from .types import GrabHandle


def point_in_area(point: Vector, pos1: Vector, pos2: Vector) -> bool:
    px, py = point
    x0, y0 = pos1
    x1, y1 = pos2
    return all(
        [
            px > min(x0, x1),
            px < max(x0, x1),
            py > min(y0, y1),
            py < max(y0, y1),
        ]
    )


class RBRMaterialPicker(bpy.types.PropertyGroup):
    def init(self, context: bpy.types.Context) -> None:
        self.__update__(context)

    # Control the alpha level of the material map
    alpha: bpy.props.FloatProperty(  # type: ignore
        name="Alpha",  # noqa: F821
        min=0,
        max=1,
        default=0.4,
    )

    def set_material_id(self, material_id: MaterialId) -> bool:
        material_id = material_id.simplify()
        is_supported = self.set_from_material_id(material_id)
        if is_supported:
            if self.to_material_id() is not material_id:
                raise RuntimeError("Failed to set material ID")
            self.material_id = material_id.value
            return True
        else:
            return False

    material_id: bpy.props.IntProperty(  # type: ignore
        name="Material ID",
    )

    def __update__(self, context: bpy.types.Context) -> None:
        self.material_id = self.to_material_id().value

    category: bpy.props.EnumProperty(  # type: ignore
        name="Category",  # noqa: F821
        items=[
            ("ROAD", "Road", "", 0),  # noqa: F821
            ("GROUND", "Ground", "", 1),  # noqa: F821
            ("PASSTHROUGH", "Passthrough", "", 2),  # noqa: F821
        ],
        update=__update__,
    )

    road_surface: bpy.props.EnumProperty(  # type: ignore
        name="Road Surface",
        items=[
            ("TARMAC", "Tarmac", "", 0),  # noqa: F821
            ("GRAVEL", "Gravel", "", 1),  # noqa: F821
            ("SNOW", "Snow", "", 2),  # noqa: F821
            ("COBBLE", "Cobble", "", 3),  # noqa: F821
        ],
        update=__update__,
    )

    wetness: bpy.props.EnumProperty(  # type: ignore
        name="Wetness",  # noqa: F821
        items=[
            ("DRY", "Dry", "", 0),  # noqa: F821
            ("DAMP", "Damp", "", 1),  # noqa: F821
            ("WET", "Wet", "", 2),  # noqa: F821
        ],
        update=__update__,
    )

    gravel_type: bpy.props.EnumProperty(  # type: ignore
        name="Gravel Type",
        items=[
            ("US", "US", "", 0),  # noqa: F821
            ("FINE", "Fine", "", 1),  # noqa: F821
            ("MEDIUM", "Medium", "", 2),  # noqa: F821
            ("COARSE", "Coarse", "", 3),  # noqa: F821
            ("BR", "British", "", 4),  # noqa: F821
        ],
        update=__update__,
    )

    gravel_depth: bpy.props.EnumProperty(  # type: ignore
        name="Gravel Depth",
        items=[
            ("SHALLOW", "Shallow", "", 0),  # noqa: F821
            ("DEEP", "Deep", "", 1),  # noqa: F821
            ("DEEPER", "Deeper", "", 2),  # noqa: F821
        ],
        update=__update__,
    )

    tarmac_type: bpy.props.EnumProperty(  # type: ignore
        name="Tarmac Type",
        items=[
            ("FINE", "Fine", "", 0),  # noqa: F821
            ("MEDIUM", "Medium", "", 1),  # noqa: F821
            ("COARSE", "Coarse", "", 2),  # noqa: F821
            ("BLACK_ICE", "Black Ice", "", 3),  # noqa: F821
        ],
        update=__update__,
    )

    tarmac_cleanliness: bpy.props.EnumProperty(  # type: ignore
        name="Tarmac Cleanliness",
        items=[
            ("CLEAN", "Clean", "", 0),  # noqa: F821
            ("SPRINKLED", "Sprinkled", "", 1),  # noqa: F821
            ("COVERED", "Covered", "", 2),  # noqa: F821
        ],
        update=__update__,
    )

    cobble_type: bpy.props.EnumProperty(  # type: ignore
        name="Cobble Type",
        items=[
            ("COBBLE", "Cobble", "", 0),  # noqa: F821
            ("SETT", "Sett", "", 1),  # noqa: F821
        ],
        update=__update__,
    )

    snow_subsurface: bpy.props.EnumProperty(  # type: ignore
        name="Snow Subsurface",
        items=[
            ("GRAVEL", "Gravel", "Snow on Gravel", 0),  # noqa: F821
            ("ICE", "Ice", "Snow on Ice", 1),  # noqa: F821
            ("BANK", "Snowbank", "Snowbank Base", 2),  # noqa: F821
        ],
        update=__update__,
    )

    snow_depth: bpy.props.EnumProperty(  # type: ignore
        name="Snow Depth",
        items=[
            ("SHALLOW", "Shallow", "", 0),  # noqa: F821
            ("MEDIUM", "Medium", "", 1),  # noqa: F821
            ("DEEP", "Deep", "", 2),  # noqa: F821
        ],
        update=__update__,
    )

    ground_surface: bpy.props.EnumProperty(  # type: ignore
        name="Ground Surface",
        items=[
            ("WATER", "Water", "", 0),  # noqa: F821
            ("GRASS", "Grass", "", 1),  # noqa: F821
            ("ROUGH", "Rough", "", 2),  # noqa: F821
            ("DIRT", "Dirt", "", 3),  # noqa: F821
        ],
        update=__update__,
    )

    hardness: bpy.props.EnumProperty(  # type: ignore
        name="Hardness",  # noqa: F821
        items=[
            ("HARD", "Hard", "", 0),  # noqa: F821
            ("MEDIUM", "Medium", "", 1),  # noqa: F821
            ("SOFT", "Soft", "", 2),  # noqa: F821
        ],
        update=__update__,
    )

    rough_type: bpy.props.EnumProperty(  # type: ignore
        name="Rough Type",
        items=[
            ("ROUGH", "Rough", "", 0),  # noqa: F821
            ("VERYROUGH", "Very Rough", "", 1),  # noqa: F821
        ],
        update=__update__,
    )

    scenery_type: bpy.props.EnumProperty(  # type: ignore
        name="Scenery Type",
        items=[
            ("TREE", "Tree", "", 0),  # noqa: F821
            ("ROCK", "Rock", "", 1),  # noqa: F821
            ("METAL", "Metal", "", 2),  # noqa: F821
        ],
        update=__update__,
    )

    tree_type: bpy.props.EnumProperty(  # type: ignore
        name="Tree Type",
        items=[
            ("TREE", "Tree", "", 0),  # noqa: F821
            ("STUMP", "Tree Stump", "", 1),  # noqa: F821
            ("TRUNK", "Tree Trunk", "", 2),  # noqa: F821
        ],
        update=__update__,
    )

    tree_size: bpy.props.EnumProperty(  # type: ignore
        name="Tree Size",
        items=[
            ("BENDABLE", "Bendable", "", 0),  # noqa: F821
            ("SMALL", "Small", "", 1),  # noqa: F821
            ("MEDIUM", "Medium", "", 2),  # noqa: F821
            ("LARGE", "Large", "", 3),  # noqa: F821
        ],
        update=__update__,
    )

    tree_trunk_size: bpy.props.EnumProperty(  # type: ignore
        name="Tree Trunk Size",
        items=[
            ("SMALL", "Small", "", 0),  # noqa: F821
            ("MEDIUM", "Medium", "", 1),  # noqa: F821
            ("LARGE", "Large", "", 2),  # noqa: F821
        ],
        update=__update__,
    )

    rock_size: bpy.props.EnumProperty(  # type: ignore
        name="Rock Size",
        items=[
            ("SMALL", "Small", "", 0),  # noqa: F821
            ("MEDIUM", "Medium", "", 1),  # noqa: F821
            ("LARGE", "Large", "", 2),  # noqa: F821
        ],
        update=__update__,
    )

    metal_type: bpy.props.EnumProperty(  # type: ignore
        name="Metal Type",
        items=[
            ("METAL_POLE", "Metal Pole", "", 0),  # noqa: F821
            ("METAL_BARRIER", "Metal Barrier", "", 1),  # noqa: F821
        ],
        update=__update__,
    )

    def draw(self, context: bpy.types.Context, ui: bpy.types.UILayout) -> None:
        ui.row(align=True).prop(self, "category", expand=True)
        ui.separator(factor=0.5)
        if self.category == "ROAD":
            ui.row(align=True).prop(self, "road_surface", expand=True)
            ui.separator(factor=0.5)
            if self.road_surface == "TARMAC":
                ui.row(align=True).prop(self, "tarmac_type", expand=True)
                if self.tarmac_type != "BLACK_ICE":
                    ui.row(align=True).prop(self, "tarmac_cleanliness", expand=True)
                    ui.row(align=True).prop(self, "wetness", expand=True)
            elif self.road_surface == "GRAVEL":
                ui.row(align=True).prop(self, "gravel_type", expand=True)
                ui.row(align=True).prop(self, "gravel_depth", expand=True)
                ui.row(align=True).prop(self, "wetness", expand=True)
            elif self.road_surface == "SNOW":
                ui.row(align=True).prop(self, "snow_subsurface", expand=True)
                if self.snow_subsurface != "BANK":
                    ui.row(align=True).prop(self, "snow_depth", expand=True)
            elif self.road_surface == "COBBLE":
                ui.row(align=True).prop(self, "cobble_type", expand=True)
                ui.row(align=True).prop(self, "wetness", expand=True)
        elif self.category == "GROUND":
            ui.row(align=True).prop(self, "ground_surface", expand=True)
            ui.separator(factor=0.5)
            if self.ground_surface == "WATER":
                pass
            elif self.ground_surface == "GRASS":
                ui.row(align=True).prop(self, "hardness", expand=True)
                ui.row(align=True).prop(self, "wetness", expand=True)
            elif self.ground_surface == "ROUGH":
                ui.row(align=True).prop(self, "rough_type", expand=True)
                ui.row(align=True).prop(self, "wetness", expand=True)
            elif self.ground_surface == "DIRT":
                ui.row(align=True).prop(self, "hardness", expand=True)
                ui.row(align=True).prop(self, "wetness", expand=True)
        elif self.category == "PASSTHROUGH":
            pass

    def set_from_material_id(self, raw_material_id: MaterialId) -> bool:
        material_id = raw_material_id.simplify()
        if material_id is MaterialId.TARMAC_FINE_CLEAN_DRY:
            self.category = "ROAD"
            self.road_surface = "TARMAC"
            self.tarmac_type = "FINE"
            self.tarmac_cleanliness = "CLEAN"
            self.wetness = "DRY"
        elif material_id is MaterialId.TARMAC_FINE_CLEAN_DAMP:
            self.category = "ROAD"
            self.road_surface = "TARMAC"
            self.tarmac_type = "FINE"
            self.tarmac_cleanliness = "CLEAN"
            self.wetness = "DAMP"
        elif material_id is MaterialId.TARMAC_FINE_CLEAN_WET:
            self.category = "ROAD"
            self.road_surface = "TARMAC"
            self.tarmac_type = "FINE"
            self.tarmac_cleanliness = "CLEAN"
            self.wetness = "WET"
        elif material_id is MaterialId.TARMAC_FINE_SPRINKLED_DRY:
            self.category = "ROAD"
            self.road_surface = "TARMAC"
            self.tarmac_type = "FINE"
            self.tarmac_cleanliness = "SPRINKLED"
            self.wetness = "DRY"
        elif material_id is MaterialId.TARMAC_FINE_SPRINKLED_DAMP:
            self.category = "ROAD"
            self.road_surface = "TARMAC"
            self.tarmac_type = "FINE"
            self.tarmac_cleanliness = "SPRINKLED"
            self.wetness = "DAMP"
        elif material_id is MaterialId.TARMAC_FINE_SPRINKLED_WET:
            self.category = "ROAD"
            self.road_surface = "TARMAC"
            self.tarmac_type = "FINE"
            self.tarmac_cleanliness = "SPRINKLED"
            self.wetness = "WET"
        elif material_id is MaterialId.TARMAC_FINE_COVERED_DRY:
            self.category = "ROAD"
            self.road_surface = "TARMAC"
            self.tarmac_type = "FINE"
            self.tarmac_cleanliness = "COVERED"
            self.wetness = "DRY"
        elif material_id is MaterialId.TARMAC_FINE_COVERED_DAMP:
            self.category = "ROAD"
            self.road_surface = "TARMAC"
            self.tarmac_type = "FINE"
            self.tarmac_cleanliness = "COVERED"
            self.wetness = "DAMP"
        elif material_id is MaterialId.TARMAC_FINE_COVERED_WET:
            self.category = "ROAD"
            self.road_surface = "TARMAC"
            self.tarmac_type = "FINE"
            self.tarmac_cleanliness = "COVERED"
            self.wetness = "WET"

        elif material_id is MaterialId.TARMAC_MEDIUM_CLEAN_DRY:
            self.category = "ROAD"
            self.road_surface = "TARMAC"
            self.tarmac_type = "MEDIUM"
            self.tarmac_cleanliness = "CLEAN"
            self.wetness = "DRY"
        elif material_id is MaterialId.TARMAC_MEDIUM_CLEAN_DAMP:
            self.category = "ROAD"
            self.road_surface = "TARMAC"
            self.tarmac_type = "MEDIUM"
            self.tarmac_cleanliness = "CLEAN"
            self.wetness = "DAMP"
        elif material_id is MaterialId.TARMAC_MEDIUM_CLEAN_WET:
            self.category = "ROAD"
            self.road_surface = "TARMAC"
            self.tarmac_type = "MEDIUM"
            self.tarmac_cleanliness = "CLEAN"
            self.wetness = "WET"
        elif material_id is MaterialId.TARMAC_MEDIUM_SPRINKLED_DRY:
            self.category = "ROAD"
            self.road_surface = "TARMAC"
            self.tarmac_type = "MEDIUM"
            self.tarmac_cleanliness = "SPRINKLED"
            self.wetness = "DRY"
        elif material_id is MaterialId.TARMAC_MEDIUM_SPRINKLED_DAMP:
            self.category = "ROAD"
            self.road_surface = "TARMAC"
            self.tarmac_type = "MEDIUM"
            self.tarmac_cleanliness = "SPRINKLED"
            self.wetness = "DAMP"
        elif material_id is MaterialId.TARMAC_MEDIUM_SPRINKLED_WET:
            self.category = "ROAD"
            self.road_surface = "TARMAC"
            self.tarmac_type = "MEDIUM"
            self.tarmac_cleanliness = "SPRINKLED"
            self.wetness = "WET"
        elif material_id is MaterialId.TARMAC_MEDIUM_COVERED_DRY:
            self.category = "ROAD"
            self.road_surface = "TARMAC"
            self.tarmac_type = "MEDIUM"
            self.tarmac_cleanliness = "COVERED"
            self.wetness = "DRY"
        elif material_id is MaterialId.TARMAC_MEDIUM_COVERED_DAMP:
            self.category = "ROAD"
            self.road_surface = "TARMAC"
            self.tarmac_type = "MEDIUM"
            self.tarmac_cleanliness = "COVERED"
            self.wetness = "DAMP"
        elif material_id is MaterialId.TARMAC_MEDIUM_COVERED_WET:
            self.category = "ROAD"
            self.road_surface = "TARMAC"
            self.tarmac_type = "MEDIUM"
            self.tarmac_cleanliness = "COVERED"
            self.wetness = "WET"

        elif material_id is MaterialId.TARMAC_COARSE_CLEAN_DRY:
            self.category = "ROAD"
            self.road_surface = "TARMAC"
            self.tarmac_type = "COARSE"
            self.tarmac_cleanliness = "CLEAN"
            self.wetness = "DRY"
        elif material_id is MaterialId.TARMAC_COARSE_CLEAN_DAMP:
            self.category = "ROAD"
            self.road_surface = "TARMAC"
            self.tarmac_type = "COARSE"
            self.tarmac_cleanliness = "CLEAN"
            self.wetness = "DAMP"
        elif material_id is MaterialId.TARMAC_COARSE_CLEAN_WET:
            self.category = "ROAD"
            self.road_surface = "TARMAC"
            self.tarmac_type = "COARSE"
            self.tarmac_cleanliness = "CLEAN"
            self.wetness = "WET"
        elif material_id is MaterialId.TARMAC_COARSE_SPRINKLED_DRY:
            self.category = "ROAD"
            self.road_surface = "TARMAC"
            self.tarmac_type = "COARSE"
            self.tarmac_cleanliness = "SPRINKLED"
            self.wetness = "DRY"
        elif material_id is MaterialId.TARMAC_COARSE_SPRINKLED_DAMP:
            self.category = "ROAD"
            self.road_surface = "TARMAC"
            self.tarmac_type = "COARSE"
            self.tarmac_cleanliness = "SPRINKLED"
            self.wetness = "DAMP"
        elif material_id is MaterialId.TARMAC_COARSE_SPRINKLED_WET:
            self.category = "ROAD"
            self.road_surface = "TARMAC"
            self.tarmac_type = "COARSE"
            self.tarmac_cleanliness = "SPRINKLED"
            self.wetness = "WET"
        elif material_id is MaterialId.TARMAC_COARSE_COVERED_DRY:
            self.category = "ROAD"
            self.road_surface = "TARMAC"
            self.tarmac_type = "COARSE"
            self.tarmac_cleanliness = "COVERED"
            self.wetness = "DRY"
        elif material_id is MaterialId.TARMAC_COARSE_COVERED_DAMP:
            self.category = "ROAD"
            self.road_surface = "TARMAC"
            self.tarmac_type = "COARSE"
            self.tarmac_cleanliness = "COVERED"
            self.wetness = "DAMP"
        elif material_id is MaterialId.TARMAC_COARSE_COVERED_WET:
            self.category = "ROAD"
            self.road_surface = "TARMAC"
            self.tarmac_type = "COARSE"
            self.tarmac_cleanliness = "COVERED"
            self.wetness = "WET"

        elif material_id is MaterialId.BLACK_ICE:
            self.category = "ROAD"
            self.road_surface = "TARMAC"
            self.tarmac_type = "BLACK_ICE"

        elif material_id is MaterialId.US_GRAVEL_FINE_SHALLOW_DRY:
            self.category = "ROAD"
            self.road_surface = "GRAVEL"
            self.gravel_type = "US"
            self.gravel_depth = "SHALLOW"
            self.wetness = "DRY"
        elif material_id is MaterialId.US_GRAVEL_FINE_SHALLOW_DAMP:
            self.category = "ROAD"
            self.road_surface = "GRAVEL"
            self.gravel_type = "US"
            self.gravel_depth = "SHALLOW"
            self.wetness = "DAMP"
        elif material_id is MaterialId.US_GRAVEL_FINE_SHALLOW_WET:
            self.category = "ROAD"
            self.road_surface = "GRAVEL"
            self.gravel_type = "US"
            self.gravel_depth = "SHALLOW"
            self.wetness = "WET"
        elif material_id is MaterialId.US_GRAVEL_FINE_DEEP_DRY:
            self.category = "ROAD"
            self.road_surface = "GRAVEL"
            self.gravel_type = "US"
            self.gravel_depth = "DEEP"
            self.wetness = "DRY"
        elif material_id is MaterialId.US_GRAVEL_FINE_DEEP_DAMP:
            self.category = "ROAD"
            self.road_surface = "GRAVEL"
            self.gravel_type = "US"
            self.gravel_depth = "DEEP"
            self.wetness = "DAMP"
        elif material_id is MaterialId.US_GRAVEL_FINE_DEEP_WET:
            self.category = "ROAD"
            self.road_surface = "GRAVEL"
            self.gravel_type = "US"
            self.gravel_depth = "DEEP"
            self.wetness = "WET"
        elif material_id is MaterialId.US_GRAVEL_FINE_DEEPER_DRY:
            self.category = "ROAD"
            self.road_surface = "GRAVEL"
            self.gravel_type = "US"
            self.gravel_depth = "DEEPER"
            self.wetness = "DRY"
        elif material_id is MaterialId.US_GRAVEL_FINE_DEEPER_DAMP:
            self.category = "ROAD"
            self.road_surface = "GRAVEL"
            self.gravel_type = "US"
            self.gravel_depth = "DEEPER"
            self.wetness = "DAMP"
        elif material_id is MaterialId.US_GRAVEL_FINE_DEEPER_WET:
            self.category = "ROAD"
            self.road_surface = "GRAVEL"
            self.gravel_type = "US"
            self.gravel_depth = "DEEPER"
            self.wetness = "WET"

        elif material_id is MaterialId.GRAVEL_FINE_SHALLOW_DRY:
            self.category = "ROAD"
            self.road_surface = "GRAVEL"
            self.gravel_type = "FINE"
            self.gravel_depth = "SHALLOW"
            self.wetness = "DRY"
        elif material_id is MaterialId.GRAVEL_FINE_SHALLOW_DAMP:
            self.category = "ROAD"
            self.road_surface = "GRAVEL"
            self.gravel_type = "FINE"
            self.gravel_depth = "SHALLOW"
            self.wetness = "DAMP"
        elif material_id is MaterialId.GRAVEL_FINE_SHALLOW_WET:
            self.category = "ROAD"
            self.road_surface = "GRAVEL"
            self.gravel_type = "FINE"
            self.gravel_depth = "SHALLOW"
            self.wetness = "WET"
        elif material_id is MaterialId.GRAVEL_FINE_DEEP_DRY:
            self.category = "ROAD"
            self.road_surface = "GRAVEL"
            self.gravel_type = "FINE"
            self.gravel_depth = "DEEP"
            self.wetness = "DRY"
        elif material_id is MaterialId.GRAVEL_FINE_DEEP_DAMP:
            self.category = "ROAD"
            self.road_surface = "GRAVEL"
            self.gravel_type = "FINE"
            self.gravel_depth = "DEEP"
            self.wetness = "DAMP"
        elif material_id is MaterialId.GRAVEL_FINE_DEEP_WET:
            self.category = "ROAD"
            self.road_surface = "GRAVEL"
            self.gravel_type = "FINE"
            self.gravel_depth = "DEEP"
            self.wetness = "WET"
        elif material_id is MaterialId.GRAVEL_FINE_DEEPER_DRY:
            self.category = "ROAD"
            self.road_surface = "GRAVEL"
            self.gravel_type = "FINE"
            self.gravel_depth = "DEEPER"
            self.wetness = "DRY"
        elif material_id is MaterialId.GRAVEL_FINE_DEEPER_DAMP:
            self.category = "ROAD"
            self.road_surface = "GRAVEL"
            self.gravel_type = "FINE"
            self.gravel_depth = "DEEPER"
            self.wetness = "DAMP"
        elif material_id is MaterialId.GRAVEL_FINE_DEEPER_WET:
            self.category = "ROAD"
            self.road_surface = "GRAVEL"
            self.gravel_type = "FINE"
            self.gravel_depth = "DEEPER"
            self.wetness = "WET"

        elif material_id is MaterialId.GRAVEL_MEDIUM_SHALLOW_DRY:
            self.category = "ROAD"
            self.road_surface = "GRAVEL"
            self.gravel_type = "MEDIUM"
            self.gravel_depth = "SHALLOW"
            self.wetness = "DRY"
        elif material_id is MaterialId.GRAVEL_MEDIUM_SHALLOW_DAMP:
            self.category = "ROAD"
            self.road_surface = "GRAVEL"
            self.gravel_type = "MEDIUM"
            self.gravel_depth = "SHALLOW"
            self.wetness = "DAMP"
        elif material_id is MaterialId.GRAVEL_MEDIUM_SHALLOW_WET:
            self.category = "ROAD"
            self.road_surface = "GRAVEL"
            self.gravel_type = "MEDIUM"
            self.gravel_depth = "SHALLOW"
            self.wetness = "WET"
        elif material_id is MaterialId.GRAVEL_MEDIUM_DEEP_DRY:
            self.category = "ROAD"
            self.road_surface = "GRAVEL"
            self.gravel_type = "MEDIUM"
            self.gravel_depth = "DEEP"
            self.wetness = "DRY"
        elif material_id is MaterialId.GRAVEL_MEDIUM_DEEP_DAMP:
            self.category = "ROAD"
            self.road_surface = "GRAVEL"
            self.gravel_type = "MEDIUM"
            self.gravel_depth = "DEEP"
            self.wetness = "DAMP"
        elif material_id is MaterialId.GRAVEL_MEDIUM_DEEP_WET:
            self.category = "ROAD"
            self.road_surface = "GRAVEL"
            self.gravel_type = "MEDIUM"
            self.gravel_depth = "DEEP"
            self.wetness = "WET"
        elif material_id is MaterialId.GRAVEL_MEDIUM_DEEPER_DRY:
            self.category = "ROAD"
            self.road_surface = "GRAVEL"
            self.gravel_type = "MEDIUM"
            self.gravel_depth = "DEEPER"
            self.wetness = "DRY"
        elif material_id is MaterialId.GRAVEL_MEDIUM_DEEPER_DAMP:
            self.category = "ROAD"
            self.road_surface = "GRAVEL"
            self.gravel_type = "MEDIUM"
            self.gravel_depth = "DEEPER"
            self.wetness = "DAMP"
        elif material_id is MaterialId.GRAVEL_MEDIUM_DEEPER_WET:
            self.category = "ROAD"
            self.road_surface = "GRAVEL"
            self.gravel_type = "MEDIUM"
            self.gravel_depth = "DEEPER"
            self.wetness = "WET"

        elif material_id is MaterialId.GRAVEL_COARSE_SHALLOW_DRY:
            self.category = "ROAD"
            self.road_surface = "GRAVEL"
            self.gravel_type = "COARSE"
            self.gravel_depth = "SHALLOW"
            self.wetness = "DRY"
        elif material_id is MaterialId.GRAVEL_COARSE_SHALLOW_DAMP:
            self.category = "ROAD"
            self.road_surface = "GRAVEL"
            self.gravel_type = "COARSE"
            self.gravel_depth = "SHALLOW"
            self.wetness = "DAMP"
        elif material_id is MaterialId.GRAVEL_COARSE_SHALLOW_WET:
            self.category = "ROAD"
            self.road_surface = "GRAVEL"
            self.gravel_type = "COARSE"
            self.gravel_depth = "SHALLOW"
            self.wetness = "WET"
        elif material_id is MaterialId.GRAVEL_COARSE_DEEP_DRY:
            self.category = "ROAD"
            self.road_surface = "GRAVEL"
            self.gravel_type = "COARSE"
            self.gravel_depth = "DEEP"
            self.wetness = "DRY"
        elif material_id is MaterialId.GRAVEL_COARSE_DEEP_DAMP:
            self.category = "ROAD"
            self.road_surface = "GRAVEL"
            self.gravel_type = "COARSE"
            self.gravel_depth = "DEEP"
            self.wetness = "DAMP"
        elif material_id is MaterialId.GRAVEL_COARSE_DEEP_WET:
            self.category = "ROAD"
            self.road_surface = "GRAVEL"
            self.gravel_type = "COARSE"
            self.gravel_depth = "DEEP"
            self.wetness = "WET"
        elif material_id is MaterialId.GRAVEL_COARSE_DEEPER_DRY:
            self.category = "ROAD"
            self.road_surface = "GRAVEL"
            self.gravel_type = "COARSE"
            self.gravel_depth = "DEEPER"
            self.wetness = "DRY"
        elif material_id is MaterialId.GRAVEL_COARSE_DEEPER_DAMP:
            self.category = "ROAD"
            self.road_surface = "GRAVEL"
            self.gravel_type = "COARSE"
            self.gravel_depth = "DEEPER"
            self.wetness = "DAMP"
        elif material_id is MaterialId.GRAVEL_COARSE_DEEPER_WET:
            self.category = "ROAD"
            self.road_surface = "GRAVEL"
            self.gravel_type = "COARSE"
            self.gravel_depth = "DEEPER"
            self.wetness = "WET"

        elif material_id is MaterialId.BR_GRAVEL_COARSE_SHALLOW_DRY:
            self.category = "ROAD"
            self.road_surface = "GRAVEL"
            self.gravel_type = "BR"
            self.gravel_depth = "SHALLOW"
            self.wetness = "DRY"
        elif material_id is MaterialId.BR_GRAVEL_COARSE_SHALLOW_DAMP:
            self.category = "ROAD"
            self.road_surface = "GRAVEL"
            self.gravel_type = "BR"
            self.gravel_depth = "SHALLOW"
            self.wetness = "DAMP"
        elif material_id is MaterialId.BR_GRAVEL_COARSE_SHALLOW_WET:
            self.category = "ROAD"
            self.road_surface = "GRAVEL"
            self.gravel_type = "BR"
            self.gravel_depth = "SHALLOW"
            self.wetness = "WET"
        elif material_id is MaterialId.BR_GRAVEL_COARSE_DEEP_DRY:
            self.category = "ROAD"
            self.road_surface = "GRAVEL"
            self.gravel_type = "BR"
            self.gravel_depth = "DEEP"
            self.wetness = "DRY"
        elif material_id is MaterialId.BR_GRAVEL_COARSE_DEEP_DAMP:
            self.category = "ROAD"
            self.road_surface = "GRAVEL"
            self.gravel_type = "BR"
            self.gravel_depth = "DEEP"
            self.wetness = "DAMP"
        elif material_id is MaterialId.BR_GRAVEL_COARSE_DEEP_WET:
            self.category = "ROAD"
            self.road_surface = "GRAVEL"
            self.gravel_type = "BR"
            self.gravel_depth = "DEEP"
            self.wetness = "WET"
        elif material_id is MaterialId.BR_GRAVEL_COARSE_DEEPER_DRY:
            self.category = "ROAD"
            self.road_surface = "GRAVEL"
            self.gravel_type = "BR"
            self.gravel_depth = "DEEPER"
            self.wetness = "DRY"
        elif material_id is MaterialId.BR_GRAVEL_COARSE_DEEPER_DAMP:
            self.category = "ROAD"
            self.road_surface = "GRAVEL"
            self.gravel_type = "BR"
            self.gravel_depth = "DEEPER"
            self.wetness = "DAMP"
        elif material_id is MaterialId.BR_GRAVEL_COARSE_DEEPER_WET:
            self.category = "ROAD"
            self.road_surface = "GRAVEL"
            self.gravel_type = "BR"
            self.gravel_depth = "DEEPER"
            self.wetness = "WET"

        elif material_id is MaterialId.SNOWONGRAVEL_SHALLOW:
            self.category = "ROAD"
            self.road_surface = "SNOW"
            self.snow_subsurface = "GRAVEL"
            self.snow_depth = "SHALLOW"
        elif material_id is MaterialId.SNOWONGRAVEL_MEDIUM:
            self.category = "ROAD"
            self.road_surface = "SNOW"
            self.snow_subsurface = "GRAVEL"
            self.snow_depth = "MEDIUM"
        elif material_id is MaterialId.SNOWONGRAVEL_DEEP:
            self.category = "ROAD"
            self.road_surface = "SNOW"
            self.snow_subsurface = "GRAVEL"
            self.snow_depth = "DEEP"
        elif material_id is MaterialId.SNOWONICE_SHALLOW:
            self.category = "ROAD"
            self.road_surface = "SNOW"
            self.snow_subsurface = "ICE"
            self.snow_depth = "SHALLOW"
        elif material_id is MaterialId.SNOWONICE_MEDIUM:
            self.category = "ROAD"
            self.road_surface = "SNOW"
            self.snow_subsurface = "ICE"
            self.snow_depth = "MEDIUM"
        elif material_id is MaterialId.SNOWONICE_DEEP:
            self.category = "ROAD"
            self.road_surface = "SNOW"
            self.snow_subsurface = "ICE"
            self.snow_depth = "DEEP"
        elif material_id is MaterialId.SNOWWALL_BOTTOM:
            self.category = "ROAD"
            self.road_surface = "SNOW"
            self.snow_subsurface = "BANK"

        elif material_id is MaterialId.COBBLE_DRY:
            self.category = "ROAD"
            self.road_surface = "COBBLE"
            self.cobble_type = "COBBLE"
            self.wetness = "DRY"
        elif material_id is MaterialId.COBBLE_DAMP:
            self.category = "ROAD"
            self.road_surface = "COBBLE"
            self.cobble_type = "COBBLE"
            self.wetness = "DAMP"
        elif material_id is MaterialId.COBBLE_WET:
            self.category = "ROAD"
            self.road_surface = "COBBLE"
            self.cobble_type = "COBBLE"
            self.wetness = "WET"
        elif material_id is MaterialId.SETT_DRY:
            self.category = "ROAD"
            self.road_surface = "COBBLE"
            self.cobble_type = "SETT"
            self.wetness = "DRY"
        elif material_id is MaterialId.SETT_DAMP:
            self.category = "ROAD"
            self.road_surface = "COBBLE"
            self.cobble_type = "SETT"
            self.wetness = "DAMP"
        elif material_id is MaterialId.SETT_WET:
            self.category = "ROAD"
            self.road_surface = "COBBLE"
            self.cobble_type = "SETT"
            self.wetness = "WET"

        elif material_id is MaterialId.WATER_SURFACE:
            self.category = "GROUND"
            self.ground_surface = "WATER"

        elif material_id is MaterialId.GRASS_HARD_DRY:
            self.category = "GROUND"
            self.ground_surface = "GRASS"
            self.hardness = "HARD"
            self.wetness = "DRY"
        elif material_id is MaterialId.GRASS_HARD_DAMP:
            self.category = "GROUND"
            self.ground_surface = "GRASS"
            self.hardness = "HARD"
            self.wetness = "DAMP"
        elif material_id is MaterialId.GRASS_HARD_WET:
            self.category = "GROUND"
            self.ground_surface = "GRASS"
            self.hardness = "HARD"
            self.wetness = "WET"
        elif material_id is MaterialId.GRASS_MEDIUM_DRY:
            self.category = "GROUND"
            self.ground_surface = "GRASS"
            self.hardness = "MEDIUM"
            self.wetness = "DRY"
        elif material_id is MaterialId.GRASS_MEDIUM_DAMP:
            self.category = "GROUND"
            self.ground_surface = "GRASS"
            self.hardness = "MEDIUM"
            self.wetness = "DAMP"
        elif material_id is MaterialId.GRASS_MEDIUM_WET:
            self.category = "GROUND"
            self.ground_surface = "GRASS"
            self.hardness = "MEDIUM"
            self.wetness = "WET"
        elif material_id is MaterialId.GRASS_SOFT_DRY:
            self.category = "GROUND"
            self.ground_surface = "GRASS"
            self.hardness = "SOFT"
            self.wetness = "DRY"
        elif material_id is MaterialId.GRASS_SOFT_DAMP:
            self.category = "GROUND"
            self.ground_surface = "GRASS"
            self.hardness = "SOFT"
            self.wetness = "DAMP"
        elif material_id is MaterialId.GRASS_SOFT_WET:
            self.category = "GROUND"
            self.ground_surface = "GRASS"
            self.hardness = "SOFT"
            self.wetness = "WET"

        elif material_id is MaterialId.ROUGH_ROUGH_DRY:
            self.category = "GROUND"
            self.ground_surface = "ROUGH"
            self.rough_type = "ROUGH"
            self.wetness = "DRY"
        elif material_id is MaterialId.ROUGH_ROUGH_WET:
            self.category = "GROUND"
            self.ground_surface = "ROUGH"
            self.rough_type = "ROUGH"
            self.wetness = "WET"
        elif material_id is MaterialId.ROUGH_ROUGH_DAMP:
            self.category = "GROUND"
            self.ground_surface = "ROUGH"
            self.rough_type = "ROUGH"
            self.wetness = "DAMP"
        elif material_id is MaterialId.ROUGH_VERYROUGH_DRY:
            self.category = "GROUND"
            self.ground_surface = "ROUGH"
            self.rough_type = "VERYROUGH"
            self.wetness = "DRY"
        elif material_id is MaterialId.ROUGH_VERYROUGH_WET:
            self.category = "GROUND"
            self.ground_surface = "ROUGH"
            self.rough_type = "VERYROUGH"
            self.wetness = "WET"
        elif material_id is MaterialId.ROUGH_VERYROUGH_DAMP:
            self.category = "GROUND"
            self.ground_surface = "ROUGH"
            self.rough_type = "VERYROUGH"
            self.wetness = "DAMP"

        elif material_id is MaterialId.DIRT_HARD_DRY:
            self.category = "GROUND"
            self.ground_surface = "DIRT"
            self.hardness = "HARD"
            self.wetness = "DRY"
        elif material_id is MaterialId.DIRT_HARD_DAMP:
            self.category = "GROUND"
            self.ground_surface = "DIRT"
            self.hardness = "HARD"
            self.wetness = "DAMP"
        elif material_id is MaterialId.DIRT_HARD_WET:
            self.category = "GROUND"
            self.ground_surface = "DIRT"
            self.hardness = "HARD"
            self.wetness = "WET"
        elif material_id is MaterialId.DIRT_MEDIUM_DRY:
            self.category = "GROUND"
            self.ground_surface = "DIRT"
            self.hardness = "MEDIUM"
            self.wetness = "DRY"
        elif material_id is MaterialId.DIRT_MEDIUM_DAMP:
            self.category = "GROUND"
            self.ground_surface = "DIRT"
            self.hardness = "MEDIUM"
            self.wetness = "DAMP"
        elif material_id is MaterialId.DIRT_MEDIUM_WET:
            self.category = "GROUND"
            self.ground_surface = "DIRT"
            self.hardness = "MEDIUM"
            self.wetness = "WET"
        elif material_id is MaterialId.DIRT_SOFT_DRY:
            self.category = "GROUND"
            self.ground_surface = "DIRT"
            self.hardness = "SOFT"
            self.wetness = "DRY"
        elif material_id is MaterialId.DIRT_SOFT_DAMP:
            self.category = "GROUND"
            self.ground_surface = "DIRT"
            self.hardness = "SOFT"
            self.wetness = "DAMP"
        elif material_id is MaterialId.DIRT_SOFT_WET:
            self.category = "GROUND"
            self.ground_surface = "DIRT"
            self.hardness = "SOFT"
            self.wetness = "WET"

        elif material_id is MaterialId.PASSTHROUGH:
            self.category = "PASSTHROUGH"

        else:
            return False
        return True

    def to_material_id(self) -> MaterialId:
        if self.category == "ROAD":
            if self.road_surface == "TARMAC":
                if self.tarmac_type == "FINE":
                    if self.tarmac_cleanliness == "CLEAN":
                        if self.wetness == "DRY":
                            return MaterialId.TARMAC_FINE_CLEAN_DRY
                        elif self.wetness == "DAMP":
                            return MaterialId.TARMAC_FINE_CLEAN_DAMP
                        elif self.wetness == "WET":
                            return MaterialId.TARMAC_FINE_CLEAN_WET
                    elif self.tarmac_cleanliness == "SPRINKLED":
                        if self.wetness == "DRY":
                            return MaterialId.TARMAC_FINE_SPRINKLED_DRY
                        elif self.wetness == "DAMP":
                            return MaterialId.TARMAC_FINE_SPRINKLED_DAMP
                        elif self.wetness == "WET":
                            return MaterialId.TARMAC_FINE_SPRINKLED_WET
                    elif self.tarmac_cleanliness == "COVERED":
                        if self.wetness == "DRY":
                            return MaterialId.TARMAC_FINE_COVERED_DRY
                        elif self.wetness == "DAMP":
                            return MaterialId.TARMAC_FINE_COVERED_DAMP
                        elif self.wetness == "WET":
                            return MaterialId.TARMAC_FINE_COVERED_WET
                elif self.tarmac_type == "MEDIUM":
                    if self.tarmac_cleanliness == "CLEAN":
                        if self.wetness == "DRY":
                            return MaterialId.TARMAC_MEDIUM_CLEAN_DRY
                        elif self.wetness == "DAMP":
                            return MaterialId.TARMAC_MEDIUM_CLEAN_DAMP
                        elif self.wetness == "WET":
                            return MaterialId.TARMAC_MEDIUM_CLEAN_WET
                    elif self.tarmac_cleanliness == "SPRINKLED":
                        if self.wetness == "DRY":
                            return MaterialId.TARMAC_MEDIUM_SPRINKLED_DRY
                        elif self.wetness == "DAMP":
                            return MaterialId.TARMAC_MEDIUM_SPRINKLED_DAMP
                        elif self.wetness == "WET":
                            return MaterialId.TARMAC_MEDIUM_SPRINKLED_WET
                    elif self.tarmac_cleanliness == "COVERED":
                        if self.wetness == "DRY":
                            return MaterialId.TARMAC_MEDIUM_COVERED_DRY
                        elif self.wetness == "DAMP":
                            return MaterialId.TARMAC_MEDIUM_COVERED_DAMP
                        elif self.wetness == "WET":
                            return MaterialId.TARMAC_MEDIUM_COVERED_WET
                elif self.tarmac_type == "COARSE":
                    if self.tarmac_cleanliness == "CLEAN":
                        if self.wetness == "DRY":
                            return MaterialId.TARMAC_COARSE_CLEAN_DRY
                        elif self.wetness == "DAMP":
                            return MaterialId.TARMAC_COARSE_CLEAN_DAMP
                        elif self.wetness == "WET":
                            return MaterialId.TARMAC_COARSE_CLEAN_WET
                    elif self.tarmac_cleanliness == "SPRINKLED":
                        if self.wetness == "DRY":
                            return MaterialId.TARMAC_COARSE_SPRINKLED_DRY
                        elif self.wetness == "DAMP":
                            return MaterialId.TARMAC_COARSE_SPRINKLED_DAMP
                        elif self.wetness == "WET":
                            return MaterialId.TARMAC_COARSE_SPRINKLED_WET
                    elif self.tarmac_cleanliness == "COVERED":
                        if self.wetness == "DRY":
                            return MaterialId.TARMAC_COARSE_COVERED_DRY
                        elif self.wetness == "DAMP":
                            return MaterialId.TARMAC_COARSE_COVERED_DAMP
                        elif self.wetness == "WET":
                            return MaterialId.TARMAC_COARSE_COVERED_WET
                elif self.tarmac_type == "BLACK_ICE":
                    return MaterialId.BLACK_ICE

            elif self.road_surface == "GRAVEL":
                if self.gravel_type == "US":
                    if self.gravel_depth == "SHALLOW":
                        if self.wetness == "DRY":
                            return MaterialId.US_GRAVEL_FINE_SHALLOW_DRY
                        elif self.wetness == "DAMP":
                            return MaterialId.US_GRAVEL_FINE_SHALLOW_DAMP
                        elif self.wetness == "WET":
                            return MaterialId.US_GRAVEL_FINE_SHALLOW_WET
                    elif self.gravel_depth == "DEEP":
                        if self.wetness == "DRY":
                            return MaterialId.US_GRAVEL_FINE_DEEP_DRY
                        elif self.wetness == "DAMP":
                            return MaterialId.US_GRAVEL_FINE_DEEP_DAMP
                        elif self.wetness == "WET":
                            return MaterialId.US_GRAVEL_FINE_DEEP_WET
                    elif self.gravel_depth == "DEEPER":
                        if self.wetness == "DRY":
                            return MaterialId.US_GRAVEL_FINE_DEEPER_DRY
                        elif self.wetness == "DAMP":
                            return MaterialId.US_GRAVEL_FINE_DEEPER_DAMP
                        elif self.wetness == "WET":
                            return MaterialId.US_GRAVEL_FINE_DEEPER_WET
                elif self.gravel_type == "FINE":
                    if self.gravel_depth == "SHALLOW":
                        if self.wetness == "DRY":
                            return MaterialId.GRAVEL_FINE_SHALLOW_DRY
                        elif self.wetness == "DAMP":
                            return MaterialId.GRAVEL_FINE_SHALLOW_DAMP
                        elif self.wetness == "WET":
                            return MaterialId.GRAVEL_FINE_SHALLOW_WET
                    elif self.gravel_depth == "DEEP":
                        if self.wetness == "DRY":
                            return MaterialId.GRAVEL_FINE_DEEP_DRY
                        elif self.wetness == "DAMP":
                            return MaterialId.GRAVEL_FINE_DEEP_DAMP
                        elif self.wetness == "WET":
                            return MaterialId.GRAVEL_FINE_DEEP_WET
                    elif self.gravel_depth == "DEEPER":
                        if self.wetness == "DRY":
                            return MaterialId.GRAVEL_FINE_DEEPER_DRY
                        elif self.wetness == "DAMP":
                            return MaterialId.GRAVEL_FINE_DEEPER_DAMP
                        elif self.wetness == "WET":
                            return MaterialId.GRAVEL_FINE_DEEPER_WET
                elif self.gravel_type == "MEDIUM":
                    if self.gravel_depth == "SHALLOW":
                        if self.wetness == "DRY":
                            return MaterialId.GRAVEL_MEDIUM_SHALLOW_DRY
                        elif self.wetness == "DAMP":
                            return MaterialId.GRAVEL_MEDIUM_SHALLOW_DAMP
                        elif self.wetness == "WET":
                            return MaterialId.GRAVEL_MEDIUM_SHALLOW_WET
                    elif self.gravel_depth == "DEEP":
                        if self.wetness == "DRY":
                            return MaterialId.GRAVEL_MEDIUM_DEEP_DRY
                        elif self.wetness == "DAMP":
                            return MaterialId.GRAVEL_MEDIUM_DEEP_DAMP
                        elif self.wetness == "WET":
                            return MaterialId.GRAVEL_MEDIUM_DEEP_WET
                    elif self.gravel_depth == "DEEPER":
                        if self.wetness == "DRY":
                            return MaterialId.GRAVEL_MEDIUM_DEEPER_DRY
                        elif self.wetness == "DAMP":
                            return MaterialId.GRAVEL_MEDIUM_DEEPER_DAMP
                        elif self.wetness == "WET":
                            return MaterialId.GRAVEL_MEDIUM_DEEPER_WET
                elif self.gravel_type == "COARSE":
                    if self.gravel_depth == "SHALLOW":
                        if self.wetness == "DRY":
                            return MaterialId.GRAVEL_COARSE_SHALLOW_DRY
                        elif self.wetness == "DAMP":
                            return MaterialId.GRAVEL_COARSE_SHALLOW_DAMP
                        elif self.wetness == "WET":
                            return MaterialId.GRAVEL_COARSE_SHALLOW_WET
                    elif self.gravel_depth == "DEEP":
                        if self.wetness == "DRY":
                            return MaterialId.GRAVEL_COARSE_DEEP_DRY
                        elif self.wetness == "DAMP":
                            return MaterialId.GRAVEL_COARSE_DEEP_DAMP
                        elif self.wetness == "WET":
                            return MaterialId.GRAVEL_COARSE_DEEP_WET
                    elif self.gravel_depth == "DEEPER":
                        if self.wetness == "DRY":
                            return MaterialId.GRAVEL_COARSE_DEEPER_DRY
                        elif self.wetness == "DAMP":
                            return MaterialId.GRAVEL_COARSE_DEEPER_DAMP
                        elif self.wetness == "WET":
                            return MaterialId.GRAVEL_COARSE_DEEPER_WET
                elif self.gravel_type == "BR":
                    if self.gravel_depth == "SHALLOW":
                        if self.wetness == "DRY":
                            return MaterialId.BR_GRAVEL_COARSE_SHALLOW_DRY
                        elif self.wetness == "DAMP":
                            return MaterialId.BR_GRAVEL_COARSE_SHALLOW_DAMP
                        elif self.wetness == "WET":
                            return MaterialId.BR_GRAVEL_COARSE_SHALLOW_WET
                    elif self.gravel_depth == "DEEP":
                        if self.wetness == "DRY":
                            return MaterialId.BR_GRAVEL_COARSE_DEEP_DRY
                        elif self.wetness == "DAMP":
                            return MaterialId.BR_GRAVEL_COARSE_DEEP_DAMP
                        elif self.wetness == "WET":
                            return MaterialId.BR_GRAVEL_COARSE_DEEP_WET
                    elif self.gravel_depth == "DEEPER":
                        if self.wetness == "DRY":
                            return MaterialId.BR_GRAVEL_COARSE_DEEPER_DRY
                        elif self.wetness == "DAMP":
                            return MaterialId.BR_GRAVEL_COARSE_DEEPER_DAMP
                        elif self.wetness == "WET":
                            return MaterialId.BR_GRAVEL_COARSE_DEEPER_WET

            elif self.road_surface == "SNOW":
                if self.snow_subsurface == "GRAVEL":
                    if self.snow_depth == "SHALLOW":
                        return MaterialId.SNOWONGRAVEL_SHALLOW
                    elif self.snow_depth == "MEDIUM":
                        return MaterialId.SNOWONGRAVEL_MEDIUM
                    elif self.snow_depth == "DEEP":
                        return MaterialId.SNOWONGRAVEL_DEEP
                elif self.snow_subsurface == "ICE":
                    if self.snow_depth == "SHALLOW":
                        return MaterialId.SNOWONICE_SHALLOW
                    elif self.snow_depth == "MEDIUM":
                        return MaterialId.SNOWONICE_MEDIUM
                    elif self.snow_depth == "DEEP":
                        return MaterialId.SNOWONICE_DEEP
                elif self.snow_subsurface == "BANK":
                    return MaterialId.SNOWWALL_BOTTOM

            elif self.road_surface == "COBBLE":
                if self.cobble_type == "COBBLE":
                    if self.wetness == "DRY":
                        return MaterialId.COBBLE_DRY
                    elif self.wetness == "DAMP":
                        return MaterialId.COBBLE_DAMP
                    elif self.wetness == "WET":
                        return MaterialId.COBBLE_WET
                elif self.cobble_type == "SETT":
                    if self.wetness == "DRY":
                        return MaterialId.SETT_DRY
                    elif self.wetness == "DAMP":
                        return MaterialId.SETT_DAMP
                    elif self.wetness == "WET":
                        return MaterialId.SETT_WET

        elif self.category == "GROUND":
            if self.ground_surface == "WATER":
                return MaterialId.WATER_SURFACE
            elif self.ground_surface == "GRASS":
                if self.hardness == "HARD":
                    if self.wetness == "DRY":
                        return MaterialId.GRASS_HARD_DRY
                    if self.wetness == "DAMP":
                        return MaterialId.GRASS_HARD_DAMP
                    if self.wetness == "WET":
                        return MaterialId.GRASS_HARD_WET
                elif self.hardness == "MEDIUM":
                    if self.wetness == "DRY":
                        return MaterialId.GRASS_MEDIUM_DRY
                    if self.wetness == "DAMP":
                        return MaterialId.GRASS_MEDIUM_DAMP
                    if self.wetness == "WET":
                        return MaterialId.GRASS_MEDIUM_WET
                elif self.hardness == "SOFT":
                    if self.wetness == "DRY":
                        return MaterialId.GRASS_SOFT_DRY
                    if self.wetness == "DAMP":
                        return MaterialId.GRASS_SOFT_DAMP
                    if self.wetness == "WET":
                        return MaterialId.GRASS_SOFT_WET
            elif self.ground_surface == "ROUGH":
                if self.rough_type == "ROUGH":
                    if self.wetness == "DRY":
                        return MaterialId.ROUGH_ROUGH_DRY
                    elif self.wetness == "WET":
                        return MaterialId.ROUGH_ROUGH_WET
                    elif self.wetness == "DAMP":
                        return MaterialId.ROUGH_ROUGH_DAMP
                elif self.rough_type == "VERYROUGH":
                    if self.wetness == "DRY":
                        return MaterialId.ROUGH_VERYROUGH_DRY
                    elif self.wetness == "WET":
                        return MaterialId.ROUGH_VERYROUGH_WET
                    elif self.wetness == "DAMP":
                        return MaterialId.ROUGH_VERYROUGH_DAMP
            elif self.ground_surface == "DIRT":
                if self.hardness == "HARD":
                    if self.wetness == "DRY":
                        return MaterialId.DIRT_HARD_DRY
                    if self.wetness == "DAMP":
                        return MaterialId.DIRT_HARD_DAMP
                    if self.wetness == "WET":
                        return MaterialId.DIRT_HARD_WET
                elif self.hardness == "MEDIUM":
                    if self.wetness == "DRY":
                        return MaterialId.DIRT_MEDIUM_DRY
                    if self.wetness == "DAMP":
                        return MaterialId.DIRT_MEDIUM_DAMP
                    if self.wetness == "WET":
                        return MaterialId.DIRT_MEDIUM_WET
                elif self.hardness == "SOFT":
                    if self.wetness == "DRY":
                        return MaterialId.DIRT_SOFT_DRY
                    if self.wetness == "DAMP":
                        return MaterialId.DIRT_SOFT_DAMP
                    if self.wetness == "WET":
                        return MaterialId.DIRT_SOFT_WET

        elif self.category == "PASSTHROUGH":
            return MaterialId.PASSTHROUGH

        raise NotImplementedError


class RBRPropertyNodePointer(bpy.types.PropertyGroup):
    """This PropertyGroup can point at a particular node in a material.
    It's necessary because from a node's draw context we can't detect the material directly.
    We instead use the node tree pointer to identify the material.
    """

    node_name: bpy.props.StringProperty()  # type: ignore
    # String instead of Int, IntProperty can overflow.
    nodetree_pointer: bpy.props.StringProperty()  # type: ignore

    def get_shader_node(self) -> Optional[bpy.types.ShaderNode]:
        found_tree = None
        # Look for the node tree matching the pointer. Can't use name equality,
        # since node trees in different materials can have the same name!
        # We can't actually use the pointer as a pointer, blender crashes. Not
        # sure what the problem is, but this loop is fast enough.
        for material in bpy.data.materials:
            if material.use_nodes and material.node_tree is not None:
                if str(material.node_tree.as_pointer()) == self.nodetree_pointer:
                    found_tree = material.node_tree
                    break
        if found_tree is None:
            return None
        node = found_tree.nodes.get(self.node_name)
        return node if isinstance(node, bpy.types.ShaderNode) else None


class RBRMaterialId(bpy.types.PropertyGroup):
    material_id: bpy.props.IntProperty()  # type: ignore

    def to_material(self) -> MaterialId:
        return MaterialId(self.material_id)


class RBRMaterialMapRow(bpy.types.PropertyGroup):
    cols: bpy.props.CollectionProperty(  # type: ignore
        type=RBRMaterialId,
    )

    def _init(self) -> None:
        for _ in range(16):
            self.cols.add()


class RBRMaterialMap(bpy.types.PropertyGroup):
    """An individual material map. This is a direct encoding of the normal
    MaterialMap class, as blender properties, so they can be saved in blend
    files."""

    rows: bpy.props.CollectionProperty(  # type: ignore
        type=RBRMaterialMapRow,
    )

    def _init(self) -> None:
        for _ in range(16):
            row = self.rows.add()
            row._init()

    def set_from_format(self, mat: MaterialMap) -> None:
        """Set this blender property based material map from a plain material
        map
        """
        self.rows.clear()
        for mat_row in mat.bitmap:
            row = self.rows.add()
            for mat_id in mat_row:
                col = row.cols.add()
                col.material_id = mat_id.value

    def to_format(self) -> MaterialMap:
        """Convert this blender property based material map into a plain
        material map
        """
        rows: List[List[MaterialId]] = []
        for mat_row in self.rows:
            cols = []
            for mat_id in mat_row.cols:
                cols.append(mat_id.to_material())
            rows.append(cols)
        return MaterialMap(bitmap=rows)


class RBRMaterialMaps(bpy.types.PropertyGroup):
    """A collection of material maps, one for each surface type/wear
    combination. This also controls the corner positions of all maps.
    """

    # Position of one corner in UV coordinates
    # This is the bottom left of the viewport
    position_1: bpy.props.FloatVectorProperty(size=2)  # type: ignore
    # Position of opposite corner in UV coordinates
    # This is the top right of the viewport
    # Invariant: both X and Y coordinates are higher than X and Y coordinates of
    # position_1. This way the maps are always the same way up, and copying and
    # pasting between them works properly.
    position_2: bpy.props.FloatVectorProperty(size=2)  # type: ignore
    maps: bpy.props.CollectionProperty(  # type: ignore
        type=RBRMaterialMap,
    )

    repeat_x: bpy.props.BoolProperty()  # type: ignore
    repeat_y: bpy.props.BoolProperty()  # type: ignore

    def _init(self) -> None:
        for _ in range(9):
            m = self.maps.add()
            m._init()
        self.maintain_position_invariant()

    # 'other' has type RBRMaterialMaps, but we can't specify that here without
    # from __future__ import annotations, and that breaks PropertyGroup
    # definitions. See CONTRIBUTING.md.
    def copy(self, other: Any) -> None:
        self.position_1 = other.position_1
        self.position_2 = other.position_2
        self.repeat_x = other.repeat_x
        self.repeat_y = other.repeat_y
        self.maps.clear()
        for other_map in other.maps:
            map = self.maps.add()
            map.set_from_format(other_map.to_format())

    def maintain_position_invariant(self) -> Tuple[bool, bool]:
        """Maintain the position invariant (see comment by position
        definitions)"""
        p1x, p1y = self.position_1
        p2x, p2y = self.position_2
        flip_x = p1x > p2x
        flip_y = p1y > p2y
        if flip_x:
            self.position_1[0] = p2x
            self.position_2[0] = p1x
        if flip_y:
            self.position_1[1] = p2y
            self.position_2[1] = p1y
        # Fix positions if this map is marked as repeated
        if self.repeat_x:
            self.position_1[0] = 0.0
            self.position_2[0] = 1.0
        if self.repeat_y:
            self.position_1[1] = 0.0
            self.position_2[1] = 1.0
        return (flip_x, flip_y)

    def update_mat_pos(
        self, handle: GrabHandle, mouse_pos: Vector
    ) -> Optional[GrabHandle]:
        """Update the material position using a grab handle, and possibly return
        a new grab handle. The returned grab handle is present when the map gets
        flipped in an axis, to make sure maps are always the same way up."""
        if handle == GrabHandle.BOTTOM_LEFT:
            self.position_1[0] = mouse_pos.x
            self.position_1[1] = mouse_pos.y
        elif handle == GrabHandle.BOTTOM_MID:
            self.position_1[1] = mouse_pos.y
        elif handle == GrabHandle.BOTTOM_RIGHT:
            self.position_2[0] = mouse_pos.x
            self.position_1[1] = mouse_pos.y
        elif handle == GrabHandle.MID_LEFT:
            self.position_1[0] = mouse_pos.x
        elif handle == GrabHandle.MID_RIGHT:
            self.position_2[0] = mouse_pos.x
        elif handle == GrabHandle.TOP_LEFT:
            self.position_1[0] = mouse_pos.x
            self.position_2[1] = mouse_pos.y
        elif handle == GrabHandle.TOP_MID:
            self.position_2[1] = mouse_pos.y
        elif handle == GrabHandle.TOP_RIGHT:
            self.position_2[0] = mouse_pos.x
            self.position_2[1] = mouse_pos.y
        flip_x, flip_y = self.maintain_position_invariant()
        return handle.flip(flip_x, flip_y)

    def drag(self, delta: Vector) -> None:
        self.position_1[0] += delta.x
        self.position_1[1] += delta.y
        self.position_2[0] += delta.x
        self.position_2[1] += delta.y
        self.maintain_position_invariant()

    def get_map(
        self, surface_type: SurfaceType, surface_age: SurfaceAge
    ) -> RBRMaterialMap:
        cond = ConditionIdentifier(surface_type=surface_type, surface_age=surface_age)
        m: RBRMaterialMap = self.maps[cond.packed_index()]
        return m

    def get_active_map(self) -> RBRMaterialMap:
        from ..shaders.texture import ShaderNodeRBRTextureInternal

        if bpy.context.scene is None:
            raise RuntimeError("No active scene")
        surface_type = bpy.context.scene.rbr_scene_settings.get_active_surface_type()
        # Walk to the highest parent node tree (ShaderNodeRBRTexture) and get
        # the internal data
        node_tree = self.id_data
        if not isinstance(node_tree, bpy.types.NodeTree):
            raise RuntimeError("Expected a node tree")
        internal = narrow(node_tree.nodes["internal"], ShaderNodeRBRTextureInternal)
        is_road_surface = internal.is_road_surface
        if is_road_surface:
            surface_age = bpy.context.scene.rbr_scene_settings.get_active_surface_age()
        else:
            surface_age = SurfaceAge.NEW
        return self.get_map(surface_type, surface_age)

    def uv_to_mat(self, pos: Vector) -> Vector:
        """From UV space (view space) to material space"""
        x, y = pos.to_tuple()
        x0, y0 = self.position_1
        x1, y1 = self.position_2
        dx = x1 - x0
        dy = y1 - y0
        if dx != 0:
            mat_x = (x - x0) / dx
        else:
            mat_x = 0
        if dy != 0:
            mat_y = (y - y0) / dy
        else:
            mat_y = 0
        return Vector((mat_x, mat_y))

    def quantized_uv(self, uv_x: float, uv_y: float) -> Tuple[int, int]:
        """Given UV coordinates in texture UV space, return the RBR collision
        material quantized UV coordinates, pre swapped. This is not quite the
        same as the x,y pixel: there are 16 pixels in a given direction, but
        also only 16 distinct UV points (which need to represent the left side
        of the leftmost pixel, and the right side of the rightmost pixel, and if
        this was treated the same way as the pixel calculation, we'd need 17
        distinct points)."""
        mat = self.uv_to_mat(Vector((uv_x, uv_y)))

        def clamp(a: float) -> int:
            return max(0, min(15, round(a * 15)))

        return (clamp(mat.y), clamp(mat.x))

    def pixel(self, uv_x: float, uv_y: float) -> Tuple[int, int]:
        """Find the x,y coordinates of the pixel containing the given UV
        coordinates"""
        mat = self.uv_to_mat(Vector((uv_x, uv_y)))

        def clamp(a: float) -> int:
            return max(0, min(15, math.floor(a * 16)))

        return (clamp(mat.x), clamp(mat.y))

    def point_in_map(self, px: int, py: int) -> bool:
        return point_in_area(Vector((px, py)), self.position_1, self.position_2)


class RBRFallbackMaterials(bpy.types.PropertyGroup):
    dry_new: bpy.props.PointerProperty(type=RBRMaterialId)  # type: ignore
    damp_new: bpy.props.PointerProperty(type=RBRMaterialId)  # type: ignore
    wet_new: bpy.props.PointerProperty(type=RBRMaterialId)  # type: ignore
    dry_normal: bpy.props.PointerProperty(type=RBRMaterialId)  # type: ignore
    damp_normal: bpy.props.PointerProperty(type=RBRMaterialId)  # type: ignore
    wet_normal: bpy.props.PointerProperty(type=RBRMaterialId)  # type: ignore
    dry_worn: bpy.props.PointerProperty(type=RBRMaterialId)  # type: ignore
    damp_worn: bpy.props.PointerProperty(type=RBRMaterialId)  # type: ignore
    wet_worn: bpy.props.PointerProperty(type=RBRMaterialId)  # type: ignore

    def active_material(self) -> MaterialId:
        if bpy.context.scene is None:
            raise RuntimeError("No active scene")
        track_settings = bpy.context.scene.rbr_scene_settings
        surface_type: SurfaceType = track_settings.get_active_surface_type()
        surface_age: SurfaceAge = track_settings.get_active_surface_age()
        return self.get_condition(surface_type, surface_age)

    def get_condition(
        self, surface_type: SurfaceType, surface_age: SurfaceAge
    ) -> MaterialId:
        if surface_type is SurfaceType.DRY and surface_age is SurfaceAge.NEW:
            return narrow(self.dry_new.to_material(), MaterialId)
        elif surface_type is SurfaceType.DRY and surface_age is SurfaceAge.NORMAL:
            return narrow(self.dry_normal.to_material(), MaterialId)
        elif surface_type is SurfaceType.DRY and surface_age is SurfaceAge.WORN:
            return narrow(self.dry_worn.to_material(), MaterialId)
        elif surface_type is SurfaceType.DAMP and surface_age is SurfaceAge.NEW:
            return narrow(self.damp_new.to_material(), MaterialId)
        elif surface_type is SurfaceType.DAMP and surface_age is SurfaceAge.NORMAL:
            return narrow(self.damp_normal.to_material(), MaterialId)
        elif surface_type is SurfaceType.DAMP and surface_age is SurfaceAge.WORN:
            return narrow(self.damp_worn.to_material(), MaterialId)
        elif surface_type is SurfaceType.WET and surface_age is SurfaceAge.NEW:
            return narrow(self.wet_new.to_material(), MaterialId)
        elif surface_type is SurfaceType.WET and surface_age is SurfaceAge.NORMAL:
            return narrow(self.wet_normal.to_material(), MaterialId)
        elif surface_type is SurfaceType.WET and surface_age is SurfaceAge.WORN:
            return narrow(self.wet_worn.to_material(), MaterialId)
        else:
            raise RuntimeError(
                f"Unhandled type/age in active_material: {surface_type} {surface_age}"
            )

    def set_from_active(self, picker: RBRMaterialPicker) -> None:
        if bpy.context.scene is None:
            return
        paint_material = picker.material_id
        track_settings = bpy.context.scene.rbr_scene_settings
        surface_type: SurfaceType = track_settings.get_active_surface_type()
        surface_age: SurfaceAge = track_settings.get_active_surface_age()
        if surface_type is SurfaceType.DRY and surface_age is SurfaceAge.NEW:
            self.dry_new.material_id = paint_material
        elif surface_type is SurfaceType.DRY and surface_age is SurfaceAge.NORMAL:
            self.dry_normal.material_id = paint_material
        elif surface_type is SurfaceType.DRY and surface_age is SurfaceAge.WORN:
            self.dry_worn.material_id = paint_material
        elif surface_type is SurfaceType.DAMP and surface_age is SurfaceAge.NEW:
            self.damp_new.material_id = paint_material
        elif surface_type is SurfaceType.DAMP and surface_age is SurfaceAge.NORMAL:
            self.damp_normal.material_id = paint_material
        elif surface_type is SurfaceType.DAMP and surface_age is SurfaceAge.WORN:
            self.damp_worn.material_id = paint_material
        elif surface_type is SurfaceType.WET and surface_age is SurfaceAge.NEW:
            self.wet_new.material_id = paint_material
        elif surface_type is SurfaceType.WET and surface_age is SurfaceAge.NORMAL:
            self.wet_normal.material_id = paint_material
        elif surface_type is SurfaceType.WET and surface_age is SurfaceAge.WORN:
            self.wet_worn.material_id = paint_material


WETTER_CONDITIONS = ((SurfaceType.DAMP, 1), (SurfaceType.WET, 2))


def derive_map(source: RBRMaterialMap, target: RBRMaterialMap, steps: int) -> None:
    wetter: dict[int, int] = {}
    for source_row, target_row in zip(source.rows, target.rows):
        for source_col, target_col in zip(source_row.cols, target_row.cols):
            value = source_col.material_id
            derived = wetter.get(value)
            if derived is None:
                derived = MaterialId(value).wetter(steps).value
                wetter[value] = derived
            if target_col.material_id != derived:
                target_col.material_id = derived


def _sync_auto_wetness(self: Any, context: bpy.types.Context) -> None:
    self.sync()


def _auto_wetness_prop(surface_type: SurfaceType, age: SurfaceAge) -> Any:
    return bpy.props.BoolProperty(
        name=f"{surface_type.pretty()}/{age.pretty()}",
        description=f"Derive the {surface_type.to_string()}/{age.to_string()} maps and fallback from dry/{age.to_string()}",
        default=False,
        options=set(),
        update=_sync_auto_wetness,
    )


class RBRAutoWetness(bpy.types.PropertyGroup):
    """Which damp/wet conditions are derived from the dry condition of the same
    age, by making each material one (damp) or two (wet) steps wetter."""

    damp_new: _auto_wetness_prop(SurfaceType.DAMP, SurfaceAge.NEW)  # type: ignore
    damp_normal: _auto_wetness_prop(SurfaceType.DAMP, SurfaceAge.NORMAL)  # type: ignore
    damp_worn: _auto_wetness_prop(SurfaceType.DAMP, SurfaceAge.WORN)  # type: ignore
    wet_new: _auto_wetness_prop(SurfaceType.WET, SurfaceAge.NEW)  # type: ignore
    wet_normal: _auto_wetness_prop(SurfaceType.WET, SurfaceAge.NORMAL)  # type: ignore
    wet_worn: _auto_wetness_prop(SurfaceType.WET, SurfaceAge.WORN)  # type: ignore

    @staticmethod
    def prop_name(surface_type: SurfaceType, surface_age: SurfaceAge) -> str:
        return f"{surface_type.to_string()}_{surface_age.to_string()}"

    def is_auto(self, surface_type: SurfaceType, surface_age: SurfaceAge) -> bool:
        if surface_type is SurfaceType.DRY:
            return False
        return bool(getattr(self, self.prop_name(surface_type, surface_age)))

    def set_auto(
        self, surface_type: SurfaceType, surface_age: SurfaceAge, value: bool
    ) -> None:
        if surface_type is not SurfaceType.DRY:
            setattr(self, self.prop_name(surface_type, surface_age), value)

    def set_all(self, value: bool) -> None:
        for surface_type, _ in WETTER_CONDITIONS:
            for age in SurfaceAge:
                self.set_auto(surface_type, age, value)

    # 'other' has type RBRAutoWetness, see RBRMaterialMaps.copy.
    def copy(self, other: Any) -> None:
        for surface_type, _ in WETTER_CONDITIONS:
            for age in SurfaceAge:
                self.set_auto(surface_type, age, other.is_auto(surface_type, age))

    def sync(
        self, surface_age: Optional[SurfaceAge] = None, region: Optional[int] = None
    ) -> None:
        """Re-derive the automatic conditions, optionally only those of one age
        or one region."""
        from .editor import invalidate

        invalidate()
        node_tree = self.id_data
        if not isinstance(node_tree, bpy.types.NodeTree):
            return
        internal: Any = node_tree.nodes.get("internal")
        if internal is None:
            return
        ages = list(SurfaceAge) if internal.is_road_surface else [SurfaceAge.NEW]
        if surface_age is not None:
            ages = [age for age in ages if age is surface_age]
        regions = internal.material_maps
        if region is not None:
            regions = [regions[region]] if region < len(regions) else []
        fallbacks: RBRFallbackMaterials = internal.fallback_materials
        for surface_type, steps in WETTER_CONDITIONS:
            for age in ages:
                if not self.is_auto(surface_type, age):
                    continue
                for maps in regions:
                    derive_map(
                        maps.get_map(SurfaceType.DRY, age),
                        maps.get_map(surface_type, age),
                        steps,
                    )
                derived = fallbacks.get_condition(SurfaceType.DRY, age).wetter(steps)
                target = getattr(fallbacks, self.prop_name(surface_type, age))
                if target.material_id != derived.value:
                    target.material_id = derived.value


def register() -> None:
    bpy.utils.register_class(RBRMaterialPicker)
    bpy.utils.register_class(RBRPropertyNodePointer)
    bpy.utils.register_class(RBRMaterialId)
    bpy.utils.register_class(RBRMaterialMapRow)
    bpy.utils.register_class(RBRMaterialMap)
    bpy.utils.register_class(RBRMaterialMaps)
    bpy.utils.register_class(RBRFallbackMaterials)
    bpy.utils.register_class(RBRAutoWetness)


def unregister() -> None:
    bpy.utils.unregister_class(RBRAutoWetness)
    bpy.utils.unregister_class(RBRFallbackMaterials)
    bpy.utils.unregister_class(RBRMaterialMaps)
    bpy.utils.unregister_class(RBRMaterialMap)
    bpy.utils.unregister_class(RBRMaterialMapRow)
    bpy.utils.unregister_class(RBRMaterialId)
    bpy.utils.unregister_class(RBRPropertyNodePointer)
    bpy.utils.unregister_class(RBRMaterialPicker)
