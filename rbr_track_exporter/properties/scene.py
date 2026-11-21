from typing import TYPE_CHECKING, List, Optional, Set

import bpy
from ..blender_utils import narrow, new_node, socket
from mathutils import Vector

from ..gnodes.brake_wall import make_brakewall_node_group
from ..types import *
from ..shaders import sky, shader_node, texture, brake_wall
from ..shaders.tint_set import ShaderNodeRBRTintSet
from ..physical_material_editor.operator import RBR_OT_edit_material_maps
from .curve import fixup_driveline_obj, fixup_brake_wall_object
from ..properties.world import RBRWorldSettings
from ..gpu.clouds import draw_clouds

if TYPE_CHECKING:
    WorldWeatherCollection = bpy.types.bpy_prop_collection["RBRWorldWeatherPtr"]
else:
    WorldWeatherCollection = object


def setup_rbr_world(world: bpy.types.World) -> None:
    """Function to connect an RBR sky node to an eevee world output. Tries not
    to break the user output (unless they happen to have connected something
    else to the eevee output)."""
    # Render clouds
    world_settings: RBRWorldSettings = world.rbr_world_settings
    cloud_name = CloudName[world_settings.cloud_name]
    scene = bpy.context.scene
    if scene is None:
        raise RuntimeError("No active scene")
    scene_settings: RBRSceneSettings = scene.rbr_scene_settings
    surface_type = scene_settings.get_active_surface_type()
    draw_clouds(surface_type, cloud_name)
    sky.set_clouds_images()
    # Setup the world material
    world.use_nodes = True
    node_tree = world.node_tree
    if node_tree is None:
        raise RuntimeError("World has no node tree")
    world_output = None
    # Find the first eevee output node
    for node in node_tree.nodes:
        if isinstance(node, bpy.types.ShaderNodeOutputWorld) and node.target == "EEVEE":
            world_output = node
            break
    # Change any "All" outputs to just output to cycles - that way they can't
    # interfere with the RBR sky.
    for node in node_tree.nodes:
        if isinstance(node, bpy.types.ShaderNodeOutputWorld) and node.target == "ALL":
            node.target = "CYCLES"
    # Or create one if missing
    if world_output is None:
        world_output = new_node(node_tree.nodes, bpy.types.ShaderNodeOutputWorld)
        world_output.target = "EEVEE"
    # Find a sky node
    sky_node = None
    for node in node_tree.nodes:
        if isinstance(node, sky.ShaderNodeRBRSky):
            sky_node = node
    # Or create one if missing
    if sky_node is None:
        sky_node = narrow(node_tree.nodes.new("ShaderNodeRBRSky"), sky.ShaderNodeRBRSky)
    node_tree.links.new(
        socket(world_output.inputs, "Surface"), socket(sky_node.outputs, "Surface")
    )


class RBRWorldWeatherPtr(bpy.types.PropertyGroup):
    def update_world(self, context: bpy.types.Context) -> None:
        if context.scene is None:
            return
        context.scene.rbr_scene_settings.update_world_context(context)

    world: bpy.props.PointerProperty(  # type: ignore
        type=bpy.types.World,
        update=update_world,
    )
    overcast_time_of_day: bpy.props.EnumProperty(  # type: ignore
        name="Overcast",  # noqa: F821
        description="Overcast Time of Day",
        items=[(t.name, t.pretty(), t.pretty()) for t in TimeOfDay],
        default=TimeOfDay.MORNING.name,
    )


class RBRContainerObject(bpy.types.PropertyGroup):
    container_name: bpy.props.StringProperty()  # type: ignore
    container_id: bpy.props.IntProperty()  # type: ignore
    flag: bpy.props.IntProperty()  # type: ignore
    random_upper_bound: bpy.props.IntProperty()  # type: ignore


class RBRElementIndex(bpy.types.PropertyGroup):
    index: bpy.props.IntProperty()  # type: ignore


