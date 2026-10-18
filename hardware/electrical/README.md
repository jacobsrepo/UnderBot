> **CURRENT DESIGN: r07 NOCO + T12.** [Open the current drawing and parts list](UnderBot-r07/index.html). User selected existing batteries; no new 6S pack/BMS/charger. Adeept kit replaces Waveshare. Earlier designs below are historical.

> **Budget/scope update (2 October 2026):** The user has selected ONE assembled arm, battery operation first, Kinect v2 and a EUR 600 funding cap. See [the revised budget](Budget-r06/README.md). Older servo-arm/Kinect-v1 shopping lists below are superseded; schematics have not yet been updated to this scope.

# UnderBot electrical design — review draft 0.1

**New linked schematic (1 October 2026):** [UnderBot-Schematic/README.md](UnderBot-Schematic/README.md) explains the six circuit sheets, connector schedule and remaining design holds. Open [UnderBot.kicad_pro](UnderBot-Schematic/UnderBot.kicad_pro) or the [seven-page schematic PDF](UnderBot-Schematic/UnderBot-schematic.pdf). This develops the earlier block diagrams into a provisional wiring/circuit project; it is not a fabrication release.

**For the team presentation:** open [the zoomable connection map](UnderBot-team-connection-map.html), [single-page PDF](UnderBot-team-connection-map.pdf), or [PNG image](UnderBot-team-connection-map.png). This newer presentation (0.2) explicitly shows the recommended initial prototype with the T12's original battery kept separate. The earlier KiCad base-power branch remains a future, unvalidated single-pack integration target.

KiCad 10.0.6 is installed at `C:\Users\samja\AppData\Local\Programs\KiCad\10.0\bin` and its CLI version was verified. Open any `.kicad_sch` in KiCad Schematic Editor. The SVG/PDF exports can be viewed without KiCad.

**These are editable module-interconnection schematics, not a fabrication-ready PCB circuit.** Symbols use logical terminals, not manufacturer pin numbers. Bus labels represent cables/interfaces. No PCB footprints, trace widths, connector pinouts, regulator component values or safety certification are implied. Parts listed below are candidates unless explicitly verified.

## Design basis

- User-selected architecture: Xiaomi T12 vacuum base with existing LiDAR, probable Xbox 360 Kinect v1, body IMU plus a separate camera-mounted IMU, dual arms/grippers and camera pan/tilt, Raspberry Pi and ESP32, 6S3P 21700 pack, roof solar and a solar charging station.
- Existing PC EMEET camera and Bluetooth audio experiments are not evidence of the final onboard sensor BOM. The previous mecanum URDF and humanoid wiring illustration are superseded for this design, but their files have not been changed.
- The shared Claude page could not be read through its security check. The user's pasted 32-item list and corrections are the source for the review below.
- Xiaomi lists the T12/B106GL at **14.8 V nominal**, with **20 V charging input** and a **350 mm diameter** body. The illustration's 200 mm footprint cannot describe this base. It also includes wheel speed sensors, bump/cliff sensors and an OEM gyro. Its accessible control/LiDAR protocol is not established. [Xiaomi specifications](https://www.mi.com/de/product/xiaomi-robot-vacuum-t12/specs/)

## Recommended power structure

Keep 6S3P, with a matched BMS, main fuse close to the pack and a service disconnect. Use commercial DC/DC modules on a distribution/carrier board for the first revision. A custom switching converter design is not necessary just to obtain several rails.

| Branch | Proposed voltage | Load and decision |
|---|---|---|
| Compute | Regulated 5.1 V target at the source; verify at Pi under load | Pi 5, its USB peripherals, fan and any SSD/accelerator. Design for the actual full peripheral load and a suitable USB-C source interface. |
| Depth | 12 V candidate, subject to original adapter label | Kinect v1 power/USB adapter; USB data to Pi. Keep independent of actuator shutdown. |
| Auxiliary | 5 V | Audio, indicators and selected accessories; individual module voltages still apply. |
| Sensor logic | 3.3 V | MCU-compatible IMUs, bus mux and monitor logic. Use actual breakout specifications; some bare sensors need other voltages. |
| Arms | TBD: commonly 6 V, 7.4 V or 12 V depending on actuator | Only select after torque, stall current and actuator protocol are known. Do not put ordinary hobby servos on 12 V. |
| Base | 14.8 V-class interface, **not yet released for connection** | Preserve OEM electronics initially. A battery-emulating supply needs input-range, battery-sense, peak-current and regenerative-energy validation. A nominal 14.8 V setting alone does not establish compatibility. |

