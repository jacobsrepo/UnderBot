import math
import unittest
import numpy as np
from simulator import Simulation


class SimulationTests(unittest.TestCase):
    def setUp(self):
        self.sim = Simulation()

    def tearDown(self):
        self.sim.close()

    def test_import_matches_r09(self):
        report = self.sim.audit()
        self.assertEqual((report['links'], report['joints'], report['visual_meshes']), (23, 22, 45))
        self.assertAlmostEqual(report['source_mass_kg'], 19.6010078)
        self.assertEqual(len(report['mimic_followers']), 2)

    def test_passive_gravity_keeps_base_fixed_and_state_finite(self):
        before = self.sim.client.getBasePositionAndOrientation(self.sim.body)
        for _ in range(240):
            self.sim.step()
            for name, (angle, speed) in self.sim.state().items():
                self.assertTrue(math.isfinite(angle) and math.isfinite(speed))
                self.assertLess(abs(speed), 40, name)
                if self.sim.elements[name].get('type') == 'revolute':
                    limit = self.sim.elements[name].find('limit')
                    self.assertGreaterEqual(angle, float(limit.get('lower')) - .002, name)
                    self.assertLessEqual(angle, float(limit.get('upper')) + .002, name)
        after = self.sim.client.getBasePositionAndOrientation(self.sim.body)
        np.testing.assert_allclose(before[0], after[0], atol=1e-12)
        np.testing.assert_allclose(before[1], after[1], atol=1e-12)
        self.assertTrue(all(math.isfinite(v) for pair in self.sim.state().values() for v in pair))

    def test_limits_and_followers_reject_invalid_targets(self):
        for name, angle in [('left_elbow_joint', 100), ('left_wheel_joint', float('nan')),
                            ('left_gripper_right_joint', .2), ('missing', 0)]:
            with self.assertRaises(ValueError):
                self.sim.set_target(name, angle)

    def test_grippers_follow_in_both_directions(self):
        for target in (.4, .1):
            for leader in self.sim.followers.values():
                self.sim.set_target(leader, target)
            self.sim.step(480)
            state = self.sim.state()
            for follower, leader in self.sim.followers.items():
                self.assertAlmostEqual(state[leader][0], target, delta=.02)
                self.assertAlmostEqual(state[follower][0], state[leader][0], delta=.005)


if __name__ == '__main__':
    unittest.main()
