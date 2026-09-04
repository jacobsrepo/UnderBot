"""
Cortex LLM Client with Dynamic Task-Specific Sampling Profiles
Uses qwen2.5-coder:7b with:
- T=0.1, top_p=0.9 for deterministic tool calling and CLI synthesis
- T=0.65, top_p=0.95 for conversational dialogue and facial expression streaming
"""

import json
import asyncio
import urllib.request
import urllib.error
from typing import List, Dict, Any, Optional

OLLAMA_BASE = "http://127.0.0.1:11434"


class LLMClient:
    def __init__(self, default_model: str = "qwen2.5-coder:7b"):
        self.default_model = default_model
        self.active_model = None
        self._discover_model()

    def _discover_model(self):
        """Find best available local model, prioritizing coder model."""
        try:
            req = urllib.request.Request(f"{OLLAMA_BASE}/api/tags")
            with urllib.request.urlopen(req, timeout=3.0) as resp:
                data = json.loads(resp.read().decode('utf-8'))
                models = [m.get("name", "") for m in data.get("models", [])]
                if self.default_model in models:
                    self.active_model = self.default_model
                elif "qwen2.5:7b-instruct-q4_K_M" in models:
                    self.active_model = "qwen2.5:7b-instruct-q4_K_M"
                elif models:
                    self.active_model = models[0]
                else:
                    self.active_model = self.default_model
        except Exception:
            self.active_model = self.default_model

    async def chat(
        self,
        messages: List[Dict[str, Any]],
        tools: Optional[List[Dict[str, Any]]] = None,
        task_type: str = "tool"
    ) -> Dict[str, Any]:
        """
        Send chat messages to Ollama with dynamic sampling profiles:
        - task_type='tool': T=0.1, top_p=0.9 (rigid schema & deterministic execution)
        - task_type='dialogue': T=0.65, top_p=0.95 (expressive personality & mood)
        """
        if not self.active_model:
            self._discover_model()

        temp = 0.1 if task_type == "tool" else 0.65
        top_p = 0.9 if task_type == "tool" else 0.95

        payload: Dict[str, Any] = {
            "model": self.active_model,
            "messages": messages,
            "stream": False,
            "options": {
                "temperature": temp,
                "top_p": top_p,
            }
        }

        if tools:
            payload["tools"] = tools

        loop = asyncio.get_running_loop()

        def _send():
            try:
                data = json.dumps(payload).encode('utf-8')
                req = urllib.request.Request(
                    f"{OLLAMA_BASE}/api/chat",
                    data=data,
                    headers={"Content-Type": "application/json"}
                )
                with urllib.request.urlopen(req, timeout=90.0) as resp:
                    return json.loads(resp.read().decode('utf-8'))
            except Exception as e:
                print(f"[LLMClient] Chat call error: {e}")
                return {"message": {"role": "assistant", "content": f"Inference notice: {str(e)}"}}

        return await loop.run_in_executor(None, _send)
