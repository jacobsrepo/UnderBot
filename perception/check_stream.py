"""Check actual ROS image delivery and inference, without storing camera images."""
import argparse
import json
import time
import cv2
import numpy as np
import rclpy
from rclpy.node import Node
from rclpy.qos import qos_profile_sensor_data
from sensor_msgs.msg import CompressedImage
from std_msgs.msg import String
from common import configure_ros, IMAGE_TOPIC, ANNOTATED_TOPIC, OBJECT_TOPIC, POSE_TOPIC, STATUS_TOPIC

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--seconds', type=int, default=20)
    parser.add_argument('--domain', type=int, default=74)
    args = parser.parse_args()
    configure_ros(args.domain)
    rclpy.init()
    node = Node('underbot_perception_check')
    counts = {IMAGE_TOPIC: 0, ANNOTATED_TOPIC: 0, OBJECT_TOPIC: 0, POSE_TOPIC: 0}
    summary = {}
    matched = {t: set() for t in counts}
    def image_callback(topic, msg):
        frame = cv2.imdecode(np.frombuffer(bytes(msg.data), np.uint8), cv2.IMREAD_COLOR)
        if frame is None:
            raise AssertionError(f'Invalid JPEG on {topic}')
        counts[topic] += 1
        matched[topic].add((msg.header.stamp.sec, msg.header.stamp.nanosec))
        summary[topic] = {'width': frame.shape[1], 'height': frame.shape[0], 'frame_id': msg.header.frame_id}
    def json_callback(topic, msg):
        value = json.loads(msg.data)
        if topic in counts:
            counts[topic] += 1
            stamp = value['header']['stamp']
            matched[topic].add((stamp['sec'], stamp['nanosec']))
        else:
            summary['inference'] = value
    for topic in (IMAGE_TOPIC, ANNOTATED_TOPIC):
        node.create_subscription(CompressedImage, topic, lambda m,t=topic: image_callback(t,m), qos_profile_sensor_data)
    for topic in (OBJECT_TOPIC, POSE_TOPIC, STATUS_TOPIC):
        node.create_subscription(String, topic, lambda m,t=topic: json_callback(t,m), qos_profile_sensor_data)
    try:
        until = time.monotonic() + args.seconds
        while time.monotonic() < until:
            rclpy.spin_once(node, timeout_sec=0.2)
        synchronized = set.intersection(*matched.values())
        print(json.dumps({'messages': counts, 'synchronized_frames': len(synchronized), **summary}, indent=2))
        if not all(counts.values()) or not synchronized:
            raise SystemExit('Camera/inference data missing or image/result timestamps do not match')
    finally:
        node.destroy_node()
        rclpy.try_shutdown()

if __name__ == '__main__':
    main()
