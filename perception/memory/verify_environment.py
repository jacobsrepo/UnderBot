"""Deployment imports and ROS message construction without attached hardware."""
import json
import cv2
import psycopg
import torch
import rclpy
from sensor_msgs.msg import CompressedImage
from std_msgs.msg import String
from .face import FaceEngine
from pathlib import Path
rclpy.init()
node=rclpy.create_node('underbot_deployment_check')
node.create_publisher(CompressedImage,'/underbot_deployment_check/image',1)
node.create_publisher(String,'/underbot_deployment_check/status',1)
node.destroy_node();rclpy.shutdown()
FaceEngine(Path(__file__).resolve().parents[1]/'models')
assert torch.version.cuda is None
print(json.dumps({'ros_jazzy_imports':'ok','opencv':cv2.__version__,'torch':torch.__version__,'postgres_driver':psycopg.__version__,'face_models':'loaded'}))
