"""Native Windows controls for the isolated Underbot Gazebo simulation."""
import json
import math
import os
from pathlib import Path
import queue
import subprocess
import threading
import time
import tkinter as tk
from tkinter import ttk, filedialog
from demonstrations import Recorder, sim_seconds, load_demo, replay
from arm_model import limits as model_limits, JOINT_NAMES, Arm
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parent
PREFIX = Path('D:/Robotics/gazebo-harmonic/.pixi/envs/default')
TOOLS = PREFIX / 'Library/libexec/gz/transport13'
SOURCE = ROOT.parents[1] / 'models/r09/underbot_description/urdf/underbot.portable.urdf'
LABELS = {'arm_base': 'Arm base', 'shoulder': 'Shoulder', 'elbow': 'Elbow',
          'wrist_pitch': 'Wrist bend', 'wrist_roll': 'Wrist rotation'}


def joint_limits():
    return model_limits()


class Transport:
    """Use native executables directly: no shell quoting or Ruby startup."""
    def __init__(self):
        self.env = dict(os.environ)
        self.env['PATH'] = f'{PREFIX / "Library/bin"};{PREFIX};' + self.env.get('PATH', '')
        self.env['GZ_PARTITION'] = 'underbot-r09-native'
        self.env['GZ_FUEL_CACHE_PATH'] = str(PREFIX.parents[2] / 'fuel-cache')
        self.limits = joint_limits()
        self.lock = threading.Lock()
        self.closed = threading.Event()
        self.pending = {}
        self.events = queue.Queue()
        self.readers = []
        self.stats = {}
        self.stats_at = 0.0
        self.positions = {}
        self.positions_at = 0.0
        self.targets = {}
        self.all_positions = {}
        self.world_poses = {}
        self.publish_lock = threading.RLock()
        self.recorder = None
        self.replay_thread = None
        self.replay_stop = threading.Event()
        for topic, kind in [('/world/underbot_world/stats', 'stats'),
                            ('/underbot/joint_states', 'joints'),
                            ('/world/underbot_world/pose/info', 'poses')]:
            threading.Thread(target=self.listen, args=(topic, kind), daemon=True).start()
        threading.Thread(target=self.worker, daemon=True).start()

    def process(self, tool, args):
        return subprocess.Popen([str(TOOLS / f'gz-transport-{tool}.exe'), *args],
            env=self.env, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            text=True, encoding='utf-8', errors='replace',
            creationflags=subprocess.CREATE_NO_WINDOW)

    def command(self, tool, args):
        process = self.process(tool, args)
        try:
            stdout, stderr = process.communicate(timeout=8)
        except subprocess.TimeoutExpired:
            process.kill()
            process.communicate()
            raise RuntimeError('Gazebo did not respond. Open the simulator and try again.')
        # This packaged Windows warning also occurs for successful commands.
        errors = '\n'.join(line for line in stderr.splitlines()
                           if not line.startswith('DynamicFactory(): Unable to parse descriptor set'))
        if process.returncode or errors.strip():
            raise RuntimeError(errors.strip() or stdout.strip() or 'Gazebo command failed')
        return stdout

    def publish(self, name, radians):
        if name not in self.limits or not math.isfinite(radians) or not self.limits[name][0] <= radians <= self.limits[name][1]:
            raise ValueError('Target is outside the model joint limits')
        with self.publish_lock:
            pose = self.current_targets()
            pose[name] = radians
            self.publish_pose(pose)

    def current_targets(self):
        with self.lock:
            if set(self.positions) != set(self.limits):
                raise RuntimeError('Waiting for joint feedback; click Play first')
            return {n: self.targets.get(n, min(hi, max(lo, self.positions[n])))
                    for n, (lo, hi) in self.limits.items()}

    def publish_pose(self, pose):
        with self.publish_lock:
            self._publish_pose(pose)

    def _publish_pose(self, pose):
        if self.replay_thread and threading.current_thread() is not self.replay_thread:
            raise RuntimeError('Stop replay before changing targets')
        if set(pose) != set(self.limits):
            raise ValueError('Provide a target for every arm and gripper joint')
        for name, radians in pose.items():
            low, high = self.limits[name]
            if not math.isfinite(radians) or not low <= radians <= high:
                raise ValueError('Target is outside the model joint limits')
        with self.lock:
            before = dict(self.positions)
            world_before = dict(self.world_poses)
            observation_stamp = sim_seconds(self.stats)
        self.command('topic', ['-t', '/underbot/arm_targets', '-m', 'gz.msgs.Actuators',
                              '-p', ' '.join(f'position: {pose[n]:.12g}' for n in JOINT_NAMES)])
        with self.lock:
            self.targets = dict(pose)
            if self.recorder:
                self.recorder.add('action', sim_seconds(self.stats), targets=dict(pose),
                                  positions=before, world_poses=world_before,
                                  observation_sim_time=observation_stamp)

    def control(self, paused):
        result = self.command('service', ['-s', '/world/underbot_world/control',
            '--reqtype', 'gz.msgs.WorldControl', '--reptype', 'gz.msgs.Boolean',
            '--timeout', '3000', '--req', f'pause: {str(paused).lower()}'])
        if 'data: true' not in result:
            raise RuntimeError('The simulator did not acknowledge Play/Pause')

    def submit(self, name, value):
        if self.replay_thread and (name in self.limits or name == 'pose'):
            self.events.put('Stop replay before changing targets')
            return
        if name == 'pause' and value:
            self.replay_stop.set()
        with self.lock:
            # Replace older pending targets rather than queuing every slider tick.
            self.pending[name] = value

    def worker(self):
        while not self.closed.wait(0.03):
            with self.lock:
                key = 'pause' if 'pause' in self.pending else next(iter(self.pending), None)
                item = (key, self.pending.pop(key)) if key else None
            if not item:
                continue
            name, value = item
            try:
                if time.monotonic() - self.stats_at > 5:
                    raise RuntimeError('No live simulator connection. Open Start UnderBot Gazebo.')
                if name == 'pause':
                    self.control(value)
                    message = 'Paused' if value else 'Running — release a slider to move a joint'
                elif name == 'focus':
                    result = self.command('service', ['-s', '/gui/move_to',
                        '--reqtype', 'gz.msgs.StringMsg', '--reptype', 'gz.msgs.Boolean',
                        '--timeout', '3000', '--req', 'data: "underbot"'])
                    if 'data: true' not in result:
                        raise RuntimeError('The viewer did not acknowledge Focus Robot')
                    message = 'Camera focused on Underbot'
                elif name == 'pose':
                    self.publish_pose(value)
                    message = 'Coordinated arm target sent'
                else:
                    self.publish(name, value)
                    message = f'Target sent: {name.replace("_joint", "")} = {math.degrees(value):.1f}°'
                self.events.put(message)
            except Exception as error:
                self.events.put(str(error))

    def listen(self, topic, kind):
        while not self.closed.is_set():
            process = self.process('topic', ['-e', '-t', topic, '--json-output'])
            self.readers.append(process)
            # stderr contains only startup diagnostics; drain it to avoid blocking.
            threading.Thread(target=lambda p=process: p.stderr.read(), daemon=True).start()
            buffer = ''
            for line in process.stdout:
                if self.closed.is_set():
                    break
                buffer += line
                try:
                    message = json.loads(buffer)
                except json.JSONDecodeError:
                    if len(buffer) > 1000000:
                        buffer = ''
                    continue
                buffer = ''
                with self.lock:
                    if kind == 'stats':
                        self.stats = message
                        self.stats_at = time.monotonic()
                    elif kind == 'poses':
                        self.world_poses = {p['name']: p for p in message.get('pose', [])
                                            if p.get('name') in ('underbot', 'pick_block', 'place_target')}
                    else:
                        self.all_positions = {j['name']: float(j.get('axis1', {}).get('position', 0))
                                              for j in message.get('joint', [])}
                        self.positions = {n: v for n, v in self.all_positions.items() if n in self.limits}
                        self.positions_at = time.monotonic()
            if process.poll() is None:
                process.terminate()
            if self.closed.wait(1):
                return

    def close(self):
        self.replay_stop.set()
        if self.recorder:
            self.recorder.finish('panel closed')
        self.closed.set()
        with self.lock:
            self.pending.clear()
        for process in self.readers:
            if process.poll() is None:
                process.terminate()


