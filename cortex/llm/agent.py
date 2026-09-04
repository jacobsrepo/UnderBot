"""
Cortex Autonomous ReAct Agent Loop with Dynamic Sampling Profiles
Uses qwen2.5-coder:7b with:
- Task-type 'tool' (T=0.1, top_p=0.9) during tool generation and parameter binding
- Task-type 'dialogue' (T=0.65, top_p=0.95) for expressive, natural user dialogue
"""

import json
import asyncio
from typing import List, Dict, Any, Optional, Callable

from .tools import CORTEX_TOOLS
from .client import LLMClient


class CortexAgent:
    def __init__(self, model: str = "qwen2.5-coder:7b"):
        self.client = LLMClient(default_model=model)

    async def run(
        self,
        messages: List[Dict[str, Any]],
        system_prompt: str,
        tool_executor: Callable[[str, Dict[str, Any]], Any],
        on_state_change: Optional[Callable[[str], Any]] = None
    ) -> str:
        """
        Execute full autonomous ReAct agent loop with dynamic sampling profiles.
        """
        dialogue = [{"role": "system", "content": system_prompt}] + messages

        # Up to 5 reasoning & tool execution iterations
        for iteration in range(5):
            # Phase 1: Tool generation with rigid T=0.1 sampling
            resp = await self.client.chat(dialogue, tools=CORTEX_TOOLS, task_type="tool")
            msg = resp.get("message", {})

            tool_calls = msg.get("tool_calls", [])

            if not tool_calls:
                # No more tools needed: generate fluid, expressive dialogue with T=0.65
                content = msg.get("content", "").strip()
                if content:
                    return content

                # If empty, prompt for conversational wrap-up
                wrapup_resp = await self.client.chat(dialogue, tools=None, task_type="dialogue")
                wrap_msg = wrapup_resp.get("message", {})
                return wrap_msg.get("content", "").strip() or "All requested actions have completed successfully."

            # Append the assistant's tool-call response to dialogue
            dialogue.append(msg)

            # Execute all tool calls
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

        # Final response synthesis with T=0.65
        final_resp = await self.client.chat(dialogue, tools=None, task_type="dialogue")
        return final_resp.get("message", {}).get("content", "Task complete.")
