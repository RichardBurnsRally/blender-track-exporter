import os
import re
from typing import TYPE_CHECKING, Callable, Dict, List, Optional, Tuple, TypeVar, Union

if TYPE_CHECKING:
    import numpy

    from .physical_material_editor.properties import RBRMaterialMaps

import bpy
from .blender_utils import gnodes_input, narrow, new_node, socket

from .gnodes.fence import GNODES_FENCE_SUBDIVIDE

from .properties.curve import RBRCurveSettings, fixup_driveline_obj  # noqa: F401
from .properties.fence import get_or_create_fence_modifier
from .properties.scene import RBRSceneSettings, RBRExportMessage
from .shaders.shader_node import (
    SHADER_CP_BACKFACE_CULL,
    SHADER_CP_OUTPUT_SURFACE,
    SHADER_GB_BLEND,
    SHADER_GB_COLLISION_SHADING,
    SHADER_GB_COLOR,
    SHADER_GB_OUTPUT_COLOR,
    SHADER_GB_OUTPUT_SURFACE,
    SHADER_GB_SHADOW_TEXTURE,
    SHADER_GB_SPECULAR_STRENGTH,
    SHADER_GB_SPECULAR_TEXTURE,
    SHADER_GB_TEXTURE_1,
    SHADER_GB_TEXTURE_2,
    SHADER_OB_ALPHA,
    SHADER_OB_COLOR,
    SHADER_OB_OUTPUT_ALPHA,
    SHADER_OB_OUTPUT_COLOR,
    SHADER_OB_OUTPUT_DISPLACEMENT,
    SHADER_OB_OUTPUT_SURFACE,
    SHADER_OB_TEXTURE_1,
    SHADER_OB_SWAY_AMP,
    SHADER_OB_SWAY_FREQ,
    SHADER_OB_SWAY_PHASE,
    ObjectDataSockets,
    ShaderNodeRBR,
)

from .shaders.shader_node import (  # noqa: F401
    SHADER_IO_SOCKETS,
    SHADER_RO_SOCKETS,
    SHADER_SB_SOCKETS,
    SHADER_WO_SOCKETS,
)
from .shaders.texture import (  # noqa: F401
    RBR_TEXTURE_OUTPUT,
    ShaderNodeRBRTexture,
    ShaderNodeRBRTextureInternal,
    get_texture_address,
    set_texture_address,
    setup_texture_node_tree as _setup_texture_node_tree,
    passes_through_dds,
    used_image_nodes,
)
from .shaders.uv_velocity import ShaderNodeUVVelocity
from .types import (
    ConditionIdentifier,
    GeomBlockType,
    RBRMeshMaterialType,
    SurfaceAge,
    SurfaceType,
    by_condition,
)
from .preferences import RBRAddonPreferences
from .instance_attributes import (
    RGBA,
    InstanceAttributes,
    UnsupportedInstanceAttribute,
)
from .reify import (
    GroupPath,
    ReifyMaterialError,
    Upstream,
    follow,
    linked,
    node_ref,
)
from . import __package__ as base_package
from .rbr_blender_track_io import (
    UVMap,
    UVVelocity,
    Attribute,
    AttributeOutput,
    TextureFormatChoice,
    TextureExport,
    Texture,
    ShadowImage,
    ClippingPlaneMaterial,
    MaterialSwitch,
    InteractiveObjectMaterial,
    GeomBlockMaterial,
    ObjectBlockMaterial,
    ReflectionObjectMaterial,
    SuperBowlMaterial,
    WaterObjectMaterial,
    TexturePhysicalMaterials,
    PhysicalMaterialMap,
)


def _texture_format_id_to_choice(format_id: str) -> TextureFormatChoice:
    if format_id == "DXT1":
        return TextureFormatChoice.Dxt1Opaque
    if format_id == "DXT1_1BIT":
        return TextureFormatChoice.Dxt1OneBit
    if format_id == "DXT3":
        return TextureFormatChoice.Dxt3
    if format_id == "DXT5":
        return TextureFormatChoice.Dxt5
    raise ValueError(f"Unknown texture format id: {format_id!r}")


def _choice_to_texture_format_id(choice: TextureFormatChoice) -> str:
    if choice == TextureFormatChoice.Dxt1Opaque:
        return "DXT1"
    if choice == TextureFormatChoice.Dxt1OneBit:
        return "DXT1_1BIT"
    if choice == TextureFormatChoice.Dxt3:
        return "DXT3"
    if choice == TextureFormatChoice.Dxt5:
        return "DXT5"
    raise ValueError(f"Unknown texture format choice: {choice!r}")


def setup_texture_node_tree(
    context: bpy.types.Context,
    name: str,
    is_road_surface: bool,
    mip_levels: int,
    texture_format: TextureFormatChoice,
    images: Dict[Tuple[str, str], bpy.types.Image],
    passthrough_dds: bool,
) -> bpy.types.NodeTree:
    return _setup_texture_node_tree(
        context,
        name,
        is_road_surface,
        mip_levels,
        _choice_to_texture_format_id(texture_format),
        images,
        passthrough_dds,
    )


def make_dds_image(name: str, data: bytes) -> bpy.types.Image:
    """An image packed with the .dds file's bytes as they are, named as a .dds
    so the texture can pass it through."""
    import tempfile

    filename = re.sub(r"[^\w.-]", "_", name) + ".dds"
    with tempfile.TemporaryDirectory() as directory:
        path = os.path.join(directory, filename)
        with open(path, "wb") as f:
            f.write(data)
        image = bpy.data.images.load(path)
        image.pack()
    image.name = name
    image.filepath_raw = "//" + filename
    return image


def material_using_node_group(
    node_group: bpy.types.NodeTree,
) -> Optional[Tuple[bpy.types.Material, str]]:
    def find(tree: bpy.types.NodeTree, path: GroupPath) -> Optional[str]:
        for node in tree.nodes:
            if isinstance(node, ShaderNodeRBRTexture) and node.node_tree == node_group:
                return node_ref(node, path)
            if isinstance(node, bpy.types.ShaderNodeGroup) and node.node_tree:
                found = find(node.node_tree, path + (node,))
                if found is not None:
                    return found
        return None

    for material in bpy.data.materials:
        if material.node_tree is None:
            continue
        ref = find(material.node_tree, ())
        if ref is not None:
            return material, ref
    return None


def make_instances_real() -> List[bpy.types.Object]:
    """Run 'Make Instances Real' on every instancer flagged for export and
    return the objects it created."""
    context = bpy.context
    if context.view_layer is None:
        raise RuntimeError("No active view layer")
    instancers = [
        o
        for o in context.view_layer.objects
        if o.rbr_object_settings.make_instances_real
    ]
    created: List[bpy.types.Object] = []
    for instancer in instancers:
        before = {o.name for o in bpy.data.objects}
        with context.temp_override(
            selected_objects=[instancer],
            selected_editable_objects=[instancer],
            active_object=instancer,
            object=instancer,
        ):
            bpy.ops.object.duplicates_make_real(
                use_base_parent=False, use_hierarchy=False
            )
        created.extend(o for o in bpy.data.objects if o.name not in before)
    return created


