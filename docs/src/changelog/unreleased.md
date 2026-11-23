# Unreleased

Changes since 1.0.0-rc.2, for the next release.

## New

- **Keep existing pacenotes** export option, for pacenotes edited outside
  Blender. See [Exporting](../exporting.md#options).

## Changed

- Only the texture images for the surface types ticked in
  [Scene Settings](../scene-settings.md) are exported.
- A texture with no image for a ticked surface type is now an export error. A
  road texture missing some ages of a surface type gets a warning instead.
- **Pass through DDS** textures now use **Mipmap Levels**: the game generates
  the levels a `.dds` lacks and drops any beyond it, and a texture's `.dds`
  files no longer need the same mipmap count. Migrated textures keep the count
  the old addon exported. See [Materials & Shading](../materials.md).
- Picking the **Brake Wall** keeps its existing setup, including its respawn
  areas, instead of resetting it.
- The **Brake Wall** field shows that it takes a curve, and the **Sun** field's
  tooltip says which objects it lists.

## Fixed

- Exporting failed when the brake wall had no respawn areas set.
- A brake wall linked from another `.blend` gave an error when picked, and
  lost its respawn areas on export.
