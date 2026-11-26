"""A shader node for RBR textures.

A key property of this is we can dynamically switch out which texture (e.g.
dry/damp/wet) is rendered in the viewport by changing some scene properties.
"""

from typing import Any, Dict, List, Iterable, Optional, Set, Tuple, Union
import math

import bpy
from ..blender_utils import group_input, group_output, narrow, new_node, socket
from ..types import OperatorReturn

from ..types import SurfaceType, SurfaceAge
from ..physical_material_editor.operator import RBR_OT_edit_material_maps
from ..physical_material_editor.properties import (
    RBRPropertyNodePointer,
    RBRMaterialMaps,
    RBRFallbackMaterials,
    RBRMaterialPicker,
)
from .utils import linear_to_srgb, magic_link, make_math_node

RBR_TEXTURE_NODE_TREE_PREFIX: str = ".RBRTextureV0."

# Texture address mode inputs, in .lbs render state flag order. They are
# hidden sockets on the texture node: the material's per-texture value lives
# in the socket default, the shared texture tree reads it through the group
# input, and the exporter reads it back from the node.
TEXTURE_ADDRESS_SOCKETS: Tuple[str, str, str, str] = (
    "U Clamp",
    "V Clamp",
    "U Mirror",
    "V Mirror",
)
TEXTURE_ADDRESS_DESCRIPTIONS = (
    "Clamp the texture horizontally instead of repeating it (wins over mirror)",
    "Clamp the texture vertically instead of repeating it (wins over mirror)",
    "Mirror the texture horizontally on every repeat",
    "Mirror the texture vertically on every repeat",
)
# Material types whose game materials apply the address modes.
TEXTURE_ADDRESS_MESH_TYPES = ("OBJECT_BLOCK", "SUPER_BOWL", "INTERACTIVE_OBJECT_VISUAL")


def get_texture_address(node: bpy.types.Node) -> Tuple[bool, bool, bool, bool]:
    [u_clamp, v_clamp, u_mirror, v_mirror] = [
        bool(socket(node.inputs, name).default_value)
        for name in TEXTURE_ADDRESS_SOCKETS
    ]
    return (u_clamp, v_clamp, u_mirror, v_mirror)


def set_texture_address(
    node: bpy.types.Node, texture_address: Tuple[bool, bool, bool, bool]
) -> None:
    for name, value in zip(TEXTURE_ADDRESS_SOCKETS, texture_address):
        socket(node.inputs, name).default_value = value


TEXTURE_FORMAT_ITEMS = [
    (
        "DXT1",
        "DXT1 (opaque)",
        "Opaque texture. Use this unless you need transparency.",
    ),
    (
        "DXT1_1BIT",
        "DXT1 (1-bit alpha)",
        "Cutout alpha. Half the vram cost of DXT3, at the cost of possible colour banding.",
    ),
    (
        "DXT3",
        "DXT3 (sharp alpha)",
        "16-level alpha. Use for sharp alpha transitions when DXT1 1-bit isn't appropriate.",
    ),
    (
        "DXT5",
        "DXT5 (smooth alpha)",
        "Best for smooth alpha gradients.",
    ),
]


def suggested_size(x: int) -> int:
    """Get the closest size for fast loading in RBR (power of two)"""
    if x <= 0:
        return 0
    s: int = 2 ** math.ceil(math.log2(x))
    return s


def recreate_internals(
    context: bpy.types.Context,
    node_tree: bpy.types.NodeTree,
) -> None:
    node_tree.links.clear()
    old_internal = None
    images = dict()
    for node in node_tree.nodes:
        if isinstance(node, bpy.types.NodeGroupInput):
            continue
        if isinstance(node, bpy.types.NodeGroupOutput):
            continue
        if isinstance(node, ShaderNodeRBRTextureInternal):
            node.name = "old_internal"
            old_internal = node
            continue
        if isinstance(node, bpy.types.ShaderNodeTexImage):
            images[node.name] = node.image
        node_tree.nodes.remove(node)
    node_tree.interface.clear()
    create_sockets(node_tree)
    make_nodes_and_links(node_tree)
    is_road_surface = False
    if old_internal is not None:
        is_road_surface = old_internal.is_road_surface
    active_name = context_active_image_name(
        context=context,
        is_road_surface=is_road_surface,
    )
    if old_internal is not None:
        internal = narrow(node_tree.nodes["internal"], ShaderNodeRBRTextureInternal)
        internal.is_road_surface = old_internal.is_road_surface
        internal.texture_format = old_internal.texture_format
        internal.mip_levels = old_internal.mip_levels
        internal.passthrough_dds = old_internal.passthrough_dds
        set_format_alpha_mode(node_tree, old_internal.texture_format)
        for original in old_internal.material_maps:
            new = internal.material_maps.add()
            new.copy(original)
        for condition in FALLBACK_CONDITIONS:
            getattr(internal.fallback_materials, condition).material_id = getattr(
                old_internal.fallback_materials, condition
            ).material_id
        node_tree.nodes.remove(old_internal)
    for name, image in images.items():
        narrow(node_tree.nodes[name], bpy.types.ShaderNodeTexImage).image = image
    link_texture_for_tree(node_tree, active_name)