def remove_objects(objects: List[bpy.types.Object]) -> None:
    orphans = []
    for obj in objects:
        if obj.data is not None:
            orphans.append(obj.data)
        bpy.data.objects.remove(obj)
    for data in orphans:
        if data.users == 0 and isinstance(data, bpy.types.Mesh):
            bpy.data.meshes.remove(data)


def join_collection(
    collection: bpy.types.Collection,
) -> Optional[bpy.types.Object]:
    bpy.ops.object.select_all(action="DESELECT")
    bpy.ops.object.select_same_collection(collection=collection.name)
    selected = bpy.context.selected_objects
    if not selected:
        return None
    [obj, *objs] = selected
    meshes = [o.data for o in objs]
    ctx = bpy.context.copy()
    ctx["active_object"] = obj
    with bpy.context.temp_override(**ctx):
        bpy.ops.object.join()
        obj.name = collection.name
        if bpy.context.scene is None:
            raise RuntimeError("No active scene")
        bpy.context.scene.collection.objects.link(obj)
        bpy.data.collections.remove(collection)
        for mesh in meshes:
            if isinstance(mesh, bpy.types.Mesh):
                bpy.data.meshes.remove(mesh)
    return obj


def make_scm_instancer_node_group() -> bpy.types.GeometryNodeTree:
    node_group = bpy.data.node_groups.new("SCM Instancer", "GeometryNodeTree")
    narrow(node_group, bpy.types.GeometryNodeTree).is_modifier = True
    node_group.interface.new_socket(
        "Geometry", in_out="INPUT", socket_type="NodeSocketGeometry"
    )
    node_group.interface.new_socket(
        "Object", in_out="INPUT", socket_type="NodeSocketObject"
    )
    node_group.interface.new_socket(
        "Use Local Rotation", in_out="INPUT", socket_type="NodeSocketBool"
    )
    node_group.interface.new_socket(
        "Geometry", in_out="OUTPUT", socket_type="NodeSocketGeometry"
    )
    nodes = node_group.nodes
    group_input = new_node(nodes, bpy.types.NodeGroupInput)
    # Instancer
    instancer = new_node(nodes, bpy.types.GeometryNodeInstanceOnPoints)
    node_group.links.new(
        socket(group_input.outputs, "Geometry"),
        socket(instancer.inputs, "Points"),
    )
    # Instance object
    object_info = new_node(nodes, bpy.types.GeometryNodeObjectInfo)
    object_info.transform_space = "RELATIVE"
    socket(object_info.inputs, "As Instance").default_value = True
    node_group.links.new(
        socket(group_input.outputs, "Object"),
        socket(object_info.inputs, "Object"),
    )
    node_group.links.new(
        socket(object_info.outputs, "Geometry"),
        socket(instancer.inputs, "Instance"),
    )
    # Rotation
    rotation = new_node(nodes, bpy.types.GeometryNodeInputNamedAttribute)
    rotation.data_type = "QUATERNION"
    socket(rotation.inputs, "Name").default_value = "rotation"
    euler = new_node(nodes, bpy.types.FunctionNodeRotationToEuler)
    node_group.links.new(
        socket(rotation.outputs, "Attribute"),
        socket(euler.inputs, "Rotation"),
    )
    # Turn off rotation for use_local_rotation=True
    rotation_switch = new_node(nodes, bpy.types.GeometryNodeSwitch)
    rotation_switch.input_type = "VECTOR"
    node_group.links.new(
        socket(group_input.outputs, "Use Local Rotation"),
        socket(rotation_switch.inputs, "Switch"),
    )
    node_group.links.new(
        socket(euler.outputs, "Euler"),
        socket(rotation_switch.inputs, "False"),
    )
    node_group.links.new(
        socket(rotation_switch.outputs, "Output"),
        socket(instancer.inputs, "Rotation"),
    )
    # Scale
    scale = new_node(nodes, bpy.types.GeometryNodeInputNamedAttribute)
    scale.data_type = "FLOAT_VECTOR"
    socket(scale.inputs, "Name").default_value = "scale"
    node_group.links.new(
        socket(scale.outputs, "Attribute"),
        socket(instancer.inputs, "Scale"),
    )
    # Output
    group_output = new_node(node_group.nodes, bpy.types.NodeGroupOutput)
    node_group.links.new(
        socket(instancer.outputs, "Instances"),
        socket(group_output.inputs, "Geometry"),
    )
    return narrow(node_group, bpy.types.GeometryNodeTree)


def setup_clipping_plane_node_tree(
    node_tree: bpy.types.ShaderNodeTree,
    backface_cull: bool,
) -> None:
    output = node_tree.get_output_node("ALL")
    nodes = node_tree.nodes
    rbr_shader = narrow(nodes.new("ShaderNodeRBR"), ShaderNodeRBR)
    rbr_shader.mesh_type = RBRMeshMaterialType.CLIPPING_PLANE.name
    socket(rbr_shader.inputs, SHADER_CP_BACKFACE_CULL).default_value = backface_cull
    node_tree.links.new(
        socket(rbr_shader.outputs, SHADER_CP_OUTPUT_SURFACE),
        socket(output.inputs, "Surface"),
    )


