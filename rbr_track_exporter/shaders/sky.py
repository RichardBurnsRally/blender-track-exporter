"""A shader node equivalent for the RBR SkyDome shader."""

import math
from typing import Optional, Tuple, Union
from dataclasses import dataclass

import bpy
from ..blender_utils import group_output, local_node_group, narrow, new_node, socket

from .utils import *

SKY_NODE_TREE_NAME: str = ".RBRSkyNodeTreeV0"


def vec_spherical_to_cubemap(
    node_tree: bpy.types.NodeTree,
    in_vec: bpy.types.NodeSocket,
) -> bpy.types.NodeSocketVector:
    separate_xyz = new_node(node_tree.nodes, bpy.types.ShaderNodeSeparateXYZ)
    node_tree.links.new(in_vec, socket(separate_xyz.inputs, "Vector"))
    in_axes = separate_xyz.outputs
    in_vec_abs = vector_abs(node_tree, in_vec)
    separate_xyz = new_node(node_tree.nodes, bpy.types.ShaderNodeSeparateXYZ)
    node_tree.links.new(in_vec_abs, socket(separate_xyz.inputs, "Vector"))
    in_axes_abs = separate_xyz.outputs

    def axis(
        a: str,
        b: str,
        c: str,
        pos_mul: Tuple[float, float],
        pos_offset: float,
        neg_mul: Tuple[float, float],
        neg_offset: float,
    ) -> bpy.types.NodeSocketVector:
        in_a = socket(in_axes, a)
        in_b = socket(in_axes, b)
        in_c = socket(in_axes, c)
        in_a_abs = socket(in_axes_abs, a)
        in_b_abs = socket(in_axes_abs, b)
        in_c_abs = socket(in_axes_abs, c)

        a_gt_b = binary_math(node_tree, "GREATER_THAN", in_a_abs, in_b_abs)
        a_gt_c = binary_math(node_tree, "GREATER_THAN", in_a_abs, in_c_abs)
        a_active = float_multiply(node_tree, a_gt_b, a_gt_c)

        u = float_divide(node_tree, in_b, in_a)
        v = float_divide(node_tree, in_c, in_a)
        uv_node = new_node(node_tree.nodes, bpy.types.ShaderNodeCombineXYZ)
        node_tree.links.new(socket(uv_node.inputs, "X"), u)
        node_tree.links.new(socket(uv_node.inputs, "Y"), v)
        uv = socket(uv_node.outputs, "Vector")

        pos = vector_multiply(
            node_tree, uv, [1 / 12 * pos_mul[0], 1 / 2 * pos_mul[1], 0]
        )
        pos = vector_add(node_tree, pos, [1 / 12 + 1 / 6 * pos_offset, 1 / 2, 0])
        neg = vector_multiply(
            node_tree, uv, [1 / 12 * neg_mul[0], 1 / 2 * neg_mul[1], 0]
        )
        neg = vector_add(node_tree, neg, [1 / 12 + 1 / 6 * neg_offset, 1 / 2, 0])

        is_pos = binary_math(node_tree, "GREATER_THAN", in_a, 0)
        is_pos = float_multiply(node_tree, is_pos, a_active)
        is_neg = binary_math(node_tree, "LESS_THAN", in_a, 0)
        is_neg = float_multiply(node_tree, is_neg, a_active)

        pos = vector_scale(node_tree, pos, is_pos)
        neg = vector_scale(node_tree, neg, is_neg)
        return vector_add(node_tree, pos, neg)

    # The cubemap is laid out like [+X][-Y][-X][+Y][+Z][-Z]
    # Z axes are rendered with Y up.
    result_x = axis("X", "Y", "Z", (-1, 1), 0, (-1, -1), 2)
    result_y = axis("Y", "X", "Z", (1, 1), 3, (1, -1), 1)
    result_z = axis("Z", "X", "Y", (-1, 1), 4, (1, 1), 5)

    result = vector_add(node_tree, result_x, result_y)
    result = vector_add(node_tree, result_z, result)
    return result


@dataclass
class ScatteringCoefficients:
    mul_scattering: bpy.types.NodeSocket
    add_scattering: bpy.types.NodeSocket


