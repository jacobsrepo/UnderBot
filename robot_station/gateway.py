"""ROS 2 station adapter. Hardware forwarding is explicitly opt-in."""
import json
import math
import time
import queue
import threading
from ai_backend import chat
from robot_brain import memory_snapshot, identity_answer, fetch_plan
from world_state import WorldState, visibility_answer
from navigation_core import navigation_intent
from navigation_language import candidate_request, interpret, describe_intent
import rclpy
from rclpy.node import Node
from geometry_msgs.msg import Twist
from std_msgs.msg import String
from rclpy.qos import qos_profile_sensor_data


def bounded_twist(msg, max_linear=0.2, max_angular=0.5):
    values = [msg.linear.x, msg.linear.y, msg.angular.z]
    if not all(math.isfinite(v) for v in values):
        return Twist()
    result = Twist()
    length = math.hypot(values[0], values[1])
    scale = min(1.0, max_linear / length) if length else 1.0
    result.linear.x, result.linear.y = values[0] * scale, values[1] * scale
    result.angular.z = max(-max_angular, min(max_angular, values[2]))
    return result


class StationGateway(Node):
    def __init__(self):
        super().__init__('underbot_station')
        self.declare_parameter('hardware_enabled', False)
        self.declare_parameter('mode', 'live')
        self.declare_parameter('command_timeout', 0.35)
        self.declare_parameter('ai_url', '')
        self.declare_parameter('ai_model', 'qwen2.5:1.5b')
        self.declare_parameter('memory_python', '')
        self.declare_parameter('memory_config', '')
        self.memory_python = self.get_parameter('memory_python').value
        self.memory_config = self.get_parameter('memory_config').value
        self.ai_url = self.get_parameter('ai_url').value
        self.ai_model = self.get_parameter('ai_model').value
        self.ai_busy = False
        self.ai_results = queue.Queue(maxsize=1)
        self.ai_state = 'configured; awaiting first request' if self.ai_url else 'not configured'
        self.enabled = self.get_parameter('hardware_enabled').value is True
        self.mode = self.get_parameter('mode').value
        if self.mode not in ('live', 'demo'):
            raise ValueError('mode must be live or demo')
        if self.mode == 'demo' and self.enabled:
            raise ValueError('Demo mode must never enable hardware')
        self.timeout = float(self.get_parameter('command_timeout').value)
        if not 0.1 <= self.timeout <= 0.5:
            raise ValueError('command_timeout must be 0.1–0.5 seconds')
        self.command = Twist()
        self.received = 0.0
        self.status = self.create_publisher(String, '/station/status', 10)
        self.response = self.create_publisher(String, '/station/ai/response', 10)
        self.plan = self.create_publisher(String, '/station/ai/plan', 10)
        self.world = WorldState()
        self.navigation = None
        self.navigation_at = 0.0
        self.command_epoch = 0
        self.nav_request = self.create_publisher(String, '/station/nav/request', 10) if self.mode == 'demo' else None
        self.create_subscription(String, '/station/nav/status', self.on_navigation, 10)
        self.create_subscription(String, '/station/nav/events', self.on_navigation_event, 10)
        self.world_pub = self.create_publisher(String, '/station/ai/world_state', 10)
        self.create_subscription(String, '/perception/emeet/objects', self.on_objects, qos_profile_sensor_data)
        # Only create a motor-output publisher when explicitly enabled.
        self.output = self.create_publisher(Twist, '/station/guarded_cmd_vel', 10) if self.enabled else None
        self.create_subscription(Twist, '/station/cmd_vel', self.on_command, 10)
        self.create_subscription(Twist, '/station/camera_cmd', self.on_camera, 10)
        self.create_subscription(String, '/station/comms/request', self.on_comms, 10)
        self.comms_state = 'adapter not connected'
        self.comms_at = 0.0
        self.create_subscription(String, '/station/comms/status', self.on_comms_status, 10)
        self.create_subscription(String, '/station/ai/request', self.on_chat, 10)
        self.last_request = 'none'
        self.create_timer(0.05, self.forward)
        self.create_timer(0.5, self.heartbeat)
        self.create_timer(0.1, self.drain_chat)

    def on_command(self, msg):
        self.command_epoch += 1
        self.command = bounded_twist(msg)
        self.received = time.monotonic()

    def on_objects(self, msg):
        try:
            self.world.update(json.loads(msg.data))
        except (ValueError, TypeError):
            return

    def on_navigation(self, msg):
        try:
            data=json.loads(msg.data)
            if data.get('mode')=='simulation' and data.get('hardware_enabled') is False:
                self.navigation=data;self.navigation_at=time.monotonic()
        except (ValueError,TypeError):
            return

    def on_navigation_event(self,msg):
        try:
            data=json.loads(msg.data)
            if self.mode!='demo' or data.get('mode')!='simulation' or not isinstance(data.get('id'),str):return
            if data.get('event') not in ('started','completed','rejected','cancelled','timed_out'):return
            self.response.publish(String(data=json.dumps({'id':data['id'],'ok':data['event'] not in ('rejected','timed_out'),
                'text':'Simulation '+data['event'].replace('_',' ')+': '+str(data.get('message',''))[:500],
                'final':True,'execution_event':True,'model':'simulation executor'})))
        except (ValueError,TypeError):return

    def on_camera(self, _msg):
        self.last_request = 'camera request received; no actuator adapter configured'

    def on_comms(self, msg):
        try:
            enabled = json.loads(msg.data)['enabled']
            if not isinstance(enabled, bool):
                return
            self.last_request = f'comms {"on" if enabled else "off"} requested'
        except (ValueError, KeyError, TypeError):
            return

    def on_comms_status(self, msg):
        try:
            state = json.loads(msg.data)['state']
            if isinstance(state, str):
                self.comms_state = state[:500]
                self.comms_at = time.monotonic()
        except (ValueError, KeyError, TypeError):
            return

    def on_chat(self, msg):
        try:
            request = json.loads(msg.data)
            if not isinstance(request.get('id'), str) or not isinstance(request.get('text'), str):
                return
            if not 1 <= len(request['id']) <= 128 or not 1 <= len(request['text'].strip()) <= 2000:
                return
            if request['text'].strip().lower().rstrip('.!') in ('stop','stop navigation','cancel','cancel navigation','stop moving') and self.nav_request:
                self.command_epoch+=1
                self.nav_request.publish(String(data=json.dumps({'action':'stop','request_id':request['id']})))
                self.reply(request['id'],True,'Stopping simulation and cancelling queued steps.');return
            if not self.ai_url or self.ai_busy:
                self.reply(request['id'], False, 'AI is busy; retry after the current reply.' if self.ai_busy else 'AI backend is not configured.')
                return
            self.ai_busy = True
            self.ai_state = 'generating'
            self.reply(request['id'], True, 'Checking robot memory and preparing a reply...', final=False)
            threading.Thread(target=self.run_chat, args=(request['id'], request['text'], self.command_epoch), daemon=True).start()
        except (ValueError, TypeError, AttributeError):
            return

    def reply(self, request_id, ok, text, final=True):
        self.response.publish(String(data=json.dumps({'id': request_id, 'ok': ok,
            'text': text, 'final': final, 'model': self.ai_model})))

    def run_chat(self, request_id, prompt, epoch=None):
        try:
            if epoch is None:epoch=self.command_epoch
            nav=self.navigation if time.monotonic()-self.navigation_at<3 else None
            parser_error=None
            try:
                intent=navigation_intent(prompt,nav.get('landmarks',{}) if nav else {})
            except ValueError as exc:
                intent=None;parser_error=str(exc)
                if any(marker in parser_error for marker in ('at most','cannot be replaced','one turn direction')):
                    self.ai_results.put((request_id,True,parser_error,None));return
            if not intent and candidate_request(prompt) and self.mode=='demo' and nav:
                try:
                    proposal=interpret(self.ai_url,self.ai_model,prompt,nav.get('landmarks',{}))
                except (ValueError,TypeError) as exc:
                    error=str(exc)
                    if 'distance with units' in error:answer='How many metres or centimetres should I move?'
                    elif 'estination' in error:answer='Which saved waypoint do you mean? Available: '+', '.join(nav.get('landmarks',{}))+'.'
                    elif 'turn amount' in error:answer='How many degrees should I turn, and in which direction?'
                    else:answer='I could not validate that instruction. Please specify a saved destination, a distance with units, or a turn angle.'
                    self.ai_results.put((request_id,True,answer,None));return
                if proposal['kind']=='clarify':
                    self.ai_results.put((request_id,True,proposal['message'] or 'Which saved destination or movement amount do you mean?',None));return
                intent=proposal['intent']
            if parser_error and not intent:
                self.ai_results.put((request_id,True,parser_error,None));return
            if intent:
                if self.mode!='demo' or not nav:
                    self.ai_results.put((request_id,True,'Navigation simulation is unavailable. Physical navigation is not connected.',None));return
                if intent['action']=='list_waypoints':
                    answer='Saved simulation waypoints (map metres):\n'+'\n'.join(f'{name}: {xy[0]:.2f}, {xy[1]:.2f}' for name,xy in nav.get('landmarks',{}).items())
                    self.ai_results.put((request_id,True,answer,None));return
                plan={'type':'navigation_simulation','request':intent,'hardware_executable':False,'epoch':epoch}
                self.ai_results.put((request_id,True,'Simulation plan: '+describe_intent(intent)+'. Sending it for map validation and execution.',plan));return
            memory = memory_snapshot(self.memory_python, self.memory_config)
            if not memory.get('available'):
                self.get_logger().warning('Memory lookup unavailable: ' + memory.get('error_code', 'not_configured_or_stale'))
            world = self.world.snapshot()
            answer = visibility_answer(prompt, memory, world)
            if answer is None:
                answer = identity_answer(prompt, memory)
            plan = fetch_plan(prompt, memory) if answer is None else None
            if plan:
                answer = 'Proposed plan only; I cannot execute it yet:\n' + '\n'.join(
                    f"{s['step']}. {s['action'].replace('_', ' ')}: {s['target']}" for s in plan['steps'])
                answer += '\nMissing: ' + '; '.join(plan['blockers']) + '.'
            if answer is None:
                answer = chat(self.ai_url, self.ai_model, prompt, self.mode,
                              context={'memory': memory, 'comms': self.comms_state,
                                       'world_state': world,
                                       'navigation_simulation': nav,
                                       'execution_enabled': False})
            result = (request_id, True, answer, plan)
        except Exception:
            result = (request_id, False, 'Qwen could not reply. Check that the Pi is online, Ollama is running, and the base SSH tunnel is connected; then retry.', None)
        self.ai_results.put(result)

    def drain_chat(self):
        try:
            result = self.ai_results.get_nowait()
        except queue.Empty:
            return
        self.ai_busy = False
        self.ai_state = 'ready' if result[1] else 'unavailable; retry to reconnect'
        if result[3] and result[3].get('type')=='navigation_simulation':
            if result[3].get('epoch')!=self.command_epoch or time.monotonic()-self.navigation_at>=3:
                result=(result[0],True,'This movement request was cancelled or the simulation connection expired; it was not executed.',None)
        self.reply(*result[:3])
        if result[3] and result[3].get('type')=='navigation_simulation' and self.nav_request:
            self.nav_request.publish(String(data=json.dumps({**result[3]['request'],'request_id':result[0]})))
        # Publish a correlated non-executable record for every request, clearing stale proposals.
        self.plan.publish(String(data=json.dumps({'id': result[0],
            'plan': result[3], 'executable': False})))

    def forward(self):
        if self.output:
            self.output.publish(self.command if time.monotonic() - self.received < self.timeout else Twist())

    def heartbeat(self):
        self.world_pub.publish(String(data=json.dumps(self.world.snapshot())))
        self.status.publish(String(data=json.dumps({
            'mode': self.mode, 'hardware_enabled': self.enabled,
            'comms': self.comms_state if time.monotonic() - self.comms_at < 3 else 'adapter not connected',
            'ai': f'{self.ai_model}: {self.ai_state}',
            'last_request': self.last_request,
        })))


def main():
    rclpy.init()
    node = StationGateway()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        if node.output:
            node.output.publish(Twist())
        node.destroy_node()
        rclpy.try_shutdown()


if __name__ == '__main__':
    main()
