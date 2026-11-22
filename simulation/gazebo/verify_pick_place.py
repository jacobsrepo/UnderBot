"""Physical grasp feasibility check. No attachment, teleporting, or learned policy."""
import json
import time
import numpy as np
from controls import Transport, ROOT
from arm_model import Arm


def main():
    t = Transport()
    arm = Arm('left')
    report = {'trained_policy': False, 'physical_lift_passed': False}
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
    def move(target):
        deadline = time.monotonic() + 50
        while time.monotonic() < deadline:
            actual, rot, q = centre()
            error = target - actual
            if np.linalg.norm(error) < 0.004:
                return
            next_q = arm.solve(arm.fk(q) + rot.T @ error, q)
            pose = t.current_targets()
            # Feedback correction compensates the provisional PD controller's sag.
            corrected = np.clip(np.array([pose[n] for n in arm.names]) + np.clip(next_q-q, -0.08, 0.08), arm.low, arm.high)
            pose.update(zip(arm.names, map(float, corrected)))
            t.publish_pose(pose)
            time.sleep(0.5)
        raise RuntimeError(f'Grasp-centre target did not converge: error {np.linalg.norm(target-centre()[0]):.4f} m')
    try:
        report['stage'] = 'connect'
        wait(lambda: t.stats_at > 0)
        t.control(False)
        report['stage'] = 'joint and object feedback'
        wait(lambda: len(t.positions) == len(t.limits) and all(n in t.world_poses for n in ('underbot', 'pick_block')))
        pose = {n: 0.0 for n in t.limits}
        # Lift the angled fingers clear of the tabletop before opening them.
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
        # Grasp above the block centre to clear the tabletop with angled fingers.
        target = initial_block + [0, 0, 0.008]
        report['stage'] = 'approach'
        move(target + [0, 0, 0.035])
        report['approach_reached'] = True
        report['stage'] = 'reach block'
        move(target)
        report['grasp_centre_reached'] = True
        report['stage'] = 'close and lift'
        t.publish('left_gripper_left_joint', 0)
        time.sleep(3)
        report['finger_closed_positions'] = {n: t.all_positions[n] for n in ('left_gripper_left_joint', 'left_gripper_right_joint')}
        move(target + [0, 0, 0.035])
        time.sleep(2)
        lifted = xyz('pick_block')
        report['lifted_block_xyz'] = lifted.tolist()
        report['physical_lift_passed'] = bool(lifted[2] - initial_block[2] > 0.02)
        if not report['physical_lift_passed']:
            raise RuntimeError('The fingers moved but the physical block was not lifted. Do not train on this attempt.')
        goal = np.array([-0.13, 0.35, target[2]])
        move(goal + [0, 0, 0.035])
        move(goal)
        t.publish('left_gripper_left_joint', 0.6)
        time.sleep(2)
        move(goal + [0, 0, 0.035])
        time.sleep(2)
        final = xyz('pick_block')
        report['final_block_xyz'] = final.tolist()
        report['physical_pick_place_passed'] = bool(np.linalg.norm(final[:2]-goal[:2]) < 0.0225 and abs(final[2]-initial_block[2]) < 0.01)
    except Exception as error:
        report['error'] = str(error)
    finally:
        try:
            t.control(True)
        finally:
            t.close()
        (ROOT / 'generated/pick-place-verification.json').write_text(json.dumps(report, indent=2))
        print(json.dumps(report, indent=2), flush=True)


if __name__ == '__main__':
    main()
