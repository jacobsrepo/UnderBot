import sys, time, json
sys.path.insert(0, r'D:\gitdemo\Underbot\.publish-underbot\perception')
from common import configure_ros
configure_ros(74)
import rclpy, cv2, numpy as np
from sensor_msgs.msg import CompressedImage
from std_msgs.msg import String
from rclpy.qos import qos_profile_sensor_data
rclpy.init()
n = rclpy.create_node('camera_diagnostic')
rows, statuses = [], []
def frame(m):
    a = cv2.imdecode(np.frombuffer(bytes(m.data), np.uint8), 1)
    rows.append({'size': list(a.shape), 'mean': round(float(a.mean()), 2), 'max': int(a.max()), 'std': round(float(a.std()), 2), 'age_seconds': round(time.time()-m.header.stamp.sec-m.header.stamp.nanosec/1e9, 2)})
n.create_subscription(CompressedImage, '/camera/emeet/image/compressed', frame, qos_profile_sensor_data)
n.create_subscription(String, '/camera/emeet/status', lambda m: statuses.append(json.loads(m.data)), qos_profile_sensor_data)
until = time.monotonic()+8
while time.monotonic()<until:
    rclpy.spin_once(n, timeout_sec=.3)
print(json.dumps({'frames_received':len(rows),'samples':rows[-3:],'camera_status':statuses[-1:]}, indent=2), flush=True)
n.destroy_node()
rclpy.shutdown()
