"""ROS-node integration checks; run in the station ROS environment on domain 75."""
import json
import math
from pathlib import Path
import unittest
from unittest.mock import Mock
import rclpy
from std_msgs.msg import String
from geometry_msgs.msg import Twist
from fleet_demo import FleetDemo
from fleet_core import ROBOTS


class FleetExecutionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        rclpy.init()

    @classmethod
    def tearDownClass(cls):
        rclpy.try_shutdown()

    def setUp(self):
        model = Path(__file__).resolve().parent.parent/'compact_lab_rover/rover.urdf'
        self.node = FleetDemo([model, model])
        self.node.events = Mock()

    def tearDown(self):
        self.node.destroy_node()

    def request(self, name, xy, request_id='test'):
        self.node.request(String(data=json.dumps(dict(action='goal', robot_id=name, xy=xy, request_id=request_id))))

    def test_two_goals_execute_with_continuous_separation(self):
        self.request('robot_1', [2., 3.], 'one')
        self.request('robot_2', [3., 2.], 'two')
        self.assertEqual(len(self.node.goals), 2, self.node.state)
        for _ in range(3000):
            self.node.tick()
            self.assertGreaterEqual(math.dist(*(self.node.positions[n] for n in ROBOTS)), self.node.planner.separation-1e-9)
            if not self.node.goals:
                break
        self.assertEqual(self.node.state, 'goals reached')
        self.assertLess(math.dist(self.node.positions['robot_1'], (2, 3)), 1e-8)
        self.assertLess(math.dist(self.node.positions['robot_2'], (3, 2)), 1e-8)
        events = [json.loads(call.args[0].data) for call in self.node.events.publish.call_args_list]
        self.assertEqual({e['id'] for e in events if e['event'] == 'completed'}, {'one', 'two'})

    def test_cancel_stops_both_and_rejected_request_preserves_safe_plan(self):
        self.request('robot_1', [2., 3.])
        paths = self.node.paths
        self.request('robot_2', [999., 999.])
        self.assertIs(self.node.paths, paths)
        self.node.on_command(Twist())
        positions = dict(self.node.positions)
        for _ in range(10):
            self.node.tick()
        self.assertEqual(self.node.positions, positions)
        self.assertFalse(self.node.paths)

    def team(self, kind='demo', request_id='team-test'):
        self.node.request(String(data=json.dumps({'action':'team_mission','mission':kind,'request_id':request_id})))

    def test_complete_team_demo_obeys_barriers_and_returns_home(self):
        self.team()
        self.assertEqual(self.node.mission['state'], 'running', self.node.state)
        observed = set()
        for _ in range(14000):
            before = self.node.mission['stage_index']
            goals = dict(self.node.mission_stages[before]['goals'])
            old_positions = dict(self.node.positions)
            self.node.tick()
            observed.add(self.node.mission['stage'])
            self.assertGreaterEqual(math.dist(*(self.node.positions[n] for n in ROBOTS)), self.node.planner.separation-1e-9)
            if self.node.mission['stage_index'] != before:
                for name in ROBOTS:
                    self.assertLess(math.dist(old_positions[name], goals[name]), 1e-8)
            if self.node.mission['state'] != 'running':
                break
        self.assertEqual(self.node.mission['state'], 'completed', self.node.state)
        self.assertEqual(len(observed), 5)
        for name in ROBOTS:
            self.assertLess(math.dist(self.node.positions[name], self.node.homes[name]), 1e-8)
        completed = [json.loads(c.args[0].data) for c in self.node.events.publish.call_args_list if json.loads(c.args[0].data)['event'] == 'completed']
        self.assertEqual(len(completed), 1)
        self.assertEqual(completed[0]['id'], 'team-test')

    def test_team_cancel_drops_future_stages(self):
        self.team()
        for _ in range(20): self.node.tick()
        self.node.on_command(Twist())
        positions = dict(self.node.positions)
        for _ in range(100): self.node.tick()
        self.assertEqual(self.node.positions, positions)
        self.assertEqual(self.node.mission['state'], 'cancelled')
        self.assertFalse(self.node.mission_stages)

    def test_invalid_replacement_preserves_mission_and_valid_goal_cancels_it(self):
        self.team()
        mission = self.node.mission
        self.request('robot_1', [999.,999.])
        self.assertIs(self.node.mission, mission)
        self.assertEqual(mission['state'], 'running')
        self.request('robot_1', [2.,3.])
        self.assertEqual(mission['state'], 'cancelled')
        self.assertNotIn('robot_2', self.node.goals)
        self.assertEqual(self.node.paths['robot_2'], [self.node.positions['robot_2']])

    def test_unplannable_mission_is_atomic(self):
        from unittest.mock import patch
        self.request('robot_1', [2.,3.])
        paths = self.node.paths
        with patch.object(self.node.planner, 'plan', side_effect=ValueError('Blocked stage')):
            self.team()
        self.assertIs(self.node.paths, paths)
        self.assertIsNone(self.node.mission)

    def test_team_collision_guard_marks_failure(self):
        from unittest.mock import patch
        self.team('swap')
        with patch.object(self.node.planner, 'clear', return_value=False):
            self.node.tick()
        self.assertEqual(self.node.mission['state'], 'failed')
        self.assertFalse(self.node.paths)

    def test_deadline_stops_team(self):
        self.team('home')
        self.node.mission_elapsed = 901
        self.node.tick()
        self.assertEqual(self.node.mission['state'], 'failed')
        self.assertFalse(self.node.paths)


if __name__ == '__main__':
    unittest.main()
