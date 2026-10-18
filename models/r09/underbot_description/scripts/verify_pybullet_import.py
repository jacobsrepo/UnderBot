"""Import the delivered URDF, independently compare FK, and inspect real mesh bounds."""
from pathlib import Path
import hashlib
import importlib.metadata
import json
import math
import sys
import xml.etree.ElementTree as ET

WORKSPACE = Path(__file__).resolve().parents[1]
import numpy as np
import pybullet as p

PKG = Path(__file__).resolve().parents[1]
URDF = PKG / "urdf/underbot.portable.urdf"
VALIDATION = PKG / "validation"
PASSIVE = {"caster_swivel_joint", "caster_wheel_joint"}


def xyz(text="0 0 0"):
    return np.asarray([float(v) for v in text.split()])


def transform(element):
    result = np.eye(4)
    if element is None:
        return result
    roll, pitch, yaw = xyz(element.get("rpy", "0 0 0"))
    cr, sr, cp, sp, cy, sy = math.cos(roll), math.sin(roll), math.cos(pitch), math.sin(pitch), math.cos(yaw), math.sin(yaw)
    result[:3, :3] = [[cy*cp, cy*sp*sr-sy*cr, cy*sp*cr+sy*sr],
                     [sy*cp, sy*sp*sr+cy*cr, sy*sp*cr-cy*sr], [-sp, cp*sr, cp*cr]]
    result[:3, 3] = xyz(element.get("xyz", "0 0 0"))
    return result


def quat_transform(position, orientation):
    result = np.eye(4)
    result[:3, :3] = np.asarray(p.getMatrixFromQuaternion(orientation)).reshape(3, 3)
    result[:3, 3] = position
    return result


def axis_rotation(axis, value):
    axis = axis / np.linalg.norm(axis)
    x, y, z = axis
    cross = np.asarray([[0, -z, y], [z, 0, -x], [-y, x, 0]])
    result = np.eye(4)
    result[:3, :3] = np.eye(3) + math.sin(value)*cross + (1-math.cos(value))*(cross@cross)
    return result