class RBRExportMessage(bpy.types.PropertyGroup):
    message: bpy.props.StringProperty()  # type: ignore
    object: bpy.props.PointerProperty(  # type: ignore
        type=bpy.types.Object,
    )
    instancer: bpy.props.PointerProperty(  # type: ignore
        type=bpy.types.Object,
    )
    material: bpy.props.PointerProperty(  # type: ignore
        type=bpy.types.Material,
    )
    node_name: bpy.props.StringProperty()  # type: ignore
    select_kind: bpy.props.StringProperty()  # type: ignore
    select_indices: bpy.props.CollectionProperty(  # type: ignore
        type=RBRElementIndex,
    )


class RBRSceneSettings(bpy.types.PropertyGroup):
    geom_block_specular_glossiness: bpy.props.FloatProperty(  # type: ignore
        name="Geom Block Specular Glossiness",
        default=12.0,
        min=0.0,
        max=20.0,
    )

    def __update_tint_set__(self, _context: bpy.types.Context) -> None:
        tint_set = self.get_active_tint_set_opt()
        available_tint_sets = self.selected_tint_sets()
        if tint_set not in available_tint_sets:
            self.active_tint_set = available_tint_sets[0].name

    tint_set_morning: bpy.props.BoolProperty(  # type: ignore
        name="Morning",
        description="Export morning tint set",
        default=True,
        update=__update_tint_set__,
    )
    tint_set_noon: bpy.props.BoolProperty(  # type: ignore
        name="Noon",
        description="Export noon tint set",
        update=__update_tint_set__,
    )
    tint_set_evening: bpy.props.BoolProperty(  # type: ignore
        name="Evening",
        description="Export evening tint set",
        update=__update_tint_set__,
    )
    tint_set_overcast: bpy.props.BoolProperty(  # type: ignore
        name="Overcast",
        description="Export overcast tint set",
        update=__update_tint_set__,
    )

    def selected_tint_sets(self) -> List[TintSet]:
        """Return the possible tint sets for this stage"""
        tint_sets = []
        if self.tint_set_morning:
            tint_sets.append(TintSet.MORNING)
        if self.tint_set_noon:
            tint_sets.append(TintSet.NOON)
        if self.tint_set_evening:
            tint_sets.append(TintSet.EVENING)
        if self.tint_set_overcast:
            tint_sets.append(TintSet.OVERCAST)
        if len(tint_sets) == 0:
            tint_sets.append(TintSet.MORNING)
        return tint_sets

    def __update_surface_type__(self, _context: bpy.types.Context) -> None:
        surface_type = self.get_active_surface_type_opt()
        available_surface_types = self.selected_surface_types()
        if surface_type not in available_surface_types:
            self.active_surface_type = available_surface_types[0].name

    surface_type_dry: bpy.props.BoolProperty(  # type: ignore
        name="Dry",
        description="The road surface can be dry",
        default=True,
        update=__update_surface_type__,
    )
    surface_type_damp: bpy.props.BoolProperty(  # type: ignore
        name="Damp",
        description="The road surface can be damp",
        update=__update_surface_type__,
    )
    surface_type_wet: bpy.props.BoolProperty(  # type: ignore
        name="Wet",
        description="The road surface can be wet",
        update=__update_surface_type__,
    )

    def selected_surface_types(self) -> List[SurfaceType]:
        """Return the possible surface types for this stage"""
        surface_types = []
        if self.surface_type_dry:
            surface_types.append(SurfaceType.DRY)
        if self.surface_type_damp:
            surface_types.append(SurfaceType.DAMP)
        if self.surface_type_wet:
            surface_types.append(SurfaceType.WET)
        if len(surface_types) == 0:
            surface_types.append(SurfaceType.DRY)
        return surface_types

    def __update_active_tint_set__(self, context: bpy.types.Context) -> None:
        tint_set = self.get_active_tint_set()
        self.active_tint_set_int = tint_set.shader_value()
        self.update_world_context(context)
        for obj in bpy.data.objects:
            os = obj.rbr_object_settings
            shown = any(
                [
                    tint_set is TintSet.MORNING and os.tint_set_morning,
                    tint_set is TintSet.NOON and os.tint_set_noon,
                    tint_set is TintSet.EVENING and os.tint_set_evening,
                    tint_set is TintSet.OVERCAST and os.tint_set_overcast,
                ]
            )
            obj.hide_render = not shown
            obj.hide_set(not shown)

    active_tint_set: bpy.props.EnumProperty(  # type: ignore
        name="Tint Set",
        description="Tint set",
        default=TintSet.MORNING.bitmask(),
        items=lambda self, context: [
            (t.name, t.pretty(), t.pretty(), t.bitmask())
            for t in self.selected_tint_sets()
        ],
        options=set(),
        update=__update_active_tint_set__,
    )

    active_tint_set_int: bpy.props.IntProperty()  # type: ignore

    def get_active_tint_set_opt(self) -> Optional[TintSet]:
        try:
            return TintSet[str(self.active_tint_set)]
        except KeyError:
            return None

    def get_active_tint_set(self) -> TintSet:
        ts = self.get_active_tint_set_opt()
        if ts is None:
            return TintSet.MORNING
        else:
            return ts

    # Update anything which depends on these values
    def __update_conditions__(self, context: bpy.types.Context) -> None:
        for node_tree in texture.all_rbr_texture_node_trees():
            texture.link_context_active_texture(context, node_tree)
        if RBR_OT_edit_material_maps.active_operator is not None:
            RBR_OT_edit_material_maps.active_operator.update_active_texture(context)
        self.update_world_context(context)

    active_surface_type: bpy.props.EnumProperty(  # type: ignore
        name="Surface Type",
        default=SurfaceType.DRY.value,
        items=lambda self, context: [
            (s.name, s.pretty(), s.description(), s.value)
            for s in self.selected_surface_types()
        ],
        update=__update_conditions__,
    )
    active_surface_age: bpy.props.EnumProperty(  # type: ignore
        name="Surface Age",
        default=SurfaceAge.NEW.value,
        items=[(s.name, s.pretty(), s.description(), s.value) for s in SurfaceAge],
        update=__update_conditions__,
    )

    def get_active_surface_type_opt(self) -> Optional[SurfaceType]:
        try:
            return SurfaceType[str(self.active_surface_type)]
        except KeyError:
            return None

    def get_active_surface_type(self) -> SurfaceType:
        st = self.get_active_surface_type_opt()
        if st is None:
            return SurfaceType.DRY
        else:
            return st

    def get_active_surface_age(self) -> SurfaceAge:
        return SurfaceAge[str(self.active_surface_age)]

    def update_world_context(self, context: bpy.types.Context) -> None:
        try:
            world_weathers = self.get_active_weathers()
            world_weather = world_weathers[self.active_world_weather]
            if context.scene is None:
                return
            context.scene.world = world_weather.world
            weather_ptr = self.get_active_weather()
            if weather_ptr is None:
                return
            if weather_ptr.world is None:
                return
            setup_rbr_world(weather_ptr.world)
        except IndexError:
            pass

    world_weathers_morning: bpy.props.CollectionProperty(  # type: ignore
        type=RBRWorldWeatherPtr,
    )
    world_weathers_noon: bpy.props.CollectionProperty(  # type: ignore
        type=RBRWorldWeatherPtr,
    )
    world_weathers_evening: bpy.props.CollectionProperty(  # type: ignore
        type=RBRWorldWeatherPtr,
    )
    world_weathers_overcast: bpy.props.CollectionProperty(  # type: ignore
        type=RBRWorldWeatherPtr,
    )
    active_world_weather: bpy.props.IntProperty(  # type: ignore
        update=update_world_context,
    )

    def get_tint_set_world_weather(self, tint_set: TintSet) -> WorldWeatherCollection:
        weathers: WorldWeatherCollection
        if tint_set is TintSet.MORNING:
            weathers = self.world_weathers_morning
        elif tint_set is TintSet.NOON:
            weathers = self.world_weathers_noon
        elif tint_set is TintSet.EVENING:
            weathers = self.world_weathers_evening
        elif tint_set is TintSet.OVERCAST:
            weathers = self.world_weathers_overcast
        else:
            raise NotImplementedError
        return weathers

    def get_active_weathers(self) -> WorldWeatherCollection:
        tint_set = self.get_active_tint_set()
        return self.get_tint_set_world_weather(tint_set)

    def get_active_weather(self) -> Optional[RBRWorldWeatherPtr]:
        world_weathers = self.get_active_weathers()
        if self.active_world_weather < len(world_weathers):
            weather: RBRWorldWeatherPtr = world_weathers[self.active_world_weather]
            return weather
        return None

    container_objects: bpy.props.CollectionProperty(  # type: ignore
        type=RBRContainerObject,
    )
    active_container_object: bpy.props.IntProperty()  # type: ignore

    export_to: bpy.props.StringProperty(  # type: ignore
        name="Export to",
    )
    track_id: bpy.props.IntProperty(  # type: ignore
        name="ID",
        description="Track number (e.g. 71 for rally school)",
        min=1,
    )
    track_name: bpy.props.StringProperty(  # type: ignore
        name="Track Name",
        description="Track name (e.g. Rally School)",
    )
    author: bpy.props.StringProperty(  # type: ignore
        name="Author",
        description="Track author",
    )
    country_code: bpy.props.StringProperty(  # type: ignore
        name="Country Code (ISO 3166-1 alpha-2)",
        default="GB",
    )
    particles: bpy.props.StringProperty(  # type: ignore
        name="Particles",
        description="Particle set used in the stage, relative to the game folder",
        default="Maps\\ps_british",
    )
    surface: bpy.props.EnumProperty(  # type: ignore
        name="Surface",
        items=[(t.name, t.pretty(), t.pretty(), t.value) for t in StageSurface],
        default=StageSurface.TARMAC.name,
    )
    simplify_shadows: bpy.props.BoolProperty(  # type: ignore
        name="Simplify shadows (experimental)",
        description=(
            "Deduplicate and atlas the shadow maps on export so the stage takes less "
            "space. Slower, and the result should be checked in game"
        ),
        default=False,
    )
    compress_textures: bpy.props.BoolProperty(  # type: ignore
        name="Compress textures",
        description=(
            "Compress the textures archive (.rbz). Turning this off makes the "
            "export faster but the archive bigger"
        ),
        default=True,
    )
    shadow_dedup_threshold: bpy.props.FloatProperty(  # type: ignore
        name="Dedup Threshold",
        description=(
            "How different two shadow triangles may be and still share one patch, "
            "as a fraction of full brightness"
        ),
        default=0.08,
        min=0.0,
        max=1.0,
        precision=3,
    )
    shadow_gradient_threshold: bpy.props.FloatProperty(  # type: ignore
        name="Gradient Threshold",
        description=(
            "How far a shadow triangle may stray from a smooth gradient and still be "
            "collapsed to one, as a fraction of full brightness"
        ),
        default=0.04,
        min=0.0,
        max=1.0,
        precision=3,
    )
    export_errors: bpy.props.CollectionProperty(  # type: ignore
        type=RBRExportMessage,
    )
    export_warnings: bpy.props.CollectionProperty(  # type: ignore
        type=RBRExportMessage,
    )

    def poll_driveline(self, object: bpy.types.Object) -> bool:
        if not isinstance(object.data, bpy.types.Curve):
            return False
        return True

    def update_driveline(self, context: bpy.types.Context) -> None:
        if self.driveline is not None:
            fixup_driveline_obj(self.driveline)

    driveline: bpy.props.PointerProperty(  # type: ignore
        name="Driveline",
        type=bpy.types.Object,
        poll=poll_driveline,
        update=update_driveline,
    )

    def poll_car_location(self, object: bpy.types.Object) -> bool:
        return object.data is None

    car_location: bpy.props.PointerProperty(  # type: ignore
        name="Car Location",
        type=bpy.types.Object,
        poll=poll_car_location,
    )

    def poll_brake_wall(self, object: bpy.types.Object) -> bool:
        if not isinstance(object.data, bpy.types.Curve):
            return False
        return True

    def update_brake_wall(self, context: bpy.types.Context) -> None:
        if self.brake_wall is not None:
            self.brake_wall.modifiers.clear()
            nodes = self.brake_wall.modifiers.new(".rbr.brake_wall", "NODES")
            nodes.node_group = make_brakewall_node_group()
            if isinstance(self.brake_wall.data, bpy.types.Curve):
                self.brake_wall.data.materials.clear()
                mat = bpy.data.materials.new(".rbr.brake_wall")
                mat.use_nodes = True
                brake_wall.setup_brake_wall_tree(
                    narrow(mat.node_tree, bpy.types.ShaderNodeTree)
                )
                # TODO do this in modifier?
                self.brake_wall.data.materials.append(mat)
                self.brake_wall.material_slots[0].link = "OBJECT"
                self.brake_wall.material_slots[0].material = mat
            fixup_brake_wall_object(self.brake_wall)

    brake_wall: bpy.props.PointerProperty(  # type: ignore
        name="Brake Wall",
        type=bpy.types.Object,
        poll=poll_brake_wall,
        update=update_brake_wall,
    )

    def poll_registration_zone(self, object: bpy.types.Object) -> bool:
        return object.data is None

    registration_zone: bpy.props.PointerProperty(  # type: ignore
        name="Registration Zone",
        type=bpy.types.Object,
        poll=poll_registration_zone,
    )


