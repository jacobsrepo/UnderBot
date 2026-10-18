"""Verify exported electrical connectivity, not merely generator syntax."""
from build_schematic_r05 import OUT, parse, child, children
import json

tree=parse((OUT/'UnderBot.net').read_text(encoding='utf-8'))
nets={child(n,'name')[1]:{(child(v,'ref')[1],child(v,'pin')[1]) for v in children(n,'node')} for n in child(tree,'nets')[1:]}
pins={p:name for name,pts in nets.items() for p in pts}
checks=[]
def same(label,*points):
    assert len({pins[p] for p in points})==1,(label,[(p,pins.get(p)) for p in points])
    checks.append(label)
def different(label,*points):
    assert len({pins[p] for p in points})==len(points),label
    checks.append(label)
same('Battery positive feeds main fuse',('J101','1'),('F101','1'))
same('Charge joins fused pack before service switch',('F101','2'),('SW101','1'),('F601','2'))
same('Service switch feeds shunt current input',('SW101','2'),('R101','1'))
same('Shunt output feeds all load branch fuses',('R101','4'),('F201','1'),('F202','1'),('F203','1'),('F401','1'),('U101','8'))
same('Positive Kelvin sense reaches INA228 IN+',('R101','2'),('U101','10'))
same('Negative Kelvin sense reaches INA228 IN-',('R101','3'),('U101','9'))
same('Protected return spans pack, charger, IC and controller',('J101','2'),('J601','2'),('U101','7'),('J301','1'))
same('3.3V supplies monitor and sensor bus',('J242','1'),('U101','6'),('J302','1'),('R303','1'))
same('SDA joins controller, monitor and upstream mux',('J301','2'),('U101','4'),('J302','3'))
same('SCL joins controller, monitor and upstream mux',('J301','3'),('U101','5'),('J302','4'))
same('NTC divider ADC junction',('R303','2'),('C301','1'),('J306','1'),('J301','8'))
same('Heartbeat crosses control and safety sheets',('J301','5'),('J406','2'))
same('PWM disable crosses control and actuator sheets',('J301','4'),('J407','5'),('R401','2'))
different('Power rails and ground are distinct',('J101','1'),('R101','4'),('J212','1'),('J222','1'),('J232','1'),('J242','1'),('J404','1'),('J101','2'))
different('Body/head I2C channels are separate',('J303','3'),('J304','3'),('J301','2'))
different('Converter harness input is not shorted to output',('J211','1'),('J212','1'))
different('External contactor is not bypassed',('J401','1'),('J402','1'))
different('Actuator converter input is not shorted to output',('J403','1'),('J404','1'))
for gpio,jpin in [('GND','1'),('GPIO8','2'),('GPIO9','3'),('GPIO5','4'),('GPIO6','5'),('GPIO7','6'),('GPIO10','7'),('GPIO4','8')]:
    same('ESP32 '+gpio+' reaches harness pin '+jpin,('A704',gpio),('J301',jpin))
same('Mux address straps all at 3.3V',('A701','A0'),('A701','A1'),('A701','A2'),('J242','1'))
for ch,ref,jref in [(0,'A702','J303'),(1,'A703','J304')]:
    same('IMU '+str(ch)+' data channel',('A701','SD'+str(ch)),(ref,'SDA'),(jref,'3'))
    same('IMU '+str(ch)+' clock channel',('A701','SC'+str(ch)),(ref,'SCL'),(jref,'4'))
    same('IMU '+str(ch)+' 3.3V supply',(ref,'VIN'),('J242','1'))
    same('IMU '+str(ch)+' ground',(ref,'GND'),('J101','2'))
same('PWM data follows mux channel 2',('A701','SD2'),('A801','SDA'),('J407','3'))
same('PWM clock follows mux channel 2',('A701','SC2'),('A801','SCL'),('J407','4'))
for i in range(10):
    j,f='J'+str(801+i),'F'+str(801+i)
    same('Servo '+str(i)+' signal',('A801','PWM'+str(i)),(j,'3'))
    same('Servo '+str(i)+' positive after fuse',(f,'2'),(j,'2'))
    source='J405' if i in (0,1,2,3,8) else 'J915'
    same('Servo '+str(i)+' fuse input',(source,'1'),(f,'1'))
    same('Servo '+str(i)+' common return',('J405','2'),(j,'1'))
different('All ten fused servo positives remain separate',*((('J'+str(801+i)),'2') for i in range(10)),('J405','1'),('J915','1'))
different('All ten PWM channels remain separate',*((('J'+str(801+i)),'3') for i in range(10)))
vplus=pins.get(('A801','VPLUS'))
assert vplus is None or len(nets[vplus])==1,'PWM board V+ must not carry servo current'
checks.append('PWM board V+ isolated from servo power')
same('Pi preregulator output feeds only PD input',('A901','VOUT'),('A902','DC_PLUS'),('J213','1'))
same('Pi preregulator input through its fuse',('A901','VIN'),('F201','2'))
same('Kinect regulator input through separate fuse',('A903','VIN'),('F202','2'))
same('Kinect regulator output reaches load',('A903','VOUT'),('J223','1'))
same('Auxiliary supply feeds logic converter',('A904','VOUT'),('A905','VIN'),('J241','1'))
same('Logic converter supplies sensor rail',('A905','VOUT'),('J242','1'))
different('Pi raw input preregulated output and USB cable are distinct',('A901','VIN'),('A902','DC_PLUS'),('A902','USB_C_OUT'))
different('Left and right BEC outputs are never paralleled',('A906','OUT_PLUS'),('A907','OUT_PLUS'))
for ref,fuse,output in [('A906','F901','J405'),('A907','F902','J915')]:
    same(ref+' input comes through fuse',(ref,'MAIN_PLUS'),(fuse,'2'))
    same(ref+' fuse follows contactor',('J402','1'),(fuse,'1'))
    same(ref+' output reaches correct group',(ref,'OUT_PLUS'),(output,'1'))
    for pin in ('BACKUP_PLUS','BACKUP_MINUS'):
        n=pins.get((ref,pin));assert n is None or len(nets[n])==1,(ref,pin,'backup must be disconnected')
    checks.append(ref+' backup inputs disconnected')
report=json.loads((OUT/'erc.json').read_text())
violations=[v for s in report['sheets'] for v in s['violations']]
errors=[v for v in violations if v['severity']=='error']
assert not errors,errors
result={'connectivity_checks_passed':checks,'net_count':len(nets),'erc_errors':len(errors),'erc_warnings':len(violations)-len(errors),'scope':'Connectivity only. No thermal, current, hardware safety, footprint or external module validation.'}
(OUT/'validation.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
print(json.dumps(result,indent=2))
