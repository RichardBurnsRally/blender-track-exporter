# Exporting

Export writes your scene to RBR's native track files in the chosen directory.

## Running an export

Either:

- **Scene Properties ▸ RBR Scene Settings ▸ Export Settings ▸ Export**, or
- **File ▸ Export ▸ RBR Track (.trk, .lbs, ...)**.

Before it will run you need to set **Export To** to one of the directories
registered in the [preferences](./installation.md#setting-up-export-directories),
and that directory must exist on disk.

Export always uses the evaluated scene, so modifiers are applied. Objects
hidden in the viewport are still exported; to leave an object out, put it in a
collection that is excluded from the view layer. Export also sets the scene's
colour management view transform to **Standard**.

## Options

These sit above the **Export** button in Export Settings:

- **Compress textures** (on by default) — turn off for a faster export and a
  bigger textures archive. See [Scene Settings](./scene-settings.md).
- **Simplify shadows (experimental)** (off by default) — makes the stage
  smaller at the cost of a slower export. See [Shadows](./shadows.md).

## What gets written

Export creates a folder named `<Track ID>-<Track Name>` in the export
directory, and writes into it:

- `Tracks<ID>.ini`, `TrackSettings<ID>.ini` and `TextureFilenameMap<ID>.ini`.
- For each enabled tint set, `track-<ID>_<M|N|E|O>` with the extensions `.trk`,
  `.dls`, `.fnc`, `.lbs`, `.col`, `.mat` and `.ini`, plus the textures archive
  `track-<ID>_<M|N|E|O>_textures.rbz`.
- A `CustomData` folder, only if fences use custom textures.

Re-exporting overwrites these files.

## Errors and warnings

The result is reported in the status bar, and any messages are collected into
**Errors** and **Warnings** sub-panels under Export Settings (they only appear
when there is something to show):

- **Errors** mean the export failed — fix them and re-export.
- **Warnings** are non-fatal; the export still completes.

Each message has a **magnifier** button. Clicking it jumps the viewport to the
offending object (selecting it and framing it) and, where relevant, selects the
faces, vertices or curve points involved, the material, and the specific shader
node in the Shader Editor. If the object only exists as an instance, it jumps
to the instancer instead. This is the fastest way to track down what a message
refers to.

After a clean export, load the track in-game to test it.

If you come across a case where the exported stage causes the game to crash,
please report it.
