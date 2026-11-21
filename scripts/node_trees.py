"""Build every node tree the addon generates in headless blender (the bpy pip
module) and fail on any error. Sockets are looked up with socket(), which raises
when a name is missing or ambiguous, so this catches socket changes in new
blender versions. Run via scripts/smoke.sh.

Builders are called directly rather than through custom node init(), because
blender prints exceptions raised in init() instead of propagating them.
"""

import os
import sys

import bpy  # type: ignore

# importable only once bpy has set up blender's script paths
import addon_utils  # type: ignore

ADDON_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ADDON_DIR)

if addon_utils.enable("rbr_track_exporter", default_set=True, persistent=False) is None:
    sys.exit("node trees FAILED: could not enable rbr_track_exporter")

from rbr_track_exporter.gnodes.brake_wall import make_brakewall_node_group  # noqa: E402
from rbr_track_exporter.properties.fence import (  # noqa: E402
    get_or_create_fence_material,
    get_or_create_fence_modifier,
)
from rbr_track_exporter.shaders.brake_wall import setup_brake_wall_tree  # noqa: E402
from rbr_track_exporter.shaders.shader_node import (  # noqa: E402
    create_rbr_shader_node_tree,
)
from rbr_track_exporter.shaders.sky import setup_sky_node_tree  # noqa: E402
from rbr_track_exporter.shaders.texture import setup_texture_node_tree  # noqa: E402
from rbr_track_exporter.shaders.tint_set import setup_tint_set_node_tree  # noqa: E402
from rbr_track_exporter.shaders.uv_velocity import (  # noqa: E402
    setup_uv_velocity_node_tree,
)
from rbr_track_exporter.types import RBRMeshMaterialType  # noqa: E402

for mesh_type in RBRMeshMaterialType:
    create_rbr_shader_node_tree(mesh_type)
setup_tint_set_node_tree()
setup_uv_velocity_node_tree()
setup_texture_node_tree(bpy.context, "node_trees", is_road_surface=False)
setup_texture_node_tree(bpy.context, "node_trees_road", is_road_surface=True)
setup_sky_node_tree(bpy.data.node_groups.new("node_trees_sky", "ShaderNodeTree"))
setup_brake_wall_tree(bpy.data.node_groups.new("node_trees_bw", "ShaderNodeTree"))
make_brakewall_node_group()
get_or_create_fence_material(bpy.data.images.new("node_trees", 4, 4))

# A straight fence: every tile section must span a range of the texture, not
# just the first (blender 5.2 shifted capture attribute sockets, which left
# every later section collapsed to a single texel).
mesh = bpy.data.meshes.new("fence")
mesh.from_pydata([(x, 0, 0) for x in (0, 4, 8, 12)], [(0, 1), (1, 2), (2, 3)], [])
obj = bpy.data.objects.new("fence", mesh)
bpy.context.scene.collection.objects.link(obj)
mesh.rbr_mesh_settings.mesh_type = "FENCE"
get_or_create_fence_modifier(obj, mesh.rbr_mesh_settings.fence)
evaluated = obj.evaluated_get(bpy.context.evaluated_depsgraph_get()).to_mesh()
uv = evaluated.attributes[".rbr.uv"]
tiles = 0
for poly in evaluated.polygons:
    xs = [
        evaluated.vertices[evaluated.loops[i].vertex_index].co.x
        for i in poly.loop_indices
    ]
    if max(xs) - min(xs) < 1:
        continue
    tiles += 1
    us = [uv.data[i].vector[0] for i in poly.loop_indices]
    if max(us) - min(us) <= 0:
        sys.exit(
            f"node trees FAILED: fence tile at x={min(xs)}..{max(xs)} has no UV span"
        )
if tiles != 3:
    sys.exit(f"node trees FAILED: expected 3 fence tiles, got {tiles}")

print("node trees passed")
