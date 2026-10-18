"""Reconstruct the approved SI manifest in Blender, retaining exact part envelopes.

Run with Blender --background --python this_file. Source URDF physics is untouched.
STL is geometry only: the GLB and packed BLEND carry PBR materials and textures.
"""
from pathlib import Path
import json, math, struct, re, hashlib, time, sys, argparse
from collections import defaultdict
import bpy, bmesh
from mathutils import Matrix, Vector, Euler
from mathutils.geometry import tessellate_polygon

ROOT = Path(__file__).resolve().parents[1]
args=argparse.ArgumentParser()
args.add_argument('--source',type=Path,default=ROOT/'outputs/underbot_description/config/geometry_manifest.json')
args.add_argument('--output',type=Path,default=ROOT/'outputs/Underbot_Final_R09')
args.add_argument('--skip-renders',action='store_true')
ARGS=args.parse_args(sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else [])
SOURCE = ARGS.source.resolve()
OUT = ARGS.output.resolve()
for sub in ('stl/components_mm', 'stl/links_local_mm', 'models/meshes', 'renders'):
    (OUT/sub).mkdir(parents=True, exist_ok=True)
DATA = json.loads(SOURCE.read_text(encoding='utf-8'))
MATDOC = json.loads((OUT/'materials.json').read_text(encoding='utf-8'))
START=time.time()
PROFILE = [(-.010,-.010),(-.003,-.010),(-.003,-.007),(.003,-.007),(.003,-.010),(.010,-.010),
           (.010,-.003),(.007,-.003),(.007,.003),(.010,.003),(.010,.010),(.003,.010),
           (.003,.007),(-.003,.007),(-.003,.010),(-.010,.010),(-.010,.003),(-.007,.003),
           (-.007,-.003),(-.010,-.003)]

def clean(n): return re.sub(r'[^A-Za-z0-9_.-]+','_',n)
def matrix(xyz, rpy): return Matrix.Translation(Vector(xyz)) @ Euler(rpy,'XYZ').to_matrix().to_4x4()
def rows(m): return [[float(v) for v in r] for r in m]
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def bounds(vs):
    return [[min(v[a] for v in vs) for a in range(3)], [max(v[a] for v in vs) for a in range(3)]]
def extent(bb): return [bb[1][a]-bb[0][a] for a in range(3)]

bpy.ops.object.select_all(action='SELECT'); bpy.ops.object.delete(use_global=False)
for block in list(bpy.data.materials): bpy.data.materials.remove(block)
scene=bpy.context.scene
scene.unit_settings.system='METRIC'; scene.unit_settings.scale_length=1.0
scene.unit_settings.length_unit='METERS'
robot=bpy.data.collections.new('UNDERBOT_R09__SI_metres');scene.collection.children.link(robot)
studio=bpy.data.collections.new('PRESENTATION_ONLY__not_exported');scene.collection.children.link(studio)

def image_node(nodes, path, label, color=True):
    im=bpy.data.images.load(str(OUT/path),check_existing=True)
    im.colorspace_settings.name='sRGB' if color else 'Non-Color'
    n=nodes.new('ShaderNodeTexImage');n.image=im;n.label=label;n.name=label
    n.extension='REPEAT';return n

