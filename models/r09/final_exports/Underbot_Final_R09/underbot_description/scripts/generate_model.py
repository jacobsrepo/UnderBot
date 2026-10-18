"""Rebuild the R08 WR141E geometry, STL visuals, portable URDF and modular Xacro.

Python 3 + numpy. Dimensions use SI. Estimated hardware values are deliberate,
documented inputs; this generator does not turn them into measurements.
"""
from pathlib import Path
import json, math, struct, copy, xml.etree.ElementTree as E
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
for folder in ('urdf', 'meshes', 'config', 'docs', 'cad', 'validation'):
    (ROOT / folder).mkdir(parents=True, exist_ok=True)
PARAMS = ROOT / 'config/model_parameters.json'
defaults = {'revision': 'R08 WR141E / 200mm tower / stripped Kinect reservation', 'units': 'm, kg, s, rad, kg*m^2', 'base_length': 0.558, 'base_width': 0.404, 'base_height': 0.205, 'stock_base_mass': 9.1, 'frame_width': 0.2, 'frame_depth': 0.2, 'frame_center_x': -0.07, 'post_size': 0.02, 'post_length': 0.5, 'post_bottom': 0.205, 'width_rail_length': 0.16, 'depth_rail_length': 0.16, 'ring_bottoms': [0.205, 0.48, 0.555, 0.685], 'shelf_thickness': 0.003, 'panel_thickness': 0.002, 'panel_bottom': 0.225, 'panel_top': 0.685, 'camera_center': [-0.005, 0, 0.635], 'camera_optical_offset': [0.034, 0.06925, 0.0065], 'camera_aperture_half_width': 0.078, 'camera_aperture_bottom': 0.603, 'camera_aperture_top': 0.6625, 'arm_root_z': 0.545, 'arm_root_y': 0.108, 'shoulder_offset': 0.04, 'upper_arm_length': 0.105, 'forearm_length': 0.09, 'wrist_length': 0.045, 'hand_length': 0.025, 'finger_length': 0.05, 'shoulder_zero_pitch': -2.6179938779914944, 'elbow_zero_pitch': 1.0471975511965976, 'wrist_zero_pitch': -1.0471975511965976, 'arm_base_range': 0.7853981633974483, 'shoulder_range': 0.3490658503988659, 'elbow_range': 0.3490658503988659, 'wrist_pitch_range': 0.5235987755982988, 'wheel_radius': 0.0925, 'wheel_width': 0.05, 'wheel_x': -0.18, 'wheel_half_separation': 0.177, 'wheel_mass': 0.75, 'retained_chassis_mass': 7.35, 'caster_radius': 0.04, 'caster_width': 0.04, 'caster_swivel_xyz': [0.215, 0, 0.11], 'caster_wheel_xyz': [-0.02, 0, -0.07], 'caster_mass': 0.1, 'caster_fork_mass': 0.15, 'noco_mass': 1.9, 'kinect_mass': 0.97, 'lidar_mass': 0.15, 't_slot_kg_per_m': 0.4, 'v_slot_kg_per_m': 0.4627, 'plastic_density': 1050.0, 'polycarbonate_density': 1200.0, 'aluminium_density': 2700.0, 'arm_effort': 1.0, 'arm_speed': 1.0, 'wheel_effort': 2.5, 'wheel_speed': 4.0, 'jaw_effort': 0.3, 'status': {'published_envelopes': ['WR141E558x404x205', 'stock base9.1kg with battery baseline', 'GB70 body222x99x69; installation222x152x70'], 'user_stock': ['20mm posts500mm x4', '20mm rails200mm x16; cut each to160mm for200mm outside frame'], 'sketch_proposals': ['200x200mm outside frame and floor blanks, 20mm corner reliefs', '2mm external flat covers; 204x204mm covered envelope around 200x200mm frame/floors', 'ring bottoms205/480/555/685mm', 'GB70 upright222mm high', 'bare Kinect components inside tower; layout unmeasured', 'mounting datum205mm', 'frame centre rearward70mm', 'closed doors'], 'unmeasured_estimates': ['wheel and caster geometry/mass', 'all arm pivots/lengths/limits/zeros', 'installed masses and mass distribution', 'actuator torque/speed', 'camera optical datum', 'plastic grade/thickness', 'LiDAR/compute/converter exact models', 'stripped Kinect PCB/optics/cooling/wiring layout and installed mass; .97kg allocation retained']}, 'floor_width': 0.2, 'floor_depth': 0.2, 'camera_packaging': 'Bare electronics reservation; not measured Kinect hardware', 'camera_module_collision_size': [0.07, 0.156, 0.056], 'camera_module_collision_xyz': [-0.001, 0, -0.0035], 'covered_body_width': 0.204, 'covered_body_depth': 0.204}
if not PARAMS.exists():
    PARAMS.write_text(json.dumps(defaults, indent=2), encoding='utf-8')
P = json.loads(PARAMS.read_text(encoding='utf-8'))
pi = math.pi
BLACK = ('matte_black', [.045, .050, .055, 1])
METAL = ('aluminium', [.62, .68, .72, 1])
DARK = ('servo_black', [.075, .085, .095, 1])
GREEN = ('pcb_green', [.10, .32, .23, 1])
BLUE = ('roof_blue', [.07, .15, .23, 1])
CLEAR = ('polycarbonate', [.38, .55, .60, .5])
ORANGE = ('worx_orange', [.96, .22, .015, 1])
RED = ('control_red', [.65, .015, .015, 1])

