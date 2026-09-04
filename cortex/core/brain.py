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

ACTION-FIRST EXECUTION MANDATE (CRITICAL):
1. IMMEDIATE ACTION: When the user requests an action (compile code, upload/flash firmware, install software/packages, search the web, check hardware, list files, run a command), CALL THE APPROPRIATE TOOL IMMEDIATELY.
2. NEVER STALL OR ASK FOR REPETITIVE PERMISSION: If the user gave an objective or goal, you have full authorization to execute all required sub-steps (searching, installing missing dependencies, compiling, testing, flashing). DO NOT ask "Would you like to proceed?", "Shall I start?", or "Do you want me to install this?". Take the action immediately and report the actual result.
3. NEVER SIMULATE OR GUESS: Never pretend to upload, flash, or test. Always invoke the real tool (`build_and_flash_sketch`, `compile_and_upload_sketch`, `run_cli_command`, `install_package_or_tool`, `check_hardware_connection`).

LIVE STATE VERIFICATION (NEVER RELY ON STALE MEMORY):
1. USB & MICROCONTROLLERS: Always call `check_hardware_connection` live whenever asked about connected devices, USB ports, or Arduino status. Never answer from previous conversation memory.
   - If it returns `connected: false`, state truthfully: "No Arduino board is currently connected to the computer. Scanned COM ports show no active USB microcontroller."
   - NEVER call `set_all_arduino_pins` or `set_arduino_pin` to check connection!
   - If the board is disconnected, NEVER claim pins are ON or responding.
2. FILES, FOLDERS & DIRECTORIES: Always verify files live on the host filesystem using `run_cli_command` with PowerShell (`Test-Path`, `Get-ChildItem`) or search tools. Never assume a file exists or doesn't exist without checking.

ARDUINO & FIRMWARE AUTOMATION:
1. CREATING, TESTING, OR RUNNING CODE (e.g. "run a basic test script on all pins", "blink LED", "write a test sketch", "test pins"):
   - ALWAYS invoke `build_and_flash_sketch` with your generated Arduino C++ code!
   - NEVER search for non-existent files in Documents or hallucinate file paths! Build the code and flash it directly with `build_and_flash_sketch`.
2. EXISTING SKETCHES ON DISK:
   - Only call `compile_and_upload_sketch` if the user gave a specific existing file path (e.g. "push binary_RTConly.ino").
3. CONVERSATIONAL SPEECH & CODE RULES (CRITICAL):
   - NEVER recite, output, or dump raw C++ or PowerShell code into your speech or conversational assistant response!
   - Your speech will be read aloud by TTS. Do NOT read code syntax aloud.
   - Speak ONLY a concise, natural, human-friendly summary of what was accomplished (e.g. "I built and flashed a pin test sketch to the Arduino Nano on COM4. All digital pins are now cycling through test states.").

POWERSHELL & PACKAGE INSTALLATION:
1. Use `install_package_or_tool` to install Python packages (pip), Arduino libraries (arduino-cli), Windows utilities (winget), or Node packages (npm) autonomously.
2. Use `run_cli_command` to execute native Windows PowerShell cmdlets, inspect directory contents, check logs, or run scripts.

NEWS & WEB INTELLIGENCE RULES:
1. When asked for the latest news, breaking news, or what is happening (e.g. "what is the latest news from Nepal?", "latest news about SpaceX"), call `search_or_browse_web`.
2. The UI automatically displays the full Reader View briefing in the browser screen. In your chat/spoken reply, provide a crisp, spoken overview of the headline and key developments. Never recite links or URLs.

