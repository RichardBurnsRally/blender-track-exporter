"""Patch fake-bpy-module stubs in place to fix bugs/gaps that block valid bpy code.

fake-bpy's generated stubs have defects; correcting them here (rather than
casting or ignoring at call sites) keeps type checking honest. Idempotent.
Run against the stub dir by scripts/ensure-venv.sh.

Fixups:
- Collection subclasses list a redundant bpy_prop base before their own
  bpy_prop_collection parent, breaking MRO so node.inputs[...] etc. don't type.
- bpy_struct lacks __contains__, so `"key" in struct` (valid ID-property
  access) fails.
- module_bl_info is typed as returning None though it returns the bl_info dict.
- operator idname()/idname_py() are instance methods, but operators are accessed
  via the class (bpy.ops.x.y.idname()); making them classmethods type-checks both.
- NodeSocket.links is typed Optional though it always returns a (possibly empty)
  sequence, so socket.links[0] / len(socket.links) wrongly need a None check.
- bpy_prop_array is a sequence at runtime but declares no __iter__/__getitem__/
  __len__, so iterating/unpacking/len-ing one fails.
- mathutils float vectors are iterable but the stub only declares __getitem__.
- the addon registers custom properties on stock types (Scene.rbr_scene_settings
  etc.); declared as Any so accessing them resolves.
- bpy_prop_collection (CollectionProperty) supports add/remove/clear/move.
- OffScreenStackContext is a context manager but lacks __enter__/__exit__.
- Image.pixels is typed float though it is a bpy_prop_array[float].
"""

import pathlib
import re
import sys

root = pathlib.Path(sys.argv[1])

GETITEM = "    def __getitem__(self, key: int | str) -> typing.Any:"
CONTAINS = "    def __contains__(self, key: str) -> bool: ..."

CUSTOM_PROPS = {
    "Scene": ["rbr_scene_settings", "rbr_addon_version"],
    "Object": ["rbr_object_settings"],
    "World": ["rbr_world_settings"],
    "Curve": ["rbr_curve_settings"],
    "Mesh": ["rbr_mesh_settings"],
    "Camera": ["rbr_camera_settings"],
    "Context": ["rbr_export_message"],
    "WindowManager": ["rbr_material_map_texture", "rbr_material_map_region"],
}

SOCKET_VALUE_ATTRS = {
    "NodeSocket": ["default_value"],
    "NodeTreeInterfaceSocket": [
        "default_value",
        "min_value",
        "max_value",
        "subtype",
    ],
}

