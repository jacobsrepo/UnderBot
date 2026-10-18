"""One-page, vector-first explanation of the proposed UnderBot architecture."""
from pathlib import Path
from html import escape
import textwrap

OUT = Path(__file__).resolve().parent
W, H = 2400, 3260
parts = [f'''<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">
<defs><marker id="arrow" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse"><path d="M0 0L10 5L0 10z" fill="context-stroke"/></marker></defs>
<style>text{{font-family:Arial,sans-serif;fill:#142b40}}.title{{font-size:58px;font-weight:700}}.section{{font-size:33px;font-weight:700}}.head{{font-size:26px;font-weight:700}}.body{{font-size:23px}}.small{{font-size:20px}}.tag{{font-size:21px;font-weight:700}}.muted{{fill:#4d6478}}</style>
<rect width="2400" height="3260" fill="#edf2f7"/>
''']
def text(x,y,s,cls='body',color=None):
    parts.append(f'<text x="{x}" y="{y}" class="{cls}"'+(f' style="fill:{color}"' if color else '')+f'>{escape(s)}</text>')
def rect(x,y,w,h,fill='#fff',stroke='none',r=16):
    parts.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{r}" fill="{fill}" stroke="{stroke}" stroke-width="2"/>')
def box(x,y,w,h,title,lines=(),color='#fff',stroke='#b9c9d8',size='body'):
    rect(x,y,w,h,color,stroke)
    text(x+20,y+35,title,'head')
    for i,line in enumerate(lines): text(x+20,y+68+29*i,line,size)
def line(points,color='#cb5d20',dash=False,arrow=True,both=False):
    coords=' '.join(f'{x},{y}' for x,y in points)
    parts.append(f'<polyline points="{coords}" fill="none" stroke="{color}" stroke-width="4" stroke-linejoin="round"'+(' stroke-dasharray="10 8"' if dash else '')+(' marker-end="url(#arrow)"' if arrow else '')+(' marker-start="url(#arrow)"' if both else '')+'/>')
def section(y,n,title,subtitle):
    rect(40,y,2320,76,'#132f46')
    text(63,y+34,f'{n}  {title}','section','#fff')
    text(63,y+61,subtitle,'small','#d8e6f2')
def dot(x,y,color='#cb5d20'):
    parts.append(f'<circle cx="{x}" cy="{y}" r="7" fill="{color}"/>')

text(55,82,'UNDERBOT  /  THE WHOLE CONNECTION MAP','title')
text(58,128,'Team presentation • Xiaomi T12 + Kinect v1 (assumed) + two IMUs + dual arms • Design proposal 0.2','body')
rect(55,153,2290,55,'#fff0d6')
text(72,188,'Read top to bottom. This explains the system; connector pin numbers and several hardware choices still need verification.','body')
line([(65,239),(135,239)]);text(150,247,'Orange = power (+ and return)','small')
line([(590,239),(660,239)],'#1375b1');text(675,247,'Blue = data / commands','small')
line([(1070,239),(1140,239)],'#b73550',True);text(1155,247,'Red = hardware stop','small')
line([(1540,239),(1610,239)],'#7b6d93',True);text(1625,247,'Dashed purple = unresolved / future','small')

