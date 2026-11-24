"""Tests for looking up instance attributes the way Blender's shaders do, in
headless blender (the bpy pip module), against blender's own results. Run via
scripts/smoke.sh.

Each scene places every instance where its position (and instanced object)
tells us which instance it really is, so the persistent id mapping, including
blender's reassignment of duplicate ids, is checked against blender itself.
"""

import os
import sys
import traceback
from typing import Callable, List

import bpy  # type: ignore

# importable only once bpy has set up blender's script paths
import addon_utils  # type: ignore

ADDON_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ADDON_DIR)

if addon_utils.enable("rbr_track_exporter", default_set=True, persistent=False) is None:
    sys.exit("instance attribute tests FAILED: could not enable rbr_track_exporter")

from rbr_track_exporter.instance_attributes import (  # noqa: E402
    InstanceAttributes,
    UnsupportedInstanceAttribute,
)

TESTS: List[Callable[[], None]] = []


def test(f: Callable[[], None]) -> Callable[[], None]:
    TESTS.append(f)
    return f


def fresh() -> None:
    bpy.ops.wm.read_factory_settings(use_empty=True)


def mesh_object(name, link=True, offset=0.0):
    me = bpy.data.meshes.new(name)
    me.from_pydata(
        [(offset, 0, 0), (offset + 0.1, 0, 0), (offset, 0.1, 0)], [], [(0, 1, 2)]
    )
    ob = bpy.data.objects.new(name, me)
    if link:
        bpy.context.scene.collection.objects.link(ob)
    return ob


def modifier(ob, build):
    ng = bpy.data.node_groups.new(ob.name, "GeometryNodeTree")
    ng.is_modifier = True
    ng.interface.new_socket(
        "Geometry", in_out="INPUT", socket_type="NodeSocketGeometry"
    )
    ng.interface.new_socket(
        "Geometry", in_out="OUTPUT", socket_type="NodeSocketGeometry"
    )
    gi, go = ng.nodes.new("NodeGroupInput"), ng.nodes.new("NodeGroupOutput")
    ng.links.new(build(ng, gi), go.inputs[0])
    ob.modifiers.new("gn", "NODES").node_group = ng


def node(ng, kind, **inputs):
    n = ng.nodes.new(kind)
    for name, value in inputs.items():
        if hasattr(value, "is_output"):
            ng.links.new(value, n.inputs[name])
        else:
            n.inputs[name].default_value = value
    return n


def line_points(ng, count, step):
    line = node(ng, "GeometryNodeMeshLine", Count=count, Offset=(step, 0, 0))
    return node(ng, "GeometryNodeMeshToPoints", Mesh=line.outputs[0]).outputs[0]


def instance(ng, points, geometry):
    return node(
        ng, "GeometryNodeInstanceOnPoints", Points=points, Instance=geometry
    ).outputs[0]


def object_info(ng, ob):
    n = node(ng, "GeometryNodeObjectInfo", Object=ob)
    n.inputs["As Instance"].default_value = True
    return n.outputs["Geometry"]


def store(ng, geometry, name, value, data_type="FLOAT"):
    n = ng.nodes.new("GeometryNodeStoreNamedAttribute")
    n.data_type = data_type
    n.domain = "INSTANCE"
    n.inputs["Name"].default_value = name
    ng.links.new(geometry, n.inputs["Geometry"])
    if hasattr(value, "is_output"):
        ng.links.new(value, n.inputs["Value"])
    else:
        n.inputs["Value"].default_value = value
    return n.outputs[0]


def index(ng):
    return ng.nodes.new("GeometryNodeInputIndex").outputs[0]


def math(ng, operation, a, b):
    n = ng.nodes.new("ShaderNodeMath")
    n.operation = operation
    ng.links.new(a, n.inputs[0])
    n.inputs[1].default_value = b
    return n.outputs[0]


def instances_of(instancer):
    dg = bpy.context.evaluated_depsgraph_get()
    dg.update()
    out = []
    for d in dg.object_instances:
        if d.is_instance and d.parent is not None and d.parent.original == instancer:
            # the object the export's walk passes: the instanced object
            out.append(
                (
                    d.instance_object if d.instance_object is not None else d.object,
                    d.parent.original,
                    tuple(d.persistent_id),
                    bool(d.particle_system),
                    tuple(round(c, 3) for c in d.matrix_world.translation),
                    d.object.name,
                )
            )
    return dg, out


def lookups(instancer, name, use_instancer=True):
    """(translation, object name, value) for every instance of instancer."""
    dg, found = instances_of(instancer)
    attributes = InstanceAttributes(dg, [name])
    return [
        (
            t,
            object_name,
            attributes.lookup(ob, parent, pid, particles, name, use_instancer),
        )
        for ob, parent, pid, particles, t, object_name in found
    ]


# Duplicate ids: blender reassigns them; we must find the same indices.