FALLBACK_CONDITIONS = (
    "dry_new",
    "damp_new",
    "wet_new",
    "dry_normal",
    "damp_normal",
    "wet_normal",
    "dry_worn",
    "damp_worn",
    "wet_worn",
)

# The texture node's one output: a bundle of the texture's colour and alpha,
# and Present, which reads 1 wherever a texture is connected and 0 (the
# bundle's fallback) where nothing is.
RBR_TEXTURE_OUTPUT: str = "Texture"
TEXTURE_BUNDLE_COLOR: str = "Color"
TEXTURE_BUNDLE_ALPHA: str = "Alpha"
TEXTURE_BUNDLE_PRESENT: str = "Present"


def create_sockets(node_tree: bpy.types.NodeTree) -> None:
    # Add the input and output sockets (this also adjusts the group
    # inputs/outputs)
    uv_socket = node_tree.interface.new_socket(
        "UV", in_out="INPUT", socket_type="NodeSocketVector"
    )
    uv_socket.hide_value = True
    for name, description in zip(TEXTURE_ADDRESS_SOCKETS, TEXTURE_ADDRESS_DESCRIPTIONS):
        flag = node_tree.interface.new_socket(
            name, in_out="INPUT", socket_type="NodeSocketBool"
        )
        flag.description = description
    node_tree.interface.new_socket(
        RBR_TEXTURE_OUTPUT, in_out="OUTPUT", socket_type="NodeSocketBundle"
    )


def setup_texture_node_tree(
    context: bpy.types.Context,
    name: str,
    is_road_surface: bool,
    mip_levels: int = 0,
    texture_format: str = "DXT1",
    images: Dict[Tuple[str, str], bpy.types.Image] = dict(),
    passthrough_dds: bool = False,
) -> bpy.types.NodeTree:
    node_tree = bpy.data.node_groups.new(
        RBR_TEXTURE_NODE_TREE_PREFIX + name, "ShaderNodeTree"
    )
    # Create the internal group input and output nodes
    new_node(node_tree.nodes, bpy.types.NodeGroupInput)
    new_node(node_tree.nodes, bpy.types.NodeGroupOutput)
    create_sockets(node_tree)
    make_nodes_and_links(node_tree, images)
    internal = narrow(node_tree.nodes["internal"], ShaderNodeRBRTextureInternal)
    internal.is_road_surface = is_road_surface
    internal.texture_format = texture_format
    internal.mip_levels = mip_levels
    internal.passthrough_dds = passthrough_dds
    set_format_alpha_mode(node_tree, texture_format)
    link_context_active_texture(context, node_tree)
    return node_tree


def link_context_active_texture(
    context: bpy.types.Context,
    node_tree: bpy.types.NodeTree,
) -> None:
    internal = node_tree.nodes.get("internal")
    if internal is None:
        raise RuntimeError("Missing internal node in texture node tree")
    if not isinstance(internal, ShaderNodeRBRTextureInternal):
        raise RuntimeError("Internal node has wrong type")
    name = context_active_image_name(
        context=context,
        is_road_surface=internal.is_road_surface,
    )
    link_texture_for_tree(node_tree, name)


