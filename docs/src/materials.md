# Materials & Shading

The addon ships custom **RBR shader nodes** so that material previews in
Blender almost exactly match in-game rendering, while also carrying the extra
data the export needs.

## RBR shader nodes

In the Shader Editor, the **Add** menu has an **RBR Nodes** submenu:

- **RBR Shader** — the main node for a surface. Its **Surface** output must
  reach the material's EEVEE output (a Material Output targeting EEVEE or All).
  Materials that don't are treated as ordinary Blender materials, and faces
  using them aren't exported. **Type** picks the geometry type: Geom Block,
  Object Block, Reflection Object, Water Object, Super Bowl, Interactive Object
  Visual or Clipping Plane. Each type has its own inputs.
- **RBR Tint Set** — routes a different input per tint set (**Morning**,
  **Noon**, **Evening**, **Overcast**). You can use this at any level, for
  textures, colours or values, because tint sets are entirely separate stages.
  Every tint set you export needs its input connected.
- **RBR Texture** — the texture node for the shader's texture inputs (diffuse
  and specular). Also holds [physical material maps](./physical-materials.md).
- **UV Velocity** — scrolls a texture's UVs over time for UV animation. Put it
  between a UV Map (or Attribute) node and an RBR Texture's **UV** input and set
  **UV Velocity**; leave that socket unconnected. Exported for Geom Block,
  Reflection Object, Water Object, Super Bowl and Interactive Object Visual.
- **RBR Sky** — used on the World, wired up automatically when you set up a
  weather (see [World Settings](./world-settings.md)). Allows previewing sky
  and cloud settings directly.

Colour and value inputs on the RBR Shader take an Attribute node (type
**Geometry**), an RGB or Value node, or nothing (the socket value is used).
Reroutes are followed. A Geom Block's **Shadow Texture** takes a plain Image
Texture node.

### Geometry type options

- **Geom Block** — **Geom Block Type** is **Near**, **Far** or **Any**. A Near
  geom block can **Generate Collision Mesh** (the ground the car drives on), and
  then optionally be **Collision Mesh Only**, which skips the visual geometry.
  Collision meshes get a **Collision Shading** input (default 0.5) that is
  written per vertex into the collision mesh.
- **Object Block** — **Object Block Type** is **Near**, **Far** or **Both**.

For every type except Geom Block and Clipping Plane, the material's **Backface
Culling** setting is exported: turn it off for double-sided faces.

## RBR Texture node

The top row picks the texture: browse existing textures, rename it, see how
many materials share it (click the number to make a single-user copy), or
unlink it. Below that:

- **Format** — the DXT compression used on export: **DXT1 (opaque)** (the
  default), **DXT1 (1-bit alpha)**, **DXT3 (sharp alpha)** or **DXT5 (smooth
  alpha)**. The viewport previews alpha the way the chosen format will store it.
- **Mipmap Levels** — 0 generates a full chain down to 1×1.
- **Road Surface (diffuse only)** — off, the texture has a **Dry**, **Damp** and
  **Wet** image. On, it has one per surface type and age (**Dry/New** …
  **Wet/Worn**), for textures that should change as the track wears.
- A **Suggested size** warning appears when an image isn't a power of two.
- **Mirror** / **Clamp** **U** / **V** — texture addressing instead of repeat.
  Only shown when the texture feeds an Object Block, Super Bowl or Interactive
  Object Visual shader. A second texture must use the same settings as the
  first.
- **Edit Material Maps** — opens the
  [physical material editor](./physical-materials.md).

On export, textures whose images and settings are identical are written once.
An image whose file is missing is reported as an error. The texture name
`rbr_blend_guard` is reserved.

## Previewing conditions

The active tint set and surface drive what these nodes display, so switching
**Active Tint Set** or **Active Surface** in
[Scene Settings](./scene-settings.md) updates the preview.

## Surface (collision) materials

Visual materials are separate from the **physical** materials that determine
grip, sound and the particles the car throws up. Those are painted per texture
with the material-map editor — see
[Physical Materials (Collision)](./physical-materials.md).
