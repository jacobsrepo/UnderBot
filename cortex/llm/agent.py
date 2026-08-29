"""
Cortex Autonomous ReAct Agent Loop
Executes multi-step tool calls dynamically with Qwen 2.5 via Ollama.
"""

import json
import urllib.request
import urllib.error
import asyncio
from typing import List, Dict, Any, Optional, Callable

from .tools import CORTEX_TOOLS

OLLAMA_BASE = "http://127.0.0.1:11434"


class CortexAgent:
    def __init__(self, model: str = "qwen2.5:7b-instruct-q4_K_M"):
        self.model = model

    async def run(
        self,
        messages: List[Dict[str, Any]],
        system_prompt: str,
        tool_executor: Callable[[str, Dict[str, Any]], Any],
        on_state_change: Optional[Callable[[str], Any]] = None
    ) -> str:
        """
        Execute full autonomous ReAct agent loop with multi-step tool calling.
        """
        dialogue = [{"role": "system", "content": system_prompt}] + messages

        # Up to 4 reasoning & tool execution iterations
        for iteration in range(4):
            payload = {
                "model": self.model,
                "messages": dialogue,
                "tools": CORTEX_TOOLS,
                "stream": False,
                "options": {
                    "temperature": 0.3,
                }
            }

            req = urllib.request.Request(
                f"{OLLAMA_BASE}/api/chat",
                data=json.dumps(payload).encode('utf-8'),
                headers={"Content-Type": "application/json"}
            )

            try:
                with urllib.request.urlopen(req, timeout=25.0) as resp:
                    data = json.loads(resp.read().decode('utf-8'))
                    msg = data.get("message", {})
            except Exception as e:
                print(f"Agent inference error: {e}")
                return "I encountered a communication interruption with my local neural core."

            tool_calls = msg.get("tool_calls", [])

            if not tool_calls:
                # No tool calls: LLM returned its final conversational text
                content = msg.get("content", "").strip()
                if content:
                    return content
                return "All requested tasks completed."

            # Append the assistant's message with tool_calls to the dialogue history
            dialogue.append(msg)

            # Execute all requested tools
            for tc in tool_calls:
                fn = tc.get("function", {})
                fn_name = fn.get("name", "")
                fn_args = fn.get("arguments", {})
                if isinstance(fn_args, str):
                    try:
                        fn_args = json.loads(fn_args)
                    except Exception:
                        fn_args = {}

                # Execute tool
                tool_output = await tool_executor(fn_name, fn_args)

                dialogue.append({
                    "role": "tool",
                    "content": json.dumps(tool_output),
                })

        return "Task processed."