def setup_geom_block_node_tree(
    node_tree: bpy.types.ShaderNodeTree,
    geom_block_type: str,
    texture_1: Optional[bpy.types.ShaderNodeTree],
    texture_1_velocity: Optional[Tuple[float, float]],
    texture_2: Optional[bpy.types.ShaderNodeTree],
    texture_2_velocity: Optional[Tuple[float, float]],
    specular_texture: Optional[bpy.types.ShaderNodeTree],
    specular_velocity: Optional[Tuple[float, float]],
    shadow_texture: Optional[bpy.types.Image],
) -> None:
    nodes = node_tree.nodes
    nodes.clear()
    eevee_output = new_node(nodes, bpy.types.ShaderNodeOutputMaterial)
    eevee_output.target = "EEVEE"
    cycles_output = new_node(nodes, bpy.types.ShaderNodeOutputMaterial)
    cycles_output.target = "CYCLES"
    bsdf = new_node(nodes, bpy.types.ShaderNodeBsdfPrincipled)
    socket(bsdf.inputs, "Roughness").default_value = 0.995
    socket(bsdf.inputs, "IOR").default_value = 1.0
    node_tree.links.new(
        socket(bsdf.outputs, "BSDF"),
        socket(cycles_output.inputs, "Surface"),
    )
    rbr_shader = narrow(nodes.new("ShaderNodeRBR"), ShaderNodeRBR)
    rbr_shader.mesh_type = RBRMeshMaterialType.GEOM_BLOCK.name
    rbr_shader.geom_block_type = geom_block_type
    node_tree.links.new(
        socket(rbr_shader.outputs, SHADER_GB_OUTPUT_SURFACE),
        socket(eevee_output.inputs, "Surface"),
    )
    node_tree.links.new(
        socket(bsdf.inputs, "Base Color"),
        socket(rbr_shader.outputs, SHADER_GB_OUTPUT_COLOR),
    )

    def link(
        from_node: bpy.types.Node,
        from_socket: str,
        to_node: bpy.types.Node,
        to_socket: str,
    ) -> None:
        node_tree.links.new(
            socket(from_node.outputs, from_socket), socket(to_node.inputs, to_socket)
        )

    def attr(name: str) -> bpy.types.ShaderNodeAttribute:
        n = new_node(nodes, bpy.types.ShaderNodeAttribute)
        n.attribute_type = "GEOMETRY"
        n.attribute_name = name
        return n

    def tex(
        nt: bpy.types.ShaderNodeTree,
        uv: bpy.types.ShaderNodeAttribute,
        velocity: Optional[Tuple[float, float]],
    ) -> ShaderNodeRBRTexture:
        n = narrow(nodes.new("ShaderNodeRBRTexture"), ShaderNodeRBRTexture)
        n.node_tree = nt
        if velocity is None:
            link(uv, "Vector", n, "UV")
        else:
            uv_velocity = nodes.new("ShaderNodeUVVelocity")
            link(uv, "Vector", uv_velocity, "UV")
            [u, v] = velocity
            socket(uv_velocity.inputs, "UV Velocity").default_value = [
                u,
                -v,
                0,
            ]
            link(uv_velocity, "UV", n, "UV")
        return n

    def img(
        image: bpy.types.Image, uv: bpy.types.ShaderNodeAttribute
    ) -> bpy.types.ShaderNodeTexImage:
        n = new_node(nodes, bpy.types.ShaderNodeTexImage)
        n.image = image
        link(uv, "Vector", n, "Vector")
        return n

    # color
    color = attr("vcol")
    link(color, "Color", rbr_shader, SHADER_GB_COLOR)
    link(color, "Alpha", rbr_shader, SHADER_GB_BLEND)
    # texture 1
    if texture_1 is not None:
        uv = attr("uv-1")
        image = tex(texture_1, uv, texture_1_velocity)
        link(image, RBR_TEXTURE_OUTPUT, rbr_shader, SHADER_GB_TEXTURE_1)
    # texture 2
    if texture_2 is not None:
        uv = attr("uv-2")
        image = tex(texture_2, uv, texture_2_velocity)
        link(image, RBR_TEXTURE_OUTPUT, rbr_shader, SHADER_GB_TEXTURE_2)
    # specular
    if specular_texture is not None:
        uv = attr("specular-uv")
        image = tex(specular_texture, uv, specular_velocity)
        link(image, RBR_TEXTURE_OUTPUT, rbr_shader, SHADER_GB_SPECULAR_TEXTURE)
        strength = attr("specular-strength")
        link(strength, "Factor", rbr_shader, SHADER_GB_SPECULAR_STRENGTH)
    # shadow
    if shadow_texture is not None:
        uv = attr("shadow-uv")
        shadow_image = img(shadow_texture, uv)
        node_tree.links.new(
            socket(uv.outputs, "Vector"),
            socket(shadow_image.inputs, "Vector"),
        )
        link(shadow_image, "Color", rbr_shader, SHADER_GB_SHADOW_TEXTURE)


def setup_object_block_node_tree(
    node_tree: bpy.types.ShaderNodeTree,
    object_block_type: str,
    texture: Optional[bpy.types.ShaderNodeTree],
    texture_address: Tuple[bool, bool, bool, bool],
) -> None:
    nodes = node_tree.nodes
    nodes.clear()
    eevee_output = new_node(nodes, bpy.types.ShaderNodeOutputMaterial)
    eevee_output.target = "EEVEE"
    cycles_output = new_node(nodes, bpy.types.ShaderNodeOutputMaterial)
    cycles_output.target = "CYCLES"
    bsdf = new_node(nodes, bpy.types.ShaderNodeBsdfPrincipled)
    socket(bsdf.inputs, "Roughness").default_value = 0.995
    socket(bsdf.inputs, "IOR").default_value = 1.0
    node_tree.links.new(
        socket(bsdf.outputs, "BSDF"),
        socket(cycles_output.inputs, "Surface"),
    )
    rbr_shader = narrow(nodes.new("ShaderNodeRBR"), ShaderNodeRBR)
    rbr_shader.mesh_type = RBRMeshMaterialType.OBJECT_BLOCK.name
    rbr_shader.object_block_type = object_block_type
    node_tree.links.new(
        socket(rbr_shader.outputs, SHADER_OB_OUTPUT_SURFACE),
        socket(eevee_output.inputs, "Surface"),
    )
    node_tree.links.new(
        socket(bsdf.inputs, "Base Color"),
        socket(rbr_shader.outputs, SHADER_OB_OUTPUT_COLOR),
    )
    node_tree.links.new(
        socket(bsdf.inputs, "Alpha"),
        socket(rbr_shader.outputs, SHADER_OB_OUTPUT_ALPHA),
    )
    node_tree.links.new(
        socket(rbr_shader.outputs, SHADER_OB_OUTPUT_DISPLACEMENT),
        socket(eevee_output.inputs, "Displacement"),
    )
    node_tree.links.new(
        socket(rbr_shader.outputs, SHADER_OB_OUTPUT_DISPLACEMENT),
        socket(cycles_output.inputs, "Displacement"),
    )

    def link(
        from_node: bpy.types.Node,
        from_socket: str,
        to_node: bpy.types.Node,
        to_socket: str,
    ) -> None:
        node_tree.links.new(
            socket(from_node.outputs, from_socket), socket(to_node.inputs, to_socket)
        )

    def attr(name: str) -> bpy.types.ShaderNodeAttribute:
        n = new_node(nodes, bpy.types.ShaderNodeAttribute)
        n.attribute_type = "GEOMETRY"
        n.attribute_name = name
        return n

    def tex(
        nt: Optional[bpy.types.ShaderNodeTree], uv: bpy.types.ShaderNodeAttribute
    ) -> ShaderNodeRBRTexture:
        n = narrow(nodes.new("ShaderNodeRBRTexture"), ShaderNodeRBRTexture)
        n.node_tree = nt
        set_texture_address(n, texture_address)
        link(uv, "Vector", n, "UV")
        return n

    # color
    color = attr("vcol")
    link(color, "Color", rbr_shader, SHADER_OB_COLOR)
    link(color, "Alpha", rbr_shader, SHADER_OB_ALPHA)
    # texture 1
    uv = attr("uv-1")
    image = tex(texture, uv)
    link(image, RBR_TEXTURE_OUTPUT, rbr_shader, SHADER_OB_TEXTURE_1)
    # sway
    freq = attr("sway-freq")
    link(freq, "Factor", rbr_shader, SHADER_OB_SWAY_FREQ)
    amp = attr("sway-amp")
    link(amp, "Factor", rbr_shader, SHADER_OB_SWAY_AMP)
    phase = attr("sway-phase")
    link(phase, "Factor", rbr_shader, SHADER_OB_SWAY_PHASE)