def scattering(
    node_tree: bpy.types.NodeTree,
    light_dir: bpy.types.NodeSocketVector,
    # Different scale for different object types
    # 1.0 for everything except superbowl
    scale: Union[float, bpy.types.NodeSocketFloat],
    view_depth: Optional[bpy.types.NodeSocketFloat] = None,
) -> ScatteringCoefficients:
    geo_node = new_node(node_tree.nodes, bpy.types.ShaderNodeNewGeometry)

    turbidity = rbr_world_float(node_tree, "turbidity")
    if view_depth is None:
        camera_data = new_node(node_tree.nodes, bpy.types.ShaderNodeCameraData)
        view_depth = narrow(
            socket(camera_data.outputs, "View Z Depth"), bpy.types.NodeSocketFloat
        )
    view_vector = socket(geo_node.outputs, "Incoming")
    scattering_depth = float_multiply(node_tree, view_depth, scale)
    r1, rayleigh_mie = setup_rayleigh_mie_nodes(
        node_tree=node_tree,
        view_vector=view_vector,
        turbidity=turbidity,
        scattering_depth=scattering_depth,
        light_dir=light_dir,
    )
    # Terrain reflectance
    terrain_reflectance_multiplier = rbr_world_float(
        node_tree, "terrain_reflectance_multiplier"
    )
    terrain_reflectance_color = rbr_world_color(node_tree, "terrain_reflectance_color")
    terrain_reflectance = vector_scale(
        node_tree, terrain_reflectance_color, terrain_reflectance_multiplier
    )
    # Inscattering
    inscattering = rbr_world_float(node_tree, "inscattering")
    # Transmittance
    transmittance = setup_transmittance_nodes(
        node_tree=node_tree,
        turbidity=turbidity,
        light_dir=light_dir,
    )
    # Sun intensity
    sun_intensity = rbr_world_float(node_tree, "sun_intensity")

    add_result = vector_scale(node_tree, vector=rayleigh_mie, scale=inscattering)
    add_result = vector_multiply(node_tree, v1=add_result, v2=transmittance)
    add_result = vector_scale(node_tree, vector=add_result, scale=sun_intensity)

    # MULTIPLY
    mul_result = vector_multiply(node_tree, v1=r1, v2=terrain_reflectance)
    # Extinction
    extinction = rbr_world_float(node_tree, "extinction")
    mul_result = vector_scale(node_tree, vector=mul_result, scale=extinction)
    # Multiply transmittance
    mul_result = vector_multiply(node_tree, v1=mul_result, v2=transmittance)
    mul_result = vector_scale(node_tree, vector=mul_result, scale=sun_intensity)

    return ScatteringCoefficients(
        mul_scattering=mul_result,
        add_scattering=add_result,
    )


def linear_fog(
    node_tree: bpy.types.NodeTree,
    input: bpy.types.NodeSocketColor,
    is_superbowl: bool,
    view_depth: Optional[bpy.types.NodeSocketFloat] = None,
) -> bpy.types.NodeSocketColor:
    fog_start = rbr_world_float(
        node_tree, "superbowl_fog_start" if is_superbowl else "fog_start"
    )
    fog_end = rbr_world_float(
        node_tree, "superbowl_fog_end" if is_superbowl else "fog_end"
    )
    if view_depth is None:
        camera_data = new_node(node_tree.nodes, bpy.types.ShaderNodeCameraData)
        view_depth = narrow(
            socket(camera_data.outputs, "View Z Depth"), bpy.types.NodeSocketFloat
        )
    fog_numerator = float_subtract(node_tree, fog_end, view_depth)
    fog_denominator = float_subtract(node_tree, fog_end, fog_start)
    fog_calc = float_divide(node_tree, fog_numerator, fog_denominator)
    use_fog = rbr_world_float(node_tree, "use_fog")
    inv_fog = float_subtract(node_tree, 1.0, use_fog)
    fog_mix = float_max(node_tree, fog_calc, inv_fog)
    fog_color = rbr_world_color(node_tree, "fog_color")
    return narrow(
        mix_rgb(node_tree, fog_mix, fog_color, input, "MIX"), bpy.types.NodeSocketColor
    )


