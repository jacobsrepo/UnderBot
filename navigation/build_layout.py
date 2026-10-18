import json
from pathlib import Path
ROOT=Path(__file__).resolve().parent
d=json.loads((ROOT.parent/'robot_station/underbot-station.json').read_text())
room=d['configById']['3D!room']
room.update({'title':'SIMULATION — public 3D map + A* route','followTf':'map','cameraState':{'perspective':True,'distance':48,'phi':.6,'thetaOffset':.3,'targetOffset':[0,0,0]},'publish':{'type':'pose','poseTopic':'/station/nav/goal','goalTopic':'/station/nav/goal','pointTopic':'/clicked_point'},'topics':{'/navigation/pointcloud':{'visible':True,'pointSize':2,'colorMode':'colormap','colorField':'z','colorMap':'turbo'},'/map':{'visible':False},'/navigation/robot':{'visible':True},'/plan':{'visible':True,'color':'#ffcc22','lineWidth':.1},'/navigation/goal':{'visible':True},'/odom':{'visible':True}}})
d['configById']['Image!camera']['imageMode']['imageTopic']='/camera/emeet/image/compressed'
d['configById']['Image!perception']['imageMode']['imageTopic']='/perception/emeet/annotated/compressed'
d['configById']['Image!camera']['title']='Existing EMEET camera'
d['configById']['Image!perception']['title']='Existing perception'
(ROOT/'underbot-navigation-layout.json').write_text(json.dumps(d,indent=2))
print('Generated navigation layout; camera panels retained.')
