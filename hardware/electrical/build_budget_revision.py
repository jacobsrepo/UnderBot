from pathlib import Path
import csv, html, json, zipfile
import xlsxwriter

OUT = Path(__file__).resolve().parent / 'Budget-r06'
OUT.mkdir(exist_ok=True)
H = ['Category','Component','Qty','Unit EUR','Subtotal EUR','Already have?','Phase 1 2027','Volt','MaxCurrent','MaxPower','Need?']
rows=[]
def add(cat,part,q,price,owned,funded,v,a,w,need,note,url=''):
    rows.append(dict(values=[cat,part,q,price,None,'X' if owned else '',funded,v,a,w,need],note=note,url=url))
arm='https://www.berrybase.de/en/waveshare-roarm-m2-s-roboterarm-esp32-4dof-3600-basis-0-5kg-traglast-12v-wifi-uart'
add('Compute','Raspberry Pi 5 8 GB',1,250,True,0,'5 V','5 A supply provision','25 W supply budget','Yes — owned','Original owned-item valuation, not a current quote. Supply capacity includes peripherals; not measured Pi consumption.','https://www.raspberrypi.com/documentation/computers/raspberry-pi.html')
add('Arms','Waveshare RoArm-M2-S (EU), assembled, controller + gripper + mains PSU',1,209.90,False,209.90,'12 V target; 7–12.6 V accepted','5 A supplied PSU; load max N/S','60 W PSU capacity','Yes — one first','Verified German listing €209.90 incl. VAT, shipping extra; showed 5 in stock on check. Buy only after battery/protection quotes make the whole budget viable. Not a guaranteed 1 kg lifting arm. Qualify reach, mounting, stability and grasping. Supplied PSU is for bench use; battery converter is separate.',arm)
add('Arms','Second identical completed arm',1,209.90,False,0,'12 V','5 A PSU provision','60 W PSU capacity','Later','Second arm deliberately deferred by user. Requires another power branch / revised power budget.',arm)
add('Compute','Raspberry Pi AI HAT+ Hailo-8, 26 TOPS',1,112,False,0,'Via Pi HAT interface','N/S','N/S; not assumed 2 W','Optional — later','€112 is original allowance, not a verified offer. Add only for a supported workload after Pi testing.','https://www.raspberrypi.com/products/ai-hat/')
add('Structure','Simple mounting deck, arm stiffener and fasteners; reuse materials',1,20,False,20,'—','—','—','Yes — allowance','€20 spending allowance, NOT the original €65 finished enclosure. Check T12 payload, wheel traction, centre of gravity and tipping with arm extended. Does not guarantee the illustrated enclosure.')
add('Drive','Extra 12 V encoder gearmotors — removed',0,15,False,0,'12 V (old proposal)','Not selected','Not selected','No initially','Use T12 drivetrain initially. Four separate wheel motors are not part of this architecture.')
add('Drive','Cytron MDD10A — removed pending base interface tests',0,27.5,False,0,'Not connected','Not selected','Not selected','Only if OEM control replaced','Do not connect extra drivers in parallel with OEM motor drivers. Replacement would require motor current, encoder and control characterization.')
add('Drive','Used Xiaomi Robot Vacuum T12, with working battery + charger/dock',1,50,False,50,'14.8 V battery; 20 V charging input','Peak N/S','45 W nameplate','Yes — used-price target','€50 is your allowance, not a sourced offer. It was NOT marked X. Require working original battery, wheels, LiDAR and dock. OEM command/LiDAR access is not yet established; do not buy just assuming ROS access. Keep original power system separate.','https://www.mi.com/de/product/xiaomi-robot-vacuum-t12/specs/')
add('Power','Professionally assembled 6S3P P42A Li-ion pack + matched BMS, NTC, enclosure',1,150,False,150,'21.6 V nominal; 25.2 V full','Request ≥10 A continuous; supplier to confirm','12.6 Ah typ.; energy is Wh, not W','Essential — QUOTE HOLD','€150 is an optimistic FUNDING CAP, not a supplier quote. Request assembled 18-cell pack, protected connectors, cell balancing, temperature and over/under-voltage protection, and pack-level discharge rating. Do not infer 135 A pack capability from cell ratings. P42A is 3.6 V, 4.2 Ah typical (4.0 Ah minimum): 6S3P gives 21.6 V, 12.6 Ah typical. Cell datasheet energy sums to 279 Wh typical / 264.6 Wh minimum before system losses. Supplier must state usable pack energy.','https://www.molicel.com/wp-content/uploads/INR21700P42A-V4-80092.pdf')
add('Power','DC-rated disconnect, main/branch fuses, hardwired actuator stop/reset hardware',1,40,False,40,'≥30 V DC rated on 6S side','Coordinate with pack, wires and faults','Not a load rating','Essential — DESIGN/QUOTE HOLD','€40 allowance is not a priced complete emergency-stop system. Do not specify arbitrary 40 A relay or 25 A fuse. Stop must address both independent T12 drive power and arm motion, with manual restart; arm can drop on loss of torque. Final contactor/relay, fuses, suppression and restart circuit require engineering selection before powered movement.')
add('Wiring','Rated power harness, XT60/XT30, ferrules, USB data cable, strain relief',1,20,False,20,'≥30 V insulation on battery side','Per branch; size after length/current check','—','Yes — allowance','€20 allowance. No Dupont leads for motor/arm/Pi power. Include appropriately rated GPIO power connection if using the proposed Pi converter.')
add('Vision','Pi Camera Module 3 Wide / existing equivalent',1,35,True,0,'Via CSI connector','N/S','Included in Pi branch budget','Yes — owned','Use existing camera. Do not manually apply 5 V to CSI pins.','https://www.raspberrypi.com/documentation/accessories/camera.html')
add('Power','Pololu D36V50F5 #4091 — Pi DC/DC candidate',1,34.95,False,34.95,'5.5–50 V in → 5 V out','5.5 A headline; thermal derating applies','27.5 W headline output','Yes — integration check','Verified €34.95 incl. VAT, shipping extra. Not 5.1 V and not a USB-C PD source. Proposed budget route is an engineered, fused 5 V/GND header harness, load-tested at the Pi; never simultaneously power USB-C. Verify voltage drop and 5 A capability across pack voltage/temperature before setting PSU_MAX_CURRENT. If a USB-C PD solution is preferred, it costs extra; 52Pi EP-0225 cannot take 25.2 V directly.','https://www.berrybase.de/pololu-d36v50f5-5v-5-5a-step-down-spannungsregler')
add('Power','Mean Well DDR-60G-12 — dedicated arm DC/DC candidate',1,30,False,30,'9–36 V in → 12 V out','5 A output, subject to derating','60 W rated output','Yes — price/thermal check','€30 allowance, not a checked landed quote. Set/verify output at 12.0 V, not the adjustable upper limit: arm maximum is 12.6 V. 60 W matches supplied arm PSU capacity but must pass transient/thermal tests. Do not also power Kinect from this branch at full arm load. DIN mount adds space/weight. This G variant is 9–36 V input.','https://www.meanwell.com/Upload/PDF/DDR-60/DDR-60-SPEC.PDF')
add('Power','Separate 5 V auxiliary regulator for audio + MG90S',1,15,False,0,'5 V target','Size from measured servo stall + audio load','TBD','Later — for audio/pan-tilt','€15 allowance only; exact regulator deferred. Leave powered pan/tilt and speaker amplification disabled until this branch is funded. Never run pan/tilt motors from Pi 3.3 V.')
add('Solar','Roof panel + matched 6S solar charger',1,None,False,0,'Panel dependent → 25.2 V CC/CV','TBD','Panel-rated W; not battery load','Optional — later','Original €30 was not a validated complete solar charging system. Use mains charging first. No roof solar, dock solar station or supercap bank in phase 1.')
add('Sensors','Pololu VL53L1X carrier #3415',4,20,False,0,'3.3 V chosen; carrier 2.6–5.5 V','40 mA peak sensor (not board guarantee)','~0.132 W sensor at 3.3 V','Later — obstacle coverage','€20 per board allowance, not an EU quote. Use T12 sensors first only where accessible and validated. Additional ToF useful for arm-height obstacles; LiDAR does not cover everything.','https://www.pololu.com/product/3415')
add('Compute','256 GB USB 3 SSD',1,25,True,0,'5 V USB','Check exact SSD/enclosure label','N/S','Yes — owned','Original valuation. Test USB power and bandwidth with Kinect; USB port count alone does not establish compatibility.')
add('Power','Pack-supplier matched 6S Li-ion charger',1,25,False,25,'25.2 V CC/CV output','2 A target; pack supplier approval','50.4 W output target','Essential — QUOTE HOLD','€25 funding allowance, not a verified offer. Supplier must confirm chemistry, termination, polarity and connector match. Charge with robot loads disconnected for phase 1; do not assume load-sharing charger. Not a 24 V lead-acid charger.')
add('Audio','USB two-microphone array',1,20,False,0,'5 V USB','Exact model N/S','N/S','Optional — later','Keep €20 original allowance. No verified SKU selected; prioritize basic battery/arm integration first.')
add('Vision','Existing pan/tilt bracket + 2 MG90S servos',1,15,True,0,'5 V selected for later servo rail','Stall current needs exact servo test','TBD','Owned — later powered motion','Only for lightweight Pi camera. Do NOT put Kinect v2 on this bracket. Keep Pi camera fixed until auxiliary rail is funded.')
add('Audio','2 MAX98357A boards + 2 existing 3 W speakers',1,12,True,0,'5 V chosen; IC range 2.5–5.5 V','Board/load dependent','6 W speaker total ≠ DC input','Owned — later','Audio output rating is not electrical consumption. Separate auxiliary supply planned; speaker outputs are bridged and must not be grounded.','https://www.analog.com/en/products/max98357a.html')
add('Control','Arduino Uno',1,12,True,0,'5 V USB / logic','Board max N/S','N/S','Owned — reuse if needed','Arms include their own controller, so do not buy another controller just for arm operation. Uno may control later pan/tilt; 5 V signals need compatibility checks before Pi/3.3 V sensors.','https://store.arduino.cc/products/arduino-uno-rev3')
add('Control','Adafruit ICM-20948 #4554 — body + camera IMUs',2,14.90,False,0,'3.3 V VIN chosen; breakout supports 3–5 V','Breakout max N/S','N/S','Yes for final design — later','Verified €14.90 listing was unavailable. Two IMUs remain in the final design, unfunded in this phase. Use addresses 0x68 and 0x69 on short Pi I2C wiring; mux not inherently necessary. Board includes regulator/level shifting; raw IC is not interchangeable. Camera IMU follows whichever camera actually moves.','https://www.berrybase.de/fr/adafruit-tdk-invensense-icm-20948-9-dof-imu-mpu-9250-upgrade')
add('Sensors','TCA9548A I2C multiplexer',1,5,False,0,'3.3 V chosen','Board-dependent','N/S','Conditional — later','€5 allowance. Not mandatory for two IMUs with different addresses. Add for address conflict or bus topology when justified.')
add('Sensors','INA226 current monitor + suitable shunt',1,8,False,0,'3.3 V logic; monitored bus ≤36 V','Shunt/PCB rating, not IC rating','Shunt loss I²R','Optional — later','€8 allowance. Do not run whole-pack current through an unqualified small breakout shunt. Independent of I2C mux; split original combined row.','https://www.ti.com/product/INA226')
add('Compute','Official Raspberry Pi 5 Active Cooler',1,5.90,False,5.90,'5 V fan header','Check supplied fan label','Included in Pi power provision','Yes','Verified €5.90 incl. VAT from linked retailer listing; shipping extra.',arm)
add('Vision','Used Xbox One Kinect v2 sensor — confirmed version',1,10,False,0,'12 V through matching adapter; verify label','Exact sensor/adapter label needed','N/S','Yes for depth — later','€10 is your used-sensor target, not a sourced bundle. Version v2 replaces all earlier v1 choices. USB 3 connection via v2-specific adapter, NOT CSI. Fixed mount. libfreenect2/Pi 5 throughput must be tested; no promise of full-rate performance.','https://github.com/OpenKinect/libfreenect2')
add('Vision','Kinect v2 PC adapter + matching PSU + USB 3 cable',1,40,False,0,'12 V sensor-side; PSU label governs','Provision 3 A rail pending label','36 W supply allowance, not sensor rating','Required with Kinect — later','€40 allowance, not a current offer. Adapter/PSU/cable may come as a bundle; do not double-buy. Future battery conversion also requires a separate adequate 12 V branch; not funded here.')
add('Wiring','Pi 5 22-pin to camera 15-pin CSI cable',1,4,False,4,'CSI only','—','—','Yes if not already owned','€4 allowance. Remove this purchase if the correct cable is already present; do not use a Pi 4 cable without the correct Pi 5 end.')
spent=round(sum(r['values'][6] for r in rows),2)
reserve=round(600-spent,2)
add('Budget','Delivery / contingency reserve',1,reserve,False,reserve,'—','—','—','Reserve — not hardware','Only this amount is left for all shipping, price changes and minor extras. If quotations exceed caps, the plan does not fit €600; revise before buying the arm.')
assert spent==589.75 and reserve==10.25
notes=[
('Decision','Battery operation + ONE complete arm prioritized. Kinect v2 confirmed. Six X-marked entries are retained as already owned. No purchases made.'),
('Budget status','€589.75 allocated to phase-1 hardware plus €10.25 reserve = €600. This is a conditional funding plan, NOT a verified complete shopping basket. Battery €150, protection €40 and charger €25 are quotation holds. Do not commit arm funds until essential battery/protection quotes fit.'),
('Meaning of columns','Exact original 11 headers retained. Qty describes the quantity on each row, including later items; Phase 1 2027 is NEW money allocated now, not automatic subtotal. X rows cost zero new money. Subtotal is row quantity × unit value; deferred rows do not enter phase-1 total. Owned values come from your screenshot. Blank price means no defensible estimate. N/S = maximum not specified/verified.'),
('Ratings','Unless stated otherwise ratings are per unit. PSU/converter output capacity is NOT a measured load maximum. Do not sum regulator capacity, battery power and load power as if separate loads. Sensor typical current was not substituted for an unknown maximum.'),
('Battery correction','P42A nominal voltage is 3.6 V and typical capacity 4.2 Ah. 6S3P is therefore 21.6 V nominal, 25.2 V fully charged, 12.6 Ah typical; the original 22.2 V/12 Ah/266 Wh describes a different nominal-cell assumption. Supplier must label the finished pack and usable energy. No six-hour guarantee: 28 W from the old component mix is not an established measurement for this robot.'),
('What phase 1 delivers','Target: existing Pi/SSD/colour camera plus one complete arm, powered from a new protected 6S pack; T12 retains its own battery/dock. Simple reused structure. Battery/stop integration and base-control qualification remain engineering work. This is not yet a finished autonomous mobile manipulator.'),
('What is deferred','Second arm, Kinect v2 and adapter, both IMUs, extra ToF, Hailo, microphone, active audio and camera pan/tilt, telemetry, solar and custom PCB fabrication. Kinect v2 stays the intended depth camera; it has not been silently replaced by the owned colour camera.'),
('Base integration','T12 is not a Roomba. It has its own battery and OEM motor controller. Preserve them initially. Its LiDAR/control interface, added payload, tipping stability and independent hardware stop are unqualified. Do not connect 6S to its battery terminals or 20 V dock. If OEM controls cannot be accessed, replacement electronics need additional budget.'),
('Power structure','6S protected pack → main fuse/disconnect → separate fused Pi 5 V converter and actuator-stop-controlled 12 V arm converter. T12 battery → OEM T12 electronics, with separately engineered drive stop. Common signal references only as required by final interfaces; do not parallel battery positives. Pi USB/Wi-Fi → arm controller. Pi CSI → existing camera. Future Kinect USB3 + dedicated 12 V branch. No new servo PWM board required for RoArm.'),
('Pi supply decision','The lower-cost proposed Pololu route uses a rated, fused GPIO 5 V/GND harness, not a USB-C PD adapter. Requires polarity/voltage-drop/thermal qualification, no simultaneous USB-C power, and correct firmware current configuration after validating supply capacity. This is a schematic design hold, not beginner wiring instructions. A packaged Pi-compatible PD supply can replace it when budget permits.'),
('Arm supply and mounting','RoArm-M2-S is preassembled and accepts 7–12.6 V. Use 12 V; never 6S directly. The DDR-60G-12 proposal matches the 5 A/60 W supplied adapter capacity; test moving/stall transients and temperature before release. Arm reset can cause motion. Stop design must consider falling loads. Payload/space must be checked on the actual base.'),
('Quote sensitivity','Example only: battery quote €200 instead of €150, protection €65 instead of €40, and €20 shipping yields €674.75 including those costs (no extra reserve). That is €74.75 over budget before any deferred sensors. The spreadsheet allocation must not conceal this risk.'),
('Buying order','First confirm T12 condition/control access and obtain the pack+charger+protection quotes. Then lock delivered costs and arm mounting. Purchase ONE completed arm if the essential total fits. Qualify converters and wiring before battery operation. No supplier contact or order has been made.'),
('Earlier schematics','r05 used individually built servo arms and Kinect v1. Those procurement selections are superseded. Its old shopping list must not be used for this new scope. The KiCad circuit has NOT yet been rewired to these new candidates; this deliverable is the budget/component revision.'),
]
sources=[
('Arm assembly / power','https://docs.waveshare.net/RoArm-M2/Preparation-Before-Use/'),
('Pi regulator technical ratings','https://www.pololu.com/product/4091'),
('Pi GPIO power and current configuration','https://pip-assets.raspberrypi.com/categories/685-app-notes-guides-whitepapers/documents/RP-009856-WP-1-USB%20Power%20delivery%20on%20Raspberry%20Pi%205.pdf'),
('IMU breakout pinout','https://learn.adafruit.com/adafruit-tdk-invensense-icm-20948-9-dof-imu/pinouts'),
('Battery assembly quote candidate, no quote obtained','https://enerpower.de/'),
]
wb=xlsxwriter.Workbook(OUT/'UnderBot-budget-r06.xlsx')
wb.set_properties({'title':'UnderBot — €600 battery-first funding plan','comments':'Conditional allocations, not a fully priced procurement release. Checked 2026-10-02.'})
title=wb.add_format({'bold':True,'font_size':20,'font_color':'#185C76'})
wrap=wb.add_format({'text_wrap':True,'valign':'top'})
money=wb.add_format({'num_format':'€0.00','valign':'top'})
totalfmt=wb.add_format({'bold':True,'bg_color':'#FFD44F','num_format':'€0.00'})
ws=wb.add_worksheet('Revised table')
ws.merge_range('A1:K1','UnderBot | €600 battery-first plan • one completed arm',title)
ws.merge_range('A2:K2','Conditional budget: €150 battery / €40 protection / €25 charger are quote holds. €10.25 reserve. NOT a released shopping basket.',wrap)
ws.set_row(1,32)
data=[]
for r in rows:
    v=r['values']; v[4]=None if v[3] is None else round(v[2]*v[3],2);data.append(v)
