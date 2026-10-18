# UnderBot linked schematic — 0.3, 1 October 2026

Open **UnderBot.kicad_pro** in KiCad, then open Schematic Editor. **UnderBot.kicad_sch is the root file**: double-click its sheet boxes to enter the actual circuits. The PDF has a cover/index plus six circuit pages.

This is a provisional **system wiring / distribution design**, not a PCB fabrication release. It advances the previous module diagrams with standard circuit symbols, actual electrical nets, a pin-level INA228 circuit, and numbered proposed harness connectors. The previous drawings and presentation remain unchanged.

## What is connected

1. **Battery:** J101 protected pack output -> F101 -> SW101 -> R101 four-terminal shunt -> switched load bus. Charge joins before SW101 through the two coordinated fuse paths. Only protected BMS return is used.
2. **Monitoring:** INA228 physical pin mapping, 3.3 V supply, 100 nF bypass, ground-address straps, ALERT pull-up, bus-voltage input and Kelvin sense. A finished breakout can substitute only after its shunt and pad connections are verified.
3. **Power rails:** three individually fused converter input harnesses, separate converter output harnesses and load connectors; an auxiliary-fed 3.3 V regulator connection. Converter electronics are external and still need exact part selection. No wire connects a converter input directly to its output.
4. **Control/sensors:** proposed ESP32 signal harness, upstream I2C bus, separate body/head mux channels, optional upstream pull-ups, and a 10k candidate NTC divider/filter. USB powers the ESP32; its 3.3 V output is not tied to the external logic regulator. Power sequencing and powered-off signal backfeed still need verification.
5. **Actuators:** fused feed to an external normally-open contactor, distinct load-side return connector, converter harness, servo distribution output and candidate PWM-board interface. PCA9685 must be changed to 0x41 with A0 bridged; a dedicated mux channel alone does not avoid the upstream INA228 address conflict. The mux is set to 0x77 to avoid PCA9685 ALLCALL 0x70.
6. **Charging:** one finished 25.2 V CC/CV charger input at a time, with a charge fuse and common-port BMS return. Parallel chargers, roof-solar combining and autonomous docking remain outside this circuit revision.

Matching **global net labels connect across sheets**. Matching local labels connect only within their sheet. Orange/blue presentation arrows have been replaced here by KiCad electrical connections; the PDF uses KiCad's standard colours.

## Connector numbering and off-board parts

The CSV connector schedule defines **our proposed harness pin assignments**, not the pin order on the Pi, ESP32, sensor breakouts, Qwiic connectors, charger or T12. Connector housing/terminal part numbers, keying, wire colours and mating views remain unselected. Do not build adapter cables by assuming matching pin numbers on third-party boards.

`TO converter` connects to the module's actual VIN/return terminals. `FROM converter` connects to its actual VOUT/return terminals. These are separate harness connections with an external converter between them. The same applies to the contactor LINE/LOAD harnesses and I2C mux channels. External modules are not secretly implemented on this PCB.

F101, SW101 and R101 carry an `Assembly=OFF-BOARD` property. They remain in the exported **system** netlist so that the entire current path can be checked. Before a PCB transfer, establish the board boundary and replace off-board parts with their board-side terminals; do not place a pack fuse/isolator on a small PCB just because it appears in the system netlist. Footprints are intentionally unassigned.

## Unfinished engineering decisions

| Item | Remaining work |
|---|---|
| Battery/BMS | Exact cell, BMS model, charge port topology, current/temperature settings, protected connector |
| Protection | Fuse coordination, cable ampacity, connector ratings, reverse polarity, transients and inrush |
| Converters | Exact models, peak/continuous output, thermal checks, grounding and startup behaviour |
| Pi supply | A verified 5.1 V target source with suitable USB-C source behaviour and cable; no generic PD circuit is implied |
| Sensors | Adafruit 4554 IMUs and 2717 mux proposed; validate firmware fusion, bus pull-ups, cable timing and power-off behaviour |
| ESP32 | Final GPIO allocation, ADC range/attenuation, heartbeat timing and startup configuration |
| Actuators | Models/counts, required voltage, stall currents, protocol, per-load fuses, gravity/braking behaviour |
| Emergency stop | Two-channel stop/reset hardware, watchdog circuit, feedback, contactor/coil selection, suppression and interlocked precharge; sheet 05 only defines interfaces |
| T12 | Original battery stays separate; confirm controller API, LiDAR access and independent hardware stop |
| Charging | Correct charger/BMS compatibility, touch-protected connector and temperature policy; unattended dock design deferred |

**DNP means “do not populate.”** R301/R302 are optional pull-ups pending the actual bus population; at least one suitable pull-up set must exist. R401 is held DNP until the PWM breakout's OE pull-down/power-on behavior is resolved. Do not enable actuator hardware with this unresolved. PWR_FLAG symbols tell ERC that the external 3.3 V module and return supply power; they are neither physical parts nor proof a power source exists.

## Sources checked

The 2 October update adds named sensor modules, manufacturer-labelled adapter connections and a servo shortlist in [COMPONENT_SELECTION.md](COMPONENT_SELECTION.md). Sheets 04/05 include the corrected bus addresses. Servo power and safety hardware remain provisional.

- [TI INA228 datasheet](https://www.ti.com/lit/ds/symlink/ina228.pdf): DGS pin table, supply limits and application guidance. A0/A1 tied to ground selects address 0x40.
- [Pololu D36V50F12](https://www.pololu.com/product/4095): candidate Kinect converter; manufacturer VIN/GND/VOUT pad names, input range and load-dependent output rating. No physical pad-number mapping is assumed.
- KiCad 10.0 installed standard libraries: Device, Switch, Connector_Generic, Sensor_Energy and power. Symbols are embedded in the schematic; inherited INA228 properties and geometry are expanded from the installed library.
- Earlier [electrical design review](../README.md) contains the battery, T12, charging and component-list references.

## Validation and files

`erc.json` is the unfiltered KiCad error/warning report. `validation.json` records checks against **KiCad's exported netlist**, including the entire fuse/switch/shunt chain, charge branch, Kelvin pins, cross-sheet I2C, ADC junction, distinct power rails and absence of contactor/converter bypasses. These checks do not validate hardware ratings, external modules, safety performance or fabrication readiness.

- `UnderBot-schematic.pdf`: seven-page review document.
- `connector-schedule.csv`: 74 proposed harness pin assignments.
- `provisional-bom.csv`: component values/status; not a purchasing list.
- `UnderBot.net`: system electrical netlist.
- `svg/`: individual vector sheet exports.
- `../build_schematic.py`: reproducible source generator; rerunning overwrites generated project/sheets.
- `../check_schematic.py`: connectivity checks; rerun after exporting a changed netlist/ERC report.

Once manual KiCad editing begins, treat those edits as authoritative and do not regenerate over them without reconciling the generator.
