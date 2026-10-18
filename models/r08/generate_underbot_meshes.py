"""Compatibility entry point for rebuilding the current Underbot package.

Requires Python 3 and NumPy. Regenerate validation evidence after changing the
model; the published ZIP is a snapshot, not automatically rebuilt here.
"""
from pathlib import Path
import runpy
import xml.etree.ElementTree as ET

root = Path(__file__).resolve().parent
package = root / "underbot_description"
for script in ("generate_model.py", "prepare_simulation.py", "build_viewer.py"):
    runpy.run_path(str(package / "scripts" / script), run_name="__main__")
for name in ("underbot_flat.urdf", "underbot_standalone.urdf"):
    robot = ET.parse(package / "urdf/underbot.portable.urdf").getroot()
    for mesh in robot.findall(".//mesh"):
        asset = (package / "urdf" / mesh.get("filename")).resolve()
        mesh.set("filename", asset.relative_to(root).as_posix())
    ET.indent(robot, space="  ")
    (root / name).write_bytes(ET.tostring(robot, encoding="utf-8", xml_declaration=True) + b"\n")
