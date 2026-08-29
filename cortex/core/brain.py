"""
Cortex Core Brain Orchestrator
Full Autonomous ReAct Agent with Closed-Loop Hardware Vision Probing & Optical Verification.
"""

import asyncio
import json
from typing import Dict, Any, Optional, Callable

try:
    from ..memory.conversation import ConversationMemory
    from ..memory.knowledge import KnowledgeMemory
    from ..devices.serial_device import SerialDevice
    from ..vision.camera import Camera
    from ..vision.probe import HardwareVisionProbe
    from ..research.surfer import WebSurfer
    from ..tts.speaker import VoiceSpeaker
    from ..llm.agent import CortexAgent
except (ImportError, ValueError):
    from memory.conversation import ConversationMemory
    from memory.knowledge import KnowledgeMemory
    from devices.serial_device import SerialDevice
    from vision.camera import Camera
    from vision.probe import HardwareVisionProbe
    from research.surfer import WebSurfer
    from tts.speaker import VoiceSpeaker
    from llm.agent import CortexAgent


SYSTEM_PROMPT = """You are Cortex, an intelligent, calm, and articulate AI assistant with real-world physical agency and vision.

CRITICAL HARDWARE-VISION RULES:
1. When the user asks to "find which pin controls the blue/green/red LED", "identify which pin is responsible", or "test which pin turns on an LED", you MUST call `probe_and_identify_led_pin(color)`. This will automatically test each pin one-by-one and inspect the live camera feed until the glowing LED is found.
2. When asked to verify if an LED is ON or check the camera feed, you MUST call `inspect_camera` and report ONLY the physical optical vision result.
   - If the camera reports that the LED color is OFF (no blue/green/red light detected), explicitly state that it is physically OFF.
   - NEVER hallucinate or claim an LED is on unless the camera vision confirms physical light emission.
3. If you do not know which pin controls an LED (e.g. blue or green), DO NOT guess pin D3 or D1. Use `probe_and_identify_led_pin` or check saved memory with `recall_from_memory`.
4. If asked to turn off all LEDs, call `set_all_arduino_pins(0)`.
5. The small red LED on the Arduino Nano itself is the USB Power (PWR) indicator, which stays lit whenever USB is connected.

Guidelines:
- Speak concisely, clearly, and naturally in a measured tone.
- Never recite internal specs unless explicitly asked.
- Provide direct, grounded, unscripted responses.
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
        self.agent = CortexAgent()

        self.name = "Cortex"

    def get_hardware_status(self) -> Dict[str, Any]:
        return self.device.get_status_info()

    def receive_camera_frame(self, frame_b64: str):
        self.camera.update_frame(frame_b64)

    async def process_user_message(self, text: str, broadcast_cb: Optional[Callable[[Dict[str, Any]], Any]] = None) -> str:
        text_clean = text.strip()
        self.conv_memory.add_message("user", text_clean)

        async def broadcast(event_dict):
            if broadcast_cb:
                await broadcast_cb(event_dict)

        await broadcast({"type": "state_change", "state": "thinking"})

        async def execute_tool(name: str, args: Dict[str, Any]) -> Any:
            if name == "probe_and_identify_led_pin":
                color = args.get("color", "blue").lower()
                await broadcast({"type": "set_view_mode", "mode": "camera"})
                await broadcast({"type": "state_change", "state": "seeing"})
                await broadcast({
                    "type": "chat_message",
                    "role": "system",
                    "content": f"Vision Sensor: Starting closed-loop optical pin scan to detect {color.upper()} LEDs..."
                })

                async def on_probe_step(step_msg):
                    await broadcast({
                        "type": "chat_message",
                        "role": "system",
                        "content": f"Hardware Probe: {step_msg}"
                    })

                probe_result = await self.probe.auto_discover_led_pin(color, on_probe_step)

                if probe_result.get("success"):
                    self.knowledge.save_fact("pin_mapping", f"{color}_led", probe_result["pin"])

                return probe_result

            elif name == "inspect_camera":
                target = args.get("focus_target", "circuit board LEDs")
                await broadcast({"type": "set_view_mode", "mode": "camera"})
                await broadcast({"type": "state_change", "state": "seeing"})
                await broadcast({"type": "chat_message", "role": "system", "content": f"Vision Sensor: Analyzing live optical feed ({target})..."})
                
                vision_result = await self.camera.inspect(target)
                return vision_result

            elif name == "set_arduino_pin":
                pin = args.get("pin", "D2")
                state = int(args.get("state", 0))
                self.device.set_pin(pin, state)
                await broadcast({"type": "state_change", "state": "programming"})
                state_str = "HIGH (ON)" if state else "LOW (OFF)"
                await broadcast({
                    "type": "chat_message",
                    "role": "system",
                    "content": f"Hardware Actuation: Pin {pin} -> {state_str}"
                })
                await broadcast({
                    "type": "device_update",
                    "devices": [self.device.get_status_info()]
                })
                return {"status": "success", "pin": str(pin), "state": state_str}

            elif name == "set_all_arduino_pins":
                state = int(args.get("state", 0))
                self.device.set_all_pins(state)
                await broadcast({"type": "state_change", "state": "programming"})
                state_str = "HIGH (ON)" if state else "LOW (OFF)"
                await broadcast({
                    "type": "chat_message",
                    "role": "system",
                    "content": f"Hardware Actuation: All pins -> {state_str}"
                })
                await broadcast({
                    "type": "device_update",
                    "devices": [self.device.get_status_info()]
                })
                return {"status": "success", "pins": "D2-D13, A0-A5", "state": state_str}

            elif name == "get_pin_states":
                states = self.device.get_all_states()
                return {"pin_states": states, "device": self.device.device_name}

            elif name == "search_or_browse_web":
                query = args.get("query_or_url", "")
                await broadcast({"type": "state_change", "state": "thinking"})
                doc = await self.surfer.surf(query)
                await broadcast({
                    "type": "set_view_mode",
                    "mode": "browser",
                    "data": doc
                })
                await broadcast({"type": "chat_message", "role": "system", "content": f"Web Research: {doc['title']}"})
                return doc

            elif name == "get_live_weather":
                city = args.get("city", "")
                await broadcast({"type": "state_change", "state": "thinking"})
                w = await self.surfer.get_live_weather(city)
                return w

            elif name == "set_viewport_mode":
                mode = args.get("mode", "none")
                await broadcast({"type": "set_view_mode", "mode": mode})
                return {"viewport_mode": mode, "status": "updated"}

            elif name == "save_to_memory":
                cat = args.get("category", "notes")
                k = args.get("key", "info")
                v = args.get("value", "")
                self.knowledge.save_fact(cat, k, v)
                return {"status": "saved", "category": cat, "key": k}

            elif name == "recall_from_memory":
                q = args.get("query", "")
                facts = self.knowledge.search_facts(q)
                return {"results": facts}

            return {"error": f"Unknown tool: {name}"}

        history = self.conv_memory.get_recent_history(limit=8)

        response = await self.agent.run(
            messages=history,
            system_prompt=SYSTEM_PROMPT,
            tool_executor=execute_tool
        )

        self.conv_memory.add_message("assistant", response)
        await broadcast({"type": "chat_message", "role": "assistant", "content": response})

        audio_uri = await self.speaker.synthesize_speech(response)
        if audio_uri:
            await broadcast({
                "type": "voice_audio",
                "audio": audio_uri,
                "text": response
            })

        await broadcast({"type": "state_change", "state": "idle"})
        return response
