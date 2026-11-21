import bpy
from ..blender_utils import narrow

from .curve import fixup_driveline_obj
from .scene import RBRSceneSettings


class RBRCameraSettings(bpy.types.PropertyGroup):
    def update_look_at_car(self, context: bpy.types.Context) -> None:
        objs = []
        for obj in bpy.data.objects:
            if obj.data == self.id_data:
                objs.append(obj)
        for obj in objs:
            # Remove existing tracking constraints
            for constraint in obj.constraints:
                if constraint.type == "TRACK_TO":
                    obj.constraints.remove(constraint)
            if not self.look_at_car:
                return
            if context.scene is None:
                return
            rbr_scene_settings: RBRSceneSettings = context.scene.rbr_scene_settings
            if rbr_scene_settings.driveline is None:
                return
            driveline_objects = fixup_driveline_obj(rbr_scene_settings.driveline)
            if driveline_objects is None:
                return
            # Add track constraint
            track_to = narrow(
                obj.constraints.new("TRACK_TO"), bpy.types.TrackToConstraint
            )
            track_to.target = driveline_objects.zfar
            track_to.track_axis = "TRACK_NEGATIVE_Z"
            track_to.up_axis = "UP_Y"

    def update_follow_path(self, context: bpy.types.Context) -> None:
        objs = []
        for obj in bpy.data.objects:
            if obj.data == self.id_data:
                objs.append(obj)
        for obj in objs:
            obj.location = [0, 0, 0]
            obj.lock_location[:] = [True, True, True]
            for constraint in obj.constraints:
                if constraint.type == "FOLLOW_PATH":
                    obj.constraints.remove(constraint)
            if self.follow_path is None:
                continue
            follow_path = narrow(
                obj.constraints.new("FOLLOW_PATH"), bpy.types.FollowPathConstraint
            )
            obj.constraints.move(len(obj.constraints) - 1, 0)
            follow_path.target = self.follow_path
            follow_path.use_fixed_location = True

    look_at_car: bpy.props.BoolProperty(  # type: ignore
        update=update_look_at_car,
        name="Look at Car",
        default=False,
    )
    helicam: bpy.props.BoolProperty(  # type: ignore
        name="Play Helicam Sound",
        default=False,
    )
    shake: bpy.props.FloatProperty(  # type: ignore
        name="Camera Shake",
        description="Higher values shake the camera more. Not visible in blender.",
        min=0,
        soft_max=0.5,
    )
    follow_path: bpy.props.PointerProperty(  # type: ignore
        update=update_follow_path,
        name="Follow Spline",
        type=bpy.types.Object,
    )


def register() -> None:
    bpy.utils.register_class(RBRCameraSettings)
    bpy.types.Camera.rbr_camera_settings = bpy.props.PointerProperty(
        type=RBRCameraSettings
    )


def unregister() -> None:
    del bpy.types.Camera.rbr_camera_settings
    bpy.utils.unregister_class(RBRCameraSettings)
