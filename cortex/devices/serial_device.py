"""
Cortex Real Hardware Serial Bridge
Supports full 16-pin control (D2 to D13 and A0 to A5) on Arduino Nano on COM4.
"""

import time
import threading
from typing import Dict, Any, Optional
import serial
import serial.tools.list_ports


class SerialDevice:
    START_BYTE = 0x02
    END_BYTE = 0x03
    CMD_SET_PIN = 0x01
    CMD_READ_PIN = 0x02
    CMD_SET_ALL = 0x04
    CMD_PING = 0x05

    def __init__(self, port: Optional[str] = None, baudrate: int = 115200):
        self.requested_port = port
        self.baudrate = baudrate
        self.port_name: Optional[str] = None
        self.serial: Optional[serial.Serial] = None
        self.is_connected = False
        self.lock = threading.Lock()

        # All controllable digital & analog pins (2 to 19: D2-D13 and A0-A5)
        self.pin_states: Dict[int, int] = {p: 0 for p in range(2, 20)}

        self.device_name = "Arduino Nano"
        self.device_detail = "Disconnected"

        self._connect()

        self.running = True
        self.watchdog_thread = threading.Thread(target=self._watchdog_loop, daemon=True)
        self.watchdog_thread.start()

    def _find_port(self) -> Optional[str]:
        if self.requested_port:
            return self.requested_port

        ports = list(serial.tools.list_ports.comports())
        for p in ports:
            if "com4" in p.device.lower():
                return p.device
            desc = p.description.lower()
            if "usb serial" in desc or "arduino" in desc or "ftdi" in desc or "ch34" in desc:
                return p.device

        for p in ports:
            if "com1" not in p.device.lower():
                return p.device

        return None

    def _connect(self) -> bool:
        target_port = self._find_port()
        if not target_port:
            self.is_connected = False
            self.device_detail = "No COM port detected (Simulation)"
            return False

        try:
            with self.lock:
                if self.serial and self.serial.is_open:
                    self.serial.close()

                self.serial = serial.Serial(
                    port=target_port,
                    baudrate=self.baudrate,
                    timeout=0.5,
                    write_timeout=0.5
                )
                time.sleep(1.2)
                self.port_name = target_port
                self.is_connected = True
                self.device_detail = f"Online ({target_port} @ {self.baudrate} baud)"
                print(f"[SerialDevice] Connected to {self.device_name} on {target_port}")
                return True
        except Exception as e:
            self.is_connected = False
            self.device_detail = f"Error ({target_port}): {e}"
            return False

    def _watchdog_loop(self):
        while self.running:
            time.sleep(3.0)
            if not self.is_connected or not self.serial or not self.serial.is_open:
                self._connect()

    def set_pin(self, pin: Any, state: int) -> bool:
        """Actuate pin on Arduino (pins 2 to 19 / D2 to A5)."""
        pin_num = self._parse_pin(pin)
        state = 1 if state else 0
        self.pin_states[pin_num] = state

        if self.is_connected and self.serial and self.serial.is_open:
            try:
                with self.lock:
                    ascii_cmd = f"SET {pin_num} {state}\n".encode('ascii')
                    self.serial.write(ascii_cmd)
                    self.serial.flush()
                    return True
            except Exception as e:
                print(f"[SerialDevice] Write error on pin {pin_num}: {e}")
                self.is_connected = False
                return False

        return True

    def set_all_pins(self, state: int) -> bool:
        """Set all digital pins (2 through 19) to HIGH or LOW."""
        state = 1 if state else 0
        for p in range(2, 20):
            self.pin_states[p] = state

        if self.is_connected and self.serial and self.serial.is_open:
            try:
                with self.lock:
                    self.serial.write(f"ALL {state}\n".encode('ascii'))
                    self.serial.flush()
                    return True
            except Exception as e:
                print(f"[SerialDevice] Bulk pin write error: {e}")
                self.is_connected = False
                return False
        return True

    def scan_pins(self) -> bool:
        """Sequentially pulse pins 2 to 19 to discover LED mappings."""
        if self.is_connected and self.serial and self.serial.is_open:
            try:
                with self.lock:
                    self.serial.write(b"SCAN\n")
                    self.serial.flush()
                    return True
            except Exception:
                return False
        return True

    def _parse_pin(self, pin: Any) -> int:
        if isinstance(pin, str):
            pin_str = pin.strip().upper()
            if pin_str.startswith("D"):
                return max(2, min(13, int(pin_str[1:])))
            if pin_str.startswith("A"):
                a_num = int(pin_str[1:])
                return 14 + max(0, min(5, a_num))
            try:
                return max(2, min(19, int(pin_str)))
            except ValueError:
                return 2
        return max(2, min(19, int(pin)))

    def get_pin_state(self, pin: Any) -> int:
        pin_num = self._parse_pin(pin)
        return self.pin_states.get(pin_num, 0)

    def get_all_states(self) -> Dict[int, int]:
        return self.pin_states.copy()

    def get_status_info(self) -> Dict[str, Any]:
        return {
            "name": f"{self.device_name} ({self.port_name or 'COM4'})",
            "status": "online" if self.is_connected else "simulated",
            "detail": self.device_detail,
            "pin_states": self.pin_states
        }

    def close(self):
        self.running = False
        with self.lock:
            if self.serial and self.serial.is_open:
                try:
                    self.serial.close()
                except Exception:
                    pass
        self.is_connected = False
