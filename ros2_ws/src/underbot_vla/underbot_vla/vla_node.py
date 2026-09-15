import rclpy
from rclpy.node import Node
from std_msgs.msg import String
from sensor_msgs.msg import Image
from cv_bridge import CvBridge

import requests
import json
import base64
import cv2
import threading

SYSTEM_PROMPT = """You are the autonomous brain of the Compact Lab Rover robot running ROS 2 Jazzy.
You have a mobile base (differential drive), a 3-DOF manipulator arm with gripper, a 2-axis pan/tilt camera, and LiDAR.
When the user gives you a natural language instruction or asks a question:
1. Provide a concise, clear verbal response to the user.
2. If the user asks you to perform an action or physical task, break it down into an ordered JSON list of action steps.
Allowed actions:
- "find_object(name)"
- "find_person(name)"
- "navigate_to(target)"
- "pick(object)"
- "place(location)"
- "handover(object, person)"
- "look_around()"
- "stop()"

Format your output strictly as:
RESPONSE: <Your conversational reply to the user>
PLAN: <JSON list of action steps, e.g. [{"step": 1, "action": "find_object", "target": "red ball"}, ...]>
If no physical action is needed, output PLAN: []
"""

class VLABrainNode(Node):
    def __init__(self):
        super().__init__('vla_brain_node')

        self.declare_parameter('model_name', 'moondream')
        self.declare_parameter('ollama_url', 'http://127.0.0.1:11434')
        self.declare_parameter('camera_topic', '/camera/image_raw')

        self.model_name = self.get_parameter('model_name').get_parameter_value().string_value
        self.ollama_url = self.get_parameter('ollama_url').get_parameter_value().string_value
        camera_topic = self.get_parameter('camera_topic').get_parameter_value().string_value

        self.bridge = CvBridge()
        self.latest_cv_image = None
        self.image_lock = threading.Lock()

        # Subscribers
        self.create_subscription(Image, camera_topic, self.image_callback, 10)
        self.create_subscription(String, '/underbot/command', self.command_callback, 10)

        # Publishers
        self.response_pub = self.create_publisher(String, '/underbot/response', 10)
        self.plan_pub = self.create_publisher(String, '/underbot/action_plan', 10)

        self.get_logger().info(f'VLA Brain Node initialized using model: {self.model_name} at {self.ollama_url}')

    def image_callback(self, msg: Image):
        try:
            cv_img = self.bridge.imgmsg_to_cv2(msg, desired_encoding='bgr8')
            with self.image_lock:
                self.latest_cv_image = cv_img
        except Exception as e:
            self.get_logger().error(f'Error converting image: {e}')

    def command_callback(self, msg: String):
        prompt = msg.data.strip()
        if not prompt:
            return

        self.get_logger().info(f'Received user command: "{prompt}"')
        threading.Thread(target=self.process_command, args=(prompt,), daemon=True).start()

    def process_command(self, prompt: str):
        # Prepare image if available
        base64_image = None
        with self.image_lock:
            if self.latest_cv_image is not None:
                _, buffer = cv2.imencode('.jpg', self.latest_cv_image, [int(cv2.IMWRITE_JPEG_QUALITY), 80])
                base64_image = base64.b64encode(buffer).decode('utf-8')

        payload = {
            "model": self.model_name,
            "prompt": f"{SYSTEM_PROMPT}\nUser Command: {prompt}",
            "stream": False
        }

        if base64_image:
            payload["images"] = [base64_image]

        try:
            res = requests.post(f"{self.ollama_url}/api/generate", json=payload, timeout=60)
            if res.status_code == 200:
                raw_response = res.json().get('response', '')
                self.handle_vla_output(raw_response)
            else:
                self.get_logger().error(f'Ollama API returned status {res.status_code}: {res.text}')
                self.response_pub.publish(String(data=f"Error contacting VLA model: HTTP {res.status_code}"))
        except Exception as e:
            self.get_logger().error(f'Failed to query VLA model: {e}')
            self.response_pub.publish(String(data=f"VLA model error: {str(e)}"))

    def handle_vla_output(self, raw_output: str):
        self.get_logger().info(f'VLA Raw Output:\n{raw_output}')

        response_text = ""
        plan_json = "[]"

        # Parse RESPONSE: and PLAN:
        if "RESPONSE:" in raw_output:
            parts = raw_output.split("PLAN:")
            response_text = parts[0].replace("RESPONSE:", "").strip()
            if len(parts) > 1:
                plan_json = parts[1].strip()
        else:
            response_text = raw_output.strip()

        # Publish conversational response
        resp_msg = String()
        resp_msg.data = response_text
        self.response_pub.publish(resp_msg)

        # Publish structured plan
        plan_msg = String()
        plan_msg.data = plan_json
        self.plan_pub.publish(plan_msg)

        self.get_logger().info(f'Published verbal response: {response_text}')
        self.get_logger().info(f'Published action plan: {plan_json}')

def main(args=None):
    rclpy.init(args=args)
    node = VLABrainNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()

if __name__ == '__main__':
    main()
