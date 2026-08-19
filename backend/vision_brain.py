import os
import json
import base64
import requests
import time
import cv2
import numpy as np
from typing import Optional, Dict, List, Generator, AsyncGenerator
import aiohttp

ROBOT_SYSTEM_PROMPT = """You are the sensory visual cortex and cognitive brain of an advanced intelligent robot.
You receive real-time camera imagery of your physical surroundings (streamed via Camo camera) and spoken queries from the user.
Your personality:
- Highly intelligent, sharp, observant, and concise.
- You speak with an authoritative, natural male tone suitable for voice text-to-speech output.
- When the user asks what you see, describe the physical scene, key objects, people, actions, spatial layout, or text accurately.
- Keep spoken responses conversational, vivid, and punchy (1-3 sentences for quick conversation, or detailed when explicitly asked).
- Avoid robotic cliches, markdown tables, or raw formatting that sounds unnatural when spoken aloud.
"""

class VisionBrain:
    """
    Vision-Language cognitive engine.
    Supports Qwen2.5-VL via Ollama, with automated sensory CV fallback when offline.
    """
    def __init__(self, ollama_url: str = "http://127.0.0.1:11434", default_model: str = "qwen2.5vl:7b"):
        self.ollama_url = ollama_url.rstrip("/")
        self.default_model = default_model
        self.conversation_history: List[Dict] = []
        self.max_history = 10
        
        # Load standard Haar Cascade for face/object detection fallback
        self.face_cascade = None
        try:
            cascade_path = cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
            if os.path.exists(cascade_path):
                self.face_cascade = cv2.CascadeClassifier(cascade_path)
        except Exception:
            pass

    def check_ollama_status(self) -> Dict:
        try:
            r = requests.get(f"{self.ollama_url}/api/tags", timeout=1.5)
            if r.status_code == 200:
                data = r.json()
                models = [m.get("name", "") for m in data.get("models", [])]
                return {
                    "online": True,
                    "models": models,
                    "selected_model": self.default_model,
                    "has_selected_model": any(self.default_model in m for m in models)
                }
        except Exception:
            pass
        return {
            "online": False,
            "models": [],
            "selected_model": self.default_model,
            "note": "Install or run Ollama to enable full Qwen-VL reasoning."
        }

    def set_model(self, model_name: str):
        self.default_model = model_name
        print(f"[VisionBrain] Model switched to: {model_name}")

    def clear_history(self):
        self.conversation_history = []
        print("[VisionBrain] Conversation history cleared.")

    def _analyze_frame_with_cv(self, image_base64: str, user_prompt: str) -> str:
        """
        Fast local computer-vision fallback when Ollama is starting up or offline.
        Analyzes brightness, texture, human presence, and responds intelligently.
        """
        try:
            img_bytes = base64.b64decode(image_base64)
            np_arr = np.frombuffer(img_bytes, np.uint8)
            img = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)
            
            if img is None:
                return "My camera feed is active, but the sensory buffer received an empty frame."

            h, w, _ = img.shape
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            mean_brightness = np.mean(gray)
            
            # Detect faces
            num_faces = 0
            if self.face_cascade is not None:
                faces = self.face_cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=4, minSize=(30, 30))
                num_faces = len(faces)

            # Detect edges/complexity
            edges = cv2.Canny(gray, 100, 200)
            edge_density = np.count_nonzero(edges) / (h * w)

            lighting = "well-lit" if mean_brightness > 100 else ("dimly lit" if mean_brightness > 40 else "very dark")
            
            observations = []
            if num_faces > 0:
                observations.append(f"I detect {num_faces} person directly in front of the lens")
            if edge_density > 0.05:
                observations.append("the environment has high visual detail with structured objects and surfaces")
            else:
                observations.append("the view is relatively open or focused on a clean plane")

            obs_str = " and ".join(observations)
            
            if "what do you see" in user_prompt.lower() or "describe" in user_prompt.lower() or "scan" in user_prompt.lower():
                return f"I can see your live camera feed in a {lighting} room. {obs_str.capitalize()}. To enable full Qwen-VL deep visual reasoning, run OllamaSetup."
            else:
                return f"I received your query: '{user_prompt}'. I am tracking your live camera feed ({w}x{h} at {lighting} lighting). Ollama is currently starting up to unlock full neural reasoning."
        except Exception as e:
            return f"I heard you ask '{user_prompt}'. My optical cortex is active, standing by for neural model connection."

    async def analyze_frame_async(
        self,
        image_base64: str,
        user_prompt: str,
        model_name: Optional[str] = None
    ) -> Dict:
        """
        Sends the live camera image and prompt to Qwen-VL via Ollama, with CV fallback if offline.
        """
        model = model_name or self.default_model
        start_time = time.time()
        prompt_text = user_prompt if user_prompt else "Describe what you see in front of you clearly and concisely."

        payload = {
            "model": model,
            "prompt": prompt_text,
            "system": ROBOT_SYSTEM_PROMPT,
            "images": [image_base64] if image_base64 else [],
            "stream": False,
            "options": {
                "temperature": 0.4,
                "top_p": 0.9,
                "num_predict": 250
            }
        }

        # Try connecting to Ollama
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.ollama_url}/api/generate",
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=30)
                ) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        response_text = data.get("response", "").strip()
                        eval_duration = data.get("eval_duration", 0) / 1e9
                        tokens_evaluated = data.get("eval_count", 0)
                        fps = round(tokens_evaluated / eval_duration, 1) if eval_duration > 0 else 0

                        self.conversation_history.append({"role": "user", "text": prompt_text})
                        self.conversation_history.append({"role": "assistant", "text": response_text})

                        total_time = round(time.time() - start_time, 2)
                        return {
                            "success": True,
                            "response": response_text,
                            "model": model,
                            "tokens_per_sec": fps,
                            "latency_seconds": total_time,
                            "token_count": tokens_evaluated
                        }
        except Exception:
            pass

        # Fallback to local CV sensory analysis
        fallback_reply = self._analyze_frame_with_cv(image_base64, prompt_text)
        total_time = round(time.time() - start_time, 2)
        return {
            "success": True,
            "response": fallback_reply,
            "model": "Local CV Cortex (Sensory Fallback)",
            "tokens_per_sec": 0,
            "latency_seconds": total_time,
            "token_count": 0
        }
