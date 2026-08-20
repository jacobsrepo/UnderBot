import cv2
import threading
import time
import base64
import platform
from typing import Optional, Tuple, List, Dict

class CameraManager:
    """
    Universal Camera Manager.
    Supports:
    - Any local USB / laptop webcam / virtual camera (Camo, OBS, Integrated)
    - Browser Client-Side Camera (frames streamed directly from phone/laptop browser)
    - Multi-platform backends (Windows MSMF/DSHOW, Linux V4L2, macOS AVFoundation)
    """
    def __init__(self, device_index: int = 0):
        self.device_index = device_index
        self.cap: Optional[cv2.VideoCapture] = None
        self.latest_frame = None
        self.latest_jpeg = None
        self.latest_base64 = None
        self.is_running = False
        self.is_client_stream = False  # True when using browser webcam
        self.lock = threading.Lock()
        self.fps = 0.0
        self.frame_count = 0
        self.last_frame_time = 0
        self.thread: Optional[threading.Thread] = None
        self.width = 1280
        self.height = 720
        self.os_type = platform.system()

    def start(self, device_index: Optional[int] = None) -> bool:
        if device_index is not None:
            self.device_index = device_index

        self.stop()
        self.is_client_stream = False

        print(f"[CameraManager] Initializing camera device index {self.device_index} on {self.os_type}...")
        
        # Pick best platform-specific backend list
        backends = []
        if self.os_type == "Windows":
            backends = [cv2.CAP_MSMF, cv2.CAP_DSHOW, cv2.CAP_ANY]
        elif self.os_type == "Darwin":  # macOS
            backends = [cv2.CAP_AVFOUNDATION, cv2.CAP_ANY]
        elif self.os_type == "Linux":
            backends = [cv2.CAP_V4L2, cv2.CAP_ANY]
        else:
            backends = [cv2.CAP_ANY]

        for backend in backends:
            try:
                cap = cv2.VideoCapture(self.device_index, backend)
                if cap.isOpened():
                    self.cap = cap
                    print(f"[CameraManager] Opened successfully with backend: {backend}")
                    break
                cap.release()
            except Exception:
                pass

        if not self.cap or not self.cap.isOpened():
            # Last fallback
            try:
                self.cap = cv2.VideoCapture(self.device_index)
            except Exception:
                pass

        if not self.cap or not self.cap.isOpened():
            print(f"[CameraManager] Note: Local camera {self.device_index} not opened. Standing by for browser webcam stream.")
            return False

        try:
            self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.width)
            self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.height)
            self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
        except Exception:
            pass

        self.is_running = True
        self.thread = threading.Thread(target=self._capture_loop, daemon=True)
        self.thread.start()
        print(f"[CameraManager] Camera worker active (Device {self.device_index})")
        return True

    def stop(self):
        self.is_running = False
        if self.thread and self.thread.is_alive():
            self.thread.join(timeout=1.0)
        if self.cap:
            try:
                self.cap.release()
            except Exception:
                pass
            self.cap = None

    def update_client_frame(self, image_base64: str):
        """
        Accepts a live frame sent directly from the client's browser webcam.
        Enables instant use on mobile phones, tablets, or laptops over the network.
        """
        try:
            img_bytes = base64.b64decode(image_base64)
            with self.lock:
                self.latest_base64 = image_base64
                self.latest_jpeg = img_bytes
                self.frame_count += 1
                self.last_frame_time = time.time()
                self.is_client_stream = True
        except Exception as e:
            print(f"[CameraManager] Error decoding client frame: {e}")

    def _capture_loop(self):
        fps_counter = 0
        fps_timer = time.time()

        while self.is_running and self.cap and self.cap.isOpened():
            ret, frame = self.cap.read()
            if not ret or frame is None:
                time.sleep(0.02)
                continue

            try:
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
                pass

            fps_counter += 1
            if time.time() - fps_timer >= 1.0:
                self.fps = fps_counter / (time.time() - fps_timer)
                fps_counter = 0
                fps_timer = time.time()

            time.sleep(0.01)

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
                "is_running": self.is_running or self.is_client_stream,
                "is_client_stream": self.is_client_stream,
                "fps": round(self.fps, 1) if not self.is_client_stream else 30.0,
                "frame_count": self.frame_count,
                "has_frame": self.latest_base64 is not None,
                "resolution": f"{self.width}x{self.height}"
            }

    @staticmethod
    def list_available_cameras(max_tested: int = 6) -> List[Dict]:
        found = []
        os_name = platform.system()

        for i in range(max_tested):
            opened = False
            backends = [cv2.CAP_MSMF, cv2.CAP_DSHOW, cv2.CAP_ANY] if os_name == "Windows" else [cv2.CAP_ANY]
            
            for backend in backends:
                try:
                    cap = cv2.VideoCapture(i, backend)
                    if cap.isOpened():
                        ret, _ = cap.read()
                        cap.release()
                        name = "Integrated / Camo Camera" if i == 0 else f"Camera Device {i}"
                        found.append({
                            "index": i,
                            "name": f"{name} (Index {i})",
                            "accessible": bool(ret)
                        })
                        opened = True
                        break
                    cap.release()
                except Exception:
                    pass
            if not opened:
                try:
                    cap = cv2.VideoCapture(i)
                    if cap.isOpened():
                        ret, _ = cap.read()
                        cap.release()
                        found.append({
                            "index": i,
                            "name": f"Camera Device {i}",
                            "accessible": bool(ret)
                        })
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