def vec(v): return np.array(v, dtype=float)
def rot(rpy):
    r,p,y = rpy
    cr,sr,cp,sp,cy,sy = math.cos(r),math.sin(r),math.cos(p),math.sin(p),math.cos(y),math.sin(y)
    return np.array([[cy*cp,cy*sp*sr-sy*cr,cy*sp*cr+sy*sr],
                     [sy*cp,sy*sp*sr+cy*cr,sy*sp*cr-cy*sr],[-sp,cp*sr,cp*cr]])
def fmt(v): return ' '.join(f'{float(x):.12g}' for x in v)
def save_xml(path, el):
    E.indent(el, space='  ')
    Path(path).write_text('<?xml version="1.0"?>\n'+E.tostring(el,encoding='unicode')+'\n', encoding='utf-8')

def box_tri(size):
    a,b,c = vec(size)/2
    v = np.array([[-a,-b,-c],[a,-b,-c],[a,b,-c],[-a,b,-c],[-a,-b,c],[a,-b,c],[a,b,c],[-a,b,c]])
    ids = [(0,2,1),(0,3,2),(4,5,6),(4,6,7),(0,1,5),(0,5,4),(1,2,6),(1,6,5),(2,3,7),(2,7,6),(3,0,4),(3,4,7)]
    return v[np.array(ids)]
def cyl_tri(radius, length, n=48):
    ts=[]
    for i in range(n):
        a,b=2*pi*i/n,2*pi*(i+1)/n
        p=np.array([radius*math.cos(a),radius*math.sin(a),-length/2])
        q=np.array([radius*math.cos(b),radius*math.sin(b),-length/2])
        pp=p+[0,0,length];qq=q+[0,0,length]
        ts.extend([[p,q,qq],[p,qq,pp],[[0,0,-length/2],q,p],[[0,0,length/2],pp,qq]])
    return np.array(ts)
def sphere_tri(radius, n=32, bands=16):
    ts=[]
    def pt(i,j):
        t=pi*i/bands;a=2*pi*j/n
        return np.array([radius*math.sin(t)*math.cos(a),radius*math.sin(t)*math.sin(a),radius*math.cos(t)])
    for i in range(bands):
        for j in range(n):
            a,b,c,d=pt(i,j),pt(i+1,j),pt(i+1,j+1),pt(i,j+1)
            if i:ts.append([a,b,d])
            if i<bands-1:ts.append([b,c,d])
    return np.array(ts)

# Simple concave 2020 section with straight slot mouths; actual supplier section
# is unspecified. Effective mass comes from linear stock mass, not solid aluminium.
PROFILE = [(-.010,-.010),(-.003,-.010),(-.003,-.007),(.003,-.007),(.003,-.010),(.010,-.010),
           (.010,-.003),(.007,-.003),(.007,.003),(.010,.003),(.010,.010),(.003,.010),
           (.003,.007),(-.003,.007),(-.003,.010),(-.010,.010),(-.010,.003),(-.007,.003),
           (-.007,-.003),(-.010,-.003)]
def earclip(poly):
    ids=list(range(len(poly)));tri=[];v=np.array(poly)
    def cross(a,b,c):
        u,v=b-a,c-a
        return u[0]*v[1]-u[1]*v[0]
    def inside(q,a,b,c):return all(x>=-1e-14 for x in (cross(a,b,q),cross(b,c,q),cross(c,a,q)))
    while len(ids)>3:
        for k,b in enumerate(ids):
            a,c=ids[k-1],ids[(k+1)%len(ids)]
            if cross(v[a],v[b],v[c])>1e-14 and not any(inside(v[q],v[a],v[b],v[c]) for q in ids if q not in (a,b,c)):
                tri.append((a,b,c));ids.pop(k);break
        else:raise ValueError('Cannot triangulate profile')
    return tri+[tuple(ids)]
def extrusion_tri(length):
    v=np.array([[x,y,z] for z in (-length/2,length/2) for x,y in PROFILE]);n=len(PROFILE);ts=[]
    for a,b,c in earclip(PROFILE):ts.extend([v[[c,b,a]],v[[a+n,b+n,c+n]]])
    for i in range(n):
        j=(i+1)%n;ts.extend([v[[i,j,j+n]],v[[i,j+n,i+n]]])
    return np.array(ts)
def stl(path,tri):
    with open(path,'wb') as f:
        f.write(b'Underbot R08 SI metres - estimated hardware'.ljust(80,b' '));f.write(struct.pack('<I',len(tri)))
        for t in tri:
            n=np.cross(t[1]-t[0],t[2]-t[0]);n/=np.linalg.norm(n)
            f.write(struct.pack('<12fH',*n,*t.flatten(),0))

links={};joints=[]
def link(name):links[name]={'name':name,'parts':[],'collisions':[]};return name
def part(l,name,kind,size,xyz=(0,0,0),rpy=(0,0,0),color=METAL,mass=0):
    d={'name':name,'kind':kind,'size':list(size),'xyz':list(xyz),'rpy':list(rpy),'material':color[0],'rgba':color[1],'mass':mass}
    links[l]['parts'].append(d);return d