MATS={}
for name,spec in MATDOC['materials'].items():
    m=bpy.data.materials.new(name);m.use_nodes=True
    ns=m.node_tree.nodes;links=m.node_tree.links;bs=ns.get('Principled BSDF')
    p=spec.get('pbrMetallicRoughness',{});ex=spec.get('extras',{})
    factor=p.get('baseColorFactor',[.1,.1,.1,1])
    base=ex.get('fallback_baseColorFactor_linear',factor)
    bs.inputs['Base Color'].default_value=(*base[:3],1)
    bs.inputs['Metallic'].default_value=p.get('metallicFactor',0)
    bs.inputs['Roughness'].default_value=p.get('roughnessFactor',.5)
    m.diffuse_color=(*base[:3],1)
    if 'baseColorTexture' in p:
        tex=image_node(ns,p['baseColorTexture']['uri'],'Base colour — 0.10 m tile')
        links.new(tex.outputs['Color'],bs.inputs['Base Color'])
    if 'metallicRoughnessTexture' in p:
        tex=image_node(ns,p['metallicRoughnessTexture']['uri'],'Packed roughness G / metallic B',False)
        split=ns.new('ShaderNodeSeparateColor');split.mode='RGB'
        links.new(tex.outputs['Color'],split.inputs['Color'])
        links.new(split.outputs['Green'],bs.inputs['Roughness'])
        links.new(split.outputs['Blue'],bs.inputs['Metallic'])
    if 'normalTexture' in spec:
        tex=image_node(ns,spec['normalTexture']['uri'],'OpenGL tangent normal',False)
        normal=ns.new('ShaderNodeNormalMap');normal.inputs['Strength'].default_value=spec['normalTexture'].get('scale',1)
        links.new(tex.outputs['Color'],normal.inputs['Color']);links.new(normal.outputs['Normal'],bs.inputs['Normal'])
    if name=='polycarbonate':
        bs.inputs['Base Color'].default_value=(.94,.985,1,1)
        bs.inputs['Transmission Weight'].default_value=.94
        bs.inputs['IOR'].default_value=1.586;bs.inputs['Roughness'].default_value=.055
        bs.inputs['Alpha'].default_value=1
    if name=='optical_black_glass':
        bs.inputs['Base Color'].default_value=(.005,.012,.019,1)
        bs.inputs['Metallic'].default_value=.05;bs.inputs['Roughness'].default_value=.07
        bs.inputs['IOR'].default_value=1.52;bs.inputs['Coat Weight'].default_value=.5
    if name=='status_led_green':
        bs.inputs['Emission Color'].default_value=(.12,.65,.03,1)
        bs.inputs['Emission Strength'].default_value=.4
    for k,v in ex.items():
        if isinstance(v,(str,float,int,bool)):m[k]=v
    MATS[name]=m

def prism(poly,h):
    verts=[(x,y,z) for z in (-h/2,h/2) for x,y in poly]
    # Keep each planar cap as a single concave face during beveling. Internal
    # cap diagonals otherwise make the bevel produce microscopic sliver faces.
    n=len(poly);faces=[tuple(reversed(range(n))),tuple(i+n for i in range(n))]
    for i in range(n):j=(i+1)%n;faces.append((i,j,j+n,i+n))
    return verts,faces

def cylinder(r,h,n=128):
    return prism([(r*math.cos(2*math.pi*i/n),r*math.sin(2*math.pi*i/n)) for i in range(n)],h)

def tyre(r,h,n=192):
    # An annular visual tyre opens the existing hub. Tread cuts never increase R.
    inner=r*.54
    zs=[-h/2,-h/2+.002,-h*.22,0,h*.22,h/2-.002,h/2]
    verts=[]
    for k,z in enumerate(zs):
        for i in range(n):
            a=2*math.pi*i/n
            groove=(.0015 if i%4==2 else 0.0) if k not in (0,len(zs)-1) else 0
            edge=.0006 if k in (0,len(zs)-1) else 0
            radius=r-groove-edge
            verts.append((radius*math.cos(a),radius*math.sin(a),z))
    off=len(verts)
    for z in (-h/2,h/2):
        verts.extend([(inner*math.cos(2*math.pi*i/n),inner*math.sin(2*math.pi*i/n),z) for i in range(n)])
    faces=[]
    for k in range(len(zs)-1):
        for i in range(n):j=(i+1)%n;faces.append((k*n+i,k*n+j,(k+1)*n+j,(k+1)*n+i))
    for i in range(n):
        j=(i+1)%n
        faces.extend([(i,off+i,off+j,j),((len(zs)-1)*n+i,(len(zs)-1)*n+j,off+n+j,off+n+i),
                      (off+i,off+n+i,off+n+j,off+j)])
    return verts,faces