def make_nodes_and_links(
    node_tree: bpy.types.NodeTree,
    images: Dict[Tuple[str, str], bpy.types.Image] = dict(),
) -> None:
    # Get user inputs
    inputs = group_input(node_tree).outputs
    uv_in = address_uv(node_tree, socket(inputs, "UV"), inputs)

    internal = node_tree.nodes.new("ShaderNodeRBRTextureInternal")
    internal.name = "internal"

    for surface_type in SurfaceType:
        for surface_age in SurfaceAge:
            # super bowl textures are interpolation=closest with 2 textures
            # https://discord.com/channels/753877988122034177/934412614723858502/1166391681545949306
            # I consider this a game bug so we can continue with linear
            tex_image = new_node(node_tree.nodes, bpy.types.ShaderNodeTexImage)
            tex_image.image = images.get(
                (surface_type.name.lower(), surface_age.name.lower())
            )
            node_tree.links.new(socket(tex_image.inputs, "Vector"), uv_in)
            tex_image.name = surface_type.name.lower() + "/" + surface_age.name.lower()

    # Convert to sRGB. The input value is linear (regardless of image
    # colorspace, blender has already converted it before this point).
    # RBR does calculations in sRGB space, so we mimic that.
    convert_out = linear_to_srgb(node_tree, "sRGBConverter")
    # The connection of the image to the converter and the alpha to the format
    # alpha chain is done in 'link_texture_for_tree'
    bundle = new_node(node_tree.nodes, bpy.types.NodeCombineBundle)
    bundle.bundle_items.new("RGBA", TEXTURE_BUNDLE_COLOR)
    bundle.bundle_items.new("FLOAT", TEXTURE_BUNDLE_ALPHA)
    bundle.bundle_items.new("FLOAT", TEXTURE_BUNDLE_PRESENT)
    socket(bundle.inputs, TEXTURE_BUNDLE_PRESENT).default_value = 1.0
    node_tree.links.new(socket(bundle.inputs, TEXTURE_BUNDLE_COLOR), convert_out)
    node_tree.links.new(
        socket(bundle.inputs, TEXTURE_BUNDLE_ALPHA), format_alpha(node_tree)
    )
    node_tree.links.new(
        socket(group_output(node_tree).inputs, RBR_TEXTURE_OUTPUT),
        socket(bundle.outputs, "Bundle"),
    )


FORMAT_ALPHA_IN: str = "formatAlphaIn"
FORMAT_ALPHA_MODE: str = "formatAlphaMode"
FORMAT_ALPHA_MODES: Dict[str, float] = {
    "DXT1": 0.0,
    "DXT1_1BIT": 1.0,
    "DXT3": 2.0,
    "DXT5": 2.0,
}


def format_alpha(node_tree: bpy.types.NodeTree) -> bpy.types.NodeSocket:
    """Shape the image alpha the way the export format will: DXT1 drops it,
    DXT1 1-bit quantises it at half, DXT3 and DXT5 keep it. The mode value
    node is set from the internal node's format."""
    alpha_in = new_node(node_tree.nodes, bpy.types.ShaderNodeMath)
    alpha_in.name = FORMAT_ALPHA_IN
    alpha_in.operation = "ADD"
    socket(alpha_in.inputs, "Value", 1).default_value = 0.0
    alpha = socket(alpha_in.outputs, "Value")
    mode_node = new_node(node_tree.nodes, bpy.types.ShaderNodeValue)
    mode_node.name = FORMAT_ALPHA_MODE
    mode = socket(mode_node.outputs, "Value")

    switch = new_node(node_tree.nodes, bpy.types.GeometryNodeIndexSwitch)
    switch.data_type = "FLOAT"
    switch.index_switch_items.new()
    node_tree.links.new(socket(switch.inputs, "Index"), mode)
    socket(switch.inputs, "0").default_value = 1.0
    node_tree.links.new(
        socket(switch.inputs, "1"),
        make_math_node(node_tree, "GREATER_THAN", alpha, 0.5),
    )
    node_tree.links.new(socket(switch.inputs, "2"), alpha)
    return socket(switch.outputs, "Output")


def set_format_alpha_mode(node_tree: bpy.types.NodeTree, texture_format: str) -> None:
    mode_node = node_tree.nodes.get(FORMAT_ALPHA_MODE)
    if mode_node is None:
        return
    socket(mode_node.outputs, "Value").default_value = FORMAT_ALPHA_MODES[
        texture_format
    ]


