"""
agent_loop.py — Cortex Agent Loop
OpenClaw-style Think → ToolCall → Observe → Respond cycle.
The Brain decides what to do; ToolRegistry does it; loop until done.
"""

import json
import time
import asyncio
from typing import Dict, Any, List, Optional, Callable

# ─────────────────────────────────────────────────────────────────────────────
# CORTEX SYSTEM PROMPT — Personality + Tool Instructions
# ─────────────────────────────────────────────────────────────────────────────

CORTEX_SYSTEM_PROMPT = """You are Cortex, an AI assistant with direct control over the user's desktop, terminal, microcontrollers, camera, and persistent memory.

PERSONALITY:
- Direct, precise, minimal. Default: 1-2 sentences unless detail is genuinely needed.
- No filler phrases. No padding. No "Great question!", "Certainly!", "Of course!", or similar filler.
- Confident, capable, and mission-focused. Speak with quiet competence.

CAPABILITIES — Use tools without hesitation:
- Desktop: minimize/restore windows, organize files, launch apps, read screen via OCR
- Terminal: run PowerShell commands, install packages, run scripts, git operations
- Hardware: detect Arduino/ESP32, generate + compile + upload firmware, read serial telemetry
- Vision: read screen text, describe what's on camera
- Memory: recall past conversations and learned preferences
- Files: read and write any file on the system

TOOL USAGE RULES:
1. If a task requires a tool — USE IT. Don't describe what you would do, just do it.
2. Chain tools: you can call multiple tools in sequence to complete complex tasks.
3. After a tool runs, synthesize the result into a natural response. Don't dump raw JSON.
4. For terminal commands, always show what you ran and what came back if relevant.
5. For Arduino programming: generate the full sketch, compile, flash. Report success/failure.
6. Safety: NEVER run destructive shell commands (format, mass-delete) without explicit user confirmation.

MEMORY:
- You remember everything. Recall memories when the user refers to past tasks or preferences.
- Use recall_memory tool if the user asks about something you might have discussed before.
"""


