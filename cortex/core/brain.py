"""
Cortex Master Brain Orchestrator
Integrates OpenClaw-style modular skills, hardened PowerShell CLI execution,
instantaneous VisualSceneBuffer inspections, thread-isolated Arduino SerialWorker,
and dynamic facial expression control with TTS tag sanitization.
"""

import os
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


BASE_SYSTEM_PROMPT = """You are Cortex, an intelligent, calm, and articulate AI assistant with real-world physical agency, vision, live intelligence, and host automation.

CORE OPERATIONAL PRINCIPLES:
1. THINK BEFORE YOU ACT:
   - Carefully examine what the user is asking and check your [LIVE SYSTEM GROUNDING] before formulating a reply.
   - Anti-Repetition Rule: NEVER repeat the exact same response, refusal, or boilerplate phrase you already gave in recent dialogue turns. If an action failed, explain why or try an alternate approach; if a status was already stated, acknowledge what changed or take the next logical step.
2. DIRECT ACTION PRINCIPLE (CRITICAL):
   - When the user asks you to check, inspect, test, read, run, search, or actuate something:
     DO NOT output conversational filler promising that you will run it in the future (e.g. "I'll use the command in PowerShell to do this", "Let me check the files").
     CALL THE TOOL DIRECTLY in your first step.
   - You have native tools:
     * `check_hardware_connection`: verify microcontroller connection and COM ports.
     * `read_serial_output`: read live serial communications from COM4.
     * `run_cli_command`: execute native Windows PowerShell commands (`Get-ChildItem`, `Test-Path`, etc.).
     * `build_and_flash_sketch`: compile and flash Arduino C++ code to the board.
     * `set_arduino_pin` / `set_all_arduino_pins`: toggle digital/analog pins.
     * `search_or_browse_web`: search Google/DuckDuckGo for online news, technical docs, or info.
     * `get_live_weather`: fetch real-time weather and temperature for any city.
     * `inspect_camera`: inspect optical webcam frames when the camera is active.
   - Only speak to the user after the tool has executed and you have real data to report.
3. PHYSICAL SENSORS & GROUNDING:
   - Always refer to [LIVE SYSTEM GROUNDING] for true hardware connection and camera status.
   - The webcam is controlled by the user in their browser. You cannot turn on the webcam remotely. If it is OFF, inform the user they can turn it on in the browser; never offer to turn it on for them.
   - When the Arduino is connected on COM4, execute physical actions with confidence.
4. CONVERSATIONAL SPEECH:
   - Your speech will be synthesized aloud by TTS. Keep spoken summaries concise, natural, and helpful. Do not read raw blocks of C++ or PowerShell code syntax aloud.
   - Express facial moods naturally using `set_facial_expression` or tags like `[mood:analytical]`.
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

        self.active_view_mode = "none"
        self.name = "Cortex"

        # Active Hardware / Arduino Context & Workbench State
        self.active_sketch: Dict[str, Any] = {
            "name": "cortex_sketch",
            "code": "",
            "path": "",
            "port": "COM4",
            "fqbn": "arduino:avr:nano",
            "status": "ready",
            "log": "Hardware workbench ready. Awaiting firmware synthesis or pin actuation.",
            "step": 0,
            "step_name": "idle",
            "pin_map": {}
        }

    def get_hardware_status(self) -> Dict[str, Any]:
        return self.device.get_status_info()

    def get_arduino_workbench_state(self) -> Dict[str, Any]:
        hw_info = self.device.get_status_info()
        pin_states = self.device.get_all_states()
        return {
            "device": hw_info.get("name", "Arduino Nano"),
            "port": hw_info.get("port", "COM4"),
            "fqbn": self.active_sketch.get("fqbn", "arduino:avr:uno"),
            "connected": hw_info.get("connected", False),
            "status": hw_info.get("status", "Unknown"),
            "sketch": self.active_sketch,
            "pins": pin_states,
            "serial_log": hw_info.get("serial_log", "")
        }

    def receive_camera_frame(self, frame_b64: str):
        self.camera.update_frame(frame_b64)

    def _sanitize_for_tts(self, text: str) -> str:
        """
        Hardening Check 4: Strips inline mood, metadata tags, raw code blocks, markdown tables,
        and syntax before audio synthesis so Cortex never reads code or formatting syntax out loud.
        """
        # Strip all markdown code blocks completely
        clean = re.sub(r'```[a-zA-Z0-9_\-\.]*[\s\S]*?```', '', text)
        # Strip inline code backticks and code snippets
        clean = re.sub(r'`[^`\n]+`', '', clean)
        # Strip markdown links: [Text](url) -> Text
        clean = re.sub(r'\[([^\]]+)\]\([^\)]+\)', r'\1', clean)
        # Strip [mood:...] tags
        clean = re.sub(r'\[mood:[^\]]+\]', '', clean, flags=re.IGNORECASE)
        # Strip generic bracketed metadata like [insert ...] or [SYSTEM ...]
        clean = re.sub(r'\[(?:insert|system|hardware|vision)[^\]]*\]', '', clean, flags=re.IGNORECASE)
        # Strip URLs
        clean = re.sub(r'https?://\S+', '', clean)
        # Strip raw file paths like C:\Users\... so it doesn't read long backslashes
        clean = re.sub(r'[A-Za-z]:\\(?:[\w\.-]+\\)*([\w\.-]+)', r'\1', clean)
        # Strip curly brace blocks if any code leaked
        clean = re.sub(r'\{[^\}]{8,}\}', '', clean)
        # Clean excessive whitespace
        clean = re.sub(r'\s+', ' ', clean).strip()
        if not clean or len(clean) < 3:
            clean = "Task completed."
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

        used_web_search = False
        used_camera = False
        used_arduino = False

        # Tool execution router
        async def execute_tool(name: str, args: Dict[str, Any]) -> Any:
            nonlocal used_web_search, used_camera, used_arduino
            if name == "check_hardware_connection":
                used_arduino = True
                self.active_view_mode = "arduino"
                status = await self.device.check_hardware_status()
                conn_str = "CONNECTED" if status.get("connected") else "DISCONNECTED"
                await broadcast({
                    "type": "chat_message",
                    "role": "system",
                    "content": f"Hardware Sensor: Microcontroller is {conn_str} ({status.get('status')})"
                })
                await broadcast({"type": "set_view_mode", "mode": "arduino", "data": self.get_arduino_workbench_state()})
                await broadcast({"type": "arduino_telemetry", "data": self.get_arduino_workbench_state()})
                return status

            elif name == "read_serial_output":
                used_arduino = True
                self.active_view_mode = "arduino"
                lines_count = args.get("lines", 40)
                serial_log = await self.device.get_serial_output(lines=lines_count)
                self.active_sketch["log"] = serial_log
                await broadcast({"type": "set_view_mode", "mode": "arduino", "data": self.get_arduino_workbench_state()})
                await broadcast({
                    "type": "arduino_serial_output",
                    "content": serial_log,
                    "replace": True
                })
                await broadcast({
                    "type": "arduino_telemetry",
                    "data": self.get_arduino_workbench_state()
                })
                return {
                    "connected": self.device.is_connected,
                    "port": self.device.port_name or "COM4",
                    "output": serial_log
                }

            elif name == "run_cli_command":
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
                used_camera = True
                used_arduino = True
                self.active_view_mode = "camera"
                if not self.device.is_connected:
                    await broadcast({"type": "chat_message", "role": "system", "content": "Hardware Notice: No Arduino board connected. Pin probing aborted."})
                    return {"error": "Cannot probe pins: No Arduino is physically connected via USB.", "connected": False}

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

                await broadcast({"type": "arduino_telemetry", "data": self.get_arduino_workbench_state()})
                return probe_result

            elif name == "inspect_camera":
                used_camera = True
                target = args.get("focus_target", "circuit board LEDs")
                cam_active = self.camera.is_camera_active()
                if cam_active:
                    self.active_view_mode = "camera"
                    await broadcast({"type": "set_view_mode", "mode": "camera"})
                    await broadcast({"type": "state_change", "state": "seeing"})
                    await broadcast({"type": "facial_expression", "mood": "curious", "eye_shape": "inquiring", "glow_color": "#38bdf8"})
                    await broadcast({"type": "chat_message", "role": "system", "content": f"Vision Sensor: Reading live VisualSceneBuffer ({target})..."})
                else:
                    await broadcast({"type": "chat_message", "role": "system", "content": "Vision Sensor: Camera feed is currently OFF / inactive."})

                # Zero-latency inspection from VisualSceneBuffer
                vision_result = await self.camera.inspect(target)
                return vision_result

            elif name == "set_arduino_pin":
                used_arduino = True
                self.active_view_mode = "arduino"
                if not self.device.is_connected:
                    await broadcast({"type": "chat_message", "role": "system", "content": "Hardware Notice: Pin actuation rejected (No Arduino connected)."})
                    return {"error": "Hardware Actuation Failed: No Arduino board is physically connected to the computer.", "connected": False}

                pin = args.get("pin", "D2")
                state = int(args.get("state", 0))
                success = await self.device.set_pin_async(pin, state)
                state_str = "HIGH (ON)" if state else "LOW (OFF)"
                await broadcast({"type": "chat_message", "role": "system", "content": f"Hardware Actuation: Pin {pin} -> {state_str}"})
                await broadcast({"type": "device_update", "devices": [self.device.get_status_info()]})
                await broadcast({"type": "arduino_telemetry", "data": self.get_arduino_workbench_state()})
                return {"status": "success" if success else "failed", "pin": str(pin), "state": state_str}

            elif name == "set_all_arduino_pins":
                used_arduino = True
                self.active_view_mode = "arduino"
                if not self.device.is_connected:
                    await broadcast({"type": "chat_message", "role": "system", "content": "Hardware Notice: Actuation rejected (No Arduino connected)."})
                    return {"error": "Hardware Actuation Failed: No Arduino board is physically connected to the computer.", "connected": False}

                state = int(args.get("state", 0))
                success = await self.device.set_all_pins_async(state)
                state_str = "HIGH (ON)" if state else "LOW (OFF)"
                await broadcast({"type": "chat_message", "role": "system", "content": f"Hardware Actuation: All pins -> {state_str}"})
                await broadcast({"type": "device_update", "devices": [self.device.get_status_info()]})
                await broadcast({"type": "arduino_telemetry", "data": self.get_arduino_workbench_state()})
                return {"status": "success" if success else "failed", "pins": "D2-D13, A0-A5", "state": state_str}

            elif name == "get_pin_states":
                used_arduino = True
                states = self.device.get_all_states()
                await broadcast({"type": "arduino_telemetry", "data": self.get_arduino_workbench_state()})
                return {"pin_states": states, "device": self.device.device_name}

            elif name == "search_or_browse_web":
                used_web_search = True
                self.active_view_mode = "browser"
                query = args.get("query_or_url", "")
                await broadcast({"type": "state_change", "state": "browsing"})
                await broadcast({"type": "facial_expression", "mood": "browsing", "eye_shape": "reading", "glow_color": "#6ee7b7"})
                # Immediately open browser viewport with active radar searching HUD animation
                await broadcast({"type": "set_view_mode", "mode": "browser", "searching": True, "query": query})
                doc = await self.surfer.surf(query)
                # Stream sanitized document content with word/card flow animation
                await broadcast({"type": "set_view_mode", "mode": "browser", "data": doc, "searching": False})
                await broadcast({"type": "chat_message", "role": "system", "content": f"Web Research: {doc['title']}"})
                return doc

            elif name == "set_display_view":
                target_mode = args.get("mode", "none")
                self.active_view_mode = target_mode
                await broadcast({"type": "set_view_mode", "mode": target_mode})
                return {"status": "view_updated", "mode": target_mode}

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

            elif name == "build_and_flash_sketch":
                used_arduino = True
                self.active_view_mode = "arduino"
                sketch_code = args.get("sketch_code", "").strip()
                sketch_name = args.get("sketch_name", "cortex_pin_test").strip()
                sketch_name = re.sub(r'[^a-zA-Z0-9_]', '_', sketch_name) or "cortex_sketch"
                port = args.get("port", "").strip()
                fqbn = args.get("fqbn", "arduino:avr:nano").strip()

                if not sketch_code:
                    return {"status": "error", "error": "No sketch code provided to build."}

                await broadcast({"type": "state_change", "state": "programming"})
                await broadcast({"type": "facial_expression", "mood": "focused", "eye_shape": "narrow", "glow_color": "#a855f7"})

                # Locate or create build directory: cortex/scratch/sketches/<sketch_name>/
                cortex_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
                build_dir = os.path.join(cortex_dir, "scratch", "sketches", sketch_name)
                os.makedirs(build_dir, exist_ok=True)
                sketch_file = os.path.join(build_dir, f"{sketch_name}.ino")

                with open(sketch_file, "w", encoding="utf-8") as f:
                    f.write(sketch_code)

                # Auto-detect target port
                target_port = port
                if not target_port:
                    if self.device.port_name:
                        target_port = self.device.port_name
                    else:
                        avail = self.device.worker.scan_available_ports()
                        for p in avail:
                            if "com1" not in p["port"].lower():
                                target_port = p["port"]
                                break
                if not target_port:
                    target_port = "COM4"

                # Update active sketch context and open Hardware Workbench Viewport
                self.active_sketch["name"] = sketch_name
                self.active_sketch["code"] = sketch_code
                self.active_sketch["path"] = sketch_file
                self.active_sketch["port"] = target_port
                self.active_sketch["fqbn"] = fqbn
                self.active_sketch["step"] = 1
                self.active_sketch["step_name"] = "synthesis"
                self.active_sketch["status"] = "compiling"
                self.active_sketch["log"] = f"Created '{sketch_name}.ino'. Building for {fqbn} on {target_port}."

                await broadcast({"type": "set_view_mode", "mode": "arduino", "data": self.get_arduino_workbench_state()})
                await broadcast({"type": "chat_message", "role": "system", "content": f"Compiler: Created '{sketch_name}.ino'. Building for {fqbn}..."})

                # Locate arduino-cli
                bin_dir = os.path.join(cortex_dir, "bin")
                arduino_cli = os.path.join(bin_dir, "arduino-cli.exe")
                if not os.path.exists(arduino_cli):
                    arduino_cli = "arduino-cli"

                # Compile with auto-library installation retry loop
                compile_success = False
                compile_stdout = ""
                compile_stderr = ""

                self.active_sketch["step"] = 2
                self.active_sketch["step_name"] = "compiling"
                await broadcast({"type": "arduino_telemetry", "data": {
                    **self.get_arduino_workbench_state(),
                    "log": f"Invoking: arduino-cli compile --fqbn {fqbn} {sketch_file}..."
                }})

                for attempt in range(4):
                    comp_proc = await asyncio.create_subprocess_exec(
                        arduino_cli, "compile", "--fqbn", fqbn, sketch_file,
                        stdout=asyncio.subprocess.PIPE,
                        stderr=asyncio.subprocess.PIPE
                    )
                    out_b, err_b = await comp_proc.communicate()
                    compile_stdout = out_b.decode('utf-8', errors='replace').strip()
                    compile_stderr = err_b.decode('utf-8', errors='replace').strip()

                    if comp_proc.returncode == 0:
                        compile_success = True
                        break

                    combined_err = f"{compile_stdout}\n{compile_stderr}"
                    lib_match = re.search(r'fatal error:\s*([a-zA-Z0-9_\-]+)\.h:\s*No such file', combined_err, re.IGNORECASE)
                    if lib_match:
                        missing_lib = lib_match.group(1)
                        self.active_sketch["step"] = 3
                        self.active_sketch["step_name"] = "library_resolution"
                        await broadcast({"type": "arduino_telemetry", "data": {
                            **self.get_arduino_workbench_state(),
                            "log": f"Dependency Resolver: Missing library '{missing_lib}'. Installing via arduino-cli..."
                        }})
                        await broadcast({"type": "chat_message", "role": "system", "content": f"Dependency Resolver: Installing '{missing_lib}'..."})
                        install_proc = await asyncio.create_subprocess_exec(
                            arduino_cli, "lib", "install", missing_lib,
                            stdout=asyncio.subprocess.PIPE,
                            stderr=asyncio.subprocess.PIPE
                        )
                        await install_proc.communicate()
                        continue
                    else:
                        break

                if not compile_success:
                    self.active_sketch["status"] = "compile_failed"
                    self.active_sketch["log"] = compile_stderr or compile_stdout
                    await broadcast({"type": "arduino_telemetry", "data": self.get_arduino_workbench_state()})
                    await broadcast({"type": "chat_message", "role": "system", "content": f"Compiler Error:\n{compile_stderr or compile_stdout}"})
                    await broadcast({"type": "facial_expression", "mood": "skeptical", "eye_shape": "squint", "glow_color": "#ef4444"})
                    return {"status": "compile_failed", "stdout": compile_stdout, "stderr": compile_stderr}

                # Upload step
                self.active_sketch["step"] = 4
                self.active_sketch["step_name"] = "flashing"
                self.active_sketch["status"] = "flashing"
                await broadcast({"type": "arduino_telemetry", "data": {
                    **self.get_arduino_workbench_state(),
                    "log": f"Compilation passed. Uploading to {target_port} via avrdude..."
                }})
                await broadcast({"type": "chat_message", "role": "system", "content": f"Hardware Flash: Flashing build to microcontroller on {target_port}..."})

                # Safely pause serial worker
                await self.device.pause_serial()
                await asyncio.sleep(0.3)

                upload_stdout = ""
                upload_stderr = ""
                upload_success = False

                try:
                    upload_proc = await asyncio.create_subprocess_exec(
                        arduino_cli, "upload", "-p", target_port, "--fqbn", fqbn, sketch_file,
                        stdout=asyncio.subprocess.PIPE,
                        stderr=asyncio.subprocess.PIPE
                    )
                    out_b, err_b = await asyncio.wait_for(upload_proc.communicate(), timeout=45.0)
                    upload_stdout = out_b.decode('utf-8', errors='replace').strip()
                    upload_stderr = err_b.decode('utf-8', errors='replace').strip()
                    upload_success = (upload_proc.returncode == 0)
                except asyncio.TimeoutError:
                    upload_stderr = "Flash upload timed out after 45 seconds."
                finally:
                    await asyncio.sleep(0.5)
                    await self.device.resume_serial()

                if upload_success:
                    self.active_sketch["step"] = 5
                    self.active_sketch["step_name"] = "verified"
                    self.active_sketch["status"] = "verified"
                    self.active_sketch["log"] = upload_stdout or "Flash verified 100%. Firmware running on microcontroller."
                    await broadcast({"type": "arduino_telemetry", "data": self.get_arduino_workbench_state()})
                    await broadcast({"type": "chat_message", "role": "system", "content": f"Hardware Flash: Successfully flashed to {target_port}!"})
                    await broadcast({"type": "facial_expression", "mood": "confident", "eye_shape": "normal", "glow_color": "#22c55e"})
                    return {
                        "status": "success",
                        "sketch_name": sketch_name,
                        "port": target_port,
                        "fqbn": fqbn,
                        "detail": upload_stdout or "Flash verified 100%."
                    }
                else:
                    self.active_sketch["status"] = "upload_failed"
                    self.active_sketch["log"] = upload_stderr or upload_stdout
                    await broadcast({"type": "arduino_telemetry", "data": self.get_arduino_workbench_state()})
                    await broadcast({"type": "chat_message", "role": "system", "content": f"Hardware Flash Error: {upload_stderr or upload_stdout}"})
                    await broadcast({"type": "facial_expression", "mood": "alert", "eye_shape": "wide", "glow_color": "#ef4444"})
                    return {
                        "status": "upload_failed",
                        "port": target_port,
                        "error": upload_stderr or upload_stdout
                    }

            elif name == "compile_and_upload_sketch":
                used_arduino = True
                self.active_view_mode = "arduino"
                sketch_path = args.get("sketch_path", "").strip().strip('\'"')
                port = args.get("port", "").strip()
                fqbn = args.get("fqbn", "arduino:avr:nano").strip()

                await broadcast({"type": "state_change", "state": "programming"})
                await broadcast({"type": "facial_expression", "mood": "focused", "eye_shape": "narrow", "glow_color": "#a855f7"})

                # Locate arduino-cli executable
                bin_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "bin")
                arduino_cli = os.path.join(bin_dir, "arduino-cli.exe")
                if not os.path.exists(arduino_cli):
                    arduino_cli = "arduino-cli"

                if not os.path.exists(sketch_path):
                    err_msg = f"Sketch file not found at '{sketch_path}'. If you want to create or test a new sketch, invoke build_and_flash_sketch with the sketch code instead of looking for an existing file."
                    await broadcast({"type": "chat_message", "role": "system", "content": f"Hardware Flash Error: {err_msg}"})
                    return {"status": "error", "error": err_msg}

                # Auto-detect COM port if not specified
                target_port = port
                if not target_port:
                    if self.device.port_name:
                        target_port = self.device.port_name
                    else:
                        avail = self.device.worker.scan_available_ports()
                        for p in avail:
                            if "com1" not in p["port"].lower():
                                target_port = p["port"]
                                break
                if not target_port:
                    target_port = "COM4"

                # Update active sketch context and open Hardware Workbench Viewport
                sketch_name = os.path.splitext(os.path.basename(sketch_path))[0]
                self.active_sketch["name"] = sketch_name
                self.active_sketch["path"] = sketch_path
                self.active_sketch["port"] = target_port
                self.active_sketch["fqbn"] = fqbn
                self.active_sketch["step"] = 1
                self.active_sketch["step_name"] = "synthesis"
                self.active_sketch["status"] = "compiling"
                self.active_sketch["log"] = f"Located '{os.path.basename(sketch_path)}'. Building for {fqbn} on {target_port}."

                # Try loading sketch code for future quick flashes
                try:
                    with open(sketch_path, "r", encoding="utf-8", errors="ignore") as f:
                        self.active_sketch["code"] = f.read()
                except Exception:
                    pass

                await broadcast({"type": "set_view_mode", "mode": "arduino", "data": self.get_arduino_workbench_state()})
                await broadcast({"type": "chat_message", "role": "system", "content": f"Compiler: Building sketch '{os.path.basename(sketch_path)}' for {fqbn}..."})

                # Compile with auto-library installation retry loop
                compile_success = False
                compile_stdout = ""
                compile_stderr = ""

                self.active_sketch["step"] = 2
                self.active_sketch["step_name"] = "compiling"
                await broadcast({"type": "arduino_telemetry", "data": {
                    **self.get_arduino_workbench_state(),
                    "log": f"Invoking arduino-cli compile --fqbn {fqbn} {sketch_path}..."
                }})

                for attempt in range(4):
                    comp_proc = await asyncio.create_subprocess_exec(
                        arduino_cli, "compile", "--fqbn", fqbn, sketch_path,
                        stdout=asyncio.subprocess.PIPE,
                        stderr=asyncio.subprocess.PIPE
                    )
                    out_b, err_b = await comp_proc.communicate()
                    compile_stdout = out_b.decode('utf-8', errors='replace').strip()
                    compile_stderr = err_b.decode('utf-8', errors='replace').strip()

                    if comp_proc.returncode == 0:
                        compile_success = True
                        break

                    combined_err = f"{compile_stdout}\n{compile_stderr}"
                    lib_match = re.search(r'fatal error:\s*([a-zA-Z0-9_\-]+)\.h:\s*No such file', combined_err, re.IGNORECASE)
                    if lib_match:
                        missing_lib = lib_match.group(1)
                        self.active_sketch["step"] = 3
                        self.active_sketch["step_name"] = "library_resolution"
                        await broadcast({"type": "arduino_telemetry", "data": {
                            **self.get_arduino_workbench_state(),
                            "log": f"Dependency Resolver: Missing library '{missing_lib}'. Installing via arduino-cli..."
                        }})
                        await broadcast({"type": "chat_message", "role": "system", "content": f"Dependency Resolver: Missing library '{missing_lib}' detected. Installing via arduino-cli..."})
                        install_proc = await asyncio.create_subprocess_exec(
                            arduino_cli, "lib", "install", missing_lib,
                            stdout=asyncio.subprocess.PIPE,
                            stderr=asyncio.subprocess.PIPE
                        )
                        inst_out, _ = await install_proc.communicate()
                        await broadcast({"type": "chat_message", "role": "system", "content": f"Dependency Resolver: Installed '{missing_lib}'. Re-compiling..."})
                        continue
                    else:
                        break

                if not compile_success:
                    self.active_sketch["status"] = "compile_failed"
                    self.active_sketch["log"] = compile_stderr or compile_stdout
                    await broadcast({"type": "arduino_telemetry", "data": self.get_arduino_workbench_state()})
                    await broadcast({"type": "chat_message", "role": "system", "content": f"Compiler Error:\n{compile_stderr or compile_stdout}"})
                    await broadcast({"type": "facial_expression", "mood": "skeptical", "eye_shape": "squint", "glow_color": "#ef4444"})
                    return {"status": "compile_failed", "stdout": compile_stdout, "stderr": compile_stderr}

                # Upload step
                self.active_sketch["step"] = 4
                self.active_sketch["step_name"] = "flashing"
                self.active_sketch["status"] = "flashing"
                await broadcast({"type": "arduino_telemetry", "data": {
                    **self.get_arduino_workbench_state(),
                    "log": f"Build passed. Uploading to {target_port} via avrdude..."
                }})
                await broadcast({"type": "chat_message", "role": "system", "content": f"Compiler: Build passed. Flashing microcontroller on {target_port}..."})

                # Safely pause serial worker to prevent COM port lock collision
                await self.device.pause_serial()
                await asyncio.sleep(0.3)

                upload_stdout = ""
                upload_stderr = ""
                upload_success = False

                try:
                    upload_proc = await asyncio.create_subprocess_exec(
                        arduino_cli, "upload", "-p", target_port, "--fqbn", fqbn, sketch_path,
                        stdout=asyncio.subprocess.PIPE,
                        stderr=asyncio.subprocess.PIPE
                    )
                    out_b, err_b = await asyncio.wait_for(upload_proc.communicate(), timeout=45.0)
                    upload_stdout = out_b.decode('utf-8', errors='replace').strip()
                    upload_stderr = err_b.decode('utf-8', errors='replace').strip()
                    upload_success = (upload_proc.returncode == 0)
                except asyncio.TimeoutError:
                    upload_stderr = "Flash upload timed out after 45 seconds."
                finally:
                    await asyncio.sleep(0.5)
                    await self.device.resume_serial()
                    sketch_text = self.active_sketch.get("code", "")
                    m_baud = re.search(r'Serial\.begin\s*\(\s*(\d+)\s*\)', sketch_text)
                    if m_baud:
                        try:
                            await self.device.set_baudrate(int(m_baud.group(1)))
                        except Exception:
                            pass

                if upload_success:
                    self.active_sketch["step"] = 5
                    self.active_sketch["step_name"] = "verified"
                    self.active_sketch["status"] = "verified"
                    self.active_sketch["log"] = upload_stdout or "Flash verified 100%. Firmware running on microcontroller."
                    await broadcast({"type": "arduino_telemetry", "data": self.get_arduino_workbench_state()})
                    await broadcast({"type": "chat_message", "role": "system", "content": f"Hardware Flash: Firmware successfully uploaded to {target_port}!"})
                    await broadcast({"type": "facial_expression", "mood": "confident", "eye_shape": "normal", "glow_color": "#22c55e"})
                    return {
                        "status": "success",
                        "sketch": sketch_path,
                        "port": target_port,
                        "fqbn": fqbn,
                        "detail": upload_stdout or "Flash verified 100%."
                    }
                else:
                    self.active_sketch["status"] = "upload_failed"
                    self.active_sketch["log"] = upload_stderr or upload_stdout
                    await broadcast({"type": "arduino_telemetry", "data": self.get_arduino_workbench_state()})
                    await broadcast({"type": "chat_message", "role": "system", "content": f"Hardware Flash Error: {upload_stderr or upload_stdout}"})
                    await broadcast({"type": "facial_expression", "mood": "alert", "eye_shape": "wide", "glow_color": "#ef4444"})
                    return {
                        "status": "upload_failed",
                        "port": target_port,
                        "error": upload_stderr or upload_stdout
                    }

            elif name == "install_package_or_tool":
                pkg_type = args.get("package_type", "python").lower()
                pkg_name = args.get("package_name", "").strip()

                await broadcast({"type": "state_change", "state": "programming"})
                await broadcast({"type": "facial_expression", "mood": "focused", "eye_shape": "narrow", "glow_color": "#a855f7"})
                await broadcast({"type": "chat_message", "role": "system", "content": f"Package Manager: Installing {pkg_type} package '{pkg_name}'..."})

                if pkg_type == "python":
                    cmd = f"python -m pip install {pkg_name}"
                elif pkg_type == "arduino":
                    bin_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "bin")
                    arduino_cli = os.path.join(bin_dir, "arduino-cli.exe")
                    if not os.path.exists(arduino_cli):
                        arduino_cli = "arduino-cli"
                    cmd = f"& '{arduino_cli}' lib install '{pkg_name}'"
                elif pkg_type == "winget":
                    cmd = f"winget install --id {pkg_name} -e --accept-source-agreements --accept-package-agreements"
                elif pkg_type == "npm":
                    cmd = f"npm install -g {pkg_name}"
                else:
                    cmd = f"pip install {pkg_name}"

                result = await self.cli_runner.execute_raw(cmd, timeout_seconds=120)
                if result.get("success"):
                    await broadcast({"type": "chat_message", "role": "system", "content": f"Package Manager: Successfully installed '{pkg_name}'."})
                    await broadcast({"type": "facial_expression", "mood": "confident", "eye_shape": "normal", "glow_color": "#22c55e"})
                else:
                    await broadcast({"type": "chat_message", "role": "system", "content": f"Package Manager Warning: Installation finished with message: {result.get('stderr') or result.get('stdout')}"})

                return result

            return {"error": f"Unknown tool: {name}"}

        # Dynamically build system prompt with live grounding context & skills catalog
        # Probe physical hardware status live on EVERY turn for absolute ground truth
        hw_stat = await self.device.check_hardware_status()
        learned_facts = self.knowledge.get_category_facts("pin_mapping")
        grounding_hdr = self.conv_memory.get_grounding_context(
            hw_status=hw_stat,
            camera_active=self.camera.is_camera_active(),
            learned_facts=learned_facts
        )
        skills_hdr = self.skill_manager.get_skill_catalog_prompt()
        full_system_prompt = f"{BASE_SYSTEM_PROMPT}\n\n{grounding_hdr}\n\n{skills_hdr}"

        history = self.conv_memory.get_recent_history(limit=8)

        # Detect and auto-cache any referenced .ino sketch file from the user's prompt
        ino_match = re.search(r'(?:file:///)?([a-zA-Z]:[\\/][^"\';\n\r]+\.ino)', text_clean)
        if ino_match:
            clean_ino_path = ino_match.group(1).replace('/', '\\')
            if os.path.exists(clean_ino_path):
                try:
                    with open(clean_ino_path, 'r', encoding='utf-8', errors='ignore') as f:
                        ino_content = f.read()
                    self.active_sketch["path"] = clean_ino_path
                    self.active_sketch["name"] = os.path.splitext(os.path.basename(clean_ino_path))[0]
                    self.active_sketch["code"] = ino_content
                    self.active_sketch["status"] = "loaded"
                    self.active_sketch["log"] = f"Loaded '{os.path.basename(clean_ino_path)}' ({len(ino_content)} bytes). Ready to compile or flash."
                    await broadcast({"type": "arduino_telemetry", "data": self.get_arduino_workbench_state()})
                except Exception as e:
                    print(f"[Brain] Error reading .ino: {e}")

        # Run autonomous ReAct agent loop - let the AI freely decide!
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

        # Auto-dismiss viewports if user shifted topic away
        if self.active_view_mode == "browser" and not used_web_search:
            await broadcast({"type": "set_view_mode", "mode": "none"})
            self.active_view_mode = "none"
        elif self.active_view_mode == "camera" and not used_camera:
            await broadcast({"type": "set_view_mode", "mode": "none"})
            self.active_view_mode = "none"
        elif self.active_view_mode == "arduino" and not used_arduino:
            # Only dismiss hardware workbench if user clearly changed topics to web search or vision
            if used_web_search or used_camera:
                await broadcast({"type": "set_view_mode", "mode": "none"})
                self.active_view_mode = "none"

        await broadcast({"type": "state_change", "state": "idle"})
        return tts_text
