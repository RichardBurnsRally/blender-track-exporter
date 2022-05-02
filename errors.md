<title></title>
## [Home](index.md) | [Download](download.md) | [Guide](guide.md) | Errors | [GitHub](https://github.com/RichardBurnsRally/blender-track-exporter/issues)

These are the error codes emitted by the addon. This is intended as a reference.

# E0001

This error indicates that your brake wall object has too many vertices.

RBR has a hard limit on the number of points a brake wall can have, equal to
2<sup>14</sup> (16384 individual points).

Lower the density of your brake wall mesh to fix this.

# E0002

When specifying your brake wall object, you must set vertex groups to tell the
addon which side of the brake wall is the inside and which side is the outside,
and optionally which sections of the wall should cause the car to respawn when
it comes to a stop within them.

This error means the addon was not able to find one of the vertex groups in your
brake wall mesh. Check your RBR object settings and mesh, ensure the vertex
groups exist in the mesh data, and ensure that the object settings are pointing
to the correct vertex groups.

# E0003

Each brake wall vertex _must_ be assigned to _either_ the inner or the outer vertex group.

Check the vertex at the given position is assigned to one of the two groups. It
must be assigned to exactly one of them.

# E0004

This error indicates that your brake wall object has no vertices, so it could
not be exported. Either disable exporting this object, or add some brake wall
points around your stage.

# E0005

Each inner vertex of the brake wall must have exactly one pairing outer vertex,
and the vertex groups of each should reflect this.

The addon was not able to pair up inner and outer vertices, because there are
different numbers of each.

# E0006

The brake wall object must be a strip of rectangles surrounding the stage.
This implies two rules for each individual vertex:

1) Each inner vertex must have three edges.

- One connecting to the corresponding outer vertex
- Two connected to the adjacent inner vertices on either side

2) Each outer vertex must have three edges.

- One connecting to the corresponding inner vertex
- Two connected to the adjacent outer vertices on either side

Check the vertex at the given world position and ensure it matches the
above rules. If it looks correct, try cleaning up the mesh manually (deleting
the edges around this vertex and recreating them) or automatically (using the
operator Mesh > Clean Up > Merge by Distance).

# E0007

This error is emitted when parsing an invalid `.col` file, or a `.col` file
which is not really a `.col` file (perhaps a bad renaming, or you just selected
the wrong one).

# E0008

The addon could not read the `.col` file due to a bad collision tree data type.

# E0009

The addon could not read the `.col` file due to a bad collision tree type.

# E0010

The `.col` file contained an unexpected collision tree data type.

# E0011

The `.col` file contained vertex data in an unexpected position, so the file
could not be read.

# E0012

Padding bytes contain non-zero data in water surfaces, which indicates parsing
has gone wrong somehow.

# E0013

Could not unpack the col file data due to a bad root file node offset within the file.

# E0014

Found unexpected collision tree type in the col file root, meaning unpacking was
not possible.

# E0015

Found non empty branch traversal structure in the col file root tree.

# E0016

Trying to unpack the brake wall at a bad offset, this indicates either a bug in
the parsers or an invalid col file.

# E0017

Trying to unpack the wet surfaces at a bad offset, this indicates either a bug
in the parsers or an invalid col file.

# E0018

Trying to unpack the water surfaces at a bad offset, this indicates either a bug
in the parsers or an invalid col file.

# E0019

Trying to unpack the vertices at a bad offset, this indicates either a bug
in the parsers or an invalid col file.

# E0020

Trying to unpack the root tree at a bad offset, this indicates either a bug
in the parsers or an invalid col file.

# E0021

Trying to unpack the sub tree nodes at a bad offset, this indicates either a bug
in the parsers or an invalid col file.

# E0022

Trying to unpack a subtree at a bad offset, this indicates either a bug in the
parsers or an invalid col file.

# E0023

Trying to unpack a subtree but encountered a bad subtree type. The addon can
only unpack relative addressed subtrees.

# E0024

Trying to unpack subtree vertices but encountered a bad offset.

# E0025

Encountered an unexpected type when unpacking a subtree.

