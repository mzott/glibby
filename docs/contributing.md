# Contributing

## Layout

```
glibby.html                          web page (self-contained, no dependencies)
skill/glibby/SKILL.md                Claude skill instructions
skill/glibby/scripts/glibby_cli.py   command-line tool (Python standard library only)
examples/                            .xyz edge cases, named by expected outcome
examples/powerpoint_ready/           finished .glb files verified in PowerPoint
tests/check_examples.py              runs every example through the CLI
docs/                                documentation
```

## Keep the two implementations in sync

The web page and the CLI are separate implementations of the same pipeline: parsing, bond detection, geometry, bones and GLB writing. A change to one usually needs the same change in the other, including the element table (`ELEMENT_SPECS`).

## Testing

Run the example suite:

```bash
python tests/check_examples.py
```

Each file in `examples/` is named by what should happen:
- `valid_*` and `stress_*` must convert.
- `prompt_*` must stop and ask about atomic numbers.
- `error_*` must be rejected.

For the web page, drag the same files onto `glibby.html` and check that the outcome matches.

To add an edge case, add a small `.xyz` with the right prefix and a name that says what it tests.

## Changes that affect PowerPoint

PowerPoint's 3D import is undocumented and stricter than other viewers (see [How it works](how-it-works.md#powerpoint-limits-glibby-works-around)). If you change the GLB structure, check before merging:
1. The file passes the [Khronos glTF Validator](https://github.khronos.org/glTF-Validator/).
2. Both files in `examples/powerpoint_ready/`, re-exported with your change, import and play in desktop PowerPoint.

## License

By contributing you agree that your contributions are licensed under the MIT License.
