# Unreleased

Changes since 1.0.0-rc.5, for the next release.

## New

- **Undefined material warning.** Export warns about each texture whose
  material maps leave cells undefined in an exported dry/damp/wet condition,
  so unpainted cells and unset fallbacks don't go unnoticed.
- **Automatic damp and wet material maps.** Damp and wet material maps and
  fallbacks can follow the dry ones, with each material made one or two steps
  wetter. New textures start automatic; switch conditions in the new **RBR
  Material Maps** panel in the Image Editor sidebar.

## Changed

- **Material map editor tools.** The material map editor is now four Image
  Editor tools, **Paint Materials**, **Fill Materials**, **Sample Material**
  and **Material Map Regions**, instead of a modal editor. Every stroke, fill and region change
  can be undone, the material palette is in the **Active Tool** panel, and the
  view no longer jumps when switching condition. Conditions are picked from a
  grid in the **RBR Material Maps** panel, and **Active Surface** can show
  surfaces the stage doesn't export.
- **Simpler shader internals.** Simplified the internal representation of
  some custom node types.

## Fixed

- **Migrating old addon files.** Migrating a file from the old addon failed
  in 1.0.0-rc.5 with a `'RBR Texture Color'` error. Textures fed by other
  nodes, such as an Image Texture, are now bundled too, and texture links the
  shader can no longer take are listed in the migration report.
- **Vertex blend and alpha on export.** Geom blocks exported the Color
  input's alpha instead of **Blend**, and reflection objects, water objects,
  super bowls and interactive objects ignored their **Alpha/Blend** or
  **Blend** input. Stages where these come from a different attribute than
  the colour, such as files migrated from the old addon, now blend in game as
  they do in the viewport.