def set_material_maps(
    node_tree: bpy.types.ShaderNodeTree,
    maps: dict[int, list[list[int]]],
) -> None:
    """Populate a material-map texture node's editable material maps from raw
    16x16 MaterialId grids, keyed by packed condition index
    (3 * surface_type + surface_age)."""
    internal = narrow(node_tree.nodes["internal"], ShaderNodeRBRTextureInternal)
    internal.material_maps.clear()
    material_maps = internal.material_maps.add()
    material_maps._init()
    material_maps.position_1 = (0.0, 0.0)
    material_maps.position_2 = (1.0, 1.0)
    for packed_index, grid in maps.items():
        material_map = material_maps.maps[packed_index]
        for i, row in enumerate(grid):
            for j, value in enumerate(row):
                material_map.rows[i].cols[j].material_id = value


def read_texture_physical_materials(
    node_tree: bpy.types.ShaderNodeTree,
) -> TexturePhysicalMaterials:
    internal = narrow(node_tree.nodes["internal"], ShaderNodeRBRTextureInternal)
    maps = []
    for source in internal.material_maps:

        def grid(
            surface_type: SurfaceType,
            surface_age: SurfaceAge,
            source: "RBRMaterialMaps" = source,
        ) -> Optional[List[List[int]]]:
            index = ConditionIdentifier(surface_type, surface_age).packed_index()
            if index >= len(source.maps):
                return None
            return [
                [col.material_id for col in row.cols] for row in source.maps[index].rows
            ]

        maps.append(
            PhysicalMaterialMap(
                position_1=tuple(source.position_1),
                position_2=tuple(source.position_2),
                repeat_x=source.repeat_x,
                repeat_y=source.repeat_y,
                grids=by_condition(grid),
            )
        )
    fb = internal.fallback_materials
    return TexturePhysicalMaterials(
        is_road_surface=internal.is_road_surface,
        maps=maps,
        fallback=by_condition(lambda st, sa: fb.get_condition(st, sa).value),
    )


def setup_colmesh_node_tree(
    node_tree: bpy.types.ShaderNodeTree,
    texture_1_tree: Optional[bpy.types.ShaderNodeTree],
    texture_2_tree: Optional[bpy.types.ShaderNodeTree],
) -> None:
    # A collision mesh is a near geom block (collision-only) whose two textures
    # are the physical material maps, blended by the "blending" attribute. It's
    # never rendered, so it only needs the EEVEE output, not the Cycles one.
    nodes = node_tree.nodes
    nodes.clear()
    eevee_output = new_node(nodes, bpy.types.ShaderNodeOutputMaterial)
    eevee_output.target = "EEVEE"

    rbr_shader = narrow(nodes.new("ShaderNodeRBR"), ShaderNodeRBR)
    rbr_shader.mesh_type = RBRMeshMaterialType.GEOM_BLOCK.name
    rbr_shader.geom_block_type = GeomBlockType.NEAR.name
    rbr_shader.is_geom_block_collision = True
    rbr_shader.is_geom_block_invisible = True
    node_tree.links.new(
        socket(rbr_shader.outputs, SHADER_GB_OUTPUT_SURFACE),
        socket(eevee_output.inputs, "Surface"),
    )

    def link(
        from_node: bpy.types.Node,
        from_socket: str,
        to_node: bpy.types.Node,
        to_socket: str,
    ) -> None:
        node_tree.links.new(
            socket(from_node.outputs, from_socket), socket(to_node.inputs, to_socket)
        )

    def attr(name: str) -> bpy.types.ShaderNodeAttribute:
        n = new_node(nodes, bpy.types.ShaderNodeAttribute)
        n.attribute_type = "GEOMETRY"
        n.attribute_name = name
        return n

    def tex(
        nt: Optional[bpy.types.ShaderNodeTree], uv: bpy.types.ShaderNodeAttribute
    ) -> ShaderNodeRBRTexture:
        n = narrow(nodes.new("ShaderNodeRBRTexture"), ShaderNodeRBRTexture)
        n.node_tree = nt
        link(uv, "Vector", n, "UV")
        return n

    # With a single material both slots must be connected, or the shader reads
    # "blending" as alpha instead of a texture blend factor.
    if texture_2_tree is None:
        texture_2_tree = texture_1_tree
    if texture_1_tree is not None:
        image = tex(texture_1_tree, attr("uv-1"))
        link(image, RBR_TEXTURE_OUTPUT, rbr_shader, SHADER_GB_TEXTURE_1)
    if texture_2_tree is not None:
        image = tex(texture_2_tree, attr("uv-2"))
        link(image, RBR_TEXTURE_OUTPUT, rbr_shader, SHADER_GB_TEXTURE_2)
    link(attr("blending"), "Factor", rbr_shader, SHADER_GB_BLEND)
    link(attr("shading"), "Factor", rbr_shader, SHADER_GB_COLLISION_SHADING)