def box(l,n,s,x=(0,0,0),r=(0,0,0),c=METAL,m=0):return part(l,n,'box',s,x,r,c,m)
def cyl(l,n,rad,h,x=(0,0,0),r=(0,0,0),c=METAL,m=0):return part(l,n,'cylinder',[rad,h],x,r,c,m)
def collision(l,n,kind,size,xyz=(0,0,0),rpy=(0,0,0)):
    links[l]['collisions'].append({'name':n,'kind':kind,'size':list(size),'xyz':list(xyz),'rpy':list(rpy)})
def joint(n,parent,child,kind='fixed',xyz=(0,0,0),rpy=(0,0,0),axis=(0,0,1),limits=None,mimic=None):
    joints.append({'name':n,'parent':parent,'child':child,'type':kind,'xyz':list(xyz),'rpy':list(rpy),'axis':list(axis),'limits':limits,'mimic':mimic})

def polygon_properties(poly):
    p=np.asarray(poly,dtype=float);q=np.roll(p,-1,axis=0)
    cross=p[:,0]*q[:,1]-q[:,0]*p[:,1];area=cross.sum()/2
    if area<=0:raise ValueError('Prism polygon must be counterclockwise')
    center=((p+q)*cross[:,None]).sum(axis=0)/(6*area)
    xx=((p[:,0]**2+p[:,0]*q[:,0]+q[:,0]**2)*cross).sum()/12-area*center[0]**2
    yy=((p[:,1]**2+p[:,1]*q[:,1]+q[:,1]**2)*cross).sum()/12-area*center[1]**2
    xy=((2*p[:,0]*p[:,1]+p[:,0]*q[:,1]+q[:,0]*p[:,1]+2*q[:,0]*q[:,1])*cross).sum()/24-area*center[0]*center[1]
    return area,center,xx,yy,xy

def prism(l,name,poly,height,xyz=(0,0,0),color=METAL,mass=0):
    poly=np.asarray(poly,dtype=float)
    if np.sum(poly[:,0]*np.roll(poly[:,1],-1)-np.roll(poly[:,0],-1)*poly[:,1])<0:poly=poly[::-1]
    d=part(l,name,'prism',[*np.ptp(poly,axis=0),height],xyz,color=color,mass=mass)
    d['polygon']=poly.tolist();return d

def prism_tri(poly,height):
    v=np.array([[x,y,z] for z in (-height/2,height/2) for x,y in poly]);n=len(poly);ts=[]
    for a,b,c in earclip(poly):ts.extend([v[[c,b,a]],v[[a+n,b+n,c+n]]])
    for i in range(n):
        j=(i+1)%n;ts.extend([v[[i,j,j+n]],v[[i,j+n,i+n]]])
    return np.asarray(ts)

def mass_center(d):
    local=np.zeros(3)
    if d['kind']=='prism':local[:2]=polygon_properties(d['polygon'])[1]
    return vec(d['xyz'])+rot(d['rpy'])@local

def inertia_of(d):
    m=d['mass'];s=d['size'];kind=d['kind']
    if kind=='prism':
        area,center,xx,yy,xy=polygon_properties(d['polygon']);h=s[2]
        tensor=m*np.array([[yy/area+h*h/12,-xy/area,0],[-xy/area,xx/area+h*h/12,0],[0,0,(xx+yy)/area]])
        R=rot(d['rpy']);return R@tensor@R.T
    if kind=='box':x,y,z=s;diag=[m*(y*y+z*z)/12,m*(x*x+z*z)/12,m*(x*x+y*y)/12]
    elif kind=='cylinder':r,h=s;diag=[m*(3*r*r+h*h)/12]*2+[m*r*r/2]
    elif kind=='sphere':diag=[.4*m*s[0]**2]*3
    elif kind=='extrusion':
        # Effective hollow section with outer20 and inner14 mm for mass distribution.
        h=s[0];q=(.020**4-.014**4)/(12*(.020**2-.014**2));diag=[m*(q+h*h/12)]*2+[2*m*q]
    R=rot(d['rpy']);return R@np.diag(diag)@R.T
def inertial(l):
    ps=[p for p in links[l]['parts'] if p['mass']>0];m=sum(p['mass'] for p in ps)
    if not m:return None
    com=sum((p['mass']*mass_center(p) for p in ps),np.zeros(3))/m
    I=np.zeros((3,3))
    for p in ps:
        d=mass_center(p)-com;I+=inertia_of(p)+p['mass']*(np.dot(d,d)*np.eye(3)-np.outer(d,d))
    return {'mass':m,'com':com.tolist(),'tensor':I.tolist()}

base=link('base_link')
cx=P['frame_center_x'];fw=P['frame_width'];fd=P['frame_depth'];ps=P['post_size']
xp=(fd-ps)/2;yp=(fw-ps)/2
# Stock mower total proxy is split between chassis, rear wheels and caster.
# No shell volume is mistaken for a solid aluminium chassis.
box(base,'wr141e_lower_chassis',[.400,.296,.090],(-.079,0,.105),c=BLACK,m=P['retained_chassis_mass']*.70)
hood=[(.279,-.145),(.250,-.185),(.050,-.190),(-.110,-.145),(-.260,-.140),(-.279,-.115),(-.279,.115),(-.260,.140),(-.110,.145),(.050,.190),(.250,.185),(.279,.145)]
prism(base,'wr141e_orange_hood',hood,.065,(0,0,.1555),ORANGE,P['retained_chassis_mass']*.30)
collision(base,'rear_chassis','box',[.375,.296,.115],(-.0675,0,.1225))
for sign in (-1,1):
    collision(base,f'nose_side_{sign}','box',[.150,.080,.090],(.200,sign*.110,.115))