class RBR_OT_add_world_weather_sky(bpy.types.Operator):
    bl_idname = "rbr.add_world_weather_sky"
    bl_label = "Add Weather"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context: bpy.types.Context) -> OperatorReturn:
        if context.scene is None:
            return {"CANCELLED"}
        rbr_scene: RBRSceneSettings = context.scene.rbr_scene_settings
        world_weathers = rbr_scene.get_active_weathers()
        next_index = len(world_weathers)
        world_weathers.add()
        rbr_scene.active_world_weather = next_index
        rbr_scene.update_world_context(context)
        return {"FINISHED"}


class RBR_OT_remove_world_weather_sky(bpy.types.Operator):
    bl_idname = "rbr.remove_world_weather_sky"
    bl_label = "Remove Weather"
    bl_options = {"REGISTER", "UNDO"}

    index: bpy.props.IntProperty(default=0)  # type: ignore

    def execute(self, context: bpy.types.Context) -> OperatorReturn:
        if context.scene is None:
            return {"CANCELLED"}
        rbr_scene: RBRSceneSettings = context.scene.rbr_scene_settings
        world_weathers = rbr_scene.get_active_weathers()
        world_weathers.remove(self.index)
        rbr_scene.update_world_context(context)
        return {"FINISHED"}


class RBR_OT_add_container_object(bpy.types.Operator):
    bl_idname = "rbr.add_container_object"
    bl_label = "Add Container Object"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context: bpy.types.Context) -> OperatorReturn:
        if context.scene is None:
            return {"CANCELLED"}
        next_index = len(context.scene.rbr_scene_settings.container_objects)
        context.scene.rbr_scene_settings.container_objects.add()
        context.scene.rbr_scene_settings.active_container_object = next_index
        return {"FINISHED"}


