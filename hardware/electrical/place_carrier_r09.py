from pathlib import Path
import json,pcbnew as p
BASE=Path(__file__).resolve().parent/'Carrier-r09';LIB=Path(r'C:\Users\samja\AppData\Local\Programs\KiCad\10.0\share\kicad\footprints')
b=p.BOARD();b.SetCopperLayerCount(2)
def xy(x,y):return p.VECTOR2I(p.FromMM(x),p.FromMM(y))
def line(x,y,x2,y2,layer=p.F_SilkS,width=.15):
 a=p.PCB_SHAPE();a.SetShape(p.SHAPE_T_SEGMENT);a.SetStart(xy(x,y));a.SetEnd(xy(x2,y2));a.SetWidth(p.FromMM(width));a.SetLayer(layer);b.Add(a)
def rect(x,y,w,h,layer=p.F_SilkS):
 for a,c in [((x,y),(x+w,y)),((x+w,y),(x+w,y+h)),((x+w,y+h),(x,y+h)),((x,y+h),(x,y))]:line(*a,*c,layer)
def text(t,x,y,size=1):
 a=p.PCB_TEXT(b);a.SetText(t);a.SetPosition(xy(x,y));a.SetTextSize(xy(size,size));a.SetTextThickness(p.FromMM(.15));a.SetLayer(p.F_SilkS);b.Add(a)
parts=json.loads((BASE/'placement.json').read_text());nets={}
for name in sorted({n for a in parts for n in a['nets'].values() if n}):n=p.NETINFO_ITEM(b,name);b.Add(n);nets[name]=n
for a in parts:
 if a['ref']=='U3':
  f=p.FOOTPRINT(b);f.SetFPID(p.LIB_ID('UnderBotCarrier','D24V50F5'))
  # Source uses bottom-view connector coordinates; mirror them into top view.
  for i in range(5):
   pad=p.PAD(f);pad.SetNumber(str(i+1));pad.SetAttribute(p.PAD_ATTRIB_PTH);pad.SetShape(p.PAD_SHAPE_CIRCLE);pad.SetSize(xy(1.8,1.8));pad.SetDrillSize(xy(1.1,1.1));pad.SetLayerSet(p.PAD.PTHMask());pad.SetPosition(xy(5.715+2.54*i,19.05));f.Add(pad)
  for x,y in [(2.159,18.161),(15.621,2.159)]:
   pad=p.PAD(f);pad.SetAttribute(p.PAD_ATTRIB_NPTH);pad.SetShape(p.PAD_SHAPE_CIRCLE);pad.SetSize(xy(2.2,2.2));pad.SetDrillSize(xy(2.2,2.2));pad.SetLayerSet(p.PAD.PTHMask());pad.SetPosition(xy(x,y));f.Add(pad)
  for v,z in [((0,0),(17.78,0)),((17.78,0),(17.78,20.32)),((17.78,20.32),(0,20.32)),((0,20.32),(0,0))]:
   sh=p.PCB_SHAPE(f);sh.SetShape(p.SHAPE_T_SEGMENT);sh.SetStart(xy(*v));sh.SetEnd(xy(*z));sh.SetWidth(p.FromMM(.15));sh.SetLayer(p.F_SilkS);f.Add(sh)
  libdir=BASE/'UnderBotCarrier.pretty';libdir.mkdir(exist_ok=True)
  p.FootprintSave(str(libdir),f)
 else:
  lib,name=a['footprint'].split(':');f=p.FootprintLoad(str(LIB/(lib+'.pretty')),name)
 f.SetReference(a['ref']);f.SetValue(a['value']);f.SetPosition(xy(a['x'],a['y']));f.Value().SetVisible(False)
 for pad in f.Pads():
  net=a['nets'].get(pad.GetNumber());
  if net:pad.SetNet(nets[net])
 b.Add(f)
rect(50,50,200,180,p.Edge_Cuts)
rect(80,70,87,57);text('A1: 52Pi EP-0225',123.5,88,1.5);text('87 x 57 mm / STANDOFFS',123.5,96);text('MOUNT HOLES NOT RELEASED',123.5,104);text('USB-C OUT -> PI',123.5,116)
rect(180,75,52.5,90);text('A2: DDR-60G-12',206.25,93,1.3);text('52.5 x 90 mm',206.25,101);text('DIN RAIL + BACKING',206.25,115);text('58.4 mm projection',206.25,124);text('VERTICAL / AIRFLOW',206.25,143);text('MOUNT HOLD',206.25,153)
# Rail bounding envelope is mechanical information, not a fabricated drilling pattern.
rect(173,106,66,35,p.Dwgs_User)
text('INPUT',63,77);text('STOP LOOP',64,209);text('SEND+ RETURN+',66,213,.8)
for t,x,y in [('PI VIN',163,154),('DDR VIN',193,195),('DDR12V RETURN',224,71),('KINECT12V',233,210),('ARM VIN',108,224),('AUX5V',158,221),('U3 AUX5V',151,164)]:text(t,x,y,.9)
text('UNDERBOT CONVERTER CARRIER r09',151,56,1.5)
text('UNROUTED / REVIEW ONLY',188,222,1.1)
b.BuildConnectivity();p.SaveBoard(str(BASE/'UnderBot.kicad_pcb'),b)
(BASE/'fp-lib-table').write_text('(fp_lib_table (version 7) (lib (name "UnderBotCarrier") (type "KiCad") (uri "${KIPRJMOD}/UnderBotCarrier.pretty") (options "") (descr "Candidate converter footprint; physical overlay check required")))')
assert len(list(b.GetFootprints()))==17
(BASE/'validation.json').write_text(json.dumps({'footprints':17,'tracks':len(list(b.GetTracks())),'size_mm':[200,180],'status':'UNROUTED / MOUNTING GEOMETRY HOLDS','drc':'not completed; no pass claimed'},indent=2))
print('Saved carrier:17 footprints; module envelopes;200x180mm')
