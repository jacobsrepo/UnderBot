"""Write a linked purchasing list with explicit quantities and ordering status."""
from pathlib import Path
import csv, html
OUT=Path(__file__).resolve().parent/'UnderBot-Schematic-r05'
rows=[
('Controller','Espressif ESP32-S3-DevKitC-1-N8R8',1,1,'BUY if not already owned','Official development board; USB data cable matched to board connector. No generic pinout substitution.','https://docs.espressif.com/projects/esp-dev-kits/en/latest/esp32s3/esp32-s3-devkitc-1/user_guide_v1.1.html'),
('Body + head IMUs','Adafruit ICM-20948 breakout #4554',2,2,'BUY','3.3V VIN; software fusion; one board per mux channel.','https://www.adafruit.com/product/4554'),
('I2C multiplexer','Adafruit TCA9548A #2717',1,1,'BUY','A0/A1/A2 high for address 0x77.','https://www.adafruit.com/product/2717'),
('PWM controller','Adafruit PCA9685 #815',1,1,'BUY','Bridge A0 for 0x41; V+ unused. OE startup modification must be resolved before powered servo tests.','https://www.adafruit.com/product/815'),
('Shoulder servos','FEETECH FT5335M / Pololu #3429',1,2,'BUY ONE FOR QUALIFICATION','Final assignment CH0 and CH4. 17T horn; use supplied horn. External bearing support required.','https://www.pololu.com/product/3429'),
('Other eight servos','FEETECH FT5121M / Pololu #3427',1,8,'BUY ONE FOR QUALIFICATION','Elbow/wrist/gripper on each side plus head pan/tilt; 25T horn. Buy remaining seven after sample test.','https://www.pololu.com/product/3427'),
('Servo DC/DC','Hobbywing UBEC 25A HV #30606000',1,2,'BUY ONE FOR QUALIFICATION','Set 6.0V. Second identical unit for other group after test. Do not buy UBEC 10A by mistake. No backup battery.','https://www.hobbywing.com/index.php/products/ubec-25a-hv95.html'),
('Pi preregulator + Kinect supply','Pololu D36V50F12 #4095',2,2,'BUY','Two separate 12V converters; one feeds EP-0225, one Kinect adapter. Stock/backorder must be checked.','https://www.pololu.com/product/4095'),
('Pi USB-C PD source','52Pi EP-0225',1,1,'BUY','Feed regulated 12V only; full 6S is above its 24V input limit. Included USB-C output cable.','https://52pi.com/products/52pi-pd-power-extension-adapter-board-for-raspberry-pi-5'),
('Auxiliary 5V supply','Pololu D36V28F5 #3782',1,1,'BUY','Prototype continuous load allocation 2A; verify thermal margin.','https://www.pololu.com/product/3782'),
('Logic 3.3V supply','Pololu D24V5F3 #2842',1,1,'BUY','Input AUX_5V; initial logic budget 0.2A.','https://www.pololu.com/product/2842'),
('Emergency-stop operator','Schneider Electric XB5AS8444',1,1,'BUY','Exact 2NC version. This is an operator only, not a complete stop system; never switch servo current through it.','https://shop.se.com/pro/us/en/product/emergency-stop-switching-off-harmony-xb5-plastic-red-mushroom-40mm-22mm-trigger-latching-turn-to-release-2nc/'),
('Battery assembly','Custom 6S3P Molicel P42A, assembled and protected',0,1,'REQUEST QUOTE','Use PACK_REQUEST.md. Do not buy loose cells, generic BMS or a mismatched stock 24V pack.','https://enerpower.de/'),
('Matched mains charger','Mascot 2440 LI, 6-cell / 25.2V variant',0,1,'ORDER THROUGH PACK SUPPLIER','Specify exact Li-ion variant and matched connector; request temperature option and system compatibility. Not 2440 LiFe.','https://www.mascot.no/products/battery-chargers/2440-li'),
('Kinect adapter','Xbox 360 Kinect v1 PC USB + power adapter',0,1,'REUSE / VERIFY MODEL','Keep original cable/adapter for first streaming test; no Xbox One adapter. Battery conversion only after checking label and polarity.','https://github.com/OpenKinect/libfreenect'),
('Pack disconnect / fuse / shunt','Integrated protected distribution assembly',0,1,'ENGINEERED ASSEMBLY QUOTE','25A main fuse remains a candidate. Supplier must coordinate fuse, switch, terminals, wire and prospective fault current.',''),
('Stop/reset/contactor assembly','Hardwired manual-reset actuator stop assembly',0,1,'ENGINEERED ASSEMBLY QUOTE','See PACK_REQUEST.md interface requirements; includes separate verified stop for independently powered T12.',''),
('Power monitor','INA228 carrier plus external Kelvin shunt',0,1,'PCB STAGE','Do not substitute an INA228 breakout with its small onboard shunt in the whole-pack path. Existing bare-IC sheet is a design, not a finished module.','https://www.ti.com/product/INA228'),
('Wiring / connectors / brackets','Harness and mechanical kit',0,1,'AFTER PHYSICAL LAYOUT','Requires rated servo distribution, strain relief, insulated terminals and connector mating drawings; not a Dupont breadboard build.',''),
('Solar station / roof solar / supercaps','Later phase',0,0,'DO NOT BUY YET','Complete wired charging, base access and measured power budget first.',''),
]
headers=['Function','Exact selection','Buy now qty','Full robot qty','Ordering status','Notes','Source / product link']
OUT.mkdir(exist_ok=True)
with (OUT/'shopping-list.csv').open('w',newline='',encoding='utf-8-sig') as f:
    w=csv.writer(f);w.writerow(headers);w.writerows(rows)
