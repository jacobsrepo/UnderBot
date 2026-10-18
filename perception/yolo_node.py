"""Subscribe to ROS images; publish YOLO objects, human keypoints and annotation."""
import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import time

ROOT = Path(__file__).resolve().parent
(ROOT / '.ultralytics').mkdir(exist_ok=True)
os.environ.setdefault('YOLO_CONFIG_DIR', str(ROOT / '.ultralytics'))
os.environ.setdefault('YOLO_AUTOINSTALL', 'false')

import cv2
import numpy as np
import rclpy
from rclpy.node import Node
from rclpy.qos import qos_profile_sensor_data
from sensor_msgs.msg import CompressedImage
from std_msgs.msg import Float32, String
import torch
from ultralytics import YOLO, settings
settings.update({'sync': False})
from common import (configure_ros, header_dict, IMAGE_TOPIC, ANNOTATED_TOPIC,
                    OBJECT_TOPIC, POSE_TOPIC, STATUS_TOPIC, KEYPOINT_NAMES, LATENCY_TOPIC)


def boxes(result):
    if result.boxes is None:
        return []
    output = []
    for xyxy, confidence, class_id in zip(result.boxes.xyxy.cpu().tolist(),
                                         result.boxes.conf.cpu().tolist(),
                                         result.boxes.cls.cpu().tolist()):
        output.append({'class_id': int(class_id), 'label': result.names[int(class_id)],
                       'confidence': float(confidence), 'xyxy': xyxy})
    return output


def people(result):
    output = boxes(result)
    if result.keypoints is not None:
        for person, points in zip(output, result.keypoints.data.cpu().tolist()):
            person['keypoints'] = [
                {'name': KEYPOINT_NAMES[i], 'x': p[0], 'y': p[1],
                 'confidence': p[2] if len(p) > 2 else None}
                for i, p in enumerate(points)
            ]
    return output