def address_uv(
    node_tree: bpy.types.NodeTree,
    uv: bpy.types.NodeSocket,
    inputs: bpy.types.NodeOutputs,
) -> bpy.types.NodeSocket:
    """Remap a UV the way the game's sampler address modes do: per axis,
    clamp to 0..1 if the clamp flag is set, else mirror every repeat if the
    mirror flag is set, else wrap (which the image node does itself)."""
    separate = new_node(node_tree.nodes, bpy.types.ShaderNodeSeparateXYZ)
    node_tree.links.new(socket(separate.inputs, "Vector"), uv)
    combine = new_node(node_tree.nodes, bpy.types.ShaderNodeCombineXYZ)
    socket(combine.inputs, "Z").default_value = 0.0

    def mix(
        factor: bpy.types.NodeSocket, a: bpy.types.NodeSocket, b: bpy.types.NodeSocket
    ) -> bpy.types.NodeSocket:
        node = new_node(node_tree.nodes, bpy.types.ShaderNodeMix)
        node.data_type = "FLOAT"
        node_tree.links.new(socket(node.inputs, "Factor"), factor)
        node_tree.links.new(socket(node.inputs, "A"), a)
        node_tree.links.new(socket(node.inputs, "B"), b)
        return socket(node.outputs, "Result")

    for axis, clamp_name, mirror_name in (
        ("X", "U Clamp", "U Mirror"),
        ("Y", "V Clamp", "V Mirror"),
    ):
        value = socket(separate.outputs, axis)
        mirrored = make_math_node(node_tree, "PINGPONG", value, 1.0)
        clamped = make_math_node(node_tree, "ADD", value, 0.0, clamp=True)
        remapped = mix(
            socket(inputs, clamp_name),
            mix(socket(inputs, mirror_name), value, mirrored),
            clamped,
        )
        node_tree.links.new(socket(combine.inputs, axis), remapped)
    return socket(combine.outputs, "Vector")


def context_active_image_name(context: bpy.types.Context, is_road_surface: bool) -> str:
    if context.scene is None:
        raise RuntimeError("No active scene")
    scene_settings = context.scene.rbr_scene_settings
    surface_type: SurfaceType = scene_settings.get_active_surface_type()
    surface_age: SurfaceAge = scene_settings.get_active_surface_age()
    if is_road_surface:
        return surface_type.name.lower() + "/" + surface_age.name.lower()
    else:
        return surface_type.name.lower() + "/" + SurfaceAge.NEW.name.lower()


def tree_name_to_texture_name(node_tree: bpy.types.NodeTree) -> Optional[str]:
    if not node_tree.name.startswith(RBR_TEXTURE_NODE_TREE_PREFIX):
        return None
    name: str = node_tree.name[len(RBR_TEXTURE_NODE_TREE_PREFIX) :]
    if node_tree.library is not None:
        return f"{name} [{node_tree.library.name}]"
    else:
        return name


def tree_name_to_texture_filename(
    node_tree: Optional[bpy.types.NodeTree],
) -> Optional[str]:
    """Return a filename suitable for RBR.
    It's still possible to have collisions between non-library and library
    names, but it's unlikely.
    """
    if node_tree is None:
        raise RuntimeError("ShaderNodeRBRTexture missing node tree")
    if not node_tree.name.startswith(RBR_TEXTURE_NODE_TREE_PREFIX):
        return None
    name: str = node_tree.name[len(RBR_TEXTURE_NODE_TREE_PREFIX) :]
    if node_tree.library is not None:
        lib_name = node_tree.library.name
        if lib_name.endswith(".blend"):
            lib_name = lib_name[0 : -len(".blend")]
        return f"{lib_name}-{name}"
    else:
        return name


def compute_max_mip_levels(internal: bpy.types.Node) -> int:
    node_tree = internal.id_data
    if not isinstance(node_tree, bpy.types.NodeTree):
        return 0
    max_dim = 0
    for node in node_tree.nodes:
        if isinstance(node, bpy.types.ShaderNodeTexImage) and node.image is not None:
            for dim in node.image.size:
                max_dim = max(max_dim, dim)
    if max_dim <= 0:
        return 0
    return int(math.floor(math.log2(max_dim))) + 1


def used_image_nodes(
    node_tree: bpy.types.NodeTree, is_road_surface: bool
) -> List[Tuple[str, bpy.types.ShaderNodeTexImage]]:
    """The texture's image nodes that hold an image and are exported, with the
    subdirectory each is exported to."""
    ages = ["new", "normal", "worn"] if is_road_surface else ["new"]
    used = []
    for surface in ["dry", "damp", "wet"]:
        for age in ages:
            node = node_tree.nodes.get(f"{surface}/{age}")
            if isinstance(node, bpy.types.ShaderNodeTexImage) and node.image:
                subdir = f"{surface}/{age}" if is_road_surface else surface
                used.append((subdir, node))
    return used