collision(base,'nose_upper','box',[.170,.290,.028],(.194,0,.174))
# Lower grille edge clears the full caster tyre width at every swivel angle.
box(base,'front_grille',[.003,.290,.070],(.2775,0,.120),c=BLACK)
collision(base,'front_grille','box',[.003,.290,.070],(.2775,0,.120))
for y in np.linspace(-.126,.126,13):
    box(base,f'front_grille_rib_{y}',[.003,.004,.065],(.2775,y,.120),c=DARK)
for sign in (-1,1):
    box(base,f'cut_to_edge_side_{sign}',[.205,.006,.075],(.110,sign*.184,.1125),c=DARK)
box(base,'control_panel',[.118,.155,.007],(.130,0,.1955),c=DARK)
cyl(base,'height_adjustment_dial',.020,.008,(.130,.047,.201),c=ORANGE)
box(base,'stop_button',[.035,.044,.010],(.135,-.010,.200),c=RED)
box(base,'display',[.030,.040,.001],(.145,-.055,.1995),c=BLACK)
box(base,'side_charging_contact_bar',[.070,.009,.024],(.100,.186,.165),c=RED)
for x in (.078,.122):box(base,f'charging_contact_{x}',[.014,.002,.006],(x,.191,.165),c=METAL)
# Proposed metal bridge: its datum is a design assumption, not a deck measurement.
box(base,'chassis_adapter',[fd,fw,.006],(cx,0,.202),c=BLACK,m=fd*fw*.006*P['aluminium_density'])
collision(base,'chassis_adapter','box',[fd,fw,.006],(cx,0,.202))
for x in (cx-xp,cx+xp):
    for y in (-yp,yp):
        box(base,f'adapter_spacer_{x}_{y}',[.025,.025,.011],(x,y,.1935),c=BLACK,m=.015)
        part(base,f'post_{x}_{y}','extrusion',[P['post_length']],(x,y,P['post_bottom']+P['post_length']/2),color=BLACK,mass=P['t_slot_kg_per_m']*P['post_length'])
        collision(base,f'post_{x}_{y}','box',[ps,ps,P['post_length']],(x,y,P['post_bottom']+P['post_length']/2))
# Each floor blank is exactly200x200mm; corner reliefs clear the four posts.
hx=P['floor_depth']/2;hy=P['floor_width']/2
notched=[(-hx,-hy+ps),(-hx+ps,-hy+ps),(-hx+ps,-hy),(hx-ps,-hy),(hx-ps,-hy+ps),(hx,-hy+ps),
         (hx,hy-ps),(hx-ps,hy-ps),(hx-ps,hy),(-hx+ps,hy),(-hx+ps,hy-ps),(-hx,hy-ps)]
area=polygon_properties(notched)[0]
for i,z in enumerate(P['ring_bottoms']):
    for a in (-1,1):
        part(base,f'rail_x_{i}_{a}','extrusion',[P['depth_rail_length']],(cx,a*yp,z+.010),(0,pi/2,0),BLACK,P['v_slot_kg_per_m']*P['depth_rail_length'])
        part(base,f'rail_y_{i}_{a}','extrusion',[P['width_rail_length']],(cx+a*xp,0,z+.010),(pi/2,0,0),BLACK,P['v_slot_kg_per_m']*P['width_rail_length'])
        collision(base,f'rail_x_{i}_{a}','box',[P['depth_rail_length'],ps,ps],(cx,a*yp,z+.010))
        collision(base,f'rail_y_{i}_{a}','box',[ps,P['width_rail_length'],ps],(cx+a*xp,0,z+.010))
    thick=P['shelf_thickness'];sc=z+.020+thick/2
    prism(base,f'polycarbonate_floor_{i}',notched,thick,(cx,0,sc),CLEAR,area*thick*P['polycarbonate_density'])
    collision(base,f'floor_{i}_center','box',[P['floor_depth']-2*ps,P['floor_width'],thick],(cx,0,sc))
    for sign in (-1,1):collision(base,f'floor_{i}_end_{sign}','box',[ps,P['floor_width']-2*ps,thick],(cx+sign*(hx-ps/2),0,sc))

t=P['panel_thickness'];lo=P['panel_bottom'];hi=P['panel_top'];zmid=(lo+hi)/2
frontx=cx+fd/2+t/2;rearx=cx-fd/2-t/2
cover_width=fw;cover_depth=fd
ab=P['camera_aperture_bottom'];at=P['camera_aperture_top'];aw=P['camera_aperture_half_width']
# Four opaque rectangles leave a true optical opening; collision follows the opening.
for n,sz,cen in [
 ('front_door_lower',[t,cover_width,ab-lo],(frontx,0,(lo+ab)/2)),
 ('front_door_upper',[t,cover_width,hi-at],(frontx,0,(hi+at)/2)),
 ('front_door_left_strip',[t,cover_width/2-aw,at-ab],(frontx,(cover_width/2+aw)/2,(at+ab)/2)),
 ('front_door_right_strip',[t,cover_width/2-aw,at-ab],(frontx,-(cover_width/2+aw)/2,(at+ab)/2))]:
    box(base,n,sz,cen,c=BLACK,m=np.prod(sz)*P['plastic_density']);collision(base,n,'box',sz,cen)