class RBR_OT_remove_container_object(bpy.types.Operator):
    bl_idname = "rbr.remove_container_object"
    bl_label = "Remove Container Object"
    bl_options = {"REGISTER", "UNDO"}

    index: bpy.props.IntProperty(default=0)  # type: ignore

    def execute(self, context: bpy.types.Context) -> OperatorReturn:
        if context.scene is None:
            return {"CANCELLED"}
        context.scene.rbr_scene_settings.container_objects.remove(self.index)
        return {"FINISHED"}


class RBR_OT_prepare_for_shadow_texture_bake(bpy.types.Operator):
    bl_idname = "rbr.prepare_for_shadow_texture_bake"
    bl_label = "Prepare for shadow texture bake"
    bl_description = "Prepare for shadow texture bake"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context: bpy.types.Context) -> OperatorReturn:
        if context.scene is None:
            return {"CANCELLED"}
        rbr_scene: RBRSceneSettings = context.scene.rbr_scene_settings
        tint_set = rbr_scene.get_active_tint_set()

        materials: set[bpy.types.Material] = set()
        for material in bpy.data.materials:
            if not material.use_nodes:
                continue
            if material.node_tree is None:
                continue
            for node in material.node_tree.nodes:
                if not isinstance(node, shader_node.ShaderNodeRBR):
                    continue
                # shadow texture
                shadow_input = node.inputs.get(shader_node.SHADER_GB_SHADOW_TEXTURE)
                if shadow_input is None:
                    continue
                for link in shadow_input.links:
                    if not isinstance(link.from_node, ShaderNodeRBRTintSet):
                        continue
                    ts_input = link.from_node.inputs.get(tint_set.name.title())
                    if ts_input is None:
                        continue
                    for link in ts_input.links:
                        if isinstance(link.from_node, bpy.types.ShaderNodeTexImage):
                            # The bake target must be both selected and active.
                            for other in material.node_tree.nodes:
                                other.select = False
                            link.from_node.select = True
                            material.node_tree.nodes.active = link.from_node
                            materials.add(material)

        for object in bpy.data.objects:
            object.select_set(False)
            if not isinstance(object.data, bpy.types.Mesh):
                continue
            for mat in object.data.materials:
                if mat in materials:
                    object.select_set(True)
                    break

        return {"FINISHED"}


