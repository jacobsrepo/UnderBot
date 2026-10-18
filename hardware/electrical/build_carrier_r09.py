"""Converter-carrier schematic and mechanically explicit placement manifest."""
from pathlib import Path
import json,csv,html
import build_schematic_r05 as k
BASE=Path(__file__).resolve().parent;OUT=BASE/'Carrier-r09';OUT.mkdir(exist_ok=True)
k.OUT=OUT;k.CROSS.clear()
TERM='TerminalBlock_Phoenix:TerminalBlock_Phoenix_MKDS-1,5-2-5.08_1x02_P5.08mm_Horizontal'
FUSE='Fuse:Fuseholder_Blade_Mini_Keystone_3568';HOLE='MountingHole:MountingHole_3.2mm_M3'
parts=[]
def record(ref,value,fp,nets,x,y):parts.append(dict(ref=ref,value=value,footprint=fp,nets=nets,x=x,y=y,angle=0))
s=k.Sheet('Carrier','NOCO converter carrier r09 - module integration')
s.note(12,12,'CONVERTER CARRIER r09 | DESIGN REVIEW / UNROUTED',2)
s.note(12,22,'NOCO12V accessory output only. External main protection/disconnect and manual-reset stop still require final design.')
def conn(ref,title,x,y,nets,bx,by):
 s.conn(ref,title,x,y,nets);record(ref,title,TERM,{str(i+1):n for i,n in enumerate(nets)},bx,by)
conn('J1','Protected12V input + / GND',50.8,50.8,['VIN','GND'],60,66)
conn('J2','Stop contact SEND+ / RETURN+ (NO GND)',182.88,50.8,['VIN','ACT'],60,200)
for i,(bus,net,x,y,bx,by) in enumerate([('VIN','PI_IN',50.8,88.9,62,95),('VIN','KINECT_IN',50.8,119.38,62,135),('ACT','ARM_IN',50.8,149.86,85,195),('ACT','AUX_IN',50.8,180.34,110,170)],1):
 s.add('Device:Fuse',f'F{i}','MINI current rating HOLD',x,y,90);s.net(f'F{i}',1,bus,-12.7);s.net(f'F{i}',2,net,12.7)
 record(f'F{i}','Keystone3568 / fuse TBD',FUSE,{'1':bus,'2':net},bx,by)
conn('J3','Short DC cable to mounted EP-0225',132.08,88.9,['PI_IN','GND'],160,145)
conn('J4','DDR input: +Vin5 / -Vin6',132.08,119.38,['KINECT_IN','GND'],190,185)
conn('J5','DDR output return: +Vo3 / -Vo1',132.08,149.86,['DEPTH_12','GND'],222,62)
conn('J6','Regulated12V to Kinect v2 adapter',132.08,180.34,['DEPTH_12','GND'],230,200)
conn('J7','Stopped nominal12V to Adeept VIN',132.08,210.82,['ARM_IN','GND'],105,215)
conn('J8','Stopped regulated5V AUX output',132.08,246.38,['AUX_5V','GND'],155,210)
lid=k.module_library('Aux_Pololu_D24V50F5',['EN','VIN','GND1','GND2'],['VOUT'])
s.add(lid,'U3','Pololu D24V50F5 #2851',236.22,226.06)
s.nc('U3','EN');s.net('U3','VIN','AUX_IN');s.net('U3','GND1','GND');s.net('U3','GND2','GND');s.net('U3','VOUT','AUX_5V',10.16)
record('U3','D24V50F5 module', 'UnderBotCarrier:D24V50F5',{'1':'','2':'AUX_IN','3':'GND','4':'GND','5':'AUX_5V'},142,172)
lid=k.module_library('Pi_EP0225',['DC_PLUS','DC_MINUS'],['USB_C_PD'])
s.add(lid,'A1','52Pi EP-0225 mounted on standoffs',294.64,71.12,onboard=False)
s.net('A1','DC_PLUS','PI_IN');s.net('A1','DC_MINUS','GND');s.net('A1','USB_C_PD','USB_C_TO_PI',10.16)
lid=k.module_library('Kinect_DDR60G12',['5_VIN_PLUS','6_VIN_MINUS'],['3_VOUT_PLUS','1_VOUT_MINUS'])
s.add(lid,'A2','Mean Well DDR-60G-12 / rail mounting',294.64,132.08,onboard=False)
s.net('A2','5_VIN_PLUS','KINECT_IN');s.net('A2','6_VIN_MINUS','GND');s.net('A2','3_VOUT_PLUS','DEPTH_12',10.16);s.net('A2','1_VOUT_MINUS','GND',10.16)
s.note(196,165,'DDR terminals2 and4 duplicate output -/+; unused.\nOutput negative intentionally joins system ground here.\nThis assembly does not preserve galvanic isolation.\nSet output12.0V and verify before plugging in Kinect.',1.2)
s.note(15,273,'A1/A2 use short harnesses within the assembly; no invented PCB electrical pin footprint. U3 is a soldered daughterboard.',1.25)
for i,(x,y) in enumerate([(55,55),(245,55),(55,225),(245,225)],1):
 s.add('Mechanical:MountingHole',f'H{i}','M3',330+i*12.7,232);record(f'H{i}','M3',HOLE,{},x,y)