def setup_object_data_node_tree(
    node_tree: bpy.types.ShaderNodeTree,
    mesh_type: str,
    sockets: ObjectDataSockets,
    texture_1: Optional[bpy.types.ShaderNodeTree],
    texture_1_velocity: Optional[Tuple[float, float]],
    texture_2: Optional[bpy.types.ShaderNodeTree],
    texture_2_velocity: Optional[Tuple[float, float]],
    specular_texture: Optional[bpy.types.ShaderNodeTree],
    specular_velocity: Optional[Tuple[float, float]],
    texture_address: Tuple[bool, bool, bool, bool],
) -> None:
    nodes = node_tree.nodes
    nodes.clear()
    eevee_output = new_node(nodes, bpy.types.ShaderNodeOutputMaterial)
    eevee_output.target = "EEVEE"
    cycles_output = new_node(nodes, bpy.types.ShaderNodeOutputMaterial)
    cycles_output.target = "CYCLES"
    bsdf = new_node(nodes, bpy.types.ShaderNodeBsdfPrincipled)
    socket(bsdf.inputs, "Roughness").default_value = 0.995
    socket(bsdf.inputs, "IOR").default_value = 1.0
    node_tree.links.new(
        socket(bsdf.outputs, "BSDF"),
        socket(cycles_output.inputs, "Surface"),
    )
    rbr_shader = narrow(nodes.new("ShaderNodeRBR"), ShaderNodeRBR)
    rbr_shader.mesh_type = mesh_type
    node_tree.links.new(
        socket(rbr_shader.outputs, sockets.output_surface()),
        socket(eevee_output.inputs, "Surface"),
    )
    node_tree.links.new(
        socket(bsdf.inputs, "Base Color"),
        socket(rbr_shader.outputs, sockets.output_color()),
    )

    def link(
        from_node: bpy.types.Node,
        from_socket: str,
        to_node: bpy.types.Node,
        to_socket: str,
    ) -> None:
        node_tree.links.new(
            socket(from_node.outputs, from_socket), socket(to_node.inputs, to_socket)
        )

    def attr(name: str) -> bpy.types.ShaderNodeAttribute:
        n = new_node(nodes, bpy.types.ShaderNodeAttribute)
        n.attribute_type = "GEOMETRY"
        n.attribute_name = name
        return n

    def tex(
        nt: bpy.types.ShaderNodeTree,
        uv_name: str,
        velocity: Optional[Tuple[float, float]],
    ) -> ShaderNodeRBRTexture:
        tex_node = narrow(nodes.new("ShaderNodeRBRTexture"), ShaderNodeRBRTexture)
        tex_node.node_tree = nt
        if uv_name != "specular-uv":
            set_texture_address(tex_node, texture_address)
        if velocity is None:
            uv = attr(uv_name)
            link(uv, "Vector", tex_node, "UV")
        else:
            uv_static = attr(uv_name)
            uv_velocity = nodes.new("ShaderNodeUVVelocity")
            link(uv_static, "Vector", uv_velocity, "UV")
            [u, v] = velocity
            socket(uv_velocity.inputs, "UV Velocity").default_value = [
                u,
                -v,
                0,
            ]
            link(uv_velocity, "UV", tex_node, "UV")
        return tex_node

    # color
    color = attr("vcol")
    link(color, "Color", rbr_shader, sockets.color())
    link(color, "Alpha", rbr_shader, sockets.alpha_blend())
    # texture 1
    if texture_1 is not None:
        image = tex(texture_1, "uv-1", texture_1_velocity)
        link(image, RBR_TEXTURE_OUTPUT, rbr_shader, sockets.texture_1())
    # texture 2
    if texture_2 is not None:
        image = tex(texture_2, "uv-2", texture_2_velocity)
        link(image, RBR_TEXTURE_OUTPUT, rbr_shader, sockets.texture_2())
    # specular
    if specular_texture is not None:
        image = tex(specular_texture, "specular-uv", specular_velocity)
        link(image, RBR_TEXTURE_OUTPUT, rbr_shader, sockets.specular_texture())
        strength = attr("specular-strength")
        link(strength, "Factor", rbr_shader, sockets.specular_strength())


def setup_pacenotes(
    curve: bpy.types.Curve,
    pacenotes: List[Tuple[float, int, int]],
) -> None:
    settings: RBRCurveSettings = curve.rbr_curve_settings
    for i, (location, pacenote, flags) in enumerate(pacenotes):
        settings.pacenotes.add()
        settings.pacenotes[i].location = location
        settings.pacenotes[i].pacenote_id = pacenote
        settings.pacenotes[i].flags = flags
    settings.update_sorted_pacenotes()


def setup_fence(
    object: bpy.types.Object,
    subdivide: bool,
) -> None:
    if not isinstance(object.data, bpy.types.Mesh):
        raise RuntimeError("Fence object must be a mesh")
    gnodes = get_or_create_fence_modifier(object, object.data.rbr_mesh_settings.fence)
    gnodes_input(gnodes, GNODES_FENCE_SUBDIVIDE).value = subdivide


def fence_subdivide(object: bpy.types.Object) -> bool:
    gnodes = object.modifiers.get(".rbr.fence")
    if gnodes is None:
        return False
    return bool(gnodes_input(gnodes, GNODES_FENCE_SUBDIVIDE).value)


def maps_directory_of_stem(stem: str) -> str:
    """The RBR Maps folder holding a stage stem, which is either directly in
    Maps or in a numbered stage folder such as Maps/711-Rally School Stage."""
    directory = os.path.dirname(stem)
    folder = os.path.basename(directory)
    if re.match(r"^\d+-", folder):
        directory = os.path.dirname(directory)
    return directory


def set_export_directory(stem: str) -> None:
    """Select the export directory that holds a stage stem, adding it to the
    preferences if it is not there yet."""
    if bpy.context.scene is None or bpy.context.preferences is None:
        return
    scene_settings: RBRSceneSettings = bpy.context.scene.rbr_scene_settings
    # Not present when the addon is enabled without touching preferences
    # (e.g. addon_utils.enable in a headless session).
    addon = bpy.context.preferences.addons.get(base_package)
    if addon is None:
        return
    prefs = narrow(addon.preferences, RBRAddonPreferences)

    def norm(path: str) -> str:
        return os.path.normcase(os.path.normpath(path))

    maps_directory = maps_directory_of_stem(stem)
    for export_directory in prefs.export_directories:
        if export_directory.directory and norm(export_directory.directory) == norm(
            maps_directory
        ):
            scene_settings.export_to = export_directory.name
            return
    name = os.path.basename(maps_directory) or maps_directory
    if prefs.get_export_directory(name) is not None:
        name = maps_directory
    export_directory = prefs.export_directories.add()
    export_directory.name = name
    export_directory.directory = maps_directory
    scene_settings.export_to = name


def set_image_pixels(image: bpy.types.Image, pixels: bytes) -> None:
    import numpy

    npixels = numpy.frombuffer(pixels, dtype="f")
    image.pixels.foreach_set(npixels)


def get_image_pixels(image: bpy.types.Image) -> Tuple[int, int, bytes]:
    import numpy

    width, height = image.size
    pixels = numpy.empty(len(image.pixels), dtype="f")
    image.pixels.foreach_get(pixels)
    return (width, height, pixels.tobytes())


def packed_dds(image: bpy.types.Image) -> Optional[Tuple[int, int, bytes]]:
    """The packed bytes of an unedited DXT1/3/5 DDS image, so the exporter can
    decode it itself instead of having Blender decode it. Reads only the
    header, since image.size or image.pixels would make Blender load it."""
    packed = image.packed_file
    if (
        packed is None
        or image.source != "FILE"
        or image.alpha_mode != "STRAIGHT"
        or image.is_dirty
    ):
        return None
    data: bytes = packed.data
    if len(data) < 128 or data[:4] != b"DDS ":
        return None
    if data[84:88] not in (b"DXT1", b"DXT3", b"DXT5"):
        return None
    height = int.from_bytes(data[12:16], "little")
    width = int.from_bytes(data[16:20], "little")
    return (width, height, data)