box(base,'rear_door_closed',[t,cover_width,hi-lo],(rearx,0,zmid),c=CLEAR,m=t*cover_width*(hi-lo)*P['polycarbonate_density'])
collision(base,'rear_door_closed','box',[t,cover_width,hi-lo],(rearx,0,zmid))
# Side sheets leave a110mm square carrier opening. Metal carriers bridge both posts.
for sign in (-1,1):
    rootz=P['arm_root_z'];bh=.055;sidey=sign*(fw/2+t/2)
    for n,sz,cen in [
      ('lower',[cover_depth,t,rootz-bh-lo],(cx,sidey,(lo+rootz-bh)/2)),
      ('upper',[cover_depth,t,hi-rootz-bh],(cx,sidey,(hi+rootz+bh)/2)),
      ('front_strip',[(cover_depth-.110)/2,t,.110],(cx+(cover_depth+.110)/4,sidey,rootz)),
      ('rear_strip',[(cover_depth-.110)/2,t,.110],(cx-(cover_depth+.110)/4,sidey,rootz))]:
        box(base,f'side_{sign}_{n}',sz,cen,c=BLACK,m=np.prod(sz)*P['plastic_density']);collision(base,f'side_{sign}_{n}','box',sz,cen)
    sz=[fd,.004,.120];box(base,f'arm_bridge_{sign}',sz,(cx,sign*(fw/2+.004),rootz),c=BLACK,m=np.prod(sz)*P['aluminium_density'])
    box(base,f'arm_flange_{sign}',[.090,.004,.090],(cx,sign*(fw/2+.008),rootz),c=BLACK,m=.090*.004*.090*P['aluminium_density'])
    collision(base,f'arm_bridge_{sign}','box',[fd,.008,.120],(cx,sign*(fw/2+.006),rootz))
    for x in (cx-xp,cx+xp):
        for z in (rootz-.040,rootz+.040):cyl(base,f'bridge_bolt_{sign}_{x}_{z}',.003,.008,(x,sign*(fw/2+.004),z),(pi/2,0,0),METAL,.003)
    for z in (lo+.012,.390,.640,hi-.012):
        for x in (cx-xp,cx+xp):cyl(base,f'panel_screw_{sign}_{x}_{z}',.0025,.0015,(x,sign*(fw/2+.0028),z),(pi/2,0,0))
for x,prefix in ((frontx+.004,'front'),(rearx-.004,'rear')):
    for z in (lo+.080,hi-.160):box(base,f'{prefix}_hinge_{z}',[.006,.014,.040],(x,.068,z),c=METAL,m=.008)
    cyl(base,prefix+'_latch',.006,.004,(x,-.068,zmid),(0,pi/2,0),DARK,.010)

# GB70 longest axis is vertical; the full152mm installation width fits160mm clear.
floor_top=lambda i:P['ring_bottoms'][i]+.020+P['shelf_thickness']
bz=floor_top(0)+.004+.222/2
box(base,'noco_tray',[.084,.156,.004],(cx,0,floor_top(0)+.002),c=BLACK,m=.100)
box(base,'noco_gb70',[.069,.099,.222],(cx,0,bz),c=DARK,m=P['noco_mass'])
box(base,'noco_label',[.001,.070,.185],(cx+.035,0,bz),c=BLACK)
box(base,'noco_rear_label',[.001,.070,.185],(cx-.035,0,bz),c=BLACK)
for k in range(4):box(base,f'charge_led_{k}',[.001,.006,.003],(cx+.0356,-.015+k*.010,bz+.075),c=GREEN)
for sign in (-1,1):box(base,f'battery_retainer_{sign}',[.074,.008,.100],(cx,sign*.0555,floor_top(0)+.004+.050),c=BLACK,m=.018)
collision(base,'noco_installed_reserve','box',[.070,.152,.222],(cx,0,bz))
box(base,'power_io',[.060,.130,.041],(cx-.030,0,floor_top(1)+.0205),c=DARK,m=.180)
box(base,'converter',[.040,.055,.015],(cx+.045,0,floor_top(1)+.0075),c=GREEN,m=.080)
box(base,'compute_board',[.056,.085,.003],(cx,0,floor_top(2)+.0045),c=GREEN,m=.070)
box(base,'active_cooler',[.040,.040,.020],(cx,0,floor_top(2)+.018),c=DARK,m=.060)
for k in range(6):box(base,f'cooler_fin_{k}',[.035,.0015,.006],(cx,-.016+k*.006,floor_top(2)+.031),c=BLACK,m=.002)
for x in (cx-.024,cx+.024):
    for y in (-.035,.035):cyl(base,f'compute_standoff_{x}_{y}',.002,.003,(x,y,floor_top(2)+.0015),m=.001)
box(base,'wiring_distribution',[.060,.090,.020],(cx+.030,0,floor_top(1)+.032),c=DARK,m=.180)
for y in (-.055,.055):box(base,f'camera_vertical_bracket_{y}',[.004,.012,.1065],(-.037,y,.65175),c=BLACK,m=.012)
box(base,'camera_shelf',[.080,.156,.003],(-.010,0,.600),c=BLACK,m=.080*.156*.003*P['aluminium_density'])
for x in (-.025,.005):
    for y in (-.065,.065):cyl(base,f'camera_pcb_standoff_{x}_{y}',.002,.010,(x,y,.6065),m=.001)
box(base,'lidar_pedestal',[.036,.036,.025],(cx,0,.7205),c=BLACK,m=.025)