# E0026

Trying to unpack subtree collision tree but encountered a bad offset.

# E0027

Did not unpack all bytes of the col file. The entire col file should be consumed
by the parser.

# E0028

A binary parser overflowed its bounds. The format might be bad, or this might be
a bug in the addon.

# E0029

A binary parser overflowed its bounds when unpacking raw bytes. The format might
be bad, or this might be a bug in the addon.

# E0030

A binary parser overflowed its bounds when unpacking raw bytes at some
particular offset.

# E0031

The parser attempted to skip some padding bytes, but the bytes were non-zero. We
expect them to be zero so we can ensure round tripping by default, and this may
indicate a bug in the parser, or a badly formatted file.

# E0032

The parser tried to unpack a length prefixed array, but the length found in the
file was not evenly divisible by the expected item size.

# E0033

When unpacking a size or length value from a binary file, the addon encountered
a number so high that it would indicate something has gone wrong (for example a
length indicating billions of items in a list).

# E0034

Couldn't parse a 3 length vector value from the given ini string.

# E0035

The DDS file header has an incorrect "magic" value, indicating that this might
not be a DDS file or it is somehow corrupted.

# E0036

The DDS file is missing some flags which are required by the DDS specification.
Check your file is actually a valid DDS file.

# E0037

The DDS file has an unexpected value for pixelformat size.

# E0038

The selected DDS file is uncompressed. You must re-export your texture using
DXT1/3/5 compression.

# E0039

The selected DDS file is compressed but has an unexpected codec. You should
export using DXT1/3/5 compression, or if you really require non-DXT compression,
open a ticket so this constraint can be relaxed.

# E0040

Something went wrong when parsing the given DDS file. See the sub error code for
more details.

# E0041

The DLS parser encountered an invalid trigger kind when parsing the sig trigger
data.

# E0042

The DLS parser encountered an invalid trigger kind when parsing the boolean
channel data. Only activation triggers are supported.

# E0043

The DLS parser encountered some boolean channels, but they are currently
unsupported because none of the native tracks have this data. If you run into
this, please open a ticket.

# E0044

The DLS parser encountered an invalid trigger kind when parsing the real
channel data.

# E0045

The real channel data contains a non-zero 'time-based' value, but the addon
expects it to be zero. If you run into this, please open a ticket.

# E0046

The animation channel descriptors have a fixed size in all native stages, but
when parsing this DLS file we encountered a different size. If you run into
this, please open a ticket.

# E0047

When unpacking a spline interpolation type, the parser left some bits behind.
This could be a bug in the addon, or an invalid file.

# E0048

The DLS trigger data parser expected the redundant unused ID to equal the real
ID of the trigger data. All native tracks obey this principle.

# E0049

The DLS file header was invalid, indicating this might not actually be a DLS
file.

# E0050

The DLS file parser missed some bytes when parsing a certain section type.

# E0051

The DLS file does not contain a required section, and is therefore invalid.

# E0052

The FNC file contains an unexpected fence type value.

# E0053

The FNC file contains an invalid version, or the file is not an FNC file.

# E0054

The FNC file has an unexpected number of texture names.

# E0055

A material in the MAT file has a bad bitmap size. The file might be invalid, or
not a MAT file.

# E0056

The shadow.dat parser missed bytes at the end of the file.

# E0057

Some mesh data is missing the 'render state' track object flag.

# E0058

Object data contains different vertex size than the expected size given the
object flags.

# E0059

Object data has no diffuse textures but has specular data, which should be
impossible.

# E0060

The LBS geom block triangle index must be divisible by 3, but the value in the
file is not.

# E0061

The LBS file render chunk data has an unexpected pixel shader ID for the given
render type. The render type restricts the possible pixel shader ID, and this
combination must be invalid.

# E0062

Some of the redundant (and unused) data contains an unexpected value in the LBS
file.

# E0063

The shadow texture values in the LBS render chunk data are invalid or
unexpected (i.e. the native tracks do not have values like this).

# E0064

The specular texture values in the LBS render chunk data are invalid or
unexpected (i.e. the native tracks do not have values like this).

