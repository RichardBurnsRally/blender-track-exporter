# RBR Glossary

We generally stick to the terms used by the original RBR developers.

Animation objects
: Animations of deer crossing or spectators running from the road can be
triggered at points along the driveline, with some element of randomness. *(not
yet authorable)*.

Brake wall
: A soft wall around the stage which prevents the car from driving too far away
from the road.

Cameras
: Viewpoints triggered during replays.

Car location
: The start position and orientation of the player car.

Clipping planes
: Occlude geometry behind them from the cameras view, but aren’t directly
visible themselves. Used to hide areas of the track which shouldn't be visible
in the distance.

Driveline
: A spline of the racing line: used to trigger events, pacenotes, and controls
where the car respawns.

Fences
: Physically flexible fences: tape or plastic net supported by poles.

Geom blocks
: Opaque static geometry: ground, buildings, etc.

Ground collision mesh
: The physical mesh the car interacts with. Each face has a material map.

Interactive objects
: Dynamic physics objects: signs, wooden fences, concrete blocks.

Material maps
: 16×16 grids of physical material IDs

Object blocks
: Transparent textured geometry: usually foliage. Vertices are animated to give the appearance of swaying in the wind.

Reflection objects
: Faked reflections: inverted geometry that exists under bodies of water.

Registration zone
: The end-of-stage registration area. The stage automatically ends when the car
stops here.

Shape collision meshes
: Static, instanced collision meshes: e.g. tree trunks.

Super bowl
: Background geometry: always drawn, so must have a low polygon count.

Surface age
: How worn-in the racing line is: **New**, **Normal**, **Worn**.

Surface type
: How wet the road surface is: **Dry**, **Damp**, **Wet**.

Tint set
: A *time of day* lighting variation. **Morning**, **Noon**, **Evening**,
**Overcast**. Each tint set is essentially a separate stage.

Water objects
: Geometry which can use transparent textures and UV animation, especially used
for planes of water (like lakes and rivers).

Weathers
: A pairing of a **Weather** description and a **Sky** description. They
control things like lighting parameters, sky appearance, and fog settings.

Wet/water surfaces
: Simple quads which define water splash areas. Water surfaces always give water
splashes, but wet surfaces only work under wet conditions.
