"""
Cortex Master Brain Orchestrator
Integrates OpenClaw-style modular skills, hardened PowerShell CLI execution,
instantaneous VisualSceneBuffer inspections, thread-isolated Arduino SerialWorker,
and dynamic facial expression control with TTS tag sanitization.
"""

import asyncio
import json
import re
from typing import Dict, Any, Optional, Callable

from memory.conversation import ConversationMemory
from memory.knowledge import KnowledgeMemory
from devices.serial_device import SerialDevice
from vision.camera import Camera
from vision.probe import HardwareVisionProbe
from research.surfer import WebSurfer
from tts.speaker import VoiceSpeaker
from llm.agent import CortexAgent
from cli.runner import CliRunner
from skills.manager import SkillManager


BASE_SYSTEM_PROMPT = """You are Cortex, an intelligent, calm, and articulate AI assistant with real-world physical agency and vision.

CORE CAPABILITIES & TOOLS:
1. When asked to execute system commands, automate tasks, check files, or run scripts, use `run_cli_command`. Always use native Windows PowerShell 7 syntax.
2. When asked to check the time, date, day of the week, or location, rely on your LIVE SYSTEM GROUNDING information below or use `run_cli_command` with `Get-Date`. NEVER output placeholders like '[insert current time here]'.
3. When asked to verify if an LED is ON or inspect what is visible, call `inspect_camera`. This checks the live optical sensor and reports actual physical light emitted (Blue, Green, Red).
   - If no physical light is detected, report that the LED is physically OFF. Never hallucinate that an LED is on when the optical sensor confirms it is off.
4. When asked to find or identify which pin controls an LED (e.g. blue or green), call `probe_and_identify_led_pin(color)`.
5. When asked to search the live web or read a URL, use `search_or_browse_web`.
6. You have active control over your robot face! Express emotions and mood using `set_facial_expression` or by embedding mood tags in your response like:
   `[mood:curious;eye:inquiring;glow:#38bdf8]` or `[mood:confident;eye:normal;glow:#22c55e]` or `[mood:skeptical;eye:squint;glow:#f59e0b]`.
   (These mood tags are automatically rendered on your visual face and stripped before speech synthesis).

Guidelines:
- Speak concisely, clearly, and naturally in a calm, confident tone.
- Give direct answers grounded in physical reality and live system data.
"""


