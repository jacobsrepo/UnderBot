"""Generate the linked UnderBot wiring schematic; libraries are embedded for portability."""
from pathlib import Path
import csv, json, math, re, uuid

BASE = Path(__file__).resolve().parent
OUT = BASE / 'UnderBot-Schematic-r04'
OUT.mkdir(exist_ok=True)
LIB = Path(r'C:\Users\samja\AppData\Local\Programs\KiCad\10.0\share\kicad\symbols')
PROJECT = 'UnderBot'
ROOT = str(uuid.uuid5(uuid.NAMESPACE_URL, 'underbot/schematic/0.3'))
def ident(s): return str(uuid.uuid5(uuid.NAMESPACE_URL, 'underbot/schematic/0.3/'+s))
def q(s): return json.dumps(str(s))
def parse(s):
    tokens = re.findall(r'"(?:\\.|[^"\\])*"|[()]|[^\s()]+', s)
    stack=[]; result=None
    for t in tokens:
        if t=='(':
            a=[]
            if stack: stack[-1].append(a)
            stack.append(a)
        elif t==')': result=stack.pop()
        else: stack[-1].append(json.loads(t) if t.startswith('"') else t)
    return result
def child(a,key): return next((v for v in a if isinstance(v,list) and v and v[0]==key),None)
def children(a,key): return [v for v in a if isinstance(v,list) and v and v[0]==key]
def extract(s,name,kind='symbol'):
    m=re.search(r'\('+kind+r'\s+"'+re.escape(name)+r'"',s)
    if not m: raise ValueError(name)
    start=m.start(); depth=0; quoted=False; escaped=False
    for i in range(start,len(s)):
        c=s[i]
        if quoted:
            if escaped: escaped=False
            elif c=='\\': escaped=True
            elif c=='"': quoted=False
        elif c=='"': quoted=True
        elif c=='(': depth+=1
        elif c==')':
            depth-=1
            if depth==0: return s[start:i+1]
    raise ValueError('Unbalanced symbol')
CACHE={}
def library(libid):
    if libid not in CACHE:
        lib,name=libid.split(':')
        raw=extract((LIB/(lib+'.kicad_sym')).read_text(encoding='utf-8'),name)
        tree=parse(raw)
        if child(tree,'extends'):
            parent=child(tree,'extends')[1]
            derived=raw
            raw=extract((LIB/(lib+'.kicad_sym')).read_text(encoding='utf-8'),parent).replace(parent,name)
            for prop in children(tree,'property'):
                replacement=extract(derived,prop[1],'property')
                try: previous=extract(raw,prop[1],'property');raw=raw.replace(previous,replacement,1)
                except ValueError: raw=raw[:-1]+replacement+')'
            tree=parse(raw)
        pins={}
        for unit in children(tree,'symbol'):
            for pin in children(unit,'pin'):
                at=child(pin,'at'); number=child(pin,'number')[1]
                pins[number]=(float(at[1]),float(at[2]),float(at[3]),child(pin,'name')[1])
        CACHE[libid]=(raw.replace('(symbol "'+name+'"','(symbol "'+libid+'"',1),pins)
    return CACHE[libid]

CONNECTORS=[]; BOM=[]; SHEETS=[]
CROSS={'GND_SYS','VBAT_FUSED','VBAT_SW','SHUNT_HI','SHUNT_LO','LOGIC_3V3','AUX_5V','I2C_SDA','I2C_SCL','PWM_OE','HEARTBEAT','STOP_STATUS','INA_ALERT'}
CROSS.update({'BODY_SDA','BODY_SCL','HEAD_SDA','HEAD_SCL','PWM_SDA','PWM_SCL','TEMP_ADC','SERVO_POWER_TBD'})