def all_images_dds(internal: "ShaderNodeRBRTextureInternal") -> bool:
    """Whether every exported image is a .dds file, going by its file name
    (cheap enough for drawing; the export checks the headers)."""
    node_tree = narrow(internal.id_data, bpy.types.NodeTree)
    used = used_image_nodes(node_tree, internal.is_road_surface)
    return bool(used) and all(
        node.image is not None and node.image.filepath.lower().endswith(".dds")
        for _, node in used
    )


def passes_through_dds(internal: "ShaderNodeRBRTextureInternal") -> bool:
    return bool(internal.passthrough_dds) and all_images_dds(internal)


def _get_mip_levels(self: bpy.types.Node) -> int:
    return int(self.get("mip_levels", 0))


def _set_mip_levels(self: bpy.types.Node, value: int) -> None:
    value = max(0, value)
    if value != 0:
        max_levels = compute_max_mip_levels(self)
        if max_levels > 0:
            value = min(value, max_levels)
    self["mip_levels"] = value


class ShaderNodeRBRTextureInternal(bpy.types.ShaderNodeCustomGroup):
    """The storage node contained within the texture node tree."""

    bl_name = ".RBRTextureInternalV0"
    bl_label = "RBR Texture Internal"
    node_tree: Optional[bpy.types.ShaderNodeTree] = None

    def __update_is_road_surface__(self, context: bpy.types.Context) -> None:
        name = context_active_image_name(
            context=context,
            is_road_surface=self.is_road_surface,
        )
        parent_tree = self.id_data
        link_texture_for_tree(narrow(parent_tree, bpy.types.NodeTree), name)
        # This might update an unrelated editor, but that's fine.
        if RBR_OT_edit_material_maps.active_operator is not None:
            RBR_OT_edit_material_maps.active_operator.update_active_texture(context)

    is_road_surface: bpy.props.BoolProperty(  # type: ignore
        name="Road Surface (diffuse only)",
        description="Textures should differ when track is worn",
        default=False,
        options=set(),  # No animation
        update=__update_is_road_surface__,
    )

    def __update_texture_format__(self, context: bpy.types.Context) -> None:
        set_format_alpha_mode(
            narrow(self.id_data, bpy.types.NodeTree), self.texture_format
        )

    texture_format: bpy.props.EnumProperty(  # type: ignore
        name="Format",
        description="DXT compression format used when exporting",
        items=TEXTURE_FORMAT_ITEMS,
        default="DXT1",
        options=set(),  # No animation
        update=__update_texture_format__,
    )

    mip_levels: bpy.props.IntProperty(  # type: ignore
        name="Mipmap Levels",  # noqa: F821
        description="Number of mipmap levels. 0 is a full chain down to 1x1. With Pass through DDS, the game generates levels the .dds files lack and drops extra ones when the track loads",
        get=_get_mip_levels,
        set=_set_mip_levels,
        min=0,
        soft_max=15,
        options=set(),  # No animation
    )

    passthrough_dds: bpy.props.BoolProperty(  # type: ignore
        name="Pass through DDS",
        description="Copy the .dds files into the export as they are, instead of re-encoding them",
        default=False,
        options=set(),  # No animation
    )

    material_maps: bpy.props.CollectionProperty(  # type: ignore
        type=RBRMaterialMaps,
    )

    fallback_materials: bpy.props.PointerProperty(  # type: ignore
        type=RBRFallbackMaterials,
    )

    material_picker: bpy.props.PointerProperty(  # type: ignore
        type=RBRMaterialPicker,
    )


def link_texture_for_tree(node_tree: bpy.types.NodeTree, node_name: str) -> None:
    convert_in = node_tree.nodes["sRGBConverter"].inputs[0]
    node_tree.links.new(
        convert_in,
        socket(node_tree.nodes[node_name].outputs, "Color"),
    )
    node_tree.links.new(
        socket(node_tree.nodes[FORMAT_ALPHA_IN].inputs, "Value", 0),
        socket(node_tree.nodes[node_name].outputs, "Alpha"),
    )


