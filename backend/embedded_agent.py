import os
import sys
import time
import json
import threading
import subprocess
import shutil
import tempfile
import urllib.request
import zipfile
import io
from typing import Dict, List, Optional, Any, Callable

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
    Embedded Hardware & Microcontroller Engine for Contender.
    Provides autonomous COM port discovery, Arduino compilation and uploading,
    ESP32 flashing, and live interactive serial telemetry.
    """

    KNOWN_CHIP_SIGNATURES = {
        (0x2341, None): "Arduino Official Device",
        (0x1A86, 0x7523): "Arduino / ESP (CH340 USB-Serial)",
        (0x10C4, 0xEA60): "ESP32 / NodeMCU (CP2102 USB-UART)",
        (0x0403, 0x6001): "FTDI USB-Serial Device",
        (0x2E8A, 0x0003): "Raspberry Pi Pico (RP2040)",
        (0x303A, None): "Espressif Native USB Device"
    }

    def __init__(self):
        self.active_serial: Optional[serial.Serial] = None
        self.active_port: Optional[str] = None
        self.baudrate: int = 115200
        self.is_monitoring: bool = False
        self.serial_listeners: List[Callable[[str], None]] = []
        self.monitor_thread: Optional[threading.Thread] = None

        self.bin_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "bin")
        self.arduino_cli_path = os.path.join(self.bin_dir, "arduino-cli.exe")
        self._ensure_arduino_cli()

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

    # ==================== AUTONOMOUS PORT DISCOVERY ====================

    def scan_ports(self) -> List[Dict[str, Any]]:
        """
        Scans all system COM ports and identifies connected microcontrollers.
        """
        if not serial:
            return []

        devices = []
        try:
            for p in serial.tools.list_ports.comports():
                board_type = "Generic Serial Device"
                fqbn = "arduino:avr:uno"
                vid = p.vid
                pid = p.pid

                if vid:
                    for (k_vid, k_pid), name in self.KNOWN_CHIP_SIGNATURES.items():
                        if k_vid == vid and (k_pid is None or k_pid == pid):
                            board_type = name
                            break

                desc = p.description or ""
                if "arduino" in desc.lower():
                    board_type = f"Arduino ({desc})"
                    if "mega" in desc.lower():
                        fqbn = "arduino:avr:mega"
                    elif "nano" in desc.lower():
                        fqbn = "arduino:avr:nano"
                    else:
                        fqbn = "arduino:avr:uno"
                elif "ch340" in desc.lower() or "cp210" in desc.lower():
                    board_type = f"Arduino / ESP32 ({desc})"

                devices.append({
                    "port": p.device,
                    "description": p.description,
                    "hwid": p.hwid,
                    "vid": p.vid,
                    "pid": p.pid,
                    "board_type": board_type,
                    "fqbn": fqbn,
                    "is_active": (self.active_port == p.device and self.is_monitoring)
                })
        except Exception as e:
            print(f"[EmbeddedAgent] Port scan notice: {e}")

        return devices

    def auto_detect_target_port(self) -> Optional[Dict[str, Any]]:
        ports = self.scan_ports()
        if not ports:
            return None
        # Prefer detected microcontrollers over generic COM1
        for p in ports:
            if "arduino" in p["board_type"].lower() or "ch340" in p["board_type"].lower() or "esp" in p["board_type"].lower() or "cp210" in p["board_type"].lower():
                return p
        return ports[0]

    # ==================== AUTONOMOUS COMPILE & FLASH PIPELINE ====================

    def auto_compile_and_flash_sketch(self, prompt: str, target_board: str = "auto") -> Dict[str, Any]:
        """
        AUTONOMOUS ACTION:
        1. Auto-detects connected Arduino or ESP device.
        2. Writes custom C++/MicroPython firmware.
        3. Compiles firmware with arduino-cli.
        4. Flashes firmware directly to the target COM port.
        """
        device = self.auto_detect_target_port()
        if not device:
            return {
                "success": False,
                "error": "No microcontroller or USB serial device detected on system COM ports. Please connect your board."
            }

        port_name = device["port"]
        fqbn = device.get("fqbn", "arduino:avr:uno")
        board_label = device.get("board_type", "Arduino Uno")

        # Disconnect active serial monitor before upload
        if self.active_port == port_name and self.is_monitoring:
            self.disconnect_serial()

        # Generate firmware
        gen_result = self.generate_microcontroller_code(prompt, board="esp32" if "esp" in board_label.lower() else "uno")
        sketch_code = gen_result["code"]

        with tempfile.TemporaryDirectory() as tmpdir:
            sketch_folder = os.path.join(tmpdir, "contender_firmware")
            os.makedirs(sketch_folder, exist_ok=True)
            sketch_file = os.path.join(sketch_folder, "contender_firmware.ino")

            with open(sketch_file, "w", encoding="utf-8") as f:
                f.write(sketch_code)

            if not os.path.exists(self.arduino_cli_path):
                return {
                    "success": False,
                    "error": "arduino-cli toolchain is not ready in bin/."
                }

            # 1. Compile Sketch
            print(f"[EmbeddedAgent] Compiling firmware for {fqbn}...")
            comp = subprocess.run(
                [self.arduino_cli_path, "compile", "--fqbn", fqbn, sketch_folder],
                capture_output=True,
                text=True,
                timeout=20
            )

            if comp.returncode != 0:
                return {
                    "success": False,
                    "stage": "compile",
                    "error": f"Compilation failed: {comp.stderr.strip() or comp.stdout.strip()}"
                }

            # 2. Upload to Device
            print(f"[EmbeddedAgent] Uploading firmware to {port_name} ({fqbn})...")
            upload = subprocess.run(
                [self.arduino_cli_path, "upload", "-p", port_name, "--fqbn", fqbn, sketch_folder],
                capture_output=True,
                text=True,
                timeout=25
            )

            if upload.returncode != 0:
                return {
                    "success": False,
                    "stage": "upload",
                    "error": f"Upload to {port_name} failed: {upload.stderr.strip() or upload.stdout.strip()}"
                }

        return {
            "success": True,
            "port": port_name,
            "board": board_label,
            "message": f"Successfully compiled and uploaded firmware to {board_label} on {port_name}."
        }

    # ==================== CODE GENERATION ====================

    def generate_microcontroller_code(self, prompt: str, board: str = "uno") -> Dict[str, Any]:
        lower = prompt.lower()
        pin = 2 if "esp" in board.lower() else 13

        if "blink" in lower or "led" in lower:
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

    # ==================== SERIAL TERMINAL ====================

    def connect_serial(self, port: str, baudrate: int = 115200) -> Dict[str, Any]:
        if not serial:
            return {"success": False, "error": "pyserial not available"}

        self.disconnect_serial()

        try:
            self.active_serial = serial.Serial(port=port, baudrate=baudrate, timeout=1)
            self.active_port = port
            self.baudrate = baudrate
            self.is_monitoring = True

            self.monitor_thread = threading.Thread(target=self._serial_reader_loop, daemon=True)
            self.monitor_thread.start()

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

    def _serial_reader_loop(self):
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
                    time.sleep(0.02)
            except Exception:
                break
        self.is_monitoring = False
