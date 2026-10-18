import json
import time
import rclpy
from std_msgs.msg import String

rclpy.init()
node = rclpy.create_node('check_robot_brain')
responses = {}
plans = {}
heartbeats = []
def reply(msg):
    value = json.loads(msg.data)
    if value.get('final', True):
        responses[value['id']] = value
def plan(msg):
    value = json.loads(msg.data)
    plans[value['id']] = value
node.create_subscription(String, '/station/ai/response', reply, 10)
node.create_subscription(String, '/station/ai/plan', plan, 10)
node.create_subscription(String, '/station/status', lambda m: heartbeats.append(json.loads(m.data)), 10)
pub = node.create_publisher(String, '/station/ai/request', 10)
def spin_until(predicate, seconds):
    end = time.monotonic() + seconds
    while not predicate() and time.monotonic() < end:
        rclpy.spin_once(node, timeout_sec=0.1)
try:
    spin_until(lambda: pub.get_subscription_count() > 0, 15)
    for i, (question, expected) in enumerate([
        ('Who is Sam?', 'Sam Jacob'),
        ('Who is Alfred?', 'no matching'),
        ('Bring Alfred the red ball.', 'Proposed plan only'),
        ('Use the supplied memory context: state the full enrolled name matching Sam. One sentence.', 'Sam Jacob'),
    ]):
        key = f'brain-check-{time.time_ns()}-{i}'
        pub.publish(String(data=json.dumps({'id': key, 'text': question})))
        spin_until(lambda: key in responses and key in plans, 175)
        result = responses.get(key, {})
        print(json.dumps({'question': question, 'response': result}), flush=True)
        assert result.get('ok') and expected.casefold() in result['text'].casefold()
        assert plans[key]['executable'] is False
        if i == 2:
            assert len(plans[key]['plan']['steps']) == 7
    assert heartbeats and all(not h['hardware_enabled'] for h in heartbeats)
    print('Memory, unknown identity, proposed plan, grounded Qwen and disabled hardware checks passed.', flush=True)
finally:
    node.destroy_node()
    rclpy.try_shutdown()
