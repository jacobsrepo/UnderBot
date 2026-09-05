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
import time
import datetime
from pathlib import Path
from typing import Dict, Any, Optional, Callable

from memory.openclaw_memory import OpenClawMemory
from core.sentence_chunker import SentenceChunker
from devices.serial_device import SerialWorker, SerialDevice
from vision.camera import Camera
from vision.probe import HardwareVisionProbe
from research.surfer import WebSurfer
from tts.speaker import VoiceSpeaker
from llm.agent import CortexAgent
from cli.runner import PowerShellRunner, CliRunner
from skills.manager import SkillManager
from pc.pc_control import PCController




class CortexBrain:
    def __init__(self):
        self.openclaw_memory = OpenClawMemory(Path(__file__).parent.parent / "memory")
        self.conv_memory = self.openclaw_memory
        self.knowledge = self.openclaw_memory
        self.sentence_chunker = SentenceChunker(min_char_threshold=20)
        self.device = SerialWorker(port="COM4", baudrate=115200)
        self.device.start()
        self.camera = Camera()
        self.probe = HardwareVisionProbe(self.device, self.camera)
        self.surfer = WebSurfer()
        self.speaker = VoiceSpeaker()
        self.agent = CortexAgent(model="qwen2.5-coder:7b")
        self.cli_runner = PowerShellRunner()
        self.skill_manager = SkillManager()
        self.pc = PCController()

        # Start camera background daemon for instant VisualSceneBuffer updates
        self.camera.start_background_daemon()

        self.active_view_mode = "none"
        self.name = "Cortex"

        # Active Hardware / Arduino Context & Workbench State
        self.active_sketch: Dict[str, Any] = {
            "name": "cortex_sketch",
            "code": "",
            "path": "",
            "port": "None",
            "fqbn": "arduino:avr:nano",
            "status": "idle",
            "log": "Hardware diagnostics ready. No physical board currently connected via USB.",
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

    @staticmethod
    def _clean_text_artifacts(text: str) -> str:
        """
        Strips any stray LLM meta-tags, mood tags, lombok artifacts, or bracketed tag leftovers.
        """
        if not text:
            return ""
        # Remove any Lombok / ombok prefix variations
        clean = re.sub(r'\[?[A-Za-z]*[Ll]ombok[A-Za-z0-9;:_<>#\s\-]*\]?>*', '', text)
        clean = re.sub(r'ombok;>*(?:glow:[^>]+>)?(?:mood:[^;\n]+;)?', '', clean, flags=re.IGNORECASE)
        # Remove any mood/glow bracket tags
        clean = re.sub(r'\[[^\]]*(?:mood|glow|eye|intensity)[^\]]*\]', '', clean, flags=re.IGNORECASE)
        clean = re.sub(r'\b(?:mood|glow):[a-zA-Z0-9_#]+;?', '', clean, flags=re.IGNORECASE)
        clean = re.sub(r'\[(?:insert|system|hardware|vision)[^\]]*\]', '', clean, flags=re.IGNORECASE)
        return clean.strip()

    def _sanitize_for_tts(self, text: str) -> str:
        """
        Hardening Check 4: Strips inline mood, metadata tags, raw code blocks, markdown tables,
        and syntax before audio synthesis so Cortex never reads code or formatting syntax out loud.
        """
        clean = self._clean_text_artifacts(text)
        # Strip all markdown code blocks completely
        clean = re.sub(r'```[a-zA-Z0-9_\-\.]*[\s\S]*?```', '', clean)
        # Strip inline code backticks and code snippets
        clean = re.sub(r'`[^`\n]+`', '', clean)
        # Strip markdown links: [Text](url) -> Text
        clean = re.sub(r'\[([^\]]+)\]\([^\)]+\)', r'\1', clean)
        # Strip URLs
        clean = re.sub(r'https?://\S+', '', clean)
        # Strip raw file paths like C:\Users\... so it doesn't read long backslashes
        clean = re.sub(r'[A-Za-z]:\\(?:[\w\.-]+\\)*([\w\.-]+)', r'\1', clean)
        # Strip curly brace blocks if any code leaked
        clean = re.sub(r'\{[^\}]{8,}\}', '', clean)
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
        print(f"[Brain] Processing user message: \"{text_clean[:60]}\"")
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
                    "port": self.device.port_name or "None",
                    "output": serial_log
                }

            elif name == "run_cli_command":
                cmd = args.get("command", "")
                cwd = args.get("cwd", None)
                await broadcast({"type": "state_change", "state": "programming"})
                # Execute with self-healing retry loop silently
                result = await self.cli_runner.execute_with_healing(cmd, cwd=cwd)
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
                    return {"error": "Cannot probe pins: No Arduino is physically connected via USB.", "connected": False}

                color = args.get("color", "blue").lower()
                await broadcast({"type": "set_view_mode", "mode": "camera"})
                await broadcast({"type": "facial_expression", "mood": "focused", "eye_shape": "narrow", "glow_color": "#a855f7"})

                async def on_probe_step(step_msg):
                    pass

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

                # Zero-latency inspection from VisualSceneBuffer
                vision_result = await self.camera.inspect(target)
                return vision_result

            elif name == "set_arduino_pin":
                used_arduino = True
                self.active_view_mode = "arduino"
                if not self.device.is_connected:
                    return {"error": "Hardware Actuation Failed: No Arduino board is physically connected to the computer.", "connected": False}

                pin = args.get("pin", "D2")
                state = int(args.get("state", 0))
                success = await self.device.set_pin_async(pin, state)
                state_str = "HIGH (ON)" if state else "LOW (OFF)"
                await broadcast({"type": "device_update", "devices": [self.device.get_status_info()]})
                await broadcast({"type": "arduino_telemetry", "data": self.get_arduino_workbench_state()})
                return {"status": "success" if success else "failed", "pin": str(pin), "state": state_str}

            elif name == "set_all_arduino_pins":
                used_arduino = True
                self.active_view_mode = "arduino"
                if not self.device.is_connected:
                    return {"error": "Hardware Actuation Failed: No Arduino board is physically connected to the computer.", "connected": False}

                state = int(args.get("state", 0))
                success = await self.device.set_all_pins_async(state)
                state_str = "HIGH (ON)" if state else "LOW (OFF)"
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
                return doc

            elif name == "get_user_location":
                loc = await self.surfer.geo.get_live_location()
                return loc

            elif name == "search_places_and_map":
                used_web_search = True
                self.active_view_mode = "browser"
                q = args.get("query", "")
                loc = args.get("location")
                limit = int(args.get("limit", 5))
                await broadcast({"type": "state_change", "state": "browsing"})
                await broadcast({"type": "facial_expression", "mood": "browsing", "eye_shape": "reading", "glow_color": "#38bdf8"})
                await broadcast({"type": "set_view_mode", "mode": "browser", "searching": True, "query": f"Places: {q}"})
                places_data = await self.surfer.geo.search_places(q, near_location=loc, limit=limit)
                await broadcast({"type": "set_view_mode", "mode": "browser", "data": places_data, "searching": False})
                return places_data

            elif name == "plan_day_itinerary":
                used_web_search = True
                self.active_view_mode = "browser"
                dest = args.get("destination", "")
                pref = args.get("preferences", "")
                budget = args.get("budget", "moderate")
                await broadcast({"type": "state_change", "state": "browsing"})
                await broadcast({"type": "facial_expression", "mood": "focused", "eye_shape": "normal", "glow_color": "#a855f7"})
                await broadcast({"type": "set_view_mode", "mode": "browser", "searching": True, "query": f"Itinerary: {dest or 'Local Area'}"})
                itin_data = await self.surfer.plan_day_itinerary(dest, preferences=pref, budget=budget)
                await broadcast({"type": "set_view_mode", "mode": "browser", "data": itin_data, "searching": False})
                return itin_data

            elif name == "search_prices":
                used_web_search = True
                self.active_view_mode = "browser"
                q = args.get("query", "")
                await broadcast({"type": "state_change", "state": "browsing"})
                await broadcast({"type": "facial_expression", "mood": "analytical", "eye_shape": "narrow", "glow_color": "#fbbf24"})
                await broadcast({"type": "set_view_mode", "mode": "browser", "searching": True, "query": f"Prices: {q}"})
                prices_data = await self.surfer.search_prices_and_deals(q)
                await broadcast({"type": "set_view_mode", "mode": "browser", "data": prices_data, "searching": False})
                return prices_data

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
                self.openclaw_memory.save_fact(cat, k, v)
                return {"status": "saved", "category": cat, "key": k}

            elif name in ("recall_from_memory", "search_memory"):
                q = args.get("query", "")
                return {"results": self.openclaw_memory.search_memory(q)}

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
                    await broadcast({"type": "facial_expression", "mood": "confident", "eye_shape": "normal", "glow_color": "#22c55e"})
                return result

            # ------------------------------------------------------------------
            # PC Control Tools
            # ------------------------------------------------------------------

            elif name == "get_volume":
                return await self.pc.get_volume()

            elif name == "set_volume":
                level = int(args.get("level", 50))
                result = await self.pc.set_volume(level)
                return result

            elif name == "mute_audio":
                return await self.pc.mute_audio()

            elif name == "unmute_audio":
                return await self.pc.unmute_audio()

            elif name == "launch_app":
                app_name = args.get("app_name", "")
                await broadcast({"type": "state_change", "state": "programming"})
                result = await self.pc.launch_app(app_name)
                return result

            elif name == "open_file":
                path = args.get("path", "")
                result = await self.pc.open_file(path)
                return result

            elif name == "list_windows":
                return await self.pc.list_windows()

            elif name == "focus_window":
                return await self.pc.focus_window(args.get("title", ""))

            elif name == "close_window":
                return await self.pc.close_window(args.get("title", ""))

            elif name == "take_screenshot":
                result = await self.pc.take_screenshot()
                if "screenshot" in result:
                    # Feed into camera for vision inspection
                    self.camera.update_frame(result["screenshot"])
                    await broadcast({"type": "set_view_mode", "mode": "camera"})
                return {k: v for k, v in result.items() if k != "screenshot"}  # don't send huge b64 to LLM

            elif name == "get_system_info":
                return await self.pc.get_system_info()

            elif name == "get_running_processes":
                limit = int(args.get("limit", 20))
                return await self.pc.get_running_processes(limit=limit)

            elif name == "kill_process":
                identifier = args.get("identifier", "")
                return await self.pc.kill_process(identifier)

            elif name == "type_text":
                text = args.get("text", "")
                interval = float(args.get("interval", 0.02))
                return await self.pc.type_text(text, interval=interval)

            elif name == "press_keys":
                keys = args.get("keys", [])
                if isinstance(keys, str):
                    keys = [k.strip() for k in keys.split(",")]
                return await self.pc.press_keys(keys)

            elif name == "read_clipboard":
                return await self.pc.read_clipboard()

            elif name == "write_clipboard":
                text = args.get("text", "")
                return await self.pc.write_clipboard(text)

            elif name == "list_directory":
                path = args.get("path", "")
                return await self.pc.list_directory(path)

            elif name == "find_files":
                root = args.get("root", "C:\\Users\\Athul C S")
                pattern = args.get("pattern", "*")
                max_results = int(args.get("max_results", 50))
                return await self.pc.find_files(root, pattern, max_results=max_results)

            return {"error": f"Unknown tool: {name}"}

        # Dynamically build system prompt with Section 5 Dynamic Prompt Template with Temporal Grounding
        now_iso = datetime.datetime.now().isoformat()
        grounding_facts = self.openclaw_memory.get_grounding_context()
        hw_stat = await self.device.check_hardware_status()
        if hw_stat.get("connected"):
            hw_str = f"Arduino Nano on {hw_stat.get('port')} (ONLINE and responsive)"
        else:
            hw_str = "DISCONNECTED (No microcontroller is physically plugged into USB. You cannot read or set pins until a board is connected. If asked, confirm no board is connected.)"
        cam_str = "ACTIVE (Streaming live video)" if self.camera.is_camera_active() else "OFF / INACTIVE (No video feed; only user can enable in browser)"
        loc = await self.surfer.geo.get_live_location()
        loc_str = f"{loc.get('city')}, {loc.get('country')} (Lat: {loc.get('latitude')}, Lon: {loc.get('longitude')})" if loc.get("city") else "Auto-detected from client"

        full_system_prompt = f"""You are Cortex, an embodied, intelligent desktop companion operating natively on Windows.
You are a calm, sharp, proactive partner (JARVIS-style). You speak naturally, directly, and with conversational continuity.

Current Environment Grounding:
- Current Local Timestamp: {now_iso}
- Host Operating System: Windows (PowerShell Core)
- Physical Microcontroller: {hw_str}
- Vision Sensor: {cam_str}
- Live Physical Location: {loc_str}

Long-Term Context Grounding (OpenClaw Root Knowledge):
{grounding_facts}

Core Directives:
1. CONVERSATIONAL PARTNERSHIP & TONE:
   - Speak naturally, sharply, and concisely. Keep spoken/chat responses intelligent, helpful, and direct.
   - Do NOT introduce yourself or recite boilerplate greetings ("Hello Athul, how can I help you today?") on every turn. Maintain natural dialogue flow.
   - Do NOT give unprompted explanations of internal steps. If the user asks for a file, answer where it is or that it does not exist.
   - NEVER narrate or announce commands or tools before running them (do NOT say "I will now search using PowerShell...", "Let me check the files...", "I am running a script..."). Run the tool silently in the background and report only the final direct answer.
   - If asked where a file or directory is: inspect silently with `run_cli_command`. If found, state the exact path. If not found, say: "No such file located."

2. PROACTIVE VISUAL PROJECTION AGENCY:
   - Whenever the user asks to see, show, look up, browse, search, compare prices, or plan a day:
     * YOU MUST CALL THE CORRESPONDING TOOL to project the visual canvas onto the screen:
       - Plan a day, trip, or schedule -> MUST call `plan_day_itinerary(destination=..., preferences=..., budget=...)`
       - Prices, deals, buying, or rates -> MUST call `search_prices(query=...)`
       - Places, maps, cafes, food, hotels, attractions, or directions -> MUST call `search_places_and_map(query=..., location=...)`
       - Web search, articles, news, or URLs -> MUST call `search_or_browse_web(query_or_url=...)`
     * When a projection is launched, your avatar glides smoothly to the companion perch while the interactive canvas expands into the main stage. Refer to the projection naturally ("I've pulled up the local map for you.", "Here is a 1-day itinerary blueprint with estimated costs.").
   - When asked where the user is physically located: state their live physical location ({loc_str}) or call `get_user_location`.

3. PHYSICAL HARDWARE HONESTY:
   - Strictly honor Physical Microcontroller status. If disconnected, state directly that no board is connected via USB. Never fabricate, assume, or claim hardware is connected when physical USB connection is absent.

4. ZERO ROBOTIC FLUFF:
   - Speak naturally without meta-tags, mood tags, bracketed prefixes, or robotic announcements.

5. NATIVE PC CONTROL (use these instead of PowerShell for system tasks):
   - Adjust volume → `set_volume`, `get_volume`, `mute_audio`, `unmute_audio`
   - Open apps or files → `launch_app`, `open_file`
   - Manage windows → `list_windows`, `focus_window`, `close_window`
   - Browse files → `list_directory`, `find_files`
   - System health → `get_system_info`, `get_running_processes`, `kill_process`
   - Keyboard/mouse input → `type_text`, `press_keys`
   - Clipboard → `read_clipboard`, `write_clipboard`
   - See the screen → `take_screenshot`
   - Only fall back to `run_cli_command` for complex multi-step shell tasks not covered above.
"""
        skills_hdr = self.skill_manager.get_skill_catalog_prompt()
        if skills_hdr:
            full_system_prompt += f"\n\n{skills_hdr}"

        # Dynamic Visual Intent Hinting: guarantees the local model executes visual browser tools instead of echoing plain text
        lower_input = text_clean.lower()
        if re.search(r'\b(daily plan|day plan|plan a day|plan my day|itinerary|day trip|schedule my day)\b', lower_input):
            full_system_prompt += "\n[IMPERATIVE: The user is requesting a day plan or itinerary. You MUST invoke `plan_day_itinerary` immediately so the interactive visual blueprint opens in the browser. DO NOT answer with text alone without executing the tool.]"
        elif re.search(r'\b(price of|prices of|cost of|how much is|look up the price|check price|compare prices|pricing|deals on)\b', lower_input):
            full_system_prompt += "\n[IMPERATIVE: The user is asking about prices or deals. You MUST invoke `search_prices` immediately so the live pricing comparison grid opens in the browser. DO NOT answer with text alone without executing the tool.]"
        elif re.search(r'\b(show me cafes|show me restaurants|places to visit|cafes near|restaurants near|places near|show me places|map of|find hotels|find cafes|spots in)\b', lower_input):
            full_system_prompt += "\n[IMPERATIVE: The user is asking for places, maps, or venues. You MUST invoke `search_places_and_map` immediately so the interactive Google Map and place cards open in the browser. DO NOT answer with text alone without executing the tool.]"
        elif re.search(r'\b(show me|browse|search the web for|look up on web|search for)\b', lower_input) and not re.search(r'\b(camera|pin|arduino|port|com4)\b', lower_input):
            full_system_prompt += "\n[IMPERATIVE: The user is asking to show or browse web content. You MUST invoke `search_or_browse_web` immediately so the visual browser viewport opens. DO NOT answer with text alone without executing the tool.]"

        history = self.openclaw_memory.get_recent_history(limit=8)

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

        # Setup real-time UI typing stream and pipelined sentence-by-sentence TTS
        msg_id = f"msg_{int(time.time() * 1000)}"
        chunk_idx = 0
        tts_queue: asyncio.Queue = asyncio.Queue()
        tts_worker_task = asyncio.create_task(self._stream_tts_worker(tts_queue, broadcast))

        tag_buffer = ""
        in_tag = False

        async def on_token_chunk(token: str):
            nonlocal chunk_idx, tag_buffer, in_tag
            if not token:
                return

            if "ombok" in token.lower():
                return

            to_send = ""
            for char in token:
                if char == '[':
                    in_tag = True
                    tag_buffer = "["
                elif in_tag:
                    tag_buffer += char
                    if char == ']':
                        in_tag = False
                        if re.match(r'\[(mood|glow|eye|intensity|lombok|insert|system)', tag_buffer, re.IGNORECASE):
                            tag_buffer = ""
                        else:
                            to_send += tag_buffer
                            tag_buffer = ""
                    elif len(tag_buffer) > 40:
                        in_tag = False
                        to_send += tag_buffer
                        tag_buffer = ""
                else:
                    to_send += char

            if not to_send:
                return

            # 1. Stream token to UI immediately
            await broadcast({
                "type": "chat_stream_chunk",
                "msg_id": msg_id,
                "chunk": to_send
            })
            # 2. Feed token into Sentence Chunker
            sentences = self.sentence_chunker.append(to_send)
            for s in sentences:
                clean_s = self._sanitize_for_tts(s)
                if clean_s:
                    await tts_queue.put((chunk_idx, clean_s, False))
                    chunk_idx += 1

        # Run autonomous ReAct agent loop with real-time streaming
        response = await self.agent.run(
            messages=history,
            system_prompt=full_system_prompt,
            tool_executor=execute_tool,
            on_token_chunk=on_token_chunk
        )

        # Flush any remaining sentence from chunker
        remaining_sentences = self.sentence_chunker.flush()
        for s in remaining_sentences:
            clean_s = self._sanitize_for_tts(s)
            if clean_s:
                await tts_queue.put((chunk_idx, clean_s, True))
                chunk_idx += 1

        # Signal TTS worker completion and await queue drain
        await tts_queue.put(None)
        await tts_worker_task

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

        # Finalize streaming message in chat UI
        clean_content = self._clean_text_artifacts(response)
        tts_text = self._sanitize_for_tts(response)
        await broadcast({
            "type": "chat_stream_end",
            "msg_id": msg_id,
            "full_content": clean_content
        })

        # Save to OpenClaw short-term session and medium-term daily journal
        self.openclaw_memory.add_message("assistant", clean_content)
        self.openclaw_memory.append_daily_log(
            action="Turn Complete",
            details=f"**User**: {text_clean}\n**Cortex**: {clean_content}"
        )

        # Keep active viewports open across turns so user can read/interact with them;
        # Only switch viewport if another tool explicitly changed active_view_mode
        if used_web_search:
            self.active_view_mode = "browser"
        elif used_camera:
            self.active_view_mode = "camera"
        elif used_arduino:
            self.active_view_mode = "arduino"

        await broadcast({"type": "state_change", "state": "idle"})
        return tts_text

    async def _stream_tts_worker(self, tts_queue: asyncio.Queue, broadcast: Callable):
        while True:
            item = await tts_queue.get()
            if item is None:
                tts_queue.task_done()
                break
            chunk_idx, text, is_final = item
            try:
                audio_uri = await self.speaker.synthesize_speech(text)
                if audio_uri:
                    await broadcast({
                        "type": "voice_audio_chunk",
                        "audio": audio_uri,
                        "text": text,
                        "chunk_index": chunk_idx,
                        "is_final": is_final
                    })
            except Exception as e:
                print(f"[TTS Stream] Synthesis error: {e}")
            finally:
                tts_queue.task_done()

    def abort_current_generation(self):
        """Barge-In: Flush chunker buffer and reset generation state."""
        self.sentence_chunker.flush()
