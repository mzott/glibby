# CLI reference

`skill/glibby/scripts/glibby_cli.py` is a single Python file that uses only the standard library. It needs Python 3.8 or newer and nothing else.

```bash
python skill/glibby/scripts/glibby_cli.py <command> [options]
```

There are two commands: `inspect` to check a file, and `convert` to make the `.glb`. On success both print `Success! Data written to: <path>`. On failure they print `Error: <message>` to stderr and exit with status 1.

## `inspect`

Reads an `.xyz` file and writes a JSON report about it, without making a model. Run this first to see which bonds form or break.

```bash
python glibby_cli.py inspect --input traj.xyz --output report.json
```

| Option | Required | Description |
|---|---|---|
| `--input PATH` | yes | The `.xyz` file. |
| `--output PATH` | yes | Where to write the JSON report. |
| `--atomic-numbers-to-symbols` | no | Read numbers in the element column (`26`) as elements (`Fe`). Without it, atomic numbers are an error. |

Example report:

```json
{
  "input_xyz": "/path/to/traj.xyz",
  "frame_count": 27,
  "is_stationary": false,
  "atom_count": 2,
  "element_counts": { "H": 2 },
  "static_bond_count": 0,
  "dynamic_bond_count": 1,
  "dynamic_bonds": [
    {
      "atoms_1based": [1, 2],
      "labels": "H1-H2",
      "d_min_A": 0.74,
      "d_max_A": 3.0,
      "d_frame0_A": 0.74,
      "cutoff_A": 0.95,
      "type": "covalent"
    }
  ],
  "static_bonds": []
}
```

`type` is `covalent` or `coordination` (a bond to a metal). A bond is **dynamic** if it crosses its cutoff during the trajectory or its length changes by more than 0.35 Å.

## `convert`

Builds the `.glb` and writes a JSON manifest describing what was exported.

```bash
python glibby_cli.py convert --input traj.xyz --glb-output traj.glb --output manifest.json
```

| Option | Default | Description |
|---|---|---|
| `--input PATH` | required | The `.xyz` file. |
| `--glb-output PATH` | required | Where to write the `.glb`. |
| `--output PATH` | required | Where to write the JSON manifest. |
| `--palette {zott,chimerax}` | `zott` | Color preset. |
| `--color EL=R,G,B` | | Override one color, in 0–255 sRGB. Repeatable. Use `CoordBond` for metal–ligand bonds, e.g. `--color Fe=200,100,0 --color CoordBond=135,175,235`. |
| `--fps N` | `12` | Animation playback speed in frames per second. |
| `--loop-mode {auto,cycle,ping-pong}` | `auto` | `auto` uses `cycle` when the first and last frames match within 0.05 Å RMSD, otherwise `ping-pong`. `ping-pong` appends the frames in reverse (N−1 … 2) so the animation loops smoothly. |
| `--dynamic-bonds {include,exclude}` | `include` | `exclude` drops dynamic bonds that are not bonded in the first frame. |
| `--add-bond I-J` | | Force a bond between atoms I and J (1-based). Repeatable. |
| `--remove-bond I-J` | | Never draw a bond between atoms I and J (1-based). Repeatable. |
| `--atomic-numbers-to-symbols` | | Same as for `inspect`. |

The manifest records the input and output paths, file size, frame counts, the loop mode actually used, FPS, atom and bond counts, the palette, the final color of every element, and the dynamic bonds.

## Examples

Static structure with ChimeraX colors:

```bash
python glibby_cli.py convert --input opt.xyz --glb-output opt.glb --output m.json --palette chimerax
```

Vibrational mode at 20 FPS with a custom nitrogen color:

```bash
python glibby_cli.py convert --input mode7.xyz --glb-output mode7.glb --output m.json --fps 20 --color N=40,90,200
```

Reaction path where you want a hydrogen-bond contact (atoms 12 and 30) drawn and a spurious bond (atoms 3 and 9) hidden:

```bash
python glibby_cli.py convert --input irc.xyz --glb-output irc.glb --output m.json --add-bond 12-30 --remove-bond 3-9
```

## Using it as a Claude skill

Copy `skill/glibby/` into your skills folder (for Claude Code, `~/.claude/skills/glibby/`). Then ask Claude to convert an `.xyz` file for PowerPoint. The skill tells Claude to run `inspect` first, show you any forming or breaking bonds, and ask before converting atomic numbers.
