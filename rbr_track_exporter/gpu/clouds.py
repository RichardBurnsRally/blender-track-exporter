from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple
import os
import zipfile
import tempfile

import bpy
from ..blender_utils import narrow
import gpu
import gpu_extras
import mathutils
import numpy as np

from ..preferences import RBRAddonPreferences
from ..types import CloudName, SurfaceType
from . import clouds_data
from .. import __package__ as base_package


# Shader compilation needs a GPU context, which doesn't exist at import time
# in background mode, so everything GPU-flavoured is created lazily on the
# first draw_clouds call.
class GpuData:
    def __init__(self) -> None:
        vert_out = gpu.types.GPUStageInterfaceInfo("rbr_clouds")
        vert_out.smooth("VEC4", "frag_color")
        vert_out.smooth("VEC2", "frag_uv")
        vert_out.smooth("FLOAT", "frag_depth")

        shader_info = gpu.types.GPUShaderCreateInfo()
        shader_info.push_constant("MAT4", "world_to_window")
        shader_info.vertex_in(0, "VEC3", "vert_pos")
        shader_info.vertex_in(1, "VEC4", "vert_color")
        shader_info.vertex_in(2, "VEC2", "vert_uv")
        shader_info.sampler(0, "FLOAT_2D", "image")
        shader_info.vertex_out(vert_out)
        shader_info.fragment_out(0, "VEC4", "FragColor")

        shader_info.vertex_source(
            "void main() {"
            "  frag_color = vert_color;"
            "  frag_uv = vert_uv;"
            "  frag_depth = length(vert_pos);"
            "  gl_Position = world_to_window * vec4(vert_pos, 1.0f);"
            "}"
        )

        shader_info.fragment_source(
            "void main() {"
            "  float4 tex = texture(image, frag_uv);"
            "  FragColor.xyz = frag_color.xyz * tex.xyz;"
            "  FragColor.w = frag_color.w * tex.w;"
            "  FragColor.xyz *= FragColor.w;"
            "}"
        )
        self.shader = gpu.shader.create_from_info(shader_info)

        shader_info.fragment_source(
            "void main() {"
            "  float4 tex_linear = texture(image, frag_uv);"
            "  FragColor.xyz = vec3(frag_depth);"
            # deliberately not multiplying frag_color.w to get a more "accurate" depth
            "  FragColor.w = tex_linear.w;"
            "  FragColor.xyz *= FragColor.w;"
            "}"
        )
        self.depth_shader = gpu.shader.create_from_info(shader_info)

        self.batches: Dict[CloudName, gpu.types.GPUBatch] = {
            CloudName.CLEAR: self.make_batch(clouds_data.clear),
            CloudName.CLEAR02: self.make_batch(clouds_data.clear02),
            CloudName.CLOUDED: self.make_batch(clouds_data.clouded),
            CloudName.CLOUDED02: self.make_batch(clouds_data.clouded02),
            CloudName.OVERCAST: self.make_batch(clouds_data.overcast),
            CloudName.OVERCAST02: self.make_batch(clouds_data.overcast02),
            CloudName.PARTLY_CLOUDED: self.make_batch(clouds_data.partly_clouded),
            CloudName.PARTLY_CLOUDED02: self.make_batch(clouds_data.partly_clouded02),
            CloudName.PRECIPITATION: self.make_batch(clouds_data.precipitation),
            CloudName.PRECIPITATION_PC: self.make_batch(clouds_data.precipitation_pc),
            CloudName.PRECIPITATION02_PC: self.make_batch(
                clouds_data.precipitation02_pc
            ),
        }

    def make_batch(
        self,
        verts: List[
            Tuple[
                Tuple[float, float, float],  # position
                Tuple[float, float, float, float],  # color
                Tuple[float, float],  # uv
            ]
        ],
    ) -> Any:
        pos = [(x, z, y) for ((x, y, z), _, _) in verts]
        color = [c for (_, c, _) in verts]
        uv = [(u, -v) for (_, _, (u, v)) in verts]
        return gpu_extras.batch.batch_for_shader(
            self.shader,
            "TRIS",
            {
                "vert_pos": pos,
                "vert_color": color,
                "vert_uv": uv,
            },
        )


