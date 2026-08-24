import os
import sys
import time
import json
import threading
import subprocess
import shutil
import tempfile
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
    Embedded Microcontroller Engineering Engine for Contender.
    Provides hardware port discovery, Arduino/ESP firmware generation,
    esptool flashing, and live serial telemetry.
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

    # ==================== PORT DISCOVERY ====================

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
                vid = p.vid
                pid = p.pid

                if vid:
                    for (k_vid, k_pid), name in self.KNOWN_CHIP_SIGNATURES.items():
                        if k_vid == vid and (k_pid is None or k_pid == pid):
                            board_type = name
                            break

                desc = p.description or ""
                if "arduino" in desc.lower():
                    board_type = f"Arduino Device ({desc})"
                elif "ch340" in desc.lower() or "cp210" in desc.lower():
                    board_type = f"ESP32 / Arduino ({desc})"

                devices.append({
                    "port": p.device,
                    "description": p.description,
                    "hwid": p.hwid,
                    "vid": p.vid,
                    "pid": p.pid,
                    "board_type": board_type,
                    "is_active": (self.active_port == p.device and self.is_monitoring)
                })
        except Exception as e:
            print(f"[EmbeddedAgent] Port scan error: {e}")

        return devices

    # ==================== ESP32 / ESP8266 CHIP INSPECTION ====================

    def inspect_esp_chip(self, port: str) -> Dict[str, Any]:
        """
        Uses esptool to query chip details (MAC, Flash Size, Features).
        """
        try:
            result = subprocess.run(
                ["esptool.py", "--port", port, "chip_id"],
                capture_output=True,
                text=True,
                timeout=8
            )
            return {
                "success": result.returncode == 0,
                "port": port,
                "output": result.stdout.strip() or result.stderr.strip()
            }
        except Exception as e:
            return {"success": False, "port": port, "error": str(e)}

    def flash_esp_firmware(self, port: str, binary_path: str, offset: str = "0x10000") -> Dict[str, Any]:
        """
        Flashes compiled binary into ESP32 / ESP8266 via esptool.
        """
        if not os.path.isfile(binary_path):
            return {"success": False, "error": f"Binary file not found: {binary_path}"}

        # Release serial port if currently open
        if self.active_port == port and self.is_monitoring:
            self.disconnect_serial()

        try:
            cmd = ["esptool.py", "--port", port, "write_flash", offset, binary_path]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            return {
                "success": result.returncode == 0,
                "port": port,
                "stdout": result.stdout.strip(),
                "stderr": result.stderr.strip()
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    # ==================== CODE GENERATION & COMPILATION ====================

    def generate_microcontroller_code(self, prompt: str, board: str = "esp32") -> Dict[str, Any]:
        """
        Generates standard, ready-to-compile Arduino C++ or MicroPython sketch.
        """
        lower = prompt.lower()
        
        # Smart template generation
        if "blink" in lower or "led" in lower:
            pin = 2 if "esp" in board.lower() else 13
            code = f"""// Contender Generated Firmware: LED Blink
// Board: {board.upper()}
#define LED_PIN {pin}

void setup() {{
  Serial.begin(115200);
  pinMode(LED_PIN, OUTPUT);
  Serial.println("[Contender] System initialized. Starting blink cycle.");
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
        elif "servo" in lower:
            code = f"""// Contender Generated Firmware: Servo Control
#include <Servo.h>

Servo myServo;
#define SERVO_PIN 9

void setup() {{
  Serial.begin(115200);
  myServo.attach(SERVO_PIN);
  Serial.println("[Contender] Servo Controller Ready.");
}}

void loop() {{
  if (Serial.available() > 0) {{
    int angle = Serial.parseInt();
    if (angle >= 0 && angle <= 180) {{
      myServo.write(angle);
      Serial.print("[Contender] Angle set to: ");
      Serial.println(angle);
    }}
  }}
}}
"""
        elif "wifi" in lower and "esp" in board.lower():
            code = """// Contender Generated Firmware: ESP32 Wi-Fi Telemetry
#include <WiFi.h>

const char* ssid = "YOUR_WIFI_SSID";
const char* password = "YOUR_WIFI_PASS";

void setup() {
  Serial.begin(115200);
  WiFi.begin(ssid, password);
  Serial.print("[Contender] Connecting to Wi-Fi");
  
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }
  Serial.println("\\n[Contender] Connected! IP Address: ");
  Serial.println(WiFi.localIP());
}

void loop() {
  Serial.print("[Telemetry] RSSI: ");
  Serial.println(WiFi.RSSI());
  delay(3000);
}
"""
        else:
            code = f"""// Contender Generated Firmware for {board.upper()}
void setup() {{
  Serial.begin(115200);
  Serial.println("[Contender] Microcontroller online and awaiting commands.");
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

    # ==================== LIVE SERIAL TERMINAL ====================

    def connect_serial(self, port: str, baudrate: int = 115200) -> Dict[str, Any]:
        """
        Connects to a serial port for real-time telemetry and command sending.
        """
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

    def remove_serial_listener(self, callback: Callable[[str], None]):
        if callback in self.serial_listeners:
            self.serial_listeners.remove(callback)

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
