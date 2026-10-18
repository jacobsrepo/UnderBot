# UnderBot — ROS 2 Jazzy Robotics & Local VLA Subsystem

The **UnderBot (Compact Lab Rover)** is an autonomous mobile manipulation robot built on a modified Xiaomi robotic vacuum differential-drive base, powered by a Raspberry Pi 5 (8GB) high-level brain and an ESP32-S3 low-level motor/sensor controller.

This subsystem provides the complete **ROS 2 Jazzy** software stack, parametric **URDF** model, **local Vision-Language-Action (VLA)** reasoning engine, and a **Tailwind CSS Web Mission Control Dashboard**.

---

## 🛠️ Subsystem Architecture

```
ros2_ws/src/
├── underbot_description/      # URDF / Xacro kinematic model, meshes, TF2 tree, RViz config
├── underbot_vla/              # Local VLA brain (Ollama + Moondream + Qwen2.5) & chat CLI
└── underbot_dashboard/        # FastAPI + WebSocket teleop server & Tailwind CSS dark UI
```

### Physical Dimensions & Sensor Layout
* **Footprint:** $200 \times 200 \times 320\text{ mm}$ chassis (<400 mm total height).
* **Drive Base:** Xiaomi vacuum differential drive ($70\text{ mm}$ wheel diameter, $170\text{ mm}$ track width) + front/rear passive casters.
* **Sensors:**
  * **LiDAR:** 360° 2D Laser Distance Sensor on Floor 1/2 (`/scan`).
  * **Dual IMUs:** Body IMU (BNO086 6-DOF Game Rotation Vector on Floor 3) + Camera Head IMU (Floor 4).
  * **ToF Array:** 4x Time-of-Flight sensors on Floor 2 (Front, Rear, Left, Right).
* **2-Axis Pan/Tilt Head:** Camera yaw ($-90^\circ \to +90^\circ$) & tilt ($-45^\circ \to +60^\circ$) on Floor 4.
* **Manipulator Arm:** 3-DOF side-mounted arm (Shoulder Yaw, Shoulder Pitch, Elbow Pitch) + Parallel Jaw Gripper.

---

## 🚀 Getting Started

### 1. Build the ROS 2 Workspace
```bash
cd ros2_ws
source /opt/ros/jazzy/setup.bash
colcon build --symlink-install
source install/setup.bash
```

### 2. Visualize the Robot in RViz2
Launch the complete kinematic tree with real-time joint sliders:
```bash
# In desktop / RDP environment:
ros2 launch underbot_description display.launch.py

# Headless mode (via SSH):
ros2 launch underbot_description display.launch.py gui:=false rviz:=false
```

### 3. Run the Local VLA Brain
Make sure Ollama is running (`systemctl status ollama`):
```bash
# Terminal 1: Launch VLA Brain Node
ros2 launch underbot_vla vla.launch.py model_name:=qwen2.5:1.5b

# Terminal 2: Interactive Terminal Chat CLI
ros2 run underbot_vla chat_cli
```
You can converse naturally or issue task commands like:
* *"Where is the red ball?"*
* *"Bring Alfred the red ball"*
* *"Look around and find my chair"*

### 4. Open the Web Mission Control Dashboard
Launch the web server:
```bash
ros2 launch underbot_dashboard dashboard.launch.py
```
Open your browser at:
👉 **`http://<robot-ip-or-tailscale-hostname>:8000`**

Features:
* 💬 **Live Natural Language VLA Chat**
* 🎙️ **Microphone Voice Control** (Browser Web Speech recognition)
* 🎮 **Teleoperation D-Pad & Keyboard Controls** (<kbd>W</kbd><kbd>A</kbd><kbd>S</kbd><kbd>D</kbd> + Space Stop)
* 🛑 **Emergency Stop**
* 📊 **Live Odometry & Raspberry Pi 5 Telemetry** (CPU Temp, RAM usage)

---

## ⚙️ Background Services (systemd)
Systemd services for persistent execution on boot are located in `services/`:
* `services/underbot-vla.service` &mdash; Auto-starts VLA brain node.
* `services/underbot-dashboard.service` &mdash; Auto-starts Mission Control web dashboard.

---

## 👨‍💻 Maintainer
* **Athul C S** (`athulcs735@gmail.com`) &mdash; ROS 2 Core, VLA Architecture & Web UI
