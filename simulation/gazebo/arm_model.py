"""Joint ordering and bounded position IK for the R09 arm (metres/radians)."""
from pathlib import Path
import xml.etree.ElementTree as ET
import numpy as np

SOURCE = Path(__file__).resolve().parents[2] / 'models/r09/underbot_description/urdf/underbot.portable.urdf'
PARTS = ('arm_base', 'shoulder', 'elbow', 'wrist_pitch', 'wrist_roll', 'gripper_left')
JOINT_NAMES = tuple(f'{side}_{part}_joint' for side in ('left', 'right') for part in PARTS)


def limits():
    joints = {j.get('name'): j for j in ET.parse(SOURCE).findall('joint')}
    return {name: tuple(float(joints[name].find('limit').get(k)) for k in ('lower', 'upper'))
            for name in JOINT_NAMES}


def rotation(axis, angle):
    axis = np.asarray(axis, dtype=float)
    axis /= np.linalg.norm(axis)
    x, y, z = axis
    cross = np.array([[0, -z, y], [z, 0, -x], [-y, x, 0]])
    return np.eye(3) + np.sin(angle) * cross + (1 - np.cos(angle)) * cross @ cross


class Arm:
    def __init__(self, side='left'):
        self.names = [f'{side}_{part}_joint' for part in PARTS[:5]]
        joints = {j.get('name'): j for j in ET.parse(SOURCE).findall('joint')}
        self.origins, self.axes = [], []
        self.low, self.high = np.array([limits()[n] for n in self.names]).T
        for name in self.names:
            joint = joints[name]
            xyz = np.fromstring(joint.find('origin').get('xyz'), sep=' ')
            r, p, y = np.fromstring(joint.find('origin').get('rpy'), sep=' ')
            matrix = np.eye(4)
            matrix[:3, :3] = rotation([0, 0, 1], y) @ rotation([0, 1, 0], p) @ rotation([1, 0, 0], r)
            matrix[:3, 3] = xyz
            self.origins.append(matrix)
            self.axes.append(np.fromstring(joint.find('axis').get('xyz'), sep=' '))

    def fk(self, q):
        matrix = np.eye(4)
        for origin, axis, angle in zip(self.origins, self.axes, q):
            turn = np.eye(4)
            turn[:3, :3] = rotation(axis, angle)
            matrix = matrix @ origin @ turn
        # Grasp centre between the fingers, 50 mm beyond the hand origin.
        return matrix[:3, 3] + matrix[:3, :3] @ np.array([0.05, 0, 0])

    def solve(self, target, seed, tolerance=0.001):
        target = np.asarray(target, dtype=float)
        q = np.clip(np.asarray(seed, dtype=float), self.low, self.high)
        if target.shape != (3,) or not np.all(np.isfinite(target)):
            raise ValueError('Invalid Cartesian target')
        for _ in range(150):
            pos = self.fk(q)
            error = target - pos
            if np.linalg.norm(error) < tolerance:
                return q
            jac = np.column_stack([(self.fk(q + np.eye(5)[i] * 1e-5) - pos) / 1e-5 for i in range(5)])
            dq = jac.T @ np.linalg.solve(jac @ jac.T + np.eye(3) * 1e-5, error)
            q = np.clip(q + np.clip(dq, -0.08, 0.08), self.low, self.high)
        raise ValueError('Target is outside the reachable workspace; try a smaller move')
