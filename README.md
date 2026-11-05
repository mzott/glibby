# glibby

Turn `.xyz` molecular structures and trajectories into 3D `.glb` models you can insert into Microsoft PowerPoint, with play/pause animation.

- **Single frame** → a static 3D molecule.
- **Multiple frames** (vibrational modes, reaction paths, IRC scans, MD) → an animated, bone-rigged model that PowerPoint can play.

In PowerPoint, insert the file with **Insert → 3D Models → This Device…** (dragging the file onto a slide can skip the animation).

## Two ways to use it

### 1. Offline Web page: `glibby.html`
Open `glibby.html` in any browser. It opens with a built-in demo (an iron complex vibrating along an N–N coupling mode). No install and no internet needed; your files never leave your computer.
Drop in an `.xyz` file, preview it, adjust colors and bonds, and click **Download PowerPoint .glb**.

### 2. Claude skill: `skill/glibby/`
A skill for Claude (Claude Code, Claude.ai) with a pure-Python CLI (standard library only, Python 3.8+).
Install by copying `skill/glibby/` into your skills folder (for Claude Code: `~/.claude/skills/glibby/`), then ask Claude to "convert this xyz to a PowerPoint glb".

You can also run the CLI directly:

```bash
python skill/glibby/scripts/glibby_cli.py inspect --input examples/valid_h2_bond_forming_breaking.xyz --output report.json
```

```bash
python skill/glibby/scripts/glibby_cli.py convert --input examples/valid_h2_bond_forming_breaking.xyz --glb-output h2.glb --output manifest.json
```

## Input format

Standard (multi-frame) XYZ: an atom-count line, a comment line (may be empty), then `Element x y z` per atom.

| Accepted | Rejected with a message naming the frame and line |
|---|---|
| Windows or Unix line endings, tabs | Last frame cut off or missing atoms |
| Empty comment lines; blank lines between frames | Atom count or atom order changing between frames |
| Extra columns after `z` (charges, forces) | Non-numeric, `nan` or `inf` coordinates |
| `1.2e-3` and Fortran `1.2D-3` numbers | Invalid element symbols |
| Lowercase/uppercase symbols (`fe`, `FE` → `Fe`) | Blank line inside a frame |
| Huge molecules (see below) | |

**Atomic numbers** (`26` instead of `Fe`) are not converted silently. The web page shows a **Convert atomic numbers to symbols** button; the CLI stops and asks you to re-run with `--atomic-numbers-to-symbols`.

## Large molecules and PowerPoint

Animated models move each atom and bond with an invisible "bone" (one per atom plus one per bond). PowerPoint refuses to import a model whose mesh uses more than about 255 bones (in testing, 235 imported and 259 failed). glibby handles this automatically:

- **Single-frame files** are exported with no bones at all, so any size works.
- **Animated files** with more than 200 bones are split into several meshes of at most 200 bones each. They look and play the same.
Have a large molecule that didn't work properly? Submit an issue.

## Examples and tests

`examples/` has one small file per edge case, mostly an H₂ molecule stretching from 0.74 Å to 3.0 Å and back, so the H–H bond breaks and re-forms. The filename says what should happen:

- `valid_*`: loads and exports.
- `prompt_*`: asks before converting atomic numbers.
- `error_*`: refused with a clear error.
- `stress_*`: large molecules. A 180-carbon (10,0) carbon nanotube, static and with an animated radial breathing mode (about 3 MB static, 6 MB animated). They exceed PowerPoint's bone limit, which glibby works around automatically.

`examples/powerpoint_ready/` has two finished `.glb` files made from the nanotube examples, both confirmed to import and play in PowerPoint. Insert one to see what glibby produces without running anything. If these don't work on your PowerPoint, let me know via an issue.

Check the CLI against all of them:

```bash
python tests/check_examples.py
```

For the web page, drag each example onto `glibby.html`.

## Documentation

- [User guide](docs/user-guide.md): making a model with the web page and presenting it in PowerPoint.
- [CLI reference](docs/cli-reference.md): every command and option.
- [How it works](docs/how-it-works.md): input rules, bond detection, styling, bones and PowerPoint limits.
- [Troubleshooting](docs/troubleshooting.md): import errors, input errors and bond fixes.
- [Contributing](docs/contributing.md): layout, tests, and keeping the two versions in sync.

## License

MIT. See [LICENSE](LICENSE).
