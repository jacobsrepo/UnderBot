"""Generate editable KiCad module-level drafts. No physical pinout or PCB implied."""
from pathlib import Path
from uuid import uuid4
import json

OUT = Path(__file__).resolve().parent
def uid(): return str(uuid4())
def q(s): return json.dumps(s)

def schematic(name, title, modules, notes):
    root = uid()
    libraries, placed = [], []
    for i, (ref, value, left, right) in enumerate(modules):
        kind = f"Module{i}"
        x, y = 65 + (i % 3) * 135, 53 + (i // 3) * 65
        count = max(len(left), len(right))
        h = max(12, (count + 1) * 2.54)
        pins, ext = [], []
        n = 0
        for side, entries in ((-1, left), (1, right)):
            for j, (label, net) in enumerate(entries):
                n += 1
                py = (len(entries)-1)*2.54 - j*5.08
                px = side*25.4
                pins.append(f'(pin passive line (at {px} {py} {0 if side == -1 else 180}) (length 5.08) (name {q(label)} (effects (font (size 1 1)))) (number "{n}" (effects (font (size 1 1)))))')
                ex, ey = x+px, y-py
                end = ex + side*7.62
                ext.append(f'(wire (pts (xy {ex} {ey}) (xy {end} {ey})) (stroke (width 0) (type default)) (uuid {uid()}))')
                ext.append(f'(label {q(net)} (at {end} {ey} 0) (effects (font (size 1 1)) (justify {"right" if side == -1 else "left"} bottom)) (uuid {uid()}))')
        libraries.append(f'''(symbol "Underbot:{kind}" (pin_names (offset 0.5)) (pin_numbers hide) (in_bom no) (on_board no)
          (property "Reference" "{ref}" (at 0 {h+5} 0) (effects (font (size 1.27 1.27))))
          (property "Value" {q(value)} (at 0 {h+2} 0) (effects (font (size 1.27 1.27))))
          (symbol "{kind}_0_1" (rectangle (start -20.32 {h}) (end 20.32 {-h}) (stroke (width 0.254) (type default)) (fill (type background))))
          (symbol "{kind}_1_1" {''.join(pins)}))''')
        symid = uid()
        placed.append(f'''(symbol (lib_id "Underbot:{kind}") (at {x} {y} 0) (unit 1) (in_bom no) (on_board no) (dnp no) (uuid {symid})
          (property "Reference" "{ref}" (at {x} {y-h-5} 0) (effects (font (size 1.27 1.27))))
          (property "Value" {q(value)} (at {x} {y-h-2} 0) (effects (font (size 1.27 1.27))))
          (instances (project "{name}" (path "/{root}" (reference "{ref}") (unit 1)))))''')
        placed.extend(ext)
    texts = []
    for i, note in enumerate(notes):
        texts.append(f'(text {q(note)} (at 20 {320+i*7} 0) (effects (font (size 1.5 1.5)) (justify left)) (uuid {uid()}))')
    data = f'''(kicad_sch (version 20250114) (generator "eeschema") (uuid {root}) (paper "A2")
      (title_block (title {q(title)}) (date "2026-09-29") (rev "0.1 DRAFT")
        (comment 1 "MODULE INTERCONNECTIONS ONLY - NOT FOR PCB FABRICATION")
        (comment 2 "Symbol terminal numbers are logical IDs, NOT connector pin numbers"))
      (lib_symbols {''.join(libraries)}) {''.join(placed)} {''.join(texts)})'''
    (OUT / f'{name}.kicad_sch').write_text(data, encoding='utf-8')

schematic('underbot_power', 'UnderBot 6S power architecture - provisional', [
 ('BT1','6S3P pack + matched BMS', [('Charger','CHARGE_PORT')], [('P+','PACK_PLUS'),('P-','GND')]),
 ('F1','Main fuse / disconnect', [('IN','PACK_PLUS')], [('OUT','FUSED_PACK')]),
 ('U1','INA228 + external shunt', [('IN','FUSED_PACK'),('RETURN','GND'),('Logic','SENSOR_3V3')], [('OUT','VBAT_SYS'),('I2C','I2C_CTRL')]),
 ('U2','Fused Pi buck + USB-C source', [('IN','VBAT_SYS'),('RETURN','GND')], [('5.1V / PD','PI_USB_C')]),
 ('U3','Fused 12V Kinect v1 buck', [('IN','VBAT_SYS'),('RETURN','GND')], [('12V verify adapter','KINECT_SUPPLY')]),
 ('U4','Fused auxiliary buck', [('IN','VBAT_SYS'),('RETURN','GND')], [('5V','AUX_5V')]),
 ('K1','DC actuator disconnect', [('POWER_IN','VBAT_SYS'),('Safety permit','HARDWARE_PERMIT'),('RETURN','GND')], [('POWER_OUT','VBAT_ACT')]),
 ('U5','Fused arm/servo converter', [('IN','VBAT_ACT'),('RETURN','GND')], [('Voltage TBD','SERVO_RAIL')]),
 ('U6','T12 interface - NOT RELEASED', [('IN','VBAT_ACT'),('RETURN','GND')], [('14.8V class / TBD','BASE_POWER')]),
 ('U7','3.3V logic regulator', [('IN','AUX_5V'),('RETURN','GND')], [('3.3V','SENSOR_3V3')]),
 ('U8','Safety controller / manual reset', [('NC E-stop loop','ESTOP_LOOP'),('Watchdog','WATCHDOG_OK'),('Supply','AUX_5V'),('RETURN','GND')], [('Permit','HARDWARE_PERMIT'),('Status','SAFETY_STATUS')]),
 ('J1','Fused charge input / selection', [('25.2V CC/CV','ROBOT_CHARGE'),('Return','GND')], [('Via BMS charge port','CHARGE_PORT')]),
], [
 '6S3P retained. P42A nominal specification: 21.6 V / 12.6 Ah typical; 25.2 V full. 266 Wh is the planning budget.',
 'Every converter block includes a branch fuse. Ratings, protection parts, connectors and physical pinouts remain TBD.',
 'K1 is a normally-open DC-rated power disconnect controlled by a hardware stop/reset circuit, not a GPIO relay sketch.',
 'BMS charge/discharge port topology must be followed. GND means protected system return, never bypass BMS at cell B-.',
 'T12 is rated 14.8 V, charging input 20 V. Neither its battery terminals nor dock accept direct 25.2 V.',
 'Kinect supply is provisional: identify version, adapter voltage, polarity and current before wiring.',
 'Separate charging drawing shows dock and roof solar. Charge currently bypasses INA228: use BMS for total pack coulomb count.',
 'No component footprints or physical connector pin assignments are specified. This is an architecture review draft.',
])

schematic('underbot_connections', 'UnderBot system connections - vacuum base, depth, dual IMU', [
 ('A1','Raspberry Pi 5 (assumed)', [('Power','PI_USB_C')], [('USB controller','MCU_USB'),('USB depth','KINECT_USB'),('Storage','STORAGE_LINK'),('Network','STATION_NET')]),
 ('A2','ESP32-S3 (proposed)', [('USB power + data','MCU_USB'),('Safety state','SAFETY_STATUS')], [('I2C','I2C_CTRL'),('Base link','BASE_LINK'),('Actuator command','ARM_CMD'),('Heartbeat','WATCHDOG_OK')]),
 ('A3','Kinect v1 + power/USB adapter', [('Power','KINECT_SUPPLY'),('Ground','GND'),('USB 2.0','KINECT_USB')], []),
 ('A4','I2C mux / bus interface', [('Bus','I2C_CTRL'),('Power','SENSOR_3V3'),('Ground','GND')], [('Channel 0','IMU_BODY_BUS'),('Channel 1','IMU_HEAD_BUS'),('Channels 2-5','TOF_BUSES')]),
 ('A5','Body IMU', [('Bus','IMU_BODY_BUS'),('Power','SENSOR_3V3'),('Ground','GND')], []),
 ('A6','Camera-mounted IMU', [('Bus','IMU_HEAD_BUS'),('Power','SENSOR_3V3'),('Ground','GND')], []),
 ('A7','Arm / gripper / pan-tilt drivers', [('Commands','ARM_CMD'),('Motor power','SERVO_RAIL'),('Logic','SENSOR_3V3'),('Ground','GND')], [('Harness','ACTUATORS')]),
 ('A8','Xiaomi T12 OEM controller', [('API TBD','BASE_LINK'),('Power interface TBD','BASE_POWER'),('Ground','GND')], [('Motors / encoders','BASE_MOTORS'),('LiDAR interface','OEM_LIDAR'),('Bump / cliff','BASE_SAFETY')]),
 ('A9','Existing LiDAR', [('OEM power/data','OEM_LIDAR')], []),
 ('A10','ToF sensors x4 (proposed)', [('Separate mux channels','TOF_BUSES'),('Power','SENSOR_3V3'),('Ground','GND')], []),
 ('A11','SSD + optional accelerator', [('Pi interfaces','STORAGE_LINK')], []),
 ('A12','Audio / display / fans / status', [('Power (verify each)','AUX_5V'),('Ground','GND'),('Data via Pi/MCU','AUX_LINKS')], []),
], [
 'Named nets in both drawings denote the same interface. Bus labels are conceptual cables, not single copper traces.',
 'Vacuum base with differential drive assumed; NO mecanum wheels. OEM motor control, encoders and safety sensors preferred.',
 'LiDAR stays on OEM wiring provisionally. Access through documented base API or a model-specific adapter to Pi; do not guess pins.',
 'Kinect v1 assumed from user: USB 2.0 + libfreenect. Confirm model label and validate depth streaming on the Pi.',
 'Two separate IMU bus channels avoid equal-address conflicts. Camera IMU must move with camera; publish separate frames.',
 'PCA9685 applies only to PWM servos. Smart bus servos require the matching bus transceiver and feedback protocol.',
 'ESP32 shown USB-powered only; do not also inject external 5V without verified power selection/backfeed protection.',
 'T12 also has an OEM gyro. Body IMU + head IMU remain explicit; OEM gyro access and LiDAR protocol are unverified.',
])

schematic('underbot_charging', 'UnderBot charging architecture - separate robot and station batteries', [
 ('G1','Station PV: 2 x 100W series', [], [('PV+ / PV-','PV_INPUT')]),
 ('U1','PV disconnect + MPPT 100/20', [('PV','PV_INPUT')], [('Battery port','STATION_BAT')]),
 ('BT1','8S LiFePO4 + BMS / fuse', [('Charge / discharge','STATION_BAT')], [('Protected 25.6V nominal','STATION_DC')]),
 ('U2','True buck-boost Li-ion charger', [('Fused input','STATION_DC')], [('25.2V CC/CV 4A','DOCK_DC')]),
 ('U3','Dock protection / interlock', [('Charge source','DOCK_DC'),('Dock detect','DOCK_DETECT')], [('Protected contacts','DOCK_CHARGE')]),
 ('U4','Mains 6S Li-ion charger', [], [('25.2V CC/CV 4A','MAINS_CHARGE')]),
 ('G2','Robot roof PV 5-6Wp', [], [('Panel','ROOF_PV')]),
 ('U5','6S solar MPPT charger', [('Panel','ROOF_PV')], [('6S profile verified','SOLAR_CHARGE')]),
 ('U6','Charge source management', [('Dock','DOCK_CHARGE'),('Mains','MAINS_CHARGE'),('Solar','SOLAR_CHARGE')], [('Selected / managed','ROBOT_CHARGE')]),
 ('BT2','Robot pack 6S3P + BMS', [('Via power drawing J1','ROBOT_CHARGE')], []),
], [
 'Cable-level diagram: every power interface includes positive AND protected return. No connection to raw cell B-.',
 'Station LiFePO4 and robot Li-ion need DIFFERENT charging profiles. Do not tie the batteries together.',
 'Use a true buck-boost charger across the station battery voltage range. CC/CV supply alone is not charge management.',
 'Charge-source management must prevent backfeed, enforce combined current/temperature limits and preserve termination.',
 'Simplest prototype: one charge source selected at a time, robot off while charging, appropriate BMS connected.',
 'Dock needs current limiting, contact sequencing, polarity protection and motion inhibit; Hall detection alone is insufficient.',
 'Validate series-panel cold Voc against 100V MPPT limit and Vmp headroom. Roof solar is supplemental, not 8A charging.',
 'Optional independent beacon is not included in the shared robot rail; give it its own protected battery/charger power path.',
])
print('Generated three KiCad architecture schematics.')
