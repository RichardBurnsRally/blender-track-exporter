# The Driveline

The driveline is a single **Bézier curve** running down the racing line. Assign
it under **Scene Settings ▸ Track Objects ▸ Driveline**. When you do, the addon
fixes the curve up for you: it keeps only the longest spline, makes it a
non-cyclic 3D Bézier with Z-up twist, locks the scale to 1, and adds a
**Render Distance** helper (a circle Empty parented to the curve). While you
edit, it keeps each point's handles aligned and of equal length.

The curve's path is driven by the frame number, so scrubbing the timeline moves
the helper along the line, one frame per metre. Keyframes on the driveline and
on [replay cameras](./objects-cameras.md) use the same frames, so they are
placed by distance along the line.

The driveline must have **scale 1**, be a **curve** with a **single Bézier
spline**, and have **no modifiers**. Problems are flagged inline in the Scene
and Object panels. On export it is an error if the driveline is missing, isn't
a curve, has no spline, its spline isn't Bézier or has fewer than two points,
or it bends back more than 180° between two points (subdivide there). Only the
first spline is exported, with a warning if there are more.

Select the driveline and open **Object Properties ▸ RBR Object Settings**. It
shows three panels.

## Render Distance

How far the game draws geometry from the car along this point of the line.

- **Render Distance** — the size of the helper circle (drag in the viewport or
  edit here). Supports keyframe animation, to vary it along the line.
- **Multiplier** — scales the render distance. Only needed if Blender's 1000 m
  limit on the helper is too small for the distance you want.

## Events

The timing markers, given as distances along the line. A value of 0 leaves the
event out.

- **Start**
- **Split 1**
- **Split 2**
- **Finish**
- **End of Stage**

**Viewport Distance** controls how far away the pacenote and event labels drawn
along the line in the Blender viewport stay visible before fading out (a
display aid, not exported).

## Pacenotes

The co-driver calls.

> Pacenotes are best created with an external tool. The panel lists what is
> present and lets you tweak individual entries.

Each pacenote has a **Location** (distance along the line), a **Pacenote** id,
and **Flags**. The recognised call is shown beside each row (e.g. *Left
Hairpin*, *Right Medium*, *Over Crest*, *Jump*, plus the timing events), or
*Unknown*. Use **Add pacenote** / the remove button to manage the stack.
Pacenotes and events are also labelled along the line in the viewport.
