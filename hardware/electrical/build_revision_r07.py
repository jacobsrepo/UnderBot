"""NOCO + OEM T12 architecture, review drawing and linked KiCad draft."""
from pathlib import Path
import json,csv,html
import xlsxwriter
import build_schematic_r05 as k
BASE=Path(__file__).resolve().parent
OUT=BASE/'UnderBot-r07';OUT.mkdir(exist_ok=True)
k.OUT=OUT;k.CROSS.clear()
k.CROSS.update({'GND_SYS','NOCO_FUSED','SYS_12','PI_INPUT','DEPTH_INPUT','ACT_INPUT','AUX_INPUT','ARM_FEED_TBD','AUX_5V','PI_3V3','PI_SDA','PI_SCL'})
k.CROSS.update({'PI_POWER_CABLE','KINECT_12_TBD'})
q=k.q

# Fresh integration draft; not a modification of historical 6S circuitry.
s=k.Sheet('01_Power','01 - NOCO input and distribution PCB boundary')
s.note(15,12,'NOCO GB70 + T12 OEM BATTERY | r07 DESIGN REVIEW',2)
s.note(15,22,'Use GB70 12V OUT accessory port and approved accessory cable. Never use jump-start clamps or override.')
s.conn('J101','GB70 accessory harness IN',55.88,50.8,['NOCO_RAW','GND_SYS'])
s.add('Device:Fuse','F101','Main fuse TBD - harness coordination',114.3,50.8,90,onboard=False)
s.net('F101',1,'NOCO_RAW',-15.24);s.net('F101',2,'NOCO_FUSED',15.24)
s.add('Switch:SW_SPST','SW101','Service disconnect / DC rated',218.44,50.8,onboard=False)
s.net('SW101',1,'NOCO_FUSED',-15.24);s.net('SW101',2,'SYS_12',15.24)
s.note(15,82,'Proposed PCB: input/output terminals, branch fuses, test points and ground distribution. Converter modules may be off-board.')
for i,(name,net) in enumerate([('PI branch','PI_INPUT'),('KINECT branch','DEPTH_INPUT'),('ACTUATOR branch','ACT_INPUT'),('AUXILIARY branch','AUX_INPUT')]):
 x=55.88+i*96.52;ref=f'F10{i+2}'
 s.add('Device:Fuse',ref,name+' / rating TBD',x,119.38)
 s.net(ref,1,'SYS_12',0,-10.16);s.net(ref,2,net,0,10.16)
 s.conn(f'J10{i+2}',name+' output',x+15.24,162.56,[net,'GND_SYS'])
s.note(15,193,'NOCO nominal output: 12V / up to 15A. This is NOT a chosen fuse rating; branch currents and transient tests determine protection.')
s.note(15,205,'Input reverse-polarity / transient protection: DESIGN HOLD. Select after measuring GB70 output range and source shutdown.')
s.note(15,217,'NO CHARGING THROUGH THIS PCB. Charge NOCO separately using its specified input. Do not connect a 25.2V charger.')
s.note(15,229,'STOP HOLD: actuator branch requires hardwired manual-reset interruption. OEM T12 drive stop is separate and unverified.')
s.note(15,241,'This sheet specifies distribution interfaces. No PCB footprints, copper widths or fabrication files have been released.')

s=k.Sheet('02_Conversion','02 - Converters, stop interfaces and power cables')
s.note(15,12,'COMMERCIAL POWER MODULES | PORT-LEVEL CONNECTIONS',2)
def module(name,ref,value,x,y,left,right,lnets,rnets):
 lid=k.module_library(name,left,right);s.add(lid,ref,value,x,y,onboard=False)
 for pin,net in zip(left,lnets):s.net(ref,pin,net,-10.16) if net else s.nc(ref,pin)
 for pin,net in zip(right,rnets):s.net(ref,pin,net,10.16) if net else s.nc(ref,pin)
