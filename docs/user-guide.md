# User guide

This guide walks through making a 3D molecule for PowerPoint with the web page, then using it in a presentation. For the command-line tool, see the [CLI reference](cli-reference.md).

## 1. Prepare an `.xyz` file

glibby reads standard XYZ files, the format most quantum chemistry and MD programs can write (ORCA, Gaussian via conversion, CP2K, ASE, Avogadro, ChimeraX, and others).

- **One frame** gives a static molecule.
- **Several frames** give an animation: a vibrational mode, an IRC or relaxed scan, a nudged elastic band path, or an MD trajectory.

Every frame must contain the same atoms in the same order. See [Input format](how-it-works.md#input-format) for the exact rules.

## 2. Open the web page

Open `glibby.html` in any modern browser (Chrome, Edge, Firefox, Safari). It works offline, and your files never leave your computer.

The page opens with a built-in demo: an iron complex vibrating along an N–N coupling mode.

## 3. Load your file

Click the drop zone or drag a file onto it. The page shows:

- **File summary:** frame count, atom count, total bonds, and how many are dynamic.
- **3D preview:** drag to rotate, scroll to zoom. Use **Pause** and the **Timeline** slider to step through frames.

If the file has a problem, a red box explains what is wrong and on which line. If the file uses atomic numbers (`26`) instead of element symbols (`Fe`), the box asks whether that was intended and offers a **Convert atomic numbers to symbols** button.

## 4. Adjust the look

**Colors.** Pick a palette:
- **Zott** (default): a muted scheme with dark-blue nitrogen and gold iron.
- **ChimeraX CPK:** the standard ChimeraX element colors.

Every element in your file gets its own color picker, plus **M–L Coord** for metal–ligand bonds. Changing the palette resets custom colors.

**Animation.**
- **Loop mode:**
  - *Auto-detect* plays a full cycle if the first and last frames match (a complete vibration), and otherwise plays forward then backward (ping-pong).
  - *Direct cycle* always plays 1 → N.
  - *Ping-pong* always plays 1 → N → 1.
- **Speed (FPS):** 4 to 30 frames per second. This is baked into the exported file.

**Dynamic bonds.** Bonds that form or break during the trajectory are listed with their distance range. They fade in and out as they form and break. Untick a bond to leave it out of the preview and the export.

## 5. Export

Click **Download PowerPoint .glb**. The file is named after your `.xyz` file.

## 6. Insert into PowerPoint

1. In PowerPoint, choose **Insert → 3D Models → This Device…** and pick the `.glb` file.
   Use this menu rather than dragging the file onto the slide; dragging can skip PowerPoint's animation loader.
2. Rotate the model with the 3D handle in its center, and resize it from the corners.
3. For animated models, the **3D Model** tab shows **Play 3D** and **Scenes**. glibby's animation appears as a single scene named *Reaction_Trajectory*.
4. To play during a slideshow, select the model, go to **Animations**, and choose the **Play 3D** effect. Set it to start *With Previous* and repeat *Until End of Slide* for a looping animation.

PowerPoint for Windows and Mac (Microsoft 365) both support 3D models. Some older or web versions of PowerPoint show a still image instead of the 3D model.

## Ready-made examples

`examples/powerpoint_ready/` has two finished files, a static and an animated carbon nanotube. Insert one to see the result before making your own.
