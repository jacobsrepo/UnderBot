"""Shared topic contract and local test isolation."""
import os

IMAGE_TOPIC = '/camera/emeet/image/compressed'
ANNOTATED_TOPIC = '/perception/emeet/annotated/compressed'
OBJECT_TOPIC = '/perception/emeet/objects'
POSE_TOPIC = '/perception/emeet/poses'
STATUS_TOPIC = '/perception/emeet/status'
LATENCY_TOPIC = '/perception/emeet/latency_ms'
FRAME_ID = 'emeet_optical_frame'
KEYPOINT_NAMES = [
    'nose', 'left_eye', 'right_eye', 'left_ear', 'right_ear',
    'left_shoulder', 'right_shoulder', 'left_elbow', 'right_elbow',
    'left_wrist', 'right_wrist', 'left_hip', 'right_hip',
    'left_knee', 'right_knee', 'left_ankle', 'right_ankle',
]

def configure_ros(domain):
    # Explicit domain and localhost scope keep this PC test off the robot network.
    os.environ['ROS_DOMAIN_ID'] = str(domain)
    os.environ['ROS_AUTOMATIC_DISCOVERY_RANGE'] = 'LOCALHOST'
    # Fast DDS participant creation crashes in this Windows installation.
    if os.name == 'nt':
        os.environ.setdefault('RMW_IMPLEMENTATION', 'rmw_cyclonedds_cpp')
        os.environ.setdefault('CYCLONEDDS_URI', '<CycloneDDS><Domain><General><Interfaces><NetworkInterface address="127.0.0.1"/></Interfaces><AllowMulticast>false</AllowMulticast></General></Domain></CycloneDDS>')

def header_dict(header):
    return {'stamp': {'sec': header.stamp.sec, 'nanosec': header.stamp.nanosec},
            'frame_id': header.frame_id}
