# FreeCAD reconstruction source

`build_underbot.FCMacro` constructs native boxes, cylinders, spheres and concave extrusion and polygon-prism solids from `../config/geometry_manifest.json`. It creates one named `App::Part` container per URDF link, with visual components and, for GUI runs, hidden collision proxies. Headless runs omit proxies because no view visibility state can be set. Joint command zero is assembled using the same origin transforms as the URDF. Link placements remain separate from component-local placements.

The macro is supplied as source. **FreeCAD was unavailable in the authoring environment, so it has not been executed and no `.FCStd` or STEP file is claimed as generated.** It requires only FreeCAD's built-in Part module, with no external URDF workbench. Primitive and extrusion authoring follow the [official FreeCAD Part scripting documentation](https://github.com/FreeCAD/FreeCAD-documentation-docusaurus/blob/Stable/docs/python-scripting/part-scripting.md).

Open the saved macro through FreeCAD's **Macro → Macros** dialog and execute it. Keep it in this package's `cad` directory so it can find the geometry manifest. It will open a new document and save `cad/underbot_R08_WR141E.FCStd`. To additionally export the complete assembled STEP, set `UNDERBOT_EXPORT_STEP=1` before running the macro. Existing open documents are not closed.

From FreeCAD's Python console, an explicit path can be supplied as follows:

```python
macro_path = r"C:\path\underbot_description\cad\build_underbot.FCMacro"
exec(compile(open(macro_path, encoding="utf-8").read(), macro_path, "exec"), {"__file__": macro_path})
```

Source units are metres and native CAD units are millimetres. Shapes and translations are multiplied by 1000 exactly once; rotations remain radians until converted into rotation matrices. The optional STEP is an assembled CAD export in millimetres. **Do not replace URDF meshes with a world-pose STEP or an unscaled FreeCAD STL export.** The delivered URDF STL visuals are already in link-local coordinates and metres. This macro intentionally does not export STL, avoiding an ambiguous CAD exporter unit conversion.

Visual extrusion profiles, servo brackets, sensor housings, hardware and mass assignments remain the same explicit approximations as the URDF. Native solid volume is not a substitute for the assigned installed mass. To change authoritative dimensions, update the model inputs and regenerate the manifest before rerunning the macro.