def module_library(name,left,right):
    """Off-board interface symbols: pin identifiers are board labels, not IC pad numbers."""
    lid='UnderBot_Modules:'+name
    height=(max(len(left),len(right))+1)*2.54
    pins={}; fragments=[]
    for side,entries in [('left',left),('right',right)]:
        for i,label in enumerate(entries):
            x=-30.48 if side=='left' else 30.48
            y=height-5.08-i*5.08; angle=0 if side=='left' else 180
            pins[label]=(x,y,angle,label)
            fragments.append(f'(pin passive line (at {x} {y} {angle}) (length 5.08) (name {q(label)} (effects (font (size 1 1)))) (number {q(label)} (effects (font (size 1 1)))))')
    raw=f'''(symbol {q(lid)} (pin_numbers hide) (pin_names (offset 1.016)) (in_bom yes) (on_board yes)
      (property "Reference" "A" (at 0 {height+5.08} 0) (effects (font (size 1.27 1.27))))
      (property "Value" {q(name)} (at 0 {height+2.54} 0) (effects (font (size 1 1))))
      (symbol "{name}_0_1" (rectangle (start -25.4 {height}) (end 25.4 {-height}) (stroke (width 0.254) (type default)) (fill (type background))))
      (symbol "{name}_1_1" {''.join(fragments)}))'''
    CACHE[lid]=(raw,pins)
    return lid
class Sheet:
    def __init__(self,name,title):
        self.name=name;self.title=title;self.uid=ident(name);self.sheetid=ident('sheet/'+name)
        self.items=[];self.libs={};self.parts={};self.counter=0;SHEETS.append(self)
    def u(self):
        self.counter+=1;return ident(self.name+'/'+str(self.counter))
    def note(self,x,y,text,size=1.5):
        self.items.append(f'(text {q(text)} (at {x} {y} 0) (effects (font (size {size} {size})) (justify left top)) (uuid {self.u()}))')
    def add(self,libid,ref,value,x,y,angle=0,dnp=False,onboard=True,offset=0):
        raw,pins=library(libid);self.libs[libid]=raw
        a=math.radians(angle)
        coords={n:(round(x+px*math.cos(a)-py*math.sin(a),4),round(y-px*math.sin(a)-py*math.cos(a),4)) for n,(px,py,_,_) in pins.items()}
        self.parts[ref]=coords
        ymax=max((v[1] for v in pins.values()),default=5)
        ty=min(p[1] for p in coords.values())-7.62-offset
        if libid.startswith('UnderBot_Modules:'):ty-=3.81
        fx=x;justify=''
        if libid in ('Device:R','Device:C') and angle==0:
            fx=x+5.08;ty=y-1.27;justify='(justify left)'
        fieldangle=90 if angle in (90,270) else 0
        props=f'(property "Reference" {q(ref)} (at {fx} {ty} {fieldangle}) (effects (font (size 1.27 1.27)) {justify})) (property "Value" {q(value)} (at {fx} {ty+2.54} {fieldangle}) (effects (font (size 1.0 1.0)) {justify})) (property "Footprint" "" (at {x} {y} 0) (effects (font (size 1.27 1.27)) hide))'
        props+=f'(property "Assembly" {q("PCB/harness TBD" if onboard else "OFF-BOARD") } (at {x} {y} 0) (effects (font (size 1 1)) hide))'
        self.items.append(f'(symbol (lib_id {q(libid)}) (at {x} {y} {angle}) (unit 1) (in_bom yes) (on_board yes) (dnp {"yes" if dnp else "no"}) (uuid {ident(self.name+ref)}) {props} (instances (project "UnderBot" (path "/{ROOT}/{self.sheetid}" (reference {q(ref)}) (unit 1)))))')
        BOM.append([self.name,ref,value,libid,'DNP' if dnp else 'PROVISIONAL','PCB / harness TBD' if onboard else 'OFF-BOARD',''])
        return coords
    def wire(self,*pts):
        for a,b in zip(pts,pts[1:]):
            if a==b: continue
            self.items.append(f'(wire (pts (xy {a[0]} {a[1]}) (xy {b[0]} {b[1]})) (stroke (width 0) (type default)) (uuid {self.u()}))')
    def junction(self,p): self.items.append(f'(junction (at {p[0]} {p[1]}) (diameter 0) (color 0 0 0 0) (uuid {self.u()}))')
    def label(self,p,name,glob=True,angle=0):
        glob=glob and name in CROSS
        typ='global_label' if glob else 'label';shape='(shape bidirectional)' if glob else ''
        self.items.append(f'({typ} {q(name)} {shape} (at {p[0]} {p[1]} {angle}) (effects (font (size 1 1)) (justify {"left" if angle==0 else "right"})) (uuid {self.u()}))')
    def net(self,ref,pin,name,dx=-10.16,dy=0,glob=True):
        p=self.parts[ref][str(pin)];end=(round(p[0]+dx,4),round(p[1]+dy,4))
        if dx and dy:self.wire(p,(p[0],end[1]),end)
        else:self.wire(p,end)
        self.label(end,name,glob,0 if dx<=0 else 180)
    def nc(self,ref,pin):
        p=self.parts[ref][str(pin)];self.items.append(f'(no_connect (at {p[0]} {p[1]}) (uuid {self.u()}))')
    def conn(self,ref,value,x,y,nets,descs=None):
        self.add(f'Connector_Generic:Conn_01x{len(nets):02}',ref,value,x,y)
        for i,net in enumerate(nets,1):
            if net: self.net(ref,i,net)
            else: self.nc(ref,i)
            CONNECTORS.append([self.name,ref,i,net or 'NC',descs[i-1] if descs else value,'Proposed carrier/harness pin; NOT OEM pin numbering'])
    def resistor(self,ref,value,x,y,top,bottom,dnp=False):
        self.add('Device:R',ref,value,x,y,dnp=dnp)
        self.net(ref,1,top,0,-5.08);self.net(ref,2,bottom,0,5.08)
    def cap(self,ref,value,x,y,top,bottom):
        self.add('Device:C',ref,value,x,y)
        self.net(ref,1,top,0,-5.08);self.net(ref,2,bottom,0,5.08)
    def save(self):
        doc=f'''(kicad_sch (version 20250114) (generator "eeschema") (uuid {self.uid}) (paper "A3")
        (title_block (title {q(self.title)}) (date "2026-10-02") (rev "0.4 REVIEW") (company "UnderBot")
        (comment 1 "PROVISIONAL CIRCUIT / HARNESS DESIGN - NOT FOR FABRICATION")
        (comment 2 "J pin numbers are proposed harness assignments, not OEM connector pinouts"))
        (lib_symbols {''.join(self.libs.values())}) {''.join(self.items)} (embedded_fonts no))'''
        (OUT/(self.name+'.kicad_sch')).write_text(doc,encoding='utf-8')

