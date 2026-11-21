# Troubleshooting

## "rbr_blender_track_io binary is missing or failed to load"

The compiled core for your platform/Blender version isn't loaded. Check that:

- You're on **Blender 5.2.x** (a release supports exactly one minor version).
- You're on a supported platform (Windows x64, macOS arm64, Linux x64).
- You installed the release zip for your platform (which bundles the core),
  not just the Python sources.

The panels still load without the core, but export won't run.

## Export directory errors

- **"No export directory"** — **Export To** is empty or names a directory that
  is no longer in the preferences.
- **"Export directory '…' has no path set"** — give that entry a folder in the
  preferences.
- **"Export directory doesn't exist: …"** — create the folder or point the entry
  at one that exists.

See [Installation & Setup](./installation.md#setting-up-export-directories).

## Track Name errors

**Track Name** is required, and it becomes the exported folder's name, so it
can't contain `< > : " / \ | ? *`, start or end with a space, or end with a dot.
Characters the game can't show (outside Windows-1252) are errors too, and any
non-ASCII character gives a warning.

## "Track ID … is already used in the export folder"

Another folder or loose track files in the export directory use the same
**Track ID**. The game only registers one stage per ID, so change the ID or
remove the other stage.

## "Must select at least one surface type" / "...tint set"

A stage needs at least one **surface type** (Dry/Damp/Wet) and at least one
**tint set** (Morning/Noon/Evening/Overcast). Tick them in
[Scene Settings](./scene-settings.md).

## "No collision geometry"

No exported mesh has a material whose RBR Shader has **Generate Collision
Mesh** ticked, so the car would have nothing to drive on. See
[Materials & Shading](./materials.md).

## "Missing car location object"

Set an Empty as the **Car Location** under
[Scene Settings ▸ Track Objects](./scene-settings.md); it's where the car
spawns.

## Driveline errors

The driveline must be a **curve** with a **Bézier spline** of at least two
points, **scale 1**, and **no modifiers**. Only the first spline is exported;
extra splines give a warning. A segment that bends more than 180° is an error;
subdivide it. The Scene and Object panels flag most problems before you export.
See [The Driveline](./objects-driveline.md).

## "Must have an image editor on screen" (material maps)

The physical-material editor runs inside an Image Editor. Open one before
clicking **Edit Material Maps**. It also refuses to edit nodes from a linked
library — edit those in their source file. See
[Physical Materials](./physical-materials.md).

## "This file was made with the old RBR addon"

Export won't work until the file is migrated. Back it up and click **Migrate**
in the scene panel. See
[Installation & Setup](./installation.md#files-made-with-the-old-addon).

## "Texture node is missing its address sockets; refresh the RBR shaders"

The file's RBR node trees are older than the addon. Run **Recreate RBR node
trees**, which rebuilds them from the installed addon. It isn't in a menu, so
first turn on **Developer Extras** (**Edit ▸ Preferences ▸ Interface**), then
find it with **Edit ▸ Operator Search**; plain F3 search only lists operators
that are in menus.

## Tracking down an export message

Use the **magnifier** button next to any error/warning in the Export Settings
panels — it jumps straight to the object (and shader node) the message is
about. See [Exporting](./exporting.md).

## Camera settings are greyed out

Replay-camera controls are disabled until the **Driveline** is set in
[Scene Settings](./scene-settings.md), because they're defined relative to it.

## Terrain looks too bright or too dark

Use the **Track Settings ▸ Ground ▸ Balance** meter in the
[World settings](./world-settings.md); aim for a value near 1.0, with **Auto
Balance** on to set the reflectance multiplier for you.
