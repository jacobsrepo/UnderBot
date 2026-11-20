import math
from pathlib import Path
import unittest
import xml.etree.ElementTree as ET
import numpy as np
from fleet_core import FleetPlanner, ROBOTS, fleet_intent, swept_distance
from fleet_urdf import load_robot


class FleetTests(unittest.TestCase):
    def planner(self):
        return FleetPlanner(np.zeros((24, 24)), .5, (0., 0.), radius=.3, margin=.1, horizon=100)

    def assert_safe(self, planner, paths):
        a, b = (paths[n] for n in ROBOTS)
        for t in range(max(len(a), len(b))):
            self.assertGreaterEqual(swept_distance(planner.at(a, t), planner.at(a, t+1), planner.at(b, t), planner.at(b, t+1)), planner.separation-1e-9)
            for path in (a, b):
                self.assertTrue(planner.clear(planner.at(path, t), planner.at(path, t+1)))

    def test_crossing_routes(self):
        p = self.planner()
        starts = dict(zip(ROBOTS, [(2.25, 6.25), (6.25, 2.25)]))
        goals = dict(zip(ROBOTS, [(10.25, 6.25), (6.25, 10.25)]))
        paths = p.plan(starts, goals)
        self.assert_safe(p, paths)
        for n in ROBOTS:
            self.assertEqual(paths[n][-1], goals[n])

    def test_head_on_swap(self):
        p = self.planner()
        starts = dict(zip(ROBOTS, [(3.25, 6.25), (9.25, 6.25)]))
        paths = p.plan(starts, dict(zip(ROBOTS, reversed(list(starts.values())))))
        self.assert_safe(p, paths)

    def test_idle_robot_is_obstacle(self):
        p = self.planner()
        starts = dict(zip(ROBOTS, [(2.25, 6.25), (6.25, 6.25)]))
        paths = p.plan(starts, {ROBOTS[0]: (10.25, 6.25)})
        self.assertEqual(paths[ROBOTS[1]], [starts[ROBOTS[1]]])
        self.assert_safe(p, paths)

    def test_overlapping_destinations_rejected(self):
        with self.assertRaises(ValueError):
            self.planner().plan(dict(zip(ROBOTS, [(2.25, 6.25), (9.25, 6.25)])), dict.fromkeys(ROBOTS, (6.25, 6.25)))

    def test_swept_swap_detected_between_endpoints(self):
        self.assertEqual(swept_distance((0, 0), (1, 0), (1, 0), (0, 0)), 0)

    def test_unknown_and_footprint_inflation(self):
        grid = np.zeros((24, 24)); grid[:, 12] = -1
        p = FleetPlanner(grid, .5, (0, 0), radius=.3)
        self.assertFalse(p.clear((5.9, 5), (5.9, 5)))
        with self.assertRaises(ValueError):
            p.route((3.25, 6.25), (9.25, 6.25))

    def test_bounded_search(self):
        p = self.planner(); p.max_expansions = 1
        with self.assertRaises(ValueError):
            p.route((2.25, 6.25), (10.25, 6.25), [(6.25, 6.25)])

    def test_parser(self):
        self.assertEqual(fleet_intent('robot 2 go to 2, 3', {})['robot_id'], 'robot_2')
        self.assertEqual(fleet_intent('robot_1 go to start', {'start': [1, 2]})['xy'], [1, 2])
        with self.assertRaises(ValueError):
            fleet_intent('robot 1 go forward 1 metre', {})

    def test_urdf_instances_have_disjoint_frames(self):
        path = Path(__file__).resolve().parent.parent/'compact_lab_rover/rover.urdf'
        models = [load_robot(path, n) for n in ROBOTS]
        frames = [{e.get('name') for e in ET.fromstring(m[0]).findall('link')} for m in models]
        self.assertFalse(frames[0] & frames[1])
        self.assertGreater(models[0][3], .2)
        self.assertTrue(math.isfinite(models[0][3]))
        for model, links in zip(models, frames):
            self.assertEqual({t[1] for t in model[2]} | {model[1]}, links)


if __name__ == '__main__':
    unittest.main()
