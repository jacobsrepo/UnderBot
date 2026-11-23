import unittest
import numpy as np
import xml.etree.ElementTree as ET
from arm_model import Arm, JOINT_NAMES
from prepare import prepare, ROOT


class ArmTests(unittest.TestCase):
    def test_neutral_grasp_centre_matches_independent_pybullet_import(self):
        np.testing.assert_allclose(Arm().fk(np.zeros(5)), [-0.07, 0.338, 0.371794923], atol=1e-7)

    def test_small_xyz_jog_is_coordinated_and_bounded(self):
        arm = Arm()
        q = np.zeros(5)
        target = arm.fk(q) + np.array([0, 0, 0.005])
        result = arm.solve(target, q)
        self.assertLess(np.linalg.norm(arm.fk(result) - target), 0.001)
        self.assertGreater(np.count_nonzero(abs(result) > 0.001), 1)
        self.assertTrue(np.all(result >= arm.low) and np.all(result <= arm.high))

    def test_unreachable_target_rejected(self):
        with self.assertRaises(ValueError):
            Arm().solve([10, 10, 10], np.zeros(5))

    def test_generated_controllers_share_vector_and_fingers_share_index(self):
        prepare(True)
        root = ET.parse(ROOT / 'generated/underbot.urdf')
        self.assertFalse(root.findall('.//mimic'))
        controllers = {p.findtext('joint_name'): p for p in root.findall('.//gazebo/plugin') if p.find('joint_name') is not None}
        self.assertEqual(len(controllers), 14)
        for name in JOINT_NAMES:
            plugin = controllers[name]
            self.assertEqual(plugin.findtext('topic'), '/underbot/arm_targets')
            self.assertEqual(int(plugin.findtext('actuator_number')), JOINT_NAMES.index(name))
        for side in ('left', 'right'):
            self.assertEqual(controllers[f'{side}_gripper_left_joint'].findtext('actuator_number'),
                             controllers[f'{side}_gripper_right_joint'].findtext('actuator_number'))

    def test_grasp_assist_is_only_generated_when_explicit(self):
        prepare(True, False)
        root = ET.parse(ROOT / 'generated/underbot.urdf')
        self.assertFalse(root.findall(".//plugin[@filename='gz-sim-detachable-joint-system']"))
        prepare(True, True)
        root = ET.parse(ROOT / 'generated/underbot.urdf')
        plugins = root.findall(".//plugin[@filename='gz-sim-detachable-joint-system']")
        self.assertEqual(len(plugins), 1)
        self.assertEqual(plugins[0].findtext('child_model'), 'pick_block')

    def test_grasp_assist_requires_pick_place_world(self):
        with self.assertRaisesRegex(ValueError, 'requires'):
            prepare(False, True)


if __name__ == '__main__':
    unittest.main()
