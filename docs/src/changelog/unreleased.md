# Unreleased

Changes since 1.0.0-rc.5, for the next release.

## New

- **Undefined material warning.** Export warns about each texture whose
  material maps leave cells undefined in an exported dry/damp/wet condition,
  so unpainted cells and unset fallbacks don't go unnoticed.

## Changed

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
