"""
Cortex LLM Client
Connects to local Ollama with live model autodiscovery.
"""

import json
import urllib.request
import urllib.error
from typing import List, Dict, Any, Optional

OLLAMA_BASE = "http://127.0.0.1:11434"


class LLMClient:
    def __init__(self, default_model: str = "qwen2.5:7b-instruct-q4_K_M"):
        self.default_model = default_model
        self.active_model = None
        self._discover_model()

    def _discover_model(self):
        """Find best available local model."""
        try:
            req = urllib.request.Request(f"{OLLAMA_BASE}/api/tags")
            with urllib.request.urlopen(req, timeout=3.0) as resp:
                data = json.loads(resp.read().decode('utf-8'))
                models = [m.get("name", "") for m in data.get("models", [])]
                if self.default_model in models:
                    self.active_model = self.default_model
                elif models:
                    self.active_model = models[0]
                else:
                    self.active_model = self.default_model
        except Exception:
            self.active_model = self.default_model

    async def generate_response(self, messages: List[Dict[str, str]], system_prompt: Optional[str] = None) -> Optional[str]:
        """Send chat messages to Ollama API and return text."""
        if not self.active_model:
            self._discover_model()

        formatted_messages = []
        if system_prompt:
            formatted_messages.append({"role": "system", "content": system_prompt})

        formatted_messages.extend(messages)

        payload = {
            "model": self.active_model,
            "messages": formatted_messages,
            "stream": False,
            "options": {
                "temperature": 0.4,
            }
        }

        data = json.dumps(payload).encode('utf-8')
        req = urllib.request.Request(
            f"{OLLAMA_BASE}/api/chat",
            data=data,
            headers={"Content-Type": "application/json"}
        )

        try:
            # 30s timeout allows clean initial model loading from disk into GPU VRAM
            with urllib.request.urlopen(req, timeout=30.0) as resp:
                result = json.loads(resp.read().decode('utf-8'))
                if "message" in result and "content" in result["message"]:
                    return result["message"]["content"]
        except Exception as e:
            print(f"Ollama generation warning: {e}")
            return None

        return None
