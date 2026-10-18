import unittest,math
import numpy as np
from navigation_core import astar,navigation_intent,plan_route,route_length,segment_is_free
class NavigationTests(unittest.TestCase):
    def test_detour_and_unknown(self):
        g=np.zeros((8,8),dtype=int);g[1:7,3]=100;g[0,3]=-1
        path=astar(g,(1,3),(6,3));self.assertTrue(any(y==7 for x,y in path));self.assertTrue(all(g[y,x]==0 for x,y in path))
    def test_unreachable(self):
        g=np.zeros((4,4),dtype=int);g[:,2]=100
        with self.assertRaises(ValueError):astar(g,(0,0),(3,0))
    def test_blocked_goal(self):
        with self.assertRaises(ValueError):astar(np.ones((3,3)),(0,0),(2,2))
    def test_eight_direction_grid_path_has_octile_cost(self):
        path=astar(np.zeros((10,10)),(1,1),(7,5))
        self.assertAlmostEqual(route_length(path),4*math.sqrt(2)+2)
        self.assertTrue(any(abs(a[0]-b[0])==abs(a[1]-b[1])==1 for a,b in zip(path,path[1:])))
    def test_direct_route_is_euclidean_and_preserves_exact_endpoint(self):
        start=(.13,.17);goal=(2.037,3.081)
        route=plan_route(np.zeros((40,40)),start,goal,.2,origin=(0,0))
        self.assertEqual(route,[start,goal]);self.assertAlmostEqual(route_length(route),math.dist(start,goal))
    def test_shortcuts_detour_around_obstacles_and_unknown(self):
        g=np.zeros((10,10));g[1:9,5]=100;g[0,5]=-1
        route=plan_route(g,(1.5,4.5),(8.5,4.5),1,origin=(0,0))
        self.assertGreater(len(route),2);self.assertGreater(route_length(route),7)
        self.assertTrue(all(segment_is_free(g,a,b) for a,b in zip(route,route[1:])))
        self.assertEqual(route[-1],(8.5,4.5))
    def test_diagonal_cannot_cut_blocked_corner(self):
        g=np.zeros((2,2));g[0,1]=100;g[1,0]=-1
        with self.assertRaises(ValueError):astar(g,(0,0),(1,1))
        self.assertFalse(segment_is_free(g,(.5,.5),(1.5,1.5)))
    def test_segment_catches_thin_obstacle_and_boundary_contact(self):
        g=np.zeros((5,100));g[2,50]=100
        self.assertFalse(segment_is_free(g,(.5,2.5),(99.5,2.5)))
        self.assertFalse(segment_is_free(g,(.5,2.),(99.5,2.)))
        self.assertTrue(segment_is_free(g,(.5,1.5),(99.5,1.5)))
    def test_mixed_direction_integer_endpoints_do_not_overshoot(self):
        g=np.zeros((10,10))
        for start,end in [((1.5,3.5),(3.,2.)),((3.5,1.5),(2.,3.)),((2.,3.),(3.5,1.5)),((3.,3.),(1.5,1.5))]:
            with self.subTest(start=start,end=end):self.assertTrue(segment_is_free(g,start,end))
    def test_intents(self):
        self.assertEqual(navigation_intent('Go to goal_a',{'goal_a':[2,3]})['xy'],[2,3])
        self.assertEqual(navigation_intent('go forward 1 metre',{})['distance'],1)
        self.assertEqual(navigation_intent('go to -2, 3',{})['xy'],[-2,3])
        with self.assertRaises(ValueError):navigation_intent('go to Sam',{})
        with self.assertRaises(ValueError):navigation_intent('go forward 900 metres',{})
        self.assertIsNone(navigation_intent('Who is Sam?',{}))
    def test_rotations_and_polite_requests(self):
        self.assertEqual(navigation_intent('Can you please spin 360 degrees?',{})['degrees'],360)
        self.assertEqual(navigation_intent('turn right 90 degrees',{})['degrees'],-90)
        self.assertEqual(navigation_intent('rotate 180 degrees clockwise',{})['degrees'],-180)
        self.assertEqual(navigation_intent('turn left',{})['degrees'],90)
        with self.assertRaises(ValueError):navigation_intent('spin 720 degrees',{})
        with self.assertRaises(ValueError):navigation_intent('spin 0 degrees',{})
    def test_reverse_and_sequences(self):
        self.assertEqual(navigation_intent('go backwards 0.5 metres',{})['action'],'backward')
        sequence=navigation_intent('turn right then go forward 1 metre then go to desk',{'desk':[2,3]})
        self.assertEqual([s['action'] for s in sequence['steps']],['turn','forward','goal'])
        with self.assertRaises(ValueError):navigation_intent(' then '.join(['turn left']*9),{})
        with self.assertRaises(ValueError):navigation_intent('turn left then tell me a joke',{})
    def test_named_waypoints_and_missing_units(self):
        self.assertEqual(navigation_intent('save waypoint desk at 2, -3',{})['xy'],[2,-3])
        self.assertIsNone(navigation_intent('save waypoint desk here',{})['xy'])
        self.assertEqual(navigation_intent('list waypoints',{})['action'],'list_waypoints')
        with self.assertRaises(ValueError):navigation_intent('save waypoint start here',{})
        with self.assertRaises(ValueError):navigation_intent('go forward',{})
        with self.assertRaises(ValueError):navigation_intent('turn 30',{})
