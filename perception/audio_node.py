"""Explicitly started microphone -> Foxglove RawAudio; no recording or playback."""
import argparse
import json
import os
from pathlib import Path
import queue
import time

import numpy as np
import sounddevice as sd

ROOT = Path(__file__).resolve().parent
STOP = ROOT / '.stop-audio'


def select_input(name, index):
    if index is not None:
        device = sd.query_devices(index)
        if device['max_input_channels'] < 1:
            raise ValueError('Select an input device, not an output.')
        return index, device
    matches = [(i, d) for i, d in enumerate(sd.query_devices())
               if d['max_input_channels'] and name.casefold() in d['name'].casefold()]
    preferred = [(i, d) for i, d in matches
                 if sd.query_hostapis(d['hostapi'])['name'] == 'Windows WASAPI']
    matches = preferred or matches
    if len(matches) != 1:
        raise ValueError(f'Found {len(matches)} matching inputs. Use --list then --device-index.')
    return matches[0]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--list', action='store_true')
    parser.add_argument('--stop', action='store_true')
    parser.add_argument('--device-name', default='Plantronics')
    parser.add_argument('--device-index', type=int)
    parser.add_argument('--domain', type=int, default=74)
    parser.add_argument('--network', action='store_true', help='Use configured ROS discovery instead of localhost')
    parser.add_argument('--topic', default='/station/audio')
    args = parser.parse_args()
    if args.stop:
        STOP.touch()
        return
    if args.list:
        print(sd.query_devices())
        return
    index, device = select_input(args.device_name, args.device_index)
    rate = int(device['default_samplerate'])
    sd.check_input_settings(device=index, channels=1, dtype='int16', samplerate=rate)
    os.environ['ROS_DOMAIN_ID'] = str(args.domain)
    if not args.network:
        os.environ['ROS_AUTOMATIC_DISCOVERY_RANGE'] = 'LOCALHOST'
    import rclpy
    from foxglove_msgs.msg import RawAudio
    from std_msgs.msg import String
    from rclpy.qos import QoSProfile, ReliabilityPolicy
    rclpy.init()
    node = rclpy.create_node('underbot_microphone')
    publisher = node.create_publisher(RawAudio, args.topic,
        QoSProfile(depth=5, reliability=ReliabilityPolicy.BEST_EFFORT))
    status_pub = node.create_publisher(String, '/station/audio_status', 1)
    packets = queue.Queue(maxsize=10)
    dropped = 0
    overflows = 0

    def capture(data, frames, clock, status):
        nonlocal dropped, overflows
        overflows += int(bool(status))
        stamp = time.time_ns() - int((clock.currentTime - clock.inputBufferAdcTime) * 1e9)
        try:
            packets.put_nowait((stamp, bytes(data)))
        except queue.Full:
            dropped += 1

    STOP.unlink(missing_ok=True)
    count = 0
    last_status = 0.0
    print(f'Microphone LIVE: {device["name"]}; {rate} Hz mono; {args.topic}. No recording.', flush=True)
    try:
        with sd.RawInputStream(device=index, samplerate=rate, channels=1,
                               dtype='int16', blocksize=rate // 50, callback=capture):
            while rclpy.ok() and not STOP.exists():
                rclpy.spin_once(node, timeout_sec=0)
                try:
                    stamp, data = packets.get(timeout=0.2)
                except queue.Empty:
                    continue
                if time.time_ns() - stamp > 500_000_000:
                    dropped += 1
                    continue
                msg = RawAudio()
                msg.timestamp.sec, msg.timestamp.nanosec = divmod(stamp, 1_000_000_000)
                msg.data = data
                msg.format = 'pcm-s16'
                msg.sample_rate = rate
                msg.number_of_channels = 1
                publisher.publish(msg)
                count += 1
                if time.monotonic() - last_status >= 1:
                    samples = np.frombuffer(data, dtype='<i2').astype(float) / 32768
                    report = {'state': 'capturing', 'device': device['name'],
                              'sample_rate': rate, 'channels': 1, 'packets': count,
                              'rms': float(np.sqrt(np.mean(samples ** 2))),
                              'dropped': dropped, 'overflows': overflows, 'recording': False}
                    status_pub.publish(String(data=json.dumps(report)))
                    last_status = time.monotonic()
    except KeyboardInterrupt:
        pass
    finally:
        STOP.unlink(missing_ok=True)
        status_pub.publish(String(data=json.dumps({'state': 'stopped', 'recording': False})))
        node.destroy_node()
        rclpy.shutdown()
        print('Microphone released.', flush=True)


if __name__ == '__main__':
    main()