for side,s in (('left',1),('right',-1)):
    wheel=link(side+'_wheel');r=P['wheel_radius'];w=P['wheel_width']
    cyl(wheel,'rubber_tyre',r,w,r=(pi/2,0,0),c=BLACK,m=P['wheel_mass']*.8)
    cyl(wheel,'hub',r*.56,w-.002,r=(pi/2,0,0),c=METAL,m=P['wheel_mass']*.2)
    for sface in (-1,1):
        for k in range(6):
            a=2*pi*k/6
            cyl(wheel,f'hub_bolt_{sface}_{k}',.002,.0015,(.015*math.sin(a),sface*(w/2-.001),.015*math.cos(a)),(pi/2,0,0))
    collision(wheel,'rolling_contact','cylinder',[r,w],rpy=(pi/2,0,0))
    joint(side+'_wheel_joint',base,wheel,'continuous',(P['wheel_x'],s*P['wheel_half_separation'],r),axis=(0,1,0),limits=[None,None,P['wheel_effort'],P['wheel_speed']])
fork=link('caster_swivel_link')
cyl(fork,'swivel_shaft',.009,.030,(0,0,0),c=METAL,m=P['caster_fork_mass']*.40)
for sign in (-1,1):
    box(fork,f'fork_cheek_{sign}',[.030,.006,.074],(-.010,sign*.026,-.039),c=BLACK,m=P['caster_fork_mass']*.30)
    collision(fork,f'fork_cheek_{sign}','box',[.030,.006,.074],(-.010,sign*.026,-.039))
cyl(fork,'caster_axle',.0035,.060,(-.020,0,-.070),(pi/2,0,0),METAL)
collision(fork,'swivel_shaft','cylinder',[.009,.030])
joint('caster_swivel_joint',base,fork,'continuous',P['caster_swivel_xyz'],axis=(0,0,1),limits=[None,None,.05,20.])
caster=link('caster_link')
cyl(caster,'front_wheel',P['caster_radius'],P['caster_width'],r=(pi/2,0,0),c=BLACK,m=P['caster_mass']*.80)
cyl(caster,'front_hub',.017,P['caster_width']+.001,r=(pi/2,0,0),c=DARK,m=P['caster_mass']*.20)
collision(caster,'rolling_contact','cylinder',[P['caster_radius'],P['caster_width']],rpy=(pi/2,0,0))
joint('caster_wheel_joint',fork,caster,'continuous',P['caster_wheel_xyz'],axis=(0,1,0),limits=[None,None,.05,30.])

cam=link('camera_mount')
# These are packaging reservations for re-housed electronics, not a measured teardown CAD.
# Retain the previous .97kg allocation until the installed electronics are weighed.
box(cam,'kinect_logic_board_provisional',[.045,.150,.003],(-.005,0,-.022),c=GREEN,m=P['kinect_mass']*.15)
box(cam,'kinect_heatspreader_provisional',[.045,.100,.020],(-.005,0,-.0105),c=METAL,m=P['kinect_mass']*.60)
box(cam,'kinect_optical_carrier_provisional',[.024,.154,.025],(.018,0,.012),c=BLACK,m=P['kinect_mass']*.25)
cyl(cam,'rgb_lens',.008,.008,(.030,-.06925,.012),(0,pi/2,0),DARK)
cyl(cam,'depth_lens',.008,.008,(.030,.06925,.0065),(0,pi/2,0),DARK)
box(cam,'infrared_emitter_provisional',[.001,.030,.015],(.0335,0,.012),c=DARK)
collision(cam,'kinect_electronics_reserve','box',P['camera_module_collision_size'],P['camera_module_collision_xyz'])
joint('camera_mount_joint',base,cam,xyz=P['camera_center'])
opt=link('camera_optical_frame');joint('camera_optical_joint',cam,opt,xyz=P['camera_optical_offset'],rpy=(-pi/2,0,-pi/2))
lid=link('lidar_mount')
cyl(lid,'lidar_head',.035,.045,(0,0,.0225),c=DARK,m=P['lidar_mass'])
cyl(lid,'lidar_band',.0352,.004,(0,0,.006),c=ORANGE)
collision(lid,'head','cylinder',[.035,.045],(0,0,.0225))
joint('lidar_mount_joint',base,lid,xyz=(P['frame_center_x'],0,.733))
scan=link('lidar_scan_frame');joint('lidar_scan_joint',lid,scan,xyz=(0,0,.0225))

def limb(l,L,m):
    # Mass budget: servo55g, remaining bracket/shaft material. Distinct geometry.
    box(l,'servo_body',[.040,.020,.036],(.013,0,0),c=DARK,m=.055)
    for s in (-1,1):
        box(l,f'aluminium_cheek_{s}',[L,.002,.025],(L/2,s*.014,0),m=(m-.075)/2)
        cyl(l,f'pivot_cap_{s}',.009,.002,(0,s*.016,0),(pi/2,0,0),METAL,.010)
        for x in (.015,L-.012):cyl(l,f'bracket_screw_{s}_{x}',.002,.0015,(x,s*.0153,0),(pi/2,0,0))
    collision(l,'link_envelope','box',[L+.018,.036,.040],(L/2-.004,0,0))
