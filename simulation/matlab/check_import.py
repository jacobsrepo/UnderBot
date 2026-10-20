"""Compare the saved MATLAB block inventory with the original R09 URDF."""
import hashlib
import json
import math
from pathlib import Path
import xml.etree.ElementTree as ET


def vector(text):
    return [float(x) for x in text.strip("[]").replace(",", " ").split()]


def equal(actual, expected):
    assert len(actual) == len(expected)
    assert all(math.isclose(a, b, rel_tol=1e-10, abs_tol=1e-12)
               for a, b in zip(actual, expected)), (actual, expected)


def main():
    here = Path(__file__).resolve().parent
    source = here.parents[1] / "models/r09/underbot_description/urdf/underbot.portable.urdf"
    robot = ET.parse(source).getroot()
    blocks = json.loads((here / "generated/imported_blocks.json").read_text())
    by_path = {b["path"].split("/", 1)[1]: b for b in blocks}
    visuals = [b for b in blocks if b["reference"].endswith("/File Solid")]
    assert len(visuals) == len(robot.findall(".//visual/geometry/mesh"))
    for block in visuals:
        params = block["parameters"]
        assert params["InertiaType"] == "Custom" and float(params["Mass"]) == 0
        equal(vector(params["MomentsOfInertia"]), [0, 0, 0])
        equal(vector(params["ProductsOfInertia"]), [0, 0, 0])
        assert params["ExtGeomFileUnits"] == "m"
        mesh = source.parent.parent / "meshes" / params["ExtGeomFileName"]
        assert mesh.is_file(), mesh
    mass = 0.0
    for link in robot.findall("link"):
        inertial = link.find("inertial")
        params = by_path[f"{link.attrib['name']}/Inertia"]["parameters"]
        expected_mass = float(inertial.find("mass").attrib["value"])
        equal([float(params["Mass"])], [expected_mass])
        assert params["MassUnits"] == "kg"
        mass += float(params["Mass"])
        tensor = inertial.find("inertia").attrib
        equal(vector(params["MomentsOfInertia"]), [float(tensor[x]) for x in ("ixx", "iyy", "izz")])
        equal(vector(params["ProductsOfInertia"]), [float(tensor[x]) for x in ("iyz", "ixz", "ixy")])
        origin = inertial.find("origin")
        transform = by_path[f"{link.attrib['name']}/InertiaOriginTransform"]["parameters"]
        equal(vector(transform["TranslationCartesianOffset"]), vector(origin.attrib.get("xyz", "0 0 0")))
        equal(vector(transform["RotationSequenceAngles"]), vector(origin.attrib.get("rpy", "0 0 0")))
        assert transform["RotationSequence"] == "XYZ" and transform["RotationSequenceAxes"] == "BaseAxes"
        assert transform["TranslationCartesianOffsetUnits"] == "m"
        assert transform["RotationSequenceAnglesUnits"] == "rad"
    followers = []
    for joint in robot.findall("joint"):
        block = by_path[joint.attrib["name"]]
        params = block["parameters"]
        fixed = joint.attrib["type"] == "fixed"
        assert block["reference"].endswith("Weld Joint" if fixed else "Revolute Joint")
        if fixed:
            continue
        assert params["TorqueActuationMode"] == "NoTorque"
        assert params["MotionActuationMode"] == "ComputedMotion"
        if joint.attrib["type"] == "revolute":
            limit = joint.find("limit").attrib
            for side in ("Lower", "Upper"):
                assert params[f"{side}LimitSpecify"] == "on"
                assert params[f"{side}LimitBoundUnits"] == "rad"
                equal([float(params[f"{side}LimitBound"])], [float(limit[side.lower()])])
        else:
            assert params["LowerLimitSpecify"] == params["UpperLimitSpecify"] == "off"
        if joint.find("mimic") is not None:
            followers.append(joint.attrib["name"])
    # The raw importer leaves all 18 rotational joints independent and unactuated.
    assert not any("/Constraints/" in b["reference"] for b in blocks)
    result = {
        "source_sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
        "imported_mass_kg": mass,
        "mass_inertia_and_com_match_source": True,
        "visual_mesh_count": len(visuals),
        "visual_meshes_resolve_in_metres_and_add_no_mass": True,
        "all_22_joint_types_match_source": True,
        "all_revolute_limits_match_source": True,
        "all_rotational_joints_passive": True,
        "mimic_coupling_imported": False,
        "uncoupled_followers": followers,
        "scope": "Raw fixed-base import. Gripper coupling, ground contact and actuators are not implemented.",
    }
    (here / "generated/import_audit.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