# E0065

The diffuse texture values in the LBS render chunk data are invalid or
unexpected (i.e. the native tracks do not have values like this).

# E0066

The LBS file render chunk data has an unexpected vertex shader ID for the given
render type. The render type restricts the possible vertex shader ID, and this
combination must be invalid.

# E0067

This render chunk data is marked as having no UV velocity, but the UV velocity
values are not null.

# E0068

Object block data is missing the 'render state' track object flag, so it cannot
be parsed.

# E0069

Object block data contained a non-zero 'init' value, but the parser expects this
to always be zero.

# E0070

Object block data contained a vertex size which does not match the expected
vertex size of the track object flags.

# E0071

The LBS segment header was an unexpected size, so the parser could not handle
it.

# E0072

The LBS segment category does not match the expected value given by the segment type.

# E0073

The LBS file is missing a required section.

# E0074

The driveline format has some redundant unused data which is expected to be zero
by the parser, but the parser encountered some non-zero values.

# E0075

The shape collision mesh field 'use local rotation' value is expected to be
boolean, i.e. 1 or 0, but some other value was encountered by the parser.

# E0076

The TRK segment header was an unexpected size, so the parser could not handle
it.

# E0077

The TRK segment category does not match the expected value given by the segment type.

# E0078

The TRK file is missing a required section.

# E0079

Collision mesh tree node header has unexpected vertices offset, so parsing was
aborted.

# E0080

Collision mesh tree root node has triangle data, but we don't expect triangle
data at the root.

# E0081

Collision mesh tree root tree at unexpected offset. The parser has unpacked the
header, and the header is pointing to a different position in the file than we
expect. This is a little strict, and the file may be loaded by the game, but the
addon parsers do not handle it.

# E0082

Collision mesh tree subtree at unexpected offset. See E0081 for more
information.

# E0083

While unpacking the world geometry chunks, the parser encountered differing
numbers of blocks for different geometry types. These lists of blocks must be
the same length because they are associated to each other by index.

# E0084

See E0083, but specifically for "visible object vecs".

# E0085

Couldn't unpack the brake wall because the parser found an odd number of
vertices. We expect the brake wall to consist of pairs of vertices, so the
number should be even.

# E0086

When unpacking a brake wall index, we expected an even offset but got an odd
offset. See E0085.

# E0087

Parser is at the wrong offset when unpacking a brake wall branch.

# E0088

Parser is at the wrong offset after unpacking the brake wall header.

# E0089

Parser is at the wrong offset when unpacking the brake wall tree.

# E0090

Parser is at the wrong offset after unpacking the brake wall.

# E0091

Encountered unexpected number of visible object vecs.

# E0092

Found second diffuse texture in object data, but there is no first diffuse
texture.

# E0093

Found specular texture in object data, but there is no diffuse texture.

# E0094

This shape collision mesh does not have the correct type given its name. Shape
meshes with "CONE" in the name will be changed to interactive objects of type
"Traffic Cone" silently by the game. Either rename your object or change the
type to match.

# E0095

This shape collision mesh does not have the correct type given its name. Shape
meshes with "BANNER_STAND" in the name will be changed to interactive objects of type
"Banner Fence" silently by the game. Either rename your object or change the
type to match.

# E0096

A shape collision mesh has too many vertices. Reduce the density of the mesh to
fit within the limit. Bear in mind that shape collision mesh objects should be
very simple, like cuboids for tree trunks. Do not join your shape collision mesh
objects into one giant object, they must be separate.

# E0097

A shape collision mesh has too many edges. See E0096.

# E0098

A shape collision mesh has too many faces. See E0096.

# E0099

There are too many shape collision meshes to export. RBR has a hard limit for
the number of unique meshes you can export. In general if you are anywhere close
to this limit you have probably structured your file incorrectly: these are
instanced objects, so if you have 2000 trees the tree trunks should only take up
a single mesh slot because each of the tree trunks should be using the same
underlying mesh data. In blender this is achieved by using the same mesh for
each of your tree trunks (by linking the collision mesh data for each of your
tree objects).