def make_wavelength(node_tree: bpy.types.NodeTree) -> bpy.types.NodeSocket:
    wavelength = new_node(node_tree.nodes, bpy.types.ShaderNodeCombineXYZ)
    socket(wavelength.inputs, "X").default_value = 0.65
    socket(wavelength.inputs, "Y").default_value = 0.57
    socket(wavelength.inputs, "Z").default_value = 0.475
    return socket(wavelength.outputs, "Vector")


def setup_transmittance_nodes(
    node_tree: bpy.types.NodeTree,
    turbidity: bpy.types.NodeSocketFloat,
    light_dir: bpy.types.NodeSocketVector,
) -> bpy.types.NodeSocketVector:
    # Compute Z (apparent solar zenith angle)
    # Z = sun polar angle - an offset derived from tracksettings
    sep_light_dir = new_node(node_tree.nodes, bpy.types.ShaderNodeSeparateXYZ)
    node_tree.links.new(light_dir, socket(sep_light_dir.inputs, "Vector"))
    light_dir_up = socket(sep_light_dir.outputs, "Z")
    # polar angle of the sun in spherical coordinates
    polar_angle = unary_math(node_tree, "ARCCOSINE", light_dir_up)
    # offset computed from tracksettings value
    sun_offset = rbr_world_float(node_tree, "sun_offset")
    sun_offset = float_multiply(node_tree, sun_offset, math.pi / 9)
    sun_offset = float_max(node_tree, sun_offset, 0.0)
    sun_offset = float_min(node_tree, sun_offset, 2 * math.pi)
    Z = float_subtract(node_tree, polar_angle, sun_offset)
    # Compute M (relative air mass)
    cosZ = unary_math(node_tree, "COSINE", Z)
    degZ = float_multiply(node_tree, Z, 180.0 / math.pi)
    deg_sub = float_subtract(node_tree, 93.885, degZ)
    deg_pow = float_pow(node_tree, deg_sub, -1.253)
    deg_mul = float_multiply(node_tree, deg_pow, 0.15)
    add_cosZ = float_add(node_tree, cosZ, deg_mul)
    M = float_pow(node_tree, add_cosZ, -1.0)
    # Compute T_a (aerosol scattering contribution)
    turbidity_mul = float_multiply(node_tree, turbidity, 0.046083659)
    B = float_subtract(node_tree, turbidity_mul, 0.045860261)
    negateB = float_multiply(node_tree, B, -1.0)
    negateBM = float_multiply(node_tree, negateB, M)
    wavelength = make_wavelength(node_tree)
    wavelength_Ta = vector_power(node_tree, exponent=-1.3, vector=wavelength)
    T_a = vector_scale(node_tree, vector=wavelength_Ta, scale=negateBM)
    # Compute T_r (rayleigh scattering contribution)
    wavelength_Tr = vector_power(node_tree, exponent=-4.08, vector=wavelength)
    rayleighM = float_multiply(node_tree, M, -0.008735)
    T_r = vector_scale(node_tree, vector=wavelength_Tr, scale=rayleighM)
    # Compute transmittance
    add_Ta_Tr = vector_add(node_tree, T_a, T_r)
    return vector_exp(node_tree, add_Ta_Tr)


