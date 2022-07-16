<title></title>
## [Home](index.md) | Download | [Guide](guide.md) | [Assets](assets.md) | [Errors](errors.md) | [GitHub](https://github.com/RichardBurnsRally/blender-track-exporter/issues)

## Installation

Just download the zip file, and install it directly in Blender's preferences
pane. You don't need to unzip it.
If you had an old version installed, you must restart blender after installing
the new version.
The addon should handle migrations between versions when you open a blend file
using an older version.

## Releases

### v0.2.5 [⭳ (zip)](https://github.com/RichardBurnsRally/blender-track-exporter/raw/master/releases/rbr-track-exporter-v0.2.5.zip)

**What's Changed**

- Exportable fences (for the `fnc` file). There's a new object type, "Fence", which allows exporting simple meshes to in-game fences. The mesh must be very simple: each vertex is the base of a pole, and the edges between the vertices define the tape or netting. A simple string of edges works best - try creating the fence as a "poly" curve, then convert it to a mesh later. You can also define a vertex colour shading layer which allows defining a multiplicative shading per fence pole. It must be a "Vertex Byte Color" type.
- Use faster convex mesh check (thanks `aesthetic_sofa`).

### v0.2.4 [⭳ (zip)](https://github.com/RichardBurnsRally/blender-track-exporter/raw/master/releases/rbr-track-exporter-v0.2.4.zip)

**What's Changed**

- Add fallback materials to the material map editor. These can be set from the "overview" mode in a given texture by pressing the `F` key. This will use the currently selected material (in the material palette panel). Note that this is _per condition_ (dry/damp/wet, new/normal/worn). For simple textures you don't even need to draw material maps now, just set the fallback material and that will be used everywhere. The fallback material is equivalent to having an infinitely large material map with the previous addon version - it's used as a last resort.
- Make convexity check for shape collision meshes and interactive objects more robust.
- Fix helicam export.

### v0.2.3 [⭳ (zip)](https://github.com/RichardBurnsRally/blender-track-exporter/raw/master/releases/rbr-track-exporter-v0.2.3.zip)

**What's Changed**

- Rework exporter cleanup to be much more robust. The exporter should never leave any extra data behind after export. Previously it would do a reasonable job cleaning up _objects_ but leave lots of duplicated meshes and materials behind. Now it should be totally reliable in cleaning up any duplicated data.
- Source object names are propagated through the exporter better. This should improve a number of error messages, which would reference objects which were duplicated (hence the names changed). Not all error messages have been switched to this yet.
- Rework interactive objects (see below)
- Add 'Instancer' object type. Objects set to this type will have the "Make instances real" operator auto applied (with 'use hierarchy'=True) before detecting other RBR object types for export. You should check that this produces the right thing before blindly exporting using this object type.
- Improve export of materials with multiple output nodes. Cycles nodes will now always be ignored.

**Interactive object rework**

- Rework interactive objects. Your file will auto migrate to the new structure, which is very similar to the old structure. The collision mesh object must still be a child of the interactive object, but the RBR object type is now "Interactive Object Collision Mesh", not "Shape Collision Mesh". The object kind is now set on the collision mesh object, not the interactive object.
- Interactive objects can now have modifiers applied upon export (there is a checkbox in the RBR object settings for this). This will cause the object mesh to be cloned for each instance of the object (and they will no longer be instanced in the RBR files). The collision meshes _do not get modifiers applied_ because there are strict limits on the counts. The kind of modifiers that will be useful here are ones which alter colour information, for example to transfer shading data from the ground mesh. If you have hundreds of objects using this setting, export will be fast if they only use a single blender material, and slow if they use more than one. This is a blender limitation, the operators to "separate by material" are slow when there are lots of objects.
- Fix a bug for resolving interactive object and shape collision mesh data by name. Now you can use interactive objects from libraries reliably.
- Enforce that scale is pre-applied before export for interactive objects and shape collision meshes. Scaling does not work properly in game.
- Check that collision meshes (shape colmesh and interactive object colmesh) are convex when exporting. They will have no collision in game if they are not.

### v0.2.2 [⭳ (zip)](https://github.com/RichardBurnsRally/blender-track-exporter/raw/master/releases/rbr-track-exporter-v0.2.2.zip)

**What's Changed**

- One tint set (morning, noon, evening, overcast) per scene. This is a big
  change to the addon, since previously we had multiple tint sets in a single
  scene. When you load up your blender file, the addon will make linked
  duplicates of your scene for each of the tint sets you were using (the ones
  which had weathers), and migrates the weathers for each one. Your original
  scene is not touched! You should verify that the newly created scenes export
  as expected before removing your old scene. This change means you can now have
  different cameras and drivelines for each tint set, and arranging those
  cameras makes sense because they each have their own timeline.
- Individual weather settings have been moved to `World`. These were previously
  all stored in the scene, but moving them to the world means that you can now
  link them between tint set scenes or files. Each weather you have has a
  `World` object associated with it, and each `Scene` links to these weathers in
  a similar way to the old weather system.
- Add support for exporting vertex colours from new style attributes
- Add support for exporting UV maps from new style attributes
- Fix infinite recursion bug for weirdly degenerate geometry in the collision
  mesh
- Add the remaining TrackSettings.ini options. These won't be visible in
  blender, they change things like shading on the car and script characters.
- Fix sky shader for blender 3.2. There was an undocumented change in the camera
  data node.

### v0.2.1 [⭳ (zip)](https://github.com/RichardBurnsRally/blender-track-exporter/raw/master/releases/rbr-track-exporter-v0.2.1.zip)

**What's Changed**

- Support RSF folder structure<br>
  The addon preferences pane now has an options for "Original" and "RSF". The
  guide has been updated to reflect this.<br>
  "RSF" stages will be automatically placed into their own folder (and will be
  immediately loadable with no tweaking of ini files).<br>
  "Original" stages will be placed into the `/Maps` directory (this is the
  behaviour of addon version v0.2.0).<br>
- Export Tracks.ini<br>
  There are new options in the export pane, e.g. stage name, author, track
  surface, etc. For non-RSF installations you will still have to copy the
  contents of `Tracks<track-id>.ini` over to the main `Tracks.ini` file, the
  same as before (and the same as the tracksettings file).
- Warn user when driveline scale is not 1, this could lead to pacenotes in the
  wrong places.
- Fix click and drag behaviour in the material map editor for blender 3.2
- Pixel perfect tweaking of material map highlighted square

### v0.2.0 [⭳ (zip)](https://github.com/RichardBurnsRally/blender-track-exporter/raw/master/releases/rbr-track-exporter-v0.2.0.zip)

The first public beta release. This is not a finished product, there are still
missing features and bugs to fix, but it's good enough to export tracks.

Requires blender version 3.1 or 3.2.
