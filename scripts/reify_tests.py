"""Tests for resolving and reifying RBR materials, in headless blender (the bpy
pip module). Run via scripts/smoke.sh.

The resolver tests always run. The material tests need the native core (the
reified materials are its types), so they're skipped when it isn't built.
"""

import os
import re
import sys
import traceback
from typing import Callable, Dict, List

import bpy  # type: ignore

# importable only once bpy has set up blender's script paths
import addon_utils  # type: ignore

ADDON_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ADDON_DIR)

if addon_utils.enable("rbr_track_exporter", default_set=True, persistent=False) is None:
    sys.exit("reify tests FAILED: could not enable rbr_track_exporter")

from rbr_track_exporter.reify import (  # noqa: E402
    ReifyMaterialError,
    Upstream,
    follow,
    node_ref,
)
from rbr_track_exporter.shaders.texture import setup_texture_node_tree  # noqa: E402

TESTS: List[Callable[[], None]] = []


def test(f: Callable[[], None]) -> Callable[[], None]:
    TESTS.append(f)
    return f


SOCKET_TYPES = {
    "SHADER": "NodeSocketShader",
    "RGBA": "NodeSocketColor",
    "VALUE": "NodeSocketFloat",
    "VECTOR": "NodeSocketVector",
    "BOOLEAN": "NodeSocketBool",
}


def new_tree():
    material = bpy.data.materials.new("test")
    material.use_nodes = True
    tree = material.node_tree
    for node in list(tree.nodes):
        tree.nodes.remove(node)
    return material, tree


def consumer(tree):
    """A node with a colour input to resolve from."""
    node = tree.nodes.new("ShaderNodeMix")
    node.data_type = "RGBA"
    return node


def colour_input(node):
    return next(s for s in node.inputs if s.type == "RGBA" and s.enabled)


def new_group(name, inputs=(), outputs=()):
    """A group tree with (name, type) interface sockets and its group
    input/output nodes."""
    group = bpy.data.node_groups.new(name, "ShaderNodeTree")
    for socket_name, socket_type in inputs:
        group.interface.new_socket(
            socket_name, in_out="INPUT", socket_type=SOCKET_TYPES[socket_type]
        )
    for socket_name, socket_type in outputs:
        group.interface.new_socket(
            socket_name, in_out="OUTPUT", socket_type=SOCKET_TYPES[socket_type]
        )
    group_in = group.nodes.new("NodeGroupInput")
    group_out = group.nodes.new("NodeGroupOutput")
    return group, group_in, group_out


def group_node(tree, group):
    node = tree.nodes.new("ShaderNodeGroup")
    node.node_tree = group
    return node


def expect_error(f, message_part, node_name):
    try:
        f()
    except ReifyMaterialError as e:
        assert message_part in e.message, e.message
        assert e.node_name == node_name, (e.node_name, node_name)
        return
    raise AssertionError("no ReifyMaterialError")


# Resolver


@test
def direct_link():
    _, tree = new_tree()
    rgb = tree.nodes.new("ShaderNodeRGB")
    c = consumer(tree)
    tree.links.new(rgb.outputs[0], colour_input(c))
    assert follow(colour_input(c), (), "M") == Upstream(rgb, rgb.outputs[0], ())


@test
def unlinked_is_its_own_default():
    _, tree = new_tree()
    c = consumer(tree)
    assert follow(colour_input(c), (), "M") == colour_input(c)


@test
def reroute_chain():
    _, tree = new_tree()
    rgb = tree.nodes.new("ShaderNodeRGB")
    r1 = tree.nodes.new("NodeReroute")
    r2 = tree.nodes.new("NodeReroute")
    c = consumer(tree)
    tree.links.new(rgb.outputs[0], r1.inputs[0])
    tree.links.new(r1.outputs[0], r2.inputs[0])
    tree.links.new(r2.outputs[0], colour_input(c))
    assert follow(colour_input(c), (), "M").node == rgb


