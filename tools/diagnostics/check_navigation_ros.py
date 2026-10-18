"""Exercise chat → simulated navigation; no physical velocity publisher."""
import json,time,math
import rclpy
from std_msgs.msg import String
from nav_msgs.msg import Path
from sensor_msgs.msg import PointCloud2
rclpy.init();node=rclpy.create_node('underbot_navigation_check')
states=[];responses={};paths=[];clouds=[];heartbeats=[]
def reply(msg):
    d=json.loads(msg.data)
    if d.get('final',True) and not d.get('execution_event'):responses[d['id']]=d
node.create_subscription(String,'/station/nav/status',lambda m:states.append(json.loads(m.data)),10)
node.create_subscription(String,'/station/ai/response',reply,10)
node.create_subscription(String,'/station/status',lambda m:heartbeats.append(json.loads(m.data)),10)
node.create_subscription(Path,'/plan',lambda m:paths.append(len(m.poses)),10)
node.create_subscription(PointCloud2,'/navigation/pointcloud',lambda m:clouds.append(m.width),10)
pub=node.create_publisher(String,'/station/ai/request',10)
def until(predicate,seconds=20):
    end=time.monotonic()+seconds
    while not predicate() and time.monotonic()<end:rclpy.spin_once(node,timeout_sec=.1)
    assert predicate(),'Timed out waiting for navigation result'
def send(text):
    key='nav-check-'+str(time.time_ns());pub.publish(String(data=json.dumps({'id':key,'text':text})));until(lambda:key in responses)
    assert responses[key]['ok'];print(json.dumps({'question':text,'reply':responses[key]['text']}),flush=True)
try:
    until(lambda:states and pub.get_subscription_count())
    start=states[-1]['pose'][:2]
    send('go forward 1 metre');until(lambda:states[-1]['state']=='goal reached in simulation',25)
    assert math.dist(start,states[-1]['pose'][:2])>.75
    send('go to goal_a');until(lambda:states[-1]['path_points']>=2)
    print('A* path points:',states[-1]['path_points'],flush=True)
    send('stop navigation');until(lambda:states[-1]['state']=='stopped')
    send('go to 999, 999');until(lambda:states[-1]['state'].startswith('rejected:'))
    send('go to goal_a');until(lambda:states[-1]['path_points']>=2)
    assert clouds and max(clouds)>1000
    assert heartbeats and all(s['hardware_enabled'] is False for s in heartbeats)
    print(json.dumps({'passed':True,'cloud_points':max(clouds),'final_navigation':states[-1],'hardware_enabled':False}),flush=True)
finally:node.destroy_node();rclpy.try_shutdown()
