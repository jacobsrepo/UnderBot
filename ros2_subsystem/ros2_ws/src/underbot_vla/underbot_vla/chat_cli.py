import rclpy
from rclpy.node import Node
from std_msgs.msg import String
import sys
import threading

class VLAChatCLI(Node):
    def __init__(self):
        super().__init__('vla_chat_cli')
        self.cmd_pub = self.create_publisher(String, '/underbot/command', 10)
        self.create_subscription(String, '/underbot/response', self.response_callback, 10)
        self.create_subscription(String, '/underbot/action_plan', self.plan_callback, 10)
        self.waiting_for_response = False

    def response_callback(self, msg: String):
        print(f"\n[ROBOT]: {msg.data}\n")
        self.waiting_for_response = False
        print("You > ", end="", flush=True)

    def plan_callback(self, msg: String):
        if msg.data and msg.data != "[]":
            print(f"[ACTION PLAN]: {msg.data}")

def input_thread(node: VLAChatCLI):
    print("=" * 60)
    print(" Compact Lab Rover — Natural Language Interface (VLA)")
    print(" Type your message or command (e.g. 'Bring Alfred the red ball')")
    print(" Type 'exit' or Ctrl+C to quit.")
    print("=" * 60)
    print("\nYou > ", end="", flush=True)

    for line in sys.stdin:
        text = line.strip()
        if not text:
            print("You > ", end="", flush=True)
            continue
        if text.lower() in ['exit', 'quit', 'q']:
            rclpy.shutdown()
            sys.exit(0)

        node.cmd_pub.publish(String(data=text))
        node.waiting_for_response = True

def main(args=None):
    rclpy.init(args=args)
    node = VLAChatCLI()

    t = threading.Thread(target=input_thread, args=(node,), daemon=True)
    t.start()

    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()

if __name__ == '__main__':
    main()