@test
def reroute_with_nothing_connected():
    _, tree = new_tree()
    r = tree.nodes.new("NodeReroute")
    c = consumer(tree)
    tree.links.new(r.outputs[0], colour_input(c))
    expect_error(lambda: follow(colour_input(c), (), "M"), "Reroute", r.name)


@test
def tint_set_picks_each_input():
    _, tree = new_tree()
    tint = tree.nodes.new("ShaderNodeRBRTintSet")
    sources = {}
    for tint_set, name in [
        ("M", "Morning"),
        ("N", "Noon"),
        ("E", "Evening"),
        ("O", "Overcast"),
    ]:
        rgb = tree.nodes.new("ShaderNodeRGB")
        tree.links.new(rgb.outputs[0], tint.inputs[name])
        sources[tint_set] = rgb
    c = consumer(tree)
    tree.links.new(tint.outputs[0], colour_input(c))
    for tint_set, rgb in sources.items():
        assert follow(colour_input(c), (), tint_set).node == rgb, tint_set


@test
def tint_set_missing_input():
    _, tree = new_tree()
    tint = tree.nodes.new("ShaderNodeRBRTintSet")
    c = consumer(tree)
    tree.links.new(tint.outputs[0], colour_input(c))
    expect_error(lambda: follow(colour_input(c), (), "N"), "Noon", tint.name)


@test
def through_a_group():
    _, tree = new_tree()
    group, gin, gout = new_group("pass", [("In", "RGBA")], [("Out", "RGBA")])
    group.links.new(gin.outputs[0], gout.inputs[0])
    g = group_node(tree, group)
    rgb = tree.nodes.new("ShaderNodeRGB")
    c = consumer(tree)
    tree.links.new(rgb.outputs[0], g.inputs[0])
    tree.links.new(g.outputs[0], colour_input(c))
    assert follow(colour_input(c), (), "M") == Upstream(rgb, rgb.outputs[0], ())


@test
def source_inside_a_group():
    _, tree = new_tree()
    group, _, gout = new_group("source", [], [("Out", "RGBA")])
    rgb = group.nodes.new("ShaderNodeRGB")
    group.links.new(rgb.outputs[0], gout.inputs[0])
    g = group_node(tree, group)
    c = consumer(tree)
    tree.links.new(g.outputs[0], colour_input(c))
    assert follow(colour_input(c), (), "M") == Upstream(rgb, rgb.outputs[0], (g,))
    assert node_ref(rgb, (g,)) == f"{g.name}\x1f{rgb.name}"


@test
def nested_groups():
    _, tree = new_tree()
    inner, _, inner_out = new_group("inner", [], [("Out", "RGBA")])
    rgb = inner.nodes.new("ShaderNodeRGB")
    inner.links.new(rgb.outputs[0], inner_out.inputs[0])
    outer, _, outer_out = new_group("outer", [], [("Out", "RGBA")])
    inner_node = group_node(outer, inner)
    outer.links.new(inner_node.outputs[0], outer_out.inputs[0])
    outer_node = group_node(tree, outer)
    c = consumer(tree)
    tree.links.new(outer_node.outputs[0], colour_input(c))
    found = follow(colour_input(c), (), "M")
    assert found == Upstream(rgb, rgb.outputs[0], (outer_node, inner_node))


@test
def unlinked_outer_input_gives_its_default():
    _, tree = new_tree()
    group, gin, gout = new_group("pass", [("In", "RGBA")], [("Out", "RGBA")])
    group.links.new(gin.outputs[0], gout.inputs[0])
    g = group_node(tree, group)
    g.inputs[0].default_value = (0.25, 0.5, 0.75, 1.0)
    c = consumer(tree)
    tree.links.new(g.outputs[0], colour_input(c))
    found = follow(colour_input(c), (), "M")
    assert found == g.inputs[0]
    assert tuple(found.default_value) == (0.25, 0.5, 0.75, 1.0)


@test
def unlinked_group_output_gives_its_default():
    _, tree = new_tree()
    group, _, gout = new_group("empty", [], [("Out", "RGBA")])
    g = group_node(tree, group)
    c = consumer(tree)
    tree.links.new(g.outputs[0], colour_input(c))
    assert follow(colour_input(c), (), "M") == gout.inputs[0]


