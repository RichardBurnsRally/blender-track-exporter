#!/usr/bin/env python3
"""Add addon zips to a Blender extension repository index (index.json).

    scripts/extension-index.py --index index.json --base-url URL zip...

Each zip's entry is its blender_manifest.toml plus archive_url (URL/<zip
name>), archive_size and archive_hash, the same as Blender's
`extension server-generate`. An existing entry is replaced when it has the
same id and overlaps a new one in platforms and blender versions: Blender
installs the first compatible entry it finds, not the newest, so only one may
match any given system.
"""

import argparse
import hashlib
import json
import os
import sys
import tomllib
import zipfile


def version_tuple(version: str) -> tuple[int, ...]:
    return tuple(int(part) for part in version.split("."))


def blender_range(entry: dict) -> tuple[tuple[int, ...], tuple[int, ...] | None]:
    high = entry.get("blender_version_max")
    return version_tuple(entry["blender_version_min"]), version_tuple(high) if high else None


def ranges_overlap(a: dict, b: dict) -> bool:
    (a_low, a_high), (b_low, b_high) = blender_range(a), blender_range(b)
    return (a_high is None or b_low < a_high) and (b_high is None or a_low < b_high)


def platforms_overlap(a: dict, b: dict) -> bool:
    a_platforms, b_platforms = set(a.get("platforms", [])), set(b.get("platforms", []))
    return not a_platforms or not b_platforms or bool(a_platforms & b_platforms)


def entry_from_zip(path: str, base_url: str) -> dict:
    with zipfile.ZipFile(path) as archive:
        entry = tomllib.loads(archive.read("blender_manifest.toml").decode("utf-8"))
    entry.pop("build", None)
    with open(path, "rb") as f:
        digest = hashlib.file_digest(f, "sha256").hexdigest()
    entry["archive_url"] = base_url.rstrip("/") + "/" + os.path.basename(path)
    entry["archive_size"] = os.path.getsize(path)
    entry["archive_hash"] = "sha256:" + digest
    return entry


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--index", required=True, help="index.json to update (created if missing)")
    parser.add_argument("--base-url", required=True, help="URL the zips are downloaded from")
    parser.add_argument("zips", nargs="+")
    args = parser.parse_args()

    if os.path.exists(args.index):
        with open(args.index, encoding="utf-8") as f:
            index = json.load(f)
    else:
        index = {"version": "v1", "blocklist": [], "data": []}

    data = index["data"]
    for path in args.zips:
        new = entry_from_zip(path, args.base_url)
        replaced = [
            old for old in data
            if old["id"] == new["id"] and platforms_overlap(old, new) and ranges_overlap(old, new)
        ]
        for old in replaced:
            print(f"replacing {old['id']} {old['version']} {old.get('platforms', [])}", file=sys.stderr)
        data[:] = [entry for entry in data if not any(entry is old for old in replaced)]
        data.append(new)
        print(f"added {new['id']} {new['version']} {new.get('platforms', [])}", file=sys.stderr)

    data.sort(key=lambda entry: (entry["id"], entry.get("platforms", []), blender_range(entry)[0]))
    with open(args.index, "w", encoding="utf-8", newline="\n") as f:
        json.dump(index, f, indent=2)
        f.write("\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