class Perception(Node):
    def __init__(self, topic):
        super().__init__('underbot_yolo_perception')
        self.latest = None
        self.create_subscription(CompressedImage, topic, self.receive, qos_profile_sensor_data)
        self.annotated = self.create_publisher(CompressedImage, ANNOTATED_TOPIC, 1)
        self.objects = self.create_publisher(String, OBJECT_TOPIC, 1)
        self.poses = self.create_publisher(String, POSE_TOPIC, 1)
        self.status = self.create_publisher(String, STATUS_TOPIC, 1)
        self.latency = self.create_publisher(Float32, LATENCY_TOPIC, 1)

    def receive(self, message):
        self.latest = message


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--domain', type=int, default=74)
    parser.add_argument('--memory-config', help='Opt-in PostgreSQL identity configuration')
    parser.add_argument('--network', action='store_true', help='Use configured robot ROS discovery')
    parser.add_argument('--input-topic', default=IMAGE_TOPIC)
    parser.add_argument('--device', default='cpu')
    parser.add_argument('--imgsz', type=int, default=416)
    parser.add_argument('--confidence', type=float, default=0.35)
    parser.add_argument('--max-fps', type=float, default=5)
    parser.add_argument('--threads', type=int, default=4)
    parser.add_argument('--object-model', default=str(ROOT / 'models/yolo26n.pt'))
    parser.add_argument('--pose-model', default=str(ROOT / 'models/yolo26n-pose.pt'))
    args = parser.parse_args()
    if not 0 < args.confidence < 1 or args.max_fps <= 0 or args.imgsz < 32 or args.threads < 1:
        parser.error('Invalid confidence, rate, image size or thread count')
    if args.network:
        os.environ['ROS_DOMAIN_ID'] = str(args.domain)
    else:
        configure_ros(args.domain)
    torch.set_num_threads(args.threads)
    (ROOT / 'models').mkdir(exist_ok=True)
    print('Loading YOLO object and human-pose models (first run downloads weights).', flush=True)
    objects_model, pose_model = YOLO(args.object_model), YOLO(args.pose_model)
    if objects_model.task != 'detect' or pose_model.task != 'pose':
        raise ValueError('Expected an object-detection model and a human-pose model')
    rclpy.init()
    node = Perception(args.input_topic)
    recognition = None
    if args.memory_config:
        try:
            from memory.runtime import Recognition
            recognition = Recognition(args.memory_config, ROOT/'models')
        except Exception as exc:
            print(f'Identity unavailable ({type(exc).__name__}); generic detection continues.', flush=True)
    processed = 0
    next_frame = 0.0
    last_status = 0.0
    options = dict(device=args.device, imgsz=args.imgsz, conf=args.confidence, verbose=False)
    try:
        while rclpy.ok():
            rclpy.spin_once(node, timeout_sec=0.01)
            now = time.monotonic()
            if node.latest is None:
                if now - last_status > 1:
                    node.status.publish(String(data=json.dumps({'state': 'waiting_for_camera', 'processed': processed})))
                    last_status = now
                continue
            if now < next_frame:
                continue
            msg, node.latest = node.latest, None
            capture_ns = msg.header.stamp.sec * 1_000_000_000 + msg.header.stamp.nanosec
            if node.get_clock().now().nanoseconds - capture_ns > 2_000_000_000:
                continue
            frame = cv2.imdecode(np.frombuffer(bytes(msg.data), dtype=np.uint8), cv2.IMREAD_COLOR)
            if frame is None:
                node.get_logger().warning('Invalid compressed image; skipped')
                continue
            begin = time.perf_counter()
            objects = objects_model.predict(frame, **options)[0]
            pose = pose_model.predict(frame, **options)[0]
            inference_ms = (time.perf_counter() - begin) * 1000
            if node.get_clock().now().nanoseconds - capture_ns > 2_000_000_000:
                node.status.publish(String(data=json.dumps({
                    'state': 'discarded_stale_result', 'inference_ms': round(inference_ms, 1),
                    'processed': processed,
                })))
                # Never present an inference result from a long CPU stall as fresh.
                continue
            # Both models see the same original pixels; annotations are composed afterward.
            annotated = pose.plot(img=objects.plot(), boxes=False)
            cv2.putText(annotated, f'LIVE EMEET | YOLO objects + human pose | {inference_ms:.0f} ms',
                        (10, 23), cv2.FONT_HERSHEY_SIMPLEX, 0.43, (0, 255, 255), 1, cv2.LINE_AA)
            object_data, pose_data = boxes(objects), people(pose)
            recognition_state = 'disabled'
            if recognition:
                try:
                    recognition_state = recognition.annotate(frame, annotated, object_data, datetime.fromtimestamp(capture_ns / 1e9, timezone.utc))
                    for person in pose_data:
                        person['identity'] = None
                        matches = [o for o in object_data if o.get('identity') and o['xyxy'][0] <= (person['xyxy'][0]+person['xyxy'][2])/2 <= o['xyxy'][2] and o['xyxy'][1] <= (person['xyxy'][1]+person['xyxy'][3])/2 <= o['xyxy'][3]]
                        if len(matches) == 1: person['identity'] = matches[0]['identity']
                except Exception:
                    recognition_state = 'unavailable'
            if node.get_clock().now().nanoseconds - capture_ns > 2_000_000_000:
                continue
            ok, jpeg = cv2.imencode('.jpg', annotated, [cv2.IMWRITE_JPEG_QUALITY, 85])
            if not ok:
                raise RuntimeError('Annotated JPEG encoding failed')
            image = CompressedImage()
            image.header, image.format, image.data = msg.header, 'jpeg', jpeg.tobytes()
            node.annotated.publish(image)
            base = {'schema_version': 1, 'header': header_dict(msg.header),
                    'recognition_state': recognition_state,
                    'image_width': frame.shape[1], 'image_height': frame.shape[0],
                    'coordinates': 'pixels_top_left_origin', 'inference_ms': inference_ms}
            node.objects.publish(String(data=json.dumps({**base, 'model': Path(args.object_model).name, 'objects': object_data})))
            node.poses.publish(String(data=json.dumps({**base, 'model': Path(args.pose_model).name, 'people': pose_data})))
            processed += 1
            age_ms = (node.get_clock().now().nanoseconds - capture_ns) / 1e6
            node.latency.publish(Float32(data=float(age_ms)))
            node.status.publish(String(data=json.dumps({
                'state': 'running', 'recognition_state': recognition_state, 'processed': processed, 'device': args.device,
                'inference_ms': round(inference_ms, 1), 'objects': len(object_data),
                'people': len(pose_data), 'source': args.input_topic,
                'image_age_ms': round(age_ms, 1),
                'recording': False,
            })))
            last_status = time.monotonic()
            if processed == 1 or processed % 100 == 0:
                print(f'Processed {processed} frames; inference {inference_ms:.0f} ms; '
                      f'{len(object_data)} objects, {len(pose_data)} people', flush=True)
            next_frame = now + 1.0 / args.max_fps
    except KeyboardInterrupt:
        pass
    finally:
        if recognition:
            recognition.close()
        node.destroy_node()
        rclpy.try_shutdown()


if __name__ == '__main__':
    main()