@test
def group_used_twice_keeps_each_use_apart():
    _, tree = new_tree()
    group, gin, gout = new_group("pass", [("In", "RGBA")], [("Out", "RGBA")])
    reroute = group.nodes.new("NodeReroute")
    group.links.new(gin.outputs[0], reroute.inputs[0])
    group.links.new(reroute.outputs[0], gout.inputs[0])
    results = []
    for _ in range(2):
        g = group_node(tree, group)
        rgb = tree.nodes.new("ShaderNodeRGB")
        c = consumer(tree)
        tree.links.new(rgb.outputs[0], g.inputs[0])
        tree.links.new(g.outputs[0], colour_input(c))
        results.append((follow(colour_input(c), (), "M").node, rgb))
    for found, rgb in results:
        assert found == rgb


@test
def picks_the_matching_group_output():
    _, tree = new_tree()
    group, _, gout = new_group("two", [], [("A", "RGBA"), ("B", "RGBA")])
    a = group.nodes.new("ShaderNodeRGB")
    b = group.nodes.new("ShaderNodeRGB")
    group.links.new(a.outputs[0], gout.inputs["A"])
    group.links.new(b.outputs[0], gout.inputs["B"])
    g = group_node(tree, group)
    c = consumer(tree)
    tree.links.new(g.outputs["B"], colour_input(c))
    assert follow(colour_input(c), (), "M").node == b


@test
def group_without_output():
    _, tree = new_tree()
    group, _, gout = new_group("broken", [], [("Out", "RGBA")])
    g = group_node(tree, group)
    c = consumer(tree)
    tree.links.new(g.outputs[0], colour_input(c))
    group.nodes.remove(gout)
    expect_error(lambda: follow(colour_input(c), (), "M"), "group output", g.name)


@test
def tint_set_inside_a_group():
    _, tree = new_tree()
    group, gin, gout = new_group("tinted", [("Noon", "RGBA")], [("Out", "RGBA")])
    tint = group.nodes.new("ShaderNodeRBRTintSet")
    morning = group.nodes.new("ShaderNodeRGB")
    group.links.new(morning.outputs[0], tint.inputs["Morning"])
    group.links.new(gin.outputs[0], tint.inputs["Noon"])
    group.links.new(tint.outputs[0], gout.inputs[0])
    g = group_node(tree, group)
    noon = tree.nodes.new("ShaderNodeRGB")
    tree.links.new(noon.outputs[0], g.inputs[0])
    c = consumer(tree)
    tree.links.new(g.outputs[0], colour_input(c))
    assert follow(colour_input(c), (), "M") == Upstream(
        morning, morning.outputs[0], (g,)
    )
    assert follow(colour_input(c), (), "N") == Upstream(noon, noon.outputs[0], ())
    expect_error(
        lambda: follow(colour_input(c), (), "E"), "Evening", f"{g.name}\x1f{tint.name}"
    )


@test
def group_inside_a_tint_set():
    _, tree = new_tree()
    group, _, gout = new_group("source", [], [("Out", "RGBA")])
    rgb = group.nodes.new("ShaderNodeRGB")
    group.links.new(rgb.outputs[0], gout.inputs[0])
    g = group_node(tree, group)
    tint = tree.nodes.new("ShaderNodeRBRTintSet")
    tree.links.new(g.outputs[0], tint.inputs["Morning"])
    c = consumer(tree)
    tree.links.new(tint.outputs[0], colour_input(c))
    assert follow(colour_input(c), (), "M") == Upstream(rgb, rgb.outputs[0], (g,))


# Materials: every reified material must come out the same when its nodes are
# moved into (nested) groups, rerouted, or put behind a tint set.

TINT_SETS = ["M", "N", "E", "O"]
MESH_TYPES = [
    "GEOM_BLOCK",
    "OBJECT_BLOCK",
    "REFLECTION_OBJECT",
    "WATER_OBJECT",
    "SUPER_BOWL",
    "INTERACTIVE_OBJECT_VISUAL",
    "CLIPPING_PLANE",
]


