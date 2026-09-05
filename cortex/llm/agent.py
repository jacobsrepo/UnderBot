"""
Cortex Autonomous ReAct Agent Loop
Empowers the LLM to freely decide whether to call tools or respond directly with text.
"""

import json
import re
import asyncio
from typing import List, Dict, Any, Optional, Callable

from .tools import CORTEX_TOOLS
from .client import LLMClient


# Map of parameter aliases that the model tends to use (PowerShell-ish names -> canonical)
_PARAM_ALIASES = {
    "app_name": "app_name", "app": "app_name", "name": "app_name",
    "query_or_url": "query_or_url", "url": "query_or_url", "query": "query",
    "command": "command", "cmd": "command",
    "path": "path", "file": "path", "filepath": "path",
    "title": "title", "window": "title",
    "level": "level", "volume": "level",
    "identifier": "identifier", "process": "identifier", "pid": "identifier",
    "text": "text", "content": "text",
    "keys": "keys", "key": "keys",
    "destination": "destination", "dest": "destination",
    "limit": "limit",
    "root": "root", "pattern": "pattern",
    "category": "category", "key_name": "key", "value": "value",
    "focus_target": "focus_target", "target": "focus_target",
    "city": "city",
    "mode": "mode",
    "state": "state",
    "pin": "pin",
    "sketch_code": "sketch_code", "sketch_name": "sketch_name",
}

# Tool -> primary parameter (for single positional arg fallback)
_PRIMARY_PARAM = {
    "run_cli_command": "command",
    "search_or_browse_web": "query_or_url",
    "get_live_weather": "city",
    "search_prices": "query",
    "search_places_and_map": "query",
    "plan_day_itinerary": "destination",
    "inspect_camera": "focus_target",
    "launch_app": "app_name",
    "open_file": "path",
    "focus_window": "title",
    "close_window": "title",
    "minimize_window": "title",
    "maximize_window": "title",
    "set_volume": "level",
    "kill_process": "identifier",
    "type_text": "text",
    "write_clipboard": "text",
    "list_directory": "path",
    "recall_from_memory": "query",
    "press_keys": "keys",
}


