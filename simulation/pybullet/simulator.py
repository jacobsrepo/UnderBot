"""R09 fixed-base dynamics, interactive joint controls, and source import audit."""
import argparse
import hashlib
import json
import math
from pathlib import Path
import time
import xml.etree.ElementTree as ET

import numpy as np
import pybullet as p
from pybullet_utils.bullet_client import BulletClient

SOURCE = Path(__file__).resolve().parents[2] / 'models/r09/underbot_description/urdf/underbot.portable.urdf'
DT = 1 / 240
INTEGRATION_STEPS = 100


def vector(text='0 0 0'):
    return np.array([float(x) for x in text.split()])


def rotation(rpy):
    return np.array(p.getMatrixFromQuaternion(p.getQuaternionFromEuler(rpy))).reshape(3, 3)


def tensor(element):
    a = element.attrib
    return np.array([[float(a['ixx']), float(a['ixy']), float(a['ixz'])],
                     [float(a['ixy']), float(a['iyy']), float(a['iyz'])],
                     [float(a['ixz']), float(a['iyz']), float(a['izz'])]])


class Simulation:
    def __init__(self, gui=False, source=SOURCE):
        self.source = Path(source).resolve()
        self.xml = ET.parse(self.source).getroot()
        self.client = BulletClient(connection_mode=p.GUI if gui else p.DIRECT)
        try:
            self.client.setGravity(0, 0, -9.81)
            # Small inertias plus source viscous damping make the system stiff.
            # Call the engine at the smaller timestep: its numSubSteps option
            # alone does not recompute damping forces at every internal step.
            self.client.setTimeStep(DT / INTEGRATION_STEPS)
            self.client.setPhysicsEngineParameter(numSolverIterations=200)
            self.body = self.client.loadURDF(str(self.source), useFixedBase=True,
                                            flags=p.URDF_USE_INERTIA_FROM_FILE)
            self.joints = {self.client.getJointInfo(self.body, i)[1].decode(): i
                           for i in range(self.client.getNumJoints(self.body))}
            self.elements = {e.attrib['name']: e for e in self.xml.findall('joint')}
            self.movable = [n for n, e in self.elements.items() if e.attrib['type'] != 'fixed']
            self.followers = {}
            for name in self.movable:
                self.client.setJointMotorControl2(self.body, self.joints[name], p.VELOCITY_CONTROL, force=0)
                mimic = self.elements[name].find('mimic')
                if mimic is not None:
                    multiplier = float(mimic.get('multiplier', '1'))
                    offset = float(mimic.get('offset', '0'))
                    if multiplier != 1 or offset != 0:
                        raise ValueError('This R09 simulator supports only 1:1, zero-offset mimic joints')
                    leader = mimic.attrib['joint']
                    constraint = self.client.createConstraint(self.body, self.joints[leader],
                        self.body, self.joints[name], p.JOINT_GEAR, [0, 1, 0], [0, 0, 0], [0, 0, 0])
                    self.client.changeConstraint(constraint, gearRatio=-1, erp=0.8, maxForce=100)
                    self.followers[name] = leader
            self.targets = {}
        except BaseException:
            self.client.disconnect()
            raise

    def close(self):
        self.client.disconnect()

    def set_target(self, name, angle):
        if name not in self.movable or name in self.followers:
            raise ValueError('Choose an independent movable joint')
        element = self.elements[name]
        limit = element.find('limit')
        if not math.isfinite(angle):
            raise ValueError('Joint target must be finite')
        if element.attrib['type'] == 'revolute' and not float(limit.get('lower')) <= angle <= float(limit.get('upper')):
            raise ValueError('Joint target is outside its URDF limits')
        self.targets[name] = angle
        self.client.setJointMotorControl2(self.body, self.joints[name], p.POSITION_CONTROL,
            targetPosition=angle, force=float(limit.get('effort')),
            maxVelocity=float(limit.get('velocity')))

    def state(self):
        return {name: self.client.getJointState(self.body, self.joints[name])[:2] for name in self.movable}

    def step(self, steps=1):
        for _ in range(steps * INTEGRATION_STEPS):
            self.client.stepSimulation()

    def audit(self):
        links = {e.attrib['name']: e for e in self.xml.findall('link')}
        imported = {self.client.getBodyInfo(self.body)[0].decode(): -1}
        for index in self.joints.values():
            info = self.client.getJointInfo(self.body, index)
            imported[info[12].decode()] = index
        if set(links) != set(imported) or set(self.elements) != set(self.joints):
            raise ValueError('Imported link or joint inventory differs from source')
        total_mass = 0
        for name, link in links.items():
            inertial = link.find('inertial')
            mass = float(inertial.find('mass').get('value'))
            total_mass += mass
            inertia = tensor(inertial.find('inertia'))
            eigenvalues = np.linalg.eigvalsh(inertia)
            if mass > 0 and (min(eigenvalues) <= 0 or max(eigenvalues) > sum(eigenvalues) / 2 + 1e-10):
                raise ValueError(f'Nonphysical inertia: {name}')
            origin = inertial.find('origin')
            expected_rotation = rotation(vector(origin.get('rpy', '0 0 0')))
            dynamics = self.client.getDynamicsInfo(self.body, imported[name])
            np.testing.assert_allclose(dynamics[3], vector(origin.get('xyz', '0 0 0')), atol=1e-9)
            # A fixed base intentionally has zero engine mass and rotational inertia.
            if imported[name] != -1:
                np.testing.assert_allclose(dynamics[0], mass, atol=1e-9)
                actual_rotation = np.array(p.getMatrixFromQuaternion(dynamics[4])).reshape(3, 3)
                actual = actual_rotation @ np.diag(dynamics[2]) @ actual_rotation.T
                expected = expected_rotation @ inertia @ expected_rotation.T
                np.testing.assert_allclose(actual, expected, atol=1e-8)
        for name, element in self.elements.items():
            info = self.client.getJointInfo(self.body, self.joints[name])
            expected_type = p.JOINT_FIXED if element.get('type') == 'fixed' else p.JOINT_REVOLUTE
            if info[2] != expected_type:
                raise ValueError(f'Joint type mismatch: {name}')
            if element.get('type') == 'revolute':
                limit = element.find('limit')
                np.testing.assert_allclose(info[8:10], [float(limit.get('lower')), float(limit.get('upper'))])
        meshes = self.xml.findall('.//visual/geometry/mesh')
        visuals = self.client.getVisualShapeData(self.body)
        if len(visuals) != len(meshes):
            raise ValueError('Imported visual geometry count differs from source')
        for mesh in meshes:
            if not (self.source.parent / mesh.get('filename')).is_file():
                raise ValueError('Missing visual mesh: ' + mesh.get('filename'))
        return dict(source=self.source.relative_to(SOURCE.parents[4]).as_posix() if self.source == SOURCE else self.source.name,
            source_sha256=hashlib.sha256(self.source.read_bytes()).hexdigest(),
            links=len(links), joints=len(self.joints), visual_meshes=len(meshes), source_mass_kg=total_mass,
            imported_parameters_match=True, base='fixed; engine base mass/inertia intentionally zero',
            mimic_followers=self.followers, timestep_s=DT / INTEGRATION_STEPS,
            control_interval_s=DT)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--gui', action='store_true', help='Open interactive joint sliders; close window to exit')
    parser.add_argument('--seconds', type=float, default=0.05, help='Headless passive simulation duration')
    parser.add_argument('--report', type=Path, default=Path(__file__).parent / 'generated/verification.json')
    args = parser.parse_args()
    if not math.isfinite(args.seconds) or args.seconds <= 0:
        parser.error('--seconds must be positive and finite')
    sim = Simulation(gui=args.gui)
    try:
        report = sim.audit()
        if args.gui:
            sim.client.resetDebugVisualizerCamera(1.5, 45, -20, [0, 0, 0.3])
            sliders = {}
            for name in sim.movable:
                if name in sim.followers or name.startswith('caster_'):
                    continue
                limit = sim.elements[name].find('limit')
                lower, upper = (float(limit.get('lower', '-3.14159')), float(limit.get('upper', '3.14159')))
                sliders[name] = sim.client.addUserDebugParameter(name, lower, upper, 0)
            while sim.client.isConnected():
                started = time.monotonic()
                for name, slider in sliders.items():
                    sim.set_target(name, sim.client.readUserDebugParameter(slider))
                sim.step()
                time.sleep(max(0, DT - (time.monotonic() - started)))
        else:
            steps = math.ceil(args.seconds / DT)
            sim.step(steps)
            state = sim.state()
            if not all(math.isfinite(x) for pair in state.values() for x in pair):
                raise ValueError('Simulation produced nonfinite state')
            report.update(simulated_seconds=steps * DT, finite_state=True, joint_state=state,
                          scope='Passive fixed-base gravity smoke test; estimated physical parameters')
            args.report.parent.mkdir(parents=True, exist_ok=True)
            args.report.write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
            print(json.dumps(report, indent=2))
    except KeyboardInterrupt:
        pass
    except p.error:
        # Closing the native viewer can disconnect between two API calls.
        if not args.gui or sim.client.isConnected():
            raise
    finally:
        if sim.client.isConnected():
            sim.close()


if __name__ == '__main__':
    main()
