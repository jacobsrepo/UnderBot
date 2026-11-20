"""Two URDF instances sharing one simulated, centrally scheduled navigation world."""
import argparse
import json
import math
from pathlib import Path
import numpy as np

import rclpy
from geometry_msgs.msg import PoseStamped, TransformStamped
from nav_msgs.msg import Path as RosPath, Odometry
from sensor_msgs.msg import Imu
from visualization_msgs.msg import Marker
from rclpy.qos import QoSProfile, DurabilityPolicy
from std_msgs.msg import String
from tf2_ros import StaticTransformBroadcaster

from navigation_demo import NavigationDemo
from fleet_core import FleetPlanner, ROBOTS, swept_distance
from fleet_urdf import load_robot
from fleet_missions import prepare_mission, MISSION_NAMES


class FleetDemo(NavigationDemo):
    def __init__(self, urdf_paths):
        super().__init__()
        self.models = {name: load_robot(path, name) for name, path in zip(ROBOTS, urdf_paths)}
        radius = max(model[3] for model in self.models.values())
        self.planner = FleetPlanner(self.grid, self.meta['resolution'], self.meta['origin'], radius=radius)
        self.positions = {ROBOTS[0]: tuple(self.meta['spawn'])}
        if not self.planner.clear(self.positions[ROBOTS[0]], self.positions[ROBOTS[0]]):
            raise ValueError('Robot footprint does not fit at map spawn.')
        candidates = [self.planner.world((x, y)) for y, x in zip(*np.where(self.planner.grid == 0))]
        candidates.sort(key=lambda p: math.dist(p, self.positions[ROBOTS[0]]))
        self.positions[ROBOTS[1]] = next(p for p in candidates if math.dist(p, self.positions[ROBOTS[0]]) >= self.planner.separation+.3)
        self.landmarks = {key: value for key, value in self.landmarks.items() if self.planner.clear(value, value)}
        self.landmarks.update({name+'_start': list(point) for name, point in self.positions.items()})
        self.headings = dict.fromkeys(ROBOTS, 0.)
        self.homes = dict(self.positions)
        self.mission = None
        self.mission_stages = []
        self.mission_elapsed = 0.
        self.stage_pause = 0.
        self.goals, self.paths, self.requests = {}, {}, {}
        self.phase = 0.
        self.slot_seconds = self.meta['resolution']*math.sqrt(2)/.4
        self.state = 'idle'
        self.path_pubs = {name: self.create_publisher(RosPath, f'/navigation/{name}/plan', 10) for name in ROBOTS}
        # Foxglove needs an advertised ROS schema before its publish tool can
        # create a client publisher. These handles advertise types, not commands.
        self.goal_schema_pubs = [self.create_publisher(PoseStamped, topic, 10) for topic in
            ['/station/nav/goal', '/station/nav/robot_1/goal', '/station/nav/robot_2/goal']]
        self.odom_pubs = {name: self.create_publisher(Odometry, f'/navigation/{name}/odom', 10) for name in ROBOTS}
        self.labels = self.create_publisher(Marker, '/navigation/team/labels', 10)
        qos = QoSProfile(depth=1, durability=DurabilityPolicy.TRANSIENT_LOCAL)
        self.descriptions = {name: self.create_publisher(String, f'/navigation/{name}/robot_description', qos) for name in ROBOTS}
        self.static_tf = StaticTransformBroadcaster(self)
        fixed = []
        for name, (xml, _, joints, _) in self.models.items():
            self.descriptions[name].publish(String(data=xml))
            for parent, child, xyz, quat in joints:
                tf = TransformStamped(); tf.header.frame_id = parent; tf.child_frame_id = child
                tf.header.stamp = self.get_clock().now().to_msg()
                tf.transform.translation.x, tf.transform.translation.y, tf.transform.translation.z = xyz
                tf.transform.rotation.x, tf.transform.rotation.y, tf.transform.rotation.z, tf.transform.rotation.w = quat
                fixed.append(tf)
            self.create_subscription(PoseStamped, f'/station/nav/{name}/goal', lambda msg, n=name: self.fleet_clicked(n, msg), 10)
        self.static_tf.sendTransform(fixed)
        self.world(); self.publish_status()

    def event(self, name, event, message, request_id=None):
        request_id = request_id or self.requests.get(name)
        if request_id:
            self.events.publish(String(data=json.dumps({'mode': 'simulation', 'id': request_id, 'event': event, 'message': f'{name}: {message}'})))

    def mission_event(self, event, message):
        if self.mission and self.mission.get('request_id'):
            self.events.publish(String(data=json.dumps({'mode': 'simulation',
                'id': self.mission['request_id'], 'event': event, 'message': 'Team: '+message,
                'step': self.mission['stage_index']+1, 'total_steps': self.mission['total_stages']})))

    def halt(self, reason, event='cancelled'):
        if self.mission and self.mission['state'] == 'running':
            self.mission_event(event, reason)
            self.mission['state'] = 'cancelled' if event == 'cancelled' else 'failed'
            self.mission['message'] = reason
        self.mission_stages = []; self.stage_pause = 0.
        for name in ROBOTS:
            self.event(name, 'cancelled', reason)
        self.goals, self.paths, self.requests = {}, {}, {}
        self.phase = 0.; self.state = reason

    def start_mission_stage(self):
        stage = self.mission_stages[self.mission['stage_index']]
        self.goals, self.paths = dict(stage['goals']), stage['paths']
        self.phase = 0.; self.stage_pause = 0.
        self.mission['stage'] = stage['name']
        self.state = 'Team: '+stage['name']
        self.mission_event('started', f"Stage {self.mission['stage_index']+1}/{self.mission['total_stages']}: {stage['name']}.")
        self.world()

    def robot_state(self, name):
        if name in self.goals and self.paths:
            path = self.paths[name]; i = int(self.phase)
            if math.dist(self.planner.at(path, i), self.planner.at(path, i+1)) < 1e-9:
                other = next(n for n in ROBOTS if n != name)
                return 'yielding to '+other
            return 'moving'
        if self.mission and self.mission['state'] == 'running':
            return 'waiting for teammate' if self.goals else 'stage complete'
        return 'idle'

    def request(self, msg):
        name, request_id = ROBOTS[0], None
        try:
            data = json.loads(msg.data)
            if not isinstance(data, dict):
                raise ValueError('Expected a navigation request object.')
            name = data.get('robot_id', ROBOTS[0]); request_id = data.get('request_id')
            if name not in ROBOTS:
                raise ValueError('Unknown robot ID.')
            if request_id is not None and (not isinstance(request_id, str) or not 1 <= len(request_id) <= 128):
                raise ValueError('Invalid request ID.')
            if data.get('action') == 'stop':
                self.halt('Fleet stopped; all reservations cleared.')
                self.event(name, 'completed', 'Fleet stopped.', request_id); return
            if data.get('action') == 'team_mission':
                kind = data.get('mission')
                stages = prepare_mission(kind, self.planner, self.positions, self.homes)
                self.halt('Replaced by a new team mission.')
                self.mission_stages = stages
                self.mission_elapsed = 0.
                self.mission = {'kind': kind, 'name': MISSION_NAMES[kind], 'state': 'running',
                    'request_id': request_id, 'stage_index': 0, 'total_stages': len(stages),
                    'completed_stages': 0, 'stage': stages[0]['name'], 'message': ''}
                self.start_mission_stage()
                self.publish_status()
                return
            if data.get('action') != 'goal':
                raise ValueError('Use robot goals, a team mission, or stop navigation in fleet mode.')
            xy = data['xy']
            if not isinstance(xy, (list, tuple)) or len(xy) != 2 or not all(type(v) in (int, float) and math.isfinite(v) for v in xy):
                raise ValueError('Goal must contain two finite coordinates.')
            team_active = self.mission and self.mission['state'] == 'running'
            goals = {**({} if team_active else self.goals), name: tuple(xy)}
            # Synchronous callback: simulation time is frozen while replanning from actual poses.
            paths = self.planner.plan(self.positions, goals)
            if team_active:
                self.halt('Individual goal replaced the team mission; teammate stopped.')
            self.event(name, 'cancelled', 'Replaced by new goal.')
            self.goals, self.paths, self.phase = goals, paths, 0.
            self.requests[name] = request_id
            self.state = 'following coordinated paths'
            self.event(name, 'started', 'Coordinated route accepted.')
        except (ValueError, KeyError, TypeError) as exc:
            self.event(name, 'rejected', str(exc), request_id)
            self.state = 'rejected: '+str(exc)
        self.world(); self.publish_status()

    def fleet_clicked(self, name, msg):
        if msg.header.frame_id != 'map':
            self.state = 'rejected: goal must use map frame'; return
        self.request(String(data=json.dumps({'robot_id': name, 'action': 'goal', 'xy': [msg.pose.position.x, msg.pose.position.y]})))

    def clicked_goal(self, msg):
        self.fleet_clicked(ROBOTS[0], msg)

    def on_command(self, msg):
        self.halt('Manual control / Cancel stopped the fleet.')

    def tick(self):
        if not hasattr(self, 'positions'):
            return
        previous_positions = dict(self.positions)
        if self.mission and self.mission['state'] == 'running':
            self.mission_elapsed += .05
            if self.mission_elapsed > 900:
                self.halt('Team mission exceeded its simulation deadline.', 'timed_out')
            elif not self.paths:
                self.stage_pause += .05
                if self.stage_pause >= 1.:
                    self.mission['stage_index'] += 1
                    self.start_mission_stage()
        if self.paths:
            next_phase = self.phase+.05/self.slot_seconds
            index, fraction = int(next_phase), next_phase % 1
            next_positions = {}
            for name in ROBOTS:
                path = self.paths[name]
                a, b = self.planner.at(path, index), self.planner.at(path, index+1)
                next_positions[name] = tuple(a[j]+fraction*(b[j]-a[j]) for j in (0, 1))
            a, b = ROBOTS
            safe = swept_distance(self.positions[a], next_positions[a], self.positions[b], next_positions[b]) >= self.planner.separation-1e-9
            if not safe or not all(self.planner.clear(self.positions[n], next_positions[n]) for n in ROBOTS):
                self.halt('Collision guard stopped the fleet.', 'rejected')
            else:
                for name in ROBOTS:
                    old, new = self.positions[name], next_positions[name]
                    if math.dist(old, new) > 1e-9:
                        self.headings[name] = math.atan2(new[1]-old[1], new[0]-old[0])
                    if name in self.goals and next_phase >= len(self.paths[name])-1:
                        self.event(name, 'completed', 'Goal reached.')
                        self.goals.pop(name); self.requests.pop(name, None)
                self.positions, self.phase = next_positions, next_phase
                if not self.goals:
                    self.paths = {}; self.state = 'goals reached'
                    if self.mission and self.mission['state'] == 'running':
                        self.mission['completed_stages'] += 1
                        if self.mission['completed_stages'] == self.mission['total_stages']:
                            self.mission['state'] = 'completed'
                            self.state = 'Team mission complete'
                            self.mission_event('completed', self.mission['name']+' completed by both robots.')
                            self.mission_stages = []
                        else:
                            self.state = 'Both robots ready; next stage in one second'
        stamp = self.get_clock().now().to_msg()
        for name in ROBOTS:
            tf = TransformStamped(); tf.header.frame_id = 'map'; tf.header.stamp = stamp
            tf.child_frame_id = self.models[name][1]
            tf.transform.translation.x, tf.transform.translation.y = self.positions[name]
            tf.transform.rotation.z, tf.transform.rotation.w = math.sin(self.headings[name]/2), math.cos(self.headings[name]/2)
            self.tf.sendTransform(tf)
            odom = Odometry(); odom.header = tf.header; odom.child_frame_id = tf.child_frame_id
            odom.pose.pose.position.x, odom.pose.pose.position.y = self.positions[name]
            odom.pose.pose.orientation = tf.transform.rotation
            odom.twist.twist.linear.x = math.dist(previous_positions[name], self.positions[name])/.05
            self.odom_pubs[name].publish(odom)
            if name == ROBOTS[0]:
                self.odom.publish(odom)
                imu = Imu(); imu.header.stamp = stamp; imu.header.frame_id = tf.child_frame_id
                imu.orientation = tf.transform.rotation; self.imu.publish(imu)

    def world(self):
        super().world()
        if not hasattr(self, 'path_pubs'):
            return
        for name in ROBOTS:
            path = RosPath(); path.header.frame_id = 'map'; path.header.stamp = self.get_clock().now().to_msg()
            for x, y in self.paths.get(name, []):
                pose = PoseStamped(); pose.header = path.header
                pose.pose.position.x, pose.pose.position.y, pose.pose.orientation.w = x, y, 1.
                path.poses.append(pose)
            self.path_pubs[name].publish(path)

    def publish_status(self):
        if not hasattr(self, 'positions'):
            return
        self.nav_pub.publish(String(data=json.dumps({'mode': 'simulation', 'hardware_enabled': False,
            'fleet': True, 'state': self.state, 'landmarks': self.landmarks,
            'pose': [*self.positions[ROBOTS[0]], self.headings[ROBOTS[0]]],
            'heading_degrees': math.degrees(self.headings[ROBOTS[0]]) % 360,
            'robots': {n: {'pose': [*self.positions[n], self.headings[n]], 'goal': self.goals.get(n), 'state': self.robot_state(n)} for n in ROBOTS},
            'mission': self.mission,
            'minimum_separation_metres': self.planner.separation,
            'planner': 'prioritized space-time A*; swept circular footprints; fixed zero-joint URDF pose'})))
        for i, name in enumerate(ROBOTS):
            label = Marker(); label.header.frame_id = 'map'; label.header.stamp = self.get_clock().now().to_msg()
            label.ns = 'team'; label.id = i; label.type = Marker.TEXT_VIEW_FACING; label.action = Marker.ADD
            label.pose.position.x, label.pose.position.y = self.positions[name]
            label.pose.position.z = .8; label.pose.orientation.w = 1.; label.scale.z = .16
            label.color.r, label.color.g, label.color.b, label.color.a = (0.2, .85, 1., 1.) if i == 0 else (1., .65, .2, 1.)
            label.text = f"Robot {i+1}: {self.robot_state(name)}"
            self.labels.publish(label)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--urdf', nargs=2, default=[str(Path(__file__).resolve().parent.parent/'compact_lab_rover/rover.urdf')]*2)
    args = parser.parse_args()
    rclpy.init(); node = FleetDemo(args.urdf)
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node(); rclpy.try_shutdown()