def build_material(mesh_type):
    """An RBR material of mesh_type with every input fed: textures from RBR
    texture nodes, colours from attributes, values from value nodes."""
    material, tree = new_tree()
    output = tree.nodes.new("ShaderNodeOutputMaterial")
    shader = tree.nodes.new("ShaderNodeRBR")
    shader.mesh_type = mesh_type
    tree.links.new(shader.outputs["Surface"], output.inputs["Surface"])
    uv = tree.nodes.new("ShaderNodeUVMap")
    uv.uv_map = "uv-1"
    inputs = [s for s in shader.inputs if s.enabled]
    for i, s in enumerate(inputs):
        if s.type == "RGBA" and "Texture" in s.name and "Shadow" not in s.name:
            texture = tree.nodes.new("ShaderNodeRBRTexture")
            texture.node_tree = setup_texture_node_tree(
                bpy.context, f"{mesh_type}-{i}", False
            )
            tree.links.new(uv.outputs[0], texture.inputs["UV"])
            tree.links.new(texture.outputs[0], s)
            alpha = shader.inputs.get(f"{s.name} Alpha")
            if alpha is not None:
                tree.links.new(texture.outputs[1], alpha)
        elif s.type == "RGBA" and "Shadow" not in s.name:
            attribute = tree.nodes.new("ShaderNodeAttribute")
            attribute.attribute_name = "colour"
            tree.links.new(attribute.outputs["Color"], s)
        elif s.type == "VALUE" and "Alpha" not in s.name:
            if i % 2:
                value = tree.nodes.new("ShaderNodeValue")
                value.outputs[0].default_value = 0.1 * i
                tree.links.new(value.outputs[0], s)
            else:
                s.default_value = 0.1 * i
    return material


def reified(material) -> Dict[str, str]:
    out = {}
    for tint_set in TINT_SETS:
        try:
            out[tint_set] = repr(ffi.reify_material(material, tint_set))
        except ReifyMaterialError as e:
            out[tint_set] = f"error: {e.message} @ {e.node_name}"
    return out


def move_into_group(tree, node, name):
    """Replace node with a group node holding a copy of it, every used input
    and output routed through the group interface."""
    group = bpy.data.node_groups.new(name, "ShaderNodeTree")
    group_in = group.nodes.new("NodeGroupInput")
    group_out = group.nodes.new("NodeGroupOutput")
    inner = group.nodes.new(node.bl_idname)
    for prop in node.bl_rna.properties:
        if prop.is_readonly or prop.identifier in {
            "name",
            "location",
            "parent",
            "select",
        }:
            continue
        try:
            setattr(inner, prop.identifier, getattr(node, prop.identifier))
        except (AttributeError, TypeError, ValueError):
            pass
    outer = group_node(tree, group)
    for i, s in enumerate(node.inputs):
        if not s.enabled or s.type not in SOCKET_TYPES:
            continue
        item = group.interface.new_socket(
            s.name, in_out="INPUT", socket_type=SOCKET_TYPES[s.type]
        )
        group.links.new(
            next(o for o in group_in.outputs if o.identifier == item.identifier),
            inner.inputs[i],
        )
        outer_input = next(o for o in outer.inputs if o.identifier == item.identifier)
        if s.is_linked:
            tree.links.new(s.links[0].from_socket, outer_input)
        elif hasattr(s, "default_value"):
            outer_input.default_value = s.default_value
    for i, s in enumerate(node.outputs):
        # input nodes (value, rgb) keep their value on the output socket
        if hasattr(s, "default_value"):
            inner.outputs[i].default_value = s.default_value
        if not s.is_linked:
            continue
        item = group.interface.new_socket(
            s.name, in_out="OUTPUT", socket_type=SOCKET_TYPES[s.type]
        )
        group.links.new(
            inner.outputs[i],
            next(o for o in group_out.inputs if o.identifier == item.identifier),
        )
        outer_output = next(o for o in outer.outputs if o.identifier == item.identifier)
        for link in list(s.links):
            tree.links.new(outer_output, link.to_socket)
    tree.nodes.remove(node)
    return outer