Most branches need **buck** conversion. A true buck-boost is useful for charging the 25.2 V robot pack from a station battery whose voltage moves above and below that target; roof solar may need boost MPPT. A regulated 24 V actuator rail would also require buck-boost across a 6S discharge range, so avoid selecting 24 V actuators solely because the battery is called “24 V.”

The Pi's recommended supply is 5 V / 5 A. A bare buck plus USB-C connector does not automatically advertise the appropriate current. Specify a working Pi-compatible power source, cable and peripheral budget. [Raspberry Pi power documentation](https://www.raspberrypi.com/documentation/computers/getting-started.html)

For initial base integration, retain the T12's original battery and charging system while identifying its interfaces. Do not connect its battery in parallel with the 6S pack, feed its 20 V dock with 25.2 V, or operate two competing motor controllers. The single-pack drawing represents the later integration target. If the OEM controller cannot provide the required command/feedback access, replacement motor drivers and a separate LiDAR adapter become a distinct engineering task.

## Connections and stop behavior

Pi -> USB -> ESP32 for low-level command/feedback. Kinect v1 -> correct power/USB adapter -> Pi USB; use libfreenect, not libfreenect2. Confirm depth and RGB streaming on the actual Pi before freezing the compute choice. [OpenKinect driver](https://github.com/OpenKinect/libfreenect)

ESP32 -> short 3.3 V I2C bus -> mux -> body IMU and camera IMU on different channels, plus four optional ToF channels. A TCA9548A-class mux is a candidate, not a selected footprint. Separate channels avoid repeated I2C-address conflicts. Check total pull-ups, cable capacitance, interrupt/reset wiring and breakout power requirements. Longer moving-head cables may require a more robust interface instead of raw I2C. Pi and ESP32 must not independently drive the same bus without a deliberate multi-master design.

Body IMU attaches rigidly to the chassis; head IMU moves with the camera. Publish calibrated `base_imu_link`, `camera_imu_link` and Kinect optical frames using pan/tilt joint positions. Neither IMU replaces wheel encoders. The T12's internal gyro is an additional OEM sensor, not assumed accessible.

PWM servos: ESP32 -> PCA9685 -> signal pins; servo power comes from a separately fused distribution bus. PCA9685 logic VCC stays at 3.3 V and its OE should default disabled. Verify OE pull-downs on the chosen breakout before adding a pull-up. Smart servos instead need their matching UART/RS-485/CAN interface. Counts and channel allocation depend on the actual arms, grippers and pan/tilt hardware. [PCA9685 wiring reference](https://learn.adafruit.com/16-channel-pwm-servo-driver/pinouts)

E-stop -> hardwired stop/reset circuit -> normally-open DC actuator disconnect. Add watchdog, power-on inhibit, manual reset, appropriate coil suppression and feedback monitoring. Firmware OE/enable is secondary. The drawing's K1 does not claim a safety-rated stop. A retained independently powered T12 needs its own verified hardware stop path; opening K1 on the new pack will not stop that battery-powered base. If switching off the entire OEM base also removes LiDAR, document that behavior; keeping LiDAR alive requires a verified separate supply/interface.

Loss of arm power can make an arm fall: braking, counterbalance or safe mechanics must be part of the arm selection. Actuator bulk capacitors and braking energy also affect stop time. A precharge bypass must not continue powering actuators after a stop.

Use a low-impedance protected ground distribution with separate actuator returns and logic returns meeting at the distribution point. Do not route motor current through the Pi/ESP32 ground wiring. All returns and chargers must respect the BMS protected port; a USB cable, chassis bond or scope ground must not bypass its switching path. “Separate aux buck” does not mean galvanically isolated. USB-powered ESP32 is shown with no simultaneous external 5 V injection.

## Review of the supplied component list

| Original items | Disposition / correction |
|---|---|
| 1: P42A / 50S, 18 cells | Keep 6S3P, but use one exact cell model. P42A is 3.6 V nominal and 4.2 Ah typical, giving 21.6 V / 12.6 Ah nominal arithmetic, not exactly 22.2 V / 12 Ah. Full charge remains 25.2 V. Manufacturer lists 15.5 Wh typical per cell; integrated energy and nominal V x Ah are not identical. Samsung 50S is not interchangeable under a blanket “4000 mAh, 45 A” rating. [Molicel datasheet](https://www.molicel.com/cn/wp-content/uploads/INR21700P42A_1.7_Product-Data-Sheet-of-INR-21700-P42A-80092.pdf) |
| 2: JK/Daly BMS | Exact model/firmware must support 6S conventional Li-ion, temperature limits and the intended ports. JK-B1A8S-10P is a 100 A-class model, not a 40 A part; configure protection around the pack/wiring, not its headline maximum. UART voltage/interface may need an adapter. [JK specification](https://www.jkbms.com/wp-content/uploads/2026/02/JK-B1A8S-10P-Product-specification-19.1.1.pdf) |
| 3: INA228 + shunt | Good monitoring concept; external Kelvin shunt and high-current terminals need explicit ratings. Example only: 1 milliohm produces 25 mV and 0.625 W at 25 A; at 40 A it dissipates 1.6 W. Account for tolerance, thermal margin and fault pulse energy. Do not assume any breakout carries main-bus current. Draft measures discharge-side loads; BMS provides total charge accounting until charge routing through the shunt is designed. [TI INA228](https://www.ti.com/product/INA228) |
| 4, 8, 12, 13, 19, 20: fuse/switch/wiring/connectors | 25 A main fuse and branch values remain placeholders. Select by wire ampacity, DC interrupt rating, connector rating, motor peaks and fuse curves. Branch input current differs from converter output current. Do not assign JST-XH to high-current power. |
| 5: two NTCs | BMS sensor must match its specified curve. The Pi has no general analog input: use an ADC or ESP32 ADC with a designed divider/filter/calibration for the second sensor. |
| 6, 7: pack assembly/enclosure | Prefer a professionally assembled protected pack. Verify insulation, cell joining, clearances, thermal design and mechanical restraint. An ideal 6-by-3 P42A layout already occupies about 130 x 65 x 70 mm before insulation, wiring and BMS; the proposed 140 x 75 x 80 mm enclosure is unverified. |
| 9, 10: mushroom/contactor | Keep a latching mushroom with verified NC contact blocks. Prefer a normally-open, electrically held contactor that drops out on loss of permit. GX11 is listed as normally open, 150 A-class, not a “30 A latching” contactor. Select exact coil/pickup/dropout behavior across pack voltage or provide a regulated coil supply. [Sensata GX family](https://www.sensata.com/products/gigavac-power-contactors-fuses/gx-contactors-800v/gx-normally-open-contactors) |
| 11: 33 ohm 5 W precharge | Recalculate after total capacitance is known: initial power at 25.2 V is 19.2 W, initial current 0.76 A, time constant 33C, energy 0.5CV². A 5 W marking alone does not establish pulse capability. Interlock precharge with the stop circuit and ensure loads do not prevent completion. |
| 14: D36V50F12 | Listed as 12 V / 4.5 A typical at 36 V input, thermally dependent; it is not a universal 10 A motor supply. Candidate for Kinect after validation; keep motor/arm rail separate. [Pololu 12 V regulator](https://www.pololu.com/product/4095/specs) |
| 15: D36V50F5 | Fixed 5 V, not 5.1 V. Listed typical current 5.5 A at 36 V input and output accuracy 4%; verify voltage drop and thermal behavior. It is not a complete Pi USB-C power supply. [Pololu 5 V regulator](https://www.pololu.com/product/4091) |
| 16: aux 5 V / 3 A | Reasonable provisional rail; total audio/LED/accessory load and surge determine adequacy. Add 3.3 V regulation where needed. |
| 17: 6 x 10 F / 2.7 V caps | Remove from first revision. In series: 16.2 V maximum, 1.67 F effective, so incompatible directly across 6S. A separate regulated hold-up rail needs balancing, charge limiting, power-path management, undervoltage handling and energy sizing. For illustration, 1.67 F from 12 V to 6 V stores only 90 J usable before losses—about 4.5 s at 20 W. |
| 18: LM74700 / P-FET | LM74700 is an external N-MOSFET ideal-diode controller, not a complete OR-ing board or a guaranteed load disconnect. Include the actual MOSFET/protection network and prevent any reverse-blocking stage from defeating required charging/regeneration paths. [TI LM74700](https://www.ti.com/product/LM74700-Q1/part-details/LM74700QDBVRQ1) |
| 21–23: roof solar/MPPT | Retain as optional supplemental energy. GVB-8-Li-25V is a 6S candidate; its 8 A figure is **input**, not 8 A into the battery. Check actual setpoint, panel voltage range, quiescent loss and temperature behavior. At 6 W, 90% efficiency and 25.2 V, output is only about 0.21 A. Add a blocking diode only if the controller topology requires it. [Genasun 25 V model](https://genasun.eu/products/genasun-gvb-8-lithium-25-volt-mppt) |
| 24, 25: dock contacts/detect | Require exact contacts, current-limited source, fuse, reverse-polarity/backfeed protection, sequencing and motion inhibit. Hall/reed detection alone cannot prove correct electrical mating. This is a new robot charge dock, not permission to reuse T12 contacts at 25.2 V. |
| 26: optional beacon | Keep independent. TP4056 plus boost is not automatically a load-sharing UPS; use a suitable protected power path and compatible charge input. Model LoRa link/current separately. |
| 27–29, 32: station PV/MPPT/LFP buffer | 2 x 100 W is 200 Wp total. 8S 50 Ah gives 1.28 kWh nominal. Validate panel cold Voc, operating voltage and current against MPPT limits. Use the station battery manufacturer's LiFePO4 charge profile, BMS and temperature limits. [Victron manual](https://www.victronenergy.com/upload/documents/Manual_SmartSolar_MPPT_75-10_up_to_100-20/29694-MPPT_solar_charger_manual-pdf-en.pdf) |
| 30: station-to-robot converter | Require a verified **true buck-boost lithium charger** with 25.2 V CV, 4 A CC, termination, reverse blocking and temperature control. “RD6018 class” is not a sufficient specification; do not approve a generic bench CC/CV supply as an unattended charger. |
| 31: mains charger | Dedicated 6S conventional Li-ion charger, 25.2 V / 4 A candidate. Use source selection or managed combining, not raw parallel outputs. Limit combined charge current if solar is simultaneously enabled. |

## Runtime: retain the target, measure the premise

The supplied arithmetic is consistent: 28 W / 0.87 = 32.18 W at the pack; six hours needs 193.1 Wh. This does not establish that this robot averages 28 W. Motors, arm holding torque, Kinect, Pi/SSD, audio, fans, contactor coil, BMS and converter idle draw all count. Model stationary sensing, driving, manipulation and sleep separately; size wiring/converters for peaks rather than the average.

Using the user's **266 Wh planning budget**, 80% usable energy and 87% conversion efficiency:

| Average at loads | Illustrative runtime |
|---|---:|
| 28 W | 6.61 h |
| 40 W | 4.63 h |
| 60 W | 3.09 h |
| 80 W | 2.31 h |

Thus six hours requires average load below about **30.9 W** under these assumptions. The 80% factor is a planning allowance, not a measured pack result. Rooftop solar is excluded; a 6 W panel gives at most 36 Wh over six hours at rated illumination before losses. Indoor output will not resemble that nameplate case. A 25.2 V / 4 A charger outputs up to 100.8 W; charging time includes the taper and any simultaneous robot load.

## Before a PCB layout

Confirm the T12 model label, original battery connector/sense lines, motor control access and LiDAR protocol; Kinect/adapter label; Pi model and peripherals; exact arm/gripper/pan-tilt actuators and stall currents; IMU/ToF modules; audio/display/fan loads. Determine whether the base retains its original battery during prototype work.

Then replace each abstract module terminal with the actual connector/schematic symbol and selected protection circuit; select fuses, shunt, cables and regulator ratings from measured load profiles. Validate emergency stop including the OEM base, charging interlocks, voltage transients, thermal behavior and USB backfeed. Only then assign footprints and lay out the distribution PCB. High-current off-board modules can remain on bolted wiring rather than forcing every power path through a small PCB.

## Files and verification

- `underbot_power.kicad_sch`: power distribution architecture.
- `underbot_connections.kicad_sch`: compute, control and sensor interfaces.
- `underbot_charging.kicad_sch`: station, roof solar and charging boundaries.
- `overall.svg`: readable whole-system overview.
- `build_draft.py`: regenerates the architecture schematic files.
- `exports/`: KiCad-rendered SVG/PDF drawings.

KiCad parsing/export verifies file readability only. The abstract passive module pins are not an electrical-rule validation of the final circuit. No fabrication files are generated.