def socket_head(r,h,n=96):
    # Both shallow end recesses remain inside the source screw head envelope.
    v=[];depth=h*.22;ir=r*.42
    for radius,z in [(r,-h/2),(r,h/2),(ir,-h/2),(ir,-h/2+depth),(ir,h/2),(ir,h/2-depth)]:
        ring=len(v)//n
        for i in range(n):
            a=2*math.pi*i/n
            rr=radius if ring<2 else radius*math.cos(math.pi/6)/math.cos((a+math.pi/6)%(math.pi/3)-math.pi/6)
            v.append((rr*math.cos(a),rr*math.sin(a),z))
    f=[]
    for i in range(n):
        j=(i+1)%n
        f.extend([(i,j,n+j,n+i),(i,2*n+i,2*n+j,j),(n+i,n+j,4*n+j,4*n+i),
                  (2*n+i,3*n+i,3*n+j,2*n+j),(4*n+i,4*n+j,5*n+j,5*n+i)])
    # Hexagon edges contain collinear angular samples; centre fans avoid
    # degenerate triangles when those recessed faces are tessellated later.
    bottom=len(v);v.append((0,0,-h/2+depth))
    top=len(v);v.append((0,0,h/2-depth))
    for i in range(n):
        j=(i+1)%n
        f.extend([(bottom,3*n+j,3*n+i),(top,5*n+i,5*n+j)])
    return v,f

def make_mesh(part):
    kind=part['kind'];s=part['size'];name=part['name']
    if kind=='box':
        x,y,z=s
        verts,faces=prism([(-x/2,-y/2),(x/2,-y/2),(x/2,y/2),(-x/2,y/2)],z)
    elif kind=='prism':verts,faces=prism(part['polygon'],s[2])
    elif kind=='extrusion':verts,faces=prism(PROFILE,s[0])
    elif kind=='cylinder':
        if name=='rubber_tyre':verts,faces=tyre(*s)
        elif ('bolt' in name or 'screw' in name) and s[0]<=.005:verts,faces=socket_head(*s)
        else:verts,faces=cylinder(*s,n=192 if s[0]>.02 else 128)
    else:raise ValueError(f'Unsupported primitive {kind}')
    mesh=bpy.data.meshes.new(clean(name)+'__geometry');mesh.from_pydata(verts,[],faces);mesh.update()
    bm=bmesh.new();bm.from_mesh(mesh);bmesh.ops.recalc_face_normals(bm,faces=bm.faces);bm.to_mesh(mesh);bm.free()
    return mesh

def set_uv(obj,tile=.10):
    me=obj.data;uv=me.uv_layers.new(name='UV_metre_scale')
    # Orthogonal per-face projection: every 0.10 m is exactly one texture tile.
    for p in me.polygons:
        axis=max(range(3),key=lambda a:abs(p.normal[a]))
        a,b=[q for q in range(3) if q!=axis]
        for li in p.loop_indices:
            co=me.vertices[me.loops[li].vertex_index].co
            uv.data[li].uv=(co[a]/tile,co[b]/tile)

