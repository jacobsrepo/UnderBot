# UnderBot electrical schematic - revision 0.4

Open `UnderBot.kicad_pro` in KiCad, then its schematic. Double-click a sheet on the index, or use the sheet navigator. `UnderBot-schematic.pdf` contains nine pages: index plus eight circuit sheets.

This separate revision preserves the previously opened revision 0.3. It is a system integration schematic, not a fabrication-ready PCB.

## New in this revision

- Sheet 07 draws the selected external mux, both IMU boards and the used ESP32 GPIO connections as named module interfaces. Pins are identified by board labels, not bare-IC pin numbers. Symbols show used interfaces only; passive pin types intentionally do not model internal electronics or verify direction/voltage compatibility.
- Sheet 08 draws ten independently fused servo outputs, each with ground, fused positive and PWM signal. Servo power bypasses the PCA9685 board. Its V+ connection is intentionally unused.
- Global labels join the actual module interfaces to the existing carrier/harness connectors. They represent cables electrically, not additional parallel hardware.
- A local `UnderBot_Modules.kicad_sym` library and `sym-lib-table` keep the custom off-board interface symbols editable and portable.

The provisional motion arrangement is left/right shoulder, elbow, wrist and gripper, plus camera pan and tilt. Joint names and count are design assumptions; this does not establish robot kinematics or payload capability. Channel mapping is on sheet 08 and in `connector-schedule.csv`.

## ESP32 assignment

Use the official ESP32-S3-DevKitC-1 board as the design reference. Match board revision and silkscreen before assembling a harness. Firmware must explicitly configure these pins; no firmware has been changed by this schematic update.

| Signal | GPIO / board label | Official J1 header pin | Direction at ESP32 |
|---|---|---|---|
| Ground | GND | 22 | Common reference |
| I2C SDA | GPIO8 | 12 | Bidirectional |
| I2C SCL | GPIO9 | 15 | Bus clock, open drain |
| PWM output disable | GPIO5 | 5 | Output; HIGH requests disable |
| Heartbeat | GPIO6 | 6 | Output to external watchdog |
| Stop status | GPIO7 | 7 | Input; source must be 3.3 V compatible |
| INA228 ALERT | GPIO10 | 16 | Input, active-low alert |
| Thermistor ADC | GPIO4 | 4 | ADC1_CH3 input |

USB from the Pi connects to the development board's USB-to-UART connector for power and serial communication. The board's 3.3 V output is not connected to the separate LOGIC_3V3 rail. This separation does not by itself prevent signal backfeeding: powered-off I/O behaviour and sequencing are still unresolved. ADC attenuation/calibration must match the divider's possible voltage range; this divider is not a battery-safety controller.

Source: [Espressif DevKitC-1 hardware reference](https://docs.espressif.com/projects/esp-dev-kits/en/latest/esp32s3/esp32-s3-devkitc-1/user_guide_v1.1.html).

## Module configuration

- INA228: 0x40, A0/A1 low as physically drawn on sheet 02.
- TCA9548A breakout: 0x77, A0/A1/A2 high as drawn on sheet 07. RST remains at its onboard pull-up. Channels 3-7 unused.
- ICM-20948 boards: their default addresses may be identical because only one mux channel is enabled at a time. Body uses channel 0 and head uses channel 1. Polling is the proposed first implementation, so interrupts are not used.
- PCA9685: channel 2, regular address 0x41 with the board's A0 jumper bridged. ALLCALL 0x70 is kept clear of the mux. The A0 modification is an assembly requirement, not an external net validated by ERC.

See [component recommendations and manufacturer sources](COMPONENT_SELECTION.md). The chosen IMUs require software orientation fusion. The schematic does not synchronize them to Kinect frames or configure ROS transforms.

## What remains unfinished

Fuse values, wire sizes, connector housings, converter current/thermal ratings and PCB footprints are not released. The actuator rail remains `SERVO_POWER_TBD` until mechanical and electrical sizing is completed. FEETECH models are candidates, not approved arm actuators.

Sheet 05 defines interfaces to a missing external safety controller and contactor system. E-stop channels, manual reset, watchdog implementation, coil drive/suppression, precharge and gravity-load restraint still need engineering. PWM_OE is not an emergency stop. Do not operate the arms from this drawing alone.

The Pi supply interface, reverse-polarity and transient protection, external regulator internals, dock automation, solar-source combining and OEM T12 integration are outside this revision. T12 retains its own battery. See [revision 0.3 design scope](../UnderBot-Schematic/README.md) for the unchanged battery, INA228 and charger limitations.

Module interfaces omit unused pads deliberately. No-connect marks for mux RST and PWM V+ mean no external wire; they do not remove a module's onboard biasing. Custom symbols and all off-board fuses remain in the system netlist for connectivity checking. Define a PCB boundary and replace off-board devices with board-side terminals before PCB transfer.

## Verification

`erc.json` is the KiCad report. `validation.json` records checks against the exported netlist, including each GPIO mapping, mux/IMU signal pair, servo signal, fuse input/output and return. These checks cannot prove external module operation, correct mechanical orientation of a connector, current ratings, address straps inside a module, or functional safety. No physical hardware was tested.

Generator: `../build_schematic_r04.py`. Validator: `../check_schematic_r04.py`. The generator overwrites this revision's generated schematic files. Reconcile manual KiCad edits before rerunning it.
