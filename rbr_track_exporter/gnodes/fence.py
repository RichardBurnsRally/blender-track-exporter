import bpy
from ..blender_utils import narrow, new_node, socket

GNODES_FENCE_KIND: str = "Socket_2"
GNODES_FENCE_POLE_TEXTURE: str = "Socket_3"
GNODES_FENCE_TILE_TEXTURE: str = "Socket_4"
GNODES_FENCE_SUBDIVIDE: str = "Socket_5"
GNODES_FENCE_VCOL: str = "Socket_6"


# TODO check sizes
# TODO check is_long scaling
def make_fence_node_group() -> bpy.types.GeometryNodeTree:
    _rbr_fence = bpy.data.node_groups.new(type="GeometryNodeTree", name=".rbr.fence")

    _rbr_fence.color_tag = "NONE"
    _rbr_fence.description = ""

    narrow(_rbr_fence, bpy.types.GeometryNodeTree).is_modifier = True

    # _rbr_fence interface
    # Socket Geometry
    geometry_socket = _rbr_fence.interface.new_socket(
        name="Geometry", in_out="OUTPUT", socket_type="NodeSocketGeometry"
    )
    geometry_socket.attribute_domain = "POINT"

    # Socket Geometry
    geometry_socket_1 = _rbr_fence.interface.new_socket(
        name="Geometry", in_out="INPUT", socket_type="NodeSocketGeometry"
    )
    geometry_socket_1.attribute_domain = "POINT"

    # Socket Fence Kind
    fence_kind_socket = _rbr_fence.interface.new_socket(
        name="Fence Kind", in_out="INPUT", socket_type="NodeSocketInt"
    )
    fence_kind_socket.subtype = "NONE"
    fence_kind_socket.default_value = 0
    fence_kind_socket.min_value = -2147483648
    fence_kind_socket.max_value = 2147483647
    fence_kind_socket.attribute_domain = "POINT"
    fence_kind_socket.hide_value = True
    fence_kind_socket.hide_in_modifier = True
    fence_kind_socket.force_non_field = True

    # Socket Pole Material
    pole_material_socket = _rbr_fence.interface.new_socket(
        name="Pole Material", in_out="INPUT", socket_type="NodeSocketMaterial"
    )
    pole_material_socket.attribute_domain = "POINT"
    pole_material_socket.hide_in_modifier = True
    pole_material_socket.description = "Texture for the fence poles"

    # Socket Tile Material
    tile_material_socket = _rbr_fence.interface.new_socket(
        name="Tile Material", in_out="INPUT", socket_type="NodeSocketMaterial"
    )
    tile_material_socket.attribute_domain = "POINT"
    tile_material_socket.hide_in_modifier = True
    tile_material_socket.description = "Texture for the tiled part of the fence"

    # Socket Subdivide
    subdivide_socket = _rbr_fence.interface.new_socket(
        name="Subdivide", in_out="INPUT", socket_type="NodeSocketBool"
    )
    subdivide_socket.attribute_domain = "POINT"
    subdivide_socket.hide_in_modifier = True
    subdivide_socket.force_non_field = True
    subdivide_socket.description = "Higher resolution used for rendering and collisions"

    # Socket Vertex Color
    vertex_color_socket = _rbr_fence.interface.new_socket(
        name="Vertex Color", in_out="INPUT", socket_type="NodeSocketColor"
    )
    vertex_color_socket.attribute_domain = "POINT"
    vertex_color_socket.description = "Vertex colors (for baked lighting)"

    # initialize _rbr_fence nodes
    # node Group Input
    group_input = new_node(_rbr_fence.nodes, bpy.types.NodeGroupInput)
    group_input.name = "Group Input"

    # node Group Output
    group_output = new_node(_rbr_fence.nodes, bpy.types.NodeGroupOutput)
    group_output.name = "Group Output"
    group_output.is_active_output = True

    # node Extrude Mesh
    extrude_mesh = new_node(_rbr_fence.nodes, bpy.types.GeometryNodeExtrudeMesh)
    extrude_mesh.name = "Extrude Mesh"
    extrude_mesh.mode = "EDGES"
    # Selection
    socket(extrude_mesh.inputs, "Selection").default_value = True
    # Offset Scale
    socket(extrude_mesh.inputs, "Offset Scale").default_value = 0.84375

    # node Combine XYZ
    combine_xyz = new_node(_rbr_fence.nodes, bpy.types.ShaderNodeCombineXYZ)
    combine_xyz.name = "Combine XYZ"
    # X
    socket(combine_xyz.inputs, "X").default_value = 0.0
    # Y
    socket(combine_xyz.inputs, "Y").default_value = 0.0
    # Z
    socket(combine_xyz.inputs, "Z").default_value = 1.0

    # node Store Named Attribute
    store_named_attribute = new_node(
        _rbr_fence.nodes, bpy.types.GeometryNodeStoreNamedAttribute
    )
    store_named_attribute.name = "Store Named Attribute"
    store_named_attribute.data_type = "FLOAT2"
    store_named_attribute.domain = "POINT"
    # Selection
    socket(store_named_attribute.inputs, "Selection").default_value = True
    # Name
    socket(store_named_attribute.inputs, "Name").default_value = ".rbr.uv"

    # node Combine XYZ.001
    combine_xyz_001 = new_node(_rbr_fence.nodes, bpy.types.ShaderNodeCombineXYZ)
    combine_xyz_001.name = "Combine XYZ.001"
    # Z
    socket(combine_xyz_001.inputs, "Z").default_value = 0.0

    # node Capture Attribute
    capture_attribute = new_node(
        _rbr_fence.nodes, bpy.types.GeometryNodeCaptureAttribute
    )
    capture_attribute.name = "Capture Attribute"
    capture_attribute.active_index = 0
    capture_attribute.capture_items.clear()
    capture_attribute.capture_items.new("FLOAT", "Total Cost")
    capture_attribute.capture_items["Total Cost"].data_type = "INT"
    capture_attribute.domain = "POINT"

    # node Index
    index = new_node(_rbr_fence.nodes, bpy.types.GeometryNodeInputIndex)
    index.name = "Index"

    # node Sort Elements
    sort_elements = new_node(_rbr_fence.nodes, bpy.types.GeometryNodeSortElements)
    sort_elements.name = "Sort Elements"
    sort_elements.domain = "POINT"
    # Selection
    socket(sort_elements.inputs, "Selection").default_value = True
    # Group ID
    socket(sort_elements.inputs, "Group ID").default_value = 0

    # node Shortest Edge Paths
    shortest_edge_paths = new_node(
        _rbr_fence.nodes, bpy.types.GeometryNodeInputShortestEdgePaths
    )
    shortest_edge_paths.name = "Shortest Edge Paths"

    # node Edge Vertices
    edge_vertices = new_node(
        _rbr_fence.nodes, bpy.types.GeometryNodeInputMeshEdgeVertices
    )
    edge_vertices.name = "Edge Vertices"

    # node Vector Math
    vector_math = new_node(_rbr_fence.nodes, bpy.types.ShaderNodeVectorMath)
    vector_math.name = "Vector Math"
    vector_math.operation = "DISTANCE"

    # node Compare
    compare = new_node(_rbr_fence.nodes, bpy.types.FunctionNodeCompare)
    compare.name = "Compare"
    compare.data_type = "INT"
    compare.mode = "ELEMENT"
    compare.operation = "EQUAL"
    # B
    socket(compare.inputs, "B").default_value = 0

    # node Index.003
    index_003 = new_node(_rbr_fence.nodes, bpy.types.GeometryNodeInputIndex)
    index_003.name = "Index.003"

    # node Cube
    cube = new_node(_rbr_fence.nodes, bpy.types.GeometryNodeMeshCube)
    cube.name = "Cube"
    # Size
    socket(cube.inputs, "Size").default_value = (
        0.019999999552965164,
        0.019999999552965164,
        1.0,
    )
    # Vertices X
    socket(cube.inputs, "Vertices X").default_value = 2
    # Vertices Y
    socket(cube.inputs, "Vertices Y").default_value = 2
    # Vertices Z
    socket(cube.inputs, "Vertices Z").default_value = 2

    # node Join Geometry
    join_geometry = new_node(_rbr_fence.nodes, bpy.types.GeometryNodeJoinGeometry)
    join_geometry.name = "Join Geometry"

    # node Realize Instances
    realize_instances = new_node(
        _rbr_fence.nodes, bpy.types.GeometryNodeRealizeInstances
    )
    realize_instances.name = "Realize Instances"
    # Selection
    socket(realize_instances.inputs, "Selection").default_value = True
    # Realize All
    socket(realize_instances.inputs, "Realize All").default_value = True
    # Depth
    socket(realize_instances.inputs, "Depth").default_value = 0

    # node Instance on Points
    instance_on_points = new_node(
        _rbr_fence.nodes, bpy.types.GeometryNodeInstanceOnPoints
    )
    instance_on_points.name = "Instance on Points"
    # Selection
    socket(instance_on_points.inputs, "Selection").default_value = True
    # Pick Instance
    socket(instance_on_points.inputs, "Pick Instance").default_value = False
    # Instance Index
    socket(instance_on_points.inputs, "Instance Index").default_value = 0
    # Rotation
    socket(instance_on_points.inputs, "Rotation").default_value = (
        0.0,
        0.0,
        0.0,
    )
    # Scale
    socket(instance_on_points.inputs, "Scale").default_value = (
        1.0,
        1.0,
        1.0,
    )

    # node Translate Instances
    translate_instances = new_node(
        _rbr_fence.nodes, bpy.types.GeometryNodeTranslateInstances
    )
    translate_instances.name = "Translate Instances"
    # Selection
    socket(translate_instances.inputs, "Selection").default_value = True
    # Translation
    socket(translate_instances.inputs, "Translation").default_value = (
        0.0,
        0.0,
        0.4999999701976776,
    )
    # Local Space
    socket(translate_instances.inputs, "Local Space").default_value = True

    # node Frame
    frame = new_node(_rbr_fence.nodes, bpy.types.NodeFrame)
    frame.label = "Net"
    frame.name = "Frame"
    frame.label_size = 20
    frame.shrink = True

    # node Frame.001
    frame_001 = new_node(_rbr_fence.nodes, bpy.types.NodeFrame)
    frame_001.label = "Pole"
    frame_001.name = "Frame.001"
    frame_001.label_size = 20
    frame_001.shrink = True

    # node Set Material
    set_material = new_node(_rbr_fence.nodes, bpy.types.GeometryNodeSetMaterial)
    set_material.name = "Set Material"
    # Selection
    socket(set_material.inputs, "Selection").default_value = True

    # node Set Material.001
    set_material_001 = new_node(_rbr_fence.nodes, bpy.types.GeometryNodeSetMaterial)
    set_material_001.name = "Set Material.001"
    # Selection
    socket(set_material_001.inputs, "Selection").default_value = True

    # node Store Named Attribute.001
    store_named_attribute_001 = new_node(
        _rbr_fence.nodes, bpy.types.GeometryNodeStoreNamedAttribute
    )
    store_named_attribute_001.name = "Store Named Attribute.001"
    store_named_attribute_001.data_type = "FLOAT2"
    store_named_attribute_001.domain = "CORNER"
    # Selection
    socket(store_named_attribute_001.inputs, "Selection").default_value = True
    # Name
    socket(store_named_attribute_001.inputs, "Name").default_value = ".rbr.uv"

    # node Capture Attribute.001
    capture_attribute_001 = new_node(
        _rbr_fence.nodes, bpy.types.GeometryNodeCaptureAttribute
    )
    capture_attribute_001.name = "Capture Attribute.001"
    capture_attribute_001.active_index = 0
    capture_attribute_001.capture_items.clear()
    capture_attribute_001.capture_items.new("FLOAT", "UV Map")
    capture_attribute_001.capture_items["UV Map"].data_type = "FLOAT_VECTOR"
    capture_attribute_001.domain = "CORNER"

    # node Combine XYZ.002
    combine_xyz_002 = new_node(_rbr_fence.nodes, bpy.types.ShaderNodeCombineXYZ)
    combine_xyz_002.name = "Combine XYZ.002"
    # Z
    socket(combine_xyz_002.inputs, "Z").default_value = 0.0

    # node Position
    position = new_node(_rbr_fence.nodes, bpy.types.GeometryNodeInputPosition)
    position.name = "Position"

    # node Separate XYZ
    separate_xyz = new_node(_rbr_fence.nodes, bpy.types.ShaderNodeSeparateXYZ)
    separate_xyz.name = "Separate XYZ"

    # node Math
    math = new_node(_rbr_fence.nodes, bpy.types.ShaderNodeMath)
    math.name = "Math"
    math.operation = "GREATER_THAN"
    math.use_clamp = False
    # Value_001
    socket(math.inputs, "Value", 1).default_value = 0.0

    # node Separate XYZ.001
    separate_xyz_001 = new_node(_rbr_fence.nodes, bpy.types.ShaderNodeSeparateXYZ)
    separate_xyz_001.name = "Separate XYZ.001"

    # node Extrude Mesh.001
    extrude_mesh_001 = new_node(_rbr_fence.nodes, bpy.types.GeometryNodeExtrudeMesh)
    extrude_mesh_001.name = "Extrude Mesh.001"
    extrude_mesh_001.mode = "EDGES"
    # Selection
    socket(extrude_mesh_001.inputs, "Selection").default_value = True
    # Offset Scale
    socket(extrude_mesh_001.inputs, "Offset Scale").default_value = 0.05000000447034836

    # node Combine XYZ.003
    combine_xyz_003 = new_node(_rbr_fence.nodes, bpy.types.ShaderNodeCombineXYZ)
    combine_xyz_003.name = "Combine XYZ.003"
    # X
    socket(combine_xyz_003.inputs, "X").default_value = 0.0
    # Y
    socket(combine_xyz_003.inputs, "Y").default_value = 0.0
    # Z
    socket(combine_xyz_003.inputs, "Z").default_value = 1.0

    # node Store Named Attribute.002
    store_named_attribute_002 = new_node(
        _rbr_fence.nodes, bpy.types.GeometryNodeStoreNamedAttribute
    )
    store_named_attribute_002.name = "Store Named Attribute.002"
    store_named_attribute_002.data_type = "FLOAT2"
    store_named_attribute_002.domain = "POINT"
    # Selection
    socket(store_named_attribute_002.inputs, "Selection").default_value = True
    # Name
    socket(store_named_attribute_002.inputs, "Name").default_value = ".rbr.uv"

    # node Combine XYZ.004
    combine_xyz_004 = new_node(_rbr_fence.nodes, bpy.types.ShaderNodeCombineXYZ)
    combine_xyz_004.name = "Combine XYZ.004"
    # Z
    socket(combine_xyz_004.inputs, "Z").default_value = 0.0

    # node Capture Attribute.002
    capture_attribute_002 = new_node(
        _rbr_fence.nodes, bpy.types.GeometryNodeCaptureAttribute
    )
    capture_attribute_002.name = "Capture Attribute.002"
    capture_attribute_002.active_index = 0
    capture_attribute_002.capture_items.clear()
    capture_attribute_002.capture_items.new("FLOAT", "Total Cost")
    capture_attribute_002.capture_items["Total Cost"].data_type = "INT"
    capture_attribute_002.domain = "POINT"

    # node Index.001
    index_001 = new_node(_rbr_fence.nodes, bpy.types.GeometryNodeInputIndex)
    index_001.name = "Index.001"

    # node Frame.002
    frame_002 = new_node(_rbr_fence.nodes, bpy.types.NodeFrame)
    frame_002.label = "Tape"
    frame_002.name = "Frame.002"
    frame_002.label_size = 20
    frame_002.shrink = True

    # node Set Material.002
    set_material_002 = new_node(_rbr_fence.nodes, bpy.types.GeometryNodeSetMaterial)
    set_material_002.name = "Set Material.002"
    # Selection
    socket(set_material_002.inputs, "Selection").default_value = True

    # node Set Position
    set_position = new_node(_rbr_fence.nodes, bpy.types.GeometryNodeSetPosition)
    set_position.name = "Set Position"
    # Selection
    socket(set_position.inputs, "Selection").default_value = True
    # Position
    socket(set_position.inputs, "Position").default_value = (0.0, 0.0, 0.0)
    # Offset
    socket(set_position.inputs, "Offset").default_value = (
        0.0,
        0.0,
        0.85999995470047,
    )

    # node Compare.001
    compare_001 = new_node(_rbr_fence.nodes, bpy.types.FunctionNodeCompare)
    compare_001.label = "Is Tape"
    compare_001.name = "Compare.001"
    compare_001.data_type = "INT"
    compare_001.mode = "ELEMENT"
    compare_001.operation = "NOT_EQUAL"
    # B
    socket(compare_001.inputs, "B").default_value = 0

    # node Compare.002
    compare_002 = new_node(_rbr_fence.nodes, bpy.types.FunctionNodeCompare)
    compare_002.label = "Is Net"
    compare_002.name = "Compare.002"
    compare_002.data_type = "INT"
    compare_002.mode = "ELEMENT"
    compare_002.operation = "NOT_EQUAL"
    # B
    socket(compare_002.inputs, "B").default_value = 1

    # node Delete Geometry
    delete_geometry = new_node(_rbr_fence.nodes, bpy.types.GeometryNodeDeleteGeometry)
    delete_geometry.name = "Delete Geometry"
    delete_geometry.domain = "POINT"
    delete_geometry.mode = "ALL"

    # node Delete Geometry.001
    delete_geometry_001 = new_node(
        _rbr_fence.nodes, bpy.types.GeometryNodeDeleteGeometry
    )
    delete_geometry_001.name = "Delete Geometry.001"
    delete_geometry_001.domain = "POINT"
    delete_geometry_001.mode = "ALL"

    # node Vector Math.001
    vector_math_001 = new_node(_rbr_fence.nodes, bpy.types.ShaderNodeVectorMath)
    vector_math_001.name = "Vector Math.001"
    vector_math_001.operation = "MULTIPLY"
    # Vector_001
    socket(vector_math_001.inputs, "Vector", 1).default_value = (32.0, 27.0, 0.0)

    # node Group Input.001
    group_input_001 = new_node(_rbr_fence.nodes, bpy.types.NodeGroupInput)
    group_input_001.name = "Group Input.001"

    # node Group Input.002
    group_input_002 = new_node(_rbr_fence.nodes, bpy.types.NodeGroupInput)
    group_input_002.name = "Group Input.002"

    # node Group Input.003
    group_input_003 = new_node(_rbr_fence.nodes, bpy.types.NodeGroupInput)
    group_input_003.name = "Group Input.003"

    # node Store Named Attribute.003
    store_named_attribute_003 = new_node(
        _rbr_fence.nodes, bpy.types.GeometryNodeStoreNamedAttribute
    )
    store_named_attribute_003.name = "Store Named Attribute.003"
    store_named_attribute_003.data_type = "FLOAT_COLOR"
    store_named_attribute_003.domain = "POINT"
    # Selection
    socket(store_named_attribute_003.inputs, "Selection").default_value = True
    # Name
    socket(store_named_attribute_003.inputs, "Name").default_value = ".rbr.color"

    # node Vector Math.002
    vector_math_002 = new_node(_rbr_fence.nodes, bpy.types.ShaderNodeVectorMath)
    vector_math_002.name = "Vector Math.002"
    vector_math_002.operation = "MULTIPLY"
    # Vector_001
    socket(vector_math_002.inputs, "Vector", 1).default_value = (14.0, 1.0, 0.0)

    # node Set Position.001
    set_position_001 = new_node(_rbr_fence.nodes, bpy.types.GeometryNodeSetPosition)
    set_position_001.name = "Set Position.001"
    # Selection
    socket(set_position_001.inputs, "Selection").default_value = True
    # Position
    socket(set_position_001.inputs, "Position").default_value = (0.0, 0.0, 0.0)
    # Offset
    socket(set_position_001.inputs, "Offset").default_value = (
        0.0,
        0.0,
        0.078125,
    )

    # node Extrude Mesh.002
    extrude_mesh_002 = new_node(_rbr_fence.nodes, bpy.types.GeometryNodeExtrudeMesh)
    extrude_mesh_002.name = "Extrude Mesh.002"
    extrude_mesh_002.mode = "EDGES"
    # Selection
    socket(extrude_mesh_002.inputs, "Selection").default_value = True
    # Offset Scale
    socket(extrude_mesh_002.inputs, "Offset Scale").default_value = 0.05000000074505806

    # node Combine XYZ.005
    combine_xyz_005 = new_node(_rbr_fence.nodes, bpy.types.ShaderNodeCombineXYZ)
    combine_xyz_005.name = "Combine XYZ.005"
    # X
    socket(combine_xyz_005.inputs, "X").default_value = 0.0
    # Y
    socket(combine_xyz_005.inputs, "Y").default_value = 0.0
    # Z
    socket(combine_xyz_005.inputs, "Z").default_value = 1.0

    # node Store Named Attribute.004
    store_named_attribute_004 = new_node(
        _rbr_fence.nodes, bpy.types.GeometryNodeStoreNamedAttribute
    )
    store_named_attribute_004.name = "Store Named Attribute.004"
    store_named_attribute_004.data_type = "FLOAT2"
    store_named_attribute_004.domain = "POINT"
    # Selection
    socket(store_named_attribute_004.inputs, "Selection").default_value = True
    # Name
    socket(store_named_attribute_004.inputs, "Name").default_value = ".rbr.uv"

    # node Combine XYZ.006
    combine_xyz_006 = new_node(_rbr_fence.nodes, bpy.types.ShaderNodeCombineXYZ)
    combine_xyz_006.name = "Combine XYZ.006"
    # Z
    socket(combine_xyz_006.inputs, "Z").default_value = 0.0

    # node Capture Attribute.003
    capture_attribute_003 = new_node(
        _rbr_fence.nodes, bpy.types.GeometryNodeCaptureAttribute
    )
    capture_attribute_003.name = "Capture Attribute.003"
    capture_attribute_003.active_index = 0
    capture_attribute_003.capture_items.clear()
    capture_attribute_003.capture_items.new("FLOAT", "Total Cost")
    capture_attribute_003.capture_items["Total Cost"].data_type = "INT"
    capture_attribute_003.domain = "POINT"

    # node Index.002
    index_002 = new_node(_rbr_fence.nodes, bpy.types.GeometryNodeInputIndex)
    index_002.name = "Index.002"

    # node Frame.003
    frame_003 = new_node(_rbr_fence.nodes, bpy.types.NodeFrame)
    frame_003.label = "Barbed"
    frame_003.name = "Frame.003"
    frame_003.label_size = 20
    frame_003.shrink = True

    # node Set Material.003
    set_material_003 = new_node(_rbr_fence.nodes, bpy.types.GeometryNodeSetMaterial)
    set_material_003.name = "Set Material.003"
    # Selection
    socket(set_material_003.inputs, "Selection").default_value = True

    # node Compare.003
    compare_003 = new_node(_rbr_fence.nodes, bpy.types.FunctionNodeCompare)
    compare_003.label = "Is Net"
    compare_003.name = "Compare.003"
    compare_003.data_type = "INT"
    compare_003.mode = "ELEMENT"
    compare_003.operation = "NOT_EQUAL"
    # B
    socket(compare_003.inputs, "B").default_value = 2

    # node Delete Geometry.002
    delete_geometry_002 = new_node(
        _rbr_fence.nodes, bpy.types.GeometryNodeDeleteGeometry
    )
    delete_geometry_002.name = "Delete Geometry.002"
    delete_geometry_002.domain = "POINT"
    delete_geometry_002.mode = "ALL"

    # node Vector Math.003
    vector_math_003 = new_node(_rbr_fence.nodes, bpy.types.ShaderNodeVectorMath)
    vector_math_003.name = "Vector Math.003"
    vector_math_003.operation = "MULTIPLY"
    # Vector_001
    socket(vector_math_003.inputs, "Vector", 1).default_value = (28.0, 1.0, 0.0)

    # node Group Input.004
    group_input_004 = new_node(_rbr_fence.nodes, bpy.types.NodeGroupInput)
    group_input_004.name = "Group Input.004"

    # node Set Position.002
    set_position_002 = new_node(_rbr_fence.nodes, bpy.types.GeometryNodeSetPosition)
    set_position_002.name = "Set Position.002"
    # Selection
    socket(set_position_002.inputs, "Selection").default_value = True
    # Position
    socket(set_position_002.inputs, "Position").default_value = (0.0, 0.0, 0.0)
    # Offset
    socket(set_position_002.inputs, "Offset").default_value = (
        0.0,
        0.0,
        0.8600000143051147,
    )

    # node Join Geometry.001
    join_geometry_001 = new_node(_rbr_fence.nodes, bpy.types.GeometryNodeJoinGeometry)
    join_geometry_001.name = "Join Geometry.001"

    # node Set Position.003
    set_position_003 = new_node(_rbr_fence.nodes, bpy.types.GeometryNodeSetPosition)
    set_position_003.name = "Set Position.003"
    # Selection
    socket(set_position_003.inputs, "Selection").default_value = True
    # Position
    socket(set_position_003.inputs, "Position").default_value = (0.0, 0.0, 0.0)
    # Offset
    socket(set_position_003.inputs, "Offset").default_value = (
        0.0,
        0.0,
        0.5000000596046448,
    )

    # node Group Input.005
    group_input_005 = new_node(_rbr_fence.nodes, bpy.types.NodeGroupInput)
    group_input_005.name = "Group Input.005"

    # node Group Input.006
    group_input_006 = new_node(_rbr_fence.nodes, bpy.types.NodeGroupInput)
    group_input_006.name = "Group Input.006"

    # node Group Input.007
    group_input_007 = new_node(_rbr_fence.nodes, bpy.types.NodeGroupInput)
    group_input_007.name = "Group Input.007"

    # node Reroute
    reroute = new_node(_rbr_fence.nodes, bpy.types.NodeReroute)
    reroute.name = "Reroute"
    # node Reroute.001
    reroute_001 = new_node(_rbr_fence.nodes, bpy.types.NodeReroute)
    reroute_001.name = "Reroute.001"
    # node Reroute.002
    reroute_002 = new_node(_rbr_fence.nodes, bpy.types.NodeReroute)
    reroute_002.name = "Reroute.002"
    # node Reroute.003
    reroute_003 = new_node(_rbr_fence.nodes, bpy.types.NodeReroute)
    reroute_003.name = "Reroute.003"
    # node Reroute.004
    reroute_004 = new_node(_rbr_fence.nodes, bpy.types.NodeReroute)
    reroute_004.name = "Reroute.004"
    # node Reroute.005
    reroute_005 = new_node(_rbr_fence.nodes, bpy.types.NodeReroute)
    reroute_005.name = "Reroute.005"
    # node Reroute.006
    reroute_006 = new_node(_rbr_fence.nodes, bpy.types.NodeReroute)
    reroute_006.name = "Reroute.006"
    # node Reroute.007
    reroute_007 = new_node(_rbr_fence.nodes, bpy.types.NodeReroute)
    reroute_007.name = "Reroute.007"
    # node Math.001
    math_001 = new_node(_rbr_fence.nodes, bpy.types.ShaderNodeMath)
    math_001.name = "Math.001"
    math_001.operation = "MULTIPLY"
    math_001.use_clamp = False

    # node Map Range
    map_range = new_node(_rbr_fence.nodes, bpy.types.ShaderNodeMapRange)
    map_range.name = "Map Range"
    map_range.clamp = True
    map_range.data_type = "FLOAT"
    map_range.interpolation_type = "LINEAR"
    # From Min
    socket(map_range.inputs, "From Min").default_value = 0.0
    # From Max
    socket(map_range.inputs, "From Max").default_value = 1.0
    # To Min
    socket(map_range.inputs, "To Min").default_value = 0.9999998807907104
    # To Max
    socket(map_range.inputs, "To Max").default_value = 2.0

    # node Math.002
    math_002 = new_node(_rbr_fence.nodes, bpy.types.ShaderNodeMath)
    math_002.name = "Math.002"
    math_002.operation = "MULTIPLY"
    math_002.use_clamp = False

    # node Map Range.001
    map_range_001 = new_node(_rbr_fence.nodes, bpy.types.ShaderNodeMapRange)
    map_range_001.name = "Map Range.001"
    map_range_001.clamp = True
    map_range_001.data_type = "FLOAT"
    map_range_001.interpolation_type = "LINEAR"
    # From Min
    socket(map_range_001.inputs, "From Min").default_value = 0.0
    # From Max
    socket(map_range_001.inputs, "From Max").default_value = 1.0
    # To Min
    socket(map_range_001.inputs, "To Min").default_value = 0.9999998807907104
    # To Max
    socket(map_range_001.inputs, "To Max").default_value = 2.0

    # node Math.003
    math_003 = new_node(_rbr_fence.nodes, bpy.types.ShaderNodeMath)
    math_003.name = "Math.003"
    math_003.operation = "MULTIPLY"
    math_003.use_clamp = False

    # node Map Range.002
    map_range_002 = new_node(_rbr_fence.nodes, bpy.types.ShaderNodeMapRange)
    map_range_002.name = "Map Range.002"
    map_range_002.clamp = True
    map_range_002.data_type = "FLOAT"
    map_range_002.interpolation_type = "LINEAR"
    # From Min
    socket(map_range_002.inputs, "From Min").default_value = 0.0
    # From Max
    socket(map_range_002.inputs, "From Max").default_value = 1.0
    # To Min
    socket(map_range_002.inputs, "To Min").default_value = 0.9999998807907104
    # To Max
    socket(map_range_002.inputs, "To Max").default_value = 2.0

    # node Separate Components
    separate_components = new_node(
        _rbr_fence.nodes, bpy.types.GeometryNodeSeparateComponents
    )
    separate_components.name = "Separate Components"

    # node Group Input.008
    group_input_008 = new_node(_rbr_fence.nodes, bpy.types.NodeGroupInput)
    group_input_008.name = "Group Input.008"

    # node Join Geometry.002
    join_geometry_002 = new_node(_rbr_fence.nodes, bpy.types.GeometryNodeJoinGeometry)
    join_geometry_002.name = "Join Geometry.002"

    # node Curve to Mesh
    curve_to_mesh = new_node(_rbr_fence.nodes, bpy.types.GeometryNodeCurveToMesh)
    curve_to_mesh.name = "Curve to Mesh"
    # Fill Caps
    socket(curve_to_mesh.inputs, "Fill Caps").default_value = False

    # node Set Spline Type
    set_spline_type = new_node(_rbr_fence.nodes, bpy.types.GeometryNodeCurveSplineType)
    set_spline_type.name = "Set Spline Type"
    set_spline_type.spline_type = "POLY"
    # Selection
    socket(set_spline_type.inputs, "Selection").default_value = True

    # Set parents
    extrude_mesh.parent = frame
    combine_xyz.parent = frame
    store_named_attribute.parent = frame
    combine_xyz_001.parent = frame
    capture_attribute.parent = frame
    index.parent = frame
    cube.parent = frame_001
    realize_instances.parent = frame_001
    instance_on_points.parent = frame_001
    translate_instances.parent = frame_001
    set_material.parent = frame
    set_material_001.parent = frame_001
    store_named_attribute_001.parent = frame_001
    capture_attribute_001.parent = frame_001
    combine_xyz_002.parent = frame_001
    position.parent = frame_001
    separate_xyz.parent = frame_001
    math.parent = frame_001
    separate_xyz_001.parent = frame_001
    extrude_mesh_001.parent = frame_002
    combine_xyz_003.parent = frame_002
    store_named_attribute_002.parent = frame_002
    combine_xyz_004.parent = frame_002
    capture_attribute_002.parent = frame_002
    index_001.parent = frame_002
    set_material_002.parent = frame_002
    set_position.parent = frame_002
    compare_001.parent = frame_002
    compare_002.parent = frame
    delete_geometry.parent = frame_002
    delete_geometry_001.parent = frame
    vector_math_001.parent = frame
    group_input_001.parent = frame
    group_input_002.parent = frame_001
    group_input_003.parent = frame_002
    vector_math_002.parent = frame_002
    set_position_001.parent = frame
    extrude_mesh_002.parent = frame_003
    combine_xyz_005.parent = frame_003
    store_named_attribute_004.parent = frame_003
    combine_xyz_006.parent = frame_003
    capture_attribute_003.parent = frame_003
    index_002.parent = frame_003
    set_material_003.parent = frame_003
    compare_003.parent = frame_003
    delete_geometry_002.parent = frame_003
    vector_math_003.parent = frame_003
    group_input_004.parent = frame_003
    set_position_002.parent = frame_003
    join_geometry_001.parent = frame_003
    set_position_003.parent = frame_003
    group_input_005.parent = frame_002
    group_input_006.parent = frame
    group_input_007.parent = frame_003
    reroute.parent = frame_001
    reroute_001.parent = frame_001
    reroute_002.parent = frame_003
    reroute_003.parent = frame_003
    reroute_004.parent = frame
    reroute_005.parent = frame
    reroute_006.parent = frame_002
    reroute_007.parent = frame_002
    math_001.parent = frame_002
    map_range.parent = frame_002
    math_002.parent = frame
    map_range_001.parent = frame
    math_003.parent = frame_003
    map_range_002.parent = frame_003

    # Set locations
    group_input.location = (-1029.563232421875, -566.0662231445312)
    group_output.location = (1955.2630615234375, -398.3929443359375)
    extrude_mesh.location = (221.16281127929688, -95.57386779785156)
    combine_xyz.location = (29.367603302001953, -90.80850982666016)
    store_named_attribute.location = (771.7409057617188, -81.2698745727539)
    combine_xyz_001.location = (405.9140930175781, -295.63055419921875)
    capture_attribute.location = (26.489843368530273, -224.9059600830078)
    index.location = (-162.94741821289062, -316.68170166015625)
    sort_elements.location = (-1213.8404541015625, -503.68878173828125)
    shortest_edge_paths.location = (-1399.33544921875, -597.1837158203125)
    edge_vertices.location = (-1756.615234375, -671.0203247070312)
    vector_math.location = (-1577.6290283203125, -669.9073486328125)
    compare.location = (-1576.152099609375, -492.3828125)
    index_003.location = (-1758.236083984375, -495.47735595703125)
    cube.location = (-97.36155700683594, -614.3021240234375)
    join_geometry.location = (1764.276611328125, -396.78875732421875)
    realize_instances.location = (991.672607421875, -657.7705688476562)
    instance_on_points.location = (627.6466064453125, -637.66259765625)
    translate_instances.location = (810.53369140625, -677.0203247070312)
    frame.location = (11.199999809265137, 0.0)
    frame_001.location = (-232.2138214111328, -599.5733642578125)
    set_material.location = (965.4658813476562, -107.5665054321289)
    set_material_001.location = (1403.5670166015625, -648.600341796875)
    store_named_attribute_001.location = (1209.5867919921875, -633.738037109375)
    capture_attribute_001.location = (445.4893493652344, -654.7245483398438)
    combine_xyz_002.location = (268.2161865234375, -732.9838256835938)
    position.location = (-278.07940673828125, -921.039794921875)
    separate_xyz.location = (-96.96356201171875, -864.8257446289062)
    math.location = (84.12660217285156, -846.897705078125)
    separate_xyz_001.location = (82.32546997070312, -706.392822265625)
    extrude_mesh_001.location = (222.11892700195312, 27.04840087890625)
    combine_xyz_003.location = (29.367603302001953, -90.80850982666016)
    store_named_attribute_002.location = (768.8378295898438, 45.097137451171875)
    combine_xyz_004.location = (408.14898681640625, -198.36721801757812)
    capture_attribute_002.location = (26.489843368530273, -224.9059600830078)
    index_001.location = (-164.72158813476562, -293.5959167480469)
    frame_002.location = (16.731983184814453, 385.66290283203125)
    set_material_002.location = (952.1151123046875, -102.72967529296875)
    set_position.location = (410.7174072265625, 26.424896240234375)
    compare_001.location = (-347.39996337890625, 77.88894653320312)
    compare_002.location = (-331.14788818359375, -99.81233215332031)
    delete_geometry.location = (-162.88267517089844, -118.11175537109375)
    delete_geometry_001.location = (-162.94869995117188, -155.5679168701172)
    vector_math_001.location = (591.8231811523438, -203.17117309570312)
    group_input_001.location = (770.4349365234375, -284.57196044921875)
    group_input_002.location = (1205.498046875, -857.59912109375)
    group_input_003.location = (766.2489013671875, -183.08775329589844)
    store_named_attribute_003.location = (-853.87451171875, -442.62103271484375)
    vector_math_002.location = (588.5167846679688, -164.84292602539062)
    set_position_001.location = (411.2640075683594, -76.15757751464844)
    extrude_mesh_002.location = (221.16281127929688, -95.57386779785156)
    combine_xyz_005.location = (29.367603302001953, -90.80850982666016)
    store_named_attribute_004.location = (771.7409057617188, -81.2698745727539)
    combine_xyz_006.location = (405.9140930175781, -291.4715576171875)
    capture_attribute_003.location = (26.489843368530273, -224.9059600830078)
    index_002.location = (-164.72158813476562, -293.5959167480469)
    frame_003.location = (0.12297353893518448, -569.5557250976562)
    set_material_003.location = (948.9645385742188, -109.2188720703125)
    compare_003.location = (-340.74407958984375, -108.80841064453125)
    delete_geometry_002.location = (-161.1743927001953, -86.46844482421875)
    vector_math_003.location = (591.8231811523438, -203.17117309570312)
    group_input_004.location = (770.4349365234375, -284.57196044921875)
    set_position_002.location = (1163.4156494140625, -44.15386962890625)
    join_geometry_001.location = (1340.894775390625, -111.47760009765625)
    set_position_003.location = (1157.7587890625, -265.17559814453125)
    group_input_005.location = (-514.717529296875, 71.5443115234375)
    group_input_006.location = (-506.94610595703125, -89.42627716064453)
    group_input_007.location = (-506.20391845703125, -191.8515625)
    reroute.location = (545.5279541015625, -599.7706298828125)
    reroute_001.location = (-270.2716064453125, -599.7706298828125)
    reroute_002.location = (-498.6422424316406, -51.22216796875)
    reroute_003.location = (-218.1531219482422, -51.22216796875)
    reroute_004.location = (-302.7561950683594, -262.64776611328125)
    reroute_005.location = (-506.46661376953125, -349.1627502441406)
    reroute_006.location = (-209.3086395263672, -348.5017395019531)
    reroute_007.location = (-509.38665771484375, -348.5017395019531)
    math_001.location = (223.49942016601562, -212.57716369628906)
    map_range.location = (-348.14105224609375, -85.7271728515625)
    math_002.location = (221.768310546875, -329.9051818847656)
    map_range_001.location = (-330.56146240234375, -279.12066650390625)
    math_003.location = (215.05360412597656, -323.9622802734375)
    map_range_002.location = (-340.6285400390625, -275.4156494140625)
    separate_components.location = (-1573.4141845703125, -257.46746826171875)
    group_input_008.location = (-1752.2738037109375, -245.8200225830078)
    join_geometry_002.location = (-1033.60009765625, -445.7371520996094)
    curve_to_mesh.location = (-1214.0120849609375, -357.4307556152344)
    set_spline_type.location = (-1383.7626953125, -306.60443115234375)

    # Set dimensions
    group_input.width, group_input.height = 140.0, 100.0
    group_output.width, group_output.height = 140.0, 100.0
    extrude_mesh.width, extrude_mesh.height = 140.0, 100.0
    combine_xyz.width, combine_xyz.height = 140.0, 100.0
    store_named_attribute.width, store_named_attribute.height = 140.0, 100.0
    combine_xyz_001.width, combine_xyz_001.height = 140.0, 100.0
    capture_attribute.width, capture_attribute.height = 140.0, 100.0
    index.width, index.height = 140.0, 100.0
    sort_elements.width, sort_elements.height = 140.0, 100.0
    shortest_edge_paths.width, shortest_edge_paths.height = 140.0, 100.0
    edge_vertices.width, edge_vertices.height = 140.0, 100.0
    vector_math.width, vector_math.height = 140.0, 100.0
    compare.width, compare.height = 140.0, 100.0
    index_003.width, index_003.height = 140.0, 100.0
    cube.width, cube.height = 140.0, 100.0
    join_geometry.width, join_geometry.height = 140.0, 100.0
    realize_instances.width, realize_instances.height = 140.0, 100.0
    instance_on_points.width, instance_on_points.height = 140.0, 100.0
    translate_instances.width, translate_instances.height = 140.0, 100.0
    frame.width, frame.height = 1717.642578125, 511.5999755859375
    frame_001.width, frame_001.height = 1917.899169921875, 513.0560302734375
    set_material.width, set_material.height = 179.17587280273438, 100.0
    set_material_001.width, set_material_001.height = 176.2990264892578, 100.0
    store_named_attribute_001.width, store_named_attribute_001.height = 140.0, 100.0
    capture_attribute_001.width, capture_attribute_001.height = 140.0, 100.0
    combine_xyz_002.width, combine_xyz_002.height = 140.0, 100.0
    position.width, position.height = 140.0, 100.0
    separate_xyz.width, separate_xyz.height = 140.0, 100.0
    math.width, math.height = 140.0, 100.0
    separate_xyz_001.width, separate_xyz_001.height = 140.0, 100.0
    extrude_mesh_001.width, extrude_mesh_001.height = 140.0, 100.0
    combine_xyz_003.width, combine_xyz_003.height = 140.0, 100.0
    store_named_attribute_002.width, store_named_attribute_002.height = 140.0, 100.0
    combine_xyz_004.width, combine_xyz_004.height = 140.0, 100.0
    capture_attribute_002.width, capture_attribute_002.height = 140.0, 100.0
    index_001.width, index_001.height = 140.0, 100.0
    frame_002.width, frame_002.height = 1707.030517578125, 514.800048828125
    set_material_002.width, set_material_002.height = 179.17587280273438, 100.0
    set_position.width, set_position.height = 140.0, 100.0
    compare_001.width, compare_001.height = 140.0, 100.0
    compare_002.width, compare_002.height = 140.0, 100.0
    delete_geometry.width, delete_geometry.height = 140.0, 100.0
    delete_geometry_001.width, delete_geometry_001.height = 140.0, 100.0
    vector_math_001.width, vector_math_001.height = 140.0, 100.0
    group_input_001.width, group_input_001.height = 140.0, 100.0
    group_input_002.width, group_input_002.height = 140.0, 100.0
    group_input_003.width, group_input_003.height = 140.0, 100.0
    store_named_attribute_003.width, store_named_attribute_003.height = 140.0, 100.0
    vector_math_002.width, vector_math_002.height = 140.0, 100.0
    set_position_001.width, set_position_001.height = 140.0, 100.0
    extrude_mesh_002.width, extrude_mesh_002.height = 140.0, 100.0
    combine_xyz_005.width, combine_xyz_005.height = 140.0, 100.0
    store_named_attribute_004.width, store_named_attribute_004.height = 140.0, 100.0
    combine_xyz_006.width, combine_xyz_006.height = 140.0, 100.0
    capture_attribute_003.width, capture_attribute_003.height = 140.0, 100.0
    index_002.width, index_002.height = 140.0, 100.0
    frame_003.width, frame_003.height = 2047.2001953125, 539.5999755859375
    set_material_003.width, set_material_003.height = 179.17587280273438, 100.0
    compare_003.width, compare_003.height = 140.0, 100.0
    delete_geometry_002.width, delete_geometry_002.height = 140.0, 100.0
    vector_math_003.width, vector_math_003.height = 140.0, 100.0
    group_input_004.width, group_input_004.height = 140.0, 100.0
    set_position_002.width, set_position_002.height = 140.0, 100.0
    join_geometry_001.width, join_geometry_001.height = 140.0, 100.0
    set_position_003.width, set_position_003.height = 140.0, 100.0
    group_input_005.width, group_input_005.height = 140.0, 100.0
    group_input_006.width, group_input_006.height = 140.0, 100.0
    group_input_007.width, group_input_007.height = 140.0, 100.0
    reroute.width, reroute.height = 16.0, 100.0
    reroute_001.width, reroute_001.height = 16.0, 100.0
    reroute_002.width, reroute_002.height = 16.0, 100.0
    reroute_003.width, reroute_003.height = 16.0, 100.0
    reroute_004.width, reroute_004.height = 16.0, 100.0
    reroute_005.width, reroute_005.height = 16.0, 100.0
    reroute_006.width, reroute_006.height = 16.0, 100.0
    reroute_007.width, reroute_007.height = 16.0, 100.0
    math_001.width, math_001.height = 140.0, 100.0
    map_range.width, map_range.height = 140.0, 100.0
    math_002.width, math_002.height = 140.0, 100.0
    map_range_001.width, map_range_001.height = 140.0, 100.0
    math_003.width, math_003.height = 140.0, 100.0
    map_range_002.width, map_range_002.height = 140.0, 100.0
    separate_components.width, separate_components.height = 140.0, 100.0
    group_input_008.width, group_input_008.height = 140.0, 100.0
    join_geometry_002.width, join_geometry_002.height = 140.0, 100.0
    curve_to_mesh.width, curve_to_mesh.height = 140.0, 100.0
    set_spline_type.width, set_spline_type.height = 140.0, 100.0

    # initialize _rbr_fence links
    # combine_xyz.Vector -> extrude_mesh.Offset
    _rbr_fence.links.new(
        socket(combine_xyz.outputs, "Vector"), socket(extrude_mesh.inputs, "Offset")
    )
    # set_position_001.Geometry -> store_named_attribute.Geometry
    _rbr_fence.links.new(
        socket(set_position_001.outputs, "Geometry"),
        socket(store_named_attribute.inputs, "Geometry"),
    )
    # vector_math_001.Vector -> store_named_attribute.Value
    _rbr_fence.links.new(
        socket(vector_math_001.outputs, "Vector"),
        socket(store_named_attribute.inputs, "Value"),
    )
    # capture_attribute.Geometry -> extrude_mesh.Mesh
    _rbr_fence.links.new(
        socket(capture_attribute.outputs, "Geometry"),
        socket(extrude_mesh.inputs, "Mesh"),
    )
    # index.Index -> capture_attribute.Total Cost
    _rbr_fence.links.new(
        socket(index.outputs, "Index"), socket(capture_attribute.inputs, "Total Cost")
    )
    # compare.Result -> shortest_edge_paths.End Vertex
    _rbr_fence.links.new(
        socket(compare.outputs, "Result"),
        socket(shortest_edge_paths.inputs, "End Vertex"),
    )
    # edge_vertices.Position 1 -> vector_math.Vector
    _rbr_fence.links.new(
        socket(edge_vertices.outputs, "Position 1"),
        socket(vector_math.inputs, "Vector", 0),
    )
    # edge_vertices.Position 2 -> vector_math.Vector
    _rbr_fence.links.new(
        socket(edge_vertices.outputs, "Position 2"),
        socket(vector_math.inputs, "Vector", 1),
    )
    # vector_math.Value -> shortest_edge_paths.Edge Cost
    _rbr_fence.links.new(
        socket(vector_math.outputs, "Value"),
        socket(shortest_edge_paths.inputs, "Edge Cost"),
    )
    # index_003.Index -> compare.A
    _rbr_fence.links.new(
        socket(index_003.outputs, "Index"), socket(compare.inputs, "A")
    )
    # extrude_mesh.Top -> combine_xyz_001.Y
    _rbr_fence.links.new(
        socket(extrude_mesh.outputs, "Top"), socket(combine_xyz_001.inputs, "Y")
    )
    # instance_on_points.Instances -> translate_instances.Instances
    _rbr_fence.links.new(
        socket(instance_on_points.outputs, "Instances"),
        socket(translate_instances.inputs, "Instances"),
    )
    # store_named_attribute.Geometry -> set_material.Geometry
    _rbr_fence.links.new(
        socket(store_named_attribute.outputs, "Geometry"),
        socket(set_material.inputs, "Geometry"),
    )
    # translate_instances.Instances -> realize_instances.Geometry
    _rbr_fence.links.new(
        socket(translate_instances.outputs, "Instances"),
        socket(realize_instances.inputs, "Geometry"),
    )
    # store_named_attribute_001.Geometry -> set_material_001.Geometry
    _rbr_fence.links.new(
        socket(store_named_attribute_001.outputs, "Geometry"),
        socket(set_material_001.inputs, "Geometry"),
    )
    # cube.Mesh -> capture_attribute_001.Geometry
    _rbr_fence.links.new(
        socket(cube.outputs, "Mesh"), socket(capture_attribute_001.inputs, "Geometry")
    )
    # capture_attribute_001.Geometry -> instance_on_points.Instance
    _rbr_fence.links.new(
        socket(capture_attribute_001.outputs, "Geometry"),
        socket(instance_on_points.inputs, "Instance"),
    )
    # capture_attribute_001.UV Map -> store_named_attribute_001.Value
    _rbr_fence.links.new(
        socket(capture_attribute_001.outputs, "UV Map"),
        socket(store_named_attribute_001.inputs, "Value"),
    )
    # combine_xyz_002.Vector -> capture_attribute_001.UV Map
    _rbr_fence.links.new(
        socket(combine_xyz_002.outputs, "Vector"),
        socket(capture_attribute_001.inputs, "UV Map"),
    )
    # position.Position -> separate_xyz.Vector
    _rbr_fence.links.new(
        socket(position.outputs, "Position"), socket(separate_xyz.inputs, "Vector")
    )
    # math.Value -> combine_xyz_002.Y
    _rbr_fence.links.new(
        socket(math.outputs, "Value"), socket(combine_xyz_002.inputs, "Y")
    )
    # separate_xyz.Z -> math.Value
    _rbr_fence.links.new(
        socket(separate_xyz.outputs, "Z"), socket(math.inputs, "Value", 0)
    )
    # cube.UV Map -> separate_xyz_001.Vector
    _rbr_fence.links.new(
        socket(cube.outputs, "UV Map"), socket(separate_xyz_001.inputs, "Vector")
    )
    # separate_xyz_001.X -> combine_xyz_002.X
    _rbr_fence.links.new(
        socket(separate_xyz_001.outputs, "X"), socket(combine_xyz_002.inputs, "X")
    )
    # combine_xyz_003.Vector -> extrude_mesh_001.Offset
    _rbr_fence.links.new(
        socket(combine_xyz_003.outputs, "Vector"),
        socket(extrude_mesh_001.inputs, "Offset"),
    )
    # set_position.Geometry -> store_named_attribute_002.Geometry
    _rbr_fence.links.new(
        socket(set_position.outputs, "Geometry"),
        socket(store_named_attribute_002.inputs, "Geometry"),
    )
    # vector_math_002.Vector -> store_named_attribute_002.Value
    _rbr_fence.links.new(
        socket(vector_math_002.outputs, "Vector"),
        socket(store_named_attribute_002.inputs, "Value"),
    )
    # index_001.Index -> capture_attribute_002.Total Cost
    _rbr_fence.links.new(
        socket(index_001.outputs, "Index"),
        socket(capture_attribute_002.inputs, "Total Cost"),
    )
    # extrude_mesh_001.Top -> combine_xyz_004.Y
    _rbr_fence.links.new(
        socket(extrude_mesh_001.outputs, "Top"), socket(combine_xyz_004.inputs, "Y")
    )
    # store_named_attribute_002.Geometry -> set_material_002.Geometry
    _rbr_fence.links.new(
        socket(store_named_attribute_002.outputs, "Geometry"),
        socket(set_material_002.inputs, "Geometry"),
    )
    # math_001.Value -> combine_xyz_004.X
    _rbr_fence.links.new(
        socket(math_001.outputs, "Value"), socket(combine_xyz_004.inputs, "X")
    )
    # extrude_mesh_001.Mesh -> set_position.Geometry
    _rbr_fence.links.new(
        socket(extrude_mesh_001.outputs, "Mesh"),
        socket(set_position.inputs, "Geometry"),
    )
    # set_material_001.Geometry -> join_geometry.Geometry
    _rbr_fence.links.new(
        socket(set_material_001.outputs, "Geometry"),
        socket(join_geometry.inputs, "Geometry"),
    )
    # compare_001.Result -> delete_geometry.Selection
    _rbr_fence.links.new(
        socket(compare_001.outputs, "Result"),
        socket(delete_geometry.inputs, "Selection"),
    )
    # compare_002.Result -> delete_geometry_001.Selection
    _rbr_fence.links.new(
        socket(compare_002.outputs, "Result"),
        socket(delete_geometry_001.inputs, "Selection"),
    )
    # delete_geometry_001.Geometry -> capture_attribute.Geometry
    _rbr_fence.links.new(
        socket(delete_geometry_001.outputs, "Geometry"),
        socket(capture_attribute.inputs, "Geometry"),
    )
    # capture_attribute_002.Geometry -> extrude_mesh_001.Mesh
    _rbr_fence.links.new(
        socket(capture_attribute_002.outputs, "Geometry"),
        socket(extrude_mesh_001.inputs, "Mesh"),
    )
    # delete_geometry.Geometry -> capture_attribute_002.Geometry
    _rbr_fence.links.new(
        socket(delete_geometry.outputs, "Geometry"),
        socket(capture_attribute_002.inputs, "Geometry"),
    )
    # combine_xyz_001.Vector -> vector_math_001.Vector
    _rbr_fence.links.new(
        socket(combine_xyz_001.outputs, "Vector"),
        socket(vector_math_001.inputs, "Vector", 0),
    )
    # group_input_001.Tile Material -> set_material.Material
    _rbr_fence.links.new(
        socket(group_input_001.outputs, "Tile Material"),
        socket(set_material.inputs, "Material"),
    )
    # group_input_002.Pole Material -> set_material_001.Material
    _rbr_fence.links.new(
        socket(group_input_002.outputs, "Pole Material"),
        socket(set_material_001.inputs, "Material"),
    )
    # group_input_003.Tile Material -> set_material_002.Material
    _rbr_fence.links.new(
        socket(group_input_003.outputs, "Tile Material"),
        socket(set_material_002.inputs, "Material"),
    )
    # group_input.Vertex Color -> store_named_attribute_003.Value
    _rbr_fence.links.new(
        socket(group_input.outputs, "Vertex Color"),
        socket(store_named_attribute_003.inputs, "Value"),
    )
    # join_geometry.Geometry -> group_output.Geometry
    _rbr_fence.links.new(
        socket(join_geometry.outputs, "Geometry"),
        socket(group_output.inputs, "Geometry"),
    )
    # combine_xyz_004.Vector -> vector_math_002.Vector
    _rbr_fence.links.new(
        socket(combine_xyz_004.outputs, "Vector"),
        socket(vector_math_002.inputs, "Vector", 0),
    )
    # realize_instances.Geometry -> store_named_attribute_001.Geometry
    _rbr_fence.links.new(
        socket(realize_instances.outputs, "Geometry"),
        socket(store_named_attribute_001.inputs, "Geometry"),
    )
    # extrude_mesh.Mesh -> set_position_001.Geometry
    _rbr_fence.links.new(
        socket(extrude_mesh.outputs, "Mesh"),
        socket(set_position_001.inputs, "Geometry"),
    )
    # shortest_edge_paths.Total Cost -> sort_elements.Sort Weight
    _rbr_fence.links.new(
        socket(shortest_edge_paths.outputs, "Total Cost"),
        socket(sort_elements.inputs, "Sort Weight"),
    )
    # join_geometry_002.Geometry -> store_named_attribute_003.Geometry
    _rbr_fence.links.new(
        socket(join_geometry_002.outputs, "Geometry"),
        socket(store_named_attribute_003.inputs, "Geometry"),
    )
    # combine_xyz_005.Vector -> extrude_mesh_002.Offset
    _rbr_fence.links.new(
        socket(combine_xyz_005.outputs, "Vector"),
        socket(extrude_mesh_002.inputs, "Offset"),
    )
    # vector_math_003.Vector -> store_named_attribute_004.Value
    _rbr_fence.links.new(
        socket(vector_math_003.outputs, "Vector"),
        socket(store_named_attribute_004.inputs, "Value"),
    )
    # capture_attribute_003.Geometry -> extrude_mesh_002.Mesh
    _rbr_fence.links.new(
        socket(capture_attribute_003.outputs, "Geometry"),
        socket(extrude_mesh_002.inputs, "Mesh"),
    )
    # index_002.Index -> capture_attribute_003.Total Cost
    _rbr_fence.links.new(
        socket(index_002.outputs, "Index"),
        socket(capture_attribute_003.inputs, "Total Cost"),
    )
    # extrude_mesh_002.Top -> combine_xyz_006.Y
    _rbr_fence.links.new(
        socket(extrude_mesh_002.outputs, "Top"), socket(combine_xyz_006.inputs, "Y")
    )
    # store_named_attribute_004.Geometry -> set_material_003.Geometry
    _rbr_fence.links.new(
        socket(store_named_attribute_004.outputs, "Geometry"),
        socket(set_material_003.inputs, "Geometry"),
    )
    # compare_003.Result -> delete_geometry_002.Selection
    _rbr_fence.links.new(
        socket(compare_003.outputs, "Result"),
        socket(delete_geometry_002.inputs, "Selection"),
    )
    # delete_geometry_002.Geometry -> capture_attribute_003.Geometry
    _rbr_fence.links.new(
        socket(delete_geometry_002.outputs, "Geometry"),
        socket(capture_attribute_003.inputs, "Geometry"),
    )
    # combine_xyz_006.Vector -> vector_math_003.Vector
    _rbr_fence.links.new(
        socket(combine_xyz_006.outputs, "Vector"),
        socket(vector_math_003.inputs, "Vector", 0),
    )
    # group_input_004.Tile Material -> set_material_003.Material
    _rbr_fence.links.new(
        socket(group_input_004.outputs, "Tile Material"),
        socket(set_material_003.inputs, "Material"),
    )
    # set_material_003.Geometry -> set_position_003.Geometry
    _rbr_fence.links.new(
        socket(set_material_003.outputs, "Geometry"),
        socket(set_position_003.inputs, "Geometry"),
    )
    # set_position_003.Geometry -> join_geometry_001.Geometry
    _rbr_fence.links.new(
        socket(set_position_003.outputs, "Geometry"),
        socket(join_geometry_001.inputs, "Geometry"),
    )
    # extrude_mesh_002.Mesh -> store_named_attribute_004.Geometry
    _rbr_fence.links.new(
        socket(extrude_mesh_002.outputs, "Mesh"),
        socket(store_named_attribute_004.inputs, "Geometry"),
    )
    # set_material_003.Geometry -> set_position_002.Geometry
    _rbr_fence.links.new(
        socket(set_material_003.outputs, "Geometry"),
        socket(set_position_002.inputs, "Geometry"),
    )
    # group_input_005.Fence Kind -> compare_001.A
    _rbr_fence.links.new(
        socket(group_input_005.outputs, "Fence Kind"), socket(compare_001.inputs, "A")
    )
    # group_input_006.Fence Kind -> compare_002.A
    _rbr_fence.links.new(
        socket(group_input_006.outputs, "Fence Kind"), socket(compare_002.inputs, "A")
    )
    # group_input_007.Fence Kind -> compare_003.A
    _rbr_fence.links.new(
        socket(group_input_007.outputs, "Fence Kind"), socket(compare_003.inputs, "A")
    )
    # reroute_001.Output -> reroute.Input
    _rbr_fence.links.new(
        socket(reroute_001.outputs, "Output"), socket(reroute.inputs, "Input")
    )
    # reroute.Output -> instance_on_points.Points
    _rbr_fence.links.new(
        socket(reroute.outputs, "Output"), socket(instance_on_points.inputs, "Points")
    )
    # store_named_attribute_003.Geometry -> reroute_001.Input
    _rbr_fence.links.new(
        socket(store_named_attribute_003.outputs, "Geometry"),
        socket(reroute_001.inputs, "Input"),
    )
    # reroute_003.Output -> delete_geometry_002.Geometry
    _rbr_fence.links.new(
        socket(reroute_003.outputs, "Output"),
        socket(delete_geometry_002.inputs, "Geometry"),
    )
    # reroute_002.Output -> reroute_003.Input
    _rbr_fence.links.new(
        socket(reroute_002.outputs, "Output"), socket(reroute_003.inputs, "Input")
    )
    # store_named_attribute_003.Geometry -> reroute_002.Input
    _rbr_fence.links.new(
        socket(store_named_attribute_003.outputs, "Geometry"),
        socket(reroute_002.inputs, "Input"),
    )
    # reroute_004.Output -> delete_geometry_001.Geometry
    _rbr_fence.links.new(
        socket(reroute_004.outputs, "Output"),
        socket(delete_geometry_001.inputs, "Geometry"),
    )
    # reroute_005.Output -> reroute_004.Input
    _rbr_fence.links.new(
        socket(reroute_005.outputs, "Output"), socket(reroute_004.inputs, "Input")
    )
    # store_named_attribute_003.Geometry -> reroute_005.Input
    _rbr_fence.links.new(
        socket(store_named_attribute_003.outputs, "Geometry"),
        socket(reroute_005.inputs, "Input"),
    )
    # reroute_007.Output -> reroute_006.Input
    _rbr_fence.links.new(
        socket(reroute_007.outputs, "Output"), socket(reroute_006.inputs, "Input")
    )
    # reroute_006.Output -> delete_geometry.Geometry
    _rbr_fence.links.new(
        socket(reroute_006.outputs, "Output"),
        socket(delete_geometry.inputs, "Geometry"),
    )
    # store_named_attribute_003.Geometry -> reroute_007.Input
    _rbr_fence.links.new(
        socket(store_named_attribute_003.outputs, "Geometry"),
        socket(reroute_007.inputs, "Input"),
    )
    # capture_attribute_002.Total Cost -> math_001.Value
    _rbr_fence.links.new(
        socket(capture_attribute_002.outputs, "Total Cost"),
        socket(math_001.inputs, "Value", 0),
    )
    # group_input_005.Subdivide -> map_range.Value
    _rbr_fence.links.new(
        socket(group_input_005.outputs, "Subdivide"), socket(map_range.inputs, "Value")
    )
    # map_range.Result -> math_001.Value
    _rbr_fence.links.new(
        socket(map_range.outputs, "Result"), socket(math_001.inputs, "Value", 1)
    )
    # map_range_001.Result -> math_002.Value
    _rbr_fence.links.new(
        socket(map_range_001.outputs, "Result"), socket(math_002.inputs, "Value", 1)
    )
    # math_002.Value -> combine_xyz_001.X
    _rbr_fence.links.new(
        socket(math_002.outputs, "Value"), socket(combine_xyz_001.inputs, "X")
    )
    # capture_attribute.Total Cost -> math_002.Value
    _rbr_fence.links.new(
        socket(capture_attribute.outputs, "Total Cost"),
        socket(math_002.inputs, "Value", 0),
    )
    # group_input_006.Subdivide -> map_range_001.Value
    _rbr_fence.links.new(
        socket(group_input_006.outputs, "Subdivide"),
        socket(map_range_001.inputs, "Value"),
    )
    # map_range_002.Result -> math_003.Value
    _rbr_fence.links.new(
        socket(map_range_002.outputs, "Result"), socket(math_003.inputs, "Value", 1)
    )
    # capture_attribute_003.Total Cost -> math_003.Value
    _rbr_fence.links.new(
        socket(capture_attribute_003.outputs, "Total Cost"),
        socket(math_003.inputs, "Value", 0),
    )
    # math_003.Value -> combine_xyz_006.X
    _rbr_fence.links.new(
        socket(math_003.outputs, "Value"), socket(combine_xyz_006.inputs, "X")
    )
    # group_input_007.Subdivide -> map_range_002.Value
    _rbr_fence.links.new(
        socket(group_input_007.outputs, "Subdivide"),
        socket(map_range_002.inputs, "Value"),
    )
    # group_input_008.Geometry -> separate_components.Geometry
    _rbr_fence.links.new(
        socket(group_input_008.outputs, "Geometry"),
        socket(separate_components.inputs, "Geometry"),
    )
    # separate_components.Mesh -> sort_elements.Geometry
    _rbr_fence.links.new(
        socket(separate_components.outputs, "Mesh"),
        socket(sort_elements.inputs, "Geometry"),
    )
    # sort_elements.Geometry -> join_geometry_002.Geometry
    _rbr_fence.links.new(
        socket(sort_elements.outputs, "Geometry"),
        socket(join_geometry_002.inputs, "Geometry"),
    )
    # set_spline_type.Curve -> curve_to_mesh.Curve
    _rbr_fence.links.new(
        socket(set_spline_type.outputs, "Curve"), socket(curve_to_mesh.inputs, "Curve")
    )
    # separate_components.Curve -> set_spline_type.Curve
    _rbr_fence.links.new(
        socket(separate_components.outputs, "Curve"),
        socket(set_spline_type.inputs, "Curve"),
    )
    # join_geometry_001.Geometry -> join_geometry.Geometry
    _rbr_fence.links.new(
        socket(join_geometry_001.outputs, "Geometry"),
        socket(join_geometry.inputs, "Geometry"),
    )
    # set_position_002.Geometry -> join_geometry_001.Geometry
    _rbr_fence.links.new(
        socket(set_position_002.outputs, "Geometry"),
        socket(join_geometry_001.inputs, "Geometry"),
    )
    # curve_to_mesh.Mesh -> join_geometry_002.Geometry
    _rbr_fence.links.new(
        socket(curve_to_mesh.outputs, "Mesh"),
        socket(join_geometry_002.inputs, "Geometry"),
    )
    # set_material.Geometry -> join_geometry.Geometry
    _rbr_fence.links.new(
        socket(set_material.outputs, "Geometry"),
        socket(join_geometry.inputs, "Geometry"),
    )
    # set_material_002.Geometry -> join_geometry.Geometry
    _rbr_fence.links.new(
        socket(set_material_002.outputs, "Geometry"),
        socket(join_geometry.inputs, "Geometry"),
    )
    return narrow(_rbr_fence, bpy.types.GeometryNodeTree)