# (subdir, width, height, packed DDS bytes or Blender's float pixels)
TextureVariant = Tuple[str, int, int, Union[bytes, "numpy.ndarray"]]


def dds_file_bytes(image: bpy.types.Image) -> Optional[bytes]:
    """The image's .dds file as it is, packed or on disk; None if missing."""
    if image.packed_file is not None:
        data: bytes = image.packed_file.data
        return data
    path = bpy.path.abspath(image.filepath, library=image.library)
    try:
        with open(path, "rb") as f:
            return f.read()
    except OSError:
        return None


def texture_export_files(
    node_tree: bpy.types.ShaderNodeTree, surfaces: List[str]
) -> TextureExport:
    """What to export for a texture's images in the given surface types:
    Blender's pixels (or packed DDS bytes) to re-encode, or with pass-through
    the .dds files' bytes as they are (None for a file that can't be read)."""
    import numpy

    internal = narrow(node_tree.nodes["internal"], ShaderNodeRBRTextureInternal)
    is_road = internal.is_road_surface
    texture_format = _texture_format_id_to_choice(internal.texture_format)
    used = [
        (subdir, node)
        for subdir, node in used_image_nodes(node_tree, is_road)
        if subdir.split("/")[0] in surfaces
    ]
    if passes_through_dds(internal):
        files: List[Tuple[str, Optional[bytes]]] = []
        unsaved: List[str] = []
        for subdir, node in used:
            image = narrow(node.image, bpy.types.Image)
            files.append((subdir, dds_file_bytes(image)))
            if image.is_dirty:
                unsaved.append(subdir)
        return TextureExport(
            is_road, internal.mip_levels, texture_format, [], files, unsaved
        )
    variants: List[TextureVariant] = []
    for subdir, node in used:
        image = narrow(node.image, bpy.types.Image)
        dds = packed_dds(image)
        if dds is not None:
            variants.append((subdir, *dds))
            continue
        width, height = image.size
        pixels = numpy.empty(len(image.pixels), dtype="f")
        image.pixels.foreach_get(pixels)
        variants.append((subdir, width, height, pixels))
    return TextureExport(
        is_road, internal.mip_levels, texture_format, variants, None, []
    )


ReifiedMaterial = Union[
    ClippingPlaneMaterial,
    InteractiveObjectMaterial,
    GeomBlockMaterial,
    ObjectBlockMaterial,
    ReflectionObjectMaterial,
    SuperBowlMaterial,
    WaterObjectMaterial,
]


def reify_uv_map(uv: Upstream) -> Optional[UVMap]:
    ref = node_ref(uv.node, uv.path)
    if isinstance(uv.node, bpy.types.ShaderNodeUVMap):
        if uv.node.from_instancer:
            raise ReifyMaterialError("UV map must not be from instancer", ref)
        return UVMap(layer_name=uv.node.uv_map)
    elif isinstance(uv.node, bpy.types.ShaderNodeAttribute):
        if uv.node.attribute_type != "GEOMETRY":
            raise ReifyMaterialError("UV map attribute type must be 'Geometry'", ref)
        if uv.socket.name != "Vector":
            raise ReifyMaterialError(
                "Attribute node UV map must be connected from the Vector socket", ref
            )
        return UVMap(layer_name=uv.node.attribute_name)
    else:
        return None


def reify_uv_velocity(uv: Upstream, tint_set: str) -> UVVelocity:
    ref = node_ref(uv.node, uv.path)
    if isinstance(uv.node, ShaderNodeUVVelocity):
        inner = linked(socket(uv.node.inputs, "UV"), uv.path, tint_set)
        if inner is None:
            raise ReifyMaterialError("UV input must be connected", ref)
        velocity = follow(socket(uv.node.inputs, "UV Velocity"), uv.path, tint_set)
        if isinstance(velocity, Upstream):
            raise ReifyMaterialError("UV velocity input must not be connected", ref)
        uv_map = reify_uv_map(inner)
        if uv_map is None:
            raise ReifyMaterialError(
                "UV input must be an Attribute or UV Velocity node", ref
            )
        return UVVelocity(
            uv_map=uv_map,
            velocity=[velocity.default_value[0], velocity.default_value[1]],
        )
    else:
        uv_map = reify_uv_map(uv)
        if uv_map is None:
            raise ReifyMaterialError(
                "UV input must be one of a UV Map, Attribute, or UV Velocity node",
                ref,
            )
        return UVVelocity(uv_map=uv_map, velocity=[0, 0])


def reify_rbr_texture(
    texture_input: bpy.types.NodeSocket,
    path: GroupPath,
    tint_set: str,
) -> Optional[Texture]:
    texture = linked(texture_input, path, tint_set)
    if texture is None:
        return None
    texture_node = texture.node
    ref = node_ref(texture_node, texture.path)
    if not isinstance(texture_node, ShaderNodeRBRTexture):
        raise ReifyMaterialError("Texture inputs take an RBR Texture node", ref)
    uv = linked(socket(texture_node.inputs, "UV"), texture.path, tint_set)
    if uv is None:
        raise ReifyMaterialError("Texture node must have a UV input", ref)
    return Texture(
        node_tree=texture_node.node_tree,
        uv_map=reify_uv_velocity(uv, tint_set),
    )


def reify_texture_address(
    texture_1_input: bpy.types.NodeSocket,
    texture_2_input: Optional[bpy.types.NodeSocket],
    path: GroupPath,
    tint_set: str,
) -> Tuple[bool, bool, bool, bool]:
    """The material's address flags, from its texture node(s). The game has
    one set of flags per material, applied to every texture stage, so a
    second texture must agree with the first."""

    def address(
        color_input: bpy.types.NodeSocket,
    ) -> Optional[Tuple[Tuple[bool, bool, bool, bool], str]]:
        texture = linked(color_input, path, tint_set)
        if texture is None or not isinstance(texture.node, ShaderNodeRBRTexture):
            return None
        ref = node_ref(texture.node, texture.path)
        try:
            return (get_texture_address(texture.node), ref)
        except KeyError:
            raise ReifyMaterialError(
                "Texture node is missing its address sockets; refresh the RBR shaders",
                ref,
            )

    first = address(texture_1_input)
    second = address(texture_2_input) if texture_2_input is not None else None
    if first is None:
        return second[0] if second is not None else (False, False, False, False)
    if second is not None and second[0] != first[0]:
        raise ReifyMaterialError(
            "Texture 2 clamp/mirror settings must match texture 1", second[1]
        )
    return first[0]


