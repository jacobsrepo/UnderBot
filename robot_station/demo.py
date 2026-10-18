"""Synthetic station data, not SLAM, Nav2, YOLO inference or physical simulation."""
import io
import math
import time
from PIL import Image, ImageDraw
import rclpy
from rclpy.node import Node
from rclpy.qos import QoSProfile, DurabilityPolicy
from geometry_msgs.msg import PoseStamped, TransformStamped, Twist
from nav_msgs.msg import OccupancyGrid, Odometry, Path
from sensor_msgs.msg import CompressedImage, Imu
from tf2_ros import TransformBroadcaster
from gateway import bounded_twist


class Demo(Node):
    def __init__(self):
        super().__init__('underbot_synthetic_demo')
        self.x, self.y, self.yaw = -1.8, -1.8, 0.0
        self.command = Twist()
        self.received = 0.0
        self.tf = TransformBroadcaster(self)
        self.odom = self.create_publisher(Odometry, '/odom', 10)
        self.imu = self.create_publisher(Imu, '/imu/data', 10)
        self.camera = self.create_publisher(CompressedImage, '/camera/image/compressed', 10)
        self.annotated = self.create_publisher(CompressedImage, '/perception/annotated/compressed', 10)
        qos = QoSProfile(depth=1, durability=DurabilityPolicy.TRANSIENT_LOCAL)
        self.map = self.create_publisher(OccupancyGrid, '/map', qos)
        self.plan = self.create_publisher(Path, '/plan', 10)
        self.create_subscription(Twist, '/station/cmd_vel', self.on_command, 10)
        self.create_timer(0.05, self.tick)
        self.create_timer(0.5, self.image)
        self.create_timer(1.0, self.world)

    def on_command(self, msg):
        self.command = bounded_twist(msg)
        self.received = time.monotonic()

    def tick(self):
        cmd = self.command if time.monotonic() - self.received < 0.35 else Twist()
        self.yaw += cmd.angular.z * 0.05
        self.x += (math.cos(self.yaw)*cmd.linear.x-math.sin(self.yaw)*cmd.linear.y)*0.05
        self.y += (math.sin(self.yaw)*cmd.linear.x+math.cos(self.yaw)*cmd.linear.y)*0.05
        stamp = self.get_clock().now().to_msg()
        odom = Odometry()
        odom.header.stamp, odom.header.frame_id, odom.child_frame_id = stamp, 'map', 'base_link'
        odom.pose.pose.position.x, odom.pose.pose.position.y = self.x, self.y
        odom.pose.pose.orientation.z, odom.pose.pose.orientation.w = math.sin(self.yaw/2), math.cos(self.yaw/2)
        odom.twist.twist = cmd
        self.odom.publish(odom)
        imu = Imu()
        imu.header.stamp, imu.header.frame_id = stamp, 'base_link'
        imu.orientation = odom.pose.pose.orientation
        self.imu.publish(imu)
        tf = TransformStamped()
        tf.header = odom.header
        tf.child_frame_id = 'base_link'
        tf.transform.translation.x, tf.transform.translation.y = self.x, self.y
        tf.transform.rotation = odom.pose.pose.orientation
        self.tf.sendTransform(tf)

    def world(self):
        grid = OccupancyGrid()
        grid.header.frame_id, grid.header.stamp = 'map', self.get_clock().now().to_msg()
        grid.info.resolution, grid.info.width, grid.info.height = 0.1, 60, 60
        grid.info.origin.position.x = grid.info.origin.position.y = -3.0
        grid.info.origin.orientation.w = 1.0
        grid.data = [100 if x < 2 or y < 2 or x > 57 or y > 57 or (25<x<35 and 23<y<38) else 0 for y in range(60) for x in range(60)]
        self.map.publish(grid)
        path = Path()
        path.header = grid.header
        for x,y in [(-1.8,-1.8),(-1.8,0.5),(-1.5,1.8),(0.7,1.8),(1.8,1.8)]:
            pose = PoseStamped()
            pose.header = grid.header
            pose.pose.position.x, pose.pose.position.y, pose.pose.orientation.w = x,y,1.0
            path.poses.append(pose)
        self.plan.publish(path)

    def image(self):
        image = Image.new('RGB',(640,360),'#152734')
        draw = ImageDraw.Draw(image)
        draw.rectangle((30,65,610,320),outline='#52778a',width=3)
        draw.text((25,20),'SYNTHETIC CAMERA / NO HARDWARE',fill='#5cddcf')
        draw.text((45,285),f'Robot x={self.x:.2f} y={self.y:.2f} heading={math.degrees(self.yaw):.1f}',fill='white')
        self.publish_image(self.camera,image)
        draw.rectangle((270,100,370,260),outline='#ffc65b',width=3)
        draw.text((245,78),'EXAMPLE POSE / NOT YOLO',fill='#ffc65b')
        joints=[(320,120),(320,150),(290,170),(275,210),(350,170),(365,210),(320,205),(300,250),(340,250)]
        for a,b in [(0,1),(1,2),(2,3),(1,4),(4,5),(1,6),(6,7),(6,8)]:
            draw.line([joints[a],joints[b]],fill='#5cddcf',width=3)
        for x,y in joints:
            draw.ellipse((x-4,y-4,x+4,y+4),fill='white')
        self.publish_image(self.annotated,image)

    def publish_image(self,publisher,image):
        buf=io.BytesIO()
        image.save(buf,format='JPEG')
        msg=CompressedImage()
        msg.header.stamp=self.get_clock().now().to_msg()
        msg.header.frame_id='camera_link'
        msg.format='jpeg'
        msg.data=buf.getvalue()
        publisher.publish(msg)


if __name__=='__main__':
    rclpy.init()
    node=Demo()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.try_shutdown()
