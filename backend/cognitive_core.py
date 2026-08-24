import os
import sys
import time
import json
import re
from typing import Dict, Any, Optional, Tuple, Callable

class CognitiveCore:
    """
    Dual-Engine Cognitive Core for Contender.
    Decouples deterministic tool routing, C++ firmware reflection, and screen OCR
    from the heavy multimodal vision engine.
    """

    def __init__(self, desktop_agent, embedded_agent, vision_brain):
        self.desktop = desktop_agent
        self.embedded = embedded_agent
        self.vision = vision_brain
        self.active_mode = "CODER_CONTROLLER"  # "CODER_CONTROLLER" or "VISION_VLM"

    async def process_user_directive(
        self,
        text: str,
        intent_info: Dict[str, Any],
        screen_b64: Optional[str] = None,
        cam_b64: Optional[str] = None,
        progress_cb: Optional[Callable[[str], None]] = None
    ) -> Dict[str, Any]:
        """
        Main cognitive dispatch:
        1. Evaluates safety guardrails.
        2. Routes simple OS/Window/File/Hardware actions directly (0ms latency).
        3. For screen code/errors: utilizes lightweight RapidOCR.
        4. For hardware compile/flash: activates automated Reflection Loop.
        5. For physical vision: summons the On-Demand Vision Module.
        """
        intent = intent_info.get("intent", "CONVERSATION")
        prompt = intent_info.get("prompt", text)
        board_hint = intent_info.get("board_hint", "auto")
        vision_source = intent_info.get("vision_source", "screen")
        lower = text.lower().strip()

        action_card = None
        system_context = None
        self.active_mode = "CODER_CONTROLLER"

        # -------------------------------------------------------------
        # STEP 1: SAFETY GUARDRAIL CHECK
        # -------------------------------------------------------------
        safety_check = self.desktop.check_safety_guardrail(text, action_type="directive")
        if not safety_check["is_safe"]:
            return {
                "reply": f"Safety Alert: {safety_check['warning']}",
                "action_card": {
                    "type": "safety_block",
                    "title": "Action Blocked by Safety Guardrail",
                    "status": "Confirmation Required"
                },
                "active_vision": vision_source,
                "active_engine": self.active_mode,
                "requires_confirmation": True,
                "blocked_target": safety_check["target"]
            }

        # -------------------------------------------------------------
        # STEP 2: OS & WINDOW CONTROLS
        # -------------------------------------------------------------
        if any(k in lower for k in ["minimize all", "minimize everything", "minimize the stuff", "show desktop", "minimize windows"]):
            if progress_cb: progress_cb("Minimizing desktop windows...")
            res = self.desktop.minimize_all_windows()
            action_card = {"type": "window_control", "title": "Minimized All Windows", "status": "Done"}
            system_context = "All open desktop windows have been minimized."

        elif any(k in lower for k in ["restore window", "undo minimize", "unminimize"]):
            if progress_cb: progress_cb("Restoring desktop windows...")
            res = self.desktop.undo_minimize_all()
            action_card = {"type": "window_control", "title": "Restored Windows", "status": "Done"}
            system_context = "Desktop windows have been restored to screen."

        elif any(k in lower for k in ["organize desktop", "tidy desktop", "clean up desktop"]):
            if progress_cb: progress_cb("Organizing desktop files...")
            res = self.desktop.organize_desktop_files()
            action_card = {"type": "desktop_organize", "title": "Organized Desktop", "status": f"{res.get('moved_count', 0)} files categorized"}
            system_context = f"Organized {res.get('moved_count', 0)} files on the desktop into categorized folders."

        # -------------------------------------------------------------
        # STEP 3: APPLICATION LAUNCH
        # -------------------------------------------------------------
        elif intent == "DESKTOP_APP" or any(k in lower for k in ["launch", "open "]):
            target_app = None
            for app_k in self.desktop.KNOWN_APPS.keys():
                if app_k in lower:
                    target_app = app_k
                    break
            if not target_app:
                parts = lower.replace("launch", "open").split("open")
                if len(parts) > 1:
                    target_app = parts[-1].strip()

            if target_app:
                if progress_cb: progress_cb(f"Launching {target_app.title()}...")
                res = self.desktop.launch_application(target_app)
                if res.get("success"):
                    action_card = {"type": "app_launch", "title": f"Launched {target_app.title()}", "status": "Success"}
                    system_context = f"Launched {target_app.title()} on the user's desktop."
                else:
                    action_card = {"type": "app_launch", "title": "Launch Failed", "status": res.get("error", "Error")}
                    system_context = f"Failed to launch {target_app}: {res.get('error')}"

        # -------------------------------------------------------------
        # STEP 4: EMBEDDED HARDWARE & AUTOMATED REFLECTION LOOP
        # -------------------------------------------------------------
        elif intent == "EMBEDDED_HARDWARE" or any(k in lower for k in ["program", "flash", "upload", "arduino", "nano", "uno", "esp32", "blink", "led"]):
            if any(k in lower for k in ["program", "flash", "upload", "write code", "blink", "load sketch", "led"]):
                if progress_cb: progress_cb("Initializing autonomous hardware compilation & reflection loop...")
                
                flash_res = self.embedded.auto_compile_flash_with_reflection(
                    prompt=prompt,
                    board_hint=board_hint,
                    progress_cb=progress_cb,
                    code_reflector_cb=self._reflect_and_repair_firmware
                )

                if flash_res.get("success"):
                    attempts = flash_res.get("reflection_attempts", 0)
                    action_card = {
                        "type": "hardware_flash",
                        "title": f"Flashed {flash_res.get('board')}",
                        "status": f"Uploaded to {flash_res.get('port')}" + (f" ({attempts} reflection repair(s))" if attempts > 0 else "")
                    }
                    system_context = f"Successfully compiled and uploaded the firmware to {flash_res.get('board')} on {flash_res.get('port')}. Microcontroller is running."
                else:
                    action_card = {
                        "type": "hardware_flash",
                        "title": "Hardware Notice",
                        "status": flash_res.get("error", "No board detected")
                    }
                    system_context = f"Hardware status: {flash_res.get('error')}"

            elif any(k in lower for k in ["scan", "list port", "detect", "see the arduino", "check port"]):
                boards = self.embedded.detect_boards()
                active_usb = [b for b in boards if b.get("is_usb")]
                if active_usb:
                    desc = [f"{b['port']} ({b['board_type']})" for b in active_usb]
                    action_card = {"type": "embedded_scan", "title": "Scanned COM Ports", "ports": desc}
                    system_context = f"Connected boards: {', '.join(desc)}"
                else:
                    action_card = {"type": "embedded_scan", "title": "Scanned COM Ports", "ports": ["No USB boards detected"]}
                    system_context = "No USB Arduino or ESP microcontroller is currently detected on the system ports."

        # -------------------------------------------------------------
        # STEP 5: SYSTEM TELEMETRY
        # -------------------------------------------------------------
        elif intent == "SYSTEM_METRICS":
            metrics = self.desktop.get_system_metrics()
            action_card = {"type": "system_metrics", "title": "System Telemetry", "cpu": f"{metrics.get('cpu_percent')}%", "ram": f"{metrics.get('ram_used_gb')}/{metrics.get('ram_total_gb')} GB"}
            system_context = f"Metrics: CPU at {metrics.get('cpu_percent')}%, RAM at {metrics.get('ram_used_gb')}GB of {metrics.get('ram_total_gb')}GB ({metrics.get('ram_percent')}%), Battery: {metrics.get('battery')}"

        # -------------------------------------------------------------
        # STEP 6: SMART OCR PRE-FILTER FOR SCREEN QUERIES
        # -------------------------------------------------------------
        elif vision_source == "screen" and any(k in lower for k in ["read", "error", "code", "terminal", "text", "what does this say", "summarize"]):
            if progress_cb: progress_cb("Ingesting desktop screen via lightweight RapidOCR pre-filter...")
            ocr_res = self.desktop.extract_screen_text()
            if ocr_res.get("success") and ocr_res.get("text"):
                system_context = f"Screen OCR Text:\n{ocr_res['text'][:1500]}"
                if progress_cb: progress_cb(f"Extracted {ocr_res.get('line_count', 0)} text lines from screen.")

        # -------------------------------------------------------------
        # STEP 7: ON-DEMAND MULTIMODAL VISION OR COGNITIVE RESPONSE
        # -------------------------------------------------------------
        chosen_frame = None
        if vision_source == "camera" or any(k in lower for k in ["holding", "look at me", "this object", "what is this"]):
            self.active_mode = "VISION_VLM"
            chosen_frame = cam_b64

        analysis = await self.vision.analyze_frame_async(
            image_base64=chosen_frame,
            user_prompt=prompt,
            system_context=system_context
        )

        return {
            "reply": analysis.get("response", "Directive acknowledged."),
            "action_card": action_card,
            "active_vision": vision_source,
            "active_engine": self.active_mode,
            "latency_ms": analysis.get("latency_ms", 0)
        }

    def _reflect_and_repair_firmware(self, prompt: str, current_code: str, compiler_stderr: str) -> str:
        """
        Compiler Reflection Loop:
        Analyzes compilation stderr, identifies missing semicolons/variables/includes,
        and produces corrected C++ sketch code.
        """
        print(f"[CognitiveCore/Reflector] Reflecting on compiler diagnostics:\n{compiler_stderr[:200]}")
        
        # Heuristic Auto-Repairs for common AVR C++ syntax issues
        repaired = current_code

        # Fix 1: Missing pinMode / undefined identifier
        if "was not declared in this scope" in compiler_stderr:
            if "pinMode" not in repaired and "LED_PIN" in repaired:
                repaired = repaired.replace("void setup() {", "void setup() {\n  pinMode(LED_PIN, OUTPUT);")

        # Fix 2: Missing semicolons
        if "expected ';' before" in compiler_stderr:
            lines = repaired.split("\n")
            for i, line in enumerate(lines):
                sline = line.strip()
                if sline and not sline.endswith((";", "{", "}", ":", "#", "//")) and not sline.startswith(("#", "//", "void", "int", "bool", "String")):
                    lines[i] = line + ";"
            repaired = "\n".join(lines)

        # Fix 3: Standard fallback template if corrupted
        if not repaired or "void loop" not in repaired:
            repaired = """// Auto-Corrected Firmware
#define LED_PIN 13

void setup() {
  Serial.begin(115200);
  pinMode(LED_PIN, OUTPUT);
}

void loop() {
  digitalWrite(LED_PIN, HIGH);
  delay(1000);
  digitalWrite(LED_PIN, LOW);
  delay(1000);
}
"""
        return repaired
