# Troubleshooting

## PowerPoint

**"An error occurred while importing this file."**
PowerPoint doesn't say why. Known causes:
1. **The file came from an old glibby version** that didn't handle large molecules. Re-export it with the current version, which works around PowerPoint's bone limit (see [How it works](how-it-works.md#powerpoint-limits-glibby-works-around)).
2. **A different limit.** To find out whether the file itself is broken, drop it on the [Khronos glTF Validator](https://github.khronos.org/glTF-Validator/) or open it in Windows 3D Viewer or Blender (File → Import → glTF 2.0). If those open it without errors, it's a PowerPoint limit. Please open an issue with the `.xyz` attached.

**The model imports but doesn't animate.**
- Check the **3D Model** tab: the **Scenes** dropdown should show *Reaction_Trajectory*. If it says *None*, select the scene.
- For slideshows, add the **Play 3D** effect from the **Animations** tab.
- Single-frame `.xyz` files are static by design.
- Insert with **Insert → 3D Models → This Device…**, not by dragging the file onto the slide.

**The animation stutters or PowerPoint is slow.**
Large molecules make big files: a 180-atom molecule is 3 MB static and 6 MB animated. Try fewer frames (every 2nd or 3rd frame of an MD run) or a lower FPS.

**Colors look different from the preview.**
The preview is a flat 2D drawing; PowerPoint lights the model in 3D, so colors shift with angle. The exported material colors match the values you picked.

## Input errors

| Message | Cause | Fix |
|---|---|---|
| `expected an atom count` | The first line of a frame isn't a whole number. | Check for a header or stray text before the first frame. |
| `Frame N ... is truncated` / `Truncated XYZ frame` | The file ends partway through a frame. | Re-export the trajectory, or delete the incomplete last frame. |
| `Frame N has X atoms but frame 1 has Y` | Atom count changes. | Every frame must contain the same atoms. |
| `atom K is El1 but in frame 1 it is El2` / `Atom order differs` | Atoms were reordered between frames. | Re-export with a fixed atom order. |
| `coordinate "..." is not a number` | A coordinate is text, `nan` or `inf`. | Usually a failed calculation step; remove that frame. |
| `expected "Element x y z"` / `Malformed atom line` | A line has fewer than four columns, or a blank line inside a frame. | Fix or delete that line. |
| `is not an element symbol` | The element column has something like `H1` or `C_a`. | Use plain symbols. |
| `element is given as atomic number` | The element column has numbers. | Confirm the conversion (web button, or `--atomic-numbers-to-symbols`). |

## Bonds look wrong

- **A bond is missing:** atoms are farther apart than the cutoff in every frame. Force it with `--add-bond I-J`.
- **An extra bond appears:** two atoms come closer than the cutoff in some frame. Hide it with `--remove-bond I-J`, or untick it in the web page's dynamic-bond list.
- **A forming/breaking bond is distracting:** use `--dynamic-bonds exclude` or untick it.
- **An element shows up magenta:** it's not in glibby's color table. Set a color with `--color El=R,G,B` or the color picker.
