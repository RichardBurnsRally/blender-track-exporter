# Installation & Setup

## Requirements

- **Blender** — the exact version depends on the extension version (see below).
- A copy of **RallySimFans RBR** to export your stages into.

| Extension version | Blender version |
| ----------------- | --------------- |
| 1.0.x             | 5.2.x           |

Releases are built for Windows x64, macOS arm64 and Linux x64.

## Installing the extension

The extension is installed from its own Blender extension repository, which
also keeps it up to date:

1. Open **Edit ▸ Preferences ▸ Get Extensions**.
2. Open the **Repositories** menu (top right), click **+** and choose **Add
   Remote Repository**.
3. Enter this URL, tick **Check for Updates on Startup**, and click **Create**:

   ```
   https://richardburnsrally.github.io/blender-track-exporter/index.json
   ```

4. Search for **RBR Track Exporter** in the extension list and click
   **Install**. Blender picks the build for your platform.

New versions then show up in **Get Extensions** like any other extension
update. Pre-releases are published here too.

### Installing a zip by hand

Every release's zips are also on the
[releases page](https://github.com/RichardBurnsRally/blender-track-exporter/releases).
Download the one for your platform and drag it into a Blender window, or use
**Edit ▸ Preferences ▸ Get Extensions ▸ Install from Disk…**. A zip installed
this way doesn't update itself.

## Setting up export directories

The exporter writes into your RBR installation's maps directory. You register
one or more named directories once, in the extension preferences, then pick one
per stage.

1. Open **Edit ▸ Preferences ▸ Add-ons** and expand the **RBR Track Exporter**
   preferences.
2. Click **Add RBR export directory**.
3. In the new row, type a name in the left field (this is the label you'll
   choose from later) and set the right field to the folder you want to export
   into. The folder must already exist.
4. Save your preferences.

Remove a directory with the **−** button at the end of its row.

You can register several — for example a live game install and a scratch
folder — and switch between them per stage via **Export To** in the scene
settings. See [Exporting](./exporting.md).

## Files made with the old addon

When you open a `.blend` made with the old (v0.x) addon, **Scene Properties ▸
RBR Scene Settings** shows a warning box. Back up the file, then click
**Migrate**. Exporting won't work until the file is migrated.

If it was last saved with an addon older than v0.2.2, the box says so: open
and save it with [v0.3.3](./legacy/download.md) first, then migrate.

If the file links in other `.blend` libraries made with the old addon, migrate
those first and then reopen this file.

For what's different in v1, see the [1.0.0-rc.2 changelog](./changelog/1.0.0-rc.2.md).

After migrating, a dialog offers **Optional migrations**: changes to geometry,
animation or datablocks that are worth checking one by one. Tick the ones to
run. Until you dismiss it, the scene panel keeps a box with **Choose...** to
run them later. The console lists what was changed and anything that needs
your attention.