def reroute_every_link(tree):
    for link in list(tree.links):
        reroute = tree.nodes.new("NodeReroute")
        from_socket, to_socket = link.from_socket, link.to_socket
        tree.links.remove(link)
        tree.links.new(from_socket, reroute.inputs[0])
        tree.links.new(reroute.outputs[0], to_socket)


def tint_set_every_colour_link(tree):
    for link in list(tree.links):
        if link.to_socket.type != "RGBA" or link.from_socket.type != "RGBA":
            continue
        tint = tree.nodes.new("ShaderNodeRBRTintSet")
        from_socket, to_socket = link.from_socket, link.to_socket
        tree.links.remove(link)
        for name in ["Morning", "Noon", "Evening", "Overcast"]:
            tree.links.new(from_socket, tint.inputs[name])
        tree.links.new(tint.outputs[0], to_socket)


def by_type(tree, bl_idname):
    return [n for n in tree.nodes if n.bl_idname == bl_idname]


def check_equivalent(transform: Callable[[object], None], label: str) -> None:
    for mesh_type in MESH_TYPES:
        material = build_material(mesh_type)
        before = reified(material)
        assert not any(v.startswith("error") or v == "None" for v in before.values()), (
            mesh_type,
            before,
        )
        transform(material.node_tree)
        after = reified(material)
        assert after == before, f"{label} {mesh_type}:\n  {before['M']}\n  {after['M']}"


def material_tests() -> None:
    @test
    def shader_in_nested_groups():
        def transform(tree):
            shader = by_type(tree, "ShaderNodeRBR")[0]
            move_into_group(tree, move_into_group(tree, shader, "shader"), "outer")

        check_equivalent(transform, "shader in nested groups")

    @test
    def textures_in_groups():
        def transform(tree):
            for i, texture in enumerate(by_type(tree, "ShaderNodeRBRTexture")):
                move_into_group(tree, texture, f"texture-{i}")

        check_equivalent(transform, "textures in groups")

    @test
    def everything_in_groups():
        def transform(tree):
            for kind in ["ShaderNodeAttribute", "ShaderNodeValue", "ShaderNodeUVMap"]:
                for i, node in enumerate(by_type(tree, kind)):
                    move_into_group(tree, node, f"{kind}-{i}")
            for i, texture in enumerate(by_type(tree, "ShaderNodeRBRTexture")):
                move_into_group(tree, texture, f"texture-{i}")
            shader = by_type(tree, "ShaderNodeRBR")[0]
            move_into_group(tree, shader, "shader")

        check_equivalent(transform, "everything in groups")

    @test
    def rerouted():
        check_equivalent(reroute_every_link, "rerouted")

    @test
    def behind_tint_sets():
        check_equivalent(tint_set_every_colour_link, "behind tint sets")

    @test
    def error_inside_groups_names_the_path():
        material = build_material("GEOM_BLOCK")
        tree = material.node_tree
        texture = by_type(tree, "ShaderNodeRBRTexture")[0]
        group = move_into_group(tree, texture, "texture")
        inner_texture = by_type(group.node_tree, "ShaderNodeRBRTexture")[0]
        group.node_tree.links.remove(inner_texture.inputs["UV"].links[0])
        error = reified(material)["M"]
        assert error == (
            f"error: Texture node must have a UV input @ "
            f"{group.name}\x1f{inner_texture.name}"
        ), error