ws.add_table(3,0,3+len(rows),10,{'name':'UnderBotBudget','style':'Table Style Medium 2','columns':[{'header':h} for h in H],'data':data})
for i,r in enumerate(rows,4):
    v=r['values'];ws.set_row(i,62)
    if v[3] is not None:
        ws.write_number(i,3,v[3],money)
        ws.write_formula(i,4,f'=C{i+1}*D{i+1}',money,v[4])
    ws.write_number(i,6,v[6],money)
    ws.write_comment(i,1,r['note'] + ('\nSource: '+r['url'] if r['url'] else ''),{'x_scale':2.5,'y_scale':2})
end=4+len(rows)
ws.write(end,5,'TOTAL NEW ALLOCATION',totalfmt)
ws.write_formula(end,6,f'=SUM(G5:G{end})',totalfmt,600)
ws.write(end+1,5,'HARDWARE (excl. reserve)',wrap);ws.write_number(end+1,6,spent,money)
ws.write(end+2,5,'BUDGET REMAINING',wrap);ws.write_formula(end+2,6,f'=600-G{end+1}',money,0)
ws.set_column('A:A',12,wrap);ws.set_column('B:B',58,wrap);ws.set_column('C:C',5,wrap)
ws.set_column('D:E',13,money);ws.set_column('F:F',15,wrap);ws.set_column('G:G',16,money)
ws.set_column('H:J',24,wrap);ws.set_column('K:K',28,wrap)
ws.freeze_panes(4,2);ws.set_landscape();ws.set_paper(8);ws.fit_to_pages(1,0);ws.repeat_rows(3);ws.set_zoom(75)
ws.print_area(0,0,end+2,10)
ns=wb.add_worksheet('Decisions and sources');ns.set_column('A:A',28,wrap);ns.set_column('B:B',115,wrap);ns.set_column('C:C',80,wrap)
ns.write_row(0,0,['Topic / component','Decision / price basis / limit','Source URL'],title)
n=1
for topic,note in notes:ns.write_row(n,0,[topic,note],wrap);ns.set_row(n,85);n+=1
for r in rows:
    ns.write_row(n,0,[r['values'][1],r['note'],r['url']],wrap);ns.set_row(n,95);n+=1