module('Pi_PD','A201','52Pi EP-0225 / DC input ONLY',86.36,71.12,['DC_PLUS','DC_MINUS'],['USB_C_PD'],['PI_INPUT','GND_SYS'],['PI_POWER_CABLE'])
s.note(150,45,'9-24V DC input -> USB-C PD 5.15V / 5A.\nUse supplied USB-C cable to Pi 5.\nVendor pages disagree on barrel dimensions:\nverify actual connector before ordering harness.',1.27)
module('Depth_supply','A202','12V conditioning / qualification HOLD',86.36,139.7,['IN_PLUS','IN_MINUS'],['OUT_PLUS','OUT_MINUS'],['DEPTH_INPUT','GND_SYS'],['KINECT_12_TBD','GND_SYS'])
s.note(150,110,'Kinect v2 requires its matching PC adapter.\nDo not assume GB70 is a precision 12V regulator.\nDirect protected feed only after output qualification;\notherwise select 12V buck-boost sized to actual label.',1.27)
module('Stop_assembly','A203','Hardwired stop + reset / HOLD',294.64,71.12,['IN_PLUS','IN_MINUS'],['SWITCHED_PLUS','RETURN'],['ACT_INPUT','GND_SYS'],['ACT_STOPPED','GND_SYS'])
module('Arm_feed','A204','VIN feed / verify documented 6-24V board',294.64,139.7,['IN_PLUS','IN_MINUS'],['OUT_PLUS','OUT_MINUS'],['ACT_STOPPED','GND_SYS'],['ARM_FEED_TBD','GND_SYS'])
s.note(236,173,'Documented controller VIN accepts 6-24V.\nConfirm purchased revision before 12V VIN feed.\nUSB VBUS blocking is mandatory pending verification.',1.27)
module('Aux_regulator','A205','5V auxiliary / current selection HOLD',86.36,226.06,['IN_PLUS','IN_MINUS'],['OUT_PLUS','OUT_MINUS'],['AUX_INPUT','GND_SYS'],['AUX_5V','GND_SYS'])
s.note(150,203,'Auxiliary: speaker amplifiers / pan-tilt servos.\nPan-tilt motor power must also be interrupted on stop;\nits final switching circuit is not released.\nStop/reset must prevent automatic restart and account\nfor arm collapse when torque is removed.',1.27)

s=k.Sheet('03_System','03 - System interfaces and sensor harnesses')
s.note(15,12,'SIGNAL CONNECTIONS | WHOLE ROBOT',2)
module('Pi_ports','A301','Existing Raspberry Pi 5',86.36,86.36,['USB_C_POWER','3V3','GND'],['USB_ARM','USB_DEPTH','USB_SSD','USB_MIC','CSI','I2C_SDA','I2C_SCL','I2S'],['PI_POWER_CABLE','PI_3V3','GND_SYS'],['USB_ARM_DATA','USB_KINECT3','USB_SSD','USB_MIC','CSI_CAMERA','PI_SDA','PI_SCL','I2S_AUDIO'])
module('Arm_kit','A302','Adeept ADA031 kit incl. 6 servos',294.64,53.34,['POWER_PLUS','POWER_MINUS','USB'],['SERVO_LOOM'],['ARM_FEED_TBD','GND_SYS','USB_ARM_BLOCKED'],['KIT_INTERNAL_SERVO_LOOM'])
s.note(236,76,'Use kit internal servo mapping. USB power backfeed\nand emergency-stop behaviour remain qualification holds.',1.27)
module('Depth_camera','A303','Kinect v2 + matching PC adapter',294.64,124.46,['POWER_PLUS','POWER_MINUS','USB3'],[],['KINECT_12_TBD','GND_SYS','USB_KINECT3'],[])
module('USB_block','A306','USB VBUS BLOCK / data preserved / HOLD',86.36,142.24,['PI_USB'],['ARM_USB'],['USB_ARM_DATA'],['USB_ARM_BLOCKED'])
for ref,name,x,y,addr in [('A304','BODY ICM20948 #4554',86.36,198.12,'0x68'),('A305','CAMERA ICM20948 #4554',294.64,198.12,'0x69')]:
 module(ref+'_ports',ref,name,x,y,['VIN','GND','SDA','SCL'],[],['PI_3V3','GND_SYS','PI_SDA','PI_SCL'],[])
 s.note(x-35,226,'Address '+addr+'; strap AD0 per breakout guide.',1.27)
