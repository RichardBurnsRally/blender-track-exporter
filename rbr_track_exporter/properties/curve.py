import enum
import math
from dataclasses import dataclass
from typing import List, Optional, Set

import bpy
from ..types import OperatorReturn

from ..blender_utils import Checks, narrow
from .fence import RBRFenceSettings, collect_objects, get_or_create_fence_modifier


class RBRCurveType(enum.Enum):
    NONE = 0x0
    FENCE = 0x1

    def pretty(self) -> str:
        if self is RBRCurveType.NONE:
            return "None"
        elif self is RBRCurveType.FENCE:
            return "Fence"
        raise NotImplementedError(self)

    def description(self) -> str:
        if self is RBRCurveType.NONE:
            return ""
        elif self is RBRCurveType.FENCE:
            return "Interactive tape fence"
        raise NotImplementedError(self)


@dataclass
class DrivelineObjects:
    spline: Optional[bpy.types.Spline]
    zfar: bpy.types.Object


def detect_zfar(driveline_obj: bpy.types.Object) -> Optional[bpy.types.Object]:
    for child in driveline_obj.children:
        if child.data is not None:
            continue
        if child.empty_display_type != "CIRCLE":
            continue
        return child
    return None


def fixup_zfar(
    driveline_obj: bpy.types.Object,
) -> bpy.types.Object:
    zfar_obj = detect_zfar(driveline_obj)
    if zfar_obj is None:
        zfar_obj = bpy.data.objects.new("render-distance", None)
        if bpy.context.scene is None:
            raise RuntimeError("No active scene")
        bpy.context.scene.collection.objects.link(zfar_obj)
        zfar_obj.empty_display_size = 300
        zfar_obj.parent = driveline_obj
    zfar_obj.show_in_front = True
    zfar_obj.empty_display_type = "CIRCLE"
    zfar_obj.location = [0, 0, 0]
    zfar_obj.lock_location[:] = [True, True, True]
    zfar_obj.lock_rotation[:] = [True, True, True]
    zfar_obj.rotation_euler = [math.pi / 2.0, 0, 0]
    s = zfar_obj.scale.x
    zfar_obj.scale = [s, s, s]
    return zfar_obj


def fixup_driveline_obj(obj: bpy.types.Object) -> Optional[DrivelineObjects]:
    obj.scale = [1, 1, 1]
    obj.lock_scale[:] = [True, True, True]
    zfar = fixup_zfar(obj)
    if isinstance(obj.data, bpy.types.Curve):
        curve = obj.data
        spline = fixup_driveline_splines(curve)
        curve.dimensions = "3D"
        curve.twist_mode = "Z_UP"
        # Make sure we are animating the path, for any child objects
        curve.use_path = True
        curve.use_path_clamp = True
        fcurve = curve.driver_add("eval_time")
        if not isinstance(fcurve, bpy.types.FCurve):
            raise RuntimeError("Expected a single FCurve from driver_add")
        for modifier in fcurve.modifiers.values():
            fcurve.modifiers.remove(narrow(modifier, bpy.types.FModifier))
        if fcurve.driver is None:
            raise RuntimeError("FCurve has no driver")
        fcurve.driver.expression = "frame"
        if spline is not None:
            length = spline.calc_length(resolution=16)
            curve.path_duration = int(length)
        return DrivelineObjects(spline=spline, zfar=zfar)
    return None


def fixup_driveline_splines(
    curve: bpy.types.Curve,
) -> Optional[bpy.types.Spline]:
    """Fixup driveline spline where possible"""
    # Find longest spline
    longest_spline = None
    longest_length = 0.0
    for this_spline in curve.splines:
        this_length = this_spline.calc_length(resolution=8)
        if this_length > longest_length:
            longest_length = this_length
            longest_spline = this_spline
    # Delete the other splines
    for spline in curve.splines:
        if spline != longest_spline:
            curve.splines.remove(spline)
    # Make it non-cyclic
    if longest_spline is not None:
        longest_spline.type = "BEZIER"
        longest_spline.use_cyclic_u = False
    return longest_spline