class ShaderNodeRBRTexture(bpy.types.ShaderNodeCustomGroup):
    """Set textures for RBR objects which can vary for dry/damp/wet and
    new/normal/worn combinations.
    """

    bl_name = "ShaderNodeRBRTexture"
    bl_label = "RBR Texture"
    # This is a field of ShaderNodeCustomGroup
    node_tree: Optional[bpy.types.ShaderNodeTree] = None

    # Use getters/setters to control these, so that we can store the texture
    # name in the node tree name (with a prefix).
    def __get_name__(self) -> str:
        if self.node_tree is None:
            raise RuntimeError("ShaderNodeRBRTexture missing node tree")
        name = tree_name_to_texture_name(self.node_tree)
        if name is None:
            raise RuntimeError(
                f"ShaderNodeRBRTexture has invalid name {self.node_tree.name}"
            )
        return name

    def __set_name__(self, value: str) -> None:
        if self.node_tree is None:
            raise RuntimeError("ShaderNodeRBRTexture missing node tree")
        self.node_tree.name = f"{RBR_TEXTURE_NODE_TREE_PREFIX}{value}"

    texture_name: bpy.props.StringProperty(  # type: ignore
        name="Texture Name",  # noqa: F821
        default="Name",  # noqa: F821
        get=__get_name__,
        set=__set_name__,
    )

    def texture_name_filename(self) -> str:
        name = tree_name_to_texture_filename(self.node_tree)
        if name is None:
            raise RuntimeError("Missing node tree for texture node")
        return name

    def set_id(
        self,
        new_name: str,
    ) -> None:
        """Call to set the "ID block" to a different one. Used when the user
        picks a different texture name from the dropdown box.
        """
        # Must iterate instead of using the name keys, because two texture nodes
        # can have the same name from two different libraries.
        for node_tree in bpy.data.node_groups:
            if tree_name_to_texture_name(node_tree) == new_name:
                self.node_tree = narrow(node_tree, bpy.types.ShaderNodeTree)
                break

    def init(self, context: bpy.types.Context) -> None:
        self.width = 300

    def update(self) -> None:
        # Runs when the node tree is assigned or its interface changes. The
        # address flags are drawn as buttons (see draw_buttons), not sockets.
        for name in TEXTURE_ADDRESS_SOCKETS:
            flag = self.inputs.get(name)
            if flag is not None and not flag.hide:
                flag.hide = True

    def address_target(self) -> bool:
        """Whether this texture feeds an RBR shader node of a type whose game
        material applies the address modes. Walks forward through reroutes."""
        from .shader_node import ShaderNodeRBR

        pending = list(self.outputs)
        seen: Set[str] = set()
        while pending:
            output = pending.pop()
            for link in output.links:
                node = link.to_node
                if isinstance(node, ShaderNodeRBR):
                    if node.mesh_type in TEXTURE_ADDRESS_MESH_TYPES:
                        return True
                elif isinstance(node, bpy.types.NodeReroute):
                    if node.name not in seen:
                        seen.add(node.name)
                        pending.extend(node.outputs)
        return False

    def free(self) -> None:
        # Intentionally leak the node tree.
        pass

    def make_single_user(self) -> None:
        if self.node_tree is not None:
            self.node_tree = self.node_tree.copy()

    def __make_texture_layout__(
        self, layout: bpy.types.UILayout, texture_node_name: str, label: str
    ) -> None:
        if self.node_tree is None:
            raise RuntimeError("ShaderNodeRBRTexture missing node tree")
        texture_node = narrow(
            self.node_tree.nodes[texture_node_name], bpy.types.ShaderNodeTexImage
        )
        img = texture_node.image
        if isinstance(img, bpy.types.Image):
            [width, height] = img.size
            ideal_width = suggested_size(width)
            ideal_height = suggested_size(height)
            if ideal_width != width or ideal_height != height:
                layout.box().label(
                    icon="ERROR",
                    text=f"Suggested size: {ideal_width}x{ideal_height}",
                )

        split = layout.split(factor=0.3)
        split.label(text=label)
        split.template_ID(texture_node, "image", new="image.new", open="image.open")

    def get_internal(self) -> ShaderNodeRBRTextureInternal:
        if self.node_tree is None:
            raise RuntimeError("Missing node tree for get_internal")
        internal = self.node_tree.nodes.get("internal")
        if not isinstance(internal, ShaderNodeRBRTextureInternal):
            raise RuntimeError("Missing internal node in node tree")
        return internal

    def get_active_image(self, context: bpy.types.Context) -> bpy.types.Image:
        name = context_active_image_name(context, self.get_internal().is_road_surface)
        if self.node_tree is None:
            raise RuntimeError("Missing node tree for get_active_image")
        node = self.node_tree.nodes.get(name)
        if not isinstance(node, bpy.types.ShaderNodeTexImage) or node.image is None:
            raise RuntimeError("Missing image node for get_active_image")
        return node.image

    def draw_buttons(
        self,
        context: bpy.types.Context,
        layout: bpy.types.UILayout,
    ) -> None:
        # Display the template_ID like UI
        template_ID = layout.row(align=True)
        choose_texture = template_ID.operator(
            "rbr.choose_texture", text="", icon="TRIA_DOWN"
        )
        if self.id_data is None:
            return
        choose_texture.node.node_name = self.name
        choose_texture.node.nodetree_pointer = str(self.id_data.as_pointer())
        if self.node_tree is None:
            new_texture = template_ID.operator("rbr.new_texture")
            new_texture.node.node_name = self.name
            new_texture.node.nodetree_pointer = str(self.id_data.as_pointer())
            return

        count = self.node_tree.users
        # Only display the "make single user" operator if it's applicable.
        if count > 1:
            split = template_ID.split(align=True, factor=0.85)
            name_container = split.column(align=True)
            name_container.enabled = self.node_tree.library is None
            name_container.prop(self, "texture_name", text="")
            make_single_user = split.operator(
                "rbr.make_texture_single_user", text=f"{count}"
            )
            make_single_user.node.node_name = self.name
            make_single_user.node.nodetree_pointer = str(self.id_data.as_pointer())
        else:
            template_ID.enabled = self.node_tree.library is None
            template_ID.prop(self, "texture_name", text="")
        unlink = template_ID.operator("rbr.unlink_texture", text="", icon="PANEL_CLOSE")
        unlink.node.node_name = self.name
        unlink.node.nodetree_pointer = str(self.id_data.as_pointer())

        texture_ui = layout.box()
        is_road_surface = False
        internal = self.node_tree.nodes.get("internal")
        if isinstance(internal, ShaderNodeRBRTextureInternal):
            is_road_surface = internal.is_road_surface
            if all_images_dds(internal):
                texture_ui.prop(internal, "passthrough_dds")
            texture_ui.prop(internal, "texture_format")
            texture_ui.prop(internal, "mip_levels", slider=True)
            texture_ui.prop(internal, "is_road_surface")
        if is_road_surface:
            self.__make_texture_layout__(texture_ui, "dry/new", "Dry/New")
            self.__make_texture_layout__(texture_ui, "dry/normal", "Dry/Normal")
            self.__make_texture_layout__(texture_ui, "dry/worn", "Dry/Worn")
            self.__make_texture_layout__(texture_ui, "damp/new", "Damp/New")
            self.__make_texture_layout__(texture_ui, "damp/normal", "Damp/Normal")
            self.__make_texture_layout__(texture_ui, "damp/worn", "Damp/Worn")
            self.__make_texture_layout__(texture_ui, "wet/new", "Wet/New")
            self.__make_texture_layout__(texture_ui, "wet/normal", "Wet/Normal")
            self.__make_texture_layout__(texture_ui, "wet/worn", "Wet/Worn")
        else:
            self.__make_texture_layout__(texture_ui, "dry/new", "Dry")
            self.__make_texture_layout__(texture_ui, "damp/new", "Damp")
            self.__make_texture_layout__(texture_ui, "wet/new", "Wet")

        if self.address_target():
            row = layout.row()
            for label, names in (
                ("Mirror", ("U Mirror", "V Mirror")),
                ("Clamp", ("U Clamp", "V Clamp")),
            ):
                row.label(text=label)
                toggles = row.row(align=True)
                for axis, name in zip("UV", names):
                    flag = self.inputs.get(name)
                    if flag is not None:
                        toggles.prop(flag, "default_value", text=axis, toggle=True)

        edit_material = layout.operator("rbr.edit_material_maps")
        edit_material.node.node_name = self.name
        edit_material.node.nodetree_pointer = str(self.id_data.as_pointer())