s.note(15,249,'Pi pin mapping: 1=3V3; 3=GPIO2/SDA; 5=GPIO3/SCL; 6=GND. IMU interrupt/reset lines unused in this draft.',1.27)
s.note(15,257,'Additional interfaces: SSD + microphone via USB; Pi camera via correct 22-to-15 pin CSI cable; cooler via fan header.',1.27)
s.note(15,265,'4 ToF sensors require XSHUT sequencing or an I2C mux. Audio I2S and pan/tilt PWM pin assignment still pending.',1.27)

s=k.Sheet('04_Base','04 - Independent T12 base and integration holds')
s.note(15,12,'T12 RETAINS OEM BATTERY + CHARGING SYSTEM',2)
module('T12_OEM','A401','Xiaomi T12 OEM system',101.6,91.44,['OEM_BATTERY','OEM_DOCK'],['WHEELS_ENCODERS','LIDAR','BUMPER_CLIFF','CONTROL_LINK'],['T12_ORIGINAL_PACK','T12_ORIGINAL_DOCK'],['OEM_WHEEL_LOOMS','OEM_LIDAR_LOOM','OEM_SENSOR_LOOMS','T12_CONTROL_TBD'])
s.note(175,49,'Original battery: 14.8V; 3.2Ah nominal / 3.0Ah rated.\nKeep OEM connectors and charging electronics.\nT12 positive power rails never join GB70 positive rails.\nControl/LiDAR protocol and signal-level interface are\nnot verified; no speculative Pi-to-OEM pin wiring.',1.5)
s.note(20,166,'BASE DRIVE STOP IS A RELEASE HOLD. Stopping the arm branch does not stop independently powered wheels.',1.5)
s.note(20,184,'Test OEM command access, navigation data access, added payload and tipping stability before free-moving operation.',1.5)
s.note(20,202,'Vacuum, brushes and mop pump assumed OFF for load estimate; independent control of these functions is unverified.',1.5)
s.note(20,220,'Current prototype baseline: ONE Adeept kit. A second kit is optional after load, mounting and firmware qualification.',1.5)
for sh in k.SHEETS:
 sh.save();p=OUT/(sh.name+'.kicad_sch');p.write_text(p.read_text().replace('0.5 PROCUREMENT','0.7 NOCO REVIEW'),encoding='utf-8')
