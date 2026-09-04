"""
Cortex Autonomous ReAct Agent Loop with Dynamic Sampling Profiles
Uses qwen2.5-coder:7b with:
- Task-type 'tool' (T=0.1, top_p=0.9) during tool generation and parameter binding
- Task-type 'dialogue' (T=0.65, top_p=0.95) for expressive, natural user dialogue
"""

import json
import re
import asyncio
from typing import List, Dict, Any, Optional, Callable

from .tools import CORTEX_TOOLS
from .client import LLMClient

# Patterns for detecting user action requests and assistant hallucinated actions
ACTION_USER_REGEX = re.compile(
    r'\b(flash|upload|compile|build|turn on|turn off|set pin|pins?|leds?|ports?|com\s*ports?|check\s*(connection|hardware|arduino|board|port|ports|com|usb|led)|status\s*(of|on)?\s*(the\s*)?(arduino|board|nano|led|connection|pins?|hardware)|hardware|nano|arduino|run cli|execute|command)\b',
    re.IGNORECASE
)

HALLUCINATED_ACTION_REGEX = re.compile(
    r'(i have (compiled|flashed|uploaded|turned on|updated|set)|has been (compiled|flashed|uploaded)|the pin is\s*\.|led should now be illuminated|led is now on|pins are now configured|let\'s run a command|checking the (available )?(com )?ports|scanned (the )?(available )?ports|no arduino (board )?is (currently )?detected|no microcontroller is connected)',
    re.IGNORECASE
)


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
        Execute full autonomous ReAct agent loop with dynamic sampling profiles
        and strict Action-Enforcement guardrails.
        """
        dialogue = [{"role": "system", "content": system_prompt}] + messages

        # Find latest user prompt to detect actionable commands
        last_user_text = ""
        for m in reversed(messages):
            if m.get("role") == "user":
                last_user_text = str(m.get("content", ""))
                break

        total_tools_executed = 0
        enforcement_retries = 0

        # Up to 6 reasoning & tool execution iterations
        for iteration in range(6):
            # Phase 1: Tool generation with rigid T=0.1 sampling
            resp = await self.client.chat(dialogue, tools=CORTEX_TOOLS, task_type="tool")
            msg = resp.get("message", {})

            tool_calls = msg.get("tool_calls", [])

            if not tool_calls:
                content = msg.get("content", "").strip()

                # Action-Enforcement Guard: Prevent conversational hallucinations when tools were required
                is_hallucinating = bool(HALLUCINATED_ACTION_REGEX.search(content))
                is_unfulfilled_action = bool(ACTION_USER_REGEX.search(last_user_text)) and total_tools_executed == 0

                if (is_hallucinating or is_unfulfilled_action) and total_tools_executed == 0 and enforcement_retries < 2:
                    enforcement_retries += 1
                    dialogue.append({
                        "role": "user",
                        "content": (
                            "[SYSTEM ACTION ENFORCEMENT: You returned conversational text claiming an action or the user gave an explicit command, but ZERO tools were executed. "
                            "Do NOT pretend or describe future actions. You MUST invoke the real tool immediately "
                            "(e.g. build_and_flash_sketch, compile_and_upload_sketch, set_arduino_pin, set_all_arduino_pins, check_hardware_connection, or run_cli_command). Emit the tool call now.]"
                        )
                    })
                    continue

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
                total_tools_executed += 1

                dialogue.append({
                    "role": "tool",
                    "content": json.dumps(tool_output),
                })

        # Final response synthesis with T=0.65
        final_resp = await self.client.chat(dialogue, tools=None, task_type="dialogue")
        return final_resp.get("message", {}).get("content", "Task complete.")
