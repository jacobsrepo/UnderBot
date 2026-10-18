"""Run in a sourced ROS environment: python -m unittest test_gateway -v."""
import math
import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch
from geometry_msgs.msg import Twist
from gateway import StationGateway, bounded_twist

class CommandTests(unittest.TestCase):
    def test_caps_vector_magnitude(self):
        cmd=Twist()
        cmd.linear.x=cmd.linear.y=10.0
        cmd.angular.z=4.0
        bounded=bounded_twist(cmd)
        self.assertAlmostEqual(math.hypot(bounded.linear.x,bounded.linear.y),0.2)
        self.assertEqual(bounded.angular.z,0.5)

    def test_rejects_nan(self):
        cmd=Twist()
        cmd.linear.x=float('nan')
        self.assertEqual(bounded_twist(cmd),Twist())

    def test_ignores_uncommanded_axes(self):
        cmd=Twist()
        cmd.linear.z=4.0
        cmd.angular.x=2.0
        self.assertEqual(bounded_twist(cmd),Twist())

    def test_watchdog_stops_stale_command(self):
        cmd = Twist()
        cmd.linear.x = 0.1
        state = SimpleNamespace(output=Mock(), command=cmd, received=10.0, timeout=0.35)
        with patch('gateway.time.monotonic', return_value=10.1):
            StationGateway.forward(state)
        state.output.publish.assert_called_with(cmd)
        with patch('gateway.time.monotonic', return_value=10.36):
            StationGateway.forward(state)
        state.output.publish.assert_called_with(Twist())

    def test_disabled_gateway_has_no_output(self):
        StationGateway.forward(SimpleNamespace(output=None))

if __name__=='__main__':
    unittest.main()