def branch_group(mesh_type):
    """A group whose output is a fully fed RBR shader of mesh_type."""
    material = build_material(mesh_type)
    tree = material.node_tree
    group = bpy.data.node_groups.new(f"branch-{mesh_type}", "ShaderNodeTree")
    group.interface.new_socket(
        "Shader", in_out="OUTPUT", socket_type="NodeSocketShader"
    )
    mapping = {}
    for n in tree.nodes:
        if n.bl_idname == "ShaderNodeOutputMaterial":
            continue
        copy = group.nodes.new(n.bl_idname)
        for prop in n.bl_rna.properties:
            if prop.is_readonly or prop.identifier in {
                "name",
                "location",
                "parent",
                "select",
            }:
                continue
            try:
                setattr(copy, prop.identifier, getattr(n, prop.identifier))
            except (AttributeError, TypeError, ValueError):
                pass
        for i, sock in enumerate(n.inputs):
            if hasattr(sock, "default_value") and not sock.is_linked:
                try:
                    copy.inputs[i].default_value = sock.default_value
                except (AttributeError, TypeError, ValueError):
                    pass
        for i, sock in enumerate(n.outputs):
            if hasattr(sock, "default_value"):
                copy.outputs[i].default_value = sock.default_value
        mapping[n.name] = copy
    group_out = group.nodes.new("NodeGroupOutput")
    for link in tree.links:
        if link.to_node.bl_idname == "ShaderNodeOutputMaterial":
            group.links.new(
                mapping[link.from_node.name].outputs[link.from_socket.identifier],
                group_out.inputs[0],
            )
            continue
        group.links.new(
            mapping[link.from_node.name].outputs[link.from_socket.identifier],
            mapping[link.to_node.name].inputs[link.to_socket.identifier],
        )
    bpy.data.materials.remove(material)
    return group


def switched_material(mesh_types, index_from="INSTANCER", output="Factor"):
    """A material whose surface is an Index Switch over RBR shaders of
    mesh_types, its index from an Attribute node (unlinked if None)."""
    material, tree = new_tree()
    output_node = tree.nodes.new("ShaderNodeOutputMaterial")
    switch = tree.nodes.new("GeometryNodeIndexSwitch")
    switch.data_type = "SHADER"
    while len([i for i in switch.inputs[1:] if i.type == "SHADER"]) < len(mesh_types):
        switch.index_switch_items.new()
    items = [i for i in switch.inputs[1:] if i.type == "SHADER"]
    for mesh_type, item in zip(mesh_types, items):
        tree.links.new(group_node(tree, branch_group(mesh_type)).outputs[0], item)
    if index_from is not None:
        attribute = tree.nodes.new("ShaderNodeAttribute")
        attribute.attribute_type = index_from
        attribute.attribute_name = "branch"
        tree.links.new(attribute.outputs[output], switch.inputs[0])
    tree.links.new(switch.outputs[0], output_node.inputs["Surface"])
    return material, switch


def reify_error(material, tint_set="M"):
    try:
        ffi.reify_material(material, tint_set)
    except ReifyMaterialError as e:
        return e.message
    return None


