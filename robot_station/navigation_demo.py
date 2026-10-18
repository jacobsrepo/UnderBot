"""Public point-cloud map plus simulated pose, static A* and path following."""
import json,math,time
from pathlib import Path
import numpy as np
import rclpy
from rclpy.qos import QoSProfile,DurabilityPolicy
from geometry_msgs.msg import PoseStamped,Twist
from nav_msgs.msg import OccupancyGrid,Path as RosPath
from sensor_msgs.msg import PointCloud2,PointField
from std_msgs.msg import String
from visualization_msgs.msg import Marker
from demo import Demo
from navigation_core import plan_route,segment_is_free,route_length

ROOT=Path(__file__).resolve().parent

def navigation_data_dir(root=ROOT):
    """Prefer installed data; allow a fresh repository checkout to use its bundled map."""
    installed=root/'navigation-data'
    if all((installed/name).is_file() for name in ('map_metadata.json','demo_map.npz')):
        return installed
    bundled=root.parent/'navigation'
    if all((bundled/name).is_file() for name in ('map_metadata.json','demo_map.npz')):
        return bundled
    raise FileNotFoundError('Navigation data missing: expected navigation-data beside the station or the repository navigation folder')

class NavigationDemo(Demo):
    def __init__(self):
        data=navigation_data_dir()
        self.meta=json.loads((data/'map_metadata.json').read_text());arrays=np.load(data/'demo_map.npz')
        self.grid=arrays['grid'];self.cloud=arrays['cloud'];self.route=[];self.route_index=0;self.nav_status='idle';self.goal_xy=None
        self.pending_steps=[];self.turn_target=None;self.turn_start=None;self.reverse=False;self.planned_length=0.
        self.task_id=None;self.task_started=0.;self.step_started=0.;self.step_number=0;self.total_steps=0
        self.waypoint_file=data/'custom_waypoints.json'
        self.landmarks=dict(self.meta['landmarks'])
        if self.waypoint_file.exists():
            try:
                saved=json.loads(self.waypoint_file.read_text())
                for name,xy in saved.items():
                    if name not in self.landmarks and self.free_xy(*xy):self.landmarks[name]=xy
            except (ValueError,TypeError,AttributeError,OSError):pass
        super().__init__()
        self.x,self.y=self.meta['spawn'];self.yaw=0
        qos=QoSProfile(depth=1,durability=DurabilityPolicy.TRANSIENT_LOCAL)
        self.points=self.create_publisher(PointCloud2,'/navigation/pointcloud',qos)
        self.costmap=self.create_publisher(OccupancyGrid,'/navigation/costmap',qos)
        self.goal_pub=self.create_publisher(PoseStamped,'/navigation/goal',10)
        self.robot_pub=self.create_publisher(Marker,'/navigation/robot',10)
        self.nav_pub=self.create_publisher(String,'/station/nav/status',10)
        self.events=self.create_publisher(String,'/station/nav/events',10)
        self.create_subscription(String,'/station/nav/request',self.request,10)
        self.create_subscription(PoseStamped,'/station/nav/goal',self.clicked_goal,10)
        self.create_timer(.5,self.publish_status)
    def cell(self,x,y):return (math.floor((x+20)/self.meta['resolution']),math.floor((y+20)/self.meta['resolution']))
    def world_cell(self,c):return (-20+(c[0]+.5)*self.meta['resolution'],-20+(c[1]+.5)*self.meta['resolution'])
    def free_xy(self,x,y):
        if not all(math.isfinite(v) for v in [x,y]):return False
        cx,cy=self.cell(x,y);h,w=self.grid.shape
        return 0<=cx<w and 0<=cy<h and self.grid[cy,cx]==0
    def free_segment(self,a,b):
        r=self.meta['resolution']
        return segment_is_free(self.grid,((a[0]+20)/r,(a[1]+20)/r),((b[0]+20)/r,(b[1]+20)/r))
    def emit(self,event,message):
        if self.task_id and hasattr(self,'events'):
            self.events.publish(String(data=json.dumps({'mode':'simulation','id':self.task_id,'event':event,'message':message,'step':self.step_number,'total_steps':self.total_steps})))
    def cancel_motion(self,reason=None):
        if reason:self.emit('cancelled',reason)
        self.task_id=None
        self.route=[];self.pending_steps=[];self.turn_target=None;self.turn_start=None;self.reverse=False;self.command=Twist()
    def start_step(self,d):
        self.step_started=time.monotonic();self.step_number+=1
        self.reverse=False
        if d['action'] in ('forward','backward'):
            distance=float(d['distance'])
            if not math.isfinite(distance) or not 0<distance<=5:raise ValueError('Invalid distance')
            self.reverse=d['action']=='backward';signed=-distance if self.reverse else distance
            x=self.x+signed*math.cos(self.yaw);y=self.y+signed*math.sin(self.yaw)
            if not self.free_segment((self.x,self.y),(x,y)):raise ValueError('Straight segment intersects blocked or unknown space')
            self.route=[(self.x,self.y),(x,y)];self.route_index=0;self.goal_xy=(x,y);self.nav_status='following simulated '+d['action']+' segment'
            self.planned_length=distance
        elif d['action']=='goal':self.set_goal(*map(float,d['xy']))
        elif d['action']=='turn':
            degrees=float(d['degrees'])
            if not math.isfinite(degrees) or not 0<abs(degrees)<=360:raise ValueError('Invalid turn angle')
            self.turn_start=self.yaw;self.turn_target=self.yaw+math.radians(degrees);self.goal_xy=None
            self.nav_status='turning in simulation'
        else:raise ValueError('Unsupported sequence step')
    def set_goal(self,x,y):
        if not all(math.isfinite(v) for v in [x,y]):raise ValueError('Non-finite goal')
        self.route=plan_route(self.grid,(self.x,self.y),(x,y),self.meta['resolution'])
        self.planned_length=route_length(self.route)
        self.route_index=0;self.goal_xy=(x,y);self.nav_status='following simulated path'
    def request(self,msg):
        try:
            d=json.loads(msg.data)
            self.cancel_motion('Replaced by a new navigation request.')
            request_id=d.get('request_id')
            if request_id is not None and (not isinstance(request_id,str) or not 1<=len(request_id)<=128):raise ValueError('Invalid request ID')
            self.task_id=request_id;self.task_started=time.monotonic();self.step_number=0;self.total_steps=1
            if d['action']=='save_waypoint':
                name=d['name']
                import re
                if not isinstance(name,str) or not re.fullmatch(r'[a-z][a-z0-9_]{0,31}',name) or name in self.meta['landmarks']:raise ValueError('Invalid or reserved waypoint name')
                xy=d.get('xy') if d.get('xy') is not None else [self.x,self.y]
                if not self.free_xy(*xy):raise ValueError('Waypoint must be in known free space')
                if name not in self.landmarks and len(self.landmarks)>=52:raise ValueError('Maximum 50 custom waypoints')
                saved={k:v for k,v in self.landmarks.items() if k not in self.meta['landmarks']};saved[name]=xy
                temporary=self.waypoint_file.with_suffix('.tmp');temporary.write_text(json.dumps(saved));temporary.replace(self.waypoint_file)
                self.landmarks[name]=xy;self.nav_status='saved waypoint '+name
                self.emit('completed',self.nav_status);self.task_id=None
            elif d['action']=='list_waypoints':pass
            else:
                if d['action']=='stop':
                    self.nav_status='stopped';self.emit('completed','Motion stopped and remaining steps cancelled.');self.task_id=None
                else:
                    steps=d['steps'] if d['action']=='sequence' else [d]
                    if not isinstance(steps,list) or not 1<=len(steps)<=8:raise ValueError('Use one to eight steps')
                    self.total_steps=len(steps);self.pending_steps=list(steps);self.start_step(self.pending_steps.pop(0));self.emit('started',f'Executing {len(steps)} step(s).')
        except (ValueError,KeyError,TypeError,AttributeError,OSError) as exc:
            self.emit('rejected',str(exc))
            self.cancel_motion();self.nav_status='rejected: '+str(exc)
        self.world();self.publish_status()
    def clicked_goal(self,msg):
        if msg.header.frame_id!='map':self.cancel_motion('Invalid goal frame.');self.nav_status='rejected: goal must be in map frame';return
        self.request(String(data=json.dumps({'action':'goal','xy':[msg.pose.position.x,msg.pose.position.y]})))
    def on_command(self,msg):
        self.cancel_motion('Manual control or Cancel button interrupted this task.');self.nav_status='manual simulation control';super().on_command(msg)
    def tick(self):
        if (self.route or self.turn_target is not None or self.pending_steps) and (time.monotonic()-self.step_started>300 or time.monotonic()-self.task_started>900):
            self.emit('timed_out','Execution deadline exceeded.');self.cancel_motion();self.nav_status='timed out; stopped'
        if self.turn_target is not None:
            remaining=self.turn_target-self.yaw;cmd=Twist()
            if abs(remaining)<.001:self.turn_target=None;self.nav_status='turn completed in simulation'
            else:cmd.angular.z=max(-.8,min(.8,remaining/.05))
            self.command=cmd;self.received=time.monotonic()
        elif self.route:
            while self.route_index<len(self.route)-1 and math.dist((self.x,self.y),self.route[self.route_index])<.02:self.route_index+=1
            target=self.route[self.route_index];distance=math.dist((self.x,self.y),target)
            cmd=Twist()
            if self.route_index==len(self.route)-1 and distance<.02:self.route=[];self.nav_status='goal reached in simulation'
            else:
                angle=math.atan2(target[1]-self.y,target[0]-self.x)+(math.pi if self.reverse else 0)-self.yaw;angle=math.atan2(math.sin(angle),math.cos(angle))
                cmd.angular.z=max(-.8,min(.8,3*angle));cmd.linear.x=(-1 if self.reverse else 1)*min(.4,1.5*distance) if abs(angle)<.08 else 0
                next_yaw=self.yaw+cmd.angular.z*.05
                nx=self.x+cmd.linear.x*math.cos(next_yaw)*.05;ny=self.y+cmd.linear.x*math.sin(next_yaw)*.05
                if not self.free_segment((self.x,self.y),(nx,ny)):self.emit('rejected','Route became blocked.');self.cancel_motion();cmd=Twist();self.nav_status='blocked; stopped'
            self.command=cmd;self.received=time.monotonic()
        elif self.pending_steps:
            try:self.start_step(self.pending_steps.pop(0))
            except (ValueError,KeyError,TypeError) as exc:self.emit('rejected',str(exc));self.cancel_motion();self.nav_status='rejected: '+str(exc)
        if self.task_id and not self.route and self.turn_target is None and not self.pending_steps:
            self.emit('completed','All requested steps finished.');self.task_id=None
        super().tick()
    def world(self):
        if not hasattr(self,'points'):return
        grid=OccupancyGrid();grid.header.frame_id='map';grid.header.stamp=self.get_clock().now().to_msg()
        grid.info.resolution=self.meta['resolution'];grid.info.width=grid.info.height=200
        grid.info.origin.position.x=grid.info.origin.position.y=-20;grid.info.origin.orientation.w=1
        grid.data=self.grid.ravel().tolist();self.map.publish(grid);self.costmap.publish(grid)
        path=RosPath();path.header=grid.header
        for x,y in self.route:
            pose=PoseStamped();pose.header=grid.header;pose.pose.position.x=x;pose.pose.position.y=y
            i=len(path.poses);next_point=self.route[min(i+1,len(self.route)-1)]
            heading=math.atan2(next_point[1]-y,next_point[0]-x) if i<len(self.route)-1 else self.yaw
            pose.pose.orientation.z=math.sin(heading/2);pose.pose.orientation.w=math.cos(heading/2);path.poses.append(pose)
        self.plan.publish(path)
        cloud=PointCloud2();cloud.header=grid.header;cloud.height=1;cloud.width=len(self.cloud)
        cloud.fields=[PointField(name=n,offset=i*4,datatype=PointField.FLOAT32,count=1) for i,n in enumerate(['x','y','z'])]
        cloud.point_step=12;cloud.row_step=12*len(self.cloud);cloud.is_dense=True;cloud.data=self.cloud.astype('<f4').tobytes();self.points.publish(cloud)
        if self.goal_xy:
            pose=PoseStamped();pose.header=grid.header;pose.pose.position.x,pose.pose.position.y=self.goal_xy;pose.pose.orientation.w=1;self.goal_pub.publish(pose)
    def publish_status(self):
        robot=Marker();robot.header.frame_id='map';robot.header.stamp=self.get_clock().now().to_msg();robot.ns='underbot_simulation';robot.id=1;robot.type=Marker.CUBE;robot.action=Marker.ADD
        robot.pose.position.x=self.x;robot.pose.position.y=self.y;robot.pose.position.z=.2;robot.pose.orientation.z=math.sin(self.yaw/2);robot.pose.orientation.w=math.cos(self.yaw/2)
        robot.scale.x=robot.scale.y=.35;robot.scale.z=.4;robot.color.r=.1;robot.color.g=.8;robot.color.b=.9;robot.color.a=1.;self.robot_pub.publish(robot)
        robot.id=2;robot.type=Marker.ARROW;robot.pose.position.z=.5;robot.scale.x=.8;robot.scale.y=robot.scale.z=.1;robot.color.r=1.;robot.color.g=.8;robot.color.b=.1;self.robot_pub.publish(robot)
        turn_progress=math.degrees(self.yaw-self.turn_start) if self.turn_start is not None else None
        self.nav_pub.publish(String(data=json.dumps({'mode':'simulation','hardware_enabled':False,'state':self.nav_status,'pose':[self.x,self.y,self.yaw],'heading_degrees':math.degrees(self.yaw)%360,'turn_progress_degrees':turn_progress,'queued_steps':len(self.pending_steps),'goal':self.goal_xy,'goal_error_metres':math.dist((self.x,self.y),self.goal_xy) if self.goal_xy else None,'planned_length_metres':self.planned_length,'goal_tolerance_metres':.02,'planner':'8-neighbour A* with collision-checked line-of-sight shortcuts','path_points':len(self.route),'landmarks':self.landmarks,'map_source':self.meta['source'],'limitations':self.meta['limitations']})))

if __name__=='__main__':
    rclpy.init();node=NavigationDemo()
    try:rclpy.spin(node)
    except KeyboardInterrupt:pass
    finally:node.destroy_node();rclpy.try_shutdown()
