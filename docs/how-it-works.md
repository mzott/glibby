# How it works

This page explains what glibby does to your file, for anyone who wants to understand or change the output.

## Input format

A frame is an atom-count line, a comment line, then one line per atom:

```
3
water (comment line; may be empty)
O   0.0000  0.0000  0.0000
H   0.9600  0.0000  0.0000
H  -0.2400  0.9300  0.0000
```

A multi-frame file is frames written one after another.

**Accepted:**
- Windows or Unix line endings, spaces or tabs.
- Empty comment lines, and blank lines between frames or at the start and end of the file.
- Extra columns after `z` (charges, forces), which are ignored.
- Numbers like `1.5`, `-.5`, `1.2e-3` and Fortran-style `1.2D-3`.
- Element symbols in any case: `fe` and `FE` both become `Fe`.

**Rejected,** with a message naming the frame and line:
- A frame that is cut off, or a count line with no atoms after it.
- A different atom count, or a different element order, in a later frame.
- Coordinates that are not finite numbers (`abc`, `nan`, `inf`) or are missing.
- Element names that are not 1–3 letters (`H1`, `X9`).
- A blank line inside a frame.

**Atomic numbers** (`8` for O) are rejected unless you confirm. They're often a sign of a mislabelled file, so glibby asks rather than guessing.

## Bonds

glibby decides bonds from distances. A pair of atoms is bonded if, in **any** frame, they are closer than a cutoff:

| Pair | Cutoff |
|---|---|
| Two non-metals | 1.22 × (sum of covalent radii) |
| H with any non-metal | 1.30 Å |
| H–H | 0.95 Å |
| Metal–H | 1.75 Å |
| Metal–C | 2.15 Å |
| Metal–other | 2.40 Å |

Metals are Fe, Co, Ni, Cu, Zn, Ru, Rh, Pd, Ir, Pt, Mo, W, Mn, Cr, V, Ti, Sc, Au, Ag, Mg, Ca and Al.

A bond is **dynamic** if it is shorter than its cutoff in some frames and longer in others, or its length changes by more than 0.35 Å. Dynamic bonds thin out as they stretch: full thickness up to about the bonded distance, fading to nothing at 1.25 × the cutoff, or 0.55 Å past full thickness if that is longer.

## Style

The style follows ChimeraX's ball-and-stick look:

- **Atoms** are spheres sized per element (0.34 Å for C, N and O; 0.48–0.50 Å for transition metals). Hydrogen spheres are the same width as a bond, so C–H bonds look like capped sticks.
- **Covalent bonds** are 0.16 Å-radius cylinders split in half, each half colored like the atom at its end.
- **Metal–ligand bonds** are thinner (0.125 Å) single-color cylinders.
- Elements missing from glibby's table get a generic magenta and a 0.38 Å sphere. Override the color with `--color` or the web page's color picker.

Colors are entered as normal 0–255 sRGB values and converted to the linear color space glTF requires, so they look the same in PowerPoint as on screen.

## Why bones?

PowerPoint only plays animations in a `.glb` that use **skeletal animation (skinning)**. That's the technique games use for characters, where invisible bones move the mesh around them. It ignores the simpler approach of moving objects directly.

So glibby gives every atom and every bond its own bone:
- **Atom bones** move to each frame's coordinates.
- **Bond bones** sit on the first atom, rotate to point at the second, and stretch to the bond length (and thin out for dynamic bonds).

Each sphere and cylinder is attached to exactly one bone, so it moves rigidly with it. The frames become keyframes, and PowerPoint interpolates linearly between them.

## PowerPoint limits glibby works around

Found by testing in PowerPoint for Windows (Microsoft 365, 2026):

| Limit | What happens | glibby's workaround |
|---|---|---|
| About 255 bones per skinned mesh (235 imported, 259 failed) | "An error occurred while importing this file" | Animated models with more than 200 bones are split into several meshes of at most 200 bones each. Single-frame models are exported with no bones; their positions are baked into the mesh. |
| No node-transform animation | Model imports but doesn't animate | All animation is skeletal (see above). |
| Back-face culling and gamma | Hollow-looking spheres, washed-out colors | Triangles wound counter-clockwise, `OPAQUE` materials, sRGB→linear color conversion. |

glibby also keeps every mesh piece at 65,535 vertices or fewer, so all indices are 16-bit, the most widely supported option.

Each file contains one animation clip (called a **Scene** in PowerPoint) however many frames it has.

## File structure

An animated file contains:

- `RootNode`, with children:
  - one `MoleculeMesh_N` node per skinned mesh (usually just one);
  - `Armature`, whose children are the bones `Bone_Atom_<n>_<El>` and `Bone_Bond_<i>_<j>`.
- One material per element (`Mat_C`, `Mat_N`, …) plus `Mat_CoordBond`.
- One animation, `Reaction_Trajectory`, with translation channels for atom bones and translation, rotation and scale channels for bond bones.

A static file contains only `RootNode` → `MoleculeMesh` and the materials.

## The two implementations

`glibby.html` (JavaScript) and `glibby_cli.py` (Python) implement the same pipeline and produce the same geometry. The test suite checks both against the same example files; see [Contributing](contributing.md).
