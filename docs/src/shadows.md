# Shadows

RBR stages carry baked shadows, either into textures or into mesh vertex
colours. The addon gives you helpers to bake them per tint set, and an
export-time pass to keep the shadow data small.

## Baking

Under **Scene Settings ▸ Tint Sets ▸ Baking Tools** there are two workflows, each
a **Prepare** + **Bake** pair. *Prepare* sets up the selection and active
targets for the **active tint set**; *Bake* runs Blender's bake with the right
settings (diffuse, direct + indirect).

- **Textures** — *Prepare* finds materials whose RBR shader takes its **shadow
  texture** from the active tint set, selects those objects, and makes the
  shadow image the active bake target. *Bake* bakes into those image textures.
- **Vertex Colors** — *Prepare* finds materials whose colour comes from a
  vertex-colour attribute for the active tint set, selects those objects and
  makes that colour layer active. *Bake* bakes into vertex colours.

Bake each tint set you support by switching the **Active Tint Set** and
repeating.

## What gets exported

Each shadow image is written as a greyscale shadow map in the tint set's
textures archive (`.rbz`), taking the brightest of each pixel's red, green and
blue. A shadow image that can't be read (for example, its file is missing) is
an export error.

## Simplifying shadows on export

Shadow maps are bulky. **Scene Settings ▸ Export Settings ▸ Simplify shadows
(experimental)** (off by default) makes the exporter deduplicate and atlas them
for each tint set. It's slower, and the result should be checked in game. With
it off, shadow maps are written unchanged.

While it's on, two thresholds appear, both as a fraction of full brightness:

- **Dedup Threshold** (default `0.08`) — how different two shadow triangles may
  be and still share one patch.
- **Gradient Threshold** (default `0.04`) — how far a shadow triangle may stray
  from a smooth gradient and still be collapsed to one.

The remaining patches are packed into atlases of at most 4096×4096; anything
beyond that spills into further atlases.

See [Exporting](./exporting.md).
