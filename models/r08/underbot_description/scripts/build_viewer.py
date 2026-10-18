#!/usr/bin/env python3
"""Generate a self-contained WebGL inspector from actual URDF/STL assets."""
import base64
import hashlib
import json
import math
from pathlib import Path
import xml.etree.ElementTree as ET


ROOT = Path(__file__).resolve().parents[1]
PASSIVE_JOINTS = {"caster_swivel_joint", "caster_wheel_joint"}
REVISION = "R08"


def replace_once(template, original, replacement):
    """Fail explicitly if a required template token is missing or duplicated."""
    if template.count(original) != 1:
        raise ValueError(f"Expected one template occurrence: {original[:70]}")
    return template.replace(original, replacement)


def current_template(template, data):
    independent = [j for j in data["joints"] if j["type"] != "fixed" and not j["mimic"]]
    passive = sum(j["passive"] for j in independent)
    actuated = len(independent) - passive
    changes = [
        ("__TITLE_REVISION__", data["revision"]),
        ("__OVERLAY_REVISION__", data["revision"]),
        ("__JOINT_INTRO__",
         f"Inspect {actuated} actuated joints and {passive} passive caster coordinates. The caster sliders inspect free joint motion; they are not motor commands. Both gripper followers use the URDF mimic relationship."),
        ("__TOPOLOGY__",
         f"{len(data['links'])} links · {len(data['joints'])} joints · {actuated} actuated + {passive} passive"),
        ("__PACKAGING_NOTE__", "Frame and floors: 200 × 200 mm. Outside 2 mm covers give a 204 × 204 mm covered body; hinges and arm mounts extend beyond it. Clear opening between 20 mm posts: 160 × 160 mm. The Kinect case is removed. Its bare electronics and optical frame are uncalibrated reservations that need measurement after disassembly."),
    ]
    for original, replacement in changes:
        template = replace_once(template, original, replacement)
    return template


def vector(element, name, default):
    return [float(value) for value in (element.attrib.get(name, default) if element is not None else default).split()]


def transform(element):
    return {"xyz": vector(element, "xyz", "0 0 0"), "rpy": vector(element, "rpy", "0 0 0")}


def main():
    urdf = ROOT / "urdf" / "underbot.portable.urdf"
    robot = ET.parse(urdf).getroot()
    materials = {item.attrib["name"]: vector(item.find("color"), "rgba", "0.6 0.6 0.6 1") for item in robot.findall("material")}
    mesh_data = {}
    visuals, collisions, joints = [], [], []
    for link in robot.findall("link"):
        name = link.attrib["name"]
        for visual in link.findall("visual"):
            mesh = visual.find("geometry/mesh")
            if mesh is None:
                raise ValueError("Expected STL visual geometry")
            path = (urdf.parent / mesh.attrib["filename"]).resolve()
            key = path.relative_to(ROOT).as_posix()
            if key not in mesh_data:
                mesh_data[key] = base64.b64encode(path.read_bytes()).decode("ascii")
            mat = visual.find("material")
            color = materials.get(mat.attrib.get("name", ""), [.6, .6, .6, 1]) if mat is not None else [.6, .6, .6, 1]
            if mat is not None and mat.find("color") is not None:
                color = vector(mat.find("color"), "rgba", "0.6 0.6 0.6 1")
            visuals.append({"link": name, "mesh": key, "color": color,
                            "scale": vector(mesh, "scale", "1 1 1"), **transform(visual.find("origin"))})
        for collision in link.findall("collision"):
            geometry = collision.find("geometry")
            shape = list(geometry)[0]
            size = vector(shape, "size", "1 1 1") if shape.tag == "box" else (
                [float(shape.attrib["radius"]), float(shape.attrib["length"])] if shape.tag == "cylinder" else [float(shape.attrib["radius"])])
            collisions.append({"link": name, "kind": shape.tag, "size": size, **transform(collision.find("origin"))})
    for joint in robot.findall("joint"):
        limit, mimic = joint.find("limit"), joint.find("mimic")
        joints.append({"name": joint.attrib["name"], "type": joint.attrib["type"],
                       "parent": joint.find("parent").attrib["link"], "child": joint.find("child").attrib["link"],
                       **transform(joint.find("origin")), "axis": vector(joint.find("axis"), "xyz", "0 0 1"),
                       "lower": -math.pi if joint.attrib["type"] == "continuous" else (float(limit.attrib.get("lower", -math.pi)) if limit is not None else 0),
                       "upper": math.pi if joint.attrib["type"] == "continuous" else (float(limit.attrib.get("upper", math.pi)) if limit is not None else 0),
                       "passive": joint.attrib["name"] in PASSIVE_JOINTS,
                       "mimic": {"joint": mimic.attrib["joint"], "multiplier": float(mimic.attrib.get("multiplier", 1)),
                                 "offset": float(mimic.attrib.get("offset", 0))} if mimic is not None else None})
    data = {"revision": REVISION, "base_model": "Worx Landroid M500 WR141E",
            "camera_status": "Uncalibrated bare Kinect electronics reservation; external case removed",
            "packaging": {"frame_and_floor_m": [0.2, 0.2], "covered_body_m": [0.204, 0.204],
                          "clear_post_opening_m": [0.16, 0.16]},
            "urdf_sha256": hashlib.sha256(urdf.read_bytes()).hexdigest(),
            "meshes": mesh_data, "visuals": visuals, "collisions": collisions, "joints": joints,
            "links": [item.attrib["name"] for item in robot.findall("link")]}
    template = Path(__file__).with_name("viewer_template.html").read_text(encoding="utf-8")
    template = current_template(template, data)
    (ROOT / "viewer.html").write_text(template.replace("__UNDERBOT_MODEL_DATA__", json.dumps(data, separators=(",", ":"))), encoding="utf-8")
    print(f"Built viewer.html: {len(mesh_data)} actual STL meshes, {len(visuals)} visuals, {len(collisions)} collision shapes")


if __name__ == "__main__":
    main()