@test
def duplicate_ids_map_to_their_instances():
    fresh()
    leaf = mesh_object("leaf", link=False)
    s = mesh_object("S")

    def build(ng, gi):
        inst = instance(ng, line_points(ng, 60, 1.0), object_info(ng, leaf))
        inst = store(ng, inst, "id", math(ng, "MODULO", index(ng), 4.0), "INT")
        return store(ng, inst, "truth", index(ng))

    modifier(s, build)
    results = lookups(s, "truth")
    assert len(results) == 60, len(results)
    for t, _, value in results:
        assert value[0] == t[0], (t, value)


@test
def negative_duplicate_ids():
    fresh()
    leaf = mesh_object("leaf", link=False)
    s = mesh_object("S")

    def build(ng, gi):
        inst = instance(ng, line_points(ng, 40, 1.0), object_info(ng, leaf))
        ids = math(ng, "SUBTRACT", math(ng, "MODULO", index(ng), 3.0), 2000000000.0)
        inst = store(ng, inst, "id", ids, "INT")
        return store(ng, inst, "truth", index(ng))

    modifier(s, build)
    for t, _, value in lookups(s, "truth"):
        assert value[0] == t[0], (t, value)


@test
def same_points_instanced_twice_and_joined():
    """Distributed points instanced as trunks and as canopies, joined: every
    id appears twice, and each half stores its own value."""
    fresh()
    trunk = mesh_object("trunk", link=False)
    canopy = mesh_object("canopy", link=False, offset=5.0)
    s = mesh_object("S")

    def build(ng, gi):
        grid = node(ng, "GeometryNodeMeshGrid", **{"Size X": 50.0, "Size Y": 50.0})
        points = node(ng, "GeometryNodeDistributePointsOnFaces", Mesh=grid.outputs[0])
        points.inputs["Density"].default_value = 0.05
        trunks = store(
            ng,
            instance(ng, points.outputs["Points"], object_info(ng, trunk)),
            "branch",
            0.0,
        )
        canopies = store(
            ng,
            instance(ng, points.outputs["Points"], object_info(ng, canopy)),
            "branch",
            1.0,
        )
        join = ng.nodes.new("GeometryNodeJoinGeometry")
        ng.links.new(canopies, join.inputs[0])
        ng.links.new(trunks, join.inputs[0])
        return join.outputs[0]

    modifier(s, build)
    results = lookups(s, "branch")
    assert len(results) > 20, len(results)
    for _, object_name, value in results:
        assert value[0] == (1.0 if object_name == "canopy" else 0.0), (
            object_name,
            value,
        )


# Nesting


@test
def nested_levels_innermost_first():
    fresh()
    leaf = mesh_object("leaf", link=False)
    s = mesh_object("S")

    def build(ng, gi):
        inner = instance(ng, line_points(ng, 3, 1.0), object_info(ng, leaf))
        inner = store(ng, inner, "inner", index(ng))
        inner = store(ng, inner, "both", math(ng, "ADD", index(ng), 1000.0))
        outer = instance(ng, line_points(ng, 4, 100.0), inner)
        outer = store(ng, outer, "outer", index(ng))
        return store(ng, outer, "both", -1.0)

    modifier(s, build)
    for name in ["outer", "inner", "both"]:
        for t, _, value in lookups(s, name):
            o, i = divmod(round(t[0]), 100)
            expected = {"outer": o, "inner": i, "both": 1000 + i}[name]
            assert value[0] == expected, (name, t, value)


@test
def into_an_instanced_object_with_its_own_instances():
    fresh()
    leaf = mesh_object("leaf", link=False)
    src = mesh_object("src")
    modifier(
        src,
        lambda ng, gi: store(
            ng,
            instance(ng, line_points(ng, 3, 1.0), object_info(ng, leaf)),
            "inner",
            index(ng),
        ),
    )
    s = mesh_object("S")
    s.location.y = 500
    modifier(
        s,
        lambda ng, gi: store(
            ng,
            instance(ng, line_points(ng, 2, 100.0), object_info(ng, src)),
            "outer",
            index(ng),
        ),
    )
    for name in ["outer", "inner"]:
        for t, object_name, value in lookups(s, name):
            if object_name != "leaf":
                continue
            o, i = divmod(round(t[0]), 100)
            assert value[0] == (o if name == "outer" else i), (name, t, value)


# Fallbacks: instancer property, then object, then object data, then 0.


@test
def falls_back_to_properties():
    fresh()
    leaf = mesh_object("leaf", link=False)
    leaf["on_object"] = 3.0
    leaf.data["on_data"] = 4
    s = mesh_object("S")
    s["on_instancer"] = True
    modifier(
        s, lambda ng, gi: instance(ng, line_points(ng, 2, 1.0), object_info(ng, leaf))
    )
    for name, expected in [
        ("on_instancer", (1.0, 1.0, 1.0, 1.0)),
        ("on_object", (3.0, 3.0, 3.0, 1.0)),
        ("on_data", (4.0, 4.0, 4.0, 1.0)),
        ("missing", (0.0, 0.0, 0.0, 0.0)),
    ]:
        for _, _, value in lookups(s, name):
            assert value == expected, (name, value)
    # the Object type only reads the object (and its data), never the instancer
    for _, _, value in lookups(s, "on_instancer", use_instancer=False):
        assert value == (0.0, 0.0, 0.0, 0.0), value


