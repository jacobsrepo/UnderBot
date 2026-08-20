import os
import sys

# Completely silence OpenCV C++ internal stderr logging
os.environ["OPENCV_LOG_LEVEL"] = "SILENT"
os.environ["OPENCV_VIDEOIO_DEBUG"] = "0"
os.environ["OPENCV_VIDEOIO_PRIORITY_MSMF"] = "0"

import cv2
try:
    cv2.setLogLevel(0)
except Exception:
    pass

import threading
import time
import base64
import platform
from typing import Optional, List, Dict

class CameraManager:
    """
    Zero-warning camera manager.
    Relies primarily on client-side browser webcam frames.
    Host camera access is purely on-demand with DirectShow to avoid MSMF errors.
    """
    def __init__(self, device_index: int = 0):
        self.device_index = device_index
        self.cap: Optional[cv2.VideoCapture] = None
        self.latest_frame = None
        self.latest_jpeg = None
        self.latest_base64 = None
        self.is_running = False
        self.is_client_stream = True  # Default to browser stream
        self.lock = threading.Lock()
        self.fps = 30.0
        self.frame_count = 0
        self.last_frame_time = 0
        self.thread: Optional[threading.Thread] = None
        self.width = 1280
        self.height = 720
        self.os_type = platform.system()

    def start(self, device_index: Optional[int] = None) -> bool:
        """Starts host camera capture only when explicitly requested."""
        if device_index is not None:
            self.device_index = device_index

        self.stop()
        self.is_client_stream = False

        # Only use DirectShow on Windows to avoid MSMF and FFMPEG warnings
        backend = cv2.CAP_DSHOW if self.os_type == "Windows" else cv2.CAP_ANY

        try:
            cap = cv2.VideoCapture(self.device_index, backend)
            if cap and cap.isOpened():
                self.cap = cap
                self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.width)
                self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.height)
                self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
                self.is_running = True
                self.thread = threading.Thread(target=self._capture_loop, daemon=True)
                self.thread.start()
                return True
        except Exception:
            pass

        self.is_client_stream = True
        return False

    def stop(self):
        self.is_running = False
        if self.thread and self.thread.is_alive():
            self.thread.join(timeout=0.5)
        if self.cap:
            try:
                self.cap.release()
            except Exception:
                pass
            self.cap = None

    def update_client_frame(self, image_base64: str):
        """Updates frame buffer with browser webcam snapshot."""
        try:
            img_bytes = base64.b64decode(image_base64)
            with self.lock:
                self.latest_base64 = image_base64
                self.latest_jpeg = img_bytes
                self.frame_count += 1
                self.last_frame_time = time.time()
                self.is_client_stream = True
        except Exception:
            pass

    def _capture_loop(self):
        while self.is_running and self.cap and self.cap.isOpened():
            try:
                ret, frame = self.cap.read()
                if not ret or frame is None:
                    time.sleep(0.1)
                    continue

                _, jpeg_buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 85])
                jpeg_bytes = jpeg_buffer.tobytes()
                b64_str = base64.b64encode(jpeg_bytes).decode('utf-8')

                with self.lock:
                    self.latest_frame = frame
                    self.latest_jpeg = jpeg_bytes
                    self.latest_base64 = b64_str
                    self.frame_count += 1
                    self.last_frame_time = time.time()
            except Exception:
                time.sleep(0.1)

            time.sleep(0.033)

    def get_latest_frame_cv2(self):
        with self.lock:
            return self.latest_frame.copy() if self.latest_frame is not None else None

    def get_latest_frame_jpeg(self) -> Optional[bytes]:
        with self.lock:
            return self.latest_jpeg

    def get_latest_frame_base64(self) -> Optional[str]:
        with self.lock:
            return self.latest_base64

    def get_stats(self) -> Dict:
        with self.lock:
            return {
                "source": "Browser Webcam" if self.is_client_stream else f"Host Camera {self.device_index}",
                "active": self.latest_base64 is not None,
                "frame_count": self.frame_count,
                "resolution": f"{self.width}x{self.height}"
            }

    @staticmethod
    def list_available_cameras() -> List[Dict]:
        """Safe camera discovery using DSHOW only on Windows."""
        found = []
        os_name = platform.system()
        backend = cv2.CAP_DSHOW if os_name == "Windows" else cv2.CAP_ANY

        for i in range(2):
            try:
                cap = cv2.VideoCapture(i, backend)
                if cap and cap.isOpened():
                    ret, _ = cap.read()
                    cap.release()
                    label = "Default Camera 0 (Camo / Webcam)" if i == 0 else f"Camera Device {i}"
                    found.append({"index": i, "name": label, "accessible": bool(ret)})
            except Exception:
                pass
        return found

    def generate_mjpeg_stream(self):
        while True:
            jpeg = self.get_latest_frame_jpeg()
            if jpeg is not None:
                yield (b'--frame\r\n'
                       b'Content-Type: image/jpeg\r\n\r\n' + jpeg + b'\r\n')
            else:
                time.sleep(0.1)
                continue
            time.sleep(0.033)