GENERAL CAPABILITIES:
1. Date & Time: Always rely on your LIVE SYSTEM GROUNDING or `Get-Date`. Never emit placeholders like '[insert current time here]'.
2. Camera & Physical LEDs: Call `inspect_camera` to read ground-truth optical light emissions (Blue, Green, Red). Never claim an LED is ON unless physical light is detected.
3. Robot Face: Actively express mood using `set_facial_expression` or tags like `[mood:curious;eye:inquiring;glow:#38bdf8]`.
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

        # Tool execution router
        async def execute_tool(name: str, args: Dict[str, Any]) -> Any:
            if name == "check_hardware_connection":
                status = await self.device.check_hardware_status()
                conn_str = "CONNECTED" if status.get("connected") else "DISCONNECTED"
                await broadcast({
                    "type": "chat_message",
                    "role": "system",
                    "content": f"Hardware Sensor: Microcontroller is {conn_str} ({status.get('status')})"
                })
                return status

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
                if not self.device.is_connected:
                    await broadcast({"type": "chat_message", "role": "system", "content": "Hardware Notice: Pin actuation rejected (No Arduino connected)."})
                    return {"error": "Hardware Actuation Failed: No Arduino board is physically connected to the computer.", "connected": False}

                pin = args.get("pin", "D2")
                state = int(args.get("state", 0))
                success = await self.device.set_pin_async(pin, state)
                state_str = "HIGH (ON)" if state else "LOW (OFF)"
                await broadcast({"type": "chat_message", "role": "system", "content": f"Hardware Actuation: Pin {pin} -> {state_str}"})
                await broadcast({"type": "device_update", "devices": [self.device.get_status_info()]})
                return {"status": "success" if success else "failed", "pin": str(pin), "state": state_str}

            elif name == "set_all_arduino_pins":
                if not self.device.is_connected:
                    await broadcast({"type": "chat_message", "role": "system", "content": "Hardware Notice: Actuation rejected (No Arduino connected)."})
                    return {"error": "Hardware Actuation Failed: No Arduino board is physically connected to the computer.", "connected": False}

                state = int(args.get("state", 0))
                success = await self.device.set_all_pins_async(state)
                state_str = "HIGH (ON)" if state else "LOW (OFF)"
                await broadcast({"type": "chat_message", "role": "system", "content": f"Hardware Actuation: All pins -> {state_str}"})
                await broadcast({"type": "device_update", "devices": [self.device.get_status_info()]})
                return {"status": "success" if success else "failed", "pins": "D2-D13, A0-A5", "state": state_str}

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

            elif name == "build_and_flash_sketch":
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

                await broadcast({"type": "chat_message", "role": "system", "content": f"Compiler: Created '{sketch_name}.ino'. Building for {fqbn}..."})

                # Locate arduino-cli
                bin_dir = os.path.join(cortex_dir, "bin")
                arduino_cli = os.path.join(bin_dir, "arduino-cli.exe")
                if not os.path.exists(arduino_cli):
                    arduino_cli = "arduino-cli"

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

                # Compile with auto-library installation retry loop
                compile_success = False
                compile_stdout = ""
                compile_stderr = ""

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
                    await broadcast({"type": "chat_message", "role": "system", "content": f"Compiler Error:\n{compile_stderr or compile_stdout}"})
                    await broadcast({"type": "facial_expression", "mood": "skeptical", "eye_shape": "squint", "glow_color": "#ef4444"})
                    return {"status": "compile_failed", "stdout": compile_stdout, "stderr": compile_stderr}

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
                    await broadcast({"type": "chat_message", "role": "system", "content": f"Hardware Flash Error: {upload_stderr or upload_stdout}"})
                    await broadcast({"type": "facial_expression", "mood": "alert", "eye_shape": "wide", "glow_color": "#ef4444"})
                    return {
                        "status": "upload_failed",
                        "port": target_port,
                        "error": upload_stderr or upload_stdout
                    }

            elif name == "compile_and_upload_sketch":
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

                await broadcast({"type": "chat_message", "role": "system", "content": f"Compiler: Building sketch '{os.path.basename(sketch_path)}' for {fqbn}..."})

                # Compile with auto-library installation retry loop
                compile_success = False
                compile_stdout = ""
                compile_stderr = ""

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

                    # Check for missing library header (e.g. fatal error: RTClib.h: No such file or directory)
                    combined_err = f"{compile_stdout}\n{compile_stderr}"
                    lib_match = re.search(r'fatal error:\s*([a-zA-Z0-9_\-]+)\.h:\s*No such file', combined_err, re.IGNORECASE)
                    if lib_match:
                        missing_lib = lib_match.group(1)
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
                    await broadcast({"type": "chat_message", "role": "system", "content": f"Compiler Error:\n{compile_stderr or compile_stdout}"})
                    await broadcast({"type": "facial_expression", "mood": "skeptical", "eye_shape": "squint", "glow_color": "#ef4444"})
                    return {"status": "compile_failed", "stdout": compile_stdout, "stderr": compile_stderr}

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
                    # Always resume serial worker
                    await asyncio.sleep(0.5)
                    await self.device.resume_serial()

                if upload_success:
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
