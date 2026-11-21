# Object Settings

Per-object settings live in **Properties ▸ Object ▸ RBR Object Settings**. What
you see depends on the object: a mesh, a curve, a camera, an empty, and the
objects assigned a special role in [Scene Settings](./scene-settings.md) each
show different controls.

## Special-role objects

If the active object is assigned in **Scene Settings ▸ Track Objects**, the
panel just confirms its role:

- **Car Location** — the car spawn point (an Empty). The addon sets it to an
  Arrows display with a fixed, locked scale; its world position and rotation
  are exported.
- **Brake Wall** — the boundary wall curve (see
  [Fences & Brake Walls](./objects-fences.md)).
- **Registration Zone** — an Empty. The addon gives it a Sphere display and a
  uniform scale. Its world position is exported, with the empty's display
  **Size** as the radius.
- A child of the driveline shows as the **Render Distance** helper (see
  [The Driveline](./objects-driveline.md)).

## Tint set visibility

Meshes, curves, cameras, empties and other plain objects show a **Tint Sets**
block (Morning / Noon / Evening / Overcast); the special scene objects, such as
the driveline, don't. Untick a tint set to leave the object out of that
time of day — both in the export and, when you switch the active tint set, in
the Blender viewport.

An object is only exported in a tint set if its parents are too, and an
instance only if both the instanced object and its instancer are. Hiding an
object in the viewport doesn't stop it exporting.

## Instances

Instances (collection instances, geometry-nodes instances…) are exported as
they are, and modifiers are always applied. Meshes and curves with no special
type, empties and other plain objects also have:

- **Export real instances** — the exporter runs *Make Instances Real* on this
  instancer for the export, exports the resulting copies, and removes them
  afterwards. Use it when the instanced objects need to differ via modifiers,
  since each copy evaluates its modifiers at its own position.

## By data type

- **Mesh** — shows a **Mesh Type** selector that unlocks collision, interactive
  objects, fences and water splashes. See [Mesh Types](./objects-mesh.md).
- **Curve** — a **Curve Type** selector (None or Fence), unless the curve is the
  driveline, which shows its own controls.
- **Camera** — replay camera settings. See [Replay Cameras](./objects-cameras.md).
- **Empty** — tint sets, **Export real instances**, and **Soft Collision**.

## Soft Collision

Tick **Soft Collision** on an empty to make it push the car away without a
hard collision. The empty needs a **Cube** or **Sphere** display type, which
gives the shape; the object's scale gives the size (the empty's outline matches
the exported volume at a display size of 1). Any other display type is flagged
in the panel and the empty is skipped on export with a warning.

It takes the same **Physics Properties** presets as a
[Static Shape Collision](./objects-mesh.md#static-shape-collision).