section(280,'1','WHERE THE ENERGY COMES FROM','The robot battery and the charging-station battery are separate. Each has its own matching battery protection and charging settings.')
box(60,390,360,130,'Station solar panels',['2 × 100 W in series','Outdoor energy source'])
box(465,390,370,130,'Station solar controller',['Victron MPPT candidate','PV fuse / DC disconnect'])
box(880,390,430,130,'Station buffer battery',['8S LiFePO4 + BMS + fuse','25.6 V / 50 Ah nominal'])
box(1355,390,440,130,'Robot charging unit',['True buck-boost Li-ion charger','25.2 V / 4 A candidate'])
box(1840,390,500,130,'Protected docking contacts',['Fuse, current limit, polarity check','Dock detect → prevent motion'])
for a,b in [(420,465),(835,880),(1310,1355),(1795,1840)]: line([(a,453),(b,453)])
box(60,565,360,130,'Optional roof panel',['5–6 W peak','Supplemental energy only'])
box(465,565,370,130,'Robot solar charger',['Boost MPPT for 6S Li-ion','Not a direct panel-to-pack wire'])
line([(420,630),(465,630)])
box(880,565,430,130,'Mains fallback charger',['Dedicated 6S Li-ion charger','25.2 V / 4 A candidate'])
box(1355,565,440,130,'Charge-source manager',['Select / safely manage sources','No raw parallel charger outputs'])
line([(835,677),(855,677),(855,732),(1575,732),(1575,695)])
line([(1310,630),(1355,630)])
line([(2090,520),(2090,542),(1575,542),(1575,565)])
box(1840,565,500,165,'ROBOT PACK: 6S3P + BMS',['18 matched 21700 cells','25.2 V full; ~266 Wh plan','Cell sense wires + temperature probe'], '#e8f4e8')
line([(1795,630),(1840,630)])
text(1845,758,'P0 = protected battery output → section 2','tag')
text(62,774,'BMS = battery protection, not a charger. All charging returns must use the correct BMS port. T12 charging remains separate below.','small')

section(810,'2','HOW POWER REACHES EACH PART','A buck converter reduces voltage. One shared voltage supply can feed several compatible devices; every branch needs appropriate protection.')
box(60,930,490,112,'P0 → Main battery fuse',['Mounted close to the pack; rating TBD'])
box(60,1090,490,112,'Main isolator / keyed switch',['Manual service power disconnect'])
box(60,1250,490,145,'Current and voltage monitor',['Rated external shunt + INA228','Measures robot load → I2C to ESP32','Bus surge / reverse protection: TBD'],size='small')
line([(305,1042),(305,1090)]);line([(305,1202),(305,1250)])
line([(550,1320),(660,1320),(660,955)],arrow=False)
text(586,921,'BATTERY BUS','tag')
rows=[
 (930,'P1','Fuse → compute buck → USB-C source','5.1 V target; verify power at Pi under load','Raspberry Pi 5 + its peripherals','USB devices / SSD / fan included in budget'),
 (1080,'P2','Fuse → 12 V sensor buck','Confirm Kinect adapter voltage and polarity','Kinect v1 power / USB adapter','Adapter supplies power; USB carries data to Pi'),
 (1230,'P3','Fuse → 5 V auxiliary buck','Independent of Pi supply; common system return','Audio / status LEDs / accessories','Each module must accept this voltage'),
 (1380,'P4','P3 → 3.3 V logic regulator','Add module decoupling; verify breakout ratings','Body IMU + head IMU + sensor logic','I2C mux / ToF / INA228 logic as selected'),
]
for y,tag,title,desc,dest,detail in rows:
    box(780,y,735,110,f'{tag}  {title}',[desc])
    box(1600,y,740,110,dest,[detail])
    line([(1515,y+55),(1600,y+55)])
    if tag!='P4':
        line([(660,y+55),(780,y+55)]);dot(660,y+55)
line([(1140,1340),(1140,1380)])
box(60,1440,490,140,'Every power cable needs a return',['GND = protected electrical return.','Motor current must not flow through','the Pi or sensor ground wires.'], '#e7eef7',size='small')
box(780,1540,735,110,'P5  Fuse → actuator buck → power bus',['Voltage and current depend on selected servos'])
box(1600,1540,740,110,'Arms + grippers + camera pan/tilt',['Separate power wires; signals come from section 3'])
line([(1515,1595),(1600,1595)])
box(60,1620,490,115,'E-stop → reset / watchdog circuit',['Removes the hardware motion permit'], '#fde8ec')
box(780,1690,735,115,'Normally-open actuator contactor',['Heavy power switch; opens when permit is lost','Coil driver + suppression + precharge interlock: design TBD'], '#fde8ec',size='small')
line([(660,1320),(660,1750),(780,1750)])
line([(1140,1690),(1140,1650)])
line([(550,1677),(705,1677),(705,1780),(780,1780)],'#b73550',True)
text(1610,1732,'E-stop target: stop motion; keep Pi / Kinect alive.','tag')
text(1610,1767,'Arm brakes / gravity behavior must be designed too.','small')
text(62,1838,'Not shown as ready-to-fit parts: transient protection, precharge/inrush limit, coil suppression, fuse values, cable gauges and connectors.','small')

