"""Screenshot example node trees for the docs, in the blender UI. Run via
scripts/docs-screenshots.sh; writes docs/src/images/<name>.png.

Each shot builds a node tree, shows it maximised in a node editor with the
side panels hidden, frames it, captures the editor and crops the capture to
the nodes. Under the AeroSpace window manager the window is made fullscreen
first, since it would otherwise be tiled small.
"""

import hashlib
import os
import shutil
import subprocess
import sys
from typing import Iterator, List, Optional, Tuple

import bpy
import addon_utils
import numpy as np

ADDON_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT_DIR = os.path.join(ADDON_DIR, "docs", "src", "images")
sys.path.insert(0, ADDON_DIR)
addon_utils.enable("rbr_track_exporter", default_set=True, persistent=False)

from rbr_track_exporter.shaders.texture import setup_texture_node_tree  # noqa: E402

WIDTH = 1600  # of the saved images
PAD = 60


# Building


def place(node, x, y, label=None):
    node.location = (x, y)
    if label:
        node.label = label
    node.select = False
    return node


def new_material(name):
    material = bpy.data.materials.new(name)
    tree = material.node_tree
    for n in list(tree.nodes):
        tree.nodes.remove(n)
    return material, tree


def output(tree, x, y):
    return place(tree.nodes.new("ShaderNodeOutputMaterial"), x, y)


def shader(tree, mesh_type, x, y):
    node = place(tree.nodes.new("ShaderNodeRBR"), x, y)
    node.mesh_type = mesh_type
    return node


def uv_map(tree, name, x, y):
    node = place(tree.nodes.new("ShaderNodeUVMap"), x, y)
    node.uv_map = name
    return node


def texture(tree, name, uv, x, y):
    node = place(tree.nodes.new("ShaderNodeRBRTexture"), x, y)
    node.node_tree = setup_texture_node_tree(bpy.context, name, False)
    tree.links.new(uv.outputs[0], node.inputs["UV"])
    return node


def attribute(tree, name, x, y):
    node = place(tree.nodes.new("ShaderNodeAttribute"), x, y)
    node.attribute_name = name
    return node


def geom_block():
    material, tree = new_material("Ground")
    out = output(tree, 450, 0)
    rbr = shader(tree, "GEOM_BLOCK", 150, 0)
    tex = texture(tree, "gravel", uv_map(tree, "uv-1", -650, -60), -420, 40)
    vcol = attribute(tree, "vcol", -120, -330)
    tree.links.new(tex.outputs[0], rbr.inputs["Texture 1"])
    tree.links.new(vcol.outputs["Color"], rbr.inputs["Color"])
    tree.links.new(vcol.outputs["Alpha"], rbr.inputs["Blend"])
    tree.links.new(rbr.outputs["Surface"], out.inputs["Surface"])
    return material


def geom_block_full():
    material, tree = new_material("Road")
    out = output(tree, 500, 0)
    rbr = shader(tree, "GEOM_BLOCK", 200, 0)
    tex_1 = texture(tree, "tarmac", uv_map(tree, "uv-1", -700, 260), -420, 300)
    tex_2 = texture(tree, "tarmac-dirt", uv_map(tree, "uv-2", -700, -90), -420, -50)
    specular = texture(
        tree, "tarmac-specular", uv_map(tree, "uv-1", -700, -440), -420, -400
    )
    shadow_uv = uv_map(tree, "shadow-uv", -380, -760)
    shadow = place(tree.nodes.new("ShaderNodeTexImage"), -120, -720, "Shadow")
    tree.links.new(shadow_uv.outputs[0], shadow.inputs["Vector"])
    vcol = attribute(tree, "vcol", -120, -1000)
    strength = attribute(tree, "specular-strength", -120, -1220)
    tree.links.new(tex_1.outputs[0], rbr.inputs["Texture 1"])
    tree.links.new(tex_2.outputs[0], rbr.inputs["Texture 2"])
    tree.links.new(specular.outputs[0], rbr.inputs["Specular Texture"])
    tree.links.new(shadow.outputs["Color"], rbr.inputs["Shadow Texture"])
    tree.links.new(vcol.outputs["Color"], rbr.inputs["Color"])
    tree.links.new(vcol.outputs["Alpha"], rbr.inputs["Blend"])
    tree.links.new(strength.outputs["Factor"], rbr.inputs["Specular Strength"])
    tree.links.new(rbr.outputs["Surface"], out.inputs["Surface"])
    return material