# (identifier, name, description, icon, numeric ID)
def get_textures_enum(x: Any, y: Any) -> List[Tuple[str, str, str, str, int]]:
    result = []
    for i, node_tree in enumerate(bpy.data.node_groups):
        texture_name = tree_name_to_texture_name(node_tree)
        if texture_name is None:
            continue
        icon = "TEXTURE"
        if node_tree.library is not None:
            icon = "LINK_BLEND"
        result.append(
            (
                texture_name,
                texture_name,
                texture_name,
                icon,
                i,
            )
        )
    return result


class RBR_OT_choose_texture(bpy.types.Operator):
    """This operator is used to produce a dropdown box similar to template_ID,
    but for our custom RBR Texture types.
    """

    bl_idname = "rbr.choose_texture"
    bl_label = "Browse existing textures"
    bl_options = {"INTERNAL", "UNDO"}
    bl_property = "texture"
    bl_description = "Select texture to be linked"

    texture: bpy.props.EnumProperty(  # type: ignore
        items=get_textures_enum,
    )
    node: bpy.props.PointerProperty(type=RBRPropertyNodePointer)  # type: ignore

    def execute(self, context: bpy.types.Context) -> OperatorReturn:
        node = self.node.get_shader_node()
        if node is None:
            return {"CANCELLED"}
        node.set_id(self.texture)
        return {"FINISHED"}

    def invoke(
        self, context: bpy.types.Context, event: bpy.types.Event
    ) -> OperatorReturn:
        if context.window_manager is None:
            return {"CANCELLED"}
        context.window_manager.invoke_search_popup(self)
        return {"FINISHED"}


