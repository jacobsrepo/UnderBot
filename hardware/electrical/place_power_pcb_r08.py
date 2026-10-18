"""Run with KiCad bundled Python; creates an honest unrouted placement board."""
from pathlib import Path
import json,pcbnew as p
BASE=Path(__file__).resolve().parent/'Power-PCB-r08'
LIB=Path(r'C:\Users\samja\AppData\Local\Programs\KiCad\10.0\share\kicad\footprints')
b=p.BOARD();b.SetCopperLayerCount(2)
def xy(x,y):return p.VECTOR2I(p.FromMM(x),p.FromMM(y))
parts=json.loads((BASE/'placement.json').read_text())
nets={}
for name in sorted({n for a in parts for n in a['nets'].values()}):
 n=p.NETINFO_ITEM(b,name);b.Add(n);nets[name]=n
for a in parts:
 lib,fp=a['footprint'].split(':');f=p.FootprintLoad(str(LIB/(lib+'.pretty')),fp)
 assert f is not None,a['footprint']
 f.SetReference(a['ref']);f.SetValue(a['value']);f.SetPosition(xy(a['x'],a['y']));f.SetOrientationDegrees(a['angle']);f.Value().SetVisible(False)
 for pad in f.Pads():
  if pad.GetNumber() in a['nets']:pad.SetNet(nets[a['nets'][pad.GetNumber()]])
 b.Add(f)
for a,z in [((50,50),(150,50)),((150,50),(150,140)),((150,140),(50,140)),((50,140),(50,50))]:
 e=p.PCB_SHAPE();e.SetShape(p.SHAPE_T_SEGMENT);e.SetStart(xy(*a));e.SetEnd(xy(*z));e.SetWidth(p.FromMM(.1));e.SetLayer(p.Edge_Cuts);b.Add(e)
def text(t,x,y,size=1):
 o=p.PCB_TEXT(b);o.SetText(t);o.SetPosition(xy(x,y));o.SetTextSize(xy(size,size));o.SetTextThickness(p.FromMM(.15));o.SetLayer(p.F_SilkS);b.Add(o)
text('UNDERBOT POWER r08',100,54,1.3)
text('PLACEMENT ONLY - UNROUTED',100,137,1)
text('J1: INPUT + / GND',72,75)
text('J2: SEND+ / RETURN+',72,109)
text('NO GND AT J2',70,112)
text('MAIN FUSE + STOP',72,121)
text('ARE EXTERNAL',72,124)
for label,y in [('PI',60),('KINECT',80),('ARM',105),('AUX',125)]:text(label,124,y+7,1)
text('ALWAYS POWERED',106,70,.8);text('STOP-SWITCHED',106,115,.8)
b.BuildConnectivity();p.SaveBoard(str(BASE/'UnderBot.kicad_pcb'),b)
assert len(list(b.GetFootprints()))==14
assert len(list(b.GetTracks()))==0
(BASE/'placement-validation.json').write_text(json.dumps({'footprints':14,'copper_tracks':0,'outline_mm':[100,90],'status':'UNROUTED - NOT FOR FABRICATION','net_count':len(nets)},indent=2))
print('Saved 100x90mm board;14 footprints;assigned nets;0 routed tracks.')
