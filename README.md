# RBR Track Exporter

A Blender extension for building Richard Burns Rally tracks and exporting
them to the game's native formats (.trk, .lbs, .col, .dls, .fnc, ...).

Do not download this repo to install! Installation instructions can be found
[on the docs site](https://richardburnsrally.github.io/blender-track-exporter/installation.html).

## Contributing

The extension is pure Python (this repository) plus a closed-source compiled
core used for export. Contributions to the Python side and docs are welcome,
but please do not dump LLM code into PRs, I will just close the PR. Detailed
bug reports in issues are much more useful.

## Docs

User-facing authoring and export docs live in `docs/`, built with
[mdBook](https://rust-lang.github.io/mdBook/) and deployed to GitHub Pages on
push to `main`. Build locally with `mdbook serve docs` (after
`cargo install mdbook`).
