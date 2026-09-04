"""
Cortex Hardened Arduino Serial Worker Singleton
Dedicated background threading.Thread with thread-safe queue.Queue and asyncio bridge.
Prevents blocking serial calls from stalling the asyncio event loop or WebSocket pipeline.
Features an automatic heartbeat watchdog with exponential backoff for USB unplug/replug resilience.
"""

import time
import threading
import queue
import asyncio
from typing import Dict, Any, Optional, Tuple
from dataclasses import dataclass
import serial
import serial.tools.list_ports


@dataclass
class SerialTask:
    action: str
    data: Dict[str, Any]
    result_future: Optional[asyncio.Future] = None
    completion_event: Optional[threading.Event] = None
    result_holder: Optional[Dict[str, Any]] = None


class SerialWorker(threading.Thread):
    def __init__(self, requested_port: Optional[str] = None, baudrate: int = 115200):
        super().__init__(name="ArduinoSerialWorker", daemon=True)
        self.requested_port = requested_port
        self.baudrate = baudrate
        self.port_name: Optional[str] = None
        self.serial: Optional[serial.Serial] = None
        self.is_connected = False

        self.cmd_queue: queue.Queue = queue.Queue()
        self.running = True

        # Track pins 2 to 19 (D2-D13 and A0-A5)
        self.pin_states: Dict[int, int] = {p: 0 for p in range(2, 20)}
        self.device_name = "Arduino Nano"
        self.device_detail = "Initializing..."

        # Reconnection backoff state
        self.backoff_delay = 1.0
        self.last_heartbeat = time.time()

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

    def _attempt_connect(self) -> bool:
        target_port = self._find_port()
        if not target_port:
            self.is_connected = False
            self.device_detail = "No COM port detected (Standby)"
            return False

        try:
            if self.serial and self.serial.is_open:
                try:
                    self.serial.close()
                except Exception:
                    pass

            self.serial = serial.Serial(
                port=target_port,
                baudrate=self.baudrate,
                timeout=0.3,
                write_timeout=0.3
            )
            time.sleep(1.2)  # Allow Arduino bootloader to settle
            self.port_name = target_port
            self.is_connected = True
            self.device_detail = f"Online ({target_port} @ {self.baudrate} baud)"
            self.backoff_delay = 1.0  # Reset backoff on success
            print(f"[SerialWorker] Connected to {self.device_name} on {target_port}")
            return True
        except Exception as e:
            self.is_connected = False
            self.device_detail = f"Disconnected ({e})"
            return False

    def _safe_disconnect(self):
        self.is_connected = False
        if self.serial:
            try:
                if self.serial.is_open:
                    self.serial.close()
            except Exception:
                pass
            self.serial = None

    def _execute_hardware_set_pin(self, pin_num: int, state: int) -> bool:
        if not (self.is_connected and self.serial and self.serial.is_open):
            return False
        try:
            cmd_str = f"SET {pin_num} {state}\n".encode('ascii')
            self.serial.write(cmd_str)
            self.serial.flush()
            # Read brief ACK
            self.serial.readline()
            return True
        except serial.SerialException as e:
            print(f"[SerialWorker] Serial exception during set_pin: {e}")
            self._safe_disconnect()
            return False

    def _execute_hardware_set_all(self, state: int) -> bool:
        if not (self.is_connected and self.serial and self.serial.is_open):
            return False
        try:
            cmd_str = f"ALL {state}\n".encode('ascii')
            self.serial.write(cmd_str)
            self.serial.flush()
            self.serial.readline()
            return True
        except serial.SerialException as e:
            print(f"[SerialWorker] Serial exception during set_all: {e}")
            self._safe_disconnect()
            return False

    def _execute_heartbeat(self):
        if self.is_connected and self.serial and self.serial.is_open:
            try:
                self.serial.write(b"PING\n")
                self.serial.flush()
                res = self.serial.readline()
                if not res and not self.serial.is_open:
                    self._safe_disconnect()
            except serial.SerialException:
                self._safe_disconnect()
        elif not self.is_connected:
            # Exponential backoff reconnection
            time.sleep(self.backoff_delay)
            connected = self._attempt_connect()
            if not connected:
                self.backoff_delay = min(10.0, self.backoff_delay * 1.5)

    def run(self):
        self._attempt_connect()

        while self.running:
            try:
                task: Optional[SerialTask] = None
                try:
                    task = self.cmd_queue.get(timeout=1.0)
                except queue.Empty:
                    pass

                if task:
                    result = False
                    if task.action == "set_pin":
                        pin_num = task.data["pin"]
                        state = task.data["state"]
                        self.pin_states[pin_num] = state
                        result = self._execute_hardware_set_pin(pin_num, state)

                    elif task.action == "set_all":
                        state = task.data["state"]
                        for p in self.pin_states:
                            self.pin_states[p] = state
                        result = self._execute_hardware_set_all(state)

                    elif task.action == "get_states":
                        result = dict(self.pin_states)

                    # Return result to caller via event or future
                    if task.result_holder is not None:
                        task.result_holder["result"] = result
                    if task.completion_event:
                        task.completion_event.set()
                    if task.result_future and not task.result_future.done():
                        # Thread-safe future resolution via loop callback
                        loop = task.result_future.get_loop()
                        loop.call_soon_threadsafe(task.result_future.set_result, result)

                    self.cmd_queue.task_done()

                # Periodic heartbeat & watchdog
                now = time.time()
                if now - self.last_heartbeat >= 2.5:
                    self.last_heartbeat = now
                    self._execute_heartbeat()

            except Exception as e:
                print(f"[SerialWorker] Error in worker loop: {e}")
                time.sleep(0.5)


