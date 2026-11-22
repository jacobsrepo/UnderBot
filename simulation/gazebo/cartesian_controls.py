"""Small Cartesian jogs, solved into coordinated joint targets."""
import math
import time
import tkinter as tk
from tkinter import ttk
import numpy as np
from arm_model import Arm


class CartesianPanel:
    def __init__(self, parent, transport):
        self.t = transport
        self.window = tk.Toplevel(parent)
        self.window.title('Underbot - coordinated gripper movement')
        body = ttk.Frame(self.window, padding=20)
        body.pack(fill='both', expand=True)
        ttk.Label(body, text='Move the grasp centre in robot-base coordinates', font=('Segoe UI', 13, 'bold')).pack()
        ttk.Label(body, text='5 mm per click. Several joints move together. Position-only IK; orientation may change.').pack(pady=8)
        for side in ('left', 'right'):
            group = ttk.LabelFrame(body, text=side.title() + ' arm', padding=10)
            group.pack(fill='x', pady=8)
            row = ttk.Frame(group)
            row.pack()
            for axis, label in enumerate(('X', 'Y', 'Z')):
                for sign in (-1, 1):
                    ttk.Button(row, text=label + (' -' if sign < 0 else ' +'),
                               command=lambda s=side, a=axis, d=sign: self.jog(s, a, d)).pack(side='left', padx=3)
            row = ttk.Frame(group)
            row.pack(pady=8)
            ttk.Button(row, text='Open fingers', command=lambda s=side: self.grip(s, 0.6)).pack(side='left', padx=5)
            ttk.Button(row, text='Close fingers', command=lambda s=side: self.grip(s, 0.0)).pack(side='left', padx=5)
        ttk.Button(body, text='Pause simulation', command=lambda: transport.submit('pause', True)).pack(pady=8)
        self.status = ttk.Label(body, text='Click Play in the main panel before moving.', wraplength=650)
        self.status.pack()
        ttk.Label(body, text='These controls do not plan around collisions. Use small moves and inspect the scene.', wraplength=650).pack(pady=8)

    def ready(self):
        if self.t.replay_thread:
            raise ValueError('Stop replay before moving')
        if time.monotonic() - min(self.t.stats_at, self.t.positions_at) > 3 or self.t.stats.get('paused', False):
            raise ValueError('Click Play and wait for fresh joint feedback')
        if self.t.pending:
            raise ValueError('Wait for the previous command')

    def jog(self, side, axis, sign):
        try:
            self.ready()
            arm = Arm(side)
            pose = self.t.current_targets()
            # Target-based jogging avoids repeatedly commanding the same point
            # while the real simulated joints are still catching up.
            q = np.array([pose[n] for n in arm.names])
            target = arm.fk(q)
            target[axis] += sign * 0.005
            solution = arm.solve(target, q)
            pose.update(zip(arm.names, map(float, solution)))
            self.t.submit('pose', pose)
            self.status.config(text=f'{side.title()} target XYZ: ' + ', '.join(f'{v:.3f} m' for v in target))
        except (ValueError, RuntimeError) as error:
            self.status.config(text=str(error))

    def grip(self, side, value):
        try:
            self.ready()
            self.t.submit(f'{side}_gripper_left_joint', value)
            self.status.config(text=f'{side.title()} finger target: {math.degrees(value):.1f} degrees')
        except (ValueError, RuntimeError) as error:
            self.status.config(text=str(error))
