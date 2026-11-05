---
name: glibby
description: >-
  Converts single-frame or multi-frame .xyz molecular structures and
  trajectories (stationary geometries, vibrational normal modes, reaction paths,
  IRC scans, or MD trajectories) into PowerPoint-compatible 3D .glb models
  (static or bone-skinned animated) rendered in ChimeraX SEQROW ball-stick-endcap
  style with customizable RGB color palettes (defaulting to the 'zott' palette).
  Use when the user asks to export, convert, or embed an .xyz molecule, reaction
  trajectory, normal mode vibration, or molecular animation into a .glb file or
  PowerPoint presentation, or mentions "glibby".
---

# Glibby: XYZ-to-PowerPoint 3D `.glb` Generator

## Overview
`glibby` converts single-frame (stationary) or multi-frame (animated) `.xyz` molecular files into binary glTF 2.0 (`.glb`) 3D models engineered specifically for **Microsoft PowerPoint** (`Insert → 3D Models → This Device...`).

Key features built into `glibby`:
* **PowerPoint Skeletal Skinning (`skins` + `JOINTS_0`/`WEIGHTS_0`):** PowerPoint ignores standard node-transform animations in `.glb` files and only enables the 3D Play/Pause and `Scenes` controls for **bone-rigged (skeletal)** animations. `glibby` automatically rigs every atom and bond cylinder to a virtual armature with quaternion bone rotations and dynamic length/thickness scaling.
* **Single-Frame Stationary Support:** If the input `.xyz` contains only 1 frame, `glibby` automatically generates a stationary 3D `.glb` model with the exact same visual styling.
* **ChimeraX `SEQROW` Ball-Stick-Endcap Style:**
  * Heavy atoms ($\text{C}, \text{N}, \text{O}, \text{Fe}$, etc.) are rendered as smooth opaque spheres.
  * Hydrogen ($\text{H}$) atoms are rendered with a sphere radius equal to the covalent bond stick radius (`0.16 Å`), turning $\text{C–H}$ and $\text{N–H}$ bonds into capped stick tubes.
  * Metal–ligand coordination bonds (e.g. $\text{Fe–N}$) are rendered as thinner (`0.125 Å`) solid light-blue cylinders rather than split half-bonds.
  * Dynamic bonds that form or cleave during a trajectory smoothly taper in and out across the bond-breaking threshold.
* **Customizable Color Palettes:** Defaults to the **`zott`** palette (`N = RGB(0, 68, 134)`, `Fe = RGB(153, 119, 0)`, `C = RGB(143, 143, 143)`), with support for the standard `chimerax` palette or per-element `--color EL=R,G,B` overrides (automatically converted from sRGB `0..255` to linear glTF PBR color space).

## Dependencies
* **Python 3 (Standard Library Only):** `scripts/glibby_cli.py` uses 100% built-in Python standard library modules (`struct`, `math`, `json`, `argparse`, `os`, `sys`) with zero external package dependencies. Invoke via `uv run python` (if the `uv` skill is available) or system `python` / `python3`, resolving `scripts/glibby_cli.py` relative to this `SKILL.md` file's directory.

## Quick Start

### 1. Inspect the `.xyz` File First
Always run `inspect` first to check the frame count, elements present, and whether any dynamic/ambiguous bonds form or cleave across the trajectory (resolve `scripts/glibby_cli.py` relative to this skill directory):

```bash
python scripts/glibby_cli.py inspect \
  --input "path/to/trajectory.xyz" \
  --output "inspect_report.json"
```

> **Interactive Rule:** If `inspect_report.json` reports any `dynamic_bonds` (bonds that form or break across the trajectory) or ambiguous metal–ligand coordination bonds, **surface those bond pairs and distance ranges to the user and ask for confirmation** (along with whether they want the default `zott` palette or custom colors) before running `convert`.

> **Atomic-number rule:** If `inspect` or `convert` fails with `element is given as atomic number`, the file uses atomic numbers (e.g. `26`) instead of element symbols (`Fe`). **Ask the user whether they provided atomic numbers on purpose and want them converted to symbols.** Only if they confirm, re-run the same command with `--atomic-numbers-to-symbols`. Never add the flag without asking.

> **Input errors:** Any other parse error (truncated last frame, atom count or atom order changing between frames, non-numeric/`nan`/`inf` coordinates, invalid element symbols) means the file itself is malformed. Report the error message, which names the frame and line, to the user. Do not try to repair or skip frames yourself.