def object_block():
    material, tree = new_material("Bush")
    out = output(tree, 450, 0)
    rbr = shader(tree, "OBJECT_BLOCK", 150, 0)
    tex = texture(tree, "bush", uv_map(tree, "uv-1", -650, -60), -420, 40)
    vcol = attribute(tree, "vcol", -120, -330)
    tree.links.new(tex.outputs[0], rbr.inputs["Texture"])
    tree.links.new(vcol.outputs["Color"], rbr.inputs["Color"])
    tree.links.new(vcol.outputs["Alpha"], rbr.inputs["Alpha"])
    rbr.inputs["Amplitude"].default_value = 0.3
    tree.links.new(rbr.outputs["Surface"], out.inputs["Surface"])
    tree.links.new(rbr.outputs["Displacement"], out.inputs["Displacement"])
    return material


def tint_set():
    material, tree = new_material("Tint Sets")
    out = output(tree, 450, 0)
    rbr = shader(tree, "GEOM_BLOCK", 150, 0)
    tex = texture(tree, "grass", uv_map(tree, "uv-1", -650, 200), -420, 260)
    tint = place(tree.nodes.new("ShaderNodeRBRTintSet"), -120, -330)
    for i, name in enumerate(["Morning", "Noon", "Evening", "Overcast"]):
        vcol = attribute(tree, f"vcol-{name.lower()}", -420, -230 - 170 * i)
        tree.links.new(vcol.outputs["Color"], tint.inputs[name])
    tree.links.new(tex.outputs[0], rbr.inputs["Texture 1"])
    tree.links.new(tint.outputs[0], rbr.inputs["Color"])
    tree.links.new(rbr.outputs["Surface"], out.inputs["Surface"])
    return material


def uv_velocity():
    material, tree = new_material("Water")
    out = output(tree, 450, 0)
    rbr = shader(tree, "WATER_OBJECT", 150, 0)
    uv = uv_map(tree, "uv-1", -900, -60)
    velocity = place(tree.nodes.new("ShaderNodeUVVelocity"), -660, -40)
    velocity.inputs["UV Velocity"].default_value = (0.05, 0.0, 0.0)
    tree.links.new(uv.outputs[0], velocity.inputs["UV"])
    tex = place(tree.nodes.new("ShaderNodeRBRTexture"), -420, 40)
    tex.node_tree = setup_texture_node_tree(bpy.context, "water", False)
    tree.links.new(velocity.outputs["UV"], tex.inputs["UV"])
    tree.links.new(tex.outputs[0], rbr.inputs["Texture 1"])
    tree.links.new(rbr.outputs["Surface"], out.inputs["Surface"])
    return material


def switch_material():
    material, tree = new_material("Tree")
    out = output(tree, 750, 0)
    switch = place(tree.nodes.new("GeometryNodeIndexSwitch"), 520, 0)
    switch.data_type = "SHADER"
    selector = attribute(tree, "superbowl", 250, 280)
    selector.attribute_type = "INSTANCER"
    tex = texture(tree, "tree-leaves", uv_map(tree, "UVMap", -650, -100), -420, -60)
    items = [i for i in switch.inputs[1:] if i.type == "SHADER"]
    for item, (mesh_type, y) in zip(
        items, [("OBJECT_BLOCK", 120), ("SUPER_BOWL", -300)]
    ):
        rbr = shader(tree, mesh_type, 0, y)
        tree.links.new(tex.outputs[0], rbr.inputs[0])
        tree.links.new(rbr.outputs["Surface"], item)
    tree.links.new(selector.outputs["Factor"], switch.inputs[0])
    tree.links.new(switch.outputs[0], out.inputs["Surface"])
    return material


