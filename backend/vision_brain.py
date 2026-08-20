import os
import json
import base64
import time
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
    Universal Multimodal Vision Brain.
    Supports:
    1. Local Ollama (Qwen2.5-VL, LLaVA, Moondream, etc.)
    2. Cloud / Custom OpenAI-compatible / Gemini multimodal endpoints
    3. Built-in Local OpenCV Sensory Analysis (100% offline, zero-install fallback)
    """
    def __init__(self, ollama_url: str = "http://127.0.0.1:11434", default_model: str = "qwen2.5vl:7b"):
        self.ollama_url = ollama_url.rstrip("/")
        self.default_model = default_model
        self.provider = "auto"  # 'auto', 'ollama', 'cloud_api', 'local_cv'
        self.api_key = os.environ.get("OPENAI_API_KEY", "") or os.environ.get("GEMINI_API_KEY", "")
        self.api_base_url = "https://api.openai.com/v1"
        self.api_model = "gpt-4o-mini"
        self.conversation_history: List[Dict] = []
        self.max_history = 10

        # Load OpenCV Face Detector for offline CV perception
        self.face_cascade = None
        try:
            cascade_path = cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
            if os.path.exists(cascade_path):
                self.face_cascade = cv2.CascadeClassifier(cascade_path)
        except Exception:
            pass

    def update_config(self, provider: str = None, model: str = None, api_key: str = None, api_base: str = None):
        if provider:
            self.provider = provider
        if model:
            self.default_model = model
        if api_key is not None:
            self.api_key = api_key
        if api_base:
            self.api_base_url = api_base.rstrip("/")

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
            "selected_model": self.default_model
        }

    def _analyze_frame_with_local_cv(self, image_base64: str, user_prompt: str) -> str:
        """
        Fast local computer vision analysis. Runs on any computer with zero GPU/server requirements.
        """
        try:
            img_bytes = base64.b64decode(image_base64)
            np_arr = np.frombuffer(img_bytes, np.uint8)
            img = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)
            
            if img is None:
                return "The optical feed is active, but no visual frame was received."

            h, w, _ = img.shape
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            mean_brightness = np.mean(gray)
            
            # Detect faces
            num_faces = 0
            if self.face_cascade is not None:
                faces = self.face_cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=4, minSize=(30, 30))
                num_faces = len(faces)

            # Edge & texture density
            edges = cv2.Canny(gray, 100, 200)
            edge_density = np.count_nonzero(edges) / (h * w)

            lighting = "well-lit" if mean_brightness > 100 else ("moderately lit" if mean_brightness > 40 else "dimly lit")
            
            details = []
            if num_faces > 0:
                details.append(f"I see {num_faces} person directly in view")
            if edge_density > 0.05:
                details.append("a detailed workspace with various objects and surfaces")
            else:
                details.append("a relatively open and clear viewpoint")

            summary = ", ".join(details)
            lower_prompt = user_prompt.lower()

            if any(k in lower_prompt for k in ["what do you see", "describe", "scan", "look", "surrounding"]):
                return f"I can see your live camera feed in a {lighting} environment. {summary.capitalize()}."
            else:
                return f"I heard your question: '{user_prompt}'. I am monitoring the live camera stream ({w}x{h} resolution in {lighting} lighting). Connect an API key or local Qwen-VL model in Settings for deep semantic answers."
        except Exception as e:
            return f"I heard your query: '{user_prompt}'. Optical cortex online."

    async def _analyze_with_cloud_api(self, image_base64: str, user_prompt: str) -> Optional[Dict]:
        """
        Sends frame to any OpenAI-compatible Vision API (e.g. OpenAI GPT-4o-mini, Groq, OpenRouter, etc.)
        """
        if not self.api_key:
            return None

        url = f"{self.api_base_url}/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

        messages = [
            {"role": "system", "content": ROBOT_SYSTEM_PROMPT}
        ]
        
        # Add recent conversation history
        for msg in self.conversation_history[-4:]:
            messages.append({"role": msg["role"], "content": msg["text"]})

        user_content = [{"type": "text", "text": user_prompt or "Describe what you see in this live camera frame."}]
        if image_base64:
            user_content.append({
                "type": "image_url",
                "image_url": {"url": f"data:image/jpeg;base64,{image_base64}"}
            })

        messages.append({"role": "user", "content": user_content})

        payload = {
            "model": self.api_model,
            "messages": messages,
            "max_tokens": 200,
            "temperature": 0.4
        }

        start_time = time.time()
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(url, json=payload, headers=headers, timeout=aiohttp.ClientTimeout(total=20)) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        text = data["choices"][0]["message"]["content"].strip()
                        return {
                            "success": True,
                            "response": text,
                            "model": f"Cloud API ({self.api_model})",
                            "tokens_per_sec": 0,
                            "latency_seconds": round(time.time() - start_time, 2)
                        }
        except Exception as e:
            print(f"[VisionBrain] Cloud API error: {e}")
        return None

    async def _analyze_with_ollama(self, image_base64: str, user_prompt: str, model_name: str) -> Optional[Dict]:
        """
        Sends frame to local Ollama instance (Qwen2.5-VL, etc.)
        """
        start_time = time.time()
        payload = {
            "model": model_name or self.default_model,
            "prompt": user_prompt or "Describe what you see in front of you clearly and concisely.",
            "system": ROBOT_SYSTEM_PROMPT,
            "images": [image_base64] if image_base64 else [],
            "stream": False,
            "options": {
                "temperature": 0.4,
                "top_p": 0.9,
                "num_predict": 250
            }
        }

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.ollama_url}/api/generate",
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=25)
                ) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        response_text = data.get("response", "").strip()
                        eval_duration = data.get("eval_duration", 0) / 1e9
                        tokens_evaluated = data.get("eval_count", 0)
                        fps = round(tokens_evaluated / eval_duration, 1) if eval_duration > 0 else 0

                        return {
                            "success": True,
                            "response": response_text,
                            "model": model_name or self.default_model,
                            "tokens_per_sec": fps,
                            "latency_seconds": round(time.time() - start_time, 2),
                            "token_count": tokens_evaluated
                        }
        except Exception as e:
            print(f"[VisionBrain] Ollama error: {e}")
        return None

    async def analyze_frame_async(
        self,
        image_base64: str,
        user_prompt: str,
        model_name: Optional[str] = None
    ) -> Dict:
        """
        Unified analysis entry point with multi-tier fallback:
        1. Cloud API (if configured)
        2. Local Ollama (if online)
        3. Local CV Sensory Analysis (guaranteed fallback)
        """
        prompt_text = user_prompt.strip() if user_prompt else "Describe what you see in front of you clearly and concisely."
        start_time = time.time()

        # Tier 1: Cloud API if provider is explicitly set or key provided
        if self.provider in ["cloud_api", "openai"] and self.api_key:
            cloud_res = await self._analyze_with_cloud_api(image_base64, prompt_text)
            if cloud_res and cloud_res.get("success"):
                self._record_history(prompt_text, cloud_res["response"])
                return cloud_res

        # Tier 2: Local Ollama (e.g. Qwen2.5-VL)
        if self.provider in ["auto", "ollama"]:
            ollama_res = await self._analyze_with_ollama(image_base64, prompt_text, model_name or self.default_model)
            if ollama_res and ollama_res.get("success"):
                self._record_history(prompt_text, ollama_res["response"])
                return ollama_res

        # Tier 3: Universal Local Computer Vision Fallback (Zero dependencies)
        fallback_reply = self._analyze_frame_with_local_cv(image_base64, prompt_text)
        self._record_history(prompt_text, fallback_reply)
        return {
            "success": True,
            "response": fallback_reply,
            "model": "Local Computer Vision (Universal Offline Mode)",
            "tokens_per_sec": 0,
            "latency_seconds": round(time.time() - start_time, 2),
            "token_count": 0
        }

    def _record_history(self, user_text: str, assistant_text: str):
        self.conversation_history.append({"role": "user", "text": user_text})
        self.conversation_history.append({"role": "assistant", "text": assistant_text})
        if len(self.conversation_history) > self.max_history * 2:
            self.conversation_history = self.conversation_history[-self.max_history * 2:]
