import json,time,unittest
from types import SimpleNamespace,MethodType
from unittest.mock import Mock,patch
from geometry_msgs.msg import Twist
from std_msgs.msg import String
from navigation_demo import NavigationDemo, navigation_data_dir
from pathlib import Path
from tempfile import TemporaryDirectory

class ExecutionTests(unittest.TestCase):
    def state(self):
        state=SimpleNamespace(task_id=None,task_started=0.,step_started=0.,step_number=0,total_steps=0,
            route=[],pending_steps=[],turn_target=None,turn_start=None,reverse=False,command=Twist(),
            x=0.,y=0.,yaw=0.,goal_xy=None,events=Mock(),world=Mock(),publish_status=Mock(),nav_status='idle',
            free_xy=lambda x,y:abs(x)<2 and abs(y)<2,
            free_segment=lambda a,b:all(abs(v)<2 for v in (*a,*b)))
        instance=NavigationDemo.__new__(NavigationDemo)
        instance.__dict__.update(state.__dict__)
        return instance
    def request(self,state,action):state.request(String(data=json.dumps(action)))
    def events(self,state):return [json.loads(call.args[0].data) for call in state.events.publish.call_args_list]
    def test_full_turn_completes_only_after_full_accumulated_angle(self):
        state=self.state();self.request(state,{'action':'turn','degrees':360,'request_id':'spin'})
        def integrate():state.yaw+=state.command.angular.z*.05
        with patch('demo.Demo.tick',side_effect=integrate):
            for _ in range(170):NavigationDemo.tick(state)
        self.assertAlmostEqual(state.yaw,6.283185307,places=6)
        self.assertIsNone(state.task_id)
        self.assertEqual([e['event'] for e in self.events(state)],['started','completed'])
    def test_stop_cancels_all_remaining_steps_and_correlates_results(self):
        state=self.state();self.request(state,{'action':'sequence','steps':[{'action':'turn','degrees':360},{'action':'forward','distance':1}],'request_id':'old'})
        self.request(state,{'action':'stop','request_id':'stop'})
        self.assertEqual(state.pending_steps,[]);self.assertIsNone(state.turn_target)
        self.assertEqual([(e['id'],e['event']) for e in self.events(state)],[('old','started'),('old','cancelled'),('stop','completed')])
    def test_deadline_stops_motion(self):
        state=self.state();self.request(state,{'action':'turn','degrees':360,'request_id':'timeout'})
        state.step_started=time.monotonic()-301
        with patch('demo.Demo.tick'):NavigationDemo.tick(state)
        self.assertIsNone(state.turn_target);self.assertEqual(state.command,Twist())
        self.assertEqual(self.events(state)[-1]['event'],'timed_out')
    def test_blocked_segment_reports_rejection(self):
        state=self.state();self.request(state,{'action':'forward','distance':3,'request_id':'blocked'})
        self.assertEqual(state.route,[]);self.assertEqual(self.events(state)[-1]['event'],'rejected')
        self.assertEqual(self.events(state)[-1]['id'],'blocked')
    def test_controller_reaches_unsnapped_diagonal_destination(self):
        import math
        from navigation_core import segment_is_free
        import numpy as np
        state=self.state();state.x=.13;state.y=.17
        state.meta={'resolution':.2};state.grid=np.zeros((200,200));state.set_goal=MethodType(NavigationDemo.set_goal,state)
        state.free_segment=MethodType(NavigationDemo.free_segment,state)
        goal=(1.037,1.481)
        self.request(state,{'action':'goal','xy':goal,'request_id':'diagonal'})
        self.assertEqual(state.goal_xy,goal);self.assertEqual(len(state.route),2)
        travelled=0.
        def integrate():
            nonlocal travelled
            old=(state.x,state.y);state.yaw+=state.command.angular.z*.05
            state.x+=math.cos(state.yaw)*state.command.linear.x*.05;state.y+=math.sin(state.yaw)*state.command.linear.x*.05
            travelled+=math.dist(old,(state.x,state.y))
        with patch('demo.Demo.tick',side_effect=integrate):
            for _ in range(600):
                NavigationDemo.tick(state)
                if state.task_id is None:break
        self.assertLess(math.dist((state.x,state.y),goal),.02)
        self.assertLess(travelled,math.dist((.13,.17),goal)*1.03)
        self.assertEqual(self.events(state)[-1]['event'],'completed')
    def test_controller_follows_obstacle_detour_without_cutting_corners(self):
        import math
        import numpy as np
        state=self.state();state.x=-18.5;state.y=-15.5
        state.meta={'resolution':1.};state.grid=np.zeros((10,10));state.grid[1:9,5]=100;state.grid[0,5]=-1
        state.set_goal=MethodType(NavigationDemo.set_goal,state);state.free_segment=MethodType(NavigationDemo.free_segment,state)
        goal=(-11.5,-15.5);self.request(state,{'action':'goal','xy':goal,'request_id':'detour'})
        self.assertGreater(len(state.route),2)
        def integrate():
            old=(state.x,state.y);state.yaw+=state.command.angular.z*.05
            state.x+=math.cos(state.yaw)*state.command.linear.x*.05;state.y+=math.sin(state.yaw)*state.command.linear.x*.05
            self.assertTrue(state.free_segment(old,(state.x,state.y)))
        with patch('demo.Demo.tick',side_effect=integrate):
            for _ in range(2500):
                NavigationDemo.tick(state)
                if state.task_id is None:break
        self.assertLess(math.dist((state.x,state.y),goal),.02)
        self.assertEqual(self.events(state)[-1]['event'],'completed')


class NavigationDataTests(unittest.TestCase):
    def test_fresh_checkout_uses_bundled_map(self):
        with TemporaryDirectory() as tmp:
            root=Path(tmp)/'robot_station'; root.mkdir()
            bundled=Path(tmp)/'navigation'; bundled.mkdir()
            for name in ('map_metadata.json','demo_map.npz'):(bundled/name).touch()
            self.assertEqual(navigation_data_dir(root),bundled)

    def test_existing_deployment_keeps_its_map(self):
        with TemporaryDirectory() as tmp:
            root=Path(tmp)/'robot_station'; installed=root/'navigation-data'; installed.mkdir(parents=True)
            for name in ('map_metadata.json','demo_map.npz'):(installed/name).touch()
            self.assertEqual(navigation_data_dir(root),installed)

    def test_missing_data_reports_setup_problem(self):
        with TemporaryDirectory() as tmp:
            with self.assertRaisesRegex(FileNotFoundError,'Navigation data missing'):
                navigation_data_dir(Path(tmp)/'robot_station')