def switch_scatter(tree_object):
    ng = bpy.data.node_groups.new("Scatter Trees", "GeometryNodeTree")
    ng.is_modifier = True
    ng.interface.new_socket(
        "Geometry", in_out="INPUT", socket_type="NodeSocketGeometry"
    )
    ng.interface.new_socket(
        "Geometry", in_out="OUTPUT", socket_type="NodeSocketGeometry"
    )
    N, L = ng.nodes, ng.links
    gi = place(N.new("NodeGroupInput"), -700, 0)
    distribute = place(N.new("GeometryNodeDistributePointsOnFaces"), -480, 0)
    info = place(N.new("GeometryNodeObjectInfo"), -480, -260)
    info.inputs["Object"].default_value = tree_object
    info.inputs["As Instance"].default_value = True
    instance = place(N.new("GeometryNodeInstanceOnPoints"), -200, 0)
    position = place(N.new("GeometryNodeInputPosition"), -200, -330)
    length = place(N.new("ShaderNodeVectorMath"), 0, -300)
    length.operation = "LENGTH"
    compare = place(N.new("FunctionNodeCompare"), 200, -260, "Far away")
    compare.data_type = "FLOAT"
    compare.operation = "GREATER_THAN"
    compare.inputs["B"].default_value = 200.0
    store = place(N.new("GeometryNodeStoreNamedAttribute"), 420, 0)
    store.data_type = "BOOLEAN"
    store.domain = "INSTANCE"
    store.inputs["Name"].default_value = "superbowl"
    go = place(N.new("NodeGroupOutput"), 640, 0)
    L.new(gi.outputs[0], distribute.inputs["Mesh"])
    L.new(distribute.outputs["Points"], instance.inputs["Points"])
    L.new(info.outputs["Geometry"], instance.inputs["Instance"])
    L.new(distribute.outputs["Rotation"], instance.inputs["Rotation"])
    L.new(position.outputs[0], length.inputs[0])
    L.new(length.outputs["Value"], compare.inputs["A"])
    L.new(instance.outputs[0], store.inputs["Geometry"])
    L.new(compare.outputs["Result"], store.inputs["Value"])
    L.new(store.outputs[0], go.inputs[0])
    return ng


def mesh_object(name, material=None):
    mesh = bpy.data.meshes.new(name)
    mesh.from_pydata([(0, 0, 0), (1, 0, 0), (0, 1, 0)], [], [(0, 1, 2)])
    for layer in ["uv-1", "uv-2", "shadow-uv", "UVMap"]:
        mesh.uv_layers.new(name=layer)
    if material is not None:
        mesh.materials.append(material)
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.scene.collection.objects.link(obj)
    return obj


# (image name, editor type, node tree to show)
Shot = Tuple[str, str, bpy.types.NodeTree]


def build_shots() -> List[Shot]:
    for o in list(bpy.data.objects):
        bpy.data.objects.remove(o)
    shots: List[Shot] = []
    for name, build in [
        ("shader-geom-block", geom_block),
        ("shader-geom-block-full", geom_block_full),
        ("shader-object-block", object_block),
        ("shader-tint-set", tint_set),
        ("shader-uv-velocity", uv_velocity),
        ("switch-material", switch_material),
    ]:
        material = build()
        mesh_object(material.name, material)
        shots.append((name, "ShaderNodeTree", material.node_tree))
    tree_object = bpy.data.objects["Tree"]
    shots.append(("switch-scatter", "GeometryNodeTree", switch_scatter(tree_object)))
    return shots


# Capturing


def current():
    """The window and its largest area, looked up afresh: maximising an area
    swaps the screen, so areas held across steps go stale."""
    window = bpy.context.window_manager.windows[0]
    return window, max(window.screen.areas, key=lambda a: a.width * a.height)


def crop(captured, path):
    """Crop a capture to its nodes (below the breadcrumb, ignoring the faint
    grid dots), pad it, scale it to WIDTH and save it to path."""
    image = bpy.data.images.load(captured)
    w, h = image.size
    pixels = np.empty(w * h * 4, dtype=np.float32)
    image.pixels.foreach_get(pixels)
    rgb = pixels.reshape(h, w, 4)[..., :3]
    below_breadcrumb = int(h * 0.92)
    body = rgb[40:below_breadcrumb, 0 : w - 40]  # rows run bottom up
    content = np.abs(body - body[5, 5]).max(axis=2) > 40 / 255
    rows = np.flatnonzero(content.any(axis=1)) + 40
    cols = np.flatnonzero(content.any(axis=0))
    bottom, top = max(rows[0] - PAD, 0), min(rows[-1] + PAD, below_breadcrumb)
    left, right = max(cols[0] - PAD, 0), min(cols[-1] + PAD, w)
    cw, ch = right - left, top - bottom
    cropped = bpy.data.images.new(os.path.basename(path), cw, ch)
    cropped.pixels.foreach_set(pixels.reshape(h, w, 4)[bottom:top, left:right].ravel())
    if cw > WIDTH:
        cropped.scale(WIDTH, round(ch * WIDTH / cw))
    cropped.filepath_raw = path
    cropped.file_format = "PNG"
    cropped.save()
    bpy.data.images.remove(image)
    bpy.data.images.remove(cropped)


