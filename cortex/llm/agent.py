"""
Cortex Autonomous ReAct Agent Loop
Empowers the LLM to freely decide whether to call tools or respond directly with text.
Zero regex interceptors, zero forced tool calling, zero canned action-enforcement blocks.
"""

import json
import re
import asyncio
from typing import List, Dict, Any, Optional, Callable

from .tools import CORTEX_TOOLS
from .client import LLMClient


class CortexAgent:
    def __init__(self, model: str = "qwen2.5-coder:7b"):
        self.client = LLMClient(default_model=model)

    @staticmethod
    def _parse_text_tool_call(content: str) -> Optional[Dict[str, Any]]:
        if not content:
            return None
        cleaned = re.sub(r'^```[a-zA-Z0-9_\-\.]*\s*', '', content.strip())
        cleaned = re.sub(r'\s*```$', '', cleaned.strip()).strip()
        m = re.match(r'^([a-zA-Z0-9_]+)\s*\((.*)\)$', cleaned, re.DOTALL)
        if not m:
            return None
        fn_name = m.group(1)
        raw_args = m.group(2).strip()
        tool_names = {t["function"]["name"] for t in CORTEX_TOOLS}
        if fn_name not in tool_names:
            return None
        args: Dict[str, Any] = {}
        if raw_args:
            try:
                parsed = json.loads(raw_args)
                if isinstance(parsed, dict):
                    args = parsed
            except Exception:
                pass
            if not args:
                if (raw_args.startswith('"') and raw_args.endswith('"')) or (raw_args.startswith("'") and raw_args.endswith("'")):
                    val = raw_args[1:-1]
                    if fn_name == "run_cli_command":
                        args = {"command": val}
                    elif fn_name in ("search_or_browse_web", "get_live_weather"):
                        args = {"query_or_url": val}
                    elif fn_name in ("search_prices", "search_places_and_map"):
                        args = {"query": val}
                    elif fn_name == "plan_day_itinerary":
                        args = {"destination": val}
                    elif fn_name == "inspect_camera":
                        args = {"focus_target": val}
                    elif fn_name == "launch_app":
                        args = {"app_name": val}
                    elif fn_name == "open_file":
                        args = {"path": val}
                    elif fn_name in ("focus_window", "close_window", "minimize_window", "maximize_window"):
                        args = {"title": val}
                    elif fn_name == "set_volume":
                        args = {"level": int(val) if val.isdigit() else 50}
                    elif fn_name == "kill_process":
                        args = {"identifier": val}
                    elif fn_name == "type_text":
                        args = {"text": val}
                    elif fn_name == "press_keys":
                        args = {"keys": [k.strip() for k in val.split(",")]}
                    elif fn_name == "write_clipboard":
                        args = {"text": val}
                    elif fn_name == "list_directory":
                        args = {"path": val}
                    elif fn_name == "find_files":
                        parts = val.split("|")
                        args = {"root": parts[0].strip(), "pattern": parts[1].strip() if len(parts) > 1 else "*"}
                    elif fn_name == "recall_from_memory":
                        args = {"query": val}
                    elif fn_name == "save_to_memory":
                        args = {"category": "notes", "key": "info", "value": val}
                else:
                    m_kv = re.findall(r'([a-zA-Z0-9_]+)\s*=\s*(?:"([^"]*)"|\'([^\']*)\'|([^\s,]+))', raw_args)
                    if m_kv:
                        for k, v1, v2, v3 in m_kv:
                            args[k] = v1 or v2 or v3
        return {"id": f"call_fallback_{fn_name}", "type": "function", "function": {"name": fn_name, "arguments": args}}

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
            # Buffer tokens during tool-decision phase so internal tool preambles are not leaked to UI/TTS
            pending_tokens: List[str] = []
            async def buffer_token(t: str):
                pending_tokens.append(t)

            # Query model with tool definitions
            resp = await self.client.chat_stream(
                dialogue,
                tools=CORTEX_TOOLS,
                task_type="tool",
                on_token=buffer_token if on_token_chunk else None
            )
            msg = resp.get("message", {})
            tool_calls = msg.get("tool_calls", [])

            # If the model chose not to invoke tools natively, check for textual function calls or deliver content
            if not tool_calls:
                content = msg.get("content", "").strip()
                fallback_tc = self._parse_text_tool_call(content)
                if fallback_tc:
                    tool_calls = [fallback_tc]
                    msg["tool_calls"] = tool_calls
                elif content:
                    if on_token_chunk:
                        for pt in pending_tokens:
                            await on_token_chunk(pt)
                    return content
                else:
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

