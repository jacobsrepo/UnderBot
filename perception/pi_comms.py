"""Operator-controlled Pi audio over SSH, published locally for Foxglove."""
import argparse
import json
import os
from pathlib import Path
import queue
import subprocess
import threading
import time

ROOT = Path(__file__).resolve().parent


class Capture:
    def __init__(self, command):
        self.command = command
        self.stop = threading.Event()
        self.packets = queue.Queue(maxsize=10)
        self.state = 'connecting to Pi microphone'
        self.process = None
        self.thread = threading.Thread(target=self.run, daemon=True)
        self.thread.start()

    def run(self):
        try:
            self.process = subprocess.Popen(self.command, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
            if self.stop.is_set():
                self.process.terminate()
            while not self.stop.is_set():
                data = self.process.stdout.read(640)  # 20 ms, 16 kHz mono PCM16
                if len(data) != 640:
                    break
                self.state = 'listening to Pi microphone'
                item = (time.time_ns(), data)
                try:
                    self.packets.put_nowait(item)
                except queue.Full:
                    self.packets.get_nowait()
                    self.packets.put_nowait(item)
            if not self.stop.is_set():
                self.state = 'unavailable: ' + self.process.stderr.read(2048).decode(errors='replace').strip()[-400:]
        except Exception as exc:
            self.state = 'unavailable: ' + str(exc)
        finally:
            self.close()

    def close(self):
        self.stop.set()
        if self.process and self.process.poll() is None:
            self.process.terminate()


class Transmit:
    """Bounded microphone queue; SSH writes never run in the audio/ROS callback."""
    def __init__(self, command, capture, device_name):
        self.command, self.capture, self.device_name = command, capture, device_name
        self.stop = threading.Event()
        self.process = None
        self.state = 'waiting for Pi audio'
        self.packets = queue.Queue(maxsize=5)
        self.sent = 0
        self.peak = 0
        self.thread = threading.Thread(target=self.run, daemon=True)
        self.thread.start()

    def run(self):
        try:
            import sounddevice as sd
            import numpy as np
            from audio_node import select_input
            index, device = select_input(self.device_name, None)
            rate = int(device['default_samplerate'])
            sd.check_input_settings(device=index, channels=1, dtype='int16', samplerate=rate)
            while self.capture.state != 'listening to Pi microphone':
                if self.stop.wait(0.1):
                    return
                if self.capture.stop.is_set():
                    raise RuntimeError('Pi audio is unavailable; reconnect and retry Comms ON')
            command = self.command[:-1] + [self.command[-1] + f' --rate {rate}']
            self.process = subprocess.Popen(command, stdin=subprocess.PIPE,
                stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, bufsize=0,
                creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
            if self.stop.is_set():
                return

            def microphone(data, frames, clock, status):
                if self.stop.is_set():
                    return
                try:
                    self.packets.put_nowait((time.monotonic(), bytes(data)))
                except queue.Full:
                    pass  # Drop instead of building up delayed speech.

            with sd.RawInputStream(device=index, samplerate=rate, channels=1,
                                   dtype='int16', blocksize=rate // 50, callback=microphone):
                while not self.stop.is_set():
                    if self.capture.stop.is_set():
                        raise RuntimeError('Pi microphone connection lost; retry Comms ON')
                    if self.process.poll() is not None:
                        raise RuntimeError(self.process.stderr.read(2048).decode(errors='replace')[-400:])
                    try:
                        stamp, data = self.packets.get(timeout=0.1)
                    except queue.Empty:
                        continue
                    if time.monotonic() - stamp > 0.2:
                        continue
                    self.process.stdin.write(data)
                    self.sent += 1
                    self.peak = max(self.peak, int(np.abs(np.frombuffer(data, dtype='<i2').astype('int32')).max()))
                    self.state = 'transmitting PC headset to Pi speaker'
        except Exception as exc:
            self.state = 'transmit unavailable: ' + str(exc)
        finally:
            self.close()

    def close(self):
        self.stop.set()
        if self.process and self.process.poll() is None:
            self.process.terminate()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--host', default='underbot@100.123.136.69')
    parser.add_argument('--key', default=str(ROOT / '.private/pi_access_ed25519'))
    parser.add_argument('--domain', default=74, type=int)
    parser.add_argument('--device-name', default='Plantronics')
    args = parser.parse_args()
    os.environ['ROS_DOMAIN_ID'] = str(args.domain)
    os.environ['ROS_AUTOMATIC_DISCOVERY_RANGE'] = 'LOCALHOST'
    import rclpy
    from std_msgs.msg import String
    from foxglove_msgs.msg import RawAudio
    from rclpy.qos import qos_profile_sensor_data
    command = ['ssh', '-T', '-i', args.key, '-o', 'IdentitiesOnly=yes', '-o', 'BatchMode=yes',
               '-o', 'ConnectTimeout=8', '-o', 'ServerAliveInterval=5', '-o', 'ServerAliveCountMax=2',
               args.host, 'python3 /home/underbot/UnderBot/perception/pi_audio_device.py capture']
    rclpy.init()
    node = rclpy.create_node('underbot_pi_comms')
    audio = node.create_publisher(RawAudio, '/station/audio/pi', qos_profile_sensor_data)
    status = node.create_publisher(String, '/station/comms/status', 10)
    capture = None
    transmit = None
    playback_command = command[:-1] + [command[-1].replace(' capture', ' play')]

    def request(msg):
        nonlocal capture, transmit
        try:
            enabled = json.loads(msg.data)['enabled']
            if not isinstance(enabled, bool):
                return
        except (ValueError, KeyError, TypeError):
            return
        if enabled and capture and not capture.stop.is_set() and transmit and not transmit.stop.is_set():
            return
        if transmit:
            transmit.close()
            transmit = None
        if capture:
            capture.close()
            capture = None
        if enabled:
            capture = Capture(command)
            transmit = Transmit(playback_command, capture, args.device_name)

    def publish():
        if capture is None:
            return
        for _ in range(10):
            try:
                stamp, data = capture.packets.get_nowait()
            except queue.Empty:
                break
            if time.time_ns() - stamp > 500_000_000:
                continue
            msg = RawAudio()
            msg.timestamp.sec, msg.timestamp.nanosec = divmod(stamp, 1_000_000_000)
            msg.data = data
            msg.format = 'pcm-s16'
            msg.sample_rate = 16000
            msg.number_of_channels = 1
            audio.publish(msg)

    def heartbeat():
        state = f'{capture.state}; {transmit.state}' if capture and transmit else 'OFF'
        status.publish(String(data=json.dumps({'state': state,
            'transmit_packets': transmit.sent if transmit else 0,
            'transmit_peak': transmit.peak if transmit else 0,
            'device': 'Pi Stone 190', 'topic': '/station/audio/pi', 'recording': False})))

    node.create_subscription(String, '/station/comms/request', request, 10)
    node.create_timer(0.02, publish)
    node.create_timer(0.5, heartbeat)
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        if transmit:
            transmit.close()
        if capture:
            capture.close()
        node.destroy_node()
        rclpy.try_shutdown()


if __name__ == '__main__':
    main()
