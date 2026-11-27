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
   Editor. Every Image Editor switches to its **View** mode and shows that
   texture's image for the active condition, with the toolbar and sidebar
   open, and the **Paint Materials** tool becomes active.

The texture stays the one being edited until you click **Edit Material Maps**
on another. The overlay and panels show whenever one of the material map tools
is active; **Esc** or picking any other tool gets back to the plain image.

The editor won't edit a node that comes from a linked library — edit those in
their source file.

## Tools

The material map tools sit in the Image Editor's toolbar (**T**), after the
built-in tools:

- **Paint Materials** — click or drag to paint the active material into
  cells.
- **Fill Materials** — click to fill the connected cells of the same
  material.
- **Sample Material** — click a cell to paint with its material, or empty
  space for the fallback material.
- **Material Map Regions** — click a region to select it, drag it or its
  handles to move or resize it, or drag on empty space to add one. Clicking
  where regions overlap cycles through them. **Delete** or **Backspace**
  removes the selected region.

**Shift+Space** then **P**, **F**, **S** or **R** picks Paint, Fill, Sample or
Regions. Middle mouse pans and zooms as usual, and every change can be undone.
The keys can be changed in **Preferences ▸ Keymap**, under **Image Editor
Tool: View, Paint Materials** and the like, and **Toolbar Popup** for the
Shift+Space letters.

Paint and fill work on the selected region where it's under the cursor, and
otherwise on the topmost region there, which they then select. The selected
region shows its cell grid; the hovered cell is highlighted with its material
named next to it.

Each region is a 16×16 grid of material cells covering a rectangle of the
texture, so a single texture can carry several material areas at different
resolutions. Regions may overlap.

## Tool settings

The **Active Tool** panel in the sidebar (**Tool** tab) holds the tool's
settings:

- **Overlay Opacity** — how strongly the material overlay is drawn over the
  texture, so you can see both.
- **Material** (painting tools) — the material you paint with. Pick a
  category, then narrow it down:
  - **Road** — **Tarmac** (fine, medium, coarse or black ice; clean, sprinkled
    or covered), **Gravel** (US, fine, medium, coarse or British; shallow, deep
    or deeper), **Snow** (on gravel, on ice, or snowbank) and **Cobble**
    (cobble or sett). Most also have dry, damp or wet.
  - **Ground** — **Water**, plus **Grass**, **Rough** and **Dirt** with
    hardness or roughness and wetness.
  - **Passthrough**.

  Each material has a fixed identifying colour used in the overlay.
- **Repeat** **X** / **Y** and **Delete Region** (regions tool) — make the
  selected region span and repeat across the whole texture width / height, or
  remove it.

Below it, the **RBR Material Maps** panel shows the texture being edited, and:

- **Set Fallback** — sets the shown condition's fallback material, named
  beside it, to the active material.
- A grid of the texture's conditions: a row per age (only **New** for a texture
  that isn't a road surface) and a column per surface type.
  - The eye shows and paints that condition. It sets the same **Active
    Surface** as [Scene Settings](./scene-settings.md), and works for surfaces
    the stage doesn't export too. A warning sign in place of the eye means one
    of the condition's region cells or its fallback is still undefined.
  - The link makes a damp or wet condition automatic from dry (see
    [Automatic damp and wet](#automatic-damp-and-wet)). Drag across the
    buttons to switch several at once.
- **Region** **Copy** / **Paste** — copy the selected region's whole grid for
  the shown condition, and paste it into another region, also on another
  texture.

## How faces get their material

On export, each collision triangle takes the smallest region that wholly
contains its UVs. A triangle that fits no region gets the texture's **fallback
material**, shown and set in the **RBR Material Maps** panel.
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
and fallbacks follow the surface type alone, whatever the active age.

## Automatic damp and wet

A damp or wet condition can be **automatic**: its maps and fallback are kept
in step with the dry condition of the same age, with every material made one
step wetter for damp and two for wet, stopping at wet. Dry gravel becomes damp
gravel in the damp maps and wet gravel in the wet maps; a damp material painted
into the dry maps is wet in both. Materials without a wetness, such as rocks,
water or undefined cells, are copied as they are.

New textures start with every damp and wet condition automatic. Textures from
imported tracks, migrated files and earlier versions of the addon start
manual. Switch conditions with the links in the **RBR Material Maps** panel;
switching one on
replaces its maps and fallback with ones derived from dry.

An automatic condition can't be painted, filled, pasted into or given a
fallback; switch it off first. The **RBR Material Maps** panel says when the
shown condition is automatic. Normal and worn are never derived from new:
paint them yourself (copy and paste helps), and their damp and wet follow them.

