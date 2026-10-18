"""Pi-side PulseAudio helper. Streams raw PCM over SSH; never records files."""
import argparse
import json
import os
import subprocess
import sys
import time

MAC = 'DD:66:D6:29:BA:CD'
CARD = 'bluez_card.' + MAC.replace(':', '_')


def pulse(kind):
    return json.loads(subprocess.check_output(['pactl', '-f', 'json', 'list', kind], timeout=8))


def microphone():
    cards = [card for card in pulse('cards') if card['name'] == CARD]
    if not cards:
        subprocess.run(['bluetoothctl', 'connect', MAC], stdout=subprocess.DEVNULL,
                       stderr=subprocess.DEVNULL, timeout=20)
        time.sleep(1)
        cards = [card for card in pulse('cards') if card['name'] == CARD]
        if not cards:
            raise RuntimeError('Stone 190 is disconnected. Turn it on near the Pi, then press Comms ON again.')
    profiles = cards[0]['profiles']
    candidates = [name for name, details in profiles.items()
                  if details.get('sources', details.get('n_sources', 0)) > 0
                  and details.get('available') not in ('no', False)
                  and ('headset' in name or 'handsfree' in name)]
    if not candidates:
        raise RuntimeError('Stone 190 has no available hands-free microphone profile.')
    active = cards[0]['active_profile']
    if isinstance(active, dict):
        active = active['name']
    selected = active if active in candidates else candidates[0]
    if active != selected:
        subprocess.run(['pactl', 'set-card-profile', CARD, selected], check=True, timeout=10)
    sources = [s for s in pulse('sources')
               if s['name'].startswith('bluez_source.' + MAC.replace(':', '_'))
               and not s['name'].endswith('.monitor')]
    if len(sources) != 1:
        raise RuntimeError('No unique Bluetooth microphone source; speaker monitors are not microphones.')
    return sources[0]['name']


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('mode', choices=['capture', 'play', 'check'])
    parser.add_argument('--rate', type=int, choices=[8000, 16000, 32000, 44100, 48000], default=16000)
    args = parser.parse_args()
    source = microphone()
    if args.mode == 'check':
        print(json.dumps({'source': source, 'sample_rate': 16000, 'channels': 1}))
        return
    command = ['parec', '--device=' + source] if args.mode == 'capture' else [
        'paplay', '--device=' + next(s['name'] for s in pulse('sinks')
                                   if s['name'].startswith('bluez_sink.' + MAC.replace(':', '_')))]
    command += ['--raw', '--format=s16le', f'--rate={args.rate}', '--channels=1', '--latency-msec=60']
    os.execvp(command[0], command)


if __name__ == '__main__':
    try:
        main()
    except Exception as error:
        print(str(error), file=sys.stderr)
        sys.exit(1)
