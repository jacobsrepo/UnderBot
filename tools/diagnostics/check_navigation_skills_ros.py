"""Live simulation skill checks; no motor output, no model-generated commands."""
import json, math, time
import rclpy
from std_msgs.msg import String

rclpy.init()
node=rclpy.create_node('underbot_simulation_skills_check')
states=[];responses={};heartbeats=[]
def reply(msg):
    data=json.loads(msg.data)
    if data.get('final',True) and not data.get('execution_event'):responses[data['id']]=data
node.create_subscription(String,'/station/nav/status',lambda m:states.append(json.loads(m.data)),10)
node.create_subscription(String,'/station/ai/response',reply,10)
node.create_subscription(String,'/station/status',lambda m:heartbeats.append(json.loads(m.data)),10)
publisher=node.create_publisher(String,'/station/ai/request',10)
def until(predicate,seconds=25):
    end=time.monotonic()+seconds
    while not predicate() and time.monotonic()<end:rclpy.spin_once(node,timeout_sec=.1)
    assert predicate(),'Timed out: '+str(states[-1] if states else 'no status')
def send(text):
    key='skills-'+str(time.time_ns());publisher.publish(String(data=json.dumps({'id':key,'text':text})))
    until(lambda:key in responses)
    assert responses[key]['ok'],responses[key]
    print(json.dumps({'instruction':text,'reply':responses[key]['text']}),flush=True)
    return responses[key]['text']
try:
    until(lambda:states and publisher.get_subscription_count())
    send('save waypoint desk here');until(lambda:'desk' in states[-1]['landmarks'])
    start=states[-1]['pose'][:]
    send('please spin 360 degrees')
    until(lambda:states[-1]['state']=='turn completed in simulation')
    assert abs(states[-1]['pose'][2]-start[2]-2*math.pi)<.02
    assert math.dist(start[:2],states[-1]['pose'][:2])<.001
    print('Verified full 360-degree accumulated rotation without translation.',flush=True)
    send('turn right then go forward 0.5 metre then go backward 0.5 metre then turn left')
    until(lambda:states[-1]['queued_steps']>0)
    until(lambda:states[-1]['state']=='turn completed in simulation' and states[-1]['queued_steps']==0)
    assert abs(states[-1]['pose'][2]-start[2]-2*math.pi)<.04
    send('go to desk');until(lambda:states[-1]['state']=='goal reached in simulation')
    assert math.dist(start[:2],states[-1]['pose'][:2])<.15
    assert 'desk:' in send('list waypoints')
    send('spin 360 degrees then go forward 1 metre')
    until(lambda:states[-1]['state']=='turning in simulation' and states[-1]['queued_steps']==1)
    send('stop navigation');until(lambda:states[-1]['state']=='stopped' and states[-1]['queued_steps']==0)
    stopped=states[-1]['pose'][:]
    end=time.monotonic()+1
    while time.monotonic()<end:rclpy.spin_once(node,timeout_sec=.1)
    assert math.dist(stopped,states[-1]['pose'])<.001
    send('save waypoint invalid at 999, 999');until(lambda:states[-1]['state'].startswith('rejected:'))
    assert 'invalid' not in states[-1]['landmarks']
    assert heartbeats and all(s['hardware_enabled'] is False for s in heartbeats)
    send('stop navigation');until(lambda:states[-1]['state']=='stopped')
    print(json.dumps({'passed':True,'checks':['saved waypoint','full spin','four-step sequence','return to custom waypoint','list waypoints','cancel entire queue','reject invalid waypoint'],'hardware_enabled':False}),flush=True)
finally:
    node.destroy_node();rclpy.try_shutdown()
