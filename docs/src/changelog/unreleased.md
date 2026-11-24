# Unreleased

Changes since 1.0.0-rc.4, for the next release.

## New

- **Node groups in materials.** RBR materials can use node groups, for
  example to share shading between materials: the export reads through them
  as if they were dissolved, and an error inside a group jumps to the node
  inside it.
