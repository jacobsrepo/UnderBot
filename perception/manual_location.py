"""Publish an explicitly manual geographic marker, never an actual GPS reading."""
import argparse
import json
import math
from pathlib import Path

import rclpy
from rclpy.node import Node
from sensor_msgs.msg import NavSatFix, NavSatStatus
from std_msgs.msg import String
from common import configure_ros

TOPIC = '/station/manual_location'
DEFAULT_FILE = Path(__file__).with_name('location.local.json')

def read_location(path):
    location = json.loads(Path(path).read_text(encoding='utf-8-sig'))
    lat, lon = location.get('latitude'), location.get('longitude')
    if (isinstance(lat, bool) or isinstance(lon, bool)
            or not isinstance(lat, (int, float)) or not isinstance(lon, (int, float))
            or not math.isfinite(lat) or not math.isfinite(lon)
            or not -90 <= lat <= 90 or not -180 <= lon <= 180):
        raise ValueError('Provide finite latitude [-90,90] and longitude [-180,180] in decimal degrees.')
    return float(lat), float(lon)

class ManualLocation(Node):
    def __init__(self, latitude, longitude):
        super().__init__('underbot_manual_location_NOT_GPS')
        self.latitude, self.longitude = latitude, longitude
        self.publisher = self.create_publisher(NavSatFix, TOPIC, 1)
        self.status = self.create_publisher(String, '/station/location_status', 1)
        self.create_timer(1.0, self.publish)
        self.get_logger().info('Publishing MANUAL static Pi marker; no GPS or live tracking.')

    def publish(self):
        msg = NavSatFix()
        msg.header.stamp = self.get_clock().now().to_msg()
        msg.header.frame_id = 'MANUAL_PI_MARKER_NOT_GPS'
        # NavSatFix is used only as Foxglove's geographic display transport.
        # This dedicated topic must never be fed to localization/GPS fusion.
        msg.status.status = NavSatStatus.STATUS_FIX
        msg.status.service = 0
        msg.latitude, msg.longitude = self.latitude, self.longitude
        msg.altitude = float('nan')  # altitude has not been supplied or measured
        msg.position_covariance_type = NavSatFix.COVARIANCE_TYPE_UNKNOWN
        self.publisher.publish(msg)
        self.status.publish(String(data=json.dumps({
            'source': 'manual', 'live_tracking': False, 'gps_fix': False,
            'label': 'Pi manually placed marker; not measured location',
        })))

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--file', type=Path, default=DEFAULT_FILE)
    parser.add_argument('--domain', type=int, default=74)
    args = parser.parse_args()
    if not args.file.is_file():
        parser.error('Create ignored location.local.json with your latitude and longitude first.')
    latitude, longitude = read_location(args.file)
    configure_ros(args.domain)
    rclpy.init()
    node = ManualLocation(latitude, longitude)
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.try_shutdown()

if __name__ == '__main__':
    main()