_gpu_data: Optional[GpuData] = None


def gpu_data() -> GpuData:
    global _gpu_data
    if _gpu_data is None:
        _gpu_data = GpuData()
    return _gpu_data


def look_at(
    eye: mathutils.Vector,
    center: mathutils.Vector,
    up: mathutils.Vector,
) -> mathutils.Matrix:
    f = (center - eye).normalized()
    up = up.normalized()
    s = narrow(f.cross(up), mathutils.Vector)
    u = narrow(s.normalized().cross(f), mathutils.Vector)
    return mathutils.Matrix(
        [
            [s.x, s.y, s.z, 0],
            [u.x, u.y, u.z, 0],
            [-f.x, -f.y, -f.z, 0],
            [0, 0, 0, 1],
        ]
    )


def perspective(
    near: float,
    far: float,
) -> mathutils.Matrix:
    x = (far + near) / (near - far)
    y = (2 * far * near) / (near - far)
    return mathutils.Matrix(
        [
            [1, 0, 0, 0],
            [0, 1, 0, 0],
            [0, 0, x, y],
            [0, 0, -1, 0],
        ]
    )


@dataclass
class View:
    vector: mathutils.Vector
    up: mathutils.Vector


views = [
    View(mathutils.Vector((1, 0, 0)), mathutils.Vector((0, 0, 1))),
    View(mathutils.Vector((0, -1, 0)), mathutils.Vector((0, 0, 1))),
    View(mathutils.Vector((-1, 0, 0)), mathutils.Vector((0, 0, 1))),
    View(mathutils.Vector((0, 1, 0)), mathutils.Vector((0, 0, 1))),
    View(mathutils.Vector((0, 0, 1)), mathutils.Vector((0, 1, 0))),
    View(mathutils.Vector((0, 0, -1)), mathutils.Vector((0, 1, 0))),
]


def load_cloud_texture(surface: SurfaceType, name: str) -> Optional[bytes]:
    if bpy.context.preferences is None or bpy.context.scene is None:
        return None
    prefs = narrow(
        bpy.context.preferences.addons[base_package].preferences,
        RBRAddonPreferences,
    )
    export_to = bpy.context.scene.rbr_scene_settings.export_to
    export_dir = prefs.get_export_directory(export_to)
    if export_dir is None:
        return None
    try:
        rbz_path = os.path.join(export_dir, "Clouds_textures.rbz")
        with zipfile.ZipFile(rbz_path) as rbz:
            surface_dir = ""
            if surface is SurfaceType.DRY:
                surface_dir = "dry"
            elif surface is SurfaceType.DAMP:
                surface_dir = "damp"
            elif surface is SurfaceType.WET:
                surface_dir = "wet"
            else:
                raise NotImplementedError(surface)
            at = f"Clouds_textures/{surface_dir}/"
            dry = zipfile.Path(rbz, at=at)
            for path in dry.iterdir():
                parts = path.name.split(sep=".")
                stem = parts[0]
                if stem.lower() != name.lower():
                    continue
                with path.open(mode="rb") as file:
                    data: bytes = file.read()
                    return data
            return None
    except FileNotFoundError as e:
        print("Missing clouds:", e)
        return None