class Panel:
    def __init__(self, window):
        self.window = window
        self.transport = Transport()
        self.touched = set()
        self.variables = {}
        self.measured = {}
        self.last_demo = None
        self.last_observation = -1.0
        window.title('Underbot — Gazebo Arm Controls')
        window.geometry('950x950')
        window.minsize(900, 930)
        style = ttk.Style()
        style.theme_use('clam')
        style.configure('TButton', padding=(12, 8))
        style.configure('Heading.TLabel', font=('Segoe UI', 16, 'bold'))
        body = ttk.Frame(window, padding=18)
        body.pack(fill='both', expand=True)
        ttk.Label(body, text='Underbot arm controls', style='Heading.TLabel').pack(anchor='w')
        ttk.Label(body, text='Gazebo simulation • Angles in degrees • Release a slider to send its target').pack(anchor='w', pady=(4, 12))
        toolbar = ttk.Frame(body)
        toolbar.pack(fill='x')
        for text, callback in [('▶ Play', lambda: self.transport.submit('pause', False)),
                               ('Ⅱ Pause', lambda: self.transport.submit('pause', True)),
                               ('Reset Arm Pose', self.reset),
                               ('Focus Robot', lambda: self.transport.submit('focus', True))]:
            ttk.Button(toolbar, text=text, command=callback).pack(side='left', padx=(0, 8))
        self.connection = ttk.Label(body, text='Connecting to Gazebo…')
        self.connection.pack(anchor='w', pady=12)
        demo = ttk.Frame(body)
        demo.pack(fill='x', pady=(0, 8))
        for text, callback in [('Record Demo', self.record_demo), ('Save Demo', self.save_demo),
                               ('Replay File', self.replay_demo), ('Stop Replay', self.stop_replay),
                               ('Move Gripper XYZ', self.cartesian)]:
            ttk.Button(demo, text=text, command=callback).pack(side='left', padx=(0, 6))
        self.demo_status = ttk.Label(body, text='Demonstrations: ready (joint motion only)', wraplength=850)
        self.demo_status.pack(anchor='w')
        arms = ttk.Frame(body)
        arms.pack(fill='both', expand=True)
        for column, side in enumerate(('left', 'right')):
            group = ttk.LabelFrame(arms, text=f'{side.title()} arm', padding=12)
            group.grid(row=0, column=column, sticky='nsew', padx=(0, 8) if column == 0 else (8, 0))
            arms.columnconfigure(column, weight=1)
            for part, label in LABELS.items():
                name = f'{side}_{part}_joint'
                low, high = self.transport.limits[name]
                row = ttk.Frame(group)
                row.pack(fill='x', pady=(0, 9))
                ttk.Label(row, text=label).pack(anchor='w')
                var = tk.DoubleVar(value=0)
                self.variables[name] = var
                scale = tk.Scale(row, from_=math.ceil(math.degrees(low)),
                    to=math.floor(math.degrees(high)), resolution=1, orient='horizontal',
                    variable=var, showvalue=True, highlightthickness=0, length=330)
                scale.pack(fill='x')
                scale.bind('<ButtonPress-1>', lambda e, n=name: self.touched.add(n))
                scale.bind('<ButtonRelease-1>', lambda e, n=name: self.send(n))
                scale.bind('<KeyRelease>', lambda e, n=name: self.send(n))
                value = ttk.Label(row, text='Measured: waiting for physics')
                value.pack(anchor='w')
                self.measured[name] = value
        ttk.Label(body, text='Use Move Gripper XYZ for coordinated motion and finger controls.').pack(anchor='w', pady=(10, 4))
        self.message = ttk.Label(body, text='Click Play, then drag and release a slider.', wraplength=850)
        self.message.pack(anchor='w')
        window.protocol('WM_DELETE_WINDOW', self.close)
        self.refresh()

    def send(self, name):
        if self.transport.replay_thread:
            self.message.config(text='Stop replay before changing targets.')
            return
        self.touched.add(name)
        self.transport.submit(name, math.radians(self.variables[name].get()))
        self.message.config(text='Target queued. If paused, click Play to see the movement.')

    def reset(self):
        try:
            pose = self.transport.current_targets()
            for name, var in self.variables.items():
                var.set(0)
                pose[name] = 0
                self.touched.add(name)
            self.transport.submit('pose', pose)
        except RuntimeError as error:
            self.message.config(text=str(error))

    def cartesian(self):
        from cartesian_controls import CartesianPanel
        CartesianPanel(self.window, self.transport)

    def record_demo(self):
        t = self.transport
        with t.lock:
            if t.recorder or t.replay_thread:
                self.demo_status.config(text='Save the current recording or stop replay first.')
                return
            if time.monotonic() - min(t.stats_at, t.positions_at) > 3 or t.stats.get('paused', False):
                self.demo_status.config(text='Click Play and wait for live joint feedback before recording.')
                return
            if set(t.positions) != set(t.limits) or t.pending:
                self.demo_status.config(text='Wait for all joint feedback and pending commands, then try again.')
                return
            # Clamp tiny physics overshoots for the replay starting target only.
            initial = {n: min(hi, max(lo, t.positions[n])) for n, (lo, hi) in t.limits.items()}
            try:
                t.recorder = Recorder(ROOT / 'demonstrations', t.limits, initial, sim_seconds(t.stats))
            except OSError as error:
                self.demo_status.config(text=str(error))
                return
            self.last_observation = -1.0
        self.demo_status.config(text='Recording. Move the sliders, then click Save Demo.')

    def save_demo(self):
        t = self.transport
        with t.lock:
            if not t.recorder:
                return
            recorder, t.recorder = t.recorder, None
            recorder.finish()
        self.last_demo = recorder.path
        self.demo_status.config(text=f'Saved: {recorder.path.name}')

    def replay_demo(self):
        t = self.transport
        if t.recorder or t.replay_thread:
            self.demo_status.config(text='Save the current recording or stop replay first.')
            return
        path = filedialog.askopenfilename(parent=self.window, title='Replay a joint demonstration',
            initialdir=ROOT / 'demonstrations', filetypes=[('Demonstrations', '*.jsonl')])
        if not path:
            return
        try:
            load_demo(path, t.limits)
        except (ValueError, OSError, KeyError, TypeError) as error:
            self.demo_status.config(text=f'Cannot replay: {error}')
            return
        t.replay_stop.clear()
        def run():
            try:
                replay(t, path, t.replay_stop)
                t.events.put('Replay complete; simulation paused.')
            except Exception as error:
                t.events.put(str(error))
            finally:
                try:
                    t.control(True)
                except Exception as error:
                    t.events.put(f'Could not pause: {error}')
                t.replay_thread = None
        with t.lock:
            t.pending.clear()
            t.replay_thread = threading.Thread(target=run, daemon=True)
            t.replay_thread.start()
        self.demo_status.config(text='Replay: restoring initial pose, then sending recorded targets. Stop Replay pauses physics.')
        self.watch_replay()

    def watch_replay(self):
        if self.transport.replay_thread:
            self.window.after(200, self.watch_replay)
        else:
            self.demo_status.config(text='Replay ended. See status below. Click Play before another recording or replay.')

    def stop_replay(self):
        self.transport.replay_stop.set()
        self.transport.submit('pause', True)

    def refresh(self):
        with self.transport.lock:
            age = time.monotonic() - self.transport.stats_at
            paused = self.transport.stats.get('paused', False)
            positions = dict(self.transport.positions)
            recorder = self.transport.recorder
            stamp = sim_seconds(self.transport.stats)
            if recorder:
                feedback_age = time.monotonic() - self.transport.positions_at
                try:
                    if age > 3 or feedback_age > 3:
                        recorder.finish('feedback lost')
                    elif stamp < recorder.last - 1e-6:
                        recorder.finish('simulation clock reset')
                    elif not paused and stamp != self.last_observation and set(positions) == set(self.transport.limits):
                        recorder.add('observation', stamp, positions=positions,
                                     targets=dict(self.transport.targets),
                                     world_poses=dict(self.transport.world_poses))
                        self.last_observation = stamp
                    if recorder.file.closed:
                        self.transport.recorder = None
                        self.demo_status.config(text=f'Recording interrupted: {recorder.path.name}')
                except (OSError, ValueError) as error:
                    recorder.file.close()
                    self.transport.recorder = None
                    self.demo_status.config(text=f'Recording failed: {error}')
        self.connection.config(text=('Disconnected — open Start UnderBot Gazebo.cmd' if age > 5 else
            'Connected • PAUSED — targets move when you click Play' if paused else 'Connected • RUNNING'))
        for name, value in positions.items():
            if name not in self.measured:
                continue
            degrees = math.degrees(value)
            self.measured[name].config(text=f'Measured: {degrees:+.1f}°' + (' (last reading)' if age > 5 else ''))
            if name not in self.touched:
                self.variables[name].set(round(degrees))
        while not self.transport.events.empty():
            self.message.config(text=self.transport.events.get_nowait())
        self.window.after(150, self.refresh)

    def close(self):
        self.transport.close()
        self.window.destroy()


if __name__ == '__main__':
    window = tk.Tk()
    Panel(window)
    window.mainloop()
