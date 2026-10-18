"""Read a named EMEET webcam and publish JPEG frames, without recording."""
import argparse
import json
import os
import time

import cv2
from cv2_enumerate_cameras import enumerate_cameras
import rclpy
from rclpy.node import Node
from sensor_msgs.msg import CompressedImage
from std_msgs.msg import String
from common import configure_ros, IMAGE_TOPIC, FRAME_ID


def choose_camera(name, index=None):
    backend = cv2.CAP_DSHOW if os.name == 'nt' else cv2.CAP_V4L2
    cameras = list(enumerate_cameras(backend))
    for camera in cameras:
        print(f'Camera {camera.index}: {camera.name}', flush=True)
    if index is not None:
        return index, backend, next((c.name for c in cameras if c.index == index), f'index {index}')
    matches = [c for c in cameras if name.casefold() in c.name.casefold()]
    if len(matches) != 1:
        raise RuntimeError(f'Expected one camera matching {name!r}, found {len(matches)}. '
                           'Use --list, then specify --camera-index explicitly.')
    return matches[0].index, backend, matches[0].name


class Camera(Node):
    def __init__(self, cap, name, fps):
        super().__init__('underbot_emeet_camera')
        self.cap, self.name = cap, name
        self.images = self.create_publisher(CompressedImage, IMAGE_TOPIC, 1)
        self.status = self.create_publisher(String, '/camera/emeet/status', 1)
        self.frames = 0
        self.failed = 0
        self.started = time.monotonic()
        self.create_timer(1.0 / fps, self.capture)
        self.create_timer(1.0, self.heartbeat)

    def capture(self):
        ok, frame = self.cap.read()
        if not ok:
            self.failed += 1
            if self.failed >= 15:
                raise RuntimeError('EMEET frame capture failed repeatedly. Check USB connection/camera access.')
            return
        self.failed = 0
        stamp = self.get_clock().now().to_msg()
        ok, jpeg = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 85])
        if not ok:
            raise RuntimeError('JPEG encoding failed')
        msg = CompressedImage()
        msg.header.stamp, msg.header.frame_id = stamp, FRAME_ID
        msg.format, msg.data = 'jpeg', jpeg.tobytes()
        self.images.publish(msg)
        self.frames += 1
        if self.frames == 1:
            self.get_logger().info(f'LIVE CAMERA: {self.name}, {frame.shape[1]}x{frame.shape[0]} -> {IMAGE_TOPIC}')

    def heartbeat(self):
        self.status.publish(String(data=json.dumps({
            'source': self.name, 'live_camera': True, 'recording': False,
            'frames': self.frames, 'capture_ok': self.failed == 0,
            'average_fps': round(self.frames / max(0.01, time.monotonic() - self.started), 2),
        })))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--list', action='store_true')
    parser.add_argument('--camera-name', default='emeet')
    parser.add_argument('--camera-index', type=int)
    parser.add_argument('--domain', type=int, default=74)
    parser.add_argument('--fps', type=float, default=15)
    parser.add_argument('--width', type=int, default=640)
    parser.add_argument('--height', type=int, default=480)
    args = parser.parse_args()
    if args.list:
        backend = cv2.CAP_DSHOW if os.name == 'nt' else cv2.CAP_V4L2
        for camera in enumerate_cameras(backend):
            print(f'{camera.index}: {camera.name}')
        return
    if not 1 <= args.fps <= 60 or min(args.width, args.height) <= 0:
        parser.error('Use 1-60 fps and positive dimensions')
    configure_ros(args.domain)
    index, backend, name = choose_camera(args.camera_name, args.camera_index)
    cap = cv2.VideoCapture(index, backend)
    node = None
    try:
        if not cap.isOpened():
            raise RuntimeError(f'Cannot open {name}. Close other camera apps and check Windows camera permission.')
        cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*'MJPG'))
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, args.width)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, args.height)
        cap.set(cv2.CAP_PROP_FPS, args.fps)
        rclpy.init()
        node = Camera(cap, name, args.fps)
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        cap.release()
        if node is not None:
            node.destroy_node()
            rclpy.try_shutdown()


if __name__ == '__main__':
    main()