total = 0
for pyi in root.rglob("*.pyi"):
    text = pyi.read_text(encoding="utf-8")
    new = text

    new, n = re.subn(r"\(\s*bpy_prop,\s*(bpy_prop_collection\[)", r"(\1", new)
    total += n

    if CONTAINS not in new and GETITEM in new:
        new = new.replace(GETITEM, f"{CONTAINS}\n{GETITEM}", 1)
        total += 1

    new, n = re.subn(
        r"(def module_bl_info\(mod, \*, info_basis=None\) -> )None:", r"\1dict:", new
    )
    total += n

    new, n = re.subn(r"(    def links\(self\) -> NodeLinks) \| None:", r"\1:", new)
    total += n

    new, n = re.subn(
        r"(    def get\[_GenericType2\]\(\n"
        r"        self, key: str \| tuple\[str, str \| None\], default: _GenericType2 = None\n"
        r"    \) -> )_GenericType2 \| None:",
        r"\1_GenericType1 | _GenericType2:",
        new,
    )
    total += n

    new, n = re.subn(
        r"(    def (?:from_node|to_node)\(self\) -> Node) \| None:", r"\1:", new
    )
    total += n
    new, n = re.subn(
        r"(    def (?:from_socket|to_socket)\(self\) -> NodeSocket) \| None:",
        r"\1:",
        new,
    )
    total += n

    new, n = re.subn(r"(    def layout\(self\) -> UILayout) \| None:", r"\1:", new)
    total += n

    new, n = re.subn(
        r"(    def interface\(self\) -> NodeTreeInterface) \| None:", r"\1:", new
    )
    total += n

    new, n = re.subn(
        r"cursor: typing\.Literal\[bpy\.stub_internal\.rna_enums\.WindowCursorItems\]"
        r" \| None",
        "cursor: str | None",
        new,
    )
    total += n
    new, n = re.subn(
        r"(def blend_set\(\s*)mode: typing\.Literal\[[^\]]*\]",
        r"\1mode: str",
        new,
    )
    total += n

    new, n = re.subn(
        r"value: collections\.abc\.Sequence\[float\] \| float\n",
        "value: collections.abc.Sequence[float] | float | mathutils.Matrix\n",
        new,
    )
    total += n

    new, n = re.subn(
        r"set\[typing\.Literal\[bpy\.stub_internal\.rna_enums\.WmReportItems\]\] \| None",
        "set[str] | None",
        new,
    )
    total += n

    new, n = re.subn(
        r"    def remove\(self, item: _GenericType1\) -> None: \.\.\.",
        "    def remove(self, index: int) -> None: ...",
        new,
    )
    total += n

    tri_strip = '        "TRI_STRIP",\n        "LINES_ADJ",'
    if tri_strip in new:
        new = new.replace(
            tri_strip,
            '        "TRI_STRIP",\n        "TRI_FAN",\n        "LINES_ADJ",',
            1,
        )
        total += 1

    vec_init = (
        "def __init__(self, seq: collections.abc.Sequence[float]"
        " = (0.0, 0.0, 0.0)) -> None:"
    )
    if vec_init in new:
        new = new.replace(vec_init, vec_init.replace("Sequence", "Iterable"), 1)
        total += 1

    new, n = re.subn(
        r'socket_type: typing\.Literal\["DEFAULT"\] \| None = "DEFAULT",',
        'socket_type: str = "DEFAULT",',
        new,
    )
    total += n

    for op_method in ("idname", "idname_py"):
        needle = f"    def {op_method}(self) -> str:"
        if needle in new:
            new = new.replace(
                needle, f"    @classmethod\n    def {op_method}(cls) -> str:"
            )
            total += 1

    bpa_doc = '    """built-in class used for array properties."""'
    bpa_iter = "    def __iter__(self) -> typing.Iterator[typing.Any]: ..."
    bpa_getitem = "    def __getitem__(self, key: int) -> typing.Any: ..."
    if bpa_iter not in new and bpa_doc in new:
        methods = f"{bpa_getitem}\n{bpa_iter}\n    def __len__(self) -> int: ..."
        new = new.replace(bpa_doc, f"{bpa_doc}\n{methods}", 1)
        total += 1

    bpa_setitem = (
        "    def __setitem__(self, key: int | slice, value: typing.Any) -> None: ..."
    )
    anchor = f"{bpa_doc}\n{bpa_getitem}"
    if bpa_setitem not in new and anchor in new:
        new = new.replace(anchor, f"{anchor}\n{bpa_setitem}", 1)
        total += 1

    vec_iter = "    def __iter__(self) -> typing.Iterator[float]: ..."
    if vec_iter not in new:
        new, n = re.subn(
            r"(    def __getitem__\(self, key: int\) -> float:)",
            f"{vec_iter}\n" + r"\1",
            new,
        )
        total += n

    for cls, props in CUSTOM_PROPS.items():
        if f"\n    {props[0]}: typing.Any" in new:
            continue
        decls = "".join(f"    {p}: typing.Any\n" for p in props)
        new, n = re.subn(
            rf"^(class {cls}\([^\n]*\):\n)", r"\1" + decls, new, count=1, flags=re.M
        )
        total += n

    for cls, attrs in SOCKET_VALUE_ATTRS.items():
        decls = "".join(f"    {a}: typing.Any\n" for a in attrs)
        m = re.search(rf"^class {cls}\([^\n]*\):\n", new, flags=re.M)
        if m and new[m.end() : m.end() + len(decls)] != decls:
            new = new[: m.end()] + decls + new[m.end() :]
            total += 1

    coll_doc = '    """built-in class used for all collections."""'
    coll_add = "    def add(self) -> _GenericType1: ..."
    if coll_add not in new and coll_doc in new:
        methods = (
            f"{coll_add}\n"
            "    def remove(self, index: int) -> None: ...\n"
            "    def clear(self) -> None: ...\n"
            "    def move(self, from_index: int, to_index: int) -> None: ..."
        )
        new = new.replace(coll_doc, f"{coll_doc}\n{methods}", 1)
        total += 1

    new, n = re.subn(
        r"^    pixels: float$", "    pixels: bpy_prop_array[float]", new, flags=re.M
    )
    total += n

    enter = "    def __enter__(self) -> typing.Any: ..."
    if "class OffScreenStackContext" in new and enter not in new:
        new, n = re.subn(
            r"^(class OffScreenStackContext[^\n]*:\n)",
            r"\1    def __enter__(self) -> typing.Any: ...\n"
            r"    def __exit__(self, *args: object) -> None: ...\n",
            new,
            count=1,
            flags=re.M,
        )
        total += n

    if "class Menu(" in new and "class NODE_MT_shader_node_add_all" not in new:
        new += "\n\nclass NODE_MT_shader_node_add_all(Menu, bpy_struct): ...\n"
        total += 1

    if new != text:
        pyi.write_text(new, encoding="utf-8")

print(f"patched {total} stub fixups under {root}")