def switch_tests() -> None:
    @test
    def switch_reifies_each_branch():
        material, _ = switched_material(["GEOM_BLOCK", "SUPER_BOWL"])
        result = ffi.reify_material(material, "M")
        text = repr(result)
        assert text.startswith("MaterialSwitch {"), text
        assert 'attribute: "branch"' in text and "from_instancer: true" in text, text
        assert "alpha: false" in text, text
        assert text.index("GeomBlockMaterial") < text.index("SuperBowl"), text
        # each branch reifies as the same shader would on its own (texture
        # trees built separately differ only in their numeric name suffix)
        unsuffixed = lambda t: re.sub(r'(RBRTextureV0\.[A-Z_]+-\d+)\.\d+"', r'\1"', t)
        for mesh_type in ["GEOM_BLOCK", "SUPER_BOWL"]:
            flat = reified(build_material(mesh_type))["M"]
            body = flat.split("{", 1)[1].rsplit("}", 1)[0].strip()
            assert unsuffixed(body) in unsuffixed(text), (mesh_type, body, text)

    @test
    def switch_by_object_attribute_alpha():
        material, _ = switched_material(
            ["GEOM_BLOCK", "OBJECT_BLOCK"], "OBJECT", "Alpha"
        )
        text = repr(ffi.reify_material(material, "M"))
        assert "from_instancer: false" in text and "alpha: true" in text, text

    @test
    def unlinked_index_picks_a_fixed_branch():
        material, switch = switched_material(["GEOM_BLOCK", "SUPER_BOWL"], None)
        switch.inputs[0].default_value = 1
        assert repr(ffi.reify_material(material, "M")).startswith(
            "SuperBowl"
        ), "branch 1"
        switch.inputs[0].default_value = 2
        assert "out of range" in (reify_error(material) or ""), reify_error(material)

    @test
    def plain_switch_errors():
        material, tree = new_tree()
        out = tree.nodes.new("ShaderNodeOutputMaterial")
        switch = tree.nodes.new("GeometryNodeSwitch")
        switch.input_type = "SHADER"
        g = group_node(tree, branch_group("GEOM_BLOCK"))
        tree.links.new(g.outputs[0], switch.inputs["True"])
        tree.links.new(switch.outputs[0], out.inputs["Surface"])
        assert "Index Switch" in (reify_error(material) or ""), reify_error(material)

    @test
    def index_must_come_from_object_or_instancer_attribute():
        material, _ = switched_material(["GEOM_BLOCK", "SUPER_BOWL"], "GEOMETRY")
        assert "Object or Instancer" in (reify_error(material) or ""), reify_error(
            material
        )
        material, switch = switched_material(["GEOM_BLOCK", "SUPER_BOWL"], None)
        value = material.node_tree.nodes.new("ShaderNodeValue")
        material.node_tree.links.new(value.outputs[0], switch.inputs[0])
        assert "Object or Instancer" in (reify_error(material) or ""), reify_error(
            material
        )

    @test
    def index_must_be_factor_or_alpha():
        material, _ = switched_material(
            ["GEOM_BLOCK", "SUPER_BOWL"], "INSTANCER", "Vector"
        )
        assert "Factor or Alpha" in (reify_error(material) or ""), reify_error(material)

    @test
    def every_branch_must_be_an_rbr_shader():
        material, switch = switched_material(["GEOM_BLOCK", "SUPER_BOWL"])
        tree = material.node_tree
        item = [i for i in switch.inputs[1:] if i.type == "SHADER"][1]
        tree.links.remove(item.links[0])
        bsdf = tree.nodes.new("ShaderNodeBsdfPrincipled")
        tree.links.new(bsdf.outputs[0], item)
        assert "RBR shader" in (reify_error(material) or ""), reify_error(material)

    @test
    def switch_inside_a_group_is_found():
        material, switch = switched_material(["GEOM_BLOCK", "SUPER_BOWL"])
        tree = material.node_tree
        output = by_type(tree, "ShaderNodeOutputMaterial")[0]
        group, gin, gout = new_group("wrap", [("In", "SHADER")], [("Out", "SHADER")])
        group.links.new(gin.outputs[0], gout.inputs[0])
        g = group_node(tree, group)
        tree.links.new(switch.outputs[0], g.inputs[0])
        tree.links.new(g.outputs[0], output.inputs["Surface"])
        assert repr(ffi.reify_material(material, "M")).startswith(
            "MaterialSwitch"
        ), "wrapped"

    @test
    def non_rbr_switch_is_not_an_rbr_material():
        material, tree = new_tree()
        out = tree.nodes.new("ShaderNodeOutputMaterial")
        switch = tree.nodes.new("GeometryNodeIndexSwitch")
        switch.data_type = "SHADER"
        bsdf = tree.nodes.new("ShaderNodeBsdfPrincipled")
        tree.links.new(bsdf.outputs[0], switch.inputs[1])
        tree.links.new(switch.outputs[0], out.inputs["Surface"])
        assert ffi.reify_material(material, "M") is None


try:
    from rbr_track_exporter import ffi  # noqa: E402
except ImportError:
    ffi = None
    print("reify tests: native core not built, skipping the material tests")
else:
    material_tests()
    switch_tests()

failures = 0
for t in TESTS:
    try:
        t()
    except Exception:
        failures += 1
        print(f"FAILED {t.__name__}")
        traceback.print_exc()
if failures:
    sys.exit(f"reify tests FAILED: {failures} of {len(TESTS)}")
print(f"reify tests passed ({len(TESTS)})")