# E0100

Encountered unexpected surface type string. Valid values are dry/damp/wet.

# E0101

Encountered unexpected surface age string. Valid values are new/normal/worn.

# E0102

A track name in the track settings file could not be parsed.

# E0103

A track specification in the track settings file could not be parsed.

# E0104

An object marked for RBR export is using a material which does not contain a
valid RBR shader node tree. Check the material node tree and ensure it uses an
RBR material setup.

# E0105

The selected export directory is missing from your addon preferences. Either add
that named directory to the addon preferences or change the export target to a
different directory.

# E0106

The 'car location' object could not be found when exporting. Create an 'empty'
object of type 'arrows' and position it where you want the car to be when the
stage is started. The Y axis points forwards, Z upwards. Set the RBR object type
to car location, and try exporting again.

# E0107

One of the textures you are using for collision mesh generation does not have
suitable material maps. Some of the UV triangles ended up outside of the bounds
of your material map definitions. Note that the addon moves your UV triangles
towards the image area, you may need to account for that. You can also use
repeated material maps to automatically cover triangles outside of the image
area, but those triangles must be less than half the width and height of the
image itself. Alternatively, expand or create more material maps to cover all
UV triangles, or move the UV triangles within the existing maps.

# E0108

One of the materials used for collision mesh generation does not have an RBR
diffuse texture associated with it, meaning the physical material could not be
mapped. Check the material and add a diffuse texture (and corresponding material
maps).

# E0109

The world collision mesh is a required part of the RBR files, but no objects for
collision mesh generation were found in blender. Check that the objects are
enabled for export, or that your "Near" geom block ground object is marked
"Generate Collisions".

# E0110

The addon found a missing vertex colour layer in the mesh. The mesh is using a
material which has a vertex colour node set to a non-existent layer. Either
change that node layer or create the layer in your mesh.

# E0111

While baking values for export, the addon encountered a clamp node which is not
set to min/max mode. Currently only min/max mode is supported, so switch your
node to that if possible. If you require other modes, contact the addon
maintainers.

# E0112

While baking values for export, the addon encountered a color ramp node which is
not set to "RGB". If you require other modes, contact the addon maintainers.

# E0113

While baking values for export, the addon encountered a color ramp node which is
using an unsupported interpolation mode. Currently supported modes are "Linear"
and "Constant". If you require other modes, contact the addon maintainers.

# E0114

A loop was detected in the given shader tree. Check your material definition and
remove loops.

# E0115

One of your RBR materials uses a geometry shader node, but is using an
unsupported output socket. If you need this socket to be exportable, contact the
addon maintainers.

# E0116

One of your RBR materials uses an unsupported node. If you need this node to be
exportable, contact the addon maintainers.

# E0117

One of your RBR materials is not using the main RBR shader, so the addon can't
find any information to export. Check the material is defined correctly with a
single RBR shader node.

# E0118

One of your RBR materials cannot be baked due to another error. Check the error
message and related error code for more details.

# E0119

One of your RBR meshes has no materials for baking. Check the object has at
least one RBR material.

# E0120

One of your materials is using a texture but has a missing UV map. Ensure you've
connected UV map nodes and set the correct layer.

# E0121

An image used in an exported texture has been packed into the blend file.
Exporting requires unpacked DDS files.

# E0122

An image used in an exported texture does not have a power of 2 size. Sizes
should be a power of 2, e.g. 512, 1024, 2048... but not necessarily square.
Resize your image file to fit these requirements.

# E0123

An image used in an exported texture could not be found at the specified path.
Check that the image file exists where blender expects it.

# E0124

The images used within an exported texture have different DDS settings to each
other. This might cause issues because some settings are shared between all
variants of a texture. Re-export these from your image editor using the same
settings.

# E0125

No images have been selected for an exported texture. You must select images for
each of the supported track variants. Check your material definitions and set
the images appropriately.

# E0126

No images have been selected for an exported specular texture. You must select
images for each of the supported track variants. Check your material definitions
and set the images appropriately.

# E0127

An exported object does not have a texture, but the object type selected
requires at least one.

