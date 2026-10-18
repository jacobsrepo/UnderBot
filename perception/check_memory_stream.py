"""Check live identity-fallback status without saving camera frames."""
import json
import time
from common import configure_ros, STATUS_TOPIC, OBJECT_TOPIC
configure_ros(74)
import rclpy
from std_msgs.msg import String
from rclpy.qos import qos_profile_sensor_data
rclpy.init();node=rclpy.create_node('underbot_memory_verify')
states=set();count=0
def status(msg):
 value=json.loads(msg.data)
 if 'recognition_state' in value:states.add(value['recognition_state'])
def objects(msg):
 global count
 value=json.loads(msg.data)
 assert isinstance(value['objects'],list)
 count+=1
subscriptions=[node.create_subscription(String,STATUS_TOPIC,status,qos_profile_sensor_data),node.create_subscription(String,OBJECT_TOPIC,objects,qos_profile_sensor_data)]
end=time.monotonic()+30
while time.monotonic()<end:
 rclpy.spin_once(node,timeout_sec=.1)
 if count>=3 and states:break
print(json.dumps({'result_messages':count,'recognition_states':sorted(states)}))
node.destroy_node();rclpy.shutdown()
assert count>=1 and 'empty_or_expired_gallery' in states