class RBR_OT_new_texture(bpy.types.Operator):
    bl_idname = "rbr.new_texture"
    bl_label = "New"
    bl_description = "Create a new texture data-block"
    bl_options = {"INTERNAL", "UNDO"}

    node: bpy.props.PointerProperty(type=RBRPropertyNodePointer)  # type: ignore

    def execute(self, context: bpy.types.Context) -> OperatorReturn:
        node = self.node.get_shader_node()
        if node is None:
            return {"CANCELLED"}
        node.node_tree = setup_texture_node_tree(context, "Name", False)
        return {"FINISHED"}


class RBR_OT_make_texture_single_user(bpy.types.Operator):
    bl_idname = "rbr.make_texture_single_user"
    bl_label = "User count"
    bl_description = (
        "Display number of users of this data (click to make a single-user copy)"
    )
    bl_options = {"INTERNAL", "UNDO"}

    node: bpy.props.PointerProperty(type=RBRPropertyNodePointer)  # type: ignore

    def execute(self, context: bpy.types.Context) -> OperatorReturn:
        node = self.node.get_shader_node()
        if node is None:
            return {"CANCELLED"}
        node.make_single_user()
        return {"FINISHED"}


class RBR_OT_unlink_texture(bpy.types.Operator):
    bl_idname = "rbr.unlink_texture"
    bl_label = "Unlink data-block"
    bl_description = "Unlink this texture data-block"
    bl_options = {"INTERNAL", "UNDO"}

    node: bpy.props.PointerProperty(type=RBRPropertyNodePointer)  # type: ignore

    def execute(self, context: bpy.types.Context) -> OperatorReturn:
        node = self.node.get_shader_node()
        if node is None:
            return {"CANCELLED"}
        node.node_tree = None
        return {"FINISHED"}


def all_rbr_texture_nodes() -> Iterable[ShaderNodeRBRTexture]:
    for material in bpy.data.materials:
        if material.node_tree is None:
            continue
        for node in material.node_tree.nodes:
            if isinstance(node, ShaderNodeRBRTexture):
                yield node


def all_rbr_texture_node_trees() -> Iterable[bpy.types.NodeTree]:
    for node_tree in bpy.data.node_groups:
        texture_name = tree_name_to_texture_name(node_tree)
        if texture_name is not None:
            yield node_tree


def all_rbr_texture_node_trees_filename() -> Iterable[Tuple[str, bpy.types.NodeTree]]:
    for node_tree in bpy.data.node_groups:
        texture_name = tree_name_to_texture_filename(node_tree)
        if texture_name is not None:
            yield (texture_name, node_tree)


def register() -> None:
    bpy.utils.register_class(RBR_OT_new_texture)
    bpy.utils.register_class(RBR_OT_choose_texture)
    bpy.utils.register_class(RBR_OT_make_texture_single_user)
    bpy.utils.register_class(RBR_OT_unlink_texture)
    bpy.utils.register_class(ShaderNodeRBRTextureInternal)
    bpy.utils.register_class(ShaderNodeRBRTexture)


def unregister() -> None:
    bpy.utils.unregister_class(ShaderNodeRBRTexture)
    bpy.utils.unregister_class(ShaderNodeRBRTextureInternal)
    bpy.utils.unregister_class(RBR_OT_unlink_texture)
    bpy.utils.unregister_class(RBR_OT_make_texture_single_user)
    bpy.utils.unregister_class(RBR_OT_choose_texture)
    bpy.utils.unregister_class(RBR_OT_new_texture)