ri=[]
for i,sh in enumerate(k.SHEETS):
 x=30+(i%2)*195;y=60+(i//2)*75
 ri.append(f'(sheet (at {x} {y}) (size 160 40) (stroke (width 0.254) (type default)) (fill (color 0 0 0 0)) (uuid {sh.sheetid}) (property "Sheetname" {q(sh.title)} (at {x} {y-2} 0) (effects (font (size 1.27 1.27)) (justify left bottom))) (property "Sheetfile" "{sh.name}.kicad_sch" (at {x} {y+42} 0) (effects (font (size 1.27 1.27)) (justify left top))) (instances (project "UnderBot" (path "/{k.ROOT}" (page "{i+2}")))))')
for i,t in enumerate(['UNDERBOT r07 - NOCO + T12 / REVIEW DRAFT','Approved power sources; one Adeept arm baseline; Kinect v2. No new 6S pack.','Port-level module interconnection draft. HOLD labels are unresolved, not approved wiring.','See overall.svg, parts.xlsx and README.md. PCB layout/fabrication not released.']):
 ri.append(f'(text {q(t)} (at 20 {20+i*9 if i<2 else 225+(i-2)*12} 0) (effects (font (size 1.8 1.8)) (justify left top)) (uuid {k.ident("r07note"+str(i))}))')
(OUT/'UnderBot.kicad_sch').write_text(f'(kicad_sch (version 20250114) (generator "eeschema") (uuid {k.ROOT}) (paper "A3") (lib_symbols) {"".join(ri)} (sheet_instances (path "/" (page "1"))) (embedded_fonts no))',encoding='utf-8')
(OUT/'UnderBot.kicad_pro').write_text(json.dumps({'meta':{'filename':'UnderBot.kicad_pro','version':1}}))
with (OUT/'connector-schedule.csv').open('w',newline='') as f:
 w=csv.writer(f);w.writerow(['Sheet','Reference','Pin','Net','Purpose','Status']);w.writerows(k.CONNECTORS)

# Preserve original column layout while replacing obsolete selections.
old=json.loads((BASE/'Budget-r06/budget-data.json').read_text(encoding='utf-8'))
rs=old['rows']
def setrow(starts,**kw):
 r=next(r for r in rs if r['values'][1].startswith(starts));v=r['values']
 for field,idx in [('part',1),('price',3),('fund',6),('v',7),('a',8),('w',9),('need',10)]:
  if field in kw:v[idx]=kw[field]
 if 'note' in kw:r['note']=kw['note']
 if 'url' in kw:r['url']=kw['url']
 return r
setrow('Waveshare',part='Adeept ADA031 5-DOF arm kit — assemble/calibrate',price=69.99,fund=69.99,v='VIN6-24V documented; verify delivered board',a='Stall/peak not verified',w='4 W average assumption, NOT rating',need='One kit first',note='Price from user Amazon screenshot incl. VAT. Complete acrylic kit, six AD002 servos and controller. Assembly required. Verify lifting capability with sample. Official controller docs say VIN6-24V; verify delivered revision and block USB VBUS backfeed before external power.',url='https://www.adeept.com/learn/detail-64.html')
setrow('Second identical',part='Second Adeept ADA031 kit — optional',price=69.99,v='TBD',a='TBD',w='TBD',note='Not funded initially. Can revisit after one-arm testing; do not buy Waveshare based on the historical list.',url='https://www.adeept.com/learn/detail-64.html')
setrow('Professionally',part='New 6S battery + BMS — removed from initial build',price=None,fund=0,v='Not used',a='—',w='—',need='No — use owned NOCO',note='User selected NOCO GB70 plus T12 original battery. No loose cells or BMS purchase required.',url='')
setrow('Pack-supplier',part='New 6S charger — removed',price=None,fund=0,v='Not used',a='—',w='—',need='No',note='Use NOCO specified charging equipment and OEM T12 dock, independently. Confirm existing accessories; any missing charger costs extra.')
setrow('Pololu D36V50F5',part='52Pi EP-0225 Pi 5 USB-C PD supply module',price=35,fund=35,v='9–24 V DC in; 5.15 V PD out',a='5 A PD output',w='25.75 W PD output capacity',need='Selected — harness check',note='EUR35 landed-cost allowance; vendor lists USD22.94 before destination charges. GB70 nominal12V feeds DC input; use included USB-C output cable. Vendor barrel dimensions conflict, verify physical connector. NO simultaneous alternative power input. No GPIO power injection required.',url='https://52pi.com/products/52pi-pd-power-extension-adapter-board-for-raspberry-pi-5')
setrow('Mean Well',part='Adeept VIN harness + USB VBUS-blocking interface',price=20,fund=20,v='VIN 6-24 V documented; internal 5 V rail',a='Peak and onboard converter limits to test',w='TBD',need='Essential — revision/backfeed check',note='EUR20 interface allowance, not another buck converter. Official archive documents VIN6-24V and internal5V regulator. Confirm delivered controller revision. USB VBUS is on5V rail: prevent backfeed and servo power through Pi USB with a qualified data-preserving VBUS-blocking interface. A charge-only cable is not suitable. Exact interface SKU pending.',url='https://www.adeept.com/learn/detail-64.html')
setrow('Separate 5 V',fund=15,need='Yes — selection HOLD')
setrow('Used Xbox',fund=10,need='Yes — used price target')
setrow('Kinect v2 PC',fund=40,need='Required — match exact v2 adapter')
setrow('Adafruit ICM',fund=29.8,need='Yes — stock/substitute check')
setrow('Pololu VL53',fund=80,need='Planned — four sensors')
setrow('USB two',fund=20,need='Planned — model selection')
setrow('TCA9548',fund=5,need='Conditional — ToF addressing',note='EUR5 allowance. Reserve for four identical ToF addresses; use short branch wiring. Exact carrier/pull-ups and XSHUT strategy still to select.')
setrow('Adafruit ICM',note='Two boards now funded at prior EUR14.90 listing each; that listing was unavailable, so price/stock needs reconfirmation or verified substitute. Addresses0x68/0x69. Use3.3V VIN with Pi. Camera IMU follows light Pi camera pan/tilt, not a presumed moving Kinect.')
setrow('Separate 5 V',note='EUR15 allowance for auxiliary converter; exact SKU and servo peak current pending. Powers audio and camera pan/tilt; motor branch must follow stop. No servo power from Pi3V3.')
setrow('Existing pan/tilt',need='Owned — interface validation',note='Only light Pi camera; NOT Kinect v2. Auxiliary power and PWM/stop wiring are design holds.')
setrow('2 MAX98357A',need='Owned — interface validation',note='Two3W speaker outputs are not DC input consumption. I2S pins and aux supply to be finalized. Bridged speaker outputs must not be grounded.')
setrow('USB two',note='EUR20 allowance, now funded; exact compatible microphone model still to select.')
setrow('DC-rated',price=60,fund=60,note='EUR60 engineering allowance, not a complete priced stop system. Includes fused distribution, disconnect and arm stop/reset hardware. Independent T12 drive stop and arm torque-loss behaviour unresolved; NO free-moving release until resolved.')
rs=[r for r in rs if not r['values'][1].startswith('Delivery /')]
def extra(part,price,fund,v,a,w,need,note,owned=False):
 rs.append({'values':['Power',part,1,price,price,'X' if owned else '',fund,v,a,w,need],'note':note,'url':''})
extra('NOCO GB70 — already owned',0,0,'12 V accessory output','15 A published output limit','56 Wh stored energy','Use existing','Only12V OUT and approved accessory cable. No jump clamps; no new battery purchase.',True)
extra('NOCO approved accessory cable + fused mating harness',15,15,'12 V nominal','Matched to fuse/wire rating','—','Verify owned accessories first','EUR15 allowance; remove if all required adapters already owned. Do not cut GB70 cables.')
extra('Kinect 12 V regulation / conditioning contingency',35,35,'12 V regulated target','Match adapter label + peaks','TBD','Conditional — output test','EUR35 allowance for dedicated buck-boost if GB70 output is not suitable directly. Exact model pending range/adapter qualification.')
extra('Distribution PCB prototype fabrication + terminals allowance',30,30,'12 V architecture','Copper/fuses TBD','—','Later fabrication — HOLD','Funding reserve only; do not order PCB before design review and connector/thermal/stop validation.')
hardware=round(sum(r['values'][6] for r in rs),2)
extra('Delivery and contingency reserve',round(600-hardware,2),round(600-hardware,2),'—','—','—','Reserve','Unspent allocation, not hardware. Prices except screenshot/previously checked items are allowances.')
assert hardware<600
for r in rs:
 v=r['values'];v[4]=None if v[3] is None else round(v[2]*v[3],2)
with (OUT/'parts.csv').open('w',newline='',encoding='utf-8-sig') as f:
 w=csv.writer(f);w.writerow(old['headers']);w.writerows(r['values'] for r in rs)
wb=xlsxwriter.Workbook(OUT/'parts.xlsx');ws=wb.add_worksheet('r07 parts');fmt=wb.add_format({'text_wrap':True,'valign':'top'});money=wb.add_format({'num_format':'€0.00'})
ws.add_table(0,0,len(rs),10,{'style':'Table Style Medium 2','columns':[{'header':h} for h in old['headers']],'data':[r['values'] for r in rs]})
ws.set_column(0,0,12,fmt);ws.set_column(1,1,58,fmt);ws.set_column(2,2,5);ws.set_column(3,4,12,money);ws.set_column(5,5,12);ws.set_column(6,6,15,money);ws.set_column(7,10,28,fmt)
for i,r in enumerate(rs,1):
 ws.set_row(i,64);ws.write_comment(i,1,r['note']+'\n'+r['url'],{'x_scale':2,'y_scale':2})
ws.write(len(rs)+2,5,'TOTAL');ws.write_formula(len(rs)+2,6,f'=SUM(G2:G{len(rs)+1})',money,600);ws.freeze_panes(1,2)
ns=wb.add_worksheet('Notes');ns.set_column(0,0,55,fmt);ns.set_column(1,1,120,fmt)
for i,r in enumerate(rs):ns.write_row(i,0,[r['values'][1],r['note']+' '+r['url']],fmt);ns.set_row(i,75)
wb.close()

# One-page vector presentation, with explicit PCB boundary and unresolved interfaces.
svg=['<svg xmlns="http://www.w3.org/2000/svg" width="1600" height="1260" viewBox="0 0 1600 1260"><defs><marker id="arr" markerWidth="8" markerHeight="8" refX="7" refY="3" orient="auto"><path d="M0,0 L0,6 L8,3 Z" fill="#176782"/></marker></defs><rect width="1600" height="1260" fill="#f4f8fb"/><style>text{font-family:Arial;fill:#173b4c}.box{fill:white;stroke:#176782;stroke-width:2}.hold{fill:#fff0cc;stroke:#b37b00;stroke-width:2}.wire{fill:none;stroke:#176782;stroke-width:3;marker-end:url(#arr)}</style>']
def txt(x,y,t,size=18):svg.append(f'<text x="{x}" y="{y}" font-size="{size}">{html.escape(t)}</text>')
def box(x,y,w,h,title,lines,hold=False):
 svg.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="10" class="{"hold" if hold else "box"}"/>');txt(x+15,y+28,title,21)
 for i,t in enumerate(lines):txt(x+15,y+55+23*i,t,16)
def wire(points):svg.append('<polyline class="wire" points="'+points+'"/>')
txt(35,40,'UNDERBOT • NOCO + T12 • SYSTEM CONNECTION MAP r07',29)
txt(35,72,'Review draft: power paths and data interfaces. Amber blocks need verification before wiring / fabrication.',18)
box(35,110,350,125,'NOCO GB70 — owned',['56 Wh • use 12V OUT accessory port','Approved accessory cable','No jump clamps; charge separately'])
box(440,110,700,125,'POWER-DISTRIBUTION PCB / HARNESS',['Main fuse + disconnect → separately fused branches','Pi / depth camera / actuator / auxiliary outputs + ground returns','Protection ratings, footprints and stop/reset circuit still on HOLD'],True)
wire('385,172 440,172')
for x,wid,title,lines,hold in [(35,350,'PI POWER MODULE',['52Pi EP-0225: DC input 9–24V','USB-C PD 5.15V / 5A','Physical input plug check pending'],False),(430,350,'KINECT POWER',['12V conditioning + v2 PC adapter','Check GB70 regulation and adapter','Buck-boost only if qualification requires'],True),(825,350,'ARM POWER',['Hardwired stop + manual reset','VIN6-24V board: internal 5V buck','Confirm revision + block USB backfeed'],True),(1220,345,'AUXILIARY POWER',['5V rail: audio + pan/tilt','Stop must also interrupt pan/tilt','Converter current rating HOLD'],True)]:
 box(x,300,wid,125,title,lines,hold)
 wire(f'790,235 790,265 {x+wid//2},265 {x+wid//2},300')
box(35,490,350,145,'RASPBERRY PI 5 — owned',['USB-C ← EP-0225 supplied cable','USB3 → Kinect + existing SSD','USB → arm + microphone','CSI → existing Pi Camera 3'])
wire('210,425 210,490')
box(430,490,350,145,'KINECT v2 — fixed mount',['Matching v2 PC adapter + USB3','Power adapter label/polarity check','Pi driver / USB bandwidth test','Not mounted on MG90S bracket'])
wire('605,425 605,490');wire('385,562 430,562')
box(825,490,350,145,'ADEEPT ADA031 — 1 kit',['6 servos + controller included','Assemble and calibrate kit','USB command interface to Pi','6-24V VIN revision / USB VBUS check'],True)
wire('1000,425 1000,490')
box(1220,490,345,145,'EXISTING AUDIO / PAN-TILT',['2 MAX98357A + 2 speakers','2 MG90S → light Pi camera only','I2S from Pi; PWM controller TBD','Do not power motors from Pi 3V3'])
wire('1392,425 1392,490')
box(35,710,745,150,'SENSORS / SMALL CONNECTIONS',['Pi I2C (GPIO2/3) → body IMU + camera IMU at different addresses','2 × ICM-20948 breakouts at 3.3V; exact carrier pin labels checked','4 × VL53L1X: mux or XSHUT address assignment required','Existing Uno available for pan/tilt; 5V/3.3V interface check','Pi fan header → active cooler; SSD and microphone share USB budget'])
wire('210,635 210,710')
box(825,710,740,150,'T12 — INDEPENDENT OEM POWER',['Original 14.8V battery: 3.2Ah nominal / 3.0Ah rated','OEM battery → original motor controller, wheels, LiDAR and sensors','Original dock → OEM charge electronics; NO NOCO connection','Pi control/LiDAR link and independent drive stop are unverified','Keep suction/brushes off for planned load estimate'],True)
txt(35,916,'DATA: Pi → arm over USB; Pi ↔ Kinect/SSD over USB3; Pi ↔ IMUs/ToF over I2C; Pi → camera over CSI.',18)
txt(35,950,'SEPARATE BATTERIES: do not join positive rails. Any signal-ground/interface connection must follow the final interface design.',18)
txt(35,1000,'WHAT IS FIXED',22)
txt(35,1030,'NOCO + T12 batteries • no new 6S pack/BMS/charger • Kinect v2 • Adeept kit • one arm initially',18)
txt(35,1080,'BEFORE PCB FABRICATION',22)
txt(35,1110,'Verify arm controller supply + peaks, Kinect adapter, NOCO output/shutdown, T12 control/stop, connector pinouts and protection.',18)
txt(35,1140,'This is a module-interconnection design. It does not authorize the amber circuits or specify finished PCB copper/footprints.',18)
txt(35,1200,f'Hardware allocations EUR {hardware:.2f} + reserve EUR {600-hardware:.2f} = EUR 600.00. Allowances are not supplier quotes.',18)
svg.append('</svg>');(OUT/'overall.svg').write_text(''.join(svg),encoding='utf-8')
notes=f'''# UnderBot r07 — NOCO + OEM T12

User-approved sources: existing NOCO GB70 accessory output for added robot systems; original T12 battery and dock for OEM base. New 6S pack/BMS/charger removed. One Adeept ADA031 kit is the current baseline; second optional after testing. Kinect v2 is retained. No purchases made.

## Deliverables
- overall.svg: one-page presentation drawing.
- UnderBot.kicad_pro / UnderBot.kicad_sch: fresh four-sheet integration draft plus index. Main/branch fuse topology, module port interfaces, Pi/sensor nets and independent OEM base documented.
- parts.xlsx / parts.csv: original 11 budget columns, current candidates, notes and purchase holds. Hardware funding {hardware:.2f} EUR; reserve {600-hardware:.2f} EUR; total 600 EUR. Not a complete quoted shopping basket.
- connector-schedule.csv: proposed harness pin assignments, NOT OEM connector numbering.

## Design holds
1. Adeept official V4 archive includes drive-board documentation specifying VIN6-24V and an arm-board schematic with a GS2678 onboard5V regulator. USB VBUS is shown on the same5V net. The archive filename says V3.0 but schematic title says V2.0: verify purchased board revision before feeding nominal12V to VIN. Prevent USB backfeeding with a qualified data-preserving VBUS-blocking interface; charge-only cables will not work. No separate arm buck is needed for the documented controller. Arm firmware, calibration, USB VBUS backfeed and torque-loss stop behaviour require tests.
2. NOCO output range/transient/low-load shutdown and usable energy. Approved accessory cable only. Charge separately; no charge connector on PCB.
3. Kinect v2 matching adapter voltage/current/polarity and Pi USB3 driver/bandwidth. Dedicated12V conditioning only after deciding whether direct supply is adequate; buck-only regulation cannot hold12V below its dropout input.
4. Pi EP-0225 accepts9–24V, supplies5.15V/5A PD. Use DC input and supplied USB-C output cable. Store and wiki give inconsistent barrel dimensions, so do not order an assumed mating plug.
5. T12 OEM drive/LiDAR access and independent hardwired stop. No guessed GPIO/UART wiring to OEM board. Electrical control interface, payload and stability must be qualified.
6. Auxiliary converter, sensor mux/address handling, I2S/PWM assignments and return paths. Current signal sheet is intentionally incomplete for these interfaces.
7. Fuse/relay/connector SKUs, anti-reversal/transient protection, PCB footprints, trace widths, fault/thermal review. No PCB layout or Gerbers released. E-stop interfaces are requirements blocks, not implemented safety circuits.

## Scope of validation
KiCad parsing/export checks verify file readability. Passive module port symbols do not validate converter pinouts, safety behaviour or hardware suitability. An ERC pass must not be called a fabrication release. Prior r05/r06 parts choices are historical and superseded.

## Sources
- Adeept official tutorial/revision archive: https://www.adeept.com/learn/detail-64.html
- Pi power module store: https://52pi.com/products/52pi-pd-power-extension-adapter-board-for-raspberry-pi-5
- Pi module wiki: https://wiki.52pi.com/index.php?title=EP-0225
- NOCO accessory output: https://no.co/gb70/specs
- T12 manual: https://user-guide2024.cnbj1.mi-fds.com/user-guide2024/Spain/Robot%20Vacuum/Xiaomi%20Robot%20Vacuum%20T12%20User%20Manual.pdf

The actual T12 purchase status has not been newly confirmed: original table had no X, so its EUR50 acquisition allowance remains. If already owned, that money returns to contingency. Existing NOCO charging/accessory equipment must be checked before removing related allowances.
'''
(OUT/'README.md').write_text(notes,encoding='utf-8')
table='<table><tr>'+''.join('<th>'+html.escape(h)+'</th>' for h in old['headers'])+'</tr>'
for r in rs:
 table+='<tr>'+''.join('<td>'+html.escape('TBD' if v is None else str(v))+'</td>' for v in r['values'])+'</tr>'
table+='</table>'
(OUT/'index.html').write_text('<!doctype html><meta charset="utf-8"><title>UnderBot r07 — NOCO + T12</title><style>body{font:16px system-ui;margin:25px;background:#f4f8fb;color:#173b4c}img{width:100%;max-width:1600px}table{border-collapse:collapse}td,th{padding:9px;border:1px solid #b9d6df}th{background:#185f7b;color:white}tr:nth-child(even){background:#d9edf5}.scroll{overflow:auto}a{color:#006e93}</style><h1>UnderBot r07 — NOCO + T12</h1><p>Approved battery architecture. Amber = engineering hold. One Adeept arm first; Kinect v2 retained. Not for PCB fabrication.</p><p><a href="parts.xlsx">Excel parts list</a> · <a href="UnderBot-schematic.pdf">KiCad schematic PDF</a> · <a href="README.md">Design notes / open checks</a></p><img src="overall.svg" alt="Whole robot connection map"><h2>Updated funding plan</h2><p>Prices include estimates. Open workbook cell comments for selection status and sources.</p><div class="scroll">'+table+'</div>',encoding='utf-8')
print(f'r07: {len(k.SHEETS)} sheets, hardware {hardware:.2f}, reserve {600-hardware:.2f}; created {OUT}')
