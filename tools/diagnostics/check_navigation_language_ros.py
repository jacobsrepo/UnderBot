"""End-to-end PC gateway -> Pi Qwen -> simulator -> correlated feedback."""
import json,math,time
import rclpy
from std_msgs.msg import String
from geometry_msgs.msg import Twist
rclpy.init();node=rclpy.create_node('underbot_language_execution_check')
states=[];responses={};events={};heartbeats=[]
def reply(msg):
    data=json.loads(msg.data)
    if data.get('execution_event'):events.setdefault(data['id'],[]).append(data)
    elif data.get('final',True):responses[data['id']]=data
node.create_subscription(String,'/station/nav/status',lambda m:states.append(json.loads(m.data)),10)
node.create_subscription(String,'/station/ai/response',reply,10)
node.create_subscription(String,'/station/status',lambda m:heartbeats.append(json.loads(m.data)),10)
pub=node.create_publisher(String,'/station/ai/request',10)
cancel=node.create_publisher(Twist,'/station/cmd_vel',10)
def until(predicate,seconds=100):
    end=time.monotonic()+seconds
    while not predicate() and time.monotonic()<end:rclpy.spin_once(node,timeout_sec=.1)
    assert predicate(),'Timed out: '+str(states[-1] if states else 'no state')
def enqueue(text):
    key='language-'+str(time.time_ns());pub.publish(String(data=json.dumps({'id':key,'text':text})));return key
def send(text):
    key=enqueue(text);until(lambda:key in responses);assert responses[key]['ok'],responses[key]
    print(json.dumps({'instruction':text,'reply':responses[key]['text']}),flush=True);return key
def completed(key):
    until(lambda:any('completed' in e['text'] for e in events.get(key,[])))
    assert not any('rejected' in e['text'] or 'timed out' in e['text'] for e in events[key]),events[key]
try:
    until(lambda:states and pub.get_subscription_count() and cancel.get_subscription_count())
    completed(send('stop navigation'))
    initial=states[-1]['pose'][:]
    key=send('Make one full clockwise revolution');completed(key)
    until(lambda:abs(states[-1]['pose'][2]-initial[2]+2*math.pi)<.02)
    assert math.dist(initial[:2],states[-1]['pose'][:2])<.001
    key=send('Back up fifty centimetres');completed(key)
    until(lambda:math.dist(initial[:2],states[-1]['pose'][:2])>.3)
    key=send('Turn around and return to start');completed(key)
    until(lambda:math.dist(states[-1]['pose'][:2],[.1,.1])<.15)
    for text in ['Move forward','Take me to the chair']:
        key=send(text)
        end=time.monotonic()+.6
        while time.monotonic()<end:rclpy.spin_once(node,timeout_sec=.1)
        assert not events.get(key),'Ambiguous instruction executed'
    key=send('go to 999, 999');until(lambda:any('rejected' in e['text'] for e in events.get(key,[])))
    # Cancel during model inference; late JSON must not start an action.
    before=states[-1]['pose'][:]
    key=enqueue('Make one full clockwise revolution')
    end=time.monotonic()+.5
    while time.monotonic()<end:rclpy.spin_once(node,timeout_sec=.1)
    cancel.publish(Twist())
    until(lambda:key in responses)
    assert 'cancelled' in responses[key]['text'],responses[key]
    assert not events.get(key),'Cancelled inference executed'
    assert math.dist(before,states[-1]['pose'])<.001
    assert heartbeats and all(h['hardware_enabled'] is False for h in heartbeats)
    completed(send('stop navigation'))
    print(json.dumps({'passed':True,'checks':['Pi model full clockwise revolution','centimetres conversion','multi-step named goal','clarification without execution','rejected goal feedback','cancelled delayed inference'],'hardware_enabled':False}),flush=True)
finally:node.destroy_node();rclpy.try_shutdown()
