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
