## blendRBR | [Home](index.md) | [Download](download.md) | Guide | [GitHub](https://github.com/RichardBurnsRally/blender-track-exporter/issues)

**[« Back to guide](guide.md)**

Features are listed by their name in RBR, with comments summarising the level of
support for each format. If anything is outdated or wrong on this page, let me
know.

### 🌍 Geom blocks

Used for opaque static geometry (i.e. the world). This geometry is split into
chunks, and these chunks are only rendered when they are within the "render
distance" circle, which is variable along the driveline.
The mesh can have vertex colours, two diffuse textures (blended by the vertex
colour alpha channel), a specular texture, and a shadow texture. The diffuse and
specular textures can be animated (UV animation, useful for water). There are 3
levels of detail: near, any, and far.

These levels of detail work as such:

- Near: High detail mesh which is visible when the chunk is closer than 600m
- Any: Mid-low detail mesh which is always visible
- Far: Very low detail mesh which is only visible when the chunk is further than 550m away

For RenderQuality=low there are some differences:
- The distances the game switches between near and far geometry is much closer
- The far geometry is always used for car reflections

Typically the geometry the player can drive on is high detail, and marked as
"near" geometry, and it has a corresponding very low polygon copy placed as
"far" geometry. This is the primary LOD mechanism of RBR, and while very simple,
it works well. Geometry further than 40m away from the stage is lower poly
(because the player can't get to it since the brake wall blocks them) and marked
"any".

| Blender Addon                 | Wallaby
|-------------------------------|------------------------
| No shadow support yet [0]     | Named "Ground meshes"
| No animated texture UVs [1]   | One diffuse texture
|                               | No specular texture
|                               | No level of detail [2]
|                               | Partial shadow support [3]
|                               | No animated texture UVs

[0] Shadow texture generation is not yet complete, but will be soon<br>
[1] Animated texture UVs are parsed, and we know how they work. We just need to
add them to the exporter and importer.<br>
[2] Everything is marked "near", so even if zfar was set correctly, which it
isn't, the maximum view distance would be 600m.<br>
[3] Partial shadow generation via a web service. There is a limit on the size of the track.<br>

### 🌲 Object blocks

Used for static geometry with transparent textures, usually foliage. This
geometry is split into the same chunks as the geom blocks. It only has one
diffuse blended textures - no specular or shadow textures. This geometry can
sway in the wind: each vertex has individual control over the amplitude,
frequency, and phase offset of the oscillation. There is some support for levels
of detail, geometry can be put into a low quality buffer or a high quality
buffer. This cuts down on geometry rendered when far away, but also is altered
by the user settings for high/low quality (although I suspect the setting is
always high these days). Import the vanilla stages to see the difference
between buffers.

| Blender Addon  | Wallaby
|----------------|-------------------------
| Full support   | Named "General meshes"
|                | Partial sway support [0]

[0] This feature was a simple toggle in version 0.28, and it made all of the
"general meshes" sway in a predetermined way. It was removed in later versions.

### 🌊 Water objects

Geometry which can use transparent textures, especially used for planes of water
(like lakes). This geometry is always transparent, no matter the low/high
settings of the user. [TODO: check this]

| Blender Addon  | Wallaby
|----------------|-------------------------
| Full support   | Not supported

### 🌊 Reflection objects

Used for faking reflections - inverted geometry that exists under bodies of
water. Has vertex colours and two diffuse blended textures.

| Blender Addon  | Wallaby
|----------------|-------------------------
| Full support   | Not supported

### 🏔 Super bowl

This is for background geometry: terrain that is so far away the user could
never reach it. Useful for distant mountains, for example. This geometry is
always drawn, no matter the camera settings or how far away the camera is, so
keep the polygon count low. Like reflection objects, it has vertex colours and
up to two diffuse blended textures per polygon.

| Blender Addon  | Wallaby
|----------------|-------------------------
| Full support   | Named "Scenery"
|                | Single diffuse texture per polygon

### ✂ Clipping planes

Simple "transparent" geometry, usually large rectangular planes, which occlude
geometry behind them from the cameras view, but aren't directly visible
themselves. Useful to cut down on the number of triangles being rendered.
Available in two flavours:

- Directional planes which block only in one direction
- Omnidirectional planes which block in both directions

| Blender Addon  | Wallaby
|----------------|-------------------------
| Full support   | Full support?

### 🛑 Brake wall

A soft wall around the track which prevents the car from driving too far away
from the stage. There's only one, so if your stage is a circuit, it must be on
the outside - you can't have one on the inside of a loop. The inner wall defines
where the slowing effect starts, and the outer wall is impenetrable.

| Blender Addon  | Wallaby
|----------------|-------------------------
| Full support   | Not supported

### 💧 Wet/water surfaces

Simple quads which define water splash areas. Water surfaces always give water
splashes, but wet surfaces only work under wet conditions.

| Blender Addon      | Wallaby
|--------------------|-------------------------
| Not supported [0]  | Not supported

[0] The structures are reverse engineered, they just aren't exportable yet. See https://github.com/RichardBurnsRally/blender-rbr-track-addon/issues/243.

### 🌐 Ground collision mesh

The ground collision mesh is an optimised structure, entirely separate to the
visual geometry of the world (at least in the game files). It contains
information about surface materials, and each polygon can have two materials
blended together, much like the two diffuse textures of geom blocks. It also has
some lighting information baked in, and this is used for shading the car and
dust.

| Blender Addon             | Wallaby
|---------------------------|-------------------------
| Full support (generated)  | No blending
|                           | No shading information [1]

[0] The addon does not expose export of this directly, instead it is generated from
your "near" or "any" geom blocks, if you check the "generate collision mesh"
checkbox on an object. The primary reason for this is simplicity (track creators
only need to care about the material mappings for each texture), but also this
makes it easy to support material blending which matches the texture
blending of the geom block.<br>
[1] Wallaby writes fixed values here instead, which causes a faint flickering on
the car as you travel across polygons.<br>

### 💥 Static shape collision meshes

While some tracks have made use of the ground collision meshes for things like
tree trunks, it's not really suited for that: the car can get stuck inside the
tree trunk. These "shape collision meshes" are simple [0] _closed_ meshes which
are instanced: there's a "root mesh" stored in the files, and then all of the
uses of that mesh just contain position, rotation, and scale information. The
mesh has a physical material, and can also have a soft volume which acts
physically like a bush or a snowwall.

| Blender Addon     | Wallaby
|-------------------|-------------------------
| Full support [1]  | Partial support for soft volume [2]
|                   | Time consuming to place in the editor [3]

[0] Max of 30 vertices, max of 84 edges, and max of 56 faces.<br>
[1] Instancing is determined by the underlying mesh data of each collision mesh
object. Duplicates must be linked in order for instancing to work. Soft volumes
are added as "empty" child objects of the main collision mesh, either boxes or
spheres. In the case of entirely soft objects like snow walls, the parent mesh
should be empty too. Import vanilla RBR stages to see how the snow walls are set
up.<br>
[2] It's possible to create bushes if you know the correct material ID.<br>
[3] You can't grab the objects and move them with the mouse, you must enter new
coordinates manually.

### 🚩 Interactive objects

Closely related to static shape collision meshes (the collision meshes are
stored together and share the same limitations), interactive objects are dynamic
physical objects which can be pushed around by the car. This is often used for
signs, fences, and concrete blocks. The choices of object are relatively few,
and their mass and inertia are baked in and not user customisable, so it may
require experimentation to find the right setting. The visual mesh data can have
vertex colours and two diffuse textures. Note that these objects are "sleeping"
until interaction with the car, so they can be used to construct destructable
fences like the vanilla stages.

| Blender Addon     | Wallaby
|-------------------|-------------------------
| Full support [0]  | Single texture

[0] The visual geometry (the "interactive object") is the parent object, and the
collision mesh should be a direct child object. Has the same instancing
constraint as static shape collision meshes.

### 🚧 Dynamic fences/tapes

Sections of coloured tape or flexible orange plastic fences which can be
interacted with.

| Blender Addon     | Wallaby
|-------------------|-------------------------
| No support yet    | Full support [0]

[0] Click to place, but altering fence positions after placing requires manual
entry of coordinates

### 🦌 Animations

Animations of deer crossing or spectators running from the road can be triggered
at points along the driveline, with some element of randomness.

| Blender Addon     | Wallaby
|-------------------|-------------------------
| No support yet    | Use of existing animations [0]

[0] Small bugs like animations having incorrect rotations in the preview

### 🐦 Sound Triggers

Spheres which cause the bird sounds to play in replays.

| Blender Addon     | Wallaby
|-------------------|------------------
| Full support      | Full support [0]

[0] Manual coordinate entry

### 🎥 Cameras

Replay cameras are placed along the road and are triggered at particular points
along the driveline. They can be steady cameras, or handheld (i.e. shakey). The
FOV and position of the cameras can be animated by bezier splines according to
driveline position, and the position animation can be used to create helicams
(along with the helicam noise setting).

| Blender Addon     | Wallaby
|-------------------|-------------------------
| Full support      | No position animation
|                   | Buggy [0]

[0] Adding markers/triggers between existing ones can result in having to delete
them all and recreate them. Additionally, placing cameras correctly requires all
geometry to be active, but this lower FPS substantially.

### ⤴ Driveline

The driveline is a bezier spline which determines when pacenotes are read out,
when events are triggered (start/finish/checkpoints), position animations of
cameras, and the render distance. It's also used to determine where and in which
direction to place the car when a driver calls for help.

| Blender Addon     | Wallaby
|-------------------|-------------------------
| Full support [0]  | No camera position animations
|                   | No render distance [1]

[0] Pacenote support is limited to native RBR notes, and they are added in the
driveline object directly. Animations are handled by blender, we treat the time
in the timeline as the distance along the stage.  When editing the driveline,
you'll notice the addon will reset your handles to keep the spline compatible
with RBR: the handles must be equal length and facing in opposite directions.
For the render distance, create an empty object of type circle, and make the
driveline spline the parent object. Set the RBR object type to render distance,
and set X rotation to 90 degrees so that the circle lies flat on the ground. You
can alter the empty display size to control the render distance, and this can be
animated over time. Import vanilla stages to see examples of how it's often
animated: it's kept to the minimum size possible without causing geometry to pop
in or out. If you need a display size > 1000m, you can do this by scaling the
object, the exported render distance is a multiplication of the scale and the
empty display size.<br>
[1] Wallaby doesn't write the render distance at all, and this would cause the
value to be unpredictable when starting a stage - it would use the last known
value from a previously driven stage. A FixUp patch fixed this recently, so it's
always reset at the start of a stage.

### 🖼 Texture

RBR textures are packaged into a .rbz file (zip format) and a .ini file
controlling texture options.

| Blender Addon                   | Wallaby
|---------------------------------|-------------------------
| Autogeneration of .rbz and .ini | Manually created
| Guards against slow loading [0] |

[0] RBR likes textures with width and height being integer powers of two (2^N).
If a texture isn't this size, it's rescaled to be this size while the stage
loads, and this process is _really_ slow. Just one badly sized texture can
change loading times from almost instant to painstakingly slow.