for side,s in (('left',1),('right',-1)):
    a=link(side+'_arm_base')
    cyl(a,'base_rotor',.021,.030,(0,0,.019),c=DARK,m=.135)
    box(a,'root_plate',[.060,.060,.002],(0,0,.001),m=.025)
    box(a,'shoulder_saddle',[.035,.046,.024],(0,0,.036),m=.040)
    collision(a,'root','cylinder',[.023,.040],(0,0,.022))
    joint(side+'_arm_base_joint',base,a,'revolute',(P['frame_center_x'],s*P['arm_root_y'],P['arm_root_z']),
          (0,-pi/2,-s*pi/2),(0,0,s),[-P['arm_base_range'],P['arm_base_range'],P['arm_effort'],P['arm_speed']])
    u=link(side+'_upper_arm');limb(u,P['upper_arm_length'],.210)
    joint(side+'_shoulder_joint',a,u,'revolute',(0,0,P['shoulder_offset']),
          (0,P['shoulder_zero_pitch'],0),(0,1,0),[-P['shoulder_range'],P['shoulder_range'],P['arm_effort'],P['arm_speed']])
    f=link(side+'_forearm');limb(f,P['forearm_length'],.180)
    joint(side+'_elbow_joint',u,f,'revolute',(P['upper_arm_length'],0,0),(0,P['elbow_zero_pitch'],0),(0,1,0),[-P['elbow_range'],P['elbow_range'],P['arm_effort'],P['arm_speed']])
    wr=link(side+'_wrist');limb(wr,P['wrist_length'],.130)
    joint(side+'_wrist_pitch_joint',f,wr,'revolute',(P['forearm_length'],0,0),(0,P['wrist_zero_pitch'],0),(0,1,0),[-P['wrist_pitch_range'],P['wrist_pitch_range'],P['arm_effort'],P['arm_speed']])
    hand=link(side+'_hand')
    box(hand,'gripper_servo',[.036,.020,.036],(.010,0,0),c=DARK,m=.055)
    box(hand,'gripper_bridge',[.025,.048,.006],(.0125,0,-.015),m=.045)
    cyl(hand,'wrist_roll_hub',.014,.008,(.003,0,0),(0,pi/2,0),METAL,.060)
    collision(hand,'hand_body','box',[.040,.048,.038],(.010,0,0))
    joint(side+'_wrist_roll_joint',wr,hand,'revolute',(P['wrist_length'],0,0),axis=(s,0,0),limits=[-pi/2,pi/2,P['arm_effort'],P['arm_speed']])
    for jaw,jsgn in (('left',1),('right',-1)):
        finger=link(side+'_gripper_'+jaw);L=P['finger_length'];slope=-jsgn*math.atan2(.012,L)
        length=math.hypot(L,.012)
        box(finger,'finger',[length,.008,.014],(L/2,-jsgn*.006,0),(0,0,slope),m=.020)
        cyl(finger,'jaw_pivot',.006,.018,c=METAL,m=.005)
        collision(finger,'jaw','box',[length,.008,.014],(L/2,-jsgn*.006,0),(0,0,slope))
        name=side+'_gripper_'+jaw+'_joint'
        joint(name,hand,finger,'revolute',(P['hand_length'],jsgn*.018,0),axis=(0,0,jsgn),
              limits=[0,.6,P['jaw_effort'],1.],mimic=(side+'_gripper_left_joint',1.,0.) if jaw=='right' else None)

def triangles(p):
    k=p['kind'];s=p['size']
    t=box_tri(s) if k=='box' else cyl_tri(*s) if k=='cylinder' else sphere_tri(s[0]) if k=='sphere' else prism_tri(p['polygon'],s[2]) if k=='prism' else extrusion_tri(s[0])
    # Micrometre-scale visual seam separation keeps independent primitive shells
    # topologically closed when combined in one STL. Physical shapes are unchanged.
    return (t*(1-1e-5))@rot(p['rpy']).T+vec(p['xyz'])
for name,l in links.items():
    l['inertial']=inertial(name);l['visuals']=[]
    groups={}
    for p in l['parts']:groups.setdefault(p['material'],[]).append(p)
    for material,ps in groups.items():
        stem=name if material=='matte_black' else name+'_'+material
        mesh='meshes/'+stem+'.stl';stl(ROOT/mesh,np.concatenate([triangles(p) for p in ps]))
        l['visuals'].append({'mesh':mesh,'material':material,'rgba':ps[0]['rgba']})

def origin(el,xyz,rpy):E.SubElement(el,'origin',{'xyz':fmt(xyz),'rpy':fmt(rpy)})
def geometry(el,d):
    g=E.SubElement(el,'geometry');s=d['size'];k=d['kind']
    if k=='box':E.SubElement(g,'box',{'size':fmt(s)})
    elif k=='cylinder':E.SubElement(g,'cylinder',{'radius':fmt([s[0]]),'length':fmt([s[1]])})
    elif k=='sphere':E.SubElement(g,'sphere',{'radius':fmt(s)})