class CortexAgent:
    def __init__(self, model: str = "qwen2.5-coder:7b"):
        self.client = LLMClient(default_model=model)

    @staticmethod
    def _parse_text_tool_call(content: str) -> Optional[Dict[str, Any]]:
        """
        Robustly parse tool calls from model text output in multiple formats:
          1. Native JSON tool call (handled upstream by Ollama)
          2. fn({"key": "val"}) - JSON object arg
          3. fn("value") or fn('value') - positional single string
          4. fn -param 'value' -param2 'value2' - PowerShell-style (most common failure mode)
          5. fn -param value - unquoted PowerShell-style
          6. fn(param=value) - keyword-equals style
        """
        if not content:
            return None

        tool_names = {t["function"]["name"] for t in CORTEX_TOOLS}

        # Strip markdown fences and leading/trailing whitespace
        lines = content.strip().splitlines()
        # Try each line in case tool call is buried in markdown
        candidates = [content.strip()]
        # Also try extracting from code blocks
        in_block = False
        block_lines = []
        for line in lines:
            stripped = line.strip()
            if stripped.startswith("```"):
                if in_block:
                    if block_lines:
                        candidates.append("\n".join(block_lines))
                    block_lines = []
                    in_block = False
                else:
                    in_block = True
            elif in_block:
                block_lines.append(stripped)
            else:
                candidates.append(stripped)

        for raw in candidates:
            raw = raw.strip()
            if not raw:
                continue

            # --- Format 1 & 2: fn({...}) or fn("val") ---
            m = re.match(r'^([a-zA-Z0-9_]+)\s*\((.*)\)\s*$', raw, re.DOTALL)
            if m:
                fn_name = m.group(1)
                if fn_name not in tool_names:
                    continue
                raw_args = m.group(2).strip()
                args = {}
                if raw_args:
                    # Try JSON object
                    try:
                        parsed = json.loads(raw_args)
                        if isinstance(parsed, dict):
                            args = parsed
                    except Exception:
                        pass
                    if not args:
                        # Single quoted/unquoted value -> primary param
                        val_m = re.match(r'^["\'](.*)["\'"]$', raw_args, re.DOTALL)
                        if val_m:
                            val = val_m.group(1)
                        else:
                            val = raw_args.strip("'\"")
                        if val and fn_name in _PRIMARY_PARAM:
                            pk = _PRIMARY_PARAM[fn_name]
                            if pk == "level":
                                try:
                                    args = {pk: int(val)}
                                except ValueError:
                                    args = {pk: 50}
                            elif pk == "keys":
                                args = {pk: [k.strip() for k in val.split(",")]}
                            else:
                                args = {pk: val}
                    if not args:
                        # keyword=value style: fn(param=val, param2=val2)
                        kv = re.findall(r'([a-zA-Z0-9_]+)\s*=\s*(?:"([^"]*)"|\'([^\']*)\'|([^\s,)]+))', raw_args)
                        if kv:
                            for k, v1, v2, v3 in kv:
                                canonical = _PARAM_ALIASES.get(k, k)
                                args[canonical] = v1 or v2 or v3
                return {
                    "id": f"call_fallback_{fn_name}",
                    "type": "function",
                    "function": {"name": fn_name, "arguments": args}
                }

            # --- Format 3: fn -param 'value' -param2 'value2' (PowerShell dash-param) ---
            m2 = re.match(r'^([a-zA-Z0-9_]+)\s+(-[a-zA-Z].*)', raw, re.DOTALL)
            if m2:
                fn_name = m2.group(1)
                if fn_name not in tool_names:
                    continue
                param_str = m2.group(2)
                args = {}
                # Extract -param_name 'value' or -param_name "value" or -param_name value
                pairs = re.findall(
                    r'-([a-zA-Z0-9_]+)\s+(?:"([^"]*)"|\'([^\']*)\'|([^\s-][^\s]*))',
                    param_str
                )
                for pname, v1, v2, v3 in pairs:
                    val = v1 or v2 or v3
                    canonical = _PARAM_ALIASES.get(pname, pname)
                    if canonical == "level":
                        try:
                            val = int(val)
                        except ValueError:
                            val = 50
                    elif canonical == "keys":
                        val = [k.strip() for k in val.split(",")]
                    args[canonical] = val
                # If no pairs found but single token after fn name, use primary param
                if not args and fn_name in _PRIMARY_PARAM:
                    remainder = param_str.strip().strip("'\"- ")
                    if remainder:
                        args = {_PRIMARY_PARAM[fn_name]: remainder}
                if args or fn_name in tool_names:
                    return {
                        "id": f"call_fallback_{fn_name}",
                        "type": "function",
                        "function": {"name": fn_name, "arguments": args}
                    }

        return None

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
        """
        dialogue = [{"role": "system", "content": system_prompt}] + messages

        max_iterations = 6

        for iteration in range(max_iterations):
            pending_tokens: List[str] = []
            async def buffer_token(t: str):
                pending_tokens.append(t)

            resp = await self.client.chat_stream(
                dialogue,
                tools=CORTEX_TOOLS,
                task_type="tool",
                on_token=buffer_token if on_token_chunk else None
            )
            msg = resp.get("message", {})
            tool_calls = msg.get("tool_calls", [])

            if not tool_calls:
                content = msg.get("content", "").strip()

                # Scan ALL lines for a tool call in any format
                fallback_tc = None
                for line in content.splitlines():
                    tc = CortexAgent._parse_text_tool_call(line.strip())
                    if tc:
                        fallback_tc = tc
                        break
                # Also try the full content block
                if not fallback_tc:
                    fallback_tc = CortexAgent._parse_text_tool_call(content)

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

            dialogue.append(msg)

            for tc in tool_calls:
                fn = tc.get("function", {})
                fn_name = fn.get("name", "")
                fn_args = fn.get("arguments", {})
                if isinstance(fn_args, str):
                    try:
                        fn_args = json.loads(fn_args)
                    except Exception:
                        fn_args = {}

                tool_output = await tool_executor(fn_name, fn_args)

                dialogue.append({
                    "role": "tool",
                    "content": json.dumps(tool_output),
                })

        final_resp = await self.client.chat_stream(
            dialogue,
            tools=None,
            task_type="dialogue",
            on_token=on_token_chunk
        )
        return final_resp.get("message", {}).get("content", "Task complete.")