def finish_mesh(obj,part):
    before=bounds([v.co for v in obj.data.vertices]);kind=part['kind'];name=part['name']
    dimensions=extent(before)
    width=min(min(dimensions)*.08,.00065)
    if kind=='extrusion':width=.00010
    if 'polycarbonate_floor' in name:width=.00008
    if 'door' in name or name.startswith('side_'):width=.00008
    if name=='wr141e_orange_hood':width=.0012
    if kind=='cylinder':width=min(part['size'][1]*.07,part['size'][0]*.04,.0004)
    if name=='rubber_tyre' or 'bolt' in name or 'screw' in name:width=0
    bpy.context.view_layer.objects.active=obj;obj.select_set(True)
    if width:
        mod=obj.modifiers.new('Dimension preserving edge fillets','BEVEL');mod.width=width;mod.segments=3
        mod.limit_method='ANGLE';mod.angle_limit=math.radians(20);mod.affect='EDGES';mod.harden_normals=True
        bpy.ops.object.modifier_apply(modifier=mod.name)
        # Restore exact min/max even when a bevel removes an extreme corner.
        after=bounds([v.co for v in obj.data.vertices])
        for v in obj.data.vertices:
            for a in range(3):
                v.co[a]=before[0][a]+(v.co[a]-after[0][a])*(before[1][a]-before[0][a])/(after[1][a]-after[0][a])
    # Remove coincident bevel vertices before STL/GLB triangulation. This is
    # far below the dimensional audit tolerance and never shrinks the object.
    bm=bmesh.new();bm.from_mesh(obj.data)
    bmesh.ops.remove_doubles(bm,verts=list(bm.verts),dist=1e-9)
    bmesh.ops.dissolve_degenerate(bm,edges=list(bm.edges),dist=1e-10)
    bmesh.ops.recalc_face_normals(bm,faces=bm.faces)
    bm.to_mesh(obj.data);bm.free()
    for p in obj.data.polygons:
        p.use_smooth=(kind=='cylinder' and abs(p.normal.z)<.99) or (width>0 and max(abs(v) for v in p.normal)<.999)
    obj.data.update()
    # Use the exact export tessellation for UV projection. Nonplanar tyre
    # quads can have a different dominant axis than their final triangles.
    me=obj.data;me.calc_loop_triangles()
    vertices=[tuple(v.co) for v in me.vertices]
    triangles=[tuple(t.vertices) for t in me.loop_triangles]
    smooth=[me.polygons[t.polygon_index].use_smooth for t in me.loop_triangles]
    me.clear_geometry();me.from_pydata(vertices,[],triangles);me.update()
    for p,s in zip(me.polygons,smooth):p.use_smooth=s
    set_uv(obj)
    obj.select_set(False)
    return width

def evaluated_triangles(obj,transform):
    me=obj.data;me.calc_loop_triangles()
    return [[transform @ me.vertices[i].co for i in tri.vertices] for tri in me.loop_triangles]

def write_stl(path,triangles,scale=1.0,description='Underbot R09'):
    path.parent.mkdir(parents=True,exist_ok=True)
    with path.open('wb') as f:
        f.write(description.encode('ascii','replace')[:80].ljust(80,b' '));f.write(struct.pack('<I',len(triangles)))
        for tri in triangles:
            # Normals are computed from exactly the float32 vertices written
            # to STL, using double arithmetic for the small fillet triangles.
            xyz=struct.unpack('<9f',struct.pack('<9f',*(float(v[a])*scale for v in tri for a in range(3))))
            u=[xyz[3+a]-xyz[a] for a in range(3)];v=[xyz[6+a]-xyz[a] for a in range(3)]
            n=[u[1]*v[2]-u[2]*v[1],u[2]*v[0]-u[0]*v[2],u[0]*v[1]-u[1]*v[0]]
            norm=math.sqrt(sum(q*q for q in n))
            if not norm:raise ValueError(f'Degenerate stored float32 triangle in {path}')
            n=[q/norm for q in n]
            f.write(struct.pack('<12fH',*n,*xyz,0))

def topology(me):
    bm=bmesh.new();bm.from_mesh(me)
    out={'vertices':len(bm.verts),'faces':len(bm.faces),'boundary_edges':sum(e.is_boundary for e in bm.edges),
         'nonmanifold_edges':sum(not e.is_manifold for e in bm.edges)}
    bm.free();return out

