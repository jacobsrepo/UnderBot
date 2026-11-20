"""Run one team demonstration through the live gateway and verify its result.

Use the sourced ROS environment on ROS_DOMAIN_ID=75. This sends simulation
navigation commands; it refuses a status with hardware enabled.
"""
import json
import math
import time
import uuid

import rclpy
from std_msgs.msg import String


def main():
    rclpy.init()
    node = rclpy.create_node('fleet_mission_verification')
    status = {}
    replies = []
    request_id = 'team-check-'+uuid.uuid4().hex[:12]
    def receive(msg):
        status.clear(); status.update(json.loads(msg.data))
    node.create_subscription(String, '/station/nav/status', receive, 10)
    node.create_subscription(String, '/station/ai/response', lambda msg: replies.append(json.loads(msg.data)), 10)
    publisher = node.create_publisher(String, '/station/ai/request', 10)
    sent = False
    try:
        deadline = time.monotonic()+10
        while (not status or publisher.get_subscription_count() == 0) and time.monotonic() < deadline:
            rclpy.spin_once(node, timeout_sec=.1)
        if status.get('mode') != 'simulation' or status.get('hardware_enabled') is not False or not status.get('fleet'):
            raise RuntimeError('Live fleet simulation is unavailable.')
        homes = {name: status['landmarks'][name+'_start'] for name in ('robot_1', 'robot_2')}
        publisher.publish(String(data=json.dumps({'id': request_id, 'text': 'run team demo'})))
        sent = True
        deadline = time.monotonic()+180
        stages = []
        minimum = math.inf
        while time.monotonic() < deadline:
            rclpy.spin_once(node, timeout_sec=.1)
            for reply in replies:
                if reply.get('id') == request_id and reply.get('ok') is False:
                    raise RuntimeError('Gateway rejected the mission: '+str(reply.get('text')))
            mission = status.get('mission') or {}
            if mission.get('request_id') != request_id:
                continue
            positions = {n: status['robots'][n]['pose'][:2] for n in homes}
            distance = math.dist(*positions.values())
            minimum = min(minimum, distance)
            if distance < status['minimum_separation_metres']-1e-8:
                raise AssertionError('Robot separation violated.')
            stage = mission['stage']
            if stage not in stages:
                stages.append(stage); print('Stage:', stage, flush=True)
            if mission['state'] == 'completed':
                if mission['completed_stages'] != 5 or len(stages) != 5:
                    raise AssertionError('Not all stages completed.')
                if any(math.dist(positions[n], homes[n]) > .02 for n in homes):
                    raise AssertionError('Robots did not return home.')
                print(json.dumps({'result':'passed', 'stages':stages,
                    'minimum_observed_separation_metres':minimum,
                    'required_separation_metres':status['minimum_separation_metres'],
                    'robots_home':True}), flush=True)
                sent = False
                return
            if mission['state'] != 'running':
                raise RuntimeError('Mission ended: '+str(mission))
        raise TimeoutError('Team mission did not finish within 180 seconds.')
    finally:
        if sent:
            publisher.publish(String(data=json.dumps({'id':request_id+'-stop', 'text':'stop navigation'})))
            rclpy.spin_once(node, timeout_sec=.2)
        node.destroy_node(); rclpy.try_shutdown()


if __name__ == '__main__':
    main()