def main():
    xml = ET.parse(URDF).getroot()
    joint_xml = {j.get("name"): j for j in xml.findall("joint")}
    link_xml = {l.get("name"): l for l in xml.findall("link")}
    child_joint = {j.find("child").get("link"): j for j in joint_xml.values()}
    independent = [j for j in joint_xml.values() if j.get("type") != "fixed" and j.find("mimic") is None]
    mimic_names = [j.get("name") for j in joint_xml.values() if j.find("mimic") is not None]
    client = p.connect(p.DIRECT)
    robot = p.loadURDF(str(URDF), basePosition=[0, 0, 0], useFixedBase=False,
                       flags=p.URDF_USE_INERTIA_FROM_FILE, physicsClientId=client)
    indices = {p.getJointInfo(robot, i)[1].decode(): i for i in range(p.getNumJoints(robot))}
    assert len(indices) == len(joint_xml) == 22
    assert len(link_xml) == 23 and len(independent) == 16
    assert len(set(j.get("name") for j in independent) - PASSIVE) == 14
    base_dynamics = p.getDynamicsInfo(robot, -1)
    assert base_dynamics[0] > 0, "The mobile base must be floating with nonzero mass"
    root_pose = quat_transform(*p.getBasePositionAndOrientation(robot)) @ np.linalg.inv(quat_transform(base_dynamics[3], base_dynamics[4]))
    assert np.max(np.abs(root_pose - np.eye(4))) < 1e-10
    values = {}
    for index, joint in enumerate(independent):
        if joint.get("type") == "continuous":
            value = .23 if index % 2 else -.31
        else:
            limit = joint.find("limit")
            lower, upper = float(limit.get("lower")), float(limit.get("upper"))
            value = lower + (.61 if index % 2 else .37)*(upper-lower)
        values[joint.get("name")] = value
    inspected_pose = dict(values)

    def joint_value(joint):
        mimic = joint.find("mimic")
        if mimic is not None:
            return joint_value(joint_xml[mimic.get("joint")])*float(mimic.get("multiplier", 1)) + float(mimic.get("offset", 0))
        return values.get(joint.get("name"), 0)

    for name, joint in joint_xml.items():
        if joint.get("type") != "fixed":
            p.resetJointState(robot, indices[name], joint_value(joint))
    matrices = {"base_link": root_pose}

    def fk(name):
        if name in matrices:
            return matrices[name]
        joint = child_joint[name]
        axis = xyz(joint.find("axis").get("xyz", "0 0 1")) if joint.find("axis") is not None else xyz("0 0 1")
        motion = axis_rotation(axis, joint_value(joint)) if joint.get("type") in ("revolute", "continuous") else np.eye(4)
        matrices[name] = fk(joint.find("parent").get("link")) @ transform(joint.find("origin")) @ motion
        return matrices[name]

    comparisons = []
    imported_frames = {"base_link": root_pose.tolist()}
    for name, index in indices.items():
        link_name = joint_xml[name].find("child").get("link")
        expected = fk(link_name)
        state = p.getLinkState(robot, index, computeForwardKinematics=True)
        actual = quat_transform(state[4], state[5])
        imported_frames[link_name] = actual.tolist()
        comparisons.append({"link": link_name,
                            "position_error_m": float(np.linalg.norm(actual[:3, 3]-expected[:3, 3])),
                            "rotation_matrix_max_error": float(np.max(np.abs(actual[:3, :3]-expected[:3, :3])))})
    maximum_position = max(item["position_error_m"] for item in comparisons)
    maximum_rotation = max(item["rotation_matrix_max_error"] for item in comparisons)
    assert maximum_position < 2e-6 and maximum_rotation < 2e-6
    dynamics = [p.getDynamicsInfo(robot, i) for i in range(-1, p.getNumJoints(robot))]
    assert all(d[0] >= 0 and np.isfinite(d[0]) and all(v >= 0 and np.isfinite(v) for v in d[2]) for d in dynamics)
    urdf_mass = sum(float(l.find("inertial/mass").get("value")) for l in link_xml.values() if l.find("inertial/mass") is not None)
    imported_mass = sum(d[0] for d in dynamics)
    assert abs(urdf_mass-imported_mass) < 1e-8

    # Inspect the delivered zero pose, without advancing physics or fixing the root.
    values.clear()
    for name, joint in joint_xml.items():
        if joint.get("type") != "fixed":
            p.resetJointState(robot, indices[name], 0)
    matrices.clear()
    matrices["base_link"] = root_pose
    mesh_hashes = {}
    bounds = []
    for name, link in link_xml.items():
        for visual in link.findall("visual"):
            mesh = visual.find("geometry/mesh")
            path = (URDF.parent / mesh.get("filename")).resolve()
            raw = path.read_bytes()
            mesh_hashes[path.relative_to(PKG).as_posix()] = hashlib.sha256(raw).hexdigest()
            count = int.from_bytes(raw[80:84], "little")
            records = np.ndarray((count,), dtype=np.dtype([("normal", "<f4", 3), ("vertices", "<f4", (3, 3)), ("attribute", "<u2")]), buffer=raw, offset=84)
            vertices = records["vertices"].reshape(-1, 3).astype(float) * xyz(mesh.get("scale", "1 1 1"))
            world = fk(name) @ transform(visual.find("origin"))
            vertices = vertices @ world[:3, :3].T + world[:3, 3]
            bounds.extend([vertices.min(axis=0), vertices.max(axis=0)])
    lower, upper = np.asarray(bounds).min(axis=0), np.asarray(bounds).max(axis=0)
    report = {"revision": "R09", "camera_status": "External case removed; bare Kinect electronics and optical frame are uncalibrated reservations.", "engine": "PyBullet", "engine_version": importlib.metadata.version("pybullet"), "engine_api_version": p.getAPIVersion(),
              "urdf": "urdf/underbot.portable.urdf", "urdf_sha256": hashlib.sha256(URDF.read_bytes()).hexdigest(),
              "flags": "URDF_USE_INERTIA_FROM_FILE", "use_fixed_base": False,
              "links": len(link_xml), "joints": len(joint_xml), "actuated_independent_joints": 14,
              "passive_independent_joints": sorted(PASSIVE), "mimic_followers": mimic_names,
              "mimic_handling": "PyBullet does not enforce URDF mimic constraints here; follower positions were explicitly set from the URDF equations for the nonzero FK check.",
              "nonzero_independent_pose_radians": inspected_pose,
              "nonzero_pose_world_link_frames": imported_frames,
              "maximum_position_error_m": maximum_position, "maximum_rotation_matrix_error": maximum_rotation,
              "fk_link_comparisons": comparisons, "urdf_mass_kg": urdf_mass, "imported_mass_kg": imported_mass,
              "zero_pose_visual_aabb_m": {"minimum": lower.tolist(), "maximum": upper.tolist()},
              "mesh_sha256": mesh_hashes,
              "status": "PASS", "scope": "Actual-file import, floating-root configuration, preserved masses, nonzero forward kinematics, zero-pose actual mesh bounds. This is not a dynamic stability or actuator validation, and does not execute ROS, Gazebo, Isaac Sim, or Isaac Lab."}
    VALIDATION.mkdir(exist_ok=True)
    (VALIDATION / "pybullet_import_R09.json").write_text(json.dumps(report, indent=2)+"\n", encoding="utf-8")
    (VALIDATION / "pybullet_import_R09.md").write_text(
        f"# R09 actual-URDF PyBullet inspection\n\nPASS: imported `underbot.portable.urdf` with `URDF_USE_INERTIA_FROM_FILE` and a floating base. "
        f"The import contains {len(link_xml)} links and {len(joint_xml)} joints, with 14 actuated and two passive independent coordinates. "
        f"Imported mass {imported_mass:.9f} kg matches the URDF sum.\n\n"
        f"At an independently selected nonzero pose, all 22 child link frames agree with separate URDF forward kinematics: "
        f"maximum position error {maximum_position:.3g} m; maximum rotation-matrix element error {maximum_rotation:.3g}. "
        "Mimic follower positions were explicitly calculated from the URDF equations because this PyBullet load does not implement a mimic actuator constraint.\n\n"
        "This check does not establish dynamic stability, measured hardware accuracy, or native ROS/Gazebo/Isaac compatibility. "
        "Exact source and asset hashes are recorded in the adjacent JSON.\n", encoding="utf-8")
    p.disconnect(client)
    print(json.dumps({"status": "PASS", "maximum_position_error_m": maximum_position,
                      "maximum_rotation_matrix_error": maximum_rotation, "mass_kg": imported_mass}, indent=2))


if __name__ == "__main__":
    main()