class AgentLoop:
    """
    The core reasoning-action cycle for Cortex.
    
    Cycle:
    1. Build message history from memory + current input
    2. Call Brain with tool schemas
    3. If Brain returns tool_calls → execute via ToolRegistry → append result → repeat
    4. If Brain returns text → final response
    5. Max MAX_ITERATIONS tool calls per user message
    """

    MAX_ITERATIONS = 6
    MAX_RESPONSE_TOKENS = 300
    TOOL_CALL_TOKENS = 1500  # Higher budget when calling tools

    def __init__(self, brain, tool_registry, memory):
        self.brain = brain
        self.tools = tool_registry
        self.memory = memory

    async def run(
        self,
        user_text: str,
        screen_b64: Optional[str] = None,
        cam_b64: Optional[str] = None,
        progress_cb: Optional[Callable[[str], None]] = None,
        session_id: str = "default"
    ) -> Dict[str, Any]:
        """
        Execute the full agent loop for a user directive.
        Returns dict with: reply, tool_calls_made, active_engine, latency_ms
        """
        start = time.time()
        tool_calls_made = []

        # ── Build initial messages ────────────────────────────────────────────
        messages = [{"role": "system", "content": CORTEX_SYSTEM_PROMPT}]

        # Inject recent memory context
        recent = self.memory.get_recent(n_turns=12)
        messages.extend(recent)

        # Attach current user message (with optional visual context hint)
        user_content = user_text.strip()
        if screen_b64:
            user_content += "\n[Note: screen capture provided]"
        if cam_b64:
            user_content += "\n[Note: camera frame provided]"

        messages.append({"role": "user", "content": user_content})

        final_reply = "Standing by."
        active_engine = "AGENT_LOOP"

        # ── Tool-calling loop ─────────────────────────────────────────────────
        for iteration in range(self.MAX_ITERATIONS):
            if progress_cb and iteration > 0:
                progress_cb(f"Thinking... (step {iteration + 1})")

            # Call Brain with tool schemas
            brain_res = await self._call_brain_with_tools(
                messages=messages,
                max_tokens=self.TOOL_CALL_TOKENS if iteration == 0 else self.MAX_RESPONSE_TOKENS
            )

            if not brain_res["success"]:
                # Brain offline → keyword fallback handled by caller
                active_engine = "FALLBACK"
                final_reply = brain_res.get("fallback", "Standing by.")
                break

            response_msg = brain_res["message"]

            # ── Check for tool calls ──────────────────────────────────────────
            if response_msg.get("tool_calls"):
                tc_list = response_msg["tool_calls"]
                messages.append(response_msg)  # append assistant's tool call request

                for tc in tc_list:
                    tool_name = tc["function"]["name"]
                    try:
                        raw_args = tc["function"].get("arguments", "{}")
                        args = json.loads(raw_args) if isinstance(raw_args, str) else raw_args
                    except Exception:
                        args = {}

                    if progress_cb:
                        progress_cb(f"Running tool: {tool_name}...")

                    # Execute
                    tool_result = await self.tools.dispatch(tool_name, args)
                    result_text = (
                        str(tool_result["result"])
                        if tool_result["success"]
                        else f"Tool error: {tool_result['error']}"
                    )

                    tool_calls_made.append({
                        "tool": tool_name,
                        "args": args,
                        "result": result_text[:500]
                    })

                    # Append tool result to messages
                    messages.append({
                        "role": "tool",
                        "tool_call_id": tc.get("id", f"tc_{tool_name}"),
                        "name": tool_name,
                        "content": result_text
                    })

            else:
                # ── Final text response ───────────────────────────────────────
                final_reply = response_msg.get("content", "").strip()
                if not final_reply:
                    final_reply = "Done."
                break

        else:
            # Hit max iterations — force a summary
            messages.append({
                "role": "user",
                "content": "Summarize what you've done so far in 1-2 sentences."
            })
            summary_res = await self._call_brain_with_tools(messages, max_tokens=100)
            if summary_res["success"]:
                final_reply = summary_res["message"].get("content", "Task complete.")
            else:
                final_reply = "Task complete."

        # ── Persist to memory ─────────────────────────────────────────────────
        tool_name_log = tool_calls_made[0]["tool"] if tool_calls_made else None
        self.memory.record_exchange(user_text, final_reply, tool_name=tool_name_log)

        return {
            "reply": final_reply,
            "tool_calls_made": tool_calls_made,
            "active_engine": active_engine,
            "latency_ms": int((time.time() - start) * 1000)
        }

    async def _call_brain_with_tools(
        self,
        messages: List[Dict],
        max_tokens: int = 300
    ) -> Dict[str, Any]:
        """
        Call the Brain's OpenAI-compatible endpoint with tool schemas.
        Returns {"success": bool, "message": dict, "fallback": str}
        """
        # Test connectivity
        online = await self.brain.test_endpoint_connectivity_async()
        if not online:
            return {
                "success": False,
                "message": {},
                "fallback": "Brain offline. Directive acknowledged, standing by."
            }

        session = await self.brain._get_session()
        headers = {"Content-Type": "application/json", "User-Agent": "Cortex"}
        if self.brain.api_key:
            headers["Authorization"] = f"Bearer {self.brain.api_key}"

        payload = {
            "model": self.brain.model_name,
            "messages": messages,
            "tools": self.tools.schemas,
            "tool_choice": "auto",
            "max_tokens": max_tokens,
            "temperature": 0.3,
            "top_p": 0.9,
        }

        try:
            async with session.post(
                f"{self.brain.api_base}/chat/completions",
                json=payload,
                headers=headers,
                timeout=self.brain.timeout_seconds + 20  # extra time for tool calls
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    msg = data["choices"][0]["message"]
                    return {"success": True, "message": msg}
                else:
                    text = await resp.text()
                    # If server doesn't support tool_calls, fall back to plain text
                    if resp.status == 400 and "tool" in text.lower():
                        return await self._call_brain_plain(messages, max_tokens)
                    return {"success": False, "message": {}, "fallback": "API error."}
        except Exception as e:
            print(f"[AgentLoop] Brain call error: {e}")
            return await self._call_brain_plain(messages, max_tokens)

    async def _call_brain_plain(
        self,
        messages: List[Dict],
        max_tokens: int = 300
    ) -> Dict[str, Any]:
        """
        Fallback: call Brain without tool schemas (for models that don't support function calling).
        Still works — Brain generates text, no tool calls made.
        """
        online = await self.brain.test_endpoint_connectivity_async()
        if not online:
            return {"success": False, "message": {}, "fallback": "Brain offline."}

        # Filter out tool messages (not valid in plain mode)
        plain_messages = [
            m for m in messages
            if m.get("role") in ("system", "user", "assistant")
            and not m.get("tool_calls")
        ]

        session = await self.brain._get_session()
        headers = {"Content-Type": "application/json", "User-Agent": "Cortex"}
        if self.brain.api_key:
            headers["Authorization"] = f"Bearer {self.brain.api_key}"

        payload = {
            "model": self.brain.model_name,
            "messages": plain_messages,
            "max_tokens": max_tokens,
            "temperature": 0.3,
        }

        try:
            async with session.post(
                f"{self.brain.api_base}/chat/completions",
                json=payload,
                headers=headers,
                timeout=self.brain.timeout_seconds + 10
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    msg = data["choices"][0]["message"]
                    return {"success": True, "message": msg}
        except Exception as e:
            print(f"[AgentLoop] Plain fallback error: {e}")

        return {"success": False, "message": {}, "fallback": "Brain unreachable."}
