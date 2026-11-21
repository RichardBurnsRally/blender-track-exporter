# Replay Cameras

A Camera object exports as a replay camera. Its controls are in **Object
Properties ▸ RBR Object Settings**.

> The **Driveline** must be set in [Scene Settings](./scene-settings.md) first —
> camera controls are disabled until it is, because "look at car" and
> spline-following are defined relative to the driveline.

The camera's world position (or its spline, see **Follow Spline**) and its
world rotation without constraints are exported. **Lens** / **Field of View**
and the **Follow Spline** offset **support keyframe animation**, so a camera can zoom and travel along its spline over the course
of a replay. Frames are metres along the [driveline](./objects-driveline.md).
Other animation, such as keyframed location, isn't exported.

## Controls

- **Lens** / **Field of View** — standard Blender camera framing.
- **Clip Start** — near clip distance.
- **Look at Car** — the camera tracks the car. Enabling it adds a *Track To*
  constraint aimed at the driveline's render-distance helper; disabling it
  removes the camera's *Track To* constraints.
- **Play Helicam Sound** — plays the helicopter sound for this camera.
- **Camera Shake** — how much the camera shakes (higher = more). Shown when
  *Look at Car* is on, and not visible in Blender.
- **Follow Spline** — make the camera ride along a curve. When set, the camera's
  location is reset and locked, it is pinned to the path via a *Follow Path*
  constraint, and an **Offset** slider appears to position it along the spline
  (also keyframeable). The curve's spline with the most points is exported.

With *Look at Car* off, a *Track To* constraint you add yourself makes the
camera look at its target object instead.

## Camera switches

Which camera is live where comes from the timeline markers. Bind a camera to a
marker (Blender's *Bind Camera to Markers*) and that camera takes over at the
marker's frame, i.e. that many metres along the driveline. A marker with no
camera ends the current camera's section; the last camera runs to the end of the
driveline.
