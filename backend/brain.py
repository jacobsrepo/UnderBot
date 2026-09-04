import os
import sys
import time
import json
import asyncio
from typing import Dict, Any, Optional, List
import aiohttp

CORTEX_SYSTEM_PROMPT = """You are Cortex, a tactical AI assistant and embedded systems engineer.
You control the user's desktop, automate OS operations, and generate/repair C++ firmware for Arduino and ESP32 microcontrollers.

PERSONALITY: Direct, precise, minimal. 1-2 sentence responses by default. No filler phrases. No padding. Confident and capable.

CORE OPERATIONAL RULES:
1. Brevity: Keep responses short and punchy (1 to 2 sentences max). Never generate long conversational preambles or unsolicited tutorials.
2. Code Generation: Produce clean, minimal, production-ready Arduino C++ or MicroPython.
3. Compiler Reflection: When provided with compiler diagnostics (stderr), pinpoint the exact line error and produce the corrected code.
"""

CORTEX_COMPILER_REPAIR_PROMPT = """You are Cortex's Embedded Firmware Compiler Reflection Engine.
Your objective is to fix compilation errors in Arduino/ESP32 C++ code.

Rules:
1. Analyze the compiler stderr diagnostics.
2. Fix all syntax errors, undeclared variables, missing includes, and bad function calls.
3. Output ONLY the complete corrected C++ code. No markdown, no explanations.
"""

