# Scene Settings

Found in **Properties (area) ▸ Scene ▸ RBR Scene Settings**. This is the hub for the
whole stage. It has four sections.

If the file was made with the old (pre-1.0) RBR addon, a box at the top asks
you to back the file up and **Migrate** it; exporting before that will not
work. After migrating, an **Optional migrations are available** box offers
**Choose...** (pick further migrations to run) and **Dismiss**.

## Export Settings

- **Export To** — the named export directory (your RBR `Maps` folder) to write
  into. Set these up in the addon preferences first (see
  [Installation](./installation.md)). The stage goes in a `<Track ID>-<Track
  Name>` folder inside it.
- **Track ID** — the track number (e.g. `71` for Rally School). The export
  warns if another stage in the export directory already uses the ID.
- **Track Name** — the stage's display name (e.g. `Rally School`). Required. It
  can't contain `< > : " / \ | ? *`, start or end with a space, or end with a
  dot, and every character must be in Windows-1252.
- **Author** — your name.
- **Country Code** — ISO 3166-1 alpha-2 country code (default `GB`).
- **Particles** — the particle set used in the stage, as a path relative to the
  game folder (default `Maps\ps_british`).
- **Surface** — the stage's surface category: **Tarmac**, **Gravel** or
  **Snow**.
- **Compress textures** (on by default) — compresses the textures archive
  (`.rbz`). Turning it off makes the export faster but the archive bigger.
- **Simplify shadows (experimental)** (off by default) — deduplicates and
  atlases the shadow maps on export, with **Dedup Threshold** and **Gradient
  Threshold** shown while it's on. See [Shadows](./shadows.md).
- **Export** — runs the export. See [Exporting](./exporting.md).

After an export, **Errors** and **Warnings** sub-panels appear if there were
any. Each message has a magnifier button that jumps the viewport (and shader
editor) to the object or material it refers to.

## Track Objects

Assign the scene's special objects here:

- **Driveline** — the Bézier curve the car follows. Validity problems (wrong
  scale, not a curve, not exactly one spline, not a Bézier spline) are flagged
  inline. See
  [The Driveline](./objects-driveline.md).
- **Car Location** — an Empty marking where the car spawns. Required.
- **Brake Wall** — a curve defining the invisible boundary wall. See
  [Fences & Brake Walls](./objects-fences.md).
- **Registration Zone** — an Empty.

## Track Surfaces

- **Surfaces** — tick the surface states the stage supports: **Dry**, **Damp**,
  **Wet**. At least one is required.
- **Active Surface** — the surface **type** and **age** (New / Normal / Worn)
  you are previewing. This drives what the material editor and viewport resolve
  against. See [RBR Glossary](./glossary.md).

## Tint Sets

- **Tint Sets** — tick the times of day you'll build: **Morning**, **Noon**,
  **Evening**, **Overcast**. At least one is required.
- **Active Tint Set** — the tint set you are previewing/editing. Changing it
  updates viewport lighting and hides objects not assigned to it.
- **Baking Tools** — helpers for baking shadows into textures or vertex colors
  for the active tint set. See [Shadows](./shadows.md).
- **{Tint Set} Weathers** — the list of weathers for the active tint set. Add a
  slot and assign a **World** to it; the World carries the sky/lighting.
  Selecting a slot makes its World the scene's world. Slots with no World are
  skipped on export. For the **Overcast** tint set each weather also has a
  **Time** (Morning, Noon or Evening). See [World Settings](./world-settings.md).
- **Weather Settings** — embeds the active weather's World settings inline for
  convenience.

There is also a global **Geom Block Glossiness** control (default 12, range
0–20, shown in the World ground settings) — it applies across the whole stage
rather than per weather.
