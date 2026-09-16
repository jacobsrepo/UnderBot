"""ROS 2 station adapter. Hardware forwarding is explicitly opt-in."""
import json
import math
import time
import rclpy
from rclpy.node import Node
from geometry_msgs.msg import Twist
from std_msgs.msg import String


def bounded_twist(msg, max_linear=0.2, max_angular=0.5):
    values = [msg.linear.x, msg.linear.y, msg.angular.z]
    if not all(math.isfinite(v) for v in values):
        return Twist()
    result = Twist()
    length = math.hypot(values[0], values[1])
    scale = min(1.0, max_linear / length) if length else 1.0
    result.linear.x, result.linear.y = values[0] * scale, values[1] * scale
    result.angular.z = max(-max_angular, min(max_angular, values[2]))
    return result


class StationGateway(Node):
    def __init__(self):
        super().__init__('underbot_station')
        self.declare_parameter('hardware_enabled', False)
        self.declare_parameter('mode', 'live')
        self.declare_parameter('command_timeout', 0.35)
        self.enabled = self.get_parameter('hardware_enabled').value is True
        self.mode = self.get_parameter('mode').value
        if self.mode not in ('live', 'demo'):
            raise ValueError('mode must be live or demo')
        if self.mode == 'demo' and self.enabled:
            raise ValueError('Demo mode must never enable hardware')
        self.timeout = float(self.get_parameter('command_timeout').value)
        if not 0.1 <= self.timeout <= 0.5:
            raise ValueError('command_timeout must be 0.1–0.5 seconds')
        self.command = Twist()
        self.received = 0.0
        self.status = self.create_publisher(String, '/station/status', 10)
        self.response = self.create_publisher(String, '/station/ai/response', 10)
        # Only create a motor-output publisher when explicitly enabled.
        self.output = self.create_publisher(Twist, '/station/guarded_cmd_vel', 10) if self.enabled else None
        self.create_subscription(Twist, '/station/cmd_vel', self.on_command, 10)
        self.create_subscription(Twist, '/station/camera_cmd', self.on_camera, 10)
        self.create_subscription(String, '/station/comms/request', self.on_comms, 10)
        self.create_subscription(String, '/station/ai/request', self.on_chat, 10)
        self.last_request = 'none'
        self.create_timer(0.05, self.forward)
        self.create_timer(0.5, self.heartbeat)

    def on_command(self, msg):
        self.command = bounded_twist(msg)
        self.received = time.monotonic()

    def on_camera(self, _msg):
        self.last_request = 'camera request received; no actuator adapter configured'

    def on_comms(self, msg):
        try:
            enabled = json.loads(msg.data)['enabled']
            if not isinstance(enabled, bool):
                return
            self.last_request = f'comms {"on" if enabled else "off"} requested; no audio adapter configured'
        except (ValueError, KeyError, TypeError):
            return

    def on_chat(self, msg):
        try:
            request = json.loads(msg.data)
            if not isinstance(request.get('id'), str) or not isinstance(request.get('text'), str):
                return
            if len(request['text']) > 2000:
                return
            reply = 'No AI backend is configured. This station is connected, but no language model is answering yet.'
            self.response.publish(String(data=json.dumps({'id': request['id'], 'ok': False, 'text': reply})))
        except (ValueError, TypeError, AttributeError):
            return

    def forward(self):
        if self.output:
            self.output.publish(self.command if time.monotonic() - self.received < self.timeout else Twist())

    def heartbeat(self):
        self.status.publish(String(data=json.dumps({
            'mode': self.mode, 'hardware_enabled': self.enabled,
            'comms': 'not configured', 'ai': 'not configured',
            'last_request': self.last_request,
        })))


def main():
    rclpy.init()
    node = StationGateway()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        if node.output:
            node.output.publish(Twist())
        node.destroy_node()
        rclpy.try_shutdown()


if __name__ == '__main__':
    main()
