"""Brief live ON/OFF test; no audio files are recorded."""
import json
import time
import numpy as np
from common import configure_ros
configure_ros(74)
import rclpy
from std_msgs.msg import String
from foxglove_msgs.msg import RawAudio
from rclpy.qos import qos_profile_sensor_data

rclpy.init()
node = rclpy.create_node('check_pi_comms')
states = []
packets = []
reports = []
def audio(msg):
    assert msg.format == 'pcm-s16' and msg.sample_rate == 16000 and msg.number_of_channels == 1
    assert len(msg.data) == 640
    samples = np.frombuffer(bytes(msg.data), dtype='<i2').astype(float)
    packets.append(float(np.sqrt(np.mean(samples * samples))))
node.create_subscription(RawAudio, '/station/audio/pi', audio, qos_profile_sensor_data)
def report(msg):
    data = json.loads(msg.data)
    reports.append(data)
    states.append(data['state'])
node.create_subscription(String, '/station/comms/status', report, 10)
publisher = node.create_publisher(String, '/station/comms/request', 10)
def spin(seconds):
    end = time.monotonic() + seconds
    while time.monotonic() < end:
        rclpy.spin_once(node, timeout_sec=0.05)
try:
    spin(3)
    assert publisher.get_subscription_count() >= 2, 'Gateway or Comms adapter missing'
    publisher.publish(String(data='{"enabled":true}'))
    spin(25)
    print(json.dumps({'packets':len(packets), 'max_rms':max(packets, default=0), 'state':states[-1] if states else None}), flush=True)
    assert len(packets) > 100, 'No Pi microphone stream'
    assert max(packets) > 0, 'Only silence received'
    tx = max(r.get('transmit_packets', 0) for r in reports)
    peak = max(r.get('transmit_peak', 0) for r in reports)
    print(json.dumps({'PC_microphone_packets_sent': tx, 'PC_microphone_peak': peak}), flush=True)
    assert tx > 100 and peak > 0, 'PC microphone transmission failed'
finally:
    publisher.publish(String(data='{"enabled":false}'))
    spin(2)
    count = len(packets)
    spin(2)
    stopped = len(packets) == count and states[-1] == 'OFF'
    print('OFF stops audio:', stopped, flush=True)
    node.destroy_node()
    rclpy.shutdown()
    assert stopped
