import json, time
import numpy as np
from common import configure_ros
configure_ros(74)
import rclpy
from foxglove_msgs.msg import RawAudio
from sensor_msgs.msg import NavSatFix
from std_msgs.msg import Float32
from rclpy.qos import qos_profile_sensor_data
rclpy.init()
n = rclpy.create_node('check_audio_map')
s = {'audio_packets':0,'nonzero_samples':0,'max_rms':0,'latency_messages':0,'manual_location':False}
last=0
def audio(m):
 global last
 assert m.format=='pcm-s16' and m.sample_rate==48000 and m.number_of_channels==1
 assert len(m.data)==1920
 stamp=m.timestamp.sec*1000000000+m.timestamp.nanosec
 assert stamp>last
 last=stamp
 x=np.frombuffer(bytes(m.data),dtype='<i2').astype(float)
 s['audio_packets']+=1
 s['nonzero_samples']+=int(np.count_nonzero(x))
 s['max_rms']=max(s['max_rms'],float(np.sqrt(np.mean(x*x))/32768))
def location(m):
 assert m.header.frame_id=='MANUAL_PI_MARKER_NOT_GPS'
 assert -90 <= m.latitude <= 90 and -180 <= m.longitude <= 180
 s['manual_location']=True
def latency(m):
 assert 0<=m.data<=2100
 s['latency_messages']+=1
subs=[n.create_subscription(RawAudio,'/station/audio',audio,qos_profile_sensor_data),n.create_subscription(NavSatFix,'/station/manual_location',location,10),n.create_subscription(Float32,'/perception/emeet/latency_ms',latency,10)]
end=time.monotonic()+8
while time.monotonic()<end:rclpy.spin_once(n,timeout_sec=.1)
print(json.dumps(s))
assert s['audio_packets']>100 and s['nonzero_samples']>0
n.destroy_node()
rclpy.shutdown()