if __name__=='__main__':
    s=Sheet('01_Battery','01 - Battery input, isolation and Kelvin shunt')
    s.note(20,15,'BATTERY -> MAIN FUSE -> SERVICE SWITCH -> SHUNT -> LOAD BUS',2)
    s.note(20,23,'Protected 6S pack only. Charge connection branches BEFORE service switch; see sheet 06.')
    s.add('Connector_Generic:Conn_01x02','J101','BMS protected output',45.72,60.96,180)
    s.add('Device:Fuse','F101','25A candidate - verify',91.44,60.96,90,onboard=False)
    s.add('Switch:SW_SPST','SW101','DC-rated isolator',147.32,60.96,onboard=False)
    s.add('Device:R_Shunt','R101','1mR Kelvin - rating TBD',213.36,60.96,90,onboard=False)
    s.wire(s.parts['J101']['1'],s.parts['F101']['1'])
    s.wire(s.parts['F101']['2'],(119.38,60.96),s.parts['SW101']['1'])
    s.label((119.38,60.96),'VBAT_FUSED');s.junction((119.38,60.96))
    s.wire(s.parts['SW101']['2'],s.parts['R101']['1'])
    s.net('R101',4,'VBAT_SW',35.56)
    s.net('R101',2,'SHUNT_HI',0,20.32)
    s.net('R101',3,'SHUNT_LO',15.24,25.4)
    s.net('J101',2,'GND_SYS',20.32,0)
    CONNECTORS.extend([['01_Battery','J101',1,'PACK_POS','BMS-protected positive','Confirm actual battery connector'],['01_Battery','J101',2,'GND_SYS','BMS-protected return P-','Never raw cell B-']])
    s.conn('J102','Switched bus service output',340.36,63.5,['VBAT_SW','GND_SYS'])
    s.note(20,124,'R101 is a FOUR-terminal shunt: pins 1/4 carry current; pins 2/3 are Kelvin sense connections to U101 (sheet 02).')
    s.note(20,132,'1 milliohm: 25A -> 25mV and 0.625W; 40A -> 1.6W. Select pulse rating, thermal margin and terminal geometry.')
    s.note(20,148,'OFF-BOARD / NOT RELEASED: cell pack, BMS, pack fuse, isolator and high-current shunt. No DIY cell assembly drawing.')
    s.note(20,156,'GND_SYS is the BMS protected return. Do not bypass the BMS with USB grounds, charger returns or chassis bonds.')
    s.note(20,172,'F101 protects the battery lead. Branch fuses are on sheets 03/05/06. No fuse, cable or contactor rating is final.')
    s.note(20,188,'UNRESOLVED: whole-system reverse-polarity / surge protection and converter inrush. No placeholder is claimed as protection.')
    s.note(20,204,'SW101 OFF isolates loads, not the charging connector. Disconnect the pack and charger before service.')
    s.note(20,220,'This shunt measures load discharge only. Charging bypasses it; BMS must supply total pack charge accounting.')

    s=Sheet('02_Monitor','02 - INA228 current / voltage monitor circuit')
    s.note(20,15,'REAL IC PIN CONNECTIONS: INA228 / DGS 10-PIN PACKAGE',2)
    s.note(20,23,'Prototype may use an equivalent breakout, but check onboard shunt and pin labels before connecting it.')
    s.add('Sensor_Energy:INA228','U101','INA228',162.56,91.44)
    for pin,net,dx,dy in [(1,'GND_SYS',20.32,0),(2,'GND_SYS',15.24,0),(3,'INA_ALERT',20.32,0),(4,'I2C_SDA',35.56,0),(5,'I2C_SCL',30.48,0),(6,'LOGIC_3V3',0,-12.7),(7,'GND_SYS',0,12.7),(8,'VBAT_SW',-30.48,0),(9,'SHUNT_LO',-30.48,0),(10,'SHUNT_HI',-35.56,0)]:
        s.net('U101',pin,net,dx,dy)
    s.cap('C101','100nF / 10V',63.5,91.44,'LOGIC_3V3','GND_SYS')
    s.resistor('R102','10k',259.08,91.44,'LOGIC_3V3','INA_ALERT')
    s.note(20,144,'C101 goes directly beside U101 VS/GND. A0=A1=GND selects 0x40; do not put another 0x40 device on the same bus segment.')
    s.note(20,156,'INA228 VS is 3.3V, NEVER battery voltage. Only VBUS and IN+/IN- connect to the high-voltage measurement path.')
    s.note(20,168,'Run SHUNT_HI / SHUNT_LO as a matched Kelvin pair from R101 sense terminals. Do not carry load current in those wires.')
    s.note(20,180,'I2C pull-ups are on sheet 04, subject to existing module pull-ups. ALERT is open-drain and pulled up by R102.')
    s.note(20,192,'Candidate shunt needs firmware calibration. Verify measurement range, reset behavior and power sequencing before use.')
    s.note(20,204,'No input filter values are assumed. Evaluate TI input-filter guidance against actual converter / motor noise.')
    s.note(20,220,'Reference: TI INA228 datasheet, pin-function table and application circuit. Footprint intentionally awaits package verification.')

    s=Sheet('03_Rails','03 - Fused converter harnesses and power outputs')
    s.note(20,15,'COMMERCIAL DC/DC MODULES: INPUT AND OUTPUT HARNESS CONNECTIONS',2)
    s.note(20,23,'Pairs TO_x and FROM_x go to an off-board converter. They are NOT shorted together on the PCB.')
    for idx,y,name,output,detail in [(1,60.96,'PI','PI_5V1','Pi-compatible 5.1V source + USB-C interface; module TBD'),(2,121.92,'KINECT','KINECT_12V','D36V50F12 candidate; verify adapter and thermal/current margin'),(3,182.88,'AUX','AUX_5V','5V auxiliary converter; model and current TBD')]:
        f=f'F20{idx}'; s.add('Device:Fuse',f,'Rating TBD',63.5,y,90)
        s.net(f,1,'VBAT_SW',-17.78)
        jin=f'J2{idx}1';s.conn(jin,'TO '+name+' converter VIN/GND',139.7,y,[name+'_VIN','GND_SYS'])
        s.wire(s.parts[f]['2'],(93.98,y));s.label((93.98,y),name+'_VIN',False)
        s.conn(f'J2{idx}2','FROM '+name+' VOUT/GND',264.16,y,[output,'GND_SYS'])
        s.conn(f'J2{idx}3',name+' load output',365.76,y,[output,'GND_SYS'])
        s.note(35,y+20.32,detail,1.27)
    s.conn('J241','TO 3.3V regulator VIN/GND',139.7,236.22,['AUX_5V','GND_SYS'])
    s.conn('J242','FROM 3.3V regulator VOUT/GND',264.16,236.22,['LOGIC_3V3','GND_SYS'])
    s.note(20,257,'All J numbers define OUR harness ends. Verify converter terminal labels, polarity and connector current limits.',1.27)
    s.note(20,264,'J213 goes to an approved USB-C SOURCE interface, not bare USB-C pins. No USB PD circuitry is implied here.',1.27)
    s.add('power:PWR_FLAG','#FLG01','PWR_FLAG',320.04,231.14)
    s.net('#FLG01',1,'LOGIC_3V3',0,5.08)
    s.add('power:PWR_FLAG','#FLG02','PWR_FLAG',350.52,231.14)
    s.net('#FLG02',1,'GND_SYS',0,5.08)

    s=Sheet('04_Control','04 - Controller and sensor harness / temperature circuit')
    s.note(20,15,'ESP32 IS USB-POWERED FROM THE PI. ALL SIGNAL LEVELS HERE ARE 3.3V.',2)
    s.conn('J301','ESP32 signal harness - see sheet 07',86.36,66.04,['GND_SYS','I2C_SDA','I2C_SCL','PWM_OE','HEARTBEAT','STOP_STATUS','INA_ALERT','TEMP_ADC'])
    s.conn('J302','Adafruit 2717 mux - 0x77',213.36,53.34,['LOGIC_3V3','GND_SYS','I2C_SDA','I2C_SCL'])
    s.conn('J303','Body: Adafruit 4554 / channel 0',358.14,53.34,['LOGIC_3V3','GND_SYS','BODY_SDA','BODY_SCL'])
    s.conn('J304','Head: Adafruit 4554 / channel 1',358.14,106.68,['LOGIC_3V3','GND_SYS','HEAD_SDA','HEAD_SCL'])
    s.conn('J305','Mux channels 0 / 1 outputs',213.36,106.68,['BODY_SDA','BODY_SCL','HEAD_SDA','HEAD_SCL'])
    s.resistor('R301','4k7 - DNP if already fitted',43.18,137.16,'LOGIC_3V3','I2C_SDA',True)
    s.resistor('R302','4k7 - DNP if already fitted',111.76,137.16,'LOGIC_3V3','I2C_SCL',True)
    s.resistor('R303','10k / 1% candidate',187.96,172.72,'LOGIC_3V3','TEMP_ADC')
    s.conn('J306','External 10k NTC',269.24,180.34,['TEMP_ADC','GND_SYS'])
    s.cap('C301','100nF',337.82,172.72,'TEMP_ADC','GND_SYS')
    s.note(20,211,'J306 NTC + R303 form an ADC divider; C301 filters noise. Confirm thermistor curve and ESP32 ADC range/calibration.',1.27)
    s.note(20,220,'IMUs: ICM-20948 breakouts, polled I2C. J303/J304 pins 1/2/3/4 -> VIN/GND/SDA/SCL. Software fusion required.',1.27)
    s.note(20,229,'The mux is OFF-BOARD. Its channel ports are J305; it is not replaced by shorting the SDA/SCL lines together.',1.27)
    s.note(20,238,'Mux A0/A1/A2 -> 3.3V: 0x77 avoids PCA9685 ALLCALL 0x70. Select ONE channel at a time. Not Qwiic pin numbering.',1.27)
    s.note(20,247,'Set PCA9685 A0 jumper CLOSED: 0x41. A mux channel alone does NOT avoid upstream INA228 address 0x40.',1.27)

    s=Sheet('05_Actuators','05 - Actuator power and external safety interfaces - HOLD')
    s.note(20,15,'ACTUATOR / SAFETY INTERFACES ONLY: HARDWARE STILL TO BE SELECTED',2)
    s.add('Device:Fuse','F401','Actuator branch - TBD',68.58,60.96,90)
    s.net('F401',1,'VBAT_SW',-20.32);s.net('F401',2,'ACTUATOR_FEED',15.24)
    s.conn('J401','TO external NO contactor LINE',152.4,60.96,['ACTUATOR_FEED','GND_SYS'])
    s.conn('J402','FROM contactor LOAD',281.94,60.96,['ACTUATOR_SWITCHED','GND_SYS'])
    s.conn('J403','TO actuator converter VIN/GND',378.46,60.96,['ACTUATOR_SWITCHED','GND_SYS'])
    s.conn('J404','FROM actuator converter',152.4,121.92,['SERVO_POWER_TBD','GND_SYS'])
    s.conn('J405','TO fused servo distribution',281.94,121.92,['SERVO_POWER_TBD','GND_SYS'])
    s.conn('J406','Safety-controller logic interface',91.44,185.42,['GND_SYS','HEARTBEAT','STOP_STATUS'])
    s.conn('J407','PCA9685 logic - A0 closed / 0x41',223.52,185.42,['LOGIC_3V3','GND_SYS','PWM_SDA','PWM_SCL','PWM_OE'])
    s.conn('J408','FROM dedicated mux channel 2',365.76,175.26,['PWM_SDA','PWM_SCL'])
    s.resistor('R401','10k candidate / DNP pending breakout',335.28,223.52,'LOGIC_3V3','PWM_OE',True)
    s.note(20,243,'Safety controller, two NC E-stop channels, reset, watchdog hardware, coil driver and suppression are NOT DESIGNED here.',1.27)
    s.note(20,251,'J401/J402 are external contactor power terminals, not a PCB jumper. Do not bypass the missing contactor or safety circuit.',1.27)
    s.note(20,259,'PWM_OE HIGH should disable output; resolve breakout pull-downs before fitting R401. Signal disable is not an E-stop.',1.27)
    s.note(20,267,'T12 battery/control wiring remains completely separate. Smart servos may replace J407/PCA9685; voltage and stall currents TBD.',1.27)

    s=Sheet('06_Charge','06 - Single-source external charger input - prototype')
    s.note(20,15,'FIRST REVISION: ONE APPROPRIATE 6S CHARGER CONNECTED AT A TIME',2)
    s.add('Connector_Generic:Conn_01x02','J601','25.2V CC/CV charger input',50.8,71.12,180)
    s.add('Device:Fuse','F601','Charge cable fuse - TBD',124.46,71.12,90)
    s.wire(s.parts['J601']['1'],s.parts['F601']['1'])
    s.net('F601',2,'VBAT_FUSED',30.48)
    s.net('J601',2,'GND_SYS',20.32,0)
    CONNECTORS.extend([['06_Charge','J601',1,'CHARGER_POS','Selected charger positive','Proposed connector; verify polarity'],['06_Charge','J601',2,'GND_SYS','Charger return to BMS P-','Common-port BMS assumed']])
    s.note(20,124,'Uses the common-port BMS topology: charge positive -> F601 -> F101 -> pack positive; return -> protected BMS return.')
    s.note(20,136,'If the selected BMS has a separate C- port, this sheet MUST change. Never wire charger return directly to raw cell negative.')
    s.note(20,148,'Use a finished 6S Li-ion charger with termination, temperature policy and reverse-current protection; 4A is a candidate limit.')
    s.note(20,160,'Prototype charging procedure: service switch OFF; appropriate pack/BMS fitted; one source; no energized motion.')
    s.note(20,180,'NOT IN THIS REVISION: unattended dock contacts/interlock, parallel solar + mains sources, charge-source OR-ing or supercapacitors.')
    s.note(20,192,'Station PV / LiFePO4 / buck-boost charger remains an EXTERNAL subsystem in the architecture drawing. No station PCB is implied.')
    s.note(20,204,'The original T12 dock/battery is independent. Neither T12 battery terminals nor its 20V charging input accepts 25.2V directly.')
    s.note(20,224,'Mechanical connector selection, touch protection and fuse coordination are still required before connecting real batteries.')

    s=Sheet('07_Modules','07 - Off-board modules and ESP32 GPIO wiring')
    s.note(20,14,'MODULE INTERFACES: CONNECT BY BOARD LABEL, NOT BARE-IC PIN NUMBER',2)
    mux=module_library('Adafruit_2717_TCA9548A',['VIN','GND','SDA','SCL','A0','A1','A2','RST'],['SD0','SC0','SD1','SC1','SD2','SC2'])
    s.add(mux,'A701','Adafruit 2717 / 0x77',111.76,76.2,onboard=False)
    for pin,net in {'VIN':'LOGIC_3V3','GND':'GND_SYS','SDA':'I2C_SDA','SCL':'I2C_SCL','A0':'LOGIC_3V3','A1':'LOGIC_3V3','A2':'LOGIC_3V3'}.items():s.net('A701',pin,net)
    s.nc('A701','RST')
    for pin,net in {'SD0':'BODY_SDA','SC0':'BODY_SCL','SD1':'HEAD_SDA','SC1':'HEAD_SCL','SD2':'PWM_SDA','SC2':'PWM_SCL'}.items():s.net('A701',pin,net,10.16)
    imu=module_library('Adafruit_4554_ICM20948',['VIN','GND','SDA','SCL'],[])
    for ref,value,y,sda,scl in [('A702','Body IMU / Adafruit 4554',55.88,'BODY_SDA','BODY_SCL'),('A703','Camera IMU / Adafruit 4554',116.84,'HEAD_SDA','HEAD_SCL')]:
        s.add(imu,ref,value,312.42,y,onboard=False)
        for pin,net in {'VIN':'LOGIC_3V3','GND':'GND_SYS','SDA':sda,'SCL':scl}.items():s.net(ref,pin,net)
    esp=module_library('ESP32_S3_DevKitC_1_used_GPIO',['GND','GPIO8','GPIO9','GPIO5','GPIO6','GPIO7','GPIO10','GPIO4'],[])
    s.add(esp,'A704','ESP32-S3-DevKitC-1 / used pins',111.76,195.58,onboard=False)
    for pin,net in {'GND':'GND_SYS','GPIO8':'I2C_SDA','GPIO9':'I2C_SCL','GPIO5':'PWM_OE','GPIO6':'HEARTBEAT','GPIO7':'STOP_STATUS','GPIO10':'INA_ALERT','GPIO4':'TEMP_ADC'}.items():s.net('A704',pin,net)
    s.note(190,163,'ESP32 J1 header mapping (official DevKitC-1):\nGND=22; GPIO8=12; GPIO9=15; GPIO5=5;\nGPIO6=6; GPIO7=7; GPIO10=16; GPIO4=4.\nPi USB -> board USB-to-UART port supplies power/data.\nDo not connect its 3V3 output to LOGIC_3V3.',1.5)
    s.note(190,203,'Mux RST left at onboard pull-up; channels 3-7 unused.\nIMUs: polled I2C; unused breakout pads not shown.\nSelect ONE mux channel at a time; software fusion required.\nNo bare sensor IC or custom mux PCB is implied.',1.5)
    s.note(20,251,'Electrical connection labels span sheets 04/05/07/08. Module symbols expose only the used interfaces.',1.27)
    s.note(20,260,'HOLD: power-off backfeed, ADC attenuation, cable timing, hardware stop and OE startup state must be validated.',1.27)

    s=Sheet('08_ServoBranches','08 - Ten servo signal and fused power branches')
    s.note(20,14,'PROVISIONAL: 2 x (3 ARM JOINTS + GRIPPER) + CAMERA PAN/TILT',2)
    pwm=module_library('Adafruit_PCA9685_used_ports',['VCC','GND','SDA','SCL','OE','VPLUS'],[f'PWM{i}' for i in range(10)])
    s.add(pwm,'A801','PCA9685 / A0 closed / 0x41',81.28,119.38,onboard=False)
    for pin,net in {'VCC':'LOGIC_3V3','GND':'GND_SYS','SDA':'PWM_SDA','SCL':'PWM_SCL','OE':'PWM_OE'}.items():s.net('A801',pin,net)
    s.nc('A801','VPLUS')
    names=['Left shoulder','Left elbow','Left wrist','Left gripper','Right shoulder','Right elbow','Right wrist','Right gripper','Camera pan','Camera tilt']
    for i,name in enumerate(names):
        signal=f'SERVO_PWM_{i}';CROSS.add(signal)
        s.net('A801',f'PWM{i}',signal,10.16)
        x=248.92+(i//5)*127;y=48.26+(i%5)*40.64
        ref=f'J{801+i}';fuse=f'F{801+i}'
        s.conn(ref,f'CH{i}: {name}',x,y,['GND_SYS',f'SERVO_{i}_FUSED',signal])
        # Each servo positive has its own fuse. Ground and signal bypass that fuse.
        s.add('Device:Fuse',fuse,'TBD',x-43.18,y+15.24,90,onboard=False)
        s.net(fuse,1,'SERVO_POWER_TBD',-30.48)
        fp=s.parts[fuse]['2'];jp=s.parts[ref]['2']
        s.wire(fp,(x-22.86,fp[1]),(x-22.86,jp[1]),jp)
    s.note(20,177,'A801 V+ stays unconnected.\nOnly PWM signals come from this board.\nHigh-current power uses separate\nfused distribution and return wiring.',1.27)
    s.note(20,208,'J801-J810: OUR harness convention\n1=GND, 2=fused power, 3=signal.\nConfirm actual servo plug orientation.\nCH10-15 unused; not represented.',1.27)
    s.note(20,246,'Candidate PWM servos: FT5335M arm joints; FT5121M grippers/pan/tilt. Mechanical sizing is not approved.',1.27)
    s.note(20,254,'Rail must suit final servos (candidate range 6-7.4V), never raw 6S or 12V. Fuse/cable ratings TBD from measured demand.',1.27)
    s.note(20,262,'Power removal may let arms fall. Complete hardware stop, restraints/braking, startup bias and pulse calibration before operation.',1.27)

    for s in SHEETS:s.save()
    custom=[raw for lid,(raw,pins) in CACHE.items() if lid.startswith('UnderBot_Modules:')]
    (OUT/'UnderBot_Modules.kicad_sym').write_text('(kicad_symbol_lib (version 20241209) (generator "kicad_symbol_editor") '+''.join(raw.replace('UnderBot_Modules:','') for raw in custom)+')',encoding='utf-8')
    (OUT/'sym-lib-table').write_text('(sym_lib_table (version 7) (lib (name "UnderBot_Modules") (type "KiCad") (uri "${KIPRJMOD}/UnderBot_Modules.kicad_sym") (options "") (descr "Off-board interface symbols; pin identifiers are board labels")))',encoding='utf-8')
    rootitems=[]
    for i,s in enumerate(SHEETS):
        x=35+(i%2)*190;y=40+(i//2)*48
        rootitems.append(f'''(sheet (at {x} {y}) (size 150 35) (stroke (width 0.254) (type default)) (fill (color 0 0 0 0)) (uuid {s.sheetid})
        (property "Sheetname" {q(s.title)} (at {x} {y-1.27} 0) (effects (font (size 1.27 1.27)) (justify left bottom)))
        (property "Sheetfile" "{s.name}.kicad_sch" (at {x} {y+36.27} 0) (effects (font (size 1.27 1.27)) (justify left top)))
        (instances (project "UnderBot" (path "/{ROOT}" (page "{i+2}")))))''')
    for i,note in enumerate(['UNDERBOT - LINKED ELECTRICAL SCHEMATIC / REVISION 0.4',
       'Double-click a sheet below to see the actual circuit. Same global net name connects between sheets.',
       'Detailed now: fuse / isolator / shunt path, INA228 pins, branch harnesses, sensor bus and NTC divider.',
       'HOLD: physical connectors, converter selection, actuator ratings, safety hardware and OEM base integration.']):
        y=[13,23,240,250][i];rootitems.append(f'(text {q(note)} (at 20 {y} 0) (effects (font (size {2 if i==0 else 1.5} {2 if i==0 else 1.5})) (justify left top)) (uuid {ident("root-note"+str(i))}))')
    rootdoc=f'''(kicad_sch (version 20250114) (generator "eeschema") (uuid {ROOT}) (paper "A3")
    (title_block (title "UnderBot - electrical integration schematic") (date "2026-10-02") (rev "0.4 REVIEW")
    (comment 1 "PROVISIONAL - NOT FOR FABRICATION")) (lib_symbols) {''.join(rootitems)}
    (sheet_instances (path "/" (page "1"))) (embedded_fonts no))'''
    (OUT/'UnderBot.kicad_sch').write_text(rootdoc,encoding='utf-8')
    (OUT/'UnderBot.kicad_pro').write_text(json.dumps({'meta':{'filename':'UnderBot.kicad_pro','version':1}},indent=2))
    for filename,header,rows in [('connector-schedule.csv',['Sheet','Reference','Pin','Net','Purpose','Status'],CONNECTORS),('provisional-bom.csv',['Sheet','Reference','Value','Symbol','Population','Location','Footprint'],[r for r in BOM if not r[1].startswith('#')])]:
        with (OUT/filename).open('w',newline='',encoding='utf-8') as f:
            w=csv.writer(f);w.writerow(header);w.writerows(rows)
    print(f'Wrote root + {len(SHEETS)} linked sheets, {len(BOM)} symbols and {len(CONNECTORS)} connector pins.')
