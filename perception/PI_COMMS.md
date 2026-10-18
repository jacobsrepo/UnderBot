# Pi Bluetooth microphone in Foxglove

The paired Stone 190 (`DD:66:D6:29:BA:CD`) exposes a real microphone through
PulseAudio's `handsfree_head_unit` profile. Native audio is 8 kHz mono; the helper
resamples it to 16 kHz PCM16 for the ROS/Foxglove stream. This does not add detail
to the original telephone-quality audio. The A2DP playback profile has no mic.

Start **D:\Robotics\Start UnderBot EMEET Live.cmd**, turn on the speaker near
the Pi and ensure it is connected to the Pi. The Comms adapter starts OFF.
In **UnderBot Controls**, **Request comms ON** starts listening and **Request
comms OFF** releases the capture process. The **Pi Stone 190 microphone - Comms
ON/OFF** audio panel uses `/station/audio/pi` (`foxglove_msgs/msg/RawAudio`).
Comms ON also captures the PC Plantronics headset microphone and sends it to the
Stone 190 speaker over a separate SSH stream. Comms OFF stops both directions.
The PC microphone uses its native sample rate; PulseAudio converts it on the Pi.
Use headphones on the PC to avoid feeding received audio back into the microphone.
Panel mute changes PC playback only; use Comms OFF to stop microphone capture.
It does not transcribe speech, send audio to Qwen or record files.

`pi_comms.py` runs on Windows in the perception Pixi environment, on local ROS
domain 74. It consumes `/station/comms/request` (JSON `{"enabled":true/false}`)
and publishes `/station/comms/status`; the gateway mirrors this in station status.
`pi_audio_device.py` runs on the Pi, selects only the Stone's actual microphone
(never a speaker monitor), and execs `parec`. PCM travels through authenticated
SSH over Tailscale. No new network listener is opened. Connection failures are
shown separately for listening and transmission in Comms status. ON attempts to
reconnect the paired speaker. Turn it on near the Pi and press ON to retry.

The PC headset stream `/station/audio` remains separate. The generic audio panel
can select either topic. The gateway, Qwen chat and motor watchdog remain separate
from audio capture. Closing Foxglove alone does not stop an enabled stream;
press Comms OFF before closing, or terminate the `pi_comms.py` adapter.

Deployment: copy `pi_audio_device.py` to
`/home/underbot/UnderBot/perception/pi_audio_device.py`; the Pi needs `pactl` and
`parec` in its user PulseAudio session. Local key stays in ignored `.private`.
The paired speaker can be reconnected with
`bluetoothctl connect DD:66:D6:29:BA:CD` on the Pi.

Live test: `pixi run python check_pi_comms.py` briefly enables capture, verifies
nonzero PCM and packet shape, then asserts OFF stops the stream. No file recorded.