class SerialDevice:
    """
    Thread-safe Singleton Serial Bridge.
    All calls route through the persistent SerialWorker queue.
    """
    _instance: Optional['SerialDevice'] = None
    _instance_lock = threading.Lock()

    def __new__(cls, *args, **kwargs):
        with cls._instance_lock:
            if cls._instance is None:
                cls._instance = super(SerialDevice, cls).__new__(cls)
                cls._instance._initialized = False
            return cls._instance

    def __init__(self, port: Optional[str] = None, baudrate: int = 115200):
        if getattr(self, "_initialized", False):
            return
        self._initialized = True

        self.worker = SerialWorker(requested_port=port, baudrate=baudrate)
        self.worker.start()

    @property
    def is_connected(self) -> bool:
        return self.worker.is_connected

    @property
    def device_name(self) -> str:
        return self.worker.device_name

    @property
    def device_detail(self) -> str:
        return self.worker.device_detail

    @property
    def port_name(self) -> Optional[str]:
        return self.worker.port_name

    def _parse_pin(self, pin: Any) -> int:
        if isinstance(pin, int):
            return pin
        pin_str = str(pin).strip().upper()
        if pin_str.startswith("D"):
            return int(pin_str[1:])
        elif pin_str.startswith("A"):
            return 14 + int(pin_str[1:])
        return int(pin_str)

    async def set_pin_async(self, pin: Any, state: int) -> bool:
        """Asynchronously dispatch pin actuation to the worker thread without blocking event loop."""
        pin_num = self._parse_pin(pin)
        state = 1 if state else 0
        loop = asyncio.get_running_loop()
        future = loop.create_future()

        task = SerialTask(
            action="set_pin",
            data={"pin": pin_num, "state": state},
            result_future=future
        )
        self.worker.cmd_queue.put(task)
        return await future

    async def set_all_pins_async(self, state: int) -> bool:
        """Asynchronously dispatch setting all pins."""
        state = 1 if state else 0
        loop = asyncio.get_running_loop()
        future = loop.create_future()

        task = SerialTask(
            action="set_all",
            data={"state": state},
            result_future=future
        )
        self.worker.cmd_queue.put(task)
        return await future

    def set_pin(self, pin: Any, state: int) -> bool:
        """Synchronous fallback with timeout event."""
        pin_num = self._parse_pin(pin)
        state = 1 if state else 0
        event = threading.Event()
        holder = {}

        task = SerialTask(
            action="set_pin",
            data={"pin": pin_num, "state": state},
            completion_event=event,
            result_holder=holder
        )
        self.worker.cmd_queue.put(task)
        event.wait(timeout=1.0)
        return holder.get("result", False)

    def set_all_pins(self, state: int) -> bool:
        state = 1 if state else 0
        event = threading.Event()
        holder = {}

        task = SerialTask(
            action="set_all",
            data={"state": state},
            completion_event=event,
            result_holder=holder
        )
        self.worker.cmd_queue.put(task)
        event.wait(timeout=1.0)
        return holder.get("result", False)

    def get_all_states(self) -> Dict[str, int]:
        return {
            f"D{p}" if p <= 13 else f"A{p-14}": state
            for p, state in self.worker.pin_states.items()
        }

    def get_status_info(self) -> Dict[str, Any]:
        return {
            "name": self.device_name,
            "port": self.port_name or "COM4 (Auto-Detect)",
            "connected": self.is_connected,
            "detail": self.device_detail,
            "pins": self.get_all_states()
        }
