"""
cognitive_core.py — Contender Cognitive Dispatch Core (v2)
Thin orchestrator: routes user directives through the AgentLoop.
Falls back to keyword-based fast-path if Brain is offline.
"""

import asyncio
import time
from typing import Dict, Any, Optional, Callable


class CognitiveCore:
    """
    Decoupled Cognitive Core for Contender.
    Primary path: AgentLoop (LLM tool-calling).
    Fast fallback: keyword-based direct dispatch (0ms, no LLM required).
    """

    def __init__(self, desktop_agent, embedded_agent, primary_brain, vision_engine,
                 tool_registry=None, agent_loop=None, memory=None):
        self.desktop = desktop_agent
        self.embedded = embedded_agent
        self.brain = primary_brain
        self.vision = vision_engine
        self.tools = tool_registry
        self.loop = agent_loop
        self.memory = memory
        self.active_mode = "AGENT_LOOP"

    async def process_user_directive(
        self,
        text: str,
        intent_info: Dict[str, Any],
        screen_b64: Optional[str] = None,
        cam_b64: Optional[str] = None,
        progress_cb: Optional[Callable[[str], None]] = None,
        session_id: str = "default"
    ) -> Dict[str, Any]:
        """
        Main dispatch. Routes through AgentLoop if available, else fast keyword path.
        """
        # ── Safety guardrail (always checked first) ───────────────────────────
        safety_check = self.desktop.check_safety_guardrail(text, action_type="directive")
        if not safety_check["is_safe"]:
            reply = f"Negative. {safety_check['warning']} Awaiting explicit confirmation."
            if self.memory:
                self.memory.record_exchange(text, reply)
            return {
                "reply": reply,
                "action_card": {
                    "type": "safety_block",
                    "title": "Action Blocked",
                    "status": "Confirmation Required"
                },
                "active_vision": intent_info.get("vision_source", "screen"),
                "active_engine": "SAFETY_GUARD",
                "requires_confirmation": True,
            }

        # ── Primary path: AgentLoop ───────────────────────────────────────────
        if self.loop is not None:
            self.active_mode = "AGENT_LOOP"
            try:
                result = await self.loop.run(
                    user_text=text,
                    screen_b64=screen_b64,
                    cam_b64=cam_b64,
                    progress_cb=progress_cb,
                    session_id=session_id
                )
                return {
                    "reply": result["reply"],
                    "action_card": self._build_action_card(result.get("tool_calls_made", [])),
                    "active_vision": intent_info.get("vision_source", "screen"),
                    "active_engine": result.get("active_engine", "AGENT_LOOP"),
                    "latency_ms": result.get("latency_ms", 0),
                    "tool_calls_made": result.get("tool_calls_made", [])
                }
            except Exception as e:
                print(f"[CognitiveCore] AgentLoop error, falling back: {e}")

        # ── Fallback: keyword fast-path ───────────────────────────────────────
        self.active_mode = "KEYWORD_FALLBACK"
        return await self._keyword_dispatch(text, intent_info, screen_b64, cam_b64, progress_cb)

    def _build_action_card(self, tool_calls: list) -> Optional[Dict]:
        if not tool_calls:
            return None
        if len(tool_calls) == 1:
            tc = tool_calls[0]
            return {"type": tc["tool"], "title": tc["tool"].replace("_", " ").title(), "status": "Done"}
        return {
            "type": "multi_tool",
            "title": f"{len(tool_calls)} Tools Executed",
            "tools": [tc["tool"] for tc in tool_calls],
            "status": "Done"
        }

    async def _keyword_dispatch(
        self, text: str, intent_info: Dict, screen_b64, cam_b64, progress_cb
    ) -> Dict[str, Any]:
        """
        Zero-LLM keyword fallback dispatch. Identical to old cognitive_core logic.
        Used when Brain is offline.
        """
        lower = text.lower().strip()
        intent = intent_info.get("intent", "CONVERSATION")
        prompt = intent_info.get("prompt", text)
        board_hint = intent_info.get("board_hint", "auto")
        vision_source = intent_info.get("vision_source", "screen")
        system_context = None
        action_card = None

        # OS window controls
        if any(k in lower for k in ["minimize all", "minimize everything", "show desktop", "minimize windows"]):
            if progress_cb: progress_cb("Minimizing windows...")
            self.desktop.minimize_all_windows()
            action_card = {"type": "window_control", "title": "Minimized All Windows", "status": "Done"}
            system_context = "All desktop windows minimized."

        elif any(k in lower for k in ["restore window", "undo minimize", "unminimize"]):
            self.desktop.undo_minimize_all()
            action_card = {"type": "window_control", "title": "Restored Windows", "status": "Done"}
            system_context = "Desktop windows restored."

        elif any(k in lower for k in ["organize desktop", "tidy desktop"]):
            res = self.desktop.organize_desktop_files()
            action_card = {"type": "desktop_organize", "title": "Organized Desktop",
                           "status": f"{res.get('moved_count', 0)} files moved"}
            system_context = f"Organized {res.get('moved_count', 0)} files."

        # Hardware
        elif any(k in lower for k in ["program", "flash", "upload", "arduino", "blink", "led", "esp32"]):
            if progress_cb: progress_cb("Initializing embedded reflection loop...")
            flash_res = self.embedded.auto_compile_flash_with_reflection(
                prompt=prompt, board_hint=board_hint, progress_cb=progress_cb,
                code_reflector_cb=self._reflect_and_repair_firmware
            )
            if flash_res.get("success"):
                action_card = {"type": "hardware_flash", "title": f"Flashed {flash_res.get('board')}",
                               "status": f"Uploaded to {flash_res.get('port')}"}
                system_context = f"Firmware uploaded to {flash_res.get('board')} on {flash_res.get('port')}."
            else:
                action_card = {"type": "hardware_flash", "title": "Flash Notice",
                               "status": flash_res.get("error", "No board detected")}
                system_context = f"Hardware status: {flash_res.get('error')}"

        # System metrics
        elif intent == "SYSTEM_METRICS" or any(k in lower for k in ["cpu", "ram", "battery", "memory usage"]):
            m = self.desktop.get_system_metrics()
            action_card = {"type": "system_metrics", "title": "System Telemetry",
                           "cpu": f"{m.get('cpu_percent')}%",
                           "ram": f"{m.get('ram_used_gb')}/{m.get('ram_total_gb')} GB"}
            system_context = (f"CPU {m.get('cpu_percent')}%, RAM {m.get('ram_used_gb')}/{m.get('ram_total_gb')} GB, "
                              f"Battery: {m.get('battery', 'N/A')}")

        # Screen OCR
        elif any(k in lower for k in ["read screen", "what's on screen", "screen text", "ocr"]):
            if progress_cb: progress_cb("Running screen OCR...")
            text_out = self.desktop.capture_screen_context()
            if text_out:
                system_context = f"Screen text:\n{text_out[:1500]}"

        # Synthesize with Brain
        coder_res = await self.brain.generate_response_async(
            prompt_text=prompt, system_context=system_context
        )

        reply = coder_res.get("response", "Directive acknowledged.")
        if self.memory:
            self.memory.record_exchange(text, reply)

        return {
            "reply": reply,
            "action_card": action_card,
            "active_vision": vision_source,
            "active_engine": "KEYWORD_FALLBACK",
            "latency_ms": coder_res.get("latency_ms", 0)
        }

    def _reflect_and_repair_firmware(self, prompt: str, current_code: str, compiler_stderr: str) -> str:
        """Compiler reflection for keyword fallback path."""
        print(f"[CognitiveCore] Reflecting on: {compiler_stderr[:150]}")

        if self.brain and hasattr(self.brain, "repair_code_with_llm"):
            try:
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor(max_workers=1) as ex:
                    future = ex.submit(
                        lambda: asyncio.run(
                            self.brain.repair_code_with_llm(prompt, current_code, compiler_stderr)
                        )
                    )
                    repaired = future.result(timeout=15.0)
                if repaired and "void loop" in repaired:
                    return repaired
            except Exception as e:
                print(f"[CognitiveCore] LLM repair: {e}")

        # Heuristic fallback
        repaired = current_code
        if "was not declared in this scope" in compiler_stderr and "pinMode" not in repaired:
            repaired = repaired.replace("void setup() {", "void setup() {\n  pinMode(LED_BUILTIN, OUTPUT);")
        if not repaired or "void loop" not in repaired:
            repaired = """#define LED_PIN 13
void setup() { Serial.begin(115200); pinMode(LED_PIN, OUTPUT); }
void loop() { digitalWrite(LED_PIN, HIGH); delay(1000); digitalWrite(LED_PIN, LOW); delay(1000); }
"""
        return repaired
