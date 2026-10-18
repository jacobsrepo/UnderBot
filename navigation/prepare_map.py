"""Create a conservative, experimental 2D grid from the public point-cloud sample."""
from pathlib import Path
import numpy as np
import json
from PIL import Image,ImageFilter
ROOT=Path(__file__).resolve().parent
with (ROOT/'sample-map-planning/pointcloud_map.pcd').open('rb') as f:
    header={}
    while True:
        line=f.readline().decode().strip();parts=line.split()
        if parts and not line.startswith('#'):header[parts[0]]=parts[1:]
        if line.startswith('DATA '):break
    assert header['DATA']==['binary'] and header['FIELDS']==['x','y','z','rgb']
    a=np.frombuffer(f.read(),dtype='<f4',count=int(header['POINTS'][0])*4).reshape(-1,4)[:,:3]
print('Cloud percentiles',np.percentile(a,[0,5,50,95,100],axis=0),flush=True)
# Flat ground candidate within the most common 0.2 m height band.
hist,edges=np.histogram(a[:,2],bins=np.arange(a[:,2].min(),a[:,2].max()+.2,.2))
floor=float(edges[hist.argmax()]+.1)
ground=a[np.abs(a[:,2]-floor)<.15]
coarse=np.floor(ground[:,:2]/10).astype(int);cells,counts=np.unique(coarse,axis=0,return_counts=True)
centre=(cells[counts.argmax()]+.5)*10
origin=centre-20;res=.2;size=200
mask=np.all((a[:,:2]>=origin)&(a[:,:2]<origin+40),axis=1)
cloud=a[mask].copy();cloud[:,:2]-=centre;cloud[:,2]-=floor
ix=np.floor((cloud[:,0]+20)/res).astype(int);iy=np.floor((cloud[:,1]+20)/res).astype(int)
ground_seen=np.zeros((size,size),dtype=np.uint8);obstacle=np.zeros_like(ground_seen)
g=np.abs(cloud[:,2])<.15;o=(cloud[:,2]>.18)&(cloud[:,2]<1.5)
ground_seen[iy[g],ix[g]]=255;obstacle[iy[o],ix[o]]=255
# Close sub-cell ground sampling gaps only; unknown remains blocked by planner.
free=np.array(Image.fromarray(ground_seen).filter(ImageFilter.MaxFilter(3)).filter(ImageFilter.MinFilter(3)))>0
inflated=np.array(Image.fromarray(obstacle).filter(ImageFilter.MaxFilter(5)))>0
grid=np.full((size,size),-1,dtype=np.int8);grid[free]=0;grid[inflated]=100
np.savez_compressed(ROOT/'demo_map.npz',grid=grid,cloud=cloud[::max(1,len(cloud)//120000)].astype('<f4'))
# Find a large connected free region; initialization is explicitly synthetic.
visited=set();components=[]
for y,x in np.argwhere(grid==0):
    cell=(int(x),int(y))
    if cell in visited:continue
    todo=[cell];visited.add(cell);region=[]
    while todo:
        cx,cy=todo.pop();region.append((cx,cy))
        for nx,ny in [(cx+1,cy),(cx-1,cy),(cx,cy+1),(cx,cy-1)]:
            if 0<=nx<size and 0<=ny<size and grid[ny,nx]==0 and (nx,ny) not in visited:
                visited.add((nx,ny));todo.append((nx,ny))
    components.append(region)
region=max(components,key=len);start=min(region,key=lambda c:(c[0]-100)**2+(c[1]-100)**2)
goal=max(region,key=lambda c:(c[0]-start[0])**2+(c[1]-start[1])**2)
world=lambda c:[round(-20+(v+.5)*res,2) for v in c]
meta={'source':'Autoware sample-map-planning pointcloud_map.pcd','source_url':'https://autoware-files.s3.us-west-2.amazonaws.com/maps/demos/sample-map-planning.zip','archive_sha256':'5536fce7bb8db7688fdf94ec004118b898637ad0d5b6175108b10989dd6e93b9','resolution':res,'origin':[-20,-20],'size':size,'global_xy_centre':centre.tolist(),'ground_height':floor,'spawn':world(start),'landmarks':{'start':world(start),'goal_a':world(goal)},'free_region_cells':len(region),'limitations':'Experimental flat-ground projection; 0.4 m obstacle inflation; unknown blocked. Not a validated traversability map. Robot pose and sensors simulated.'}
(ROOT/'map_metadata.json').write_text(json.dumps(meta,indent=2))
img=np.zeros((size,size,3),dtype=np.uint8);img[grid==-1]=[55,67,78];img[grid==0]=[221,233,237];img[grid==100]=[30,37,45]
Image.fromarray(img[::-1]).resize((800,800)).save(ROOT/'map-preview.png')
print(json.dumps(meta,indent=2),flush=True)