auxid='UnderBot_Modules:Aux_Pololu_D24V50F5'
for number,pin in enumerate(['EN','VIN','GND1','GND2','VOUT'],1):
 s.libs[auxid]=s.libs[auxid].replace('(number '+k.q(pin)+' ', '(number '+k.q(number)+' ')
s.save();p=OUT/'Carrier.kicad_sch';doc=p.read_text(encoding='utf-8')
for pt in parts:
 pos=doc.index('(uuid '+k.ident(s.name+pt['ref'])+')');j=doc.index('(property "Footprint" ""',pos)
 doc=doc[:j]+doc[j:].replace('(property "Footprint" ""','(property "Footprint" '+k.q(pt['footprint']),1)
doc=doc.replace('0.5 PROCUREMENT','0.9 CARRIER')
p.write_text(doc,encoding='utf-8')
(OUT/'UnderBot.kicad_sch').write_text(f'''(kicad_sch (version 20250114) (generator "eeschema") (uuid {k.ROOT}) (paper "A3") (lib_symbols)
(sheet (at 30 55) (size 185 45) (stroke (width 0.254) (type default)) (fill (color 0 0 0 0)) (uuid {s.sheetid})
(property "Sheetname" "Converter carrier circuit r09" (at 30 53 0) (effects (font (size 1.5 1.5)) (justify left bottom)))
(property "Sheetfile" "Carrier.kicad_sch" (at 30 102 0) (effects (font (size 1.5 1.5)) (justify left top)))
(instances (project "UnderBot" (path "/{k.ROOT}" (page "2")))))
(text "NOCO + T12 / CONVERTER CARRIER / MECHANICAL & ELECTRICAL REVIEW" (at 20 25 0) (effects (font (size 2 2)) (justify left top)) (uuid {k.ident('r09title')}))
(sheet_instances (path "/" (page "1"))) (embedded_fonts no))''',encoding='utf-8')
(OUT/'UnderBot.kicad_pro').write_text(json.dumps({'meta':{'filename':'UnderBot.kicad_pro','version':1}}))
(OUT/'placement.json').write_text(json.dumps(parts,indent=2))

# Price allocations updated transparently; do not silently drop sensors to force a total.
with (BASE/'UnderBot-r07/parts.csv').open(encoding='utf-8-sig') as f:r=list(csv.reader(f))
headers=r.pop(0)
for row in r:
 name=row[1]
 if name.startswith('Separate 5 V'):
  row[1]='Pololu D24V50F5 #2851 auxiliary module';row[3]='45';row[4]='45';row[6]='45';row[7]='6-38V in / 5V out';row[8]='5A typical, thermal limited';row[10]='Selected; EUR45 allowance, not quote'
 elif name.startswith('Kinect 12 V regulation'):
  row[1]='Mean Well DDR-60G-12 Kinect supply module';row[3]='35';row[4]='35';row[6]='35';row[7]='9-36V in / regulated12V out';row[8]='4.25A at <=18V input, <=50C vertical';row[9]='51W under those conditions';row[10]='Selected; EUR35 allowance, not quote'
 elif name.startswith('Distribution PCB prototype'):
  row[1]='Carrier PCB + rail/standoffs/mounting allowance';row[3]='45';row[4]='45';row[6]='45';row[10]='Fabrication HOLD; EUR45 allowance'
 elif name.startswith('Delivery and contingency'):row[6]='0';row[3]='0';row[4]='0';row[10]='Reserve exhausted under current allowances'