md=['# UnderBot selected parts - 2 October 2026','','Buy the **Buy now** quantities first. Full-robot quantities are the total eventual quantities, not additional quantities. The two servo samples qualify mechanics and power before duplicating the design. Prices, tax, shipping and stock are not guaranteed. Existing Pi, T12 and Kinect are reused.','','| Function | Exact selection | Buy now | Full robot | Status |','|---|---|---:|---:|---|']
for role,part,now,total,status,note,url in rows:
    link=f'[{part}]({url})' if url else part
    md.append(f'| {role} | {link} | {now} | {total} | {status} |')
md+=['','## Ordering notes','']
for role,part,now,total,status,note,url in rows:md.append(f'- **{part}:** {note}')
md+=['','The supply architecture and mechanical target are documented in [README.md](README.md). The pack supplier request is [PACK_REQUEST.md](PACK_REQUEST.md). No purchases or supplier messages have been sent.']
(OUT/'BUY_LIST.md').write_text('\n'.join(md),encoding='utf-8')
tr=[]
for role,part,now,total,status,note,url in rows:
    link=f'<a href="{html.escape(url,quote=True)}">{html.escape(part)}</a>' if url else html.escape(part)
    tr.append(f'<tr><td>{html.escape(role)}</td><td>{link}<small>{html.escape(note)}</small></td><td>{now}</td><td>{total}</td><td>{html.escape(status)}</td></tr>')
(OUT/'BUY_LIST.html').write_text('''<!doctype html><html><head><meta charset="utf-8"><title>UnderBot - selected parts</title><style>body{font:16px system-ui;max-width:1350px;margin:40px auto;padding:20px;color:#183047;background:#f5f7fa}h1{font-size:32px}table{width:100%;border-collapse:collapse;background:white}td,th{padding:14px;text-align:left;border-bottom:1px solid #dbe2ea;vertical-align:top}th{background:#183047;color:white}a{color:#0369a1}small{display:block;margin-top:6px;color:#4b5563;max-width:620px}p{max-width:1000px;line-height:1.6}</style></head><body><h1>UnderBot - what to buy</h1><p>Selected prototype parts · 2 October 2026. Buy the <b>Buy now</b> quantities first. Full robot means the eventual total, not additional parts. Servo samples qualify the mechanism before the remaining units are ordered. Reuse your Pi, Kinect and T12.</p><p><b>Design target:</b> two compact arms, approximately 190 mm reach and 250 g payload target; ten PWM servos, two separate 6.0 V supplies. This is a target for testing, not a demonstrated lifting rating.</p><table><thead><tr><th>Function</th><th>Exact component and ordering notes</th><th>Buy now</th><th>Full robot</th><th>Status</th></tr></thead><tbody>'''+''.join(tr)+'''</tbody></table><p><b>Still required before battery operation:</b> rated harness/protection, verified stop hardware, load tests and base integration. Solar, dock automation and custom PCB ordering are later phases. Check stock and local delivered prices; no purchases have been placed.</p></body></html>''',encoding='utf-8')
print('Wrote shopping-list.csv, BUY_LIST.md and BUY_LIST.html')
