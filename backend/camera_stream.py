import cv2
import threading
import time
import base64
from typing import Optional, Tuple, List, Dict

class CameraManager:
    """
    Manages video capture from local cameras (including Camo Studio virtual camera).
    Runs a persistent background thread to keep the latest frame buffer fresh with zero lag.
    """
    def __init__(self, device_index: int = 0):
        self.device_index = device_index
        self.cap: Optional[cv2.VideoCapture] = None
        self.latest_frame = None
        self.latest_jpeg = None
        self.latest_base64 = None
        self.is_running = False
        self.lock = threading.Lock()
        self.fps = 0.0
        self.frame_count = 0
        self.last_frame_time = 0
        self.thread: Optional[threading.Thread] = None
        self.width = 1280
        self.height = 720

    def start(self, device_index: Optional[int] = None) -> bool:
        if device_index is not None:
            self.device_index = device_index

        self.stop()

        print(f"[CameraManager] Initializing camera device index {self.device_index}...")
        # Try Windows Media Foundation first (most reliable in server processes)
        for backend in [cv2.CAP_MSMF, cv2.CAP_DSHOW, cv2.CAP_ANY]:
            cap = cv2.VideoCapture(self.device_index, backend)
            if cap.isOpened():
                self.cap = cap
                print(f"[CameraManager] Opened with backend: {backend}")
                break
            cap.release()

        if not self.cap or not self.cap.isOpened():
            # Last resort: default index with no backend hint
            self.cap = cv2.VideoCapture(self.device_index)

        if not self.cap or not self.cap.isOpened():
            print(f"[CameraManager] Failed to open camera device index {self.device_index}")
            return False

        # Configure preferred resolution
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.width)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.height)
        self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
        time.sleep(0.5)  # Let device stabilize before first read

        self.is_running = True
        self.thread = threading.Thread(target=self._capture_loop, daemon=True)
        self.thread.start()
        print(f"[CameraManager] Camera started successfully (Index {self.device_index})")
        return True

    def stop(self):
        self.is_running = False
        if self.thread and self.thread.is_alive():
            self.thread.join(timeout=1.0)
        if self.cap:
            self.cap.release()
            self.cap = None

    def _capture_loop(self):
        fps_counter = 0
        fps_timer = time.time()

        while self.is_running and self.cap and self.cap.isOpened():
            ret, frame = self.cap.read()
            if not ret or frame is None:
                time.sleep(0.01)
                continue

            # Encode to JPEG
            _, jpeg_buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 85])
            jpeg_bytes = jpeg_buffer.tobytes()
            b64_str = base64.b64encode(jpeg_bytes).decode('utf-8')

            with self.lock:
                self.latest_frame = frame
                self.latest_jpeg = jpeg_bytes
                self.latest_base64 = b64_str
                self.frame_count += 1
                self.last_frame_time = time.time()

            fps_counter += 1
            if time.time() - fps_timer >= 1.0:
                self.fps = fps_counter / (time.time() - fps_timer)
                fps_counter = 0
                fps_timer = time.time()

            time.sleep(0.01)  # Yield CPU

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
                "device_index": self.device_index,
                "is_running": self.is_running,
                "fps": round(self.fps, 1),
                "frame_count": self.frame_count,
                "has_frame": self.latest_frame is not None,
                "resolution": f"{self.width}x{self.height}"
            }

    @staticmethod
    def list_available_cameras(max_tested: int = 5) -> List[Dict]:
        found = []
        for i in range(max_tested):
            opened = False
            for backend in [cv2.CAP_MSMF, cv2.CAP_ANY]:
                cap = cv2.VideoCapture(i, backend)
                if cap.isOpened():
                    time.sleep(0.2)
                    ret, _ = cap.read()
                    cap.release()
                    label = "Camo Studio" if i == 0 else f"Camera Device {i}"
                    found.append({
                        "index": i,
                        "name": f"{label} (Device {i})",
                        "accessible": bool(ret)
                    })
                    opened = True
                    break
                cap.release()
        return found

    def generate_mjpeg_stream(self):
        """Generator for FastAPI StreamingResponse MJPEG"""
        while self.is_running:
            jpeg = self.get_latest_frame_jpeg()
            if jpeg is not None:
                yield (b'--frame\r\n'
                       b'Content-Type: image/jpeg\r\n\r\n' + jpeg + b'\r\n')
            else:
                time.sleep(0.1)  # Wait for first frame
                continue
            time.sleep(0.033)  # ~30 FPS