def capture(name):
    """Capture the maximised editor to a temporary file: its path and a hash
    of what it shows."""
    window, area = current()
    path = os.path.join(bpy.app.tempdir, f"{name}.png")
    with bpy.context.temp_override(window=window, area=area):
        bpy.ops.screen.screenshot_area(filepath=path)
    with open(path, "rb") as f:
        return path, hashlib.md5(f.read()).hexdigest()


def settle(name: str, different_from: Optional[str]) -> Iterator[float]:
    """Wait until the capture differs from different_from (if given) and two
    captures in a row match: Blender redraws on its own schedule."""
    previous = None
    for _ in range(20):
        _, current_hash = capture(name)
        if current_hash != different_from and current_hash == previous:
            return
        previous = current_hash
        current()[1].tag_redraw()
        yield 0.5
    raise TimeoutError(name)


def frame_all() -> None:
    window, area = current()
    region = next(r for r in area.regions if r.type == "WINDOW")
    with bpy.context.temp_override(window=window, area=area, region=region):
        bpy.ops.node.view_all()
    area.tag_redraw()


def shoot(shot: Shot) -> Iterator[float]:
    """Steps of one shot, each yielding how long to wait before the next."""
    name, ui_type, tree = shot
    _, before = capture(name)

    window, area = current()
    area.type = "NODE_EDITOR"
    area.ui_type = ui_type
    space = area.spaces.active
    space.show_region_ui = False
    space.show_region_toolbar = False
    # pinned, so the editor shows exactly this tree
    space.pin = True
    space.path.start(tree)
    area.tag_redraw()
    try:
        # framing uses the nodes' drawn sizes, so the tree must be drawn first
        yield from settle(name, before)
        for _ in range(2):
            frame_all()
            yield from settle(name, None)
    except TimeoutError:
        print(f"SHOT FAILED {name}: the editor never settled on the tree")
        return

    window, area = current()
    if (
        area.type != "NODE_EDITOR"
        or len(window.screen.areas) != 1
        or window.width < 1000
    ):
        print(f"SHOT FAILED {name}: editor not maximised in a large window")
        return
    if area.spaces.active.edit_tree != tree:
        print(f"SHOT FAILED {name}: editor shows another tree")
        return
    path, _ = capture(name)
    crop(path, os.path.join(OUT_DIR, f"{name}.png"))
    print("SHOT", name)


SHOTS: List[Iterator[float]] = []


def run_shots():
    while SHOTS:
        try:
            return next(SHOTS[0])
        except StopIteration:
            SHOTS.pop(0)
    bpy.ops.wm.quit_blender()
    return None


def start():
    shots = build_shots()
    window, area = current()
    with bpy.context.temp_override(window=window, area=area):
        bpy.ops.screen.screen_full_area(use_hide_panels=True)
    SHOTS.extend(shoot(shot) for shot in shots)
    bpy.app.timers.register(run_shots, first_interval=2.0)
    return None


def aerospace_windows():
    listing = subprocess.run(
        ["aerospace", "list-windows", "--all", "--format", "%{window-id} %{app-pid}"],
        capture_output=True,
        text=True,
    ).stdout.splitlines()
    pid = str(os.getpid())
    return [line.split()[0] for line in listing if line.split()[1:] == [pid]]


def fullscreen_then(then, tries=20):
    """The window registers with AeroSpace a moment after blender starts, and
    can be listed a moment before it can be acted on."""
    if shutil.which("aerospace") is None:
        then()
        return None
    ok = any(
        subprocess.run(
            ["aerospace", "fullscreen", "on", "--window-id", w, "--no-outer-gaps"],
            capture_output=True,
        ).returncode
        == 0
        for w in aerospace_windows()
    )
    if not ok and tries > 0:
        bpy.app.timers.register(
            lambda: fullscreen_then(then, tries - 1), first_interval=0.5
        )
        return None
    bpy.app.timers.register(lambda: (then(), None)[1], first_interval=1.5)
    return None


bpy.app.timers.register(lambda: fullscreen_then(start), first_interval=0.5)
