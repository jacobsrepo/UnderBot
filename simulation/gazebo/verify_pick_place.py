"""Pick-and-place task check, with optional explicitly reported grasp assist."""
import argparse
import json
import threading
import time
import numpy as np
from controls import Transport, ROOT
from arm_model import Arm
from demonstrations import Recorder, sim_seconds


def main(grasp_assist=False, record_demo=False):
    t = Transport()
    arm = Arm('left')
    report = {'trained_policy': False, 'grasp_assist': grasp_assist,
              'physical_lift_passed': False, 'task_lift_passed': False}
    recorder = None
    sampler_stop = threading.Event()
    sampler = None
    def wait(predicate, timeout=30):
        end = time.monotonic() + timeout
        while time.monotonic() < end:
            if predicate():
                return
            time.sleep(0.1)
        raise RuntimeError('Timed out waiting for simulation feedback or joint motion')
    def xyz(name):
        pos = t.world_poses[name]['position']
        return np.array([pos.get(k, 0) for k in ('x', 'y', 'z')])
    def centre():
        # Account for base movement using the model's measured world transform.
        base = t.world_poses['underbot']
        o = base.get('orientation', {})
        x, y, z, w = (o.get(k, 1 if k == 'w' else 0) for k in ('x', 'y', 'z', 'w'))
        rot = np.array([[1-2*(y*y+z*z), 2*(x*y-z*w), 2*(x*z+y*w)],
                        [2*(x*y+z*w), 1-2*(x*x+z*z), 2*(y*z-x*w)],
                        [2*(x*z-y*w), 2*(y*z+x*w), 1-2*(x*x+y*y)]])
        q = np.array([t.positions[n] for n in arm.names])
        return xyz('underbot') + rot @ arm.fk(q), rot, q
    def move(target, tolerance=0.004):
        deadline = time.monotonic() + 50
        while time.monotonic() < deadline:
            actual, rot, q = centre()
            error = target - actual
            if np.linalg.norm(error) < tolerance:
                return
            next_q = arm.solve(arm.fk(q) + rot.T @ error, q)
            pose = t.current_targets()
            # Feedback correction compensates the provisional PD controller's sag.
            corrected = np.clip(np.array([pose[n] for n in arm.names]) + np.clip(next_q-q, -0.08, 0.08), arm.low, arm.high)
            pose.update(zip(arm.names, map(float, corrected)))
            t.publish_pose(pose)
            time.sleep(0.5)
        raise RuntimeError(f'Grasp-centre target did not converge: error {np.linalg.norm(target-centre()[0]):.4f} m')
    def move_object(target):
        """Visually servo a grasped object, compensating for in-gripper slip."""
        deadline = time.monotonic() + 60
        while time.monotonic() < deadline:
            error = target - xyz('pick_block')
            if np.linalg.norm(error) < 0.006:
                return
            _, rot, q = centre()
            local_step = rot.T @ np.clip(error, -0.01, 0.01)
            next_q = arm.solve(arm.fk(q) + local_step, q)
            pose = t.current_targets()
            corrected = np.clip(np.array([pose[n] for n in arm.names]) + np.clip(next_q-q, -0.06, 0.06), arm.low, arm.high)
            pose.update(zip(arm.names, map(float, corrected)))
            t.publish_pose(pose)
            time.sleep(0.5)
        raise RuntimeError(f'Block target did not converge: error {np.linalg.norm(target-xyz("pick_block")):.4f} m')
    try:
        report['stage'] = 'connect'
        wait(lambda: t.stats_at > 0)
        if grasp_assist:
            # DetachableJoint starts attached. Remove that joint while the
            # world is still paused so every episode begins with a free block.
            t.command('topic', ['-t', '/underbot/grasp/detach', '-m', 'gz.msgs.Empty', '-p', 'unused: true'])
            report['initial_grasp_detached'] = True
            time.sleep(0.5)
        t.control(False)
        report['stage'] = 'joint and object feedback'
        wait(lambda: len(t.positions) == len(t.limits) and all(n in t.world_poses for n in ('underbot', 'pick_block')))
        pose = {n: 0.0 for n in t.limits}
        # Rotate away from the task object and lift the angled fingers clear of
        # the tabletop before opening them.
        pose['left_arm_base_joint'] = -0.4
        pose['left_elbow_joint'] = 0.18
        pose['left_gripper_left_joint'] = 0.6
        t.publish_pose(pose)
        report['stage'] = 'open fingers'
        # Reissue the idempotent initial target after discovery/startup settles.
        time.sleep(2)
        t.publish_pose(pose)
        wait(lambda: all(abs(t.all_positions.get(n, -10)-0.6) < 0.06 for n in ('left_gripper_left_joint', 'left_gripper_right_joint')))
        report['finger_open_positions'] = {n: t.all_positions[n] for n in ('left_gripper_left_joint', 'left_gripper_right_joint')}
        report['initial_block_xyz'] = xyz('pick_block').tolist()
        initial_block = xyz('pick_block').copy()
        if record_demo:
            recorder = Recorder(ROOT / 'demonstrations', t.limits, dict(t.positions),
                                sim_seconds(t.stats), metadata={
                                    'task': 'pick_place',
                                    'replayable': False,
                                    'grasp_assist': grasp_assist,
                                    'note': 'Joint/object training data; grasp attach/detach events are not replay actions'})
            t.recorder = recorder
            report['demonstration_path'] = str(recorder.path)
            def sample_observations():
                last = -1.0
                while not sampler_stop.wait(0.15):
                    with t.lock:
                        stamp = sim_seconds(t.stats)
                        positions = dict(t.positions)
                        targets = dict(t.targets)
                        world_poses = dict(t.world_poses)
                    if stamp > last and set(positions) == set(t.limits):
                        recorder.add('observation', stamp, positions=positions,
                                     targets=targets, world_poses=world_poses)
                        last = stamp
            sampler = threading.Thread(target=sample_observations, daemon=True)
            sampler.start()
        # Pinch through the block's centre of mass. The previous 8 mm high
        # contact created a torque that tipped the block out of the fingers.
        # The 14 mm-tall jaw colliders still clear the tabletop at this height.
        target = initial_block.copy()
        report['stage'] = 'approach'
        move(target + [0, 0, 0.035])
        report['approach_reached'] = True
        report['approach_grasp_centre_xyz'] = centre()[0].tolist()
        report['stage'] = 'reach block'
        # Descend to the actual grasp centre in both modes. Grasp assist only
        # replaces the unreliable contact constraint after the fingers close;
        # it must not attach an object from the overhead approach pose.
        move(target)
        report['grasp_centre_reached'] = True
        report['grasp_centre_xyz'] = centre()[0].tolist()
        report['block_xyz_at_grasp'] = xyz('pick_block').tolist()
        report['stage'] = 'close and lift'
        if grasp_assist:
            separation = float(np.linalg.norm(xyz('pick_block') - centre()[0]))
            report['attach_separation_metres'] = separation
            if separation > 0.025:
                raise RuntimeError('Grasp assist refused: block is not between the fingers')
        t.publish('left_gripper_left_joint', 0)
        if grasp_assist:
            t.command('topic', ['-t', '/underbot/grasp/attach', '-m', 'gz.msgs.Empty', '-p', 'unused: true'])
            report['grasp_attached'] = True
        time.sleep(3)
        report['finger_closed_positions'] = {n: t.all_positions[n] for n in ('left_gripper_left_joint', 'left_gripper_right_joint')}
        if grasp_assist:
            move_object(initial_block + [0, 0, 0.035])
        else:
            move(target + [0, 0, 0.035])
        time.sleep(2)
        lifted = xyz('pick_block')
        report['lifted_block_xyz'] = lifted.tolist()
        report['physical_lift_passed'] = bool(lifted[2] - initial_block[2] > 0.02)
        report['task_lift_passed'] = report['physical_lift_passed']
        if grasp_assist:
            report['assisted_lift_passed'] = report['physical_lift_passed']
            report['physical_lift_passed'] = False
        if not report['task_lift_passed']:
            raise RuntimeError('The fingers moved but the physical block was not lifted. Do not train on this attempt.')
        report['stage'] = 'transport'
        goal = np.array([-0.02, 0.38, initial_block[2]])
        report['carry_offset_after_lift'] = (lifted - centre()[0]).tolist()
        move_object(goal + [0, 0, 0.035])
        report['carry_offset_before_place'] = (xyz('pick_block') - centre()[0]).tolist()
        report['stage'] = 'place'
        # Lower to a short release height. The current simulated arm cannot
        # reach the tabletop at this lateral pose without crossing a joint limit; the
        # remaining 20 mm is a controlled drop onto the target.
        move_object(goal + [0, 0, 0.020])
        time.sleep(2)
        report['block_xyz_before_release'] = xyz('pick_block').tolist()
        report['stage'] = 'release'
        if grasp_assist:
            t.command('topic', ['-t', '/underbot/grasp/detach', '-m', 'gz.msgs.Empty', '-p', 'unused: true'])
            report['grasp_detached'] = True
            time.sleep(1)
        # Transfer weight to the table, then reduce the pinch in small steps so
        # high-friction pads do not flick the block sideways.
        start_open = max(t.all_positions[n] for n in ('left_gripper_left_joint', 'left_gripper_right_joint'))
        for value in np.linspace(start_open + 0.02, 0.6, 20):
            t.publish('left_gripper_left_joint', float(value))
            time.sleep(0.25)
        time.sleep(2)
        move(centre()[0] + [0, 0, 0.035])
        time.sleep(2)
        final = xyz('pick_block')
        report['final_block_xyz'] = final.tolist()
        report['pick_place_passed'] = bool(np.linalg.norm(final[:2]-goal[:2]) < 0.0225 and abs(final[2]-initial_block[2]) < 0.01)
        report['physical_pick_place_passed'] = bool(report['pick_place_passed'] and not grasp_assist)
        if not report['pick_place_passed']:
            raise RuntimeError('Block did not settle inside the placement tolerance')
        report['stage'] = 'complete'
    except Exception as error:
        report['error'] = str(error)
    finally:
        sampler_stop.set()
        if sampler:
            sampler.join(timeout=2)
        if recorder:
            t.recorder = None
            recorder.finish('saved' if report.get('pick_place_passed') else 'verification failed')
            report['demonstration_records'] = recorder.count
        try:
            t.control(True)
        finally:
            t.close()
        (ROOT / 'generated/pick-place-verification.json').write_text(json.dumps(report, indent=2))
        print(json.dumps(report, indent=2), flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--grasp-assist', action='store_true',
                        help='use Gazebo detachable-joint assist after a proximity-checked close command')
    parser.add_argument('--record-demo', action='store_true',
                        help='save a successful task episode as training JSONL')
    args = parser.parse_args()
    main(args.grasp_assist, args.record_demo)