def setup_rayleigh_mie_nodes(
    node_tree: bpy.types.NodeTree,
    view_vector: bpy.types.NodeSocket,
    turbidity: bpy.types.NodeSocketFloat,
    scattering_depth: bpy.types.NodeSocketFloat,
    light_dir: bpy.types.NodeSocketVector,
) -> Tuple[bpy.types.NodeSocketVector, bpy.types.NodeSocketVector]:
    # The mixed Rayleigh-Mie values
    rayleigh_multiplier = rbr_world_float(node_tree, "rayleigh_multiplier")
    scaled_rayleigh_mixed = vector_scale(
        node_tree,
        vector=(
            0.00069715281,
            0.0011789137,
            0.0024445958,
        ),
        scale=rayleigh_multiplier,
    )
    mie_multiplier = rbr_world_float(node_tree, "mie_multiplier")
    mie_turbidity = float_multiply(node_tree, turbidity, 6.544)
    mie_turbidity = float_subtract(node_tree, mie_turbidity, 6.510)
    mie_contribution_mixed = vector_scale(
        node_tree,
        vector=(
            1.6213017e12 * 1.3634512 * 39.47842 * 9.99999983775159e-18,
            2.089874e12 * 1.3634512 * 39.47842 * 9.99999983775159e-18,
            2.9695295e12 * 1.3634512 * 39.47842 * 9.99999983775159e-18,
        ),
        scale=mie_turbidity,
    )
    scaled_mie_mixed = vector_scale(
        node_tree, vector=mie_contribution_mixed, scale=mie_multiplier
    )
    rayleigh_mie_mixed = vector_add(
        node_tree, v1=scaled_rayleigh_mixed, v2=scaled_mie_mixed
    )
    inverse_rayleigh_mie_mixed = vector_math(
        node_tree, "DIVIDE", v1=(1.0, 1.0, 1.0), v2=rayleigh_mie_mixed
    )

    # Rayleigh contributions
    cos_theta_dot = vector_math_float(
        node_tree, "DOT_PRODUCT", v1=view_vector, v2=light_dir
    )
    cos_theta = float_min(node_tree, cos_theta_dot, 0.0)
    cos_theta_sq = float_multiply(node_tree, cos_theta, cos_theta)
    rayleigh_phase = float_add(node_tree, cos_theta_sq, 1.0)
    rayleigh = vector_scale(
        node_tree,
        vector=(
            0.00004160824,
            0.000070361231,
            0.00014590107,
        ),
        scale=rayleigh_multiplier,
    )
    rayleigh_cont = vector_scale(node_tree, vector=rayleigh, scale=rayleigh_phase)
    # Greenstein values
    greenstein_value = rbr_world_float(node_tree, "greenstein_value")
    greenstein_x = float_multiply(node_tree, greenstein_value, greenstein_value)
    greenstein_x = float_subtract(node_tree, 1.0, greenstein_x)
    greenstein_y = float_add(node_tree, greenstein_value, 1.0)
    greenstein_z = float_multiply(node_tree, greenstein_value, 2.0)
    # Henyey-Greenstein phase function
    hg_denominator = float_multiply(node_tree, greenstein_z, cos_theta)
    hg_denominator = float_add(node_tree, hg_denominator, greenstein_y)
    hg_denominator = unary_math(node_tree, "ABSOLUTE", in1=hg_denominator)
    hg_denominator = float_pow(node_tree, hg_denominator, -1.5)
    henyey_greenstein_phase = float_multiply(node_tree, hg_denominator, greenstein_x)
    # Mie contributions
    mie_contribution = vector_scale(
        node_tree,
        vector=(
            2.3668638e12 * 0.217 * 39.47842 * 9.99999983775159e-18,
            3.0778702e12 * 0.217 * 39.47842 * 9.99999983775159e-18,
            4.4321331e12 * 0.217 * 39.47842 * 9.99999983775159e-18,
        ),
        scale=mie_turbidity,
    )
    mie = vector_scale(node_tree, vector=mie_contribution, scale=mie_multiplier)
    mie_cont = vector_scale(node_tree, vector=mie, scale=henyey_greenstein_phase)
    # Combined Rayleigh-Mie
    add_rayleigh_mie = vector_add(node_tree, v1=rayleigh_cont, v2=mie_cont)
    negate_scattering_depth = float_multiply(node_tree, scattering_depth, -1.0)
    rayleigh_mie_scaled = vector_scale(
        node_tree, vector=rayleigh_mie_mixed, scale=negate_scattering_depth
    )
    # Construct the result
    r1 = vector_exp(node_tree, rayleigh_mie_scaled)
    result = vector_subtract(node_tree, v1=(1.0, 1.0, 1.0), v2=r1)
    result = vector_multiply(node_tree, v1=add_rayleigh_mie, v2=result)
    result = vector_multiply(node_tree, v1=result, v2=inverse_rayleigh_mie_mixed)
    return (r1, result)


def set_clouds_images() -> None:
    existing_tree = local_node_group(SKY_NODE_TREE_NAME)
    if existing_tree is not None:
        clouds = existing_tree.nodes.get(".rbr.clouds")
        if isinstance(clouds, bpy.types.ShaderNodeTexImage):
            clouds.image = bpy.data.images.get(".rbr.clouds")
        depth = existing_tree.nodes.get(".rbr.clouds.depth")
        if isinstance(depth, bpy.types.ShaderNodeTexImage):
            depth.image = bpy.data.images.get(".rbr.clouds.depth")


