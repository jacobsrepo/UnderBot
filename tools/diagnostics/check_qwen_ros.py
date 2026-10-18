import json
import time
import rclpy
from std_msgs.msg import String

rclpy.init()
node = rclpy.create_node('underbot_chat_check')
result = []
heartbeats = []
request_id = 'qwen-setup-' + str(time.time_ns())
def receive(msg):
    data = json.loads(msg.data)
    if data.get('id') == request_id:
        print(json.dumps(data), flush=True)
        if data.get('final', True):
            result.append(data)
node.create_subscription(String, '/station/ai/response', receive, 10)
node.create_subscription(String, '/station/status', lambda m: heartbeats.append(json.loads(m.data)), 10)
publisher = node.create_publisher(String, '/station/ai/request', 10)
deadline = time.monotonic() + 15
while publisher.get_subscription_count() == 0 and time.monotonic() < deadline:
    rclpy.spin_once(node, timeout_sec=0.2)
assert publisher.get_subscription_count(), 'No chat gateway subscriber'
publisher.publish(String(data=json.dumps({'id': request_id, 'text': 'In one short sentence, say hello and name the computer you run on.'})))
started = time.monotonic()
while not result and time.monotonic() - started < 170:
    rclpy.spin_once(node, timeout_sec=0.2)
print('Heartbeat count during inference:', len(heartbeats))
print('Elapsed seconds:', round(time.monotonic()-started, 1))
assert result and result[0]['ok'], 'Chat failed'
assert len(heartbeats) > 2, 'Station heartbeat stalled'
assert all(not s['hardware_enabled'] for s in heartbeats)
node.destroy_node()
rclpy.shutdown()
