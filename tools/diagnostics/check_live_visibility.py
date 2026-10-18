import json
import time
import rclpy
from std_msgs.msg import String

rclpy.init()
node = rclpy.create_node('check_live_visibility')
worlds = []
results = {}
def response(msg):
    data = json.loads(msg.data)
    if data.get('final', True):
        results[data['id']] = data
node.create_subscription(String, '/station/ai/world_state', lambda msg: worlds.append(json.loads(msg.data)), 10)
node.create_subscription(String, '/station/ai/response', response, 10)
pub = node.create_publisher(String, '/station/ai/request', 10)
def spin(seconds, condition=lambda: False):
    deadline = time.monotonic() + seconds
    while time.monotonic() < deadline and not condition():
        rclpy.spin_once(node, timeout_sec=0.1)
try:
    spin(20, lambda: worlds and worlds[-1]['fresh'])
    assert worlds, 'No world-state messages'
    print(json.dumps({'live_world_state': worlds[-1]}), flush=True)
    for prompt in ['Who is Sam?', 'Can you see Sam?', 'Who can you see?', 'When did you last see Sam?']:
        key = str(time.time_ns())
        pub.publish(String(data=json.dumps({'id': key, 'text': prompt})))
        spin(20, lambda: key in results)
        assert key in results and results[key]['ok'], 'No successful chat reply'
        print(json.dumps({'question': prompt, 'answer': results[key]['text']}), flush=True)
finally:
    node.destroy_node()
    rclpy.try_shutdown()
