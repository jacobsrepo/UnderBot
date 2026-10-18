"""Create a separate, unrouted power-distribution PCB placement and matching circuit."""
from pathlib import Path
import json,csv,sys
import build_schematic_r05 as k
BASE=Path(__file__).resolve().parent
OUT=BASE/'Power-PCB-r08';OUT.mkdir(exist_ok=True)
k.OUT=OUT;k.CROSS.clear()
TERM='TerminalBlock_Phoenix:TerminalBlock_Phoenix_MKDS-1,5-2-5.08_1x02_P5.08mm_Horizontal'
FUSE='Fuse:Fuseholder_Blade_Mini_Keystone_3568'
HOLE='MountingHole:MountingHole_3.2mm_M3'
parts=[]
def rec(ref,value,fp,nets,x,y,angle=0):parts.append(dict(ref=ref,value=value,footprint=fp,nets=nets,x=x,y=y,angle=angle))
s=k.Sheet('Distribution','UnderBot - standalone fused distribution board r08')
s.note(15,12,'POWER DISTRIBUTION PCB | PLACEMENT DRAFT - NOT FOR FABRICATION',2)
s.note(15,24,'Input is NOCO 12V OUT via approved cable, EXTERNAL main fuse, service disconnect and qualified polarity protection.')
s.conn('J1','INPUT + / GND',55.88,60.96,['VIN_PROTECTED','GND_SYS'])
rec('J1','Phoenix 1715721 INPUT',TERM,{'1':'VIN_PROTECTED','2':'GND_SYS'},58,65)
s.conn('J2','STOP LOOP: pin1 SEND+ / pin2 RETURN+ (NO GND)',208.28,60.96,['VIN_PROTECTED','ACT_SWITCHED'])
rec('J2','Phoenix 1715721 STOP LOOP',TERM,{'1':'VIN_PROTECTED','2':'ACT_SWITCHED'},58,100)
s.note(240,45,'J2 goes to off-board normally-open power contact.\nExternal hardwired stop + manual reset must control it.\nNO permanent bridge. This is NOT a logic input.\nBoth terminals are POSITIVE rails; neither is ground.',1.27)
for i,(name,source,net,sy,by) in enumerate([('PI MODULE','VIN_PROTECTED','PI_12',111.76,60),('KINECT CONDITIONER','VIN_PROTECTED','DEPTH_12',149.86,80),('ARM VIN','ACT_SWITCHED','ARM_12',187.96,105),('AUX CONVERTER','ACT_SWITCHED','AUX_12',226.06,125)],1):
 ref=f'F{i}';s.add('Device:Fuse',ref,'MINI fuse rating HOLD',96.52,sy,90)
 s.net(ref,1,source,-20.32);s.net(ref,2,net,20.32)
 s.conn(f'J{i+2}',name+' + / GND',223.52,sy,[net,'GND_SYS'])
 rec(ref,'Keystone3568 / fuse TBD',FUSE,{'1':source,'2':net},104,by)
 rec(f'J{i+2}','Phoenix1715721 '+name,TERM,{'1':net,'2':'GND_SYS'},132,by)
 s.note(245,sy-3,{'PI MODULE':'52Pi EP-0225 DC input -> supplied USB-C cable -> Pi5.','KINECT CONDITIONER':'12V regulation/adapter matching still requires qualification.','ARM VIN':'Documented Adeept VIN6-24V; verify revision + USB VBUS block.','AUX CONVERTER':'5V converter -> audio and camera pan/tilt. All aux stops with arm.'}[name],1.1)
s.note(15,258,'Converter modules are OFF-BOARD. Board distributes nominal12V; it does NOT directly provide5V or3.3V.',1.4)
s.note(15,269,'T12 has independent battery/stop. All fuse values, wire ratings, input protection and current limits remain release holds.',1.4)
for i,(x,y) in enumerate([(55,55),(145,55),(55,135),(145,135)],1):
 s.add('Mechanical:MountingHole',f'H{i}','M3 3.2mm',310+i*12.7,226.06)
 rec(f'H{i}','M3',HOLE,{},x,y)
s.save()
p=OUT/'Distribution.kicad_sch';doc=p.read_text(encoding='utf-8')
for pt in parts:
 # Locate symbol using its deterministic uuid, then replace its empty footprint property.
 uid=k.ident(s.name+pt['ref']);start=doc.index('(symbol (lib_id',doc.index('(lib_symbols')+1)
 target='(uuid '+uid+')';pos=doc.index(target)
 fpos=doc.index('(property "Footprint" ""',pos)
 doc=doc[:fpos]+doc[fpos:].replace('(property "Footprint" ""','(property "Footprint" '+k.q(pt['footprint']),1)
