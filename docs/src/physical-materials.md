# Physical Materials (Collision)

Physical materials decide how each patch of ground behaves: grip, the sound the
tyres make, and the particles the car kicks up. They are painted **per texture**
as **material maps** laid over the texture in the Image Editor, independent of
the visual material. Every material using a texture shares its maps.

Only collision meshes use them: Near Geom Block materials with **Generate
Collision Mesh** on (see [Materials & Shading](./materials.md)). Collision for
objects such as trees, rocks, barriers and spectators is set per object with
**Physics Properties** instead (see [Mesh Types](./objects-mesh.md)).

## Opening the editor

1. Have an **Image Editor** somewhere on screen.
2. Click **Edit Material Maps** on an **RBR Texture** node in the Shader
   Editor. Every Image Editor switches to that texture's image for the active
   surface, and the map editor takes over as a modal tool.
3. The **RBR Material Picker** panel appears in the Image Editor sidebar
   (**Tool** tab).

The editor won't edit a node that comes from a linked library — edit those in
their source file.

## The material picker

In the **RBR Material Picker** panel:

- **Material Map Transparency** — how strongly the material overlay is drawn
  over the texture, so you can see both.
- **Material Palette** — the material you paint with. Pick a category, then
  narrow it down:
  - **Road** — **Tarmac** (fine, medium, coarse or black ice; clean, sprinkled
    or covered), **Gravel** (US, fine, medium, coarse or British; shallow, deep
    or deeper), **Snow** (on gravel, on ice, or snowbank) and **Cobble**
    (cobble or sett). Most also have dry, damp or wet.
  - **Ground** — **Water**, plus **Grass**, **Rough** and **Dirt** with
    hardness or roughness and wetness.
  - **Passthrough**.

  Each material has a fixed identifying colour used in the overlay.

## Editing

The editor works in modes. The current mode is shown in the lower-left corner
of the Image Editor, and its controls in the status bar. Middle mouse pans and
zooms in every mode.

- **Overview** — shows the map regions over the texture. Click a region to move
  or resize it, right-click to create a new one, **F** to set the fallback
  material, **Esc** to exit the editor.
- **Create New Map** — drag out the new region's bounds. **Esc** goes back.
- **Move/Resize Map** — drag the region or its handles. Click an overlapping
  region to switch to it, or empty space to go back. **X** / **Y** make the
  region span and repeat across the whole texture width / height. **Delete** or **Backspace**
  removes it. **Tab** edits its materials.
- **Edit Materials** — paint the region's 16×16 grid of cells. **T** cycles
  the tool between **Paint**, **Bucket fill** and **Edit UV** (which passes
  clicks through to the Image Editor). Right-click samples the hovered cell's
  material. **C** / **V** copy and paste the whole grid, also between textures.
  **Tab** goes back to move/resize, **Esc** to overview.

Each region is a 16×16 grid of material cells covering a rectangle of the
texture, so a single texture can carry several material areas at different
resolutions. Regions may overlap.

## How faces get their material

On export, each collision triangle takes the smallest region that wholly
contains its UVs. A triangle that fits no region gets the texture's **fallback
material**, shown in the overview corner and set with **F** from the palette.
On a material with a second texture, the triangle's second material comes from
that texture's maps in the same way.

A collision mesh can use at most 256 distinct material maps (identical maps are
merged); the export reports an error beyond that.

## Conditions

Each region holds a separate grid, and each texture a separate fallback, for
every surface type (dry, damp, wet) and age (new, normal, worn). The editor
shows and paints the one for the **Active Surface** you set in
[Scene Settings](./scene-settings.md). Switch the active surface to author or
review the maps for different conditions.

A texture that isn't a **Road Surface** only uses the **New** age: its grids
follow the surface type alone, and only its New fallbacks are exported, so set
those with the active age on New.