for label,url in sources:ns.write_row(n,0,[label,'Supporting primary source',url],wrap);ns.set_row(n,40);n+=1
ns.freeze_panes(1,1);ns.autofilter(0,0,n-1,2)
wb.close()
with (OUT/'UnderBot-budget-r06.csv').open('w',newline='',encoding='utf-8-sig') as f:
    writer=csv.writer(f);writer.writerow(H);writer.writerows(data);writer.writerow(['','','','','','TOTAL',600,'','','',''])
(OUT/'budget-data.json').write_text(json.dumps({'headers':H,'rows':rows,'notes':notes,'hardware':spent,'reserve':reserve},ensure_ascii=False,indent=2),encoding='utf-8')
esc=html.escape
trs=[]
for r in rows:
    cells=[]
    for j,v in enumerate(r['values']):
        s='TBD' if v is None else (f'€{v:,.2f}' if j in (3,4,6) else str(v))
        if j==1:
            s=esc(s)+(f' <a href="{esc(r["url"],quote=True)}">↗</a>' if r['url'] else '')+f'<details><summary>Basis / limits</summary>{esc(r["note"])}</details>'
        else:s=esc(s)
        cells.append('<td>'+s+'</td>')
    trs.append('<tr>'+''.join(cells)+'</tr>')