parents={j['child']:j for j in DATA['joints']}
LINK_WORLD={}
def world_link(name):
    if name in LINK_WORLD:return LINK_WORLD[name]
    j=parents.get(name)
    m=Matrix.Identity(4) if j is None else world_link(j['parent']) @ matrix(j['xyz'],j['rpy'])
    LINK_WORLD[name]=m;return m

empties={}
for lname,l in DATA['links'].items():
    e=bpy.data.objects.new(lname,None);robot.objects.link(e);e.empty_display_type='PLAIN_AXES';e.empty_display_size=.015
    e['frame']='URDF link frame in metres';e['source_inertial_json']=json.dumps(l.get('inertial'))
    e['source_collisions_json']=json.dumps(l.get('collisions',[]))
    if lname in parents:e['parent_joint_json']=json.dumps(parents[lname])
    empties[lname]=e
for lname,e in empties.items():
    j=parents.get(lname)
    if j:e.parent=empties[j['parent']];e.matrix_local=matrix(j['xyz'],j['rpy'])
    else:e.matrix_world=Matrix.Identity(4)

objects=[];records=[];all_triangles=[];buckets=defaultdict(list);bucket_objects=defaultdict(list);link_triangles=defaultdict(list)
for lname,l in DATA['links'].items():
    for index,part in enumerate(l['parts']):
        obj=bpy.data.objects.new(clean(lname+'__'+part['name']),make_mesh(part));robot.objects.link(obj)
        obj.parent=empties[lname];local=matrix(part['xyz'],part['rpy']);obj.matrix_local=local
        obj['source_part_name']=part['name'];obj['source_link']=lname;obj['source_primitive']=part['kind']
        obj['source_primitive_json']=json.dumps(part);obj['source_material_bucket']=part['material']
        assignment=MATDOC.get('part_assignments',{}).get(lname,{}).get(part['name'],part['material'])
        if assignment not in MATS:raise ValueError(f'No PBR material: {assignment}')
        obj.data.materials.append(MATS[assignment]);fillet=finish_mesh(obj,part)
        topo=topology(obj.data)
        if topo['nonmanifold_edges']:raise ValueError(f'Nonmanifold single part {obj.name}: {topo}')
        wm=world_link(lname)@local
        localtri=evaluated_triangles(obj,Matrix.Identity(4));linktri=evaluated_triangles(obj,local)
        worldtri=evaluated_triangles(obj,wm)
        path=Path('stl/components_mm')/(clean(lname)+'__'+str(index).zfill(3)+'__'+clean(part['name'])+'.stl')
        write_stl(OUT/path,localtri,1000,'Underbot R09 millimetres - individual part local frame')
        records.append({'link':lname,'part':part['name'],'primitive':part['kind'],'source_dimensions_m':part['size'],
                        'material':assignment,'material_bucket':part['material'],'path':path.as_posix(),'units':'mm',
                        'frame':'part_local','part_to_link_m':rows(local),'part_to_world_m':rows(wm),
                        'link_to_world_m':rows(world_link(lname)),'local_bounds_m':bounds([v.co for v in obj.data.vertices]),
                        'world_bounds_m':bounds([wm@v.co for v in obj.data.vertices]),'triangles':len(localtri),
                        'fillet_radius_m':fillet,'topology':topo,'sha256':sha(OUT/path)})
        all_triangles.extend(worldtri);buckets[(lname,part['material'])].extend(linktri);link_triangles[lname].extend(linktri)
        bucket_objects[(lname,part['material'])].append((obj,local))
        objects.append(obj)
    print(f'BUILT {lname}: {len(l["parts"])} detailed components',flush=True)