def reify_shadow_image(
    shadow_input: bpy.types.NodeSocket,
    path: GroupPath,
    tint_set: str,
) -> Optional[ShadowImage]:
    shadow = linked(shadow_input, path, tint_set)
    if shadow is None:
        return None
    shadow_node = shadow.node
    ref = node_ref(shadow_node, shadow.path)
    if not isinstance(shadow_node, bpy.types.ShaderNodeTexImage):
        raise ReifyMaterialError(
            "Shadow texture node must be an image texture node", ref
        )
    if shadow.socket.name != "Color":
        raise ReifyMaterialError(
            "Shadow texture node must be connected from the color channel", ref
        )
    if shadow_node.image is None:
        raise ReifyMaterialError("Shadow texture node must have an image selected", ref)
    uv = linked(socket(shadow_node.inputs, "Vector"), shadow.path, tint_set)
    if uv is None:
        raise ReifyMaterialError("Shadow texture node must have a UV input", ref)
    uv_map = reify_uv_map(uv)
    if uv_map is None:
        raise ReifyMaterialError(
            "Shadow texture node UV input must be either a UV map node or an attribute node",
            ref,
        )
    return ShadowImage(
        image=shadow_node.image,
        uv_map=uv_map,
    )


def reify_attribute_link(attribute: Upstream) -> Attribute:
    node = attribute.node
    ref = node_ref(node, attribute.path)
    if not isinstance(node, bpy.types.ShaderNodeAttribute):
        raise ReifyMaterialError("Attribute link must come from an attribute node", ref)
    if node.attribute_type != "GEOMETRY":
        raise ReifyMaterialError("Attribute type must be 'Geometry'", ref)
    if attribute.socket.name == "Color":
        output = AttributeOutput.Color
    elif attribute.socket.name == "Vector":
        output = AttributeOutput.Vector
    elif attribute.socket.name == "Factor":
        output = AttributeOutput.Factor
    elif attribute.socket.name == "Alpha":
        output = AttributeOutput.Alpha
    else:
        raise NotImplementedError(
            f"Missing attribute link type: {attribute.socket.name}"
        )
    return Attribute(name=node.attribute_name, output=output)


def reify_attribute_or_color(
    color_input: bpy.types.NodeSocket,
    path: GroupPath,
    tint_set: str,
) -> Union[Attribute, List[float]]:
    source = follow(color_input, path, tint_set)
    if not isinstance(source, Upstream):
        return source.default_value
    if isinstance(source.node, bpy.types.ShaderNodeAttribute):
        return reify_attribute_link(source)
    elif isinstance(source.node, bpy.types.ShaderNodeRGB):
        return socket(source.node.outputs, "Color").default_value
    else:
        raise ReifyMaterialError(
            "Color input must be an attribute node, RGB input node, or disconnected",
            node_ref(source.node, source.path),
        )


def reify_attribute_or_float(
    float_input: bpy.types.NodeSocket,
    path: GroupPath,
    tint_set: str,
) -> Union[Attribute, List[float]]:
    source = follow(float_input, path, tint_set)
    if not isinstance(source, Upstream):
        return source.default_value
    if isinstance(source.node, bpy.types.ShaderNodeAttribute):
        return reify_attribute_link(source)
    elif isinstance(source.node, bpy.types.ShaderNodeValue):
        return socket(source.node.outputs, "Value").default_value
    else:
        raise ReifyMaterialError(
            "Value input must be an attribute node, value input node, or disconnected",
            node_ref(source.node, source.path),
        )


_ObjectDataMaterial = TypeVar("_ObjectDataMaterial")


def reify_object_data_material(
    material: bpy.types.Material,
    shader_node: ShaderNodeRBR,
    path: GroupPath,
    sockets: ObjectDataSockets,
    tint_set: str,
    material_class: Callable[..., _ObjectDataMaterial],
) -> _ObjectDataMaterial:
    def input(name: str) -> bpy.types.NodeSocket:
        return socket(shader_node.inputs, name)

    texture_1 = reify_rbr_texture(input(sockets.texture_1()), path, tint_set)
    texture_2 = reify_rbr_texture(input(sockets.texture_2()), path, tint_set)
    specular = None
    specular_strength: Union[Attribute, List[float], float] = 1.0
    if sockets.has_specular:
        specular = reify_rbr_texture(input(sockets.specular_texture()), path, tint_set)
        specular_strength = reify_attribute_or_float(
            input(sockets.specular_strength()), path, tint_set
        )
    color = reify_attribute_or_color(input(sockets.color()), path, tint_set)
    return material_class(
        texture_1,
        texture_2,
        specular,
        specular_strength,
        color,
        not material.use_backface_culling,
        *reify_texture_address(
            input(sockets.texture_1()), input(sockets.texture_2()), path, tint_set
        ),
    )


def reify_material(
    material: bpy.types.Material, tint_set: str
) -> Optional[Union[ReifiedMaterial, MaterialSwitch]]:
    """Throws for invalid RBR materials, returns None for none-RBR materials"""
    nt = material.node_tree
    if nt is None:
        return None
    output = nt.get_output_node("EEVEE")
    if output is None:
        return None
    surface = linked(socket(output.inputs, "Surface"), (), tint_set)
    if surface is None:
        return None
    if isinstance(surface.node, bpy.types.GeometryNodeIndexSwitch):
        return reify_switch(material, surface, tint_set)
    if isinstance(
        surface.node, (bpy.types.GeometryNodeSwitch, bpy.types.GeometryNodeMenuSwitch)
    ) and any(
        isinstance(
            getattr(linked(i, surface.path, tint_set), "node", None), ShaderNodeRBR
        )
        for i in surface.node.inputs
        if i.type == "SHADER"
    ):
        raise ReifyMaterialError(
            "Use an Index Switch to choose between RBR shader nodes",
            node_ref(surface.node, surface.path),
        )
    if not isinstance(surface.node, ShaderNodeRBR):
        return None
    return reify_shader(material, surface.node, surface.path, tint_set)


def reify_switch(
    material: bpy.types.Material, switch: Upstream, tint_set: str
) -> Optional[Union[ReifiedMaterial, MaterialSwitch]]:
    """An Index Switch choosing between RBR shader nodes, by an Object or
    Instancer Attribute node's Fac or Alpha, or by a fixed index."""
    node = switch.node
    ref = node_ref(node, switch.path)
    items = [i for i in node.inputs[1:] if i.type == "SHADER"]
    shaders = [linked(i, switch.path, tint_set) for i in items]
    rbr = [s is not None and isinstance(s.node, ShaderNodeRBR) for s in shaders]
    if not any(rbr):
        return None
    if not all(rbr):
        raise ReifyMaterialError(
            "Every Index Switch input must be an RBR shader node", ref
        )
    branches = [
        reify_shader(material, narrow(s.node, ShaderNodeRBR), s.path, tint_set)
        for s in shaders
        if s is not None
    ]
    index = follow(node.inputs[0], switch.path, tint_set)
    if not isinstance(index, Upstream):
        if not 0 <= index.default_value < len(branches):
            raise ReifyMaterialError(
                f"Index Switch index {index.default_value} is out of range", ref
            )
        return branches[index.default_value]
    attribute = index.node
    if not isinstance(attribute, bpy.types.ShaderNodeAttribute) or (
        attribute.attribute_type not in ("OBJECT", "INSTANCER")
    ):
        raise ReifyMaterialError(
            "Index Switch index must come from an Object or Instancer Attribute node",
            ref,
        )
    if index.socket.name not in ("Factor", "Alpha"):
        raise ReifyMaterialError(
            "Index Switch index must come from the Attribute node's Factor or Alpha",
            node_ref(attribute, index.path),
        )
    return MaterialSwitch(
        attribute.attribute_name,
        attribute.attribute_type == "INSTANCER",
        index.socket.name == "Alpha",
        branches,
    )