class RBR_OT_prepare_for_shadow_vcol_bake(bpy.types.Operator):
    bl_idname = "rbr.prepare_for_shadow_vcol_bake"
    bl_description = "Prepare for shadow vertex color bake"
    bl_label = "Prepare for shadow vertex color bake"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context: bpy.types.Context) -> OperatorReturn:
        if context.scene is None:
            return {"CANCELLED"}
        rbr_scene: RBRSceneSettings = context.scene.rbr_scene_settings
        tint_set = rbr_scene.get_active_tint_set()

        materials: dict[bpy.types.Material, str] = dict()
        for material in bpy.data.materials:
            if not material.use_nodes:
                continue
            if material.node_tree is None:
                continue
            for node in material.node_tree.nodes:
                if not isinstance(node, shader_node.ShaderNodeRBR):
                    continue
                # vcol
                vcol_input = node.inputs.get(shader_node.SHADER_GB_COLOR)
                if vcol_input is None:
                    continue
                for link in vcol_input.links:
                    if not isinstance(link.from_node, ShaderNodeRBRTintSet):
                        continue
                    ts_input = link.from_node.inputs.get(tint_set.name.title())
                    if ts_input is None:
                        continue
                    for link in ts_input.links:
                        if isinstance(link.from_node, bpy.types.ShaderNodeAttribute):
                            materials[material] = link.from_node.attribute_name

        for object in bpy.data.objects:
            object.select_set(False)
            if not isinstance(object.data, bpy.types.Mesh):
                continue
            for mat in object.data.materials:
                if mat in materials:
                    object.select_set(True)
                    vcol_name = materials[mat]
                    vcol_layer = object.data.attributes.get(vcol_name)
                    if vcol_layer is not None:
                        object.data.attributes.active_color = vcol_layer
                    break

        return {"FINISHED"}


