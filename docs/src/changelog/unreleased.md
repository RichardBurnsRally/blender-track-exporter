# Unreleased

Changes since 1.0.0-rc.5, for the next release.

## Fixed

- **Migrating old addon files.** Migrating a file from the old addon failed
  in 1.0.0-rc.5 with a `'RBR Texture Color'` error. Textures fed by other
  nodes, such as an Image Texture, are now bundled too, and texture links the
  shader can no longer take are listed in the migration report.