doc=doc.replace('0.5 PROCUREMENT','0.8 PLACEMENT')
p.write_text(doc,encoding='utf-8')
root=f'''(kicad_sch (version 20250114) (generator "eeschema") (uuid {k.ROOT}) (paper "A3") (lib_symbols)
(sheet (at 40 60) (size 180 50) (stroke (width 0.254) (type default)) (fill (color 0 0 0 0)) (uuid {s.sheetid})
(property "Sheetname" "Power distribution PCB circuit" (at 40 58 0) (effects (font (size 1.5 1.5)) (justify left bottom)))
(property "Sheetfile" "Distribution.kicad_sch" (at 40 112 0) (effects (font (size 1.5 1.5)) (justify left top)))
(instances (project "UnderBot" (path "/{k.ROOT}" (page "2")))))
(text "r08 - POWER DISTRIBUTION PCB / UNROUTED PLACEMENT / NOT FOR FABRICATION" (at 20 25 0) (effects (font (size 2 2)) (justify left top)) (uuid {k.ident('r08-title')}))
(sheet_instances (path "/" (page "1"))) (embedded_fonts no))'''
(OUT/'UnderBot.kicad_sch').write_text(root,encoding='utf-8')
(OUT/'UnderBot.kicad_pro').write_text(json.dumps({'meta':{'filename':'UnderBot.kicad_pro','version':1}}))
(OUT/'placement.json').write_text(json.dumps(parts,indent=2))
with (OUT/'pcb-bom.csv').open('w',newline='',encoding='utf-8-sig') as f:
 w=csv.writer(f);w.writerow(['Reference','Part','Qty','Status','Source'])
 w.writerows([['J1-J6','Phoenix Contact1715721 MKDS1,5/2-5,08',6,'Selected footprint candidate; drawing/mating/torque verification before release','https://mall.phoenixcontact.com.cn/commodity/detail/MKDS1%2C5-2-5%2C08-1715721'],['F1-F4 holder','Keystone3568 MINI blade fuse holder',4,'Selected holder candidate; compare manufacturer drawing before fabrication','https://www.keyelco.com/product-pdf.cfm?p=306'],['F1-F4 fuse','Littelfuse297 MINI32V series; amperages TBD',4,'Do not select amperages solely from average load. Startup, wire and interruption coordination required.','https://www.littelfuse.com/ja-jp/products/fuses-overcurrent-protection/fuses/automotive-fuses/blade-fuses-shunt/mini/297/0297005-wxmx'],['H1-H4','M3 mounting hardware / insulating standoffs',4,'Select enclosure height and clearance',''],['External','Pololu D24V50F5 #2851 auxiliary5V candidate',1,'Typical up to5A subject to thermal derating; compare budget and load before order','https://www.pololu.com/product/2851/specs']])
notes='''# UnderBot power-distribution PCB r08

**UNROUTED PLACEMENT DRAFT — NOT FOR FABRICATION.** This is the first physical PCB artifact, not a working board. No Gerbers released. All converter modules are external, connected by rated harnesses; this board distributes fused nominal12V. It does not yet mount converters or generate5V/3.3V itself.

## Board and circuit
100 x90 mm outline; two copper layers proposed; four3.2mm mounting holes. Six2-way terminals and four MINI fuse holders. Footprints have assigned nets and schematic references. Ratsnest/unconnected DRC findings are expected because copper routing has deliberately not been finalized before protection/current/connector review. A3 circuit PDF accompanies the PCB.

J1 pin1 = protected input positive; pin2 = ground. NOCO approved accessory cable, external main fuse, disconnect and qualified polarity protection are REQUIRED before J1; this PCB does not implement those yet.

J2 pin1 = positive send to EXTERNAL stop power contact; pin2 = switched positive return. **Neither J2 terminal is ground.** A permanent bridge would defeat the intended stop architecture. The external normally-open contact must have a qualified hardwired manual-reset controller. This circuit does not implement a complete emergency-stop system.

J3 pin1 = fused supply to Pi module, J4 pin1 = fused supply to Kinect conditioner, J5 pin1 = fused supply to Adeept VIN, J6 pin1 = fused supply to auxiliary converter. Pin2 of J3-J6 is ground. Actual auxiliary converter, connector wire sizes and fuse values pending qualification. All auxiliary power (including audio) now stops with arm power, so camera pan/tilt has no live auxiliary bypass. Pi and Kinect remain powered while the external motion contact opens.

T12 remains independent: the board does not stop its wheels. Its separate drive-stop interface must be resolved. Adeept USB VBUS must be blocked without interrupting required data; otherwise Pi USB can bypass arm power interruption.

## Specific component progress
- Six Phoenix1715721 5.08mm screw terminals selected as footprint candidates. Manufacturer nominal current is17.5A under specified conditions; this does NOT rate PCB traces or connected wires.
- Four Keystone3568 MINI fuse holders selected as footprint candidates.
- Littelfuse29732V MINI fuse family selected; exact amperages intentionally not guessed. The linked5A part demonstrates the family, NOT a released fuse choice for all branches.
- Pololu D24V50F5 is a concrete auxiliary5V candidate, specified typical up to5A with thermal limits. Its current USD32.95 listing exceeds the old EUR15 allowance; the shopping budget needs a landed quote before substitution. Do not claim current r07 total includes this price.
- Kinect converter and stop/reset hardware remain open selections.

## Before routing/release
Check mounting envelope and cable exit directions; compare terminal/fuse mechanical drawings; verify input polarity protection; measure NOCO output envelope and interruption behaviour; verify arm revision/backfeed/peaks, Kinect label/startup and pan/tilt load; choose stop power contacts and wire/fuse coordination; then set copper thickness/width/clearance and route. No trace ampacity or total PCB current rating is claimed at placement stage.

Next PCB step is routing once those design inputs are defensible. There are no purchases, fabrication uploads or live hardware changes in this revision.
'''
(OUT/'README.md').write_text(notes,encoding='utf-8')
print('Created matching distribution circuit and placement manifest:',OUT)