section(1870,'3','HOW THE ROBOT TALKS AND SENSES','Power labels P1–P5 refer to section 2. Data connections do not replace a device’s power supply. The ESP32 handles low-level control.')
box(60,1980,410,145,'Raspberry Pi 5  [P1]',['ROS / perception / navigation','Network ↔ team computer','USB ↔ Kinect v1 [P2]'])
box(565,1980,505,145,'ESP32 controller  [Pi USB power]',['Commands + feedback over USB','No simultaneous external 5 V feed','Heartbeat → hardware watchdog'])
line([(470,2045),(565,2045)],'#1375b1',both=True)
box(1170,1980,405,145,'I2C sensor bus / mux [P4]',['Routes one short bus into','separate sensor channels','Avoids duplicate addresses'])
line([(1070,2045),(1170,2045)],'#1375b1',both=True)
box(1680,1980,660,145,'Two separate IMUs + optional ToF x4 [P4]',['Channel 0: body IMU fixed to chassis','Channel 1: head IMU moves with camera','Other channels: front / rear / left / right ToF'])
line([(1575,2045),(1680,2045)],'#1375b1',both=True)
box(60,2170,410,185,'Pi accessory connections',['SSD → USB or chosen PCIe HAT','Mic / audio interface → Pi','Pi audio → amplifier → speaker','Fan → correct fan connection','Optional AI board: verify Pi interface'],size='small')
line([(265,2125),(265,2170)],'#1375b1')
box(565,2170,505,160,'Power / temperature feedback',['INA228 → ESP32 I2C bus','BMS serial → voltage-safe adapter','Second NTC → divider / ADC','Pi has no general analog input'],size='small')
line([(810,2170),(810,2125)],'#1375b1')
box(1170,2170,405,160,'Actuator signal interface',['PWM servos: PCA9685 [P4]','Smart servos: matching bus','Select one suitable approach','Output defaults disabled'],size='small')
line([(1070,2090),(1110,2090),(1110,2245),(1170,2245)],'#1375b1')
box(1680,2170,660,160,'Left arm / right arm / grippers / pan-tilt',['Signal wires from the selected driver → actuators','Motor power from P5 → separate distribution','Servo voltage, stall current and pinouts still TBD','Camera IMU is a sensor, not a pan/tilt controller'],size='small')
line([(1575,2245),(1680,2245)],'#1375b1')
text(63,2371,'I2C = short sensor-data bus. Use correct pull-ups and local capacitors; confirm interrupt/reset wires and cable lengths after module selection.','small')

section(2400,'4','THE XIAOMI BASE: KEEP ITS POWER SEPARATE FOR THE FIRST PROTOTYPE','This is a differential-drive vacuum base, not mecanum. Do not assume the existing controller exposes an open motor or LiDAR interface.')
box(60,2510,440,145,'Original T12 battery / dock',['14.8 V-rated base system','20 V-rated charging input','Never parallel with the new 6S pack'], '#fff0d6')
box(595,2510,505,145,'T12 original controller',['Own verified hardware stop required','Power / commands → wheel motors','Wheel encoders → feedback'])
line([(500,2575),(595,2575)])
box(1195,2510,520,145,'Existing base sensors',['LiDAR + bump + cliff sensors','OEM gyro is an additional sensor','Their internal pinouts are unverified'])
line([(1100,2575),(1195,2575)],'#1375b1',both=True)
box(1810,2510,530,145,'Pi / ESP32 integration — TBD',['Model-specific data / control adapter','Motor commands + odometry + LiDAR','Discover protocol before wiring'], '#f1eafa')
line([(1715,2575),(1810,2575)],'#7b6d93',True,both=True)
text(65,2700,'Future single-pack option: 6S → separately fused, validated base supply + motion disconnect → T12. Do not build from voltage alone.','body')
text(65,2735,'Check battery-sense pins, peak motor current and braking energy first. Opening the new pack contactor does NOT stop an OEM-battery-powered base.','small')