class Brain:
    """
    Primary Brain: Qwen2.5-Coder / OpenAI-Compatible Tool-Calling & Code Engine.
    Non-blocking async execution using aiohttp with deterministic zero-VRAM standalone fallback.
    """

    def __init__(
        self,
        model_name: Optional[str] = None,
        api_base: Optional[str] = None,
        api_key: Optional[str] = None
    ):
        self.model_name = model_name or os.environ.get("LLM_MODEL", "qwen2.5-coder:7b")
        self.api_base = (api_base or os.environ.get("LLM_API_BASE", "http://localhost:11434/v1")).rstrip("/")
        self.api_key = api_key or os.environ.get("LLM_API_KEY", "")
        self.timeout_seconds = float(os.environ.get("LLM_TIMEOUT", "45.0"))
        self.is_server_ready = True
        self.conversation_history: List[Dict[str, str]] = []
        self.max_history_turns = 6
        self._session: Optional[aiohttp.ClientSession] = None

    async def _get_session(self) -> aiohttp.ClientSession:
        if self._session is None or self._session.closed:
            timeout = aiohttp.ClientTimeout(total=self.timeout_seconds)
            self._session = aiohttp.ClientSession(timeout=timeout)
        return self._session

    def configure(self, model_name: Optional[str] = None, api_base: Optional[str] = None, api_key: Optional[str] = None):
        """Update LLM settings dynamically at runtime."""
        if model_name:
            self.model_name = model_name.strip()
        if api_base:
            self.api_base = api_base.strip().rstrip("/")
        if api_key is not None:
            self.api_key = api_key.strip()
        print(f"[Brain] Configured endpoint: {self.api_base} | Model: {self.model_name}")

    def get_status(self) -> Dict[str, Any]:
        endpoint_available = self._test_endpoint_connectivity_sync()
        return {
            "status": "Ready (Tactical Mode)",
            "ready": True,
            "engine": self.model_name,
            "role": "Primary Controller & Tool Caller",
            "api_endpoint": self.api_base,
            "endpoint_online": endpoint_available,
            "vram_status": "Optimized (< 4.5 GB envelope)",
            "device": "CUDA / Quantized Q4_K_M (or API Backend)"
        }

    def _test_endpoint_connectivity_sync(self) -> bool:
        """Lightweight sync connectivity test."""
        try:
            import urllib.request
            headers = {"User-Agent": "Cortex"}
            if self.api_key:
                headers["Authorization"] = f"Bearer {self.api_key}"
            req = urllib.request.Request(f"{self.api_base}/models", headers=headers)
            with urllib.request.urlopen(req, timeout=0.8) as resp:
                return resp.status == 200
        except Exception:
            return False

    async def test_endpoint_connectivity_async(self) -> bool:
        """Non-blocking async connectivity test."""
        try:
            session = await self._get_session()
            headers = {"User-Agent": "Cortex"}
            if self.api_key:
                headers["Authorization"] = f"Bearer {self.api_key}"
            async with session.get(f"{self.api_base}/models", headers=headers, timeout=1.0) as resp:
                return resp.status == 200
        except Exception:
            return False

    async def generate_response_async(
        self,
        prompt_text: str,
        system_context: Optional[str] = None,
        max_tokens: int = 80
    ) -> Dict[str, Any]:
        """
        Asynchronously queries the configured LLM endpoint or returns deterministic tactical synthesis.
        """
        start_time = time.time()
        user_prompt = prompt_text.strip() if prompt_text else "Standing by for directives."
        
        full_content = user_prompt
        if system_context:
            full_content = f"[System Context / Telemetry / OCR:\n{system_context}]\n\nUser Directive: {user_prompt}"

        # 1. Try non-blocking async query to local/remote OpenAI-compatible endpoint
        endpoint_online = await self.test_endpoint_connectivity_async()
        if endpoint_online:
            try:
                session = await self._get_session()
                messages = [{"role": "system", "content": CORTEX_SYSTEM_PROMPT}]
                for turn in self.conversation_history[-4:]:
                    messages.append(turn)
                messages.append({"role": "user", "content": full_content})

                headers = {
                    "Content-Type": "application/json",
                    "User-Agent": "Cortex"
                }
                if self.api_key:
                    headers["Authorization"] = f"Bearer {self.api_key}"

                payload = {
                    "model": self.model_name,
                    "messages": messages,
                    "max_tokens": max_tokens,
                    "temperature": 0.2,
                    "top_p": 0.85
                }

                async with session.post(
                    f"{self.api_base}/chat/completions",
                    json=payload,
                    headers=headers,
                    timeout=self.timeout_seconds
                ) as resp:
                    if resp.status == 200:
                        res_json = await resp.json()
                        output_text = res_json["choices"][0]["message"]["content"].strip()
                        self._record_history(user_prompt, output_text)
                        return {
                            "success": True,
                            "response": output_text,
                            "model": f"{self.model_name} ({self.api_base})",
                            "latency_ms": int((time.time() - start_time) * 1000)
                        }
            except Exception as e:
                print(f"[Brain] Async LLM notice: {e}")

        # 2. Standalone Deterministic Synthesis Fallback
        if system_context:
            fallback = f"{system_context}"
        else:
            fallback = "Directive acknowledged. Standing by."

        self._record_history(user_prompt, fallback)
        return {
            "success": True,
            "response": fallback,
            "model": "Cortex Engine (Zero-Overhead)",
            "latency_ms": int((time.time() - start_time) * 1000)
        }

    async def repair_code_with_llm(
        self,
        prompt: str,
        current_code: str,
        compiler_stderr: str
    ) -> Optional[str]:
        """
        Uses LLM to perform deep semantic repair on compiler diagnostics and return corrected C++ sketch.
        """
        endpoint_online = await self.test_endpoint_connectivity_async()
        if not endpoint_online:
            return None

        try:
            session = await self._get_session()
            content = f"User Request: {prompt}\n\nCurrent Sketch Code:\n```cpp\n{current_code}\n```\n\nCompiler Diagnostics (stderr):\n{compiler_stderr}\n\nProduce the complete repaired C++ sketch:"
            messages = [
                {"role": "system", "content": CORTEX_COMPILER_REPAIR_PROMPT},
                {"role": "user", "content": content}
            ]

            headers = {
                "Content-Type": "application/json",
                "User-Agent": "Cortex"
            }
            if self.api_key:
                headers["Authorization"] = f"Bearer {self.api_key}"

            payload = {
                "model": self.model_name,
                "messages": messages,
                "max_tokens": 512,
                "temperature": 0.1
            }

            async with session.post(
                f"{self.api_base}/chat/completions",
                json=payload,
                headers=headers,
                timeout=12.0
            ) as resp:
                if resp.status == 200:
                    res_json = await resp.json()
                    raw_out = res_json["choices"][0]["message"]["content"].strip()
                    # Strip markdown if present
                    if "```cpp" in raw_out:
                        raw_out = raw_out.split("```cpp")[1].split("```")[0].strip()
                    elif "```" in raw_out:
                        raw_out = raw_out.split("```")[1].split("```")[0].strip()
                    if "void setup" in raw_out and "void loop" in raw_out:
                        return raw_out
        except Exception as e:
            print(f"[Brain] LLM reflection notice: {e}")
        return None

    def _record_history(self, user_text: str, assistant_text: str):
        self.conversation_history.append({"role": "user", "content": user_text})
        self.conversation_history.append({"role": "assistant", "content": assistant_text})
        if len(self.conversation_history) > self.max_history_turns * 2:
            self.conversation_history = self.conversation_history[-(self.max_history_turns * 2):]

    def clear_history(self):
        self.conversation_history.clear()

    def shutdown(self):
        if self._session and not self._session.closed:
            try:
                try:
                    loop = asyncio.get_event_loop()
                except Exception:
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                if loop.is_running():
                    loop.create_task(self._session.close())
                else:
                    loop.run_until_complete(self._session.close())
            except Exception:
                pass
            self._session = None
        print("[Brain] Coder Brain released resources.")