# E0128

An object block object is using a material which is not set to an alpha blend
mode. These objects must use an alpha blend mode (blend or hashed will give the
best preview).

# E0129

An object block object is using a material with an invalid texture setup. Object
blocks must have exactly one diffuse texture and no specular texture.

# E0130

Your file has interactive objects which are missing their corresponding shape
collision meshes. Each interactive object must have a child shape collision mesh
object.

# E0131

There is more than one zfar object in your track, so it's ambiguous which one
should be used. Delete all but one of the zfar circles.

# E0132

In order for correct visualisation in blender, the parent of the render distance
circle must be the driveline. Check your render distance object obeys this rule.

# E0133

In order for correct visualisation in blender, the render distance object must
be an empty of type "circle".

# E0134

There must be exactly one exportable driveline object in order to export for
RBR. Ensure you have one (and only one) object marked as "Driveline".

# E0135

The driveline object must be a bezier spline in order to be exported. If you've
constructed a mesh poly line, you can convert it to a curve (ensure it is a
bezier spline).

# E0136

The driveline object has a hard cap on the number of points it can have in
total. Reduce the density to get below the specified limit.

# E0137

The driveline curve must obey a few rules in order to function properly in game.

In this case, any adjacent handles must not be rotated beyond 180 degrees of
each other. For example, see the image below. Curve 1 is illegal, since the
curve handles are more than 180 degrees apart (see they splay away from each
other at the top). This can be fixed by either subdividing that segment (like
curve 2) or tweaking the handles so they point slightly towards each other at
the top (like curve 3).

![Curve examples](assets/driveline-subdivision-example.png)

The addon is strict about this condition, because the game will interpolate the
segment backwards in case 1, which could lead to corner cutting penalties.

Check the world position given by the error message, this will point you to the
bad section of your driveline. Fix that segment according to the rule above, and
try to re-export.

# E0138

One of the materials used in an RBR object is not using a node tree, which means
it is not using the RBR material shaders. The addon can only export RBR shaders.
Update this material so it fits the expected material node layout.

# E0139

An RBR shader node has an unconnected texture socket. All of the texture sockets
must have connections to RBR texture nodes. If you don't need a particular
texture socket, uncheck it in the shader node options and it will be removed.

# E0140

An RBR shader node has a texture socket which is not connected to an RBR texture
node. Ensure your texture nodes are connected _directly_ to the shader sockets
(i.e. with nothing inbetween).

# E0141

An RBR material contains texture nodes with no UV map input connected. Connect
either a UV map node to each of your textures or a UV velocity node (for
animated textures).

# E0142

An RBR material contains texture nodes with an unsupported UV map input. Connect
either a UV map node to each of your textures or a UV velocity node (for
animated textures).

# E0143

An RBR material contains a UV velocity node with a connected UV velocity input.
Disconnect the UV velocity input on your UV velocity node. You can set the UV
velocity with the input boxes.

While the UV velocity input _could_ just be inputs without a socket,
implementing them as a socket input means all UV velocity nodes can share a node
tree.

# E0144

An RBR material contains a UV velocity node with a disconnected UV map input.
Ensure a UV map node is connected to the UV map input of your UV velocity node.

# E0145

An RBR material contains a UV velocity node with an unsupported UV map input.
Ensure a UV map node is connected to the UV map input of your UV velocity node.
There cannot be any nodes in between the UV map node and the UV velocity node.

# E0146

While importing the material maps, we encountered mismatched numbers for
different surface conditions. This is probably a bug in the stage data.

# E0147

A mesh is using an RBR material which requires a particular UV map layer, but
that UV map layer is missing in your mesh data.

# E0148

In order to export the cameras or render distance objects, a driveline is
necessary. Make sure you have a single driveline object active.

# E0149

Some vector math nodes operations are not supported for export. They can be
added if needed, please create a ticket for the operation you need.

# E0150

A material in an exported object is using a material which is linked to the
object, not to the data (i.e. the mesh). Check the material in question and mark
it as linked to the data. The button for this is on the right of the text box
where you can rename the material.
