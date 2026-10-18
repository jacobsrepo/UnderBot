import rclpy
from rclpy.node import Node
from std_msgs.msg import String
from geometry_msgs.msg import Twist
from nav_msgs.msg import Odometry

import asyncio
import json
import os
import threading
import subprocess
import uvicorn
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse

app = FastAPI(title="Underbot Dashboard")
active_connections: list[WebSocket] = []
ros_node = None

class DashboardROSNode(Node):
    def __init__(self):
        super().__init__('dashboard_ros_node')

        # Publishers
        self.cmd_pub = self.create_publisher(String, '/underbot/command', 10)
        self.twist_pub = self.create_publisher(Twist, '/cmd_vel', 10)

        # Subscribers
        self.create_subscription(String, '/underbot/response', self.response_callback, 10)
        self.create_subscription(String, '/underbot/action_plan', self.plan_callback, 10)
        self.create_subscription(Odometry, '/odom', self.odom_callback, 10)

        self.get_logger().info('Dashboard ROS Node initialized')

    def response_callback(self, msg: String):
        broadcast_message({"type": "response", "text": msg.data})

    def plan_callback(self, msg: String):
        broadcast_message({"type": "plan", "data": msg.data})

    def odom_callback(self, msg: Odometry):
        pos = msg.pose.pose.position
        twist = msg.twist.twist
        broadcast_message({
            "type": "odom",
            "x": round(pos.x, 3),
            "y": round(pos.y, 3),
            "v": round(twist.linear.x, 2),
            "w": round(twist.angular.z, 2)
        })

def broadcast_message(message: dict):
    if not active_connections:
        return
    msg_json = json.dumps(message)
    loop = asyncio.get_event_loop()
    for ws in list(active_connections):
        try:
            asyncio.run_coroutine_threadsafe(ws.send_text(msg_json), loop)
        except Exception:
            pass

def get_system_stats():
    # Read Pi temperature
    temp = "N/A"
    try:
        with open("/sys/class/thermal/thermal_zone0/temp", "r") as f:
            temp = f"{round(int(f.read().strip()) / 1000.0, 1)} °C"
    except Exception:
        pass

    # Read RAM usage
    ram_usage = "N/A"
    try:
        out = subprocess.check_output("free -m | awk 'NR==2{printf \"%.1f / %.1f GB (%.0f%%)\", $3/1024, $2/1024, $3*100/$2 }'", shell=True).decode()
        ram_usage = out.strip()
    except Exception:
        pass

    return {
        "type": "telemetry",
        "temp": temp,
        "ram": ram_usage,
        "battery": "100%", # Default or from INA260 topic
        "status": "Online"
    }

async def telemetry_loop():
    while True:
        await asyncio.sleep(2.0)
        if active_connections:
            stats = get_system_stats()
            msg_json = json.dumps(stats)
            for ws in list(active_connections):
                try:
                    await ws.send_text(msg_json)
                except Exception:
                    pass

@app.on_event("startup")
async def startup_event():
    asyncio.create_task(telemetry_loop())

@app.get("/", response_class=HTMLResponse)
async def get_index():
    template_path = os.path.join(os.path.dirname(__file__), "templates", "index.html")
    if not os.path.exists(template_path):
        # Fallback to installed share path
        from ament_index_python.packages import get_package_share_directory
        template_path = os.path.join(get_package_share_directory('underbot_dashboard'), 'templates', 'index.html')
    with open(template_path, "r", encoding="utf-8") as f:
        return f.read()

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    active_connections.append(websocket)
    # Send initial status
    await websocket.send_text(json.dumps(get_system_stats()))
    try:
        while True:
            data = await websocket.receive_text()
            payload = json.loads(data)
            action_type = payload.get("type")

            if action_type == "command":
                text = payload.get("text", "").strip()
                if text and ros_node:
                    ros_node.cmd_pub.publish(String(data=text))

            elif action_type == "cmd_vel":
                linear = float(payload.get("linear", 0.0))
                angular = float(payload.get("angular", 0.0))
                if ros_node:
                    t = Twist()
                    t.linear.x = linear
                    t.angular.z = angular
                    ros_node.twist_pub.publish(t)

            elif action_type == "stop":
                if ros_node:
                    ros_node.twist_pub.publish(Twist())

    except WebSocketDisconnect:
        if websocket in active_connections:
            active_connections.remove(websocket)
    except Exception:
        if websocket in active_connections:
            active_connections.remove(websocket)

def ros_spin_thread(node):
    rclpy.spin(node)

def main():
    global ros_node
    rclpy.init()
    ros_node = DashboardROSNode()

    t = threading.Thread(target=ros_spin_thread, args=(ros_node,), daemon=True)
    t.start()

    port = 8000
    print(f"==================================================")
    print(f" Underbot Dashboard starting on http://0.0.0.0:{port}")
    print(f" Access via: http://ros2-brain-system:{port}")
    print(f"         or: http://100.123.136.69:{port}")
    print(f"==================================================")

    uvicorn.run(app, host="0.0.0.0", port=port, log_level="info")

    ros_node.destroy_node()
    rclpy.shutdown()

if __name__ == "__main__":
    main()