def reify_shader(
    material: bpy.types.Material,
    shader_node: ShaderNodeRBR,
    path: GroupPath,
    tint_set: str,
) -> ReifiedMaterial:
    def input(name: str) -> bpy.types.NodeSocket:
        return socket(shader_node.inputs, name)

    mesh_type = RBRMeshMaterialType[shader_node.mesh_type]
    if mesh_type is RBRMeshMaterialType.CLIPPING_PLANE:
        backface_cull = follow(input(SHADER_CP_BACKFACE_CULL), path, tint_set)
        if isinstance(backface_cull, Upstream):
            backface_cull = input(SHADER_CP_BACKFACE_CULL)
        return ClippingPlaneMaterial(bool(backface_cull.default_value))
    elif mesh_type is RBRMeshMaterialType.INTERACTIVE_OBJECT_VISUAL:
        return reify_object_data_material(
            material,
            shader_node,
            path,
            SHADER_IO_SOCKETS,
            tint_set,
            InteractiveObjectMaterial,
        )
    elif mesh_type is RBRMeshMaterialType.GEOM_BLOCK:
        is_collision = shader_node.is_geom_block_collision
        is_invisible = is_collision and shader_node.is_geom_block_invisible
        texture_1 = reify_rbr_texture(input(SHADER_GB_TEXTURE_1), path, tint_set)
        if texture_1 is None:
            raise ReifyMaterialError(
                "Missing texture 1 input to RBR shader node",
                node_ref(shader_node, path),
            )
        return GeomBlockMaterial(
            texture_1=texture_1,
            texture_2=reify_rbr_texture(input(SHADER_GB_TEXTURE_2), path, tint_set),
            texture_specular=reify_rbr_texture(
                input(SHADER_GB_SPECULAR_TEXTURE), path, tint_set
            ),
            texture_shadow=reify_shadow_image(
                input(SHADER_GB_SHADOW_TEXTURE), path, tint_set
            ),
            color=reify_attribute_or_color(input(SHADER_GB_COLOR), path, tint_set),
            blend=reify_attribute_or_float(input(SHADER_GB_BLEND), path, tint_set),
            specular_strength=reify_attribute_or_float(
                input(SHADER_GB_SPECULAR_STRENGTH), path, tint_set
            ),
            collision_shading=reify_attribute_or_float(
                input(SHADER_GB_COLLISION_SHADING), path, tint_set
            ),
            distance=shader_node.geom_block_type,
            is_collision=is_collision,
            is_invisible=is_invisible,
        )
    elif mesh_type is RBRMeshMaterialType.OBJECT_BLOCK:
        texture = reify_rbr_texture(input(SHADER_OB_TEXTURE_1), path, tint_set)
        if texture is None:
            raise ReifyMaterialError(
                "Missing texture input to RBR object block shader node",
                node_ref(shader_node, path),
            )
        [u_clamp, v_clamp, u_mirror, v_mirror] = reify_texture_address(
            input(SHADER_OB_TEXTURE_1), None, path, tint_set
        )
        return ObjectBlockMaterial(
            texture=texture,
            object_block_type=shader_node.object_block_type,
            color=reify_attribute_or_color(input(SHADER_OB_COLOR), path, tint_set),
            alpha=reify_attribute_or_float(input(SHADER_OB_ALPHA), path, tint_set),
            sway_frequency=reify_attribute_or_float(
                input(SHADER_OB_SWAY_FREQ), path, tint_set
            ),
            sway_amplitude=reify_attribute_or_float(
                input(SHADER_OB_SWAY_AMP), path, tint_set
            ),
            sway_phase=reify_attribute_or_float(
                input(SHADER_OB_SWAY_PHASE), path, tint_set
            ),
            no_culling=not material.use_backface_culling,
            u_clamp=u_clamp,
            v_clamp=v_clamp,
            u_mirror=u_mirror,
            v_mirror=v_mirror,
        )
    elif mesh_type is RBRMeshMaterialType.REFLECTION_OBJECT:
        return reify_object_data_material(
            material,
            shader_node,
            path,
            SHADER_RO_SOCKETS,
            tint_set,
            ReflectionObjectMaterial,
        )
    elif mesh_type is RBRMeshMaterialType.SUPER_BOWL:
        return reify_object_data_material(
            material, shader_node, path, SHADER_SB_SOCKETS, tint_set, SuperBowlMaterial
        )
    elif mesh_type is RBRMeshMaterialType.WATER_OBJECT:
        return reify_object_data_material(
            material,
            shader_node,
            path,
            SHADER_WO_SOCKETS,
            tint_set,
            WaterObjectMaterial,
        )
    else:
        raise NotImplementedError(mesh_type)


def instance_attributes(names: List[str]) -> InstanceAttributes:
    return InstanceAttributes(bpy.context.evaluated_depsgraph_get(), names)


def instance_attribute_values(
    attributes: InstanceAttributes,
    object: bpy.types.Object,
    instancer: Optional[bpy.types.Object],
    persistent_id: List[int],
    from_particles: bool,
    lookups: List[Tuple[str, bool]],
) -> Tuple[Optional[List[RGBA]], Optional[str]]:
    """The value of each (attribute, from instancer) lookup for one instance,
    or why they can't be looked up."""
    try:
        return [
            attributes.lookup(
                object, instancer, persistent_id, from_particles, name, from_instancer
            )
            for name, from_instancer in lookups
        ], None
    except UnsupportedInstanceAttribute as e:
        return None, str(e)


def register_export_message(
    object: Optional[bpy.types.Object],
    instancer: Optional[bpy.types.Object],
    select_kind: str,
    select_indices: List[int],
    material: Optional[bpy.types.Material],
    node_name: str,
    message: str,
    severity: str,
) -> None:
    if bpy.context.scene is None:
        return
    scene_settings: RBRSceneSettings = bpy.context.scene.rbr_scene_settings
    err: RBRExportMessage
    if severity == "warning":
        err = scene_settings.export_warnings.add()
    else:
        err = scene_settings.export_errors.add()
    err.message = message
    err.object = object
    err.instancer = instancer
    err.material = material
    err.node_name = node_name
    err.select_kind = select_kind
    for index in select_indices:
        err.select_indices.add().index = index
