# Fences & Brake Walls

## Fences

A fence is an interactive tape/net/wire barrier generated along a mesh or curve
by a geometry-nodes modifier. Turn an object into a fence by setting its **Mesh
Type** to **Fence** (for meshes) or **Curve Type** to **Fence** (for curves) in
**Object Properties ▸ RBR Object Settings**. The addon adds and manages the
fence modifier automatically, and re-adds it if you delete it from a fence
mesh. The geometry it generates is a viewport preview; the export writes the
fence from its posts and settings.

Posts sit on the line's points:

- **Mesh** — the vertices after the object's other modifiers (such as a
  Shrinkwrap onto the terrain), joined by edges into open chains. Each chain is
  its own fence. Branches or stray vertices skip the whole mesh with a warning, and
  closed loops are skipped with a warning.
- **Curve** — each spline's control points. Each spline is its own fence;
  cyclic splines are skipped with a warning. Other modifiers on a curve fence
  aren't exported, and the export warns about them.

A fence needs at least two posts.

Controls:

- **Fence Kind** — **Tape**, **Net** or **Barbed Wire**.
- **Vertex Color** — the colour applied along the fence, per post. You can drive
  it from a mesh colour attribute instead of a flat colour using the toggle
  beside it (new fence meshes use a `vcol` attribute if they have one).
- **Tile Texture** — the texture for the fence's spanning material.
- **Pole Texture** — the texture for the posts.
- **Subdivide** — higher resolution fence, used for rendering and collisions.

Each texture is either **Built-in** — a texture from the game's `fence.dat`,
picked from the ones offered for the current Fence Kind — or **Custom**, an
image shipped with the stage. Custom images are written as DDS files to the
stage's `CustomData/Textures` folder, named after the image with characters
other than letters, digits and `-` replaced by `_`. It is an export error if two
custom images would get the same file name, or one would replace a built-in
texture another fence uses. A fence with no tile or pole texture is skipped
with a warning.

## Brake Walls

The brake wall is the invisible boundary that stops the car leaving the stage.
Assign a **curve** as the **Brake Wall** under **Scene Settings ▸ Track
Objects**. On assignment the addon fixes the curve up (keeps the longest spline,
makes it a **cyclic poly** spline, 3D, Z-up, scale locked to 1) and replaces the
object's modifiers and materials with the brake-wall geometry-nodes modifier
and material. While you edit, it keeps the points at Z = 0.

Selecting the brake-wall object shows a simple confirmation in its Object
panel; shape the curve itself. Each point is paired with a second one, offset
sideways by the point's **Radius** and turned by its **Tilt**; the viewport
geometry shows the result.

**Respawn Areas** — a collection input on the brake-wall modifier. Wall
segments whose middle lies inside one of the collection's objects (a cube of the
object's empty display size, as transformed by the object) are flagged as
auto-respawn.

On export, the brake wall needs at least three points, no two neighbouring
points in the same place, and no point where it turns straight back on itself;
it may have at most 8191 points. Breaking these is an export error. A wall that
isn't a single poly spline is skipped (or only its first spline exported) with
a warning.
