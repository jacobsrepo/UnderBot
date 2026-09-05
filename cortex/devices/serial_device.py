import threading
import queue
import time
import asyncio
from typing import Optional, Tuple, Dict, Any, List
import serial
import serial.tools.list_ports


class SerialWorker:
    """Threaded singleton supervisor for persistent Arduino serial communication."""

    def __init__(self, port: str = "COM4", baudrate: int = 115200):
        self.preferred_port = port
        self.port: Optional[str] = None
        self.baudrate = baudrate
        self.tx_queue: queue.Queue = queue.Queue()
        self._running = threading.Event()
        self._thread: Optional[threading.Thread] = None
        self._serial: Optional[serial.Serial] = None
        self._last_log: List[str] = []
        self._pin_states: Dict[str, int] = {}
        self.device_name = "Arduino Nano"

    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._running.set()
        self._thread = threading.Thread(target=self._worker_loop, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._running.clear()
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=2.0)
        if self._serial and self._serial.is_open:
            try:
                self._serial.close()
            except Exception:
                pass
            self._serial = None
        self.port = None

    def _find_board_port(self) -> Optional[str]:
        """Scans COM ports and strictly matches physical USB serial devices (Arduino, CH340, FTDI, CP210x), ignoring legacy motherboard/ACPI ports like COM1."""
        ports = list(serial.tools.list_ports.comports())
        for p in ports:
            hwid = (p.hwid or "").upper()
            desc = (p.description or "").upper()
            device = (p.device or "").upper()

            # Ignore motherboard UART / ACPI / legacy ports
            if "ACPI" in hwid or "PNP0501" in hwid:
                continue
            if desc == "COMMUNICATIONS PORT" and "USB" not in hwid:
                continue

            # Require USB serial identifiers (VID/PID, Arduino, CH340, FTDI, CP210, USB-SERIAL)
            is_usb = any(k in hwid or k in desc for k in ["USB", "VID_", "ARDUINO", "CH340", "FTDI", "CP210", "SILABS", "PROLIFIC"])
            if is_usb:
                # If preferred port matches, prioritize it
                if device == self.preferred_port.upper():
                    return p.device
                return p.device
        return None

    def _connect(self) -> bool:
        target_port = self._find_board_port()
        if not target_port:
            if self._serial:
                try:
                    self._serial.close()
                except Exception:
                    pass
                self._serial = None
            self.port = None
            return False

        try:
            if self._serial and self._serial.is_open:
                self._serial.close()
            self._serial = serial.Serial(target_port, self.baudrate, timeout=1.0)
            self.port = target_port
            time.sleep(1.5)
            # Send initial PING to verify communication
            try:
                self._serial.write(b"PING\n")
                resp = self._serial.readline().decode("utf-8", errors="replace").strip()
                if resp:
                    self._last_log.append(f"[INIT_HANDSHAKE] {resp}")
            except Exception:
                pass
            return True
        except Exception:
            self._serial = None
            self.port = None
            return False

    @property
    def is_connected(self) -> bool:
        return bool(self._serial and self._serial.is_open and self.port is not None)

    @property
    def port_name(self) -> str:
        return self.port or "None (Disconnected)"

    def _worker_loop(self) -> None:
        last_heartbeat = time.time()
        while self._running.is_set():
            if not self._serial or not self._serial.is_open:
                if not self._connect():
                    time.sleep(2.0)
                    continue

            # Heartbeat supervision every 3 seconds
            if time.time() - last_heartbeat > 3.0:
                try:
                    self._serial.write(b"PING\n")
                    resp = self._serial.readline().decode("utf-8", errors="replace").strip()
                    if resp:
                        self._last_log.append(f"[HEARTBEAT] {resp}")
                    last_heartbeat = time.time()
                except Exception:
                    try:
                        self._serial.close()
                    except Exception:
                        pass
                    self._serial = None
                    continue

            try:
                cmd, done_event, container = self.tx_queue.get(timeout=0.2)
                try:
                    self._serial.write(f"{cmd.strip()}\n".encode("utf-8"))
                    response = self._serial.readline().decode("utf-8", errors="replace").strip()
                    container.append(response)
                    if response:
                        self._last_log.append(f">> {cmd.strip()} -> {response}")
                except Exception as e:
                    container.append(f"SERIAL_ERROR: {str(e)}")
                    try:
                        self._serial.close()
                    except Exception:
                        pass
                    self._serial = None
                finally:
                    done_event.set()
                    self.tx_queue.task_done()
            except queue.Empty:
                # Poll incoming stream for any serial output emitted by Arduino
                try:
                    if self._serial and self._serial.in_waiting > 0:
                        line = self._serial.readline().decode("utf-8", errors="replace").strip()
                        if line:
                            self._last_log.append(line)
                            if len(self._last_log) > 200:
                                self._last_log = self._last_log[-100:]
                except Exception:
                    pass

    def send_command(self, cmd: str, timeout: float = 3.0) -> str:
        done = threading.Event()
        result: list = []
        self.tx_queue.put((cmd, done, result))
        if done.wait(timeout=timeout):
            return result[0] if result else "NO_RESPONSE"
        return "COMMAND_TIMEOUT"

    async def send_command_async(self, cmd: str, timeout: float = 3.0) -> str:
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, self.send_command, cmd, timeout)

    async def set_pin_async(self, pin: Any, state: int) -> bool:
        pin_str = str(pin).upper()
        if not pin_str.startswith("D") and not pin_str.startswith("A"):
            pin_str = f"D{pin_str}"
        self._pin_states[pin_str] = state
        resp = await self.send_command_async(f"PIN:{pin_str}:{state}")
        return "SERIAL_ERROR" not in resp and "COMMAND_TIMEOUT" not in resp

    async def set_all_pins_async(self, state: int) -> bool:
        digital_pins = [f"D{i}" for i in range(2, 14)]
        analog_pins = [f"A{i}" for i in range(6)]
        for p in digital_pins + analog_pins:
            self._pin_states[p] = state
        resp = await self.send_command_async(f"ALL_PINS:{state}")
        return "SERIAL_ERROR" not in resp and "COMMAND_TIMEOUT" not in resp

    def get_all_states(self) -> Dict[str, int]:
        return dict(self._pin_states)

    async def check_hardware_status(self) -> Dict[str, Any]:
        connected = self.is_connected
        return {
            "connected": connected,
            "port": self.port or "None (Disconnected)",
            "device": self.device_name if connected else "None",
            "status": "Online and responsive via USB" if connected else "Disconnected (No microcontroller detected)"
        }

    def get_status_info(self) -> Dict[str, Any]:
        return {
            "name": f"{self.device_name} ({self.port})" if self.is_connected else "Microcontroller",
            "status": "online" if self.is_connected else "offline",
            "detail": f"{self.port} @ {self.baudrate} Baud" if self.is_connected else "No USB board detected"
        }

    async def get_serial_output(self, lines: int = 40) -> str:
        if not self._last_log:
            return "[INIT] Serial log initialized. No stream data captured."
        return "\n".join(self._last_log[-lines:])

    def get_serial_output_sync(self, lines: int = 40) -> str:
        if not self._last_log:
            return "[INIT] Serial log initialized. No stream data captured."
        return "\n".join(self._last_log[-lines:])

    async def clear_serial_output(self) -> None:
        self._last_log.clear()

    async def pause_serial(self) -> None:
        pass

    async def resume_serial(self) -> None:
        pass

    async def set_baudrate(self, baud: int) -> None:
        self.baudrate = baud
        if self._serial and self._serial.is_open:
            try:
                self._serial.baudrate = baud
            except Exception:
                pass


# Singleton instance & alias
arduino_serial = SerialWorker()
SerialDevice = SerialWorker