grouped=[]
mtl_lines=['# Underbot R09 PBR companion: OBJ readers differ in roughness/normal support.']
for name,spec in MATDOC['materials'].items():
    pm=spec.get('pbrMetallicRoughness',{});col=pm.get('baseColorFactor',[.1,.1,.1,1])
    mtl_lines.extend([f'newmtl {name}',f'Kd {col[0]} {col[1]} {col[2]}',f'Pr {pm.get("roughnessFactor",.5)}',
                      f'Pm {pm.get("metallicFactor",0)}','d '+str(.22 if name=='polycarbonate' else 1),
                      'Ni '+str(1.586 if name=='polycarbonate' else 1.5)])
    if 'baseColorTexture' in pm:mtl_lines.append('map_Kd ../../'+pm['baseColorTexture']['uri'])
    rough=spec.get('extras',{}).get('standalone_roughness_uri')
    if rough:mtl_lines.append('map_Pr ../../'+rough)
    if 'normalTexture' in spec:mtl_lines.append('norm ../../'+spec['normalTexture']['uri'])
    mtl_lines.append('')
(OUT/'models/meshes/Underbot_R09.mtl').write_text('\n'.join(mtl_lines),encoding='utf-8')

def write_obj(path,source_objects):
    lines=['# Underbot R09 SI metres; original URDF link-local coordinates','mtllib Underbot_R09.mtl']
    offset=1
    for obj,transform in source_objects:
        me=obj.data;me.calc_loop_triangles();rot=transform.to_3x3();uv=me.uv_layers.active
        lines.extend([f'o {obj.name}',f'usemtl {obj.data.materials[0].name}'])
        # Split corners explicitly so UV seams and smooth corner normals remain faithful.
        for tri in me.loop_triangles:
            for li in tri.loops:
                vi=me.loops[li].vertex_index;v=transform@me.vertices[vi].co
                no=rot@me.corner_normals[li].vector;no.normalize();st=uv.data[li].uv
                lines.extend([f'v {v.x:.10g} {v.y:.10g} {v.z:.10g}',f'vt {st.x:.10g} {st.y:.10g}',
                              f'vn {no.x:.10g} {no.y:.10g} {no.z:.10g}'])
            lines.append('f '+' '.join(f'{i}/{i}/{i}' for i in range(offset,offset+3)));offset+=3
    path.write_text('\n'.join(lines)+'\n',encoding='utf-8')

for lname,l in DATA['links'].items():
    if link_triangles[lname]:
        path=Path('stl/links_local_mm')/(lname+'.stl')
        write_stl(OUT/path,link_triangles[lname],1000,'Underbot R09 millimetres - link local frame multiple shells')
        grouped.append({'path':path.as_posix(),'units':'mm','frame':lname,'link_to_world_m':rows(world_link(lname)),
                        'triangles':len(link_triangles[lname]),'sha256':sha(OUT/path)})
    for visual in l.get('visuals',[]):
        path=Path('models')/visual['mesh'];tris=buckets[(lname,visual['material'])]
        write_stl(OUT/path,tris,1,'Underbot R09 SI metres - URDF visual material bucket')
        write_obj((OUT/path).with_suffix('.obj'),bucket_objects[(lname,visual['material'])])
        grouped.append({'path':path.as_posix(),'units':'m','frame':lname,'material':visual['material'],
                        'link_to_world_m':rows(world_link(lname)),'triangles':len(tris),'sha256':sha(OUT/path)})
assembly_path=OUT/'stl/Underbot_R09_assembled_mm.stl'
write_stl(assembly_path,all_triangles,1000,'Underbot R09 millimetres world zero-pose - multiple closed shells')

# Select robot only; exporting no studio surfaces, lights, cameras, or scaling helpers.
bpy.ops.object.select_all(action='DESELECT')
for obj in [*objects,*empties.values()]:obj.select_set(True)
bpy.context.view_layer.update()
glb=OUT/'models/Underbot_R09_textured.glb'
bpy.ops.export_scene.gltf(filepath=str(glb),export_format='GLB',use_selection=True,export_extras=True,
                         export_yup=True,export_texcoords=True,export_normals=True,export_materials='EXPORT',
                         export_apply=False,export_cameras=False,export_lights=False,export_animations=False)

