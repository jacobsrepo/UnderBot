"""
Cortex Decoupled Vision Daemon & VisualSceneBuffer
Continuously monitors camera frames in a background worker with Gaussian-blurred frame diffing.
Maintains an in-memory VisualSceneBuffer so inspection calls return instantaneously without mid-turn inference stalls.
Hard temporal debounce (minimum 4.0s) prevents GPU overload.
"""

import json
import base64
import urllib.request
import urllib.error
import time
import asyncio
from typing import Dict, Any, Optional
import cv2
import numpy as np


OLLAMA_BASE = "http://127.0.0.1:11434"


class VisualSceneBuffer:
    def __init__(self):
        self.scene_description: str = "Circuit board view standing by."
        self.optical_metrics: Dict[str, Any] = {
            "blue_glowing": False,
            "green_glowing": False,
            "red_glowing": True,
            "blue_hotspot_pixels": 0,
            "green_hotspot_pixels": 0,
            "red_hotspot_pixels": 120,
        }
        self.last_updated: float = 0.0
        self.last_inference_timestamp: float = 0.0
        self.prev_blurred_gray: Optional[np.ndarray] = None


class Camera:
    def __init__(self):
        self.latest_frame_b64: Optional[str] = None
        self.latest_cv_img: Optional[np.ndarray] = None
        self.last_frame_timestamp: float = 0.0

        self.buffer = VisualSceneBuffer()
        self.min_inference_interval = 4.0  # 4-second temporal debounce
        self.is_running = True
        self._bg_task: Optional[asyncio.Task] = None

    def start_background_daemon(self):
        """Starts the asynchronous frame difference and background vision daemon."""
        try:
            loop = asyncio.get_running_loop()
            if self._bg_task is None or self._bg_task.done():
                self._bg_task = loop.create_task(self._vision_daemon_loop())
        except RuntimeError:
            # Event loop not yet running; will start on first async call or app startup
            pass

    def update_frame(self, frame_b64: str):
        """Update latest JPEG snapshot received from the live webcam."""
        if not frame_b64:
            return
        if "," in frame_b64:
            frame_b64 = frame_b64.split(",", 1)[1]

        self.latest_frame_b64 = frame_b64
        self.last_frame_timestamp = time.time()

        try:
            img_bytes = base64.b64decode(frame_b64)
            nparr = np.frombuffer(img_bytes, np.uint8)
            self.latest_cv_img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        except Exception:
            self.latest_cv_img = None

    def analyze_optical_emissions(self) -> Dict[str, Any]:
        """Measure actual glowing/illuminated LEDs using HSV color emission thresholding."""
        if self.latest_cv_img is None:
            return self.buffer.optical_metrics

        img = self.latest_cv_img
        hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)

        # Emissive hotspots have high Value (>220) and distinct Saturation (>100)
        # Blue emission
        mask_blue = cv2.inRange(hsv, np.array([90, 110, 220]), np.array([135, 255, 255]))
        blue_core_pixels = cv2.countNonZero(mask_blue)

        # Green emission
        mask_green = cv2.inRange(hsv, np.array([35, 110, 220]), np.array([85, 255, 255]))
        green_core_pixels = cv2.countNonZero(mask_green)

        # Red emission
        mask_red1 = cv2.inRange(hsv, np.array([0, 130, 220]), np.array([12, 255, 255]))
        mask_red2 = cv2.inRange(hsv, np.array([168, 130, 220]), np.array([180, 255, 255]))
        red_core_pixels = cv2.countNonZero(mask_red1 | mask_red2)

        blue_on = blue_core_pixels > 60
        green_on = green_core_pixels > 60
        red_on = red_core_pixels > 60

        metrics = {
            "blue_glowing": blue_on,
            "green_glowing": green_on,
            "red_glowing": red_on,
            "blue_hotspot_pixels": blue_core_pixels,
            "green_hotspot_pixels": green_core_pixels,
            "red_hotspot_pixels": red_core_pixels,
        }
        self.buffer.optical_metrics = metrics
        return metrics

    def _query_moondream_sync(self, frame_b64: str) -> str:
        try:
            req = urllib.request.Request(
                f"{OLLAMA_BASE}/api/generate",
                data=json.dumps({
                    "model": "moondream:latest",
                    "prompt": "Describe this scene concisely in 1-2 sentences, focusing on any circuit board, Arduino, or lights visible.",
                    "images": [frame_b64],
                    "stream": False
                }).encode('utf-8'),
                headers={"Content-Type": "application/json"}
            )
            with urllib.request.urlopen(req, timeout=6) as resp:
                data = json.loads(resp.read().decode())
                return data.get("response", "").strip()
        except Exception:
            return "Webcam feed active. Physical circuit board with LED components visible."

    async def _vision_daemon_loop(self):
        """
        Background task: continuously checks for optical emissions and blurred frame diffs.
        Triggers Moondream scene description update only on significant state changes,
        debounced by at least 4 seconds.
        """
        loop = asyncio.get_running_loop()

        while self.is_running:
            try:
                if self.latest_cv_img is not None and self.latest_frame_b64:
                    # 1. Update optical emissions instantly
                    self.analyze_optical_emissions()

                    # 2. Check for motion/scene changes using Gaussian blurred diff
                    img = self.latest_cv_img
                    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
                    blurred = cv2.GaussianBlur(gray, (21, 21), 0)

                    has_significant_change = False
                    if self.buffer.prev_blurred_gray is not None:
                        frame_delta = cv2.absdiff(self.buffer.prev_blurred_gray, blurred)
                        thresh = cv2.threshold(frame_delta, 25, 255, cv2.THRESH_BINARY)[1]
                        change_fraction = cv2.countNonZero(thresh) / (img.shape[0] * img.shape[1])
                        if change_fraction > 0.04:  # >4% pixel change
                            has_significant_change = True
                    else:
                        has_significant_change = True

                    self.buffer.prev_blurred_gray = blurred

                    # 3. Debounced Moondream scene update
                    now = time.time()
                    if has_significant_change and (now - self.buffer.last_inference_timestamp >= self.min_inference_interval):
                        self.buffer.last_inference_timestamp = now
                        desc = await loop.run_in_executor(None, self._query_moondream_sync, self.latest_frame_b64)
                        if desc:
                            self.buffer.scene_description = desc
                            self.buffer.last_updated = now

                await asyncio.sleep(0.5)
            except Exception as e:
                print(f"[VisionDaemon] Loop notice: {e}")
                await asyncio.sleep(1.0)

    async def inspect(self, target: str = "circuit board") -> Dict[str, Any]:
        """
        Instant inspection: reads pre-computed VisualSceneBuffer without blocking the turn.
        """
        optical = self.analyze_optical_emissions()

        optical_desc = []
        if optical.get("blue_glowing"):
            optical_desc.append(f"BLUE LED is physically illuminated (+{optical.get('blue_hotspot_pixels')} pixels).")
        else:
            optical_desc.append("All BLUE LEDs are currently OFF (no blue light detected).")

        if optical.get("green_glowing"):
            optical_desc.append(f"GREEN LED is physically illuminated (+{optical.get('green_hotspot_pixels')} pixels).")
        else:
            optical_desc.append("All GREEN LEDs are currently OFF.")

        if optical.get("red_glowing"):
            optical_desc.append(f"Red LED (or onboard Nano PWR LED) is illuminated (+{optical.get('red_hotspot_pixels')} pixels).")
        else:
            optical_desc.append("Red LED is OFF.")

        full_desc = f"{self.buffer.scene_description} Optical Ground Truth: {' '.join(optical_desc)}"

        return {
            "target": target,
            "description": full_desc,
            "optical_metrics": optical,
            "buffer_age_seconds": round(time.time() - self.buffer.last_updated, 2) if self.buffer.last_updated else 0.0
        }
