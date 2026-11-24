# Unreleased

Changes since 1.0.0-rc.4, for the next release.

## New

- **Node groups in materials.** RBR materials can use node groups, for
  example to share shading between materials: the export reads through them
  as if they were dissolved, and an error inside a group jumps to the node
  inside it.
- **Material switches.** An Index Switch in front of RBR Shader nodes picks
  the shader per instance or object, from a geometry nodes instance attribute
  or a custom property; for example Super Bowl for distant scattered trees.
  See [Materials & Shading](../materials.md#switching-shaders-per-instance).