manifest={'revision':'R09 exact-dimension detailed visual export','source_geometry_manifest':str(SOURCE),
          'source_sha256':sha(SOURCE),'coordinate_convention':'ROS x forward, y left, z up; GLB converts to glTF y-up',
          'source_units':'metres','components':records,'grouped_meshes':grouped,
          'joints':DATA['joints'],'links':{n:{'world_matrix_m':rows(world_link(n)),'inertial':l.get('inertial')}
                                        for n,l in DATA['links'].items()},
          'assembled':{'path':'stl/Underbot_R09_assembled_mm.stl','units':'mm','frame':'base_link world zero pose',
                       'triangles':len(all_triangles),'bounds_m':bounds([v for t in all_triangles for v in t]),
                       'sha256':sha(assembly_path),'multiple_closed_shells':True,'boolean_union':False},
          'visual_only_changes':['dimension preserving edge fillets','128/192 segment circular surfaces',
                                 'annular tyre revealing existing hub; tread grooves inside original radius',
                                 'shallow hex recesses inside existing screw head envelope','UV mapped PBR surfaces'],
          'unmeasured_hardware':DATA['parameters'].get('status',{}).get('unmeasured_estimates',[])}
(OUT/'geometry_export_manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')

# Studio scene, kept in a distinct collection and excluded from GLB/STL exports.
def move_collection(obj,col):
    for c in list(obj.users_collection):c.objects.unlink(obj)
    col.objects.link(obj)
def aim(obj,target):obj.rotation_euler=(Vector(target)-obj.location).to_track_quat('-Z','Y').to_euler()
def area(name,loc,power,size,color,target=(-.04,0,.40)):
    light=bpy.data.lights.new(name,'AREA');light.energy=power;light.shape='DISK';light.size=size;light.color=color
    obj=bpy.data.objects.new(name,light);studio.objects.link(obj);obj.location=loc;aim(obj,target);return obj

bpy.ops.object.select_all(action='DESELECT')
bpy.ops.mesh.primitive_plane_add(size=200,location=(0,0,-.0003));floor=bpy.context.object;floor.name='Studio floor — not exported';move_collection(floor,studio)
fm=bpy.data.materials.new('Studio warm grey');fm.use_nodes=True
fbs=fm.node_tree.nodes.get('Principled BSDF');fbs.inputs['Base Color'].default_value=(.115,.125,.14,1);fbs.inputs['Roughness'].default_value=.83
floor.data.materials.append(fm)
area('Large soft key',(1.5,-1.7,2.4),180,1.7,(1,.93,.83))
area('Cool edge',(-1.2,.7,1.7),220,1.1,(.75,.87,1))
area('Front fill',(1.1,1.4,.9),95,1.4,(.9,.95,1))
area('Top softbox',(-.2,-.2,2.7),100,1.3,(1,1,1))
world=bpy.data.worlds.new('Soft studio environment');scene.world=world;world.use_nodes=True
world.node_tree.nodes.get('Background').inputs['Color'].default_value=(.30,.34,.40,1)
world.node_tree.nodes.get('Background').inputs['Strength'].default_value=.35
camd=bpy.data.cameras.new('Studio camera');cam=bpy.data.objects.new('Studio camera',camd);studio.objects.link(cam);scene.camera=cam
camd.type='ORTHO';camd.ortho_scale=1.11;camd.lens=65
scene.render.engine='CYCLES';scene.cycles.samples=48;scene.cycles.use_denoising=True
scene.cycles.use_adaptive_sampling=True;scene.cycles.adaptive_threshold=.025
try:
    prefs=bpy.context.preferences.addons['cycles'].preferences;prefs.compute_device_type='CUDA';prefs.get_devices()
    for device in prefs.devices:device.use=device.type=='CUDA'
    if any(d.type=='CUDA' for d in prefs.devices):scene.cycles.device='GPU'
    print('CYCLES_DEVICES',[(d.name,d.type,d.use) for d in prefs.devices],flush=True)
