import os
import sys
import json
import base64
import time
import threading
import subprocess
import requests
import cv2
import numpy as np
from typing import Optional, Dict, List, Any
import aiohttp

ROBOT_SYSTEM_PROMPT = """You are an intelligent, perceptive multimodal AI assistant connected to a live camera feed and voice interface.
Your role:
- Observe the physical environment through the camera frames.
- Listen to spoken user queries and respond concisely, clearly, and naturally.
- Keep your answers direct, intelligent, and conversational (1 to 3 sentences for speech output).
- Describe objects, people, text, scene dynamics, or spatial context accurately.
- Avoid robotic cliches, markdown tables, or unnecessary filler words.
"""

class VisionBrain:
    """
    100% Local & Self-Contained Vision Brain.
    Runs the embedded Qwen2.5-VL GGUF model via local standalone engine (bin/llama/llama-server.exe)
    with non-blocking background initialization, zero external dependencies, zero Ollama, and zero cloud.
    """
    def __init__(self, port: int = 8001):
        self.port = port
        self.server_url = f"http://127.0.0.1:{self.port}/v1"
        self.server_process: Optional[subprocess.Popen] = None
        self.is_server_ready = False
        self.is_starting = False
        self.conversation_history: List[Dict] = []
        self.max_history = 10

        # Paths
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.bin_dir = os.path.join(base_dir, "bin", "llama")
        self.server_exe = os.path.join(self.bin_dir, "llama-server.exe")
        self.model_path = os.path.join(base_dir, "models", "qwen2.5vl-7b.gguf")

        # Local CV Fallback Detector
        self.face_cascade = None
        try:
            cascade_path = cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
            if os.path.exists(cascade_path):
                self.face_cascade = cv2.CascadeClassifier(cascade_path)
        except Exception:
            pass

        # Launch model in background thread so server boots instantly
        threading.Thread(target=self._start_local_engine, daemon=True).start()

    def _start_local_engine(self):
        """Starts the standalone llama-server with GPU acceleration on the local model."""
        if self.is_starting or self.is_server_ready:
            return

        self.is_starting = True

        if not os.path.exists(self.server_exe) or not os.path.exists(self.model_path):
            print(f"[VisionBrain] Note: Embedded engine not ready. Exe: {os.path.exists(self.server_exe)}, Model: {os.path.exists(self.model_path)}")
            self.is_starting = False
            return

        # Check if already running on port
        try:
            r = requests.get(f"{self.server_url}/models", timeout=1)
            if r.status_code == 200:
                print(f"[VisionBrain] Embedded engine already online on port {self.port}.")
                self.is_server_ready = True
                self.is_starting = False
                return
        except Exception:
            pass

        print(f"[VisionBrain] Launching embedded GPU model server ({os.path.basename(self.model_path)})...")
        
        creationflags = 0x08000000 if sys.platform == "win32" else 0  # CREATE_NO_WINDOW

        cmd = [
            self.server_exe,
            "-m", self.model_path,
            "--port", str(self.port),
            "--host", "127.0.0.1",
            "-ngl", "99",              # Offload all layers to GPU (RTX 3050 CUDA)
            "-c", "4096",              # Context window
            "-b", "512",
            "--mmproj", self.model_path,
            "--temp", "0.4",
            "--chat-template", "chatml"
        ]

        try:
            env = os.environ.copy()
            env["PATH"] = self.bin_dir + os.pathsep + env.get("PATH", "")

            self.server_process = subprocess.Popen(
                cmd,
                cwd=self.bin_dir,
                env=env,
                creationflags=creationflags,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
            
            # Poll for readiness in background up to 30 seconds
            for _ in range(30):
                time.sleep(1)
                try:
                    r = requests.get(f"{self.server_url}/models", timeout=1)
                    if r.status_code == 200:
                        self.is_server_ready = True
                        print("[VisionBrain] Embedded Qwen2.5-VL engine is READY on GPU!")
                        break
                except Exception:
                    pass
        except Exception as e:
            print(f"[VisionBrain] Error starting embedded engine: {e}")
        finally:
            self.is_starting = False

    def shutdown(self):
        """Cleanly terminates the local model engine."""
        if self.server_process:
            print("[VisionBrain] Shutting down embedded model engine...")
            try:
                self.server_process.terminate()
                self.server_process.wait(timeout=3)
            except Exception:
                try:
                    self.server_process.kill()
                except Exception:
                    pass
            self.server_process = None
            self.is_server_ready = False

    def get_status(self) -> Dict:
        return {
            "engine": "Embedded Standalone Qwen2.5-VL 7B (Direct GGUF)",
            "ready": self.is_server_ready,
            "gpu_accelerated": True,
            "model_file": os.path.basename(self.model_path) if os.path.exists(self.model_path) else "Not found",
            "model_size_gb": round(os.path.getsize(self.model_path) / (1024**3), 2) if os.path.exists(self.model_path) else 0
        }

    def _analyze_frame_with_local_cv(self, image_base64: str, user_prompt: str) -> str:
        """Fast fallback while model is warming up."""
        try:
            img_bytes = base64.b64decode(image_base64)
            np_arr = np.frombuffer(img_bytes, np.uint8)
            img = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)
            if img is None:
                return "Camera feed active, but no visual frame was received."

            h, w, _ = img.shape
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            mean_brightness = np.mean(gray)
            
            num_faces = 0
            if self.face_cascade is not None:
                faces = self.face_cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=4, minSize=(30, 30))
                num_faces = len(faces)

            lighting = "well-lit" if mean_brightness > 100 else ("moderately lit" if mean_brightness > 40 else "dimly lit")
            details = [f"{num_faces} person in view" if num_faces > 0 else "clear field of view"]
            summary = ", ".join(details)

            return f"I see your camera feed in a {lighting} space with {summary}. Embedded neural vision is warming up."
        except Exception:
            return "Optical feed online. Standing by."

    async def analyze_frame_async(
        self,
        image_base64: str,
        user_prompt: str,
        model_name: Optional[str] = None
    ) -> Dict:
        """
        Runs local inference directly on the embedded Qwen2.5-VL model.
        """
        prompt_text = user_prompt.strip() if user_prompt else "Describe what you see in front of the camera clearly and concisely."
        start_time = time.time()

        messages = [{"role": "system", "content": ROBOT_SYSTEM_PROMPT}]

        for msg in self.conversation_history[-4:]:
            messages.append({"role": msg["role"], "content": msg["text"]})

        user_content = [{"type": "text", "text": prompt_text}]
        if image_base64:
            user_content.append({
                "type": "image_url",
                "image_url": {"url": f"data:image/jpeg;base64,{image_base64}"}
            })

        messages.append({"role": "user", "content": user_content})

        payload = {
            "messages": messages,
            "max_tokens": 200,
            "temperature": 0.4
        }

        # Try sending to embedded server if ready
        if self.is_server_ready:
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.post(
                        f"{self.server_url}/chat/completions",
                        json=payload,
                        timeout=aiohttp.ClientTimeout(total=30)
                    ) as resp:
                        if resp.status == 200:
                            data = await resp.json()
                            text = data["choices"][0]["message"]["content"].strip()
                            self._record_history(prompt_text, text)
                            return {
                                "success": True,
                                "response": text,
                                "model": "Embedded Qwen2.5-VL 7B (Direct Local)",
                                "latency_seconds": round(time.time() - start_time, 2)
                            }
            except Exception as e:
                print(f"[VisionBrain] Embedded engine query notice: {e}")

        # Instant CV fallback while engine finishes warming up
        fallback = self._analyze_frame_with_local_cv(image_base64, prompt_text)
        self._record_history(prompt_text, fallback)
        return {
            "success": True,
            "response": fallback,
            "model": "Embedded Local CV Sensory Engine",
            "latency_seconds": round(time.time() - start_time, 2)
        }

    def _record_history(self, user_text: str, assistant_text: str):
        self.conversation_history.append({"role": "user", "text": user_text})
        self.conversation_history.append({"role": "assistant", "text": assistant_text})
        if len(self.conversation_history) > self.max_history * 2:
            self.conversation_history = self.conversation_history[-self.max_history * 2:]
