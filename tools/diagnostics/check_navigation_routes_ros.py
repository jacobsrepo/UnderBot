"""Verify diagonal plans, exact endpoints and arrival through the live gateway."""
import heapq,json,math,time
from pathlib import Path
import numpy as np
import rclpy
from std_msgs.msg import String
from nav_msgs.msg import Path as RosPath,Odometry
from navigation_core import plan_route,route_length,segment_is_free

data=Path('D:/Robotics/robot-station/navigation-data')
grid=np.load(data/'demo_map.npz')['grid'];meta=json.loads((data/'map_metadata.json').read_text())
start=tuple(meta['spawn']);goal=(2.037,3.081)
def cell(p):return tuple(math.floor((v+20)/meta['resolution']) for v in p)
def old_cost(a,b):
    q=[(0,a)];seen=set()
    while q:
        cost,c=heapq.heappop(q)
        if c in seen:continue
        if c==b:return cost*meta['resolution']
        seen.add(c)
        for dx,dy in ((1,0),(-1,0),(0,1),(0,-1)):
            n=(c[0]+dx,c[1]+dy)
            if 0<=n[0]<grid.shape[1] and 0<=n[1]<grid.shape[0] and grid[n[1],n[0]]==0 and n not in seen:heapq.heappush(q,(cost+1,n))
    raise ValueError('No old route')
route=plan_route(grid,start,goal,meta['resolution'])
assert route==[start,goal],route
old_length=old_cost(cell(start),cell(goal));new_length=route_length(route)
far_start=time.monotonic();far=plan_route(grid,start,tuple(meta['landmarks']['goal_a']),meta['resolution'])
assert all(segment_is_free(grid,tuple((v+20)/meta['resolution'] for v in a),tuple((v+20)/meta['resolution'] for v in b)) for a,b in zip(far,far[1:]))
print(json.dumps({'old_cardinal_length':old_length,'new_direct_length':new_length,'improvement_percent':100*(1-new_length/old_length),'far_goal_waypoints':len(far),'far_goal_length':route_length(far),'far_goal_planning_seconds':time.monotonic()-far_start}),flush=True)
rclpy.init();node=rclpy.create_node('underbot_diagonal_route_check')
states=[];responses={};events={};paths=[];poses=[];heartbeats=[]
def reply(msg):
    d=json.loads(msg.data)
    if d.get('execution_event'):events.setdefault(d['id'],[]).append(d)
    elif d.get('final',True):responses[d['id']]=d
node.create_subscription(String,'/station/nav/status',lambda m:states.append(json.loads(m.data)),10)
node.create_subscription(String,'/station/ai/response',reply,10)
node.create_subscription(String,'/station/status',lambda m:heartbeats.append(json.loads(m.data)),10)
node.create_subscription(RosPath,'/plan',lambda m:paths.append([(p.pose.position.x,p.pose.position.y) for p in m.poses]),10)
node.create_subscription(Odometry,'/odom',lambda m:poses.append((m.pose.pose.position.x,m.pose.pose.position.y)),100)
pub=node.create_publisher(String,'/station/ai/request',10)
def until(predicate,seconds=45):
    deadline=time.monotonic()+seconds
    while not predicate() and time.monotonic()<deadline:rclpy.spin_once(node,timeout_sec=.1)
    assert predicate(),str(states[-1] if states else 'no state')
def send(text):
    key='route-'+str(time.time_ns());pub.publish(String(data=json.dumps({'id':key,'text':text})))
    until(lambda:key in responses);assert responses[key]['ok'];return key
def completed(key):until(lambda:any('completed' in e['text'] for e in events.get(key,[])))
try:
    until(lambda:states and pub.get_subscription_count())
    completed(send('go to start'));until(lambda:states[-1].get('goal_error_metres',1)<.02)
    start_pose=states[-1]['pose'][:2];poses.clear();paths.clear()
    key=send('go to 2.037, 3.081')
    until(lambda:any(p and p[-1]==goal for p in paths))
    active=next(p for p in paths if p and p[-1]==goal)
    assert len(active)==2,active
    assert active[-1]==goal
    completed(key);until(lambda:states[-1]['state']=='goal reached in simulation' and states[-1]['goal_error_metres']<.02)
    assert not any('rejected' in e['text'] for e in events[key])
    travelled=route_length(poses);straight=math.dist(start_pose,goal)
    assert travelled<straight*1.03,(travelled,straight)
    result={'passed':True,'requested_goal':goal,'actual_pose':states[-1]['pose'][:2],'arrival_error_cm':states[-1]['goal_error_metres']*100,'published_path_points':len(active),'old_cardinal_length_metres':old_length,'new_direct_length_metres':new_length,'observed_travel_metres':travelled,'improvement_percent':100*(1-new_length/old_length),'far_goal_shortcut_points':len(far),'hardware_enabled':False}
    assert heartbeats and all(h['hardware_enabled'] is False for h in heartbeats)
    Path('D:/gitdemo/Underbot/.publish-underbot/navigation/route-verification.json').write_text(json.dumps(result,indent=2))
    print(json.dumps(result),flush=True)
finally:node.destroy_node();rclpy.try_shutdown()
