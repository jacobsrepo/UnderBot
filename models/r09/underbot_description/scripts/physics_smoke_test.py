"""Optional independent engine smoke test: pip install numpy mujoco.

Imports the actual URDF, adds only engine/world/control configuration, and reports
what was tested. The two caster joints remain passive, with no hidden supports.
This is not a Gazebo or Isaac certification or a hardware test.
"""
from pathlib import Path
from datetime import datetime, timezone
import hashlib, json, math, sys, xml.etree.ElementTree as E
import numpy as np
import mujoco

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'validation';OUT.mkdir(exist_ok=True)
SOURCE=ROOT/'urdf/underbot.portable.urdf'
CASTERS=('caster_swivel_joint','caster_wheel_joint')
WHEELS=('left_wheel_joint','right_wheel_joint')
metadata={'engine':'MuJoCo '+mujoco.__version__,'urdf':'urdf/underbot.portable.urdf',
          'generated_at_utc':datetime.now(timezone.utc).isoformat()}
def failure_report(kind,error,trace):
    # Replace a stale PASS report even if an import/assertion fails mid-test.
    report=dict(metadata,result='FAIL',error=kind.__name__+': '+str(error),
                limitations=['Not a Gazebo/Isaac or hardware test'])
    for name in ('rest','drive','turn','motion','arm_tests'):
        if name in globals():report[name]=globals()[name]
    if 'data' in globals():
        report['failure_state']={'stage':globals().get('stage'),'qpos':data.qpos.tolist(),'qvel':data.qvel.tolist()}
    if 'stability_history' in globals():report['stability_history']=stability_history
    if 'self_contact_history' in globals():report['robot_contact_history_minimum_distance_m']=self_contact_history
    (OUT/'physics_smoke.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    (OUT/'physics_smoke.md').write_text('# Independent physics smoke test\n\n**FAIL**\n\n'+report['error']+'\n\nSource SHA-256: `'+metadata.get('urdf_sha256','unavailable')+'`\n',encoding='utf-8')
    sys.__excepthook__(kind,error,trace)
sys.excepthook=failure_report
def save(path,root):
    E.indent(root,space='  ');E.ElementTree(root).write(path,encoding='unicode')
source=SOURCE.read_bytes();metadata['urdf_sha256']=hashlib.sha256(source).hexdigest()
urdf=E.fromstring(source)
source_joints={j.get('name'):j for j in urdf.findall('joint')}
source_links={l.get('name'):l for l in urdf.findall('link')}
metadata['source_topology']={'link_count':len(source_links),'joint_count':len(source_joints),
    'joint_types':{kind:sum(j.get('type')==kind for j in source_joints.values()) for kind in ('fixed','continuous','revolute')}}
declared_mass=sum(float(l.find('inertial/mass').get('value')) for l in source_links.values() if l.find('inertial/mass') is not None)
metadata['declared_mass_kg']=declared_mass
mass_tolerance=max(1e-8,declared_mass*1e-10)
wheel_radii={n:float(source_links[source_joints[n].find('child').get('link')].find('collision/geometry/cylinder').get('radius')) for n in WHEELS}
assert min(wheel_radii.values())>0 and math.isclose(*wheel_radii.values(),rel_tol=1e-10)
wheel_origins={n:[float(v) for v in source_joints[n].find('origin').get('xyz').split()] for n in WHEELS}
track=abs(wheel_origins[WHEELS[0]][1]-wheel_origins[WHEELS[1]][1])
assert track>0
for n in CASTERS:assert source_joints[n].get('type')=='continuous', 'Missing passive continuous caster joint: '+n
allowed_supports={source_joints[n].find('child').get('link') for n in (*WHEELS,'caster_wheel_joint')}
metadata['rolling_geometry']={'wheel_radii_m':wheel_radii,'track_m':track,'expected_ground_bodies':sorted(allowed_supports),
                              'friction_sliding_torsional_rolling':[.8,.001,.0001]}
extra=E.SubElement(urdf,'mujoco')
E.SubElement(extra,'compiler',{'fusestatic':'false','discardvisual':'true'})
imported=mujoco.MjModel.from_xml_string(E.tostring(urdf,encoding='unicode'))
metadata['direct_import_mass_kg']=float(imported.body_mass.sum())
assert abs(metadata['direct_import_mass_kg']-declared_mass)<=mass_tolerance, 'Direct URDF import changed total mass'
converted=OUT/'underbot_imported.xml';mujoco.mj_saveLastXML(str(converted),imported)
scene=E.parse(converted).getroot()
# mj_saveLastXML rounds values; restore exact importer mass and principal inertia
# before adding the test world so the second compile preserves declared physics.
compiler=scene.find('compiler')
if compiler is None:compiler=E.SubElement(scene,'compiler')
compiler.set('fusestatic','false');compiler.set('inertiafromgeom','false')
precise=lambda values:' '.join(format(float(v),'.17g') for v in values)
for body in scene.iter('body'):
    bid=mujoco.mj_name2id(imported,mujoco.mjtObj.mjOBJ_BODY,body.get('name'))
    assert bid>=0
    if imported.body_mass[bid]<=0:continue
    node=body.find('inertial')
    if node is None:node=E.SubElement(body,'inertial')
    node.attrib.clear();node.attrib.update({'mass':precise([imported.body_mass[bid]]),
        'pos':precise(imported.body_ipos[bid]),'quat':precise(imported.body_iquat[bid]),
        'diaginertia':precise(imported.body_inertia[bid])})
E.SubElement(scene,'option',{'timestep':'.001','gravity':'0 0 -9.81','integrator':'implicitfast','iterations':'100'})
world=scene.find('worldbody');base=world.find("body[@name='base_link']")
assert base is not None, 'URDF root must not be fused into the static world'
base.insert(0,E.Element('freejoint',{'name':'floating_base'}))
E.SubElement(world,'geom',{'name':'ground','type':'plane','size':'3 3 .1','rgba':'.18 .21 .25 1','friction':'.8 .001 .0001'})
for body in world.iter('body'):
    if body.get('name') in allowed_supports:
        for geom in body.findall('geom'):
            geom.set('friction','.8 .001 .0001');geom.set('priority','1')
eq_nodes=scene.findall('equality')
assert len(eq_nodes)<=1, 'Importer produced multiple equality sections'
eq=eq_nodes[0] if eq_nodes else E.SubElement(scene,'equality')
mimics={};native_mimics=[];added_mimics=[]
for joint in urdf.findall('joint'):
    mimic=joint.find('mimic')
    if mimic is None:continue
    follower=joint.get('name');leader=mimic.get('joint');scale=float(mimic.get('multiplier','1'));offset=float(mimic.get('offset','0'))
    mimics[follower]={'leader':leader,'multiplier':scale,'offset':offset}
    existing=[node for node in eq.findall('joint') if node.get('joint1')==follower and node.get('joint2')==leader]
    assert len(existing)<=1, 'Duplicate imported mimic constraint: '+follower
    if existing:
        coeff=[float(v) for v in existing[0].get('polycoef','0 1 0 0 0').split()]
        assert np.allclose(coeff,[offset,scale,0,0,0],atol=1e-12,rtol=0), 'Imported mimic relation differs from URDF: '+follower
        # URDF mimic is an ideal kinematic relation. The importer's generic
        # 20 ms equality softness leaves appreciable jaw lag with passive joint
        # damping. Use one explicit 2 ms equality, not duplicate constraints.
        existing[0].set('solref','.002 1')
        native_mimics.append(follower)
    else:
        E.SubElement(eq,'joint',{'name':follower+'_coupling','joint1':follower,'joint2':leader,
            'polycoef':precise([offset,scale,0,0,0]),'solref':'.002 1'})
        added_mimics.append(follower)
assert len(mimics)==2, 'Expected two dependent jaw joints'
assert len(list(eq))==len(mimics) and all(node.tag=='joint' for node in eq), 'Unexpected imported equality constraints'
metadata['mimic_adapter']={'verified_native_relations':native_mimics,'added_relations':added_mimics,
    'total_constraint_count':len(list(eq)),'equality_solref_time_constant_s':.002,'equality_solref_damping_ratio':1.,
    'reason':'Approximate ideal URDF mimic with one explicit equality per jaw pair; generic native softness otherwise causes lag'}
act=E.SubElement(scene,'actuator');control=[]
for joint in urdf.findall('joint'):
    if joint.get('type') not in ('revolute','continuous') or joint.find('mimic') is not None:continue
    name=joint.get('name')
    if name in CASTERS:continue
    eff=joint.find('limit').get('effort')
    E.SubElement(act,'motor',{'name':name+'_motor','joint':name,'ctrllimited':'true','ctrlrange':'-'+eff+' '+eff,
                             'forcelimited':'true','forcerange':'-'+eff+' '+eff})
    control.append(name)
assert len(control)==14, 'Exactly 14 motors required; caster and mimic followers remain passive'
scene_path=OUT/'underbot_smoke.xml';save(scene_path,scene)
model=mujoco.MjModel.from_xml_path(str(scene_path));data=mujoco.MjData(model)
metadata['mass_kg']=float(model.body_mass.sum());metadata['mass_difference_kg']=metadata['mass_kg']-declared_mass
metadata['motor_count']=model.nu;metadata['actuated_joint_names']=control;metadata['passive_joint_names']=list(CASTERS)
metadata['degrees_of_freedom']={'floating_root':6,'actuated':len(control),'passive_caster':len(CASTERS),
    'dependent_jaw_coordinates':len(mimics),'joint_coupling_equalities':int(model.neq),
    'engine_velocity_coordinates':int(model.nv)}
assert abs(metadata['mass_difference_kg'])<=mass_tolerance, 'Final test model changed total URDF mass'
assert model.nu==14
assert model.nv==6+len(control)+len(CASTERS)+len(mimics) and model.neq==len(mimics), 'Unexpected hidden freedoms or constraints'
names={name:mujoco.mj_name2id(model,mujoco.mjtObj.mjOBJ_JOINT,name) for name in (*control,*CASTERS,*mimics)}
assert min(names.values())>=0
qadr={name:int(model.jnt_qposadr[j]) for name,j in names.items()}
vadr={name:int(model.jnt_dofadr[j]) for name,j in names.items()}
limits={j.get('name'):float(j.find('limit').get('effort')) for j in urdf.findall('joint') if j.find('limit') is not None}
position_targets={name:0. for name in control if 'wheel' not in name}
wheel_targets={name:0. for name in WHEELS}
# The passive caster must turn against static tyre contact friction. A weak
# velocity loop can stall at a correct, positive yaw sign even below effort caps.
# This feedback gain changes only the torque-capped test controller.
wheel_velocity_gain=3.
metadata['test_controller']={'wheel_velocity_gain_Nm_per_rad_s':wheel_velocity_gain,
    'arm_kp_Nm_per_rad':30.,'arm_kd_Nm_per_rad_s':1.,
    'wrist_pitch_kp_Nm_per_rad':30.,'wrist_pitch_kd_Nm_per_rad_s':.05,
    'wrist_roll_kp_Nm_per_rad':12.,'wrist_roll_kd_Nm_per_rad_s':0.,
    'gripper_kp_Nm_per_rad':8.,'gripper_kd_Nm_per_rad_s':.03}
peak_effort={name:0. for name in control};saturated={name:0 for name in control};step_count=0
ground_id=mujoco.mj_name2id(model,mujoco.mjtObj.mjOBJ_GEOM,'ground')
ground_history={};self_contact_history={};stability_history={};stage='initial'
def caster_state():
    return {n:{'angle_rad':float(data.qpos[qadr[n]]),'rate_rad_s':float(data.qvel[vadr[n]]),
               'actuator_torque_Nm':float(data.qfrc_actuator[vadr[n]])} for n in CASTERS}
def contacts():
    result=[]
    for c in data.contact:
        if ground_id not in (int(c.geom1),int(c.geom2)):continue
        other=int(c.geom2) if int(c.geom1)==ground_id else int(c.geom1)
        result.append({'body':mujoco.mj_id2name(model,mujoco.mjtObj.mjOBJ_BODY,int(model.geom_bodyid[other])),
                       'geom':mujoco.mj_id2name(model,mujoco.mjtObj.mjOBJ_GEOM,other),'distance_m':float(c.dist)})
    return result
def robot_contacts():
    result=[]
    for c in data.contact:
        if ground_id in (int(c.geom1),int(c.geom2)):continue
        bodies=[mujoco.mj_id2name(model,mujoco.mjtObj.mjOBJ_BODY,int(model.geom_bodyid[g])) for g in (int(c.geom1),int(c.geom2))]
        result.append({'bodies':bodies,'distance_m':float(c.dist)})
    return result
def support_geometry():
    # Derive both COM and the convex support polygon from the imported physics.
    # This contains no tower dimensions, battery orientation or mass constant.
    com=np.sum(model.body_mass[:,None]*data.xipos,axis=0)/model.body_mass.sum()
    points=sorted(set(tuple(float(v) for v in c.pos[:2]) for c in data.contact
                      if ground_id in (int(c.geom1),int(c.geom2))))
    def cross(o,a,b):return (a[0]-o[0])*(b[1]-o[1])-(a[1]-o[1])*(b[0]-o[0])
    lower=[];upper=[]
    for p in points:
        while len(lower)>=2 and cross(lower[-2],lower[-1],p)<=1e-12:lower.pop()
        lower.append(p)
    for p in reversed(points):
        while len(upper)>=2 and cross(upper[-2],upper[-1],p)<=1e-12:upper.pop()
        upper.append(p)
    hull=lower[:-1]+upper[:-1] if len(points)>1 else points
    distances=[]
    if len(hull)>=3:
        for a,b in zip(hull,hull[1:]+hull[:1]):
            distances.append(float(cross(a,b,com[:2])/math.hypot(b[0]-a[0],b[1]-a[1])))
    return {'center_of_mass_world_m':com.tolist(),'ground_support_polygon_xy_m':hull,
        'geometric_margin_m':min(distances) if distances else None,
        'interpretation':'COM projection margin; dynamic inertial loads are not included'}
def update():
    for i,name in enumerate(control):
        if 'wheel' in name:torque=wheel_velocity_gain*(wheel_targets[name]-data.qvel[vadr[name]])
        else:
            if 'gripper' in name:kp,kd=8.,.03
            elif 'wrist_roll' in name:kp,kd=12.,0.
            elif 'wrist_pitch' in name:kp,kd=30.,.05
            else:kp,kd=30.,1.
            torque=kp*(position_targets[name]-data.qpos[qadr[name]])-kd*data.qvel[vadr[name]]
        if abs(torque)>=limits[name]:saturated[name]+=1
        data.ctrl[i]=np.clip(torque,-limits[name],limits[name])
def advance(seconds):
    global step_count
    for _ in range(round(seconds/model.opt.timestep)):
        update();mujoco.mj_step(model,data)
        step_count+=1
        for i,n in enumerate(control):
            force=abs(float(data.actuator_force[i]));peak_effort[n]=max(peak_effort[n],force)
            assert force<=limits[n]+1e-9, 'Effort cap exceeded: '+n
        actual=contacts();bodies={c['body'] for c in actual}
        assert not (bodies-allowed_supports), 'Unexpected/hidden ground support in '+stage+': '+str(sorted(bodies-allowed_supports))
        assert all(c['distance_m']>-.005 for c in actual), 'Rolling contact penetrated ground by over 5 mm in '+stage
        record=ground_history.setdefault(stage,{'bodies':set(),'minimum_distance_m':0.})
        record['bodies'].update(bodies)
        if actual:record['minimum_distance_m']=min(record['minimum_distance_m'],min(c['distance_m'] for c in actual))
        for c in robot_contacts():
            assert c['distance_m']>-.005, 'Robot self-penetration exceeded 5 mm in '+stage+': '+str(c)
            pair=' / '.join(sorted(c['bodies']))
            prior=self_contact_history.setdefault(stage,{}).get(pair,0.)
            self_contact_history[stage][pair]=min(prior,c['distance_m'])
        assert all(abs(v['actuator_torque_Nm'])<1e-12 for v in caster_state().values()), 'Caster received actuator torque'
        if step_count%20==0:
            tilt=max(abs(v) for v in roll_pitch(data.qpos[3:7]))
            sample=support_geometry()
            record=stability_history.setdefault(stage,{'samples':0,'max_abs_roll_pitch_rad':0.,
                'minimum_geometric_support_margin_m':None,'samples_without_support_polygon':0})
            record['samples']+=1
            record['max_abs_roll_pitch_rad']=max(record['max_abs_roll_pitch_rad'],tilt)
            margin=sample['geometric_margin_m']
            if margin is None:record['samples_without_support_polygon']+=1
            elif record['minimum_geometric_support_margin_m'] is None:record['minimum_geometric_support_margin_m']=margin
            else:record['minimum_geometric_support_margin_m']=min(record['minimum_geometric_support_margin_m'],margin)
            assert tilt<.12, 'Body tilt exceeded 0.12 rad during '+stage
    assert np.all(np.isfinite(data.qpos)) and np.all(np.isfinite(data.qvel)), 'Nonfinite simulated state'
def roll_pitch(q):
    w,x,y,z=q
    return [math.atan2(2*(w*x+y*z),1-2*(x*x+y*y)),math.asin(np.clip(2*(w*y-z*x),-1,1))]
def yaw(q):
    w,x,y,z=q;return math.atan2(2*(w*z+x*y),1-2*(y*y+z*z))
data.qpos[2]=.002
mujoco.mj_forward(model,data)
gravity={name:float(data.qfrc_bias[vadr[name]]) for name in control if 'wheel' not in name}
stage='gravity_rest'
advance(2.)
rest={'base_xyz':data.qpos[:3].tolist(),'roll_pitch_rad':roll_pitch(data.qpos[3:7]),'contacts':int(data.ncon),
      'base_linear_speed_m_s':float(np.linalg.norm(data.qvel[:3])),
      'base_angular_speed_rad_s':float(np.linalg.norm(data.qvel[3:6])),
      'support_geometry':support_geometry(),
      'max_joint_position_error_rad':max(abs(data.qpos[qadr[n]]) for n in position_targets),
      'ground_contacts':contacts(),'passive_caster':caster_state()}
assert max(abs(v) for v in rest['roll_pitch_rad'])<.05, 'Robot did not rest upright'
assert abs(rest['base_xyz'][2])<.01, 'Resting ground datum drifted by over 10 mm'
assert rest['max_joint_position_error_rad']<.08, 'Torque-capped joints did not hold the folded pose'
assert {c['body'] for c in rest['ground_contacts']}==allowed_supports, 'Not all three intended rolling bodies support the resting robot'
assert rest['base_linear_speed_m_s']<.01 and rest['base_angular_speed_rad_s']<.1, 'Resting base did not settle'
assert rest['support_geometry']['geometric_margin_m'] is not None and rest['support_geometry']['geometric_margin_m']>.01, 'Resting COM has under 10 mm margin inside actual ground support polygon'
start=data.qpos[:3].copy()
stage='forward_drive'
for k in range(20):
    speed=.060*(k+1)/20
    wheel_targets={n:speed/wheel_radii[n] for n in WHEELS};advance(.05)
advance(1.)
drive={'translation_m':(data.qpos[:3]-start).tolist(),'roll_pitch_rad':roll_pitch(data.qpos[3:7]),
       'support_geometry':support_geometry(),
       'command_wheel_speed_rad_s':dict(wheel_targets),
       'final_wheel_speed_rad_s':{n:float(data.qvel[vadr[n]]) for n in wheel_targets},
       'ground_contacts':contacts(),'passive_caster':caster_state()}
assert drive['translation_m'][0]>.02, 'Equal positive wheel commands did not move forward'
assert max(abs(v) for v in drive['roll_pitch_rad'])<.1, 'Excessive body tilt during gentle drive'
for k in range(20):
    wheel_targets={n:.060*(19-k)/20/wheel_radii[n] for n in WHEELS};advance(.025)
advance(.3)
start_yaw=yaw(data.qpos[3:7])
stage='positive_yaw_turn'
for k in range(20):
    angular=.25*(k+1)/20
    wheel_targets={WHEELS[0]:-angular*track/2/wheel_radii[WHEELS[0]],WHEELS[1]:angular*track/2/wheel_radii[WHEELS[1]]}
    advance(.025)
advance(1.)
turn_transient={'yaw_change_rad':yaw(data.qpos[3:7])-start_yaw,'passive_caster':caster_state()}
# Allow the passive caster to align; retain the initial lag in the report.
advance(3.)
delta=yaw(data.qpos[3:7])-start_yaw
turn={'yaw_change_rad':math.atan2(math.sin(delta),math.cos(delta)),'roll_pitch_rad':roll_pitch(data.qpos[3:7]),
      'support_geometry':support_geometry(),
      'command_wheel_speed_rad_s':dict(wheel_targets),'command_yaw_rate_rad_s':.25,
      'ramp_duration_s':.5,'constant_command_duration_s':4.,'initial_1_5_s_transient':turn_transient,
      'final_wheel_speed_rad_s':{n:float(data.qvel[vadr[n]]) for n in WHEELS},
      'ground_contacts':contacts(),'passive_caster':caster_state()}
assert turn['yaw_change_rad']>.15, 'Opposite wheel commands did not produce a useful turn with expected sign'
assert max(abs(v) for v in turn['roll_pitch_rad'])<.1, 'Excessive body tilt during gentle turn'
for k in range(20):
    angular=.25*(19-k)/20
    wheel_targets={WHEELS[0]:-angular*track/2/wheel_radii[WHEELS[0]],WHEELS[1]:angular*track/2/wheel_radii[WHEELS[1]]}
    advance(.025)
advance(.3)
arm_tests={}
for suffix in ('arm_base_joint','shoulder_joint','elbow_joint','wrist_pitch_joint','wrist_roll_joint'):
    stage='arm_motion_'+suffix
    pair=[s+'_'+suffix for s in ('left','right')]
    before={n:float(data.qpos[qadr[n]]) for n in pair};targets={}
    for n in pair:
        limit=source_joints[n].find('limit');lo,hi=float(limit.get('lower')),float(limit.get('upper'))
        target=min(.1,.4*hi) if hi>.01 else max(-.1,.4*lo)
        assert lo<=target<=hi and abs(target)>.001
        position_targets[n]=target;targets[n]=target
    advance(.8)
    after={n:float(data.qpos[qadr[n]]) for n in pair}
    arm_tests[suffix]={'targets_rad':targets,'before_rad':before,'after_rad':after,
        'change_rad':{n:after[n]-before[n] for n in pair},
        'tracking_error_rad':{n:targets[n]-after[n] for n in pair},
        'final_speed_rad_s':{n:float(data.qvel[vadr[n]]) for n in pair},
        'support_geometry':support_geometry(),
        'robot_contacts':robot_contacts(),'passive_caster':caster_state()}
    for n in pair:
        assert (after[n]-before[n])*targets[n]>.5*targets[n]**2, 'Joint did not achieve half the intended change: '+n
        assert abs(targets[n]-after[n])<.04, 'Joint command tracking error exceeded 0.04 rad: '+n
        assert abs(data.qvel[vadr[n]])<.2, 'Joint did not settle below 0.2 rad/s: '+n
        position_targets[n]=0.
    advance(.35)
stage='gripper_motion'
for n in position_targets:
    if 'gripper_left' in n:position_targets[n]=min(.3,float(source_joints[n].find('limit').get('upper'))*.5)
advance(1.)
motion={'targets_rad':dict(position_targets),
    'support_geometry':support_geometry(),
    'position_rad':{n:float(data.qpos[qadr[n]]) for n in position_targets},
    'final_speed_rad_s':{n:float(data.qvel[vadr[n]]) for n in position_targets},
    'mimic_error_rad':{},'robot_contacts':robot_contacts(),'passive_caster':caster_state()}
for follower,relation in mimics.items():
    leader=relation['leader']
    motion['mimic_error_rad'][follower]=float(data.qpos[qadr[follower]]-relation['offset']-relation['multiplier']*data.qpos[qadr[leader]])
    assert data.qpos[qadr[leader]]>.1, 'Gripper did not open: '+leader
    assert abs(position_targets[leader]-data.qpos[qadr[leader]])<.03, 'Gripper command tracking error exceeded 0.03 rad: '+leader
    assert abs(data.qvel[vadr[leader]])<.2, 'Gripper did not settle below 0.2 rad/s: '+leader
assert max(abs(v) for v in motion['mimic_error_rad'].values())<.01, 'Gripper coupling error excessive'
report={**metadata,'result':'PASS',
    'tests':['URDF importer with retained declared inertia','floating base under gravity','2 seconds upright rest',
        'settled base / resting COM at least 10 mm inside contact-derived support polygon',
        'gentle forward drive / same wheel sign','positive yaw turn / opposite wheel signs',
        'all ten positioning joints / torque-capped small commands','both grippers / mimic equality',
        'two passive caster joints / high sliding friction rolling contacts','mass preservation / no hidden supports'],
    'mass_kg':float(model.body_mass.sum()),'gravity_joint_torque_Nm':gravity,
    'rest':rest,'drive':drive,'turn':turn,'arm_motion_tests':arm_tests,'arm_and_gripper':motion,
    'dependent_joints':mimics,
    'actuator_effort':{'declared_limits_Nm':{n:limits[n] for n in control},'observed_peak_abs_Nm':peak_effort,
                       'saturated_steps':saturated,'simulated_steps':step_count},
    'ground_contact_history':{n:{'bodies':sorted(v['bodies']),'minimum_distance_m':v['minimum_distance_m']} for n,v in ground_history.items()},
    'robot_contact_history_minimum_distance_m':self_contact_history,
    'stability_history':stability_history,
    'no_hidden_supports':{'base_attachment':'freejoint','added_world_geometry':['ground'],
                          'equality_constraints':'two jaw couplings only','allowed_ground_bodies':sorted(allowed_supports),
                          'unexpected_ground_bodies':[]},
    'adapter_changes':['retain static bodies while importing','add mobile-root freejoint','add ground/gravity',
        'verify native jaw mimic equalities; add only absent relations; set explicit 2 ms equality time constant',
        'torque-capped test motors with external PD',
        'preserve exact importer mass/inertia across saved-MJCF numeric rounding',
        'proposed high sliding and low rolling friction for wheels; caster remains passive'],
    'limitations':['Not a Gazebo/Isaac/RViz runtime test','Hardware dimensions, mass and actuator values remain estimates',
        'Gentle no-load motion only; not a payload or exhaustive self-collision test',
        'MuJoCo default parent-child collision filtering applies',
        'Passive caster alignment produces turn tracking lag; wheel commands are not perfectly achieved',
        'Proposed caster mechanics/friction and actuator gains are not calibrated hardware data']}
(OUT/'physics_smoke.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
text=['# Independent physics smoke test','',f"PASS — MuJoCo {mujoco.__version__} imported the actual portable URDF.",'',
    f"Source SHA-256: `{report['urdf_sha256']}`.",
    f"Declared / imported mass: {declared_mass:.9f} / {report['mass_kg']:.9f} kg (estimated hardware inputs).",
    'Motors: 14. Caster swivel and rolling joints are passive; all recorded ground contacts belong to the three intended rolling bodies.',
    f"Rest tilt: {np.degrees(rest['roll_pitch_rad']).tolist()} degrees; contacts: {rest['contacts']}.",
    f"Resting COM: {rest['support_geometry']['center_of_mass_world_m']} m in world coordinates; margin inside the actual ground support polygon: {rest['support_geometry']['geometric_margin_m']:.4f} m.",
    f"Gentle forward translation: {drive['translation_m'][0]:.4f} m.",
    f"Positive turn: {turn['yaw_change_rad']:.4f} rad.",
    f"Caster alignment transient: {turn['initial_1_5_s_transient']['yaw_change_rad']:.4f} rad in the first 1.5 s. Final turn follows a 0.5 s ramp and 4 s hold at a commanded 0.25 rad/s; this is a sign and stability check, not accurate velocity tracking.",
    f"Maximum jaw-coupling error: {max(abs(v) for v in motion['mimic_error_rad'].values()):.6f} rad.",'',
    '| Commanded joint (both arms) | Target rad | Left / right achieved rad | Maximum final speed rad/s |',
    '|---|---:|---:|---:|',
    *[f"| {suffix} | {next(iter(item['targets_rad'].values())):.3f} | {' / '.join(f'{v:.6f}' for v in item['after_rad'].values())} | {max(abs(v) for v in item['final_speed_rad_s'].values()):.6f} |" for suffix,item in arm_tests.items()],
    '',
    'The adapter adds the ground, floating root and test motors. It verifies native jaw mimic constraints, only adds a relation if the importer omitted it, and uses an explicit 2 ms equality time constant for the ideal jaw coupling. It preserves the URDF mass, inertia and collision model. See physics_smoke.json for passive caster angles/rates, contact history, observed effort caps and exact configuration. The generated MJCF is a reproducible test scene, not an Isaac or Gazebo profile.','',
    'These tests validate import, numerical behavior and motion signs for this estimated model. They do not measure the real robot or prove payload capability, full-range collision freedom or compatibility with other engines.']
(OUT/'physics_smoke.md').write_text('\n'.join(text)+'\n',encoding='utf-8')
print(json.dumps({'result':'PASS','urdf_sha256':report['urdf_sha256'],'mass_kg':report['mass_kg'],
                  'motor_count':model.nu,'forward_m':drive['translation_m'][0],'yaw_rad':turn['yaw_change_rad'],
                  'passive_caster':caster_state(),'mimic':motion['mimic_error_rad']}))