### 2. Convert `.xyz` to `.glb`
Run `convert` to produce the `.glb` file and a JSON conversion manifest:

```bash
python scripts/glibby_cli.py convert \
  --input "path/to/trajectory.xyz" \
  --glb-output "path/to/trajectory.glb" \
  --output "convert_manifest.json" \
  --palette zott
```

## Utility Scripts

### `scripts/glibby_cli.py`

#### `inspect` Subcommand
Parses an `.xyz` file and writes a JSON summary of frames, element counts, static bonds, and dynamic bonds.
* `--input` (required): Path to the input `.xyz` file.
* `--output` (required): Path to the output JSON inspection report.
* `--atomic-numbers-to-symbols` (optional): Convert atomic numbers in the element column to symbols. Only after the user confirms (see the atomic-number rule above).

#### `convert` Subcommand
Builds the `.glb` file and writes a JSON manifest to `--output`.
* `--input` (required): Path to the input `.xyz` file (1 frame for stationary 3D model, or $N>1$ frames for animated 3D trajectory).
* `--glb-output` (required): Path where the `.glb` file will be saved.
* `--output` (required): Path where the JSON conversion manifest will be saved.
* `--palette` (optional, default: `zott`): Choose `zott` (`N=0,68,134`, `Fe=153,119,0`, `C=143,143,143`) or `chimerax` (standard ChimeraX CPK colors).
* `--color` (optional, repeatable): Custom sRGB `0..255` override for any element symbol or `CoordBond`, e.g.:
  ```bash
  --color N=0,68,134 --color Fe=153,119,0 --color CoordBond=135,175,235
  ```
* `--fps` (optional, default: `12.0`): Playback frame rate for multi-frame animations.
* `--loop-mode` (optional, default: `auto`):
  * `auto`: Uses `cycle` if Frame 0 and Frame $N-1$ are within `0.05 Å` RMSD (e.g. a complete vibrational normal mode cycle), or `ping-pong` if they differ (e.g. a one-way IRC or relaxed scan).
  * `cycle`: Plays frames $0 \dots N-1$ directly.
  * `ping-pong`: Appends reversed frames $N-2 \dots 1$ for a seamless back-and-forth loop in PowerPoint.
* `--dynamic-bonds` (optional, default: `include`): `include` tapers forming/breaking bonds smoothly; `exclude` only renders bonds present in Frame 0.
* `--atomic-numbers-to-symbols` (optional): Same as for `inspect`; only after user confirmation.
* `--add-bond` / `--remove-bond` (optional, repeatable): Force-include or force-exclude specific 1-based atom pairs (e.g., `--add-bond 44-47` or `--remove-bond 42-44`).

## Input Format
* Standard multi-frame XYZ: atom count line, comment line (may be empty), then one `Element x y z` line per atom. Extra columns after `z` (charges, forces) are ignored.
* Element symbols are case-insensitive (`fe`, `FE` → `Fe`). Coordinates accept decimals, `1.2e-3` and Fortran `1.2D-3`. Windows line endings, tabs, and blank lines between frames are fine.
* Every frame must have the same atoms in the same order.
* Large molecules are supported. PowerPoint fails to import a skinned mesh with more than ~255 bones (one bone per atom plus one per bond; 235 imported, 259 failed in testing). glibby therefore exports single-frame files as plain meshes with no bones, and splits animated models with more than 200 bones into several skinned meshes of at most 200 bones each. Meshes are also chunked to at most 65,535 vertices so every index stays 16-bit.

## Common Mistakes
1. **Dragging and dropping `.glb` into PowerPoint:** Dragging a `.glb` file from a file manager onto a slide can bypass PowerPoint's 3D animation loader. Always instruct the user to insert via **Insert → 3D Models → This Device...**.
2. **Using raw sRGB values in glTF `baseColorFactor`:** glTF 2.0 requires **linear RGB** floats (`0.0–1.0`). Passing `c / 255.0` directly without sRGB-to-linear gamma conversion (`((c/255 + 0.055)/1.055)**2.4`) makes colors look washed out in PowerPoint. `glibby_cli.py` handles this conversion automatically.
3. **Inside-out triangle winding:** Reversed triangle winding (`CW` instead of `CCW`) causes PowerPoint's back-face culling to hide front faces, making spheres look hollow or transparent. `glibby_cli.py` enforces strict outward `CCW` winding and `"alphaMode": "OPAQUE"`.
