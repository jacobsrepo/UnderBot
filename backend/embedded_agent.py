import os
import sys
import time
import json
import queue
import threading
import subprocess
import shutil
import tempfile
import urllib.request
import zipfile
import io
from typing import Dict, List, Optional, Any, Callable, Tuple

try:
    import serial
    import serial.tools.list_ports
except ImportError:
    serial = None

try:
    import esptool
except ImportError:
    esptool = None

class EmbeddedAgent:
    """
    Deterministic Embedded Hardware & Reflection Engine for Contender.
    Provides structured JSON hardware discovery, automated compilation-error reflection loops,
    esptool flashing, and a thread-safe non-blocking serial telemetry queue.
    """

    KNOWN_CHIP_SIGNATURES = {
        (0x2341, None): "Arduino Official Board",
        (0x1A86, 0x7523): "Arduino Nano / Uno (CH340 USB)",
        (0x1A86, 0x55D4): "Arduino / CH343 USB-Serial",
        (0x10C4, 0xEA60): "ESP32 / NodeMCU (CP2102 USB)",
        (0x0403, 0x6001): "Arduino Nano (FT232R USB UART)",
        (0x2E8A, 0x0003): "Raspberry Pi Pico (RP2040)",
        (0x303A, None): "Espressif Native USB Device"
    }

    def __init__(self):
        self.active_serial: Optional[serial.Serial] = None
        self.active_port: Optional[str] = None
        self.baudrate: int = 115200
        self.is_monitoring: bool = False
        self.serial_listeners: List[Callable[[str], None]] = []
        self.telemetry_queue: queue.Queue = queue.Queue(maxsize=1000)
        self.monitor_thread: Optional[threading.Thread] = None

        self.bin_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "bin")
        self.arduino_cli_path = os.path.join(self.bin_dir, "arduino-cli.exe")
        self._ensure_arduino_cli()
        
        threading.Thread(target=self.auto_connect_default_port, daemon=True).start()

    def _ensure_arduino_cli(self):
        os.makedirs(self.bin_dir, exist_ok=True)
        if not os.path.exists(self.arduino_cli_path):
            try:
                print("[EmbeddedAgent] Fetching standalone arduino-cli...")
                url = "https://downloads.arduino.cc/arduino-cli/arduino-cli_latest_Windows_64bit.zip"
                req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
                with urllib.request.urlopen(req, timeout=25) as resp:
                    zip_data = resp.read()
                with zipfile.ZipFile(io.BytesIO(zip_data)) as z:
                    z.extract("arduino-cli.exe", self.bin_dir)
                print("[EmbeddedAgent] arduino-cli installed in bin/.")
            except Exception as e:
                print(f"[EmbeddedAgent] Notice: Could not download arduino-cli ({e})")

    # ==================== STRUCTURED CLI AUTO-DISCOVERY ====================

    def detect_boards(self) -> List[Dict[str, Any]]:
        """
        Executes 'arduino-cli board list --format json' and merges with pyserial comports
        to return standardized, structured board dictionaries.
        """
        devices = []
        cli_detected_map = {}

        # 1. Query structured arduino-cli JSON
        if os.path.exists(self.arduino_cli_path):
            try:
                res = subprocess.run(
                    [self.arduino_cli_path, "board", "list", "--format", "json"],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                if res.returncode == 0 and res.stdout.strip():
                    cli_json = json.loads(res.stdout)
                    for item in cli_json.get("detected_ports", []):
                        p_info = item.get("port", {})
                        addr = p_info.get("address")
                        boards = item.get("boards", [])
                        board_name = boards[0].get("name") if boards else None
                        fqbn = boards[0].get("fqbn") if boards else None
                        if addr:
                            cli_detected_map[addr] = {
                                "board_name": board_name,
                                "fqbn": fqbn,
                                "protocol": p_info.get("protocol", "serial")
                            }
            except Exception as e:
                print(f"[EmbeddedAgent] arduino-cli list error: {e}")

        # 2. Query pyserial comports
        if serial:
            try:
                for p in serial.tools.list_ports.comports():
                    port_name = p.device
                    board_type = "Generic Serial Port"
                    fqbn = "arduino:avr:uno"
                    vid = p.vid
                    pid = p.pid
                    is_usb = vid is not None

                    if vid:
                        for (k_vid, k_pid), name in self.KNOWN_CHIP_SIGNATURES.items():
                            if k_vid == vid and (k_pid is None or k_pid == pid):
                                board_type = name
                                break

                    desc = p.description or ""
                    if "nano" in desc.lower():
                        board_type = f"Arduino Nano ({desc})"
                        fqbn = "arduino:avr:nano:cpu=atmega328"
                    elif "mega" in desc.lower():
                        board_type = f"Arduino Mega ({desc})"
                        fqbn = "arduino:avr:mega"
                    elif "arduino" in desc.lower():
                        board_type = f"Arduino ({desc})"
                        fqbn = "arduino:avr:uno"
                    elif "ch340" in desc.lower() or "cp210" in desc.lower() or "ft232" in desc.lower():
                        board_type = f"Arduino Nano / ESP32 ({desc})"
                        fqbn = "arduino:avr:nano:cpu=atmega328old"
                    elif port_name == "COM1" and not is_usb:
                        board_type = "Motherboard Serial Header (COM1)"

                    # Merge with CLI structured discovery if available
                    if port_name in cli_detected_map:
                        cli_entry = cli_detected_map[port_name]
                        if cli_entry.get("board_name"):
                            board_type = cli_entry["board_name"]
                        if cli_entry.get("fqbn"):
                            fqbn = cli_entry["fqbn"]

                    devices.append({
                        "port": port_name,
                        "description": p.description,
                        "hwid": p.hwid,
                        "vid": p.vid,
                        "pid": p.pid,
                        "is_usb": is_usb,
                        "board_type": board_type,
                        "fqbn": fqbn,
                        "is_active": (self.active_port == port_name and self.is_monitoring)
                    })
            except Exception as e:
                print(f"[EmbeddedAgent] Port scan notice: {e}")

        return devices

    def scan_ports(self) -> List[Dict[str, Any]]:
        return self.detect_boards()

    def auto_detect_target_port(self, board_hint: str = "auto") -> Optional[Dict[str, Any]]:
        ports = self.detect_boards()
        if not ports:
            return None

        if board_hint and board_hint != "auto":
            for p in ports:
                if board_hint.lower() in p["board_type"].lower():
                    return p

        for p in ports:
            if p.get("is_usb") and ("arduino" in p["board_type"].lower() or "ch340" in p["board_type"].lower() or "esp" in p["board_type"].lower() or "cp210" in p["board_type"].lower() or "ft232" in p["board_type"].lower()):
                return p

        for p in ports:
            if p.get("is_usb"):
                return p

        return None

    def auto_connect_default_port(self):
        time.sleep(1.0)
        target = self.auto_detect_target_port()
        if target and not self.is_monitoring:
            print(f"[EmbeddedAgent] Auto-connecting to {target['port']} ({target['board_type']})...")
            self.connect_serial(target["port"], baudrate=115200)

    # ==================== DETERMINISTIC COMPILATION & REFLECTION LOOP ====================

    def compile_and_flash(self, fqbn: str, port: str, sketch_path: str) -> Dict[str, Any]:
        """
        Executes: arduino-cli compile --fqbn <fqbn> --upload -p <port> <sketch_path> --format json
        Returns structured dictionary with parsed diagnostics.
        """
        if not os.path.exists(self.arduino_cli_path):
            return {"success": False, "error": "arduino-cli toolchain not found in bin/."}

        # Step 1: Compile
        comp_cmd = [self.arduino_cli_path, "compile", "--fqbn", fqbn, "--format", "json", sketch_path]
        try:
            comp_res = subprocess.run(comp_cmd, capture_output=True, text=True, timeout=25)
            comp_stdout = comp_res.stdout.strip()
            comp_stderr = comp_res.stderr.strip()

            comp_diag = []
            if comp_stdout:
                try:
                    parsed = json.loads(comp_stdout)
                    if not parsed.get("success", True):
                        comp_diag = parsed.get("compiler_out", {}).get("diagnostics", [])
                except Exception:
                    pass

            if comp_res.returncode != 0:
                diag_messages = [d.get("message", "") for d in comp_diag if d.get("severity") == "ERROR"]
                error_summary = "\n".join(diag_messages) if diag_messages else (comp_stderr or comp_stdout)
                return {
                    "success": False,
                    "stage": "compile",
                    "diagnostics": comp_diag,
                    "error": error_summary,
                    "stdout": comp_stdout,
                    "stderr": comp_stderr
                }
        except subprocess.TimeoutExpired:
            return {"success": False, "stage": "compile", "error": "Compilation timed out after 25s."}

        # Step 2: Upload
        upload_cmd = [self.arduino_cli_path, "upload", "-p", port, "--fqbn", fqbn, sketch_path]
        try:
            upload_res = subprocess.run(upload_cmd, capture_output=True, text=True, timeout=18)
            if upload_res.returncode != 0:
                return {
                    "success": False,
                    "stage": "upload",
                    "error": upload_res.stderr.strip() or upload_res.stdout.strip(),
                    "stdout": upload_res.stdout,
                    "stderr": upload_res.stderr
                }
        except subprocess.TimeoutExpired:
            return {"success": False, "stage": "upload", "error": f"Upload to {port} timed out."}

        return {
            "success": True,
            "stage": "complete",
            "port": port,
            "fqbn": fqbn,
            "message": f"Successfully compiled and uploaded to {port}."
        }

    def auto_compile_flash_with_reflection(
        self,
        prompt: str,
        board_hint: str = "auto",
        max_reflection_retries: int = 2,
        progress_cb: Optional[Callable[[str], None]] = None,
        code_reflector_cb: Optional[Callable[[str, str, str], str]] = None
    ) -> Dict[str, Any]:
        """
        Executes autonomous firmware generation, compilation, and automated self-repair reflection.
        If compilation fails, compiler stderr is fed into code_reflector_cb to auto-correct and re-flash.
        """
        def update_progress(msg: str):
            print(f"[EmbeddedAgent] {msg}")
            if progress_cb:
                try:
                    progress_cb(msg)
                except Exception:
                    pass

        update_progress("Scanning system COM ports for USB boards...")
        device = self.auto_detect_target_port(board_hint)
        if not device:
            return {
                "success": False,
                "error": "No USB Arduino or ESP microcontroller detected on system ports. Please ensure your Arduino USB cable is plugged into the computer."
            }

        port_name = device["port"]
        board_label = device.get("board_type", "Arduino Nano")
        fqbn = device.get("fqbn", "arduino:avr:nano:cpu=atmega328")

        if board_hint == "nano" or "nano" in prompt.lower():
            fqbn = "arduino:avr:nano:cpu=atmega328"
            board_label = "Arduino Nano"
        elif board_hint == "uno" or "uno" in prompt.lower():
            fqbn = "arduino:avr:uno"
            board_label = "Arduino Uno"
        elif board_hint == "mega" or "mega" in prompt.lower():
            fqbn = "arduino:avr:mega"
            board_label = "Arduino Mega"

        # Disconnect active serial monitor before upload
        if self.active_port == port_name and self.is_monitoring:
            self.disconnect_serial()

        update_progress(f"Generating optimized C++ sketch for {board_label}...")
        gen_result = self.generate_microcontroller_code(prompt, board="esp32" if "esp" in board_label.lower() else "uno")
        sketch_code = gen_result["code"]

        with tempfile.TemporaryDirectory() as tmpdir:
            sketch_folder = os.path.join(tmpdir, "contender_firmware")
            os.makedirs(sketch_folder, exist_ok=True)
            sketch_file = os.path.join(sketch_folder, "contender_firmware.ino")

            # Reflection Loop
            for attempt in range(max_reflection_retries + 1):
                with open(sketch_file, "w", encoding="utf-8") as f:
                    f.write(sketch_code)

                update_progress(f"Compiling firmware for {board_label} (Attempt {attempt + 1})...")
                flash_res = self.compile_and_flash(fqbn, port_name, sketch_folder)

                if flash_res["success"]:
                    update_progress(f"Firmware active on {port_name}! Reconnecting serial telemetry...")
                    time.sleep(0.5)
                    self.connect_serial(port_name, baudrate=115200)
                    return {
                        "success": True,
                        "port": port_name,
                        "board": board_label,
                        "reflection_attempts": attempt,
                        "message": f"Successfully compiled and uploaded firmware to {board_label} on {port_name}."
                    }

                # If compilation failed and reflector callback exists, self-repair code!
                if flash_res.get("stage") == "compile" and attempt < max_reflection_retries and code_reflector_cb:
                    err_text = flash_res.get("error", "Unknown compilation error")
                    update_progress(f"[Reflection Loop] Compiler error detected. Auto-correcting sketch...\nError: {err_text[:120]}")
                    sketch_code = code_reflector_cb(prompt, sketch_code, err_text)
                    continue
                else:
                    # If upload failed on Nano with new bootloader, retry with old bootloader (CH340 clone support)
                    if "nano" in fqbn and "old" not in fqbn:
                        update_progress("Retrying Arduino Nano upload with Old Bootloader (CH340)...")
                        fqbn = "arduino:avr:nano:cpu=atmega328old"
                        flash_res = self.compile_and_flash(fqbn, port_name, sketch_folder)
                        if flash_res["success"]:
                            update_progress(f"Upload complete on {port_name}!")
                            time.sleep(0.5)
                            self.connect_serial(port_name, baudrate=115200)
                            return {
                                "success": True,
                                "port": port_name,
                                "board": board_label,
                                "message": f"Successfully uploaded firmware to {board_label} on {port_name}."
                            }

                    return {
                        "success": False,
                        "error": flash_res.get("error", "Upload failed.")
                    }

        return {"success": False, "error": "Operation terminated."}

    def auto_compile_and_flash_sketch(self, prompt: str, board_hint: str = "auto", progress_cb: Optional[Callable[[str], None]] = None) -> Dict[str, Any]:
        return self.auto_compile_flash_with_reflection(prompt, board_hint=board_hint, progress_cb=progress_cb)

    # ==================== CODE GENERATION ====================

    def generate_microcontroller_code(self, prompt: str, board: str = "uno") -> Dict[str, Any]:
        lower = prompt.lower()
        pin = 2 if "esp" in board.lower() else 13

        if "blink" in lower or "led" in lower or "13" in lower:
            code = f"""// Contender Autonomous Firmware: LED Controller
#define LED_PIN {pin}

void setup() {{
  Serial.begin(115200);
  pinMode(LED_PIN, OUTPUT);
  Serial.println("[Contender] Microcontroller online. LED Blink sequence initialized.");
}}

void loop() {{
  digitalWrite(LED_PIN, HIGH);
  Serial.println("[Contender] LED ON");
  delay(1000);
  digitalWrite(LED_PIN, LOW);
  Serial.println("[Contender] LED OFF");
  delay(1000);
}}
"""
        elif "relay" in lower or "motor" in lower:
            code = """// Contender Autonomous Firmware: Relay / Motor Actuator
#define RELAY_PIN 7

void setup() {
  Serial.begin(115200);
  pinMode(RELAY_PIN, OUTPUT);
  digitalWrite(RELAY_PIN, LOW);
  Serial.println("[Contender] Relay Actuator Ready. Awaiting commands (ON/OFF).");
}

void loop() {
  if (Serial.available() > 0) {
    String cmd = Serial.readStringUntil('\\n');
    cmd.trim();
    if (cmd.equalsIgnoreCase("ON")) {
      digitalWrite(RELAY_PIN, HIGH);
      Serial.println("[Contender] RELAY ACTIVATED");
    } else if (cmd.equalsIgnoreCase("OFF")) {
      digitalWrite(RELAY_PIN, LOW);
      Serial.println("[Contender] RELAY DEACTIVATED");
    }
  }
}
"""
        elif "servo" in lower:
            code = """// Contender Autonomous Firmware: Servo Controller
#include <Servo.h>

Servo myServo;
#define SERVO_PIN 9

void setup() {
  Serial.begin(115200);
  myServo.attach(SERVO_PIN);
  Serial.println("[Contender] Servo Controller Online.");
}

void loop() {
  if (Serial.available() > 0) {
    int angle = Serial.parseInt();
    if (angle >= 0 && angle <= 180) {
      myServo.write(angle);
      Serial.print("[Contender] Angle set to: ");
      Serial.println(angle);
    }
  }
}
"""
        else:
            code = f"""// Contender Autonomous Firmware for {board.upper()}
void setup() {{
  Serial.begin(115200);
  Serial.println("[Contender] Microcontroller online and awaiting instructions.");
}}

void loop() {{
  if (Serial.available()) {{
    String cmd = Serial.readStringUntil('\\n');
    cmd.trim();
    Serial.print("[Echo] ");
    Serial.println(cmd);
  }}
  delay(100);
}}
"""
        return {
            "success": True,
            "board": board,
            "code": code,
            "filename": f"contender_{board}_sketch.ino"
        }

    # ==================== NON-BLOCKING QUEUE-BASED SERIAL MONITOR ====================

    def connect_serial(self, port: str, baudrate: int = 115200) -> Dict[str, Any]:
        if not serial:
            return {"success": False, "error": "pyserial not available"}

        self.disconnect_serial()

        try:
            self.active_serial = serial.Serial(port=port, baudrate=baudrate, timeout=0.1)
            self.active_port = port
            self.baudrate = baudrate
            self.is_monitoring = True

            self.monitor_thread = threading.Thread(target=self._serial_queue_worker, daemon=True)
            self.monitor_thread.start()

            for cb in self.serial_listeners:
                try:
                    cb(f"[Contender] Connected to {port} @ {baudrate} baud.")
                except Exception:
                    pass

            return {
                "success": True,
                "port": port,
                "baudrate": baudrate,
                "message": f"Connected to {port} at {baudrate} baud."
            }
        except Exception as e:
            return {"success": False, "port": port, "error": str(e)}

    def disconnect_serial(self) -> Dict[str, Any]:
        self.is_monitoring = False
        port_name = self.active_port
        if self.active_serial and self.active_serial.is_open:
            try:
                self.active_serial.close()
            except Exception:
                pass
        self.active_serial = None
        self.active_port = None
        return {"success": True, "message": f"Disconnected from {port_name}."}

    def send_serial_data(self, data: str) -> Dict[str, Any]:
        if not self.active_serial or not self.active_serial.is_open:
            return {"success": False, "error": "No active serial connection"}

        try:
            payload = (data.strip() + "\n").encode("utf-8")
            self.active_serial.write(payload)
            return {"success": True, "sent": data}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def add_serial_listener(self, callback: Callable[[str], None]):
        if callback not in self.serial_listeners:
            self.serial_listeners.append(callback)

    def remove_serial_listener(self, callback: Callable[[str], None]):
        if callback in self.serial_listeners:
            self.serial_listeners.remove(callback)

    def _serial_queue_worker(self):
        """Thread-safe non-blocking serial reader worker."""
        while self.is_monitoring and self.active_serial and self.active_serial.is_open:
            try:
                if self.active_serial.in_waiting:
                    line = self.active_serial.readline().decode("utf-8", errors="ignore").strip()
                    if line:
                        for cb in self.serial_listeners:
                            try:
                                cb(line)
                            except Exception:
                                pass
                else:
                    time.sleep(0.015)
            except Exception:
                break
        self.is_monitoring = False