except Exception as err:print('CUDA_UNAVAILABLE',str(err),flush=True)
scene.cycles.max_bounces=12;scene.cycles.transmission_bounces=10;scene.cycles.transparent_max_bounces=12
scene.render.resolution_x=2200;scene.render.resolution_y=2400;scene.render.resolution_percentage=100
scene.render.image_settings.file_format='PNG';scene.render.image_settings.color_mode='RGBA';scene.render.film_transparent=False
scene.view_settings.view_transform='AgX'
try:scene.view_settings.look='AgX - Medium High Contrast'
except:pass
scene.render.image_settings.color_depth='8';scene.render.resolution_percentage=100

render_specs=[('Underbot_R09_hero',(1.40,-1.55,1.10),False),
              ('Underbot_R09_rear',(-1.35,1.40,.98),False),
              ('Underbot_R09_cutaway',(1.25,-1.45,1.08),True)]
render_results=[]
# Save the editable, packed scene before rendering so lighting can be reviewed
# or re-rendered without rebuilding geometry if a render is interrupted.
for im in bpy.data.images:
    if im.source=='FILE':
        try:im.pack()
        except Exception as err:print('PACK_WARNING',im.name,str(err))
cam.location=render_specs[0][1];aim(cam,(-.035,0,.385))
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'models/Underbot_R09_studio.blend'))
if not ARGS.skip_renders:
    scene.render.resolution_percentage=45;scene.cycles.samples=16
    scene.render.filepath=str(OUT/'renders/Underbot_R09_preview.png')
    print('RENDER quick preview',flush=True);bpy.ops.render.render(write_still=True)
    scene.render.resolution_percentage=100;scene.cycles.samples=48
for name,pos,cutaway in render_specs:
    if ARGS.skip_renders:break
    removed=[]
    if cutaway:
        for obj in objects:
            pn=obj.get('source_part_name','')
            if pn.startswith('front_door_') or pn.startswith('side_-1_') or pn.startswith('panel_screw_-1_') or pn.startswith('front_hinge_') or pn=='front_latch':
                obj.hide_render=True;removed.append(obj.name)
    cam.location=pos;aim(cam,(-.035,0,.385))
    scene.render.filepath=str(OUT/'renders'/f'{name}.png')
    print(f'RENDER {name}',flush=True);bpy.ops.render.render(write_still=True)
    render_results.append({'path':f'renders/{name}.png','size_px':[2200,2400],'removed_for_cutaway':removed})
    for obj in objects:obj.hide_render=False
cam.location=render_specs[0][1];aim(cam,(-.035,0,.385))
for im in bpy.data.images:
    if im.source=='FILE':
        try:im.pack()
        except Exception as err:print('PACK_WARNING',im.name,str(err))
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'models/Underbot_R09_studio.blend'))
report={'status':'built','component_count':len(records),'link_count':len(DATA['links']),
        'urdf_visual_mesh_count':sum(1 for g in grouped if g['units']=='m'),
        'assembled_triangles':len(all_triangles),'all_components_closed_manifold':all(r['topology']['nonmanifold_edges']==0 for r in records),
        'exact_dimension_policy':'No global shrink. Bevelled parts restore their exact original local bounds.',
        'assembly_topology':'Separate intersecting closed components; not a Boolean-unioned printable solid.',
        'stl_units':'assembled/components/link-local STL in mm; models/meshes URDF visuals in m',
        'texture_format':'Embedded PBR PNGs in GLB; packed Blender images; STL has no colour or texture',
        'renders':render_results,'elapsed_seconds':time.time()-START,
        'blender_version':bpy.app.version_string,'native_simulator_validation':False}
(OUT/'build_report.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print('R09_BUILD_COMPLETE',json.dumps(report),flush=True)