def check_driveline_validity(
    obj: bpy.types.Object,
) -> Checks:
    errors = []
    if obj.scale.x != 1 or obj.scale.y != 1 or obj.scale.z != 1:
        errors.append("Scale must be 1")
    if not isinstance(obj.data, bpy.types.Curve):
        errors.append("Must be a curve object")
    elif len(obj.data.splines) == 0:
        errors.append("Must have a single spline")
    elif obj.data.splines[0].type != "BEZIER":
        errors.append("Must be a bezier spline")
    return Checks(errors=errors)


def fixup_brake_wall_object(obj: bpy.types.Object) -> Optional[bpy.types.Spline]:
    obj.scale = [1, 1, 1]
    obj.lock_scale[:] = [True, True, True]
    if isinstance(obj.data, bpy.types.Curve):
        curve = obj.data
        spline = fixup_brake_wall_splines(curve)
        curve.dimensions = "3D"
        curve.twist_mode = "Z_UP"
        return spline
    return None


def fixup_brake_wall_splines(
    curve: bpy.types.Curve,
) -> Optional[bpy.types.Spline]:
    """Fixup brake wall spline where possible"""
    # Find longest spline
    longest_spline = None
    longest_length = 0.0
    for this_spline in curve.splines:
        this_length = this_spline.calc_length(resolution=8)
        if this_length > longest_length:
            longest_length = this_length
            longest_spline = this_spline
    # Delete the other splines
    for spline in curve.splines:
        if spline != longest_spline:
            curve.splines.remove(spline)
    # Make it cyclic and a poly spline
    if longest_spline is not None:
        if longest_spline.type != "POLY":
            longest_spline.type = "POLY"
        longest_spline.use_cyclic_u = True
    return longest_spline


class RBR_OT_remove_pacenote(bpy.types.Operator):
    """Remove a pacenote from a driveline object"""

    bl_idname = "rbr.remove_pacenote"
    bl_label = "Remove pacenote"
    bl_description = "Remove pacenote from the stack"
    bl_options = {"UNDO"}

    index: bpy.props.IntProperty()  # type: ignore

    @classmethod
    def poll(cls, context: bpy.types.Context) -> bool:
        obj = context.active_object
        if obj is None or context.scene is None:
            return False
        if not isinstance(obj.data, bpy.types.Curve):
            return False
        # TODO make this typed
        driveline = context.scene.rbr_scene_settings.driveline
        return bool(driveline == obj)

    def execute(self, context: bpy.types.Context) -> OperatorReturn:
        return self.invoke(context, None)

    def invoke(
        self, context: bpy.types.Context, event: Optional[bpy.types.Event]
    ) -> OperatorReturn:
        obj = context.active_object
        if obj is None or not isinstance(obj.data, bpy.types.Curve):
            return {"CANCELLED"}
        curve: RBRCurveSettings = obj.data.rbr_curve_settings
        curve.pacenotes.remove(self.index)
        curve.update_sorted_pacenotes()
        return {"FINISHED"}


class RBR_OT_add_pacenote(bpy.types.Operator):
    """Add a pacenote to a driveline object"""

    bl_idname = "rbr.add_pacenote"
    bl_label = "Add pacenote"
    bl_description = "Add a pacenote to the stack"
    bl_options = {"UNDO"}

    @classmethod
    def poll(cls, context: bpy.types.Context) -> bool:
        return RBR_OT_remove_pacenote.poll(context)

    def execute(self, context: bpy.types.Context) -> OperatorReturn:
        return self.invoke(context, None)

    def invoke(
        self, context: bpy.types.Context, event: Optional[bpy.types.Event]
    ) -> OperatorReturn:
        obj = context.active_object
        if obj is None or not isinstance(obj.data, bpy.types.Curve):
            return {"CANCELLED"}
        curve: RBRCurveSettings = obj.data.rbr_curve_settings
        pacenote = curve.pacenotes.add()
        pacenote.location = max(map(lambda p: p.location, curve.pacenotes))
        curve.update_sorted_pacenotes()
        return {"FINISHED"}


