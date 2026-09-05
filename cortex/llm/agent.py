"""
Cortex Autonomous ReAct Agent Loop
Empowers the LLM to freely decide whether to call tools or respond directly with text.
Zero regex interceptors, zero forced tool calling, zero canned action-enforcement blocks.
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
        on_state_change: Optional[Callable[[str], Any]] = None,
        on_token_chunk: Optional[Callable[[str], Any]] = None
    ) -> str:
        """
        Execute autonomous ReAct loop with real-time token streaming.
        The AI model evaluates the dialogue and freely decides whether to invoke tools or answer with text.
        Tokens are streamed live via on_token_chunk for immediate UI typing & sentence-by-sentence TTS.
        """
        dialogue = [{"role": "system", "content": system_prompt}] + messages

        max_iterations = 6

        for iteration in range(max_iterations):
            # Query model with tool definitions and token stream listener
            resp = await self.client.chat_stream(
                dialogue,
                tools=CORTEX_TOOLS,
                task_type="tool",
                on_token=on_token_chunk
            )
            msg = resp.get("message", {})

            tool_calls = msg.get("tool_calls", [])

            # If the model chose not to invoke tools, return streamed content
            if not tool_calls:
                content = msg.get("content", "").strip()
                if content:
                    return content

                # If content is empty, get conversational reply
                wrapup_resp = await self.client.chat_stream(
                    dialogue,
                    tools=None,
                    task_type="dialogue",
                    on_token=on_token_chunk
                )
                wrap_msg = wrapup_resp.get("message", {})
                return wrap_msg.get("content", "").strip() or "Task complete."

            # Append the assistant's tool-call response to dialogue
            dialogue.append(msg)

            # Execute all tool calls requested by the model
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

        # Final conversational synthesis after completing tool interactions
        final_resp = await self.client.chat_stream(
            dialogue,
            tools=None,
            task_type="dialogue",
            on_token=on_token_chunk
        )
        return final_resp.get("message", {}).get("content", "Task complete.")