@test
def rna_paths():
    fresh()
    leaf = mesh_object("leaf", link=False)
    s = mesh_object("S")
    s.scale = (2.0, 3.0, 4.0)
    modifier(
        s, lambda ng, gi: instance(ng, line_points(ng, 1, 1.0), object_info(ng, leaf))
    )
    for _, _, value in lookups(s, "scale"):
        assert value == (2.0, 3.0, 4.0, 1.0), value
    for _, _, value in lookups(s, "name"):
        assert value == (0.0, 0.0, 0.0, 0.0), value


@test
def raw_geometry_instances_read_the_instancer_as_their_object():
    """Instances of geometry made in the node tree (no object referenced):
    blender's dupli object is the instancer, with the instanced mesh as its
    data, so the Object type reads the instancer's properties."""
    fresh()
    s = mesh_object("S")
    s["on_instancer"] = 5.0

    def build(ng, gi):
        cube = node(ng, "GeometryNodeMeshCube")
        return instance(ng, line_points(ng, 3, 1.0), cube.outputs[0])

    modifier(s, build)
    dg, found = instances_of(s)
    assert len(found) == 3, len(found)
    attributes = InstanceAttributes(dg, ["on_instancer"])
    for _, parent, pid, particles, _, _ in found:
        for d in dg.object_instances:
            if d.is_instance and tuple(d.persistent_id) == pid:
                for ob in [d.object, d.instance_object]:
                    value = attributes.lookup(
                        ob, parent, pid, particles, "on_instancer", False
                    )
                    assert value == (5.0, 5.0, 5.0, 1.0), (ob, value)
                break


# Collections


@test
def through_a_collection_reads_the_outer_level():
    fresh()
    col = bpy.data.collections.new("tree")
    col.objects.link(mesh_object("trunk", link=False))
    col.objects.link(mesh_object("crown", link=False, offset=0.5))
    s = mesh_object("S")

    def build(ng, gi):
        info = node(ng, "GeometryNodeCollectionInfo", Collection=col)
        info.inputs["Separate Children"].default_value = False
        return store(
            ng,
            instance(ng, line_points(ng, 3, 100.0), info.outputs[0]),
            "outer",
            index(ng),
        )

    modifier(s, build)
    results = lookups(s, "outer")
    assert len(results) == 6, len(results)
    for t, _, value in results:
        assert value[0] == round(t[0]) // 100, (t, value)


@test
def attribute_inside_a_collection_is_unsupported():
    fresh()
    leaf = mesh_object("leaf", link=False)
    inner = mesh_object("inner", link=False)
    modifier(
        inner,
        lambda ng, gi: store(
            ng,
            instance(ng, line_points(ng, 2, 1.0), object_info(ng, leaf)),
            "outer",
            7.0,
        ),
    )
    col = bpy.data.collections.new("holder")
    col.objects.link(inner)
    s = mesh_object("S")

    def build(ng, gi):
        info = node(ng, "GeometryNodeCollectionInfo", Collection=col)
        return store(
            ng, instance(ng, line_points(ng, 2, 100.0), info.outputs[0]), "outer", 1.0
        )

    modifier(s, build)
    try:
        lookups(s, "outer")
    except UnsupportedInstanceAttribute as e:
        assert "holder" in str(e), str(e)
        return
    raise AssertionError("no UnsupportedInstanceAttribute")


# Attribute types convert to a colour the way blender does.


@test
def attribute_types_convert_like_blender():
    for data_type, value in [
        ("FLOAT", 2.5),
        ("INT", -3),
        ("BOOLEAN", True),
        ("FLOAT2", (1.5, -2.0, 0.0)),
        ("FLOAT_VECTOR", (1.0, 2.0, 3.0)),
        ("FLOAT_COLOR", (0.25, 0.5, 0.75, 0.5)),
    ]:
        fresh()
        leaf = mesh_object("leaf", link=False)
        s = mesh_object("S")

        def build(ng, gi, data_type=data_type, value=value):
            inst = store(
                ng,
                instance(ng, line_points(ng, 1, 1.0), object_info(ng, leaf)),
                "v",
                value,
                data_type,
            )
            read = ng.nodes.new("GeometryNodeInputNamedAttribute")
            read.data_type = "FLOAT_COLOR"
            read.inputs["Name"].default_value = "v"
            return store(ng, inst, "blender", read.outputs["Attribute"], "FLOAT_COLOR")

        modifier(s, build)
        ours = lookups(s, "v")[0][2]
        theirs = lookups(s, "blender")[0][2]
        assert all(abs(a - b) < 1e-6 for a, b in zip(ours, theirs)), (
            data_type,
            ours,
            theirs,
        )


failures = 0
for t in TESTS:
    try:
        t()
    except Exception:
        failures += 1
        print(f"FAILED {t.__name__}")
        traceback.print_exc()
if failures:
    sys.exit(f"instance attribute tests FAILED: {failures} of {len(TESTS)}")
print(f"instance attribute tests passed ({len(TESTS)})")