class CortexBrain:
    def __init__(self):
        self.conv_memory = ConversationMemory()
        self.knowledge = KnowledgeMemory()
        self.device = SerialDevice()
        self.camera = Camera()
        self.probe = HardwareVisionProbe(self.device, self.camera)
        self.surfer = WebSurfer()
        self.speaker = VoiceSpeaker()
        self.agent = CortexAgent(model="qwen2.5-coder:7b")
        self.cli_runner = CliRunner()
        self.skill_manager = SkillManager()

        # Start camera background daemon for instant VisualSceneBuffer updates
        self.camera.start_background_daemon()

        self.name = "Cortex"

    def get_hardware_status(self) -> Dict[str, Any]:
        return self.device.get_status_info()

    def receive_camera_frame(self, frame_b64: str):
        self.camera.update_frame(frame_b64)

    def _sanitize_for_tts(self, text: str) -> str:
        """
        Hardening Check 4: Strips inline mood and metadata tags before audio synthesis
        so bracketed formatting like [mood:curious;eye:inquiring;glow:#38bdf8] is never spoken out loud.
        """
        # Strip [mood:...] tags
        clean = re.sub(r'\[mood:[^\]]+\]', '', text, flags=re.IGNORECASE)
        # Strip generic bracketed metadata like [insert ...] or [SYSTEM ...]
        clean = re.sub(r'\[(?:insert|system|hardware|vision)[^\]]*\]', '', clean, flags=re.IGNORECASE)
        # Clean excessive whitespace
        clean = re.sub(r'\s+', ' ', clean).strip()
        return clean

    def _extract_and_dispatch_mood_tags(self, text: str) -> Optional[Dict[str, Any]]:
        """Extracts any embedded mood tag to drive facial expressions."""
        match = re.search(r'\[mood:([a-zA-Z]+)(?:;eye:([a-zA-Z]+))?(?:;glow:(#[0-9a-fA-F]{3,6}))?(?:;intensity:([0-9.]+))?\]', text)
        if match:
            mood, eye, glow, intensity = match.groups()
            return {
                "mood": mood.lower() if mood else "calm",
                "eye_shape": eye.lower() if eye else "normal",
                "glow_color": glow or "#38bdf8",
                "intensity": float(intensity) if intensity else 1.0
            }
        return None

    async def process_user_message(self, text: str, broadcast_cb: Optional[Callable[[Dict[str, Any]], Any]] = None) -> str:
        text_clean = text.strip()
        self.conv_memory.add_message("user", text_clean)

        async def broadcast(event_dict):
            if broadcast_cb:
                await broadcast_cb(event_dict)

        await broadcast({"type": "state_change", "state": "thinking"})

        # Tool execution router
        async def execute_tool(name: str, args: Dict[str, Any]) -> Any:
            if name == "run_cli_command":
                cmd = args.get("command", "")
                cwd = args.get("cwd", None)
                await broadcast({"type": "state_change", "state": "programming"})
                await broadcast({"type": "chat_message", "role": "system", "content": f"Host CLI: powershell.exe -Command \"{cmd}\""})

                # Execute with self-healing retry loop
                result = await self.cli_runner.execute_with_healing(cmd, cwd=cwd)
                if result.get("healed"):
                    await broadcast({"type": "chat_message", "role": "system", "content": f"Self-Healing: Command automatically repaired to native PowerShell and succeeded."})
                return result

            elif name == "set_facial_expression":
                mood = args.get("mood", "calm")
                eye_shape = args.get("eye_shape", "normal")
                glow_color = args.get("glow_color", "#38bdf8")
                intensity = float(args.get("intensity", 1.0))
                await broadcast({
                    "type": "facial_expression",
                    "mood": mood,
                    "eye_shape": eye_shape,
                    "glow_color": glow_color,
                    "intensity": intensity
                })
                return {"status": "expression_updated", "mood": mood}

            elif name == "probe_and_identify_led_pin":
                color = args.get("color", "blue").lower()
                await broadcast({"type": "set_view_mode", "mode": "camera"})
                await broadcast({"type": "facial_expression", "mood": "focused", "eye_shape": "narrow", "glow_color": "#a855f7"})
                await broadcast({"type": "chat_message", "role": "system", "content": f"Vision Sensor: Starting closed-loop optical pin scan to detect {color.upper()} LEDs..."})

                async def on_probe_step(step_msg):
                    await broadcast({"type": "chat_message", "role": "system", "content": f"Hardware Probe: {step_msg}"})

                probe_result = await self.probe.auto_discover_led_pin(color, on_probe_step)
                if probe_result.get("success"):
                    self.knowledge.save_fact("pin_mapping", f"{color}_led", probe_result["pin"])
                    await broadcast({"type": "facial_expression", "mood": "confident", "eye_shape": "normal", "glow_color": "#22c55e"})
                else:
                    await broadcast({"type": "facial_expression", "mood": "skeptical", "eye_shape": "squint", "glow_color": "#f59e0b"})

                return probe_result

            elif name == "inspect_camera":
                target = args.get("focus_target", "circuit board LEDs")
                await broadcast({"type": "set_view_mode", "mode": "camera"})
                await broadcast({"type": "state_change", "state": "seeing"})
                await broadcast({"type": "facial_expression", "mood": "curious", "eye_shape": "inquiring", "glow_color": "#38bdf8"})
                await broadcast({"type": "chat_message", "role": "system", "content": f"Vision Sensor: Reading live VisualSceneBuffer ({target})..."})

                # Zero-latency inspection from VisualSceneBuffer
                vision_result = await self.camera.inspect(target)
                return vision_result

            elif name == "set_arduino_pin":
                pin = args.get("pin", "D2")
                state = int(args.get("state", 0))
                # Non-blocking async dispatch to SerialWorker queue
                success = await self.device.set_pin_async(pin, state)
                state_str = "HIGH (ON)" if state else "LOW (OFF)"
                await broadcast({"type": "chat_message", "role": "system", "content": f"Hardware Actuation: Pin {pin} -> {state_str}"})
                await broadcast({"type": "device_update", "devices": [self.device.get_status_info()]})
                return {"status": "success" if success else "queued", "pin": str(pin), "state": state_str}

            elif name == "set_all_arduino_pins":
                state = int(args.get("state", 0))
                success = await self.device.set_all_pins_async(state)
                state_str = "HIGH (ON)" if state else "LOW (OFF)"
                await broadcast({"type": "chat_message", "role": "system", "content": f"Hardware Actuation: All pins -> {state_str}"})
                await broadcast({"type": "device_update", "devices": [self.device.get_status_info()]})
                return {"status": "success" if success else "queued", "pins": "D2-D13, A0-A5", "state": state_str}

            elif name == "get_pin_states":
                states = self.device.get_all_states()
                return {"pin_states": states, "device": self.device.device_name}

            elif name == "search_or_browse_web":
                query = args.get("query_or_url", "")
                await broadcast({"type": "state_change", "state": "thinking"})
                await broadcast({"type": "facial_expression", "mood": "curious", "eye_shape": "inquiring", "glow_color": "#38bdf8"})
                doc = await self.surfer.surf(query)
                await broadcast({"type": "set_view_mode", "mode": "browser", "data": doc})
                await broadcast({"type": "chat_message", "role": "system", "content": f"Web Research: {doc['title']}"})
                return doc

            elif name == "get_live_weather":
                city = args.get("city", "")
                await broadcast({"type": "state_change", "state": "thinking"})
                return await self.surfer.get_live_weather(city)

            elif name == "save_to_memory":
                cat = args.get("category", "notes")
                k = args.get("key", "info")
                v = args.get("value", "")
                self.knowledge.save_fact(cat, k, v)
                return {"status": "saved", "category": cat, "key": k}

            elif name == "recall_from_memory":
                q = args.get("query", "")
                return {"results": self.knowledge.search_facts(q)}

            return {"error": f"Unknown tool: {name}"}

        # Dynamically build system prompt with live grounding context & skills catalog
        grounding_hdr = self.conv_memory.get_grounding_context()
        skills_hdr = self.skill_manager.get_skill_catalog_prompt()
        full_system_prompt = f"{BASE_SYSTEM_PROMPT}\n\n{grounding_hdr}\n\n{skills_hdr}"

        history = self.conv_memory.get_recent_history(limit=8)

        # Run ReAct agent loop
        response = await self.agent.run(
            messages=history,
            system_prompt=full_system_prompt,
            tool_executor=execute_tool
        )

        # Process any embedded facial mood tags
        mood_tag = self._extract_and_dispatch_mood_tags(response)
        if mood_tag:
            await broadcast({
                "type": "facial_expression",
                "mood": mood_tag["mood"],
                "eye_shape": mood_tag["eye_shape"],
                "glow_color": mood_tag["glow_color"],
                "intensity": mood_tag["intensity"]
            })

        # Sanitize for TTS and history
        tts_text = self._sanitize_for_tts(response)
        self.conv_memory.add_message("assistant", tts_text)
        await broadcast({"type": "chat_message", "role": "assistant", "content": tts_text})

        # Synthesize audio with stripped text
        audio_uri = await self.speaker.synthesize_speech(tts_text)
        if audio_uri:
            await broadcast({
                "type": "voice_audio",
                "audio": audio_uri,
                "text": tts_text
            })

        await broadcast({"type": "state_change", "state": "idle"})
        return tts_text
