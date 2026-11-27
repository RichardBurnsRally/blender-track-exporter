# Quick Start

This walks through the smallest stage that will load and drive in-game. It
assumes the addon is installed and you have registered an export directory (see
[Installation & Setup](./installation.md)).

All RBR settings live in the **Properties editor**, under the Scene, World and
Object tabs, and in the RBR nodes of the Shader Editor.

## 1. Set the stage metadata

In **Scene Properties ▸ RBR Scene Settings ▸ Export Settings**:

- **Export To** — choose the directory you registered.
- **Track ID** — the track number (e.g. `71` for Rally School).
- **Track Name** — required; it also names the exported folder.
- **Author**, **Country Code** — descriptive metadata.
- **Particles** — the particle set, relative to the game folder (defaults to
  `Maps\ps_british`).
- **Surface** — the stage's surface category: Tarmac, Gravel or Snow.

## 2. Choose conditions and tint sets

Still in Scene Settings:

- **Track Surfaces** — tick which surfaces the stage supports (**Dry**,
  **Damp**, **Wet**); at least one is required. **Active Surface** picks the
  surface and age you preview in the viewport.
- **Tint Sets** — tick the times of day you'll build lighting for (**Morning**,
  **Noon**, **Evening**, **Overcast**); at least one is required. **Active Tint
  Set** picks the one you preview.

See [RBR Glossary](./glossary.md) for what these mean.

## 3. Add a weather

Under **Tint Sets ▸ {tint set} Weathers**, click **+** to add a weather slot and
assign a World to it. The World's **RBR World Settings** hold the sky, fog and
lighting for that condition — see [World Settings](./world-settings.md).

## 4. Build the road and the driveline

- Model the road and scenery as ordinary meshes, and give them materials built
  from an **RBR Shader** node (Geom Block type) with an **RBR Texture** — see
  [Materials & Shading](./materials.md). Faces without an RBR material are not
  exported.
- On the road's RBR Shader, tick **Generate Collision Mesh** so the car has
  ground to drive on. Export fails without any collision geometry.
- Add a **Bézier curve** running down the centre of the road, then set it as
  the **Driveline** under **Scene Settings ▸ Track Objects**. The addon fixes up
  the curve (single spline, 3D, Z-up, scale 1) and adds a render-distance
  helper.
- Select the driveline and open **Object Properties ▸ RBR Object Settings** to
  set the timing **Events** (Start, Finish, …) and **Pacenotes**. See
  [The Driveline](./objects-driveline.md).

## 5. Place the car start

Add an **Empty** and assign it as the **Car Location** under **Track Objects**.
This is where the car spawns; the export fails without one.

## 6. Paint surface materials

Open an **Image Editor**, then click **Edit Material Maps** on the road's RBR
Texture node to paint the
[physical (collision) material maps](./physical-materials.md) that decide grip
and particles per surface region with the **Paint Materials** tool. Pick the
material in the Image Editor sidebar's **Active Tool** panel.

## 7. Export

Click **Export** in **Scene Settings ▸ Export Settings** (or use **File ▸
Export ▸ RBR Track (.trk, .lbs, ...)**). Any problems appear in the **Errors**
and **Warnings** panels; click the magnifier beside a message to jump straight
to the offending object or material. See [Exporting](./exporting.md).

Load the track in-game to test it.