def recreate_internals() -> None:
    existing_tree = local_node_group(SKY_NODE_TREE_NAME)
    if existing_tree is not None:
        setup_sky_node_tree(existing_tree)


def setup_sky_node_tree(node_tree: bpy.types.NodeTree) -> None:
    # Reset if already present
    node_tree.links.clear()
    output_exists = False
    for node in node_tree.nodes:
        if isinstance(node, bpy.types.NodeGroupOutput):
            output_exists = True
            continue
        node_tree.nodes.remove(node)
    # Create the internal group output node
    if not output_exists:
        new_node(node_tree.nodes, bpy.types.NodeGroupOutput)
    # Adjust the output sockets (this also adjusts the group outputs)
    seen_surface_output = False
    for item in node_tree.interface.items_tree:
        if isinstance(item, bpy.types.NodeTreeInterfaceSocket):
            if item.in_out == "OUTPUT":
                if item.name == "Surface" and not seen_surface_output:
                    seen_surface_output = True
                    continue
        node_tree.interface.remove(item)
    if not seen_surface_output:
        node_tree.interface.new_socket(
            "Surface", in_out="OUTPUT", socket_type="NodeSocketShader"
        )

    # Create the internal nodes
    light_dir = rbr_world_vector(node_tree, "light_direction")
    skybox_scale = rbr_world_float(node_tree, "skybox_scale")
    geometry = new_node(node_tree.nodes, bpy.types.ShaderNodeNewGeometry)
    view_vector = socket(geometry.outputs, "Incoming")

    # Compute depth to scattering point
    # Flip the view vector around
    flipped_view_vec = new_node(node_tree.nodes, bpy.types.ShaderNodeVectorMath)
    flipped_view_vec.operation = "SCALE"
    socket(flipped_view_vec.inputs, "Scale").default_value = -1.0
    node_tree.links.new(
        socket(geometry.outputs, "Incoming"),
        socket(flipped_view_vec.inputs, "Vector", 0),
    )
    # Go from world to camera space
    transform = new_node(node_tree.nodes, bpy.types.ShaderNodeVectorTransform)
    transform.vector_type = "VECTOR"
    transform.convert_from = "WORLD"
    transform.convert_to = "CAMERA"
    node_tree.links.new(
        socket(flipped_view_vec.outputs, "Vector"), socket(transform.inputs, "Vector")
    )
    # Separate out Z (depth)
    view_vec_z_node = new_node(node_tree.nodes, bpy.types.ShaderNodeSeparateXYZ)
    node_tree.links.new(
        socket(transform.outputs, "Vector"), socket(view_vec_z_node.inputs, "Vector")
    )
    view_vec_z = socket(view_vec_z_node.outputs, "Z")
    view_dome_z = float_multiply(node_tree, view_vec_z, 100.0)
    scattering_depth = float_multiply(node_tree, view_dome_z, skybox_scale)
    # Rayleigh-Mie scattering
    turbidity = rbr_world_float(node_tree, "turbidity")
    _, rayleigh_mie = setup_rayleigh_mie_nodes(
        node_tree=node_tree,
        view_vector=view_vector,
        turbidity=turbidity,
        scattering_depth=scattering_depth,
        light_dir=light_dir,
    )
    # Multiply inscattering
    inscattering = rbr_world_float(node_tree, "inscattering")
    sky_result = vector_scale(node_tree, vector=rayleigh_mie, scale=inscattering)
    # Multiply transmittance
    transmittance = setup_transmittance_nodes(node_tree, turbidity, light_dir)
    sky_result = vector_multiply(node_tree, v1=sky_result, v2=transmittance)
    # Multiply sun intensity
    sun_intensity = rbr_world_float(node_tree, "sun_intensity")
    sky_result = vector_scale(node_tree, vector=sky_result, scale=sun_intensity)
    sky_result = vector_math(node_tree, "MINIMUM", v1=sky_result, v2=(1.0, 1.0, 1.0))

    # Clouds
    geometry = new_node(node_tree.nodes, bpy.types.ShaderNodeNewGeometry)
    cubemap_vec = vec_spherical_to_cubemap(
        node_tree, socket(geometry.outputs, "Position")
    )
    clouds = new_node(node_tree.nodes, bpy.types.ShaderNodeTexImage)
    clouds.name = ".rbr.clouds"
    clouds.image = bpy.data.images.get(".rbr.clouds")
    clouds.interpolation = "Closest"
    node_tree.links.new(socket(clouds.inputs, "Vector"), cubemap_vec)
    clouds_depth_node = new_node(node_tree.nodes, bpy.types.ShaderNodeTexImage)
    clouds_depth_node.name = ".rbr.clouds.depth"
    clouds_depth_node.image = bpy.data.images.get(".rbr.clouds.depth")
    clouds_depth_node.interpolation = "Closest"
    node_tree.links.new(socket(clouds_depth_node.inputs, "Vector"), cubemap_vec)
    clouds_depth = float_divide(
        node_tree,
        socket(clouds_depth_node.outputs, "Color"),
        float_max(node_tree, socket(clouds_depth_node.outputs, "Alpha"), 0.0001),
    )
    clouds_depth = float_multiply(node_tree, clouds_depth, 100.0)
    clouds_depth = float_multiply(node_tree, clouds_depth, view_vec_z)
    clouds_alpha = socket(clouds.outputs, "Alpha")
    clouds_color = vector_math(
        node_tree,
        "DIVIDE",
        v1=socket(clouds.outputs, "Color"),
        v2=float_max(node_tree, clouds_alpha, 0.0001),
    )
    # Scattering for clouds
    scattering_coefficients = scattering(
        node_tree=node_tree,
        light_dir=rbr_world_vector(node_tree, "light_direction"),
        scale=rbr_world_float(node_tree, "cloud_scale"),
        view_depth=clouds_depth,
    )
    clouds_result = mix_rgb(
        node_tree,
        1.0,
        clouds_color,
        scattering_coefficients.mul_scattering,
        "MULTIPLY",
        True,
    )
    clouds_result = mix_rgb(
        node_tree,
        1.0,
        clouds_result,
        scattering_coefficients.add_scattering,
        "ADD",
        True,
    )

    # Sky + clouds
    result: bpy.types.NodeSocket = mix_rgb(
        node_tree, fac=clouds_alpha, a=sky_result, b=clouds_result, blend_type="MIX"
    )
    # Fog
    skybox_saturation = rbr_world_float(node_tree, "skybox_saturation")
    use_fog = rbr_world_float(node_tree, "use_fog")
    inv_fog = float_subtract(node_tree, 1.0, use_fog)
    fog_mix = float_max(node_tree, skybox_saturation, inv_fog)
    fog_color = rbr_world_color(node_tree, "fog_color")
    result = mix_rgb(
        node_tree, fac=fog_mix, a=fog_color, b=result, blend_type="MIX", clamp=True
    )
    result = srgb_to_linear(node_tree, result)
    # Link to output
    node_tree.links.new(
        socket(group_output(node_tree).inputs, "Surface"),
        result,
    )


class ShaderNodeRBRSky(bpy.types.ShaderNodeCustomGroup):
    bl_name = "ShaderNodeRBRSky"
    bl_label = "RBR Sky"
    # This is a field of ShaderNodeCustomGroup
    node_tree: Optional[bpy.types.ShaderNodeTree] = None

    def init(self, context: Optional[bpy.types.Context]) -> None:
        existing_tree = local_node_group(SKY_NODE_TREE_NAME)
        if isinstance(existing_tree, bpy.types.ShaderNodeTree):
            self.node_tree = existing_tree
        else:
            self.node_tree = narrow(
                bpy.data.node_groups.new(SKY_NODE_TREE_NAME, "ShaderNodeTree"),
                bpy.types.ShaderNodeTree,
            )
            setup_sky_node_tree(self.node_tree)

    def free(self) -> None:
        return

    def draw_buttons(
        self, context: bpy.types.Context, layout: bpy.types.UILayout
    ) -> None:
        return


def register() -> None:
    bpy.utils.register_class(ShaderNodeRBRSky)


def unregister() -> None:
    bpy.utils.unregister_class(ShaderNodeRBRSky)