def register() -> None:
    bpy.utils.register_class(RBRWorldWeatherPtr)
    bpy.utils.register_class(RBRContainerObject)
    bpy.utils.register_class(RBRElementIndex)
    bpy.utils.register_class(RBRExportMessage)
    bpy.utils.register_class(RBRSceneSettings)

    bpy.types.Scene.rbr_scene_settings = bpy.props.PointerProperty(
        type=RBRSceneSettings,
    )

    bpy.utils.register_class(RBR_OT_add_world_weather_sky)
    bpy.utils.register_class(RBR_OT_remove_world_weather_sky)
    bpy.utils.register_class(RBR_OT_add_container_object)
    bpy.utils.register_class(RBR_OT_remove_container_object)
    bpy.utils.register_class(RBR_OT_prepare_for_shadow_texture_bake)
    bpy.utils.register_class(RBR_OT_prepare_for_shadow_vcol_bake)


def unregister() -> None:
    bpy.utils.unregister_class(RBR_OT_prepare_for_shadow_vcol_bake)
    bpy.utils.unregister_class(RBR_OT_prepare_for_shadow_texture_bake)
    bpy.utils.unregister_class(RBR_OT_remove_container_object)
    bpy.utils.unregister_class(RBR_OT_add_container_object)
    bpy.utils.unregister_class(RBR_OT_remove_world_weather_sky)
    bpy.utils.unregister_class(RBR_OT_add_world_weather_sky)

    del bpy.types.Scene.rbr_scene_settings

    bpy.utils.unregister_class(RBRSceneSettings)
    bpy.utils.unregister_class(RBRExportMessage)
    bpy.utils.unregister_class(RBRElementIndex)
    bpy.utils.unregister_class(RBRContainerObject)
    bpy.utils.unregister_class(RBRWorldWeatherPtr)