page='''<!doctype html><html lang="en"><meta charset="utf-8"><title>UnderBot — battery-first budget</title><style>
body{font:15px/1.45 system-ui;margin:30px;color:#173b4c;background:#f5fafc}h1{font-size:30px;margin-bottom:6px}p{max-width:1100px}.warning{background:#fff1cd;border-left:5px solid #d99500;padding:16px}.stats{display:flex;gap:18px;margin:22px 0}.stats div{background:white;padding:16px 22px;border:1px solid #b9d8e5}.stats b{display:block;font-size:25px}.scroll{overflow:auto}table{border-collapse:collapse;width:100%;min-width:1500px;background:white}th{background:#185f7b;color:white;text-align:left;position:sticky;top:0}td,th{padding:10px;border:1px solid #bad5e0;vertical-align:top}tbody tr:nth-child(odd){background:#d7edf6}td:nth-child(2){min-width:290px}td:nth-child(11){min-width:130px}details{font-size:12px;margin-top:7px;max-width:450px}summary{cursor:pointer;color:#176783}tfoot{background:#ffcc40;font-weight:bold}a{color:#086996}.notes{max-width:1150px}.notes dt{font-weight:700;margin-top:18px}.notes dd{margin-left:0}button{padding:10px;background:#185f7b;color:white;border:0;cursor:pointer}@media print{body{margin:0;font-size:9px}.scroll{overflow:visible}table{min-width:0}td,th{padding:4px}td:nth-child(2){min-width:0}th{position:static}button{display:none}.notes{page-break-before:always}}@page{size:A3 landscape;margin:10mm}
</style><h1>UnderBot · battery operation first</h1><p>One completed arm now · Kinect v2 confirmed for the depth-camera phase · 2 October 2026</p>
<p class="warning"><b>€600 is a funding cap, not a confirmed shopping basket.</b> The €150 assembled battery, €40 protection assembly and €25 charger still need supplier quotes. Do not order the arm until those essential costs fit. The earlier servo-arm/Kinect-v1 shopping list is superseded.</p>
'''+f'<div class="stats"><div>Hardware allocation<b>€{spent:.2f}</b></div><div>Delivery / contingency<b>€{reserve:.2f}</b></div><div>Total allocated<b>€600.00</b></div></div>' + '''<p>Original columns preserved. X = already owned, with €0 new spending. “Later” rows stay visible but have €0 in Phase 1. Supply capacity is labelled separately from actual load consumption. Click “Basis / limits” for price assumptions and engineering holds.</p><p><a href="UnderBot-budget-r06.xlsx">Download Excel</a> · <a href="UnderBot-budget-r06.csv">CSV</a> · <button onclick="document.querySelectorAll('details').forEach(x=>x.open=!x.open)">Toggle all notes</button></p><div class="scroll"><table><thead><tr>'''+''.join('<th>'+esc(h)+'</th>' for h in H)+ '</tr></thead><tbody>'+''.join(trs)+'</tbody><tfoot><tr><td colspan="6">TOTAL NEW ALLOCATION — includes reserve</td><td>€600.00</td><td colspan="4">Conditional on quotations</td></tr></tfoot></table></div><dl class="notes">'+''.join('<dt>'+esc(a)+'</dt><dd>'+esc(b)+'</dd>' for a,b in notes)+'</dl><h2>Additional primary sources</h2><ul>'+''.join(f'<li><a href="{esc(b,quote=True)}">{esc(a)}</a></li>' for a,b in sources)+'</ul></html>'
(OUT/'UnderBot-budget-r06.html').write_text(page,encoding='utf-8')
(OUT/'README.md').write_text('# UnderBot battery-first budget revision\n\nOpen [the revised table](UnderBot-budget-r06.html) or [Excel workbook](UnderBot-budget-r06.xlsx).\n\n'+ '\n\n'.join('**'+a+':** '+b for a,b in notes),encoding='utf-8')
assert len(H)==11 and sum(r['values'][5]=='X' for r in rows)==6
assert round(sum(r['values'][6] for r in rows),2)==600
assert all(r['values'][6]==0 for r in rows if r['values'][5]=='X')
with zipfile.ZipFile(OUT/'UnderBot-budget-r06.xlsx') as z:assert z.testzip() is None
print(f'Created {OUT}; {len(rows)} rows; hardware €{spent:.2f}; reserve €{reserve:.2f}; total €600.00; 6 owned rows verified.')