def link_xml(name,portable=False):
    l=links[name];el=E.Element('link',{'name':name});I=l['inertial']
    if I:
        ie=E.SubElement(el,'inertial');origin(ie,I['com'],[0,0,0]);E.SubElement(ie,'mass',{'value':fmt([I['mass']])})
        t=I['tensor'];E.SubElement(ie,'inertia',{key:fmt([t[i][j]]) for key,i,j in [('ixx',0,0),('ixy',0,1),('ixz',0,2),('iyy',1,1),('iyz',1,2),('izz',2,2)]})
    elif not l['parts'] and not l['collisions']:
        # Fixed reference frames have exactly zero mass, explicitly, so importers
        # do not invent a default 1 kg body for missing inertial data.
        ie=E.SubElement(el,'inertial');origin(ie,[0,0,0],[0,0,0])
        E.SubElement(ie,'mass',{'value':'0'})
        E.SubElement(ie,'inertia',{key:'0' for key in ('ixx','ixy','ixz','iyy','iyz','izz')})
    for i,v in enumerate(l['visuals']):
        ve=E.SubElement(el,'visual',{'name':name+'_visual_'+str(i)});origin(ve,[0,0,0],[0,0,0]);g=E.SubElement(ve,'geometry')
        E.SubElement(g,'mesh',{'filename':('../' if portable else 'package://underbot_description/')+v['mesh'],'scale':'1 1 1'})
        mat=E.SubElement(ve,'material',{'name':v['material']});E.SubElement(mat,'color',{'rgba':fmt(v['rgba'])})
    for d in l['collisions']:
        ce=E.SubElement(el,'collision',{'name':name+'_'+d['name']});origin(ce,d['xyz'],d['rpy']);geometry(ce,d)
    return el
def joint_xml(j):
    el=E.Element('joint',{'name':j['name'],'type':j['type']});E.SubElement(el,'parent',{'link':j['parent']});E.SubElement(el,'child',{'link':j['child']});origin(el,j['xyz'],j['rpy'])
    if j['type']!='fixed':
        E.SubElement(el,'axis',{'xyz':fmt(j['axis'])});lo,hi,eff,vel=j['limits'];attrs={'effort':fmt([eff]),'velocity':fmt([vel])}
        if lo is not None:attrs.update(lower=fmt([lo]),upper=fmt([hi]))
        E.SubElement(el,'limit',attrs);E.SubElement(el,'dynamics',{'damping':'.001' if 'caster' in j['name'] else '.02' if 'wheel' in j['name'] else '.1','friction':'.0001' if 'caster' in j['name'] else '.02'})
        if j['mimic']:E.SubElement(el,'mimic',{'joint':j['mimic'][0],'multiplier':fmt([j['mimic'][1]]),'offset':fmt([j['mimic'][2]])})
    return el
for portable in (False,True):
    robot=E.Element('robot',{'name':'underbot'});robot.append(E.Comment('R08 WR141E geometry; 200mm floors, 204mm external covers. Read docs/accuracy_and_physics.md before interpreting estimated values as hardware data.'))
    for n in links:robot.append(link_xml(n,portable))
    for j in joints:robot.append(joint_xml(j))
    save_xml(ROOT/'urdf'/('underbot.portable.urdf' if portable else 'underbot.urdf'),robot)

# Modular Xacro uses the exact same generated elements, without runtime dependency
# on this generator. Relative includes resolve against the including Xacro file.
ns='http://www.ros.org/wiki/xacro';E.register_namespace('xacro',ns)
categories={'base':lambda n:n in ('base_link','left_wheel','right_wheel','caster_swivel_link','caster_link'),
            'sensors':lambda n:n.startswith(('camera','lidar')),
            'arm':lambda n:n.startswith(('left_','right_')) and n not in ('left_wheel','right_wheel')}
main=E.Element('robot',{'name':'underbot'})
for category,predicate in categories.items():
    sub=E.Element('robot');macro=E.SubElement(sub,'{'+ns+'}macro',{'name':'underbot_'+category})
    for n in links:
        if predicate(n):macro.append(link_xml(n))
    for j in joints:
        if predicate(j['child']):macro.append(joint_xml(j))
    save_xml(ROOT/'urdf'/(category+'.xacro'),sub)
    E.SubElement(main,'{'+ns+'}include',{'filename':category+'.xacro'})
    E.SubElement(main,'{'+ns+'}underbot_'+category)
save_xml(ROOT/'urdf/underbot.urdf.xacro',main)

manifest={'parameters':P,'links':links,'joints':joints,'independent_commands':14,'passive_joint_names':['caster_swivel_joint','caster_wheel_joint'],'independent_coordinates':16,'ground_datum':'base_link origin, z=0'}
(ROOT/'config/geometry_manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
expect={'expected_joints':{},'expected_world_bounds':{},'ground_contacts':['left_wheel','right_wheel','caster_link'],
        'allow_collision_pairs':[['base_link','camera_mount'],['base_link','lidar_mount']],
        'sweep_joint_names':[j['name'] for j in joints if j['type']=='revolute' and not j['mimic']]}
for j in joints:
    expect['expected_joints'][j['name']]={k:j[k] for k in ('parent','child','type','axis','xyz','rpy')}
expect['expected_world_bounds']['lidar_mount']={'min':[-.1052,-.0352,.733],'max':[-.0348,.0352,.778],'geometry':'visual','tolerance':.0004}
expect['expected_world_bounds']['camera_mount']={'min':[-.0325,-.07725,.6115],'max':[.029,.07725,.6595],'geometry':'visual','tolerance':.0005}
expect['mirror_link_pairs']=[[f'left_{n}',f'right_{n}'] for n in ('arm_base','upper_arm','forearm','wrist','hand')]
expect['mirror_link_pairs'] += [['left_gripper_left','right_gripper_right'],['left_gripper_right','right_gripper_left']]
(ROOT/'config/validation_expectations.json').write_text(json.dumps(expect,indent=2),encoding='utf-8')
print(f'Generated {len(links)} links, {len(joints)} joints; 14 independent commands; '+str(len(list((ROOT/'meshes').glob('*.stl'))))+' visual meshes.')