section(2770,'5','WHAT THE TEAM SHOULD UNDERSTAND BEFORE BUILDING','A custom PCB is optional for the prototype. Start with protected modules and a labelled wiring harness; consolidate after interfaces are proven.')
box(60,2880,720,220,'The small parts do important jobs',['Fuse: protects a wire branch against excess current.','Buck: reduces voltage; it does not create extra energy.','Contactor: electrically operated high-current switch.','Shunt: small resistor used to measure current.','BMS: monitors/protects cells and pack temperature.'],size='small')
box(840,2880,720,220,'Important design boundaries',['USB-C source must support the Pi’s power needs.','Do not power actuators through a sensor board.','No raw 6S into T12, Pi, ESP32 or ordinary servos.','Six 2.7 V supercaps are NOT suitable across 6S.','Standalone emergency beacon needs its own protected','battery/charger; it is optional, not a shared power rail.'], '#fff0d6',size='small')
box(1620,2880,720,220,'Still needed to finish the wiring',['Exact Kinect / adapter and T12 model labels.','Arm / gripper / pan-tilt actuator models and counts.','IMU / ToF boards, audio, storage and cooling choices.','Peak-current measurements and base API discovery.','Then: actual pin numbers, fuses, wires and PCB layout.'],size='small')
text(62,3146,'Runtime is a target, not a measurement: 266 Wh × 80% usable × 87% efficiency gives ~6.6 h at 28 W, or ~3.1 h at 60 W.','body')
text(62,3190,'Based on the user’s corrected component list and manufacturer references in README.md. Solid lines describe proposed routes, not bench-tested wiring.','small')
text(62,3230,'UnderBot • 29 September 2026 • Concept / integration review • No PCB fabrication or pin-level wiring approval implied','small')
parts.append('</svg>')
(OUT/'UnderBot-team-connection-map.svg').write_text('\n'.join(parts),encoding='utf-8')

html='''<!doctype html><html lang="en"><meta charset="utf-8"><title>UnderBot — team connection map</title>
<style>body{margin:0;background:#132f46;font:16px Arial;color:white}nav{position:sticky;top:0;padding:12px 20px;background:#132f46;display:flex;gap:12px;align-items:center;z-index:2}button,a{font:inherit;padding:9px 13px;border:0;border-radius:6px;background:#fff;color:#132f46;text-decoration:none;cursor:pointer}span{margin-right:auto}main{overflow:auto;height:calc(100vh - 67px)}img{display:block;width:100%;max-width:none} @page{size:594mm 841mm;margin:10mm} @media print{nav{display:none}body{background:white}main{height:auto;overflow:visible}img{width:574mm!important;height:auto;max-height:821mm;object-fit:contain}}
</style><nav><span><b>UnderBot</b> · One-page team map · Zoom in to follow each connection</span><button onclick="zoom(1.25)">Zoom +</button><button onclick="zoom(.8)">Zoom −</button><button onclick="fit()">Fit width</button><button onclick="print()">Print / PDF</button><a href="UnderBot-team-connection-map.svg" download>SVG</a><a href="README.md">Technical notes</a></nav><main><img id="poster" src="UnderBot-team-connection-map.svg" alt="UnderBot full connection map: charging, protected power branches, compute and sensors, separate Xiaomi base, and plain-language glossary"></main><script>let scale=1;function zoom(f){scale=Math.min(4,Math.max(.4,scale*f));document.getElementById('poster').style.width=(scale*100)+'%'}function fit(){scale=1;document.getElementById('poster').style.width='100%'}</script></html>'''
(OUT/'UnderBot-team-connection-map.html').write_text(html,encoding='utf-8')
print('Created team SVG poster and offline zoomable viewer.')
