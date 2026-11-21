# World Settings

Each weather slot in a tint set is backed by a Blender **World**. Its settings
live in **Properties ▸ World ▸ RBR World Settings**, and are also embedded
inline under **Scene Settings ▸ Tint Sets ▸ Weather Settings** for the active
weather.

On export each weather is written to `TrackSettings<Track ID>.ini`, keyed by
its tint set, **Weather** and **Sky** (for Overcast, the slot's **Time** too). If
two weathers in a tint set share the same Weather and Sky, only one of them is
exported.

The two top-level fields classify the weather:

- **Weather** — Crisp, Hazy, Light/Heavy Fog, No/Light/Heavy Rain,
  No/Light/Heavy Snow.
- **Sky** — Clear, Part Cloud, Light Cloud, Heavy Cloud.

Below that the settings are grouped into collapsible panels.

## Fog

Toggle **Use Fog** to enable the fog panel:

- **Color** — fog colour.
- **Start** / **End** — distances over which fog ramps in.
- **Superbowl Start** / **Superbowl End** — fog distances for the skybox
  ("superbowl").
- **Skybox Saturation** — how much of the sky dome (sky and clouds) shows
  through the fog colour in the preview: `0` paints it entirely in the fog
  colour, `1` leaves it unfogged.

## Track Settings

The main panel for sun and atmosphere.

- **Cloud Name** — the cloud texture set. The preview reads the cloud textures
  from `Clouds_textures.rbz` in the export directory, for the active surface
  type, so it needs **Export To** set.
- **Sun** — point this at a Sun light object to take the light direction from
  its rotation. **Light Direction** then follows the sun as you rotate it and
  is greyed out; otherwise set **Light Direction** by hand.
- **Sun Intensity** — overall sunlight strength.

It contains three sub-panels:

### Ground

Controls how bright the terrain reads. The **Balance** meter shows
max(Reflectance Color) × Extinction × Sun Intensity × Reflectance Multiplier,
and the box below it turns red when that is more than 0.2 away from 1.0:

- **Auto Balance** (on by default) — sets **Reflectance Multiplier** to bring
  the balance to 1.0 whenever Extinction, Reflectance Color or Sun Intensity
  change, and greys the multiplier out.
- **Extinction**, **Reflectance Multiplier**, **Reflectance Color** — terrain
  reflectance.
- **Specular Alpha**, **Specular Glossiness** — terrain specular response.
- **Geom Block Glossiness** — a global (whole-stage) specular glossiness for
  geometry blocks.
- **Superbowl Scale** — scale of the skybox terrain.

### Sky

Atmospheric scattering and skybox tuning: **Greenstein Value**,
**Inscattering**, **Mie Multiplier**, **Rayleigh Multiplier**, **Cloud Scale**,
**Skybox Scale**, **Turbidity**, **Sun Offset**.

### Other

Lighting that doesn't feed the sky shaders: **Ambient**, **Car Ambient
Lighting**, **Car Diffuse Lighting**, **Car Deep Shadow Alpha**, **Car Shadow
Alpha**, **Character Lighting**, **Mip Map Bias**, **Particle Lighting**.

> Most of these map directly onto RBR's per-weather lighting parameters. The
> defaults are reasonable starting points; tune them against the in-game look
> for each weather.