def render_offscreen(
    size: int,
    cloud_name: CloudName,
    data: GpuData,
    shader: gpu.types.GPUShader,
    clear_color: Tuple[float, float, float, float],
) -> Any:
    offscreen = gpu.types.GPUOffScreen(size * 6, size, format="RGBA32F")
    with offscreen.bind():
        # Depth write off, test off
        gpu.state.depth_mask_set(False)
        gpu.state.depth_test_set("NONE")
        blend = gpu.state.blend_get()
        gpu.state.blend_set("ALPHA_PREMULT")
        gpu.state.face_culling_set("NONE")

        fb = gpu.state.active_framebuffer_get()
        fb.clear(color=clear_color)

        for i, view in enumerate(views):
            world_to_view = look_at(
                eye=mathutils.Vector((0, 0, 0)),
                center=view.vector,
                up=view.up,
            )
            # Skybox is a sphere with radius 100 - clouds are planes within that
            # sphere
            view_to_window = perspective(near=1, far=100)
            world_to_window = view_to_window @ world_to_view
            shader.uniform_float("world_to_window", world_to_window)

            gpu.state.viewport_set(i * size, 0, size, size)

            batch = data.batches.get(cloud_name)
            if batch is None:
                raise NotImplementedError(cloud_name)
            batch.draw(shader)

        gpu.state.blend_set(blend)
    buffer = offscreen.texture_color.read()
    offscreen.free()
    return buffer


def draw_clouds(surface_type: SurfaceType, cloud_name: CloudName) -> None:
    # Load texture into image
    cloud_file = cloud_name.texture_name()
    bytes = load_cloud_texture(surface_type, cloud_file)
    if bytes is None:
        return
    image = bpy.data.images.get(".rbr.clouds.texture")
    if image is not None:
        bpy.data.images.remove(image)
    with tempfile.NamedTemporaryFile(delete=False) as tmp:
        tmp.write(bytes)
        image = bpy.data.images.load(tmp.name)
        image.name = ".rbr.clouds.texture"
        colorspace = image.colorspace_settings
        if colorspace is not None:
            colorspace.is_data = True
    data = gpu_data()
    data.shader.bind()
    texture = gpu.texture.from_image(image)
    data.shader.uniform_sampler("image", texture)

    # Render clouds
    SIZE = 2048
    buffer = render_offscreen(SIZE, cloud_name, data, data.shader, (0.0, 0.0, 0.0, 0.0))
    image = bpy.data.images.get(".rbr.clouds")
    if image is not None:
        image.scale(SIZE * 6, SIZE)
    else:
        image = bpy.data.images.new(
            ".rbr.clouds", SIZE * 6, SIZE, is_data=True, alpha=True, float_buffer=True
        )
    image.alpha_mode = "CHANNEL_PACKED"
    buffer.dimensions = SIZE * 6 * SIZE * 4
    buf = np.frombuffer(buffer, dtype=np.float32)
    image.pixels.foreach_set(buf)
    image.pack()

    # Render clouds depth
    SIZE = 1048
    depth_buffer = render_offscreen(
        SIZE, cloud_name, data, data.depth_shader, (0.0, 0.0, 0.0, 0.0)
    )
    image = bpy.data.images.get(".rbr.clouds.depth")
    if image is not None and image.alpha_mode != "CHANNEL_PACKED":
        bpy.data.images.remove(image)
        image = bpy.data.images.get(".rbr.clouds.depth")
    if image is not None:
        image.scale(SIZE * 6, SIZE)
    else:
        image = bpy.data.images.new(
            ".rbr.clouds.depth",
            SIZE * 6,
            SIZE,
            is_data=True,
            alpha=True,
            float_buffer=True,
        )
        image.alpha_mode = "CHANNEL_PACKED"
    depth_buffer.dimensions = SIZE * 6 * SIZE * 4
    buf = np.frombuffer(depth_buffer, dtype=np.float32)
    r, g, b, a = np.hsplit(buf.reshape((SIZE * 6 * SIZE, 4)), 4)
    # Blender seems to limit pixel values to 1.0 somewhere
    rgb = np.hstack((r / 100, g / 100, b / 100, a)).reshape(SIZE * 6 * SIZE * 4)
    image.pixels.foreach_set(rgb)
    image.pack()