hardware=round(sum(float(row[6]) for row in r),2)
with (OUT/'updated-budget.csv').open('w',newline='',encoding='utf-8-sig') as f:w=csv.writer(f);w.writerow(headers);w.writerows(r)
sources=[('Pi supply','52Pi EP-0225','87x57mm; mounting centres unpublished','https://wiki.52pi.com/index.php?title=EP-0225'),('Depth supply','Mean Well DDR-60G-12','52.5x90x54.5mm body;58.4mm max projection;DIN TS35','https://www.meanwell.com/Upload/PDF/DDR-60/DDR-60-SPEC.PDF'),('Aux supply','Pololu D24V50F5 #2851','17.8x20.3x8.8mm;2.54mm electrical pitch','https://www.pololu.com/product/2851'),('Aux footprint drawing','Pololu drawing0J1436','Top vs bottom view mirrored correctly; dimensions from mil values','https://www.pololu.com/file/0J1436/d24v50f5-step-down-voltage-regulator-dimensions.pdf')]
with (OUT/'module-selection.csv').open('w',newline='',encoding='utf-8-sig') as f:w=csv.writer(f);w.writerow(['Purpose','Model','Mechanics','Source']);w.writerows(sources)
notes=f'''# r09 converter carrier — review draft

## What changed
The power assembly now reserves physical locations for the Pi, Kinect and auxiliary converter modules on a200x180mm carrier. This larger outline is provisional and reflects real module sizes rather than the old100x90mm fuse-only board. The T12 battery stays separate. One Adeept arm still uses its onboard regulator after controller revision/USB-backfeed verification.

Electrical: Pi fuse -> J3 -> EP-0225 DC input -> supplied USB-C cable to Pi. Kinect fuse -> J4 -> DDR terminal5+ and6-; DDR terminals3+ and1- -> J5 -> J6 -> Kinect v2 adapter. Terminal2(-) and4(+) unused duplicates. U3 auxiliary module mounts directly via soldered pins -> J8 regulated5V. Arm J7 remains switched nominal12V. J2 remains the external manual-reset stop contact interface; both pins positive, no ground. Aux/audio/pan-tilt stop with arm. System GND deliberately bonds DDR negative output and input: isolation is not claimed.

## Module decisions and mechanical evidence
1. 52Pi EP-0225 is87x57mm per official labelled photograph. Accepts9-24V and supplies5.15V/5A USB-C PD. It will sit above the carrier on standoffs with short DC cable. Exact mounting-hole centre coordinates are NOT published in reviewed material: an outline and access allowance are drawn, but holes are NOT invented/drilled. Obtain physical measurements or vendor CAD. Preserve button/switch and USB cable access. Barrel-size conflict in vendor pages remains unresolved.
2. Mean Well DDR-60G-12 is9-36V input,12V output. The headline60W/5A requires appropriate conditions: at input9-18V its curve allows85%, i.e.51W/4.25A up to50C in specified vertical mounting. Higher temperature requires further derating. This has more provision than the provisional36W Kinect supply budget, but exact adapter/startup demand still needs verifying. Body52.5x90x54.5mm with58.4mm maximum projection;216g. This is a bulky DIN-rail part, selected for documented input range/rating rather than compactness. A short TS35 rail and backing support are required; no solder-in footprint is claimed. The diagram reserves its space; rail fastener holes await actual rail/end-stop selection. Support load through enclosure standoffs/backing, not unsupported FR4. Observe installation spacing and vertical orientation; flat mounting requires separate thermal qualification.
3. Pololu D24V50F5 #2851:6-38V input,5V fixed output (4% accuracy), typical up to5A subject to heat.17.8x20.3x8.8mm. New carrier footprint from official drawing, with top-view left-to-right pins EN,VIN,GND,GND,VOUT. NC EN permits normal enable. Two ground pins connect. Use directly soldered adequately rated pins, not an unqualified removable header at5A. Underside component clearance and module elevation require checking. The footprint remains a candidate until1:1 physical overlay verification.

## Budget impact — not hidden
Updated hardware allocations: EUR{hardware:.2f}, before a delivery reserve. That is EUR{hardware-600:.2f} above the EUR600 cap. Changes: auxiliary converter allowance15->45; carrier/mechanics30->45; Kinect module allowance remains35. Earlier35.31 reserve absorbs most but not all increase. These are allowances, not final landed quotations. Options to recover budget: defer microphone allowance20, or defer one/two ToF boards at20 each. No items are silently removed; no purchase or fabrication has occurred. Prefer recovery through actual quotes first. The oldEUR600 table no longer establishes affordability of this revision.

## Still unresolved before routing/fabrication
Physical Pi/rail mount geometry, enclosure cooling/clearance, stop power-contact/reset hardware and independent T12 stop, input polarity/transient protection, fuse amperages/wire fault coordination, NOCO operating output range, arm revision/USB VBUS blocking, Kinect adapter polarity/current. Modules are selected candidates, not hardware-qualified. Copper is UNROUTED; no trace ampacity, DRC pass or fabrication readiness claimed. No Gerbers generated.

Sources and local downloaded diagrams are in module-selection.csv and vendor/. Board preview silhouettes are placement envelopes, not detailed manufacturer3D models. r09 supersedes the physical r08 placement; r07 remains the whole-system context with its old power-module choices superseded here.
'''
(OUT/'README.md').write_text(notes,encoding='utf-8')
print('Created carrier circuit + manifest; hardware allowance EUR',hardware)
