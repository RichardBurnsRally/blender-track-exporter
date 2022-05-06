<title></title>
## [Home](index.md) | Download | [Guide](guide.md) | [Errors](errors.md) | [GitHub](https://github.com/RichardBurnsRally/blender-track-exporter/issues)

## Installation

Just download the zip file, and install it directly in Blender's preferences
pane. You don't need to unzip it.
If you had an old version installed, you must restart blender after installing
the new version.
The addon should handle migrations between versions when you open a blend file
using an older version.

## Releases

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