class RBRPacenoteDefinition(bpy.types.PropertyGroup):
    def update(self, context: bpy.types.Context) -> None:
        if isinstance(self.id_data, bpy.types.Curve):
            curve: RBRCurveSettings = self.id_data.rbr_curve_settings
            curve.update_sorted_pacenotes()

    location: bpy.props.FloatProperty(  # type: ignore
        name="Location",  # noqa: F821
        min=0,
        max=100000,
        update=update,
    )

    flags: bpy.props.IntProperty(  # type: ignore
        name="Flags",
        subtype="UNSIGNED",
        min=0,
    )

    pacenote_id: bpy.props.IntProperty(  # type: ignore
        name="Pacenote",
        subtype="UNSIGNED",
        min=0,
    )


class RBRCurveSettings(bpy.types.PropertyGroup):
    def _update_curve_type(self, context: bpy.types.Context) -> None:
        curve_type = RBRCurveType[str(self.curve_type)]
        if curve_type is RBRCurveType.FENCE:
            objs = collect_objects(self.id_data)
            for obj in objs:
                get_or_create_fence_modifier(obj, self.fence)
        else:
            return

    curve_type: bpy.props.EnumProperty(  # type: ignore
        items=[(t.name, t.pretty(), t.description(), t.value) for t in RBRCurveType],
        name="Curve Type",
        default=RBRCurveType.NONE.name,
        update=_update_curve_type,
    )

    fence: bpy.props.PointerProperty(  # type: ignore
        type=RBRFenceSettings,
    )

    # We maintain a list of sorted pacenotes so we don't have to compute it
    # every frame
    def get_sorted_pacenote_indices(self) -> List[int]:
        if "_sorted_pacenote_indices" in self:
            return list(self["_sorted_pacenote_indices"])
        else:
            return []

    def update_sorted_pacenotes(self) -> None:
        self["_sorted_pacenote_indices"] = list(
            map(
                lambda t: t[0],
                sorted(enumerate(self.pacenotes), key=lambda t: t[1].location),
            )
        )

    def update_render_distance_scale(self, context: bpy.types.Context) -> None:
        objs = []
        for obj in bpy.data.objects:
            if obj.data == self.id_data:
                objs.append(obj)
        for obj in objs:
            driveline = fixup_driveline_obj(obj)
            if driveline is not None:
                s = self.render_distance_scale
                driveline.zfar.scale = [s, s, s]

    render_distance_scale: bpy.props.FloatProperty(  # type: ignore
        name="Render Distance Scale",
        description="Multiplier for the render distance, only required if the 1000m blender limit is too small",
        default=1,
        min=1,
        soft_max=3,
        update=update_render_distance_scale,
    )

    alpha_far: bpy.props.FloatProperty(  # type: ignore
        name="Viewport Distance",
        description="Blender viewport visible distance",
        min=1e3,
        default=3e3,
        max=2e4,
    )

    event_start: bpy.props.FloatProperty(  # type: ignore
        name="Start",
    )
    event_split_1: bpy.props.FloatProperty(  # type: ignore
        name="Split 1",
    )
    event_split_2: bpy.props.FloatProperty(  # type: ignore
        name="Split 2",
    )
    event_finish: bpy.props.FloatProperty(  # type: ignore
        name="Finish",
    )
    event_end_of_stage: bpy.props.FloatProperty(  # type: ignore
        name="End of Stage",
    )
    pacenotes: bpy.props.CollectionProperty(  # type: ignore
        type=RBRPacenoteDefinition,
        name="Pacenotes",  # noqa: F821
    )


def register() -> None:
    bpy.utils.register_class(RBRPacenoteDefinition)
    bpy.utils.register_class(RBRCurveSettings)
    bpy.types.Curve.rbr_curve_settings = bpy.props.PointerProperty(
        type=RBRCurveSettings,
    )
    bpy.utils.register_class(RBR_OT_remove_pacenote)
    bpy.utils.register_class(RBR_OT_add_pacenote)


def unregister() -> None:
    bpy.utils.unregister_class(RBR_OT_add_pacenote)
    bpy.utils.unregister_class(RBR_OT_remove_pacenote)
    del bpy.types.Curve.rbr_curve_settings
    bpy.utils.unregister_class(RBRCurveSettings)
    bpy.utils.unregister_class(RBRPacenoteDefinition)
