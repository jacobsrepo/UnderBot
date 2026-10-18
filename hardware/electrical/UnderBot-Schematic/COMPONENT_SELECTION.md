# Component recommendations - 2 October 2026

These are prototype recommendations, not an order for a complete robot. The schematic remains a review draft. No arm dimensions, masses or final joint count have been supplied.

## Sensors selected for this draft

Use two **Adafruit ICM-20948 breakouts, product 4554**: one rigidly attached to the body, one to the moving camera bracket. Use their VIN at 3.3 V, GND, SDA and SCL pins. This is a raw motion-sensor choice: orientation estimation, calibration and timestamps must be implemented in software. It is not a drop-in BNO086 fusion replacement. Keep magnetometers away from motor wiring; do not assume compass heading remains accurate beside servos.

Use **Adafruit TCA9548A breakout 2717** for the external bus multiplexer. Set A0, A1 and A2 to 3.3 V, giving address 0x77. Select one channel at a time, initially at 100 kHz; validate rise time and cable length on the actual harness. Each selected IMU board includes SDA/SCL pull-ups. Resolve upstream pull-ups R301/R302 after accounting for all fitted boards.

| Schematic connection | Physical breakout pin label |
|---|---|
| J302 pin 1 / pin 2 | Mux VIN / GND |
| J302 pin 3 / pin 4 | Mux SDA / SCL |
| J305 pin 1 / pin 2 | Mux SD0 / SC0 |
| J305 pin 3 / pin 4 | Mux SD1 / SC1 |
| J303 pins 1, 2, 3, 4 | Body IMU VIN, GND, SDA, SCL |
| J304 pins 1, 2, 3, 4 | Camera IMU VIN, GND, SDA, SCL |
| J408 pin 1 / pin 2 | Mux SD2 / SC2, if PWM board fitted |

These J pin numbers belong to our harness, NOT to a STEMMA/Qwiic cable. Use board silkscreen labels when making adapters. Initial firmware polls the IMUs; their interrupt outputs remain unused. Leave their address straps at the board default, since the two channels are selected separately.

Sources: [IMU pinout](https://learn.adafruit.com/adafruit-tdk-invensense-icm-20948-9-dof-imu/pinouts), [IMU product](https://www.adafruit.com/product/4554), [mux pinout](https://learn.adafruit.com/adafruit-tca9548a-1-to-8-i2c-multiplexer-breakout/pinouts).

## PWM controller address correction

For a PWM prototype, use an **Adafruit PCA9685 16-channel servo breakout**, with A0 bridged to select **0x41**. Connect J407 pins 1..5 to VCC, GND, SDA, SCL, OE respectively. INA228 remains at 0x40. A downstream mux does not isolate a selected device from a same-address upstream device. The earlier draft note suggesting channel separation alone fixed this was incorrect and has been replaced.

The mux uses 0x77 to avoid the PCA9685's default ALLCALL address 0x70. Do not use 0x70 as the mux address in this configuration. Configure firmware addresses explicitly. OE startup bias and hardware stop remain unresolved: do not energize actuators yet.

Use the PWM board for signals only. Servo positives and high-current returns go to a separate rated distribution assembly; do not route all servo current through its small terminal block or headers. Keep its V+ unconnected in this arrangement, with a common signal-reference ground. Verify the chosen board revision and signal voltage before wiring.

Sources: [Adafruit controller addressing](https://learn.adafruit.com/16-channel-pwm-servo-driver?view=all), [NXP PCA9685 datasheet, ALLCALL](https://www.nxp.com/docs/en/data-sheet/PCA9685.pdf).

## Servo shortlist and mechanical limits

| Use | Candidate | Decision |
|---|---|---|
| Shoulder/elbow bench prototype | FEETECH FT5335M | PWM candidate, 6-7.4 V; large and heavy. Size each joint before ordering a set. |
| Gripper / balanced camera pan-tilt prototype | FEETECH FT5121M | PWM candidate, 6-7.4 V. Check linkage force, bracket bearings and camera centre of mass. |
| Arms requiring position/current feedback | ROBOTIS XM430-W350-T | Alternative smart-servo architecture; use a suitable TTL half-duplex controller, not PCA9685. Requires a different actuator rail/interface revision. |

The FEETECH manufacturer lists FT5121M peak stall torque as 17.5 kgf-cm at 6 V and 20.5 kgf-cm at 7.4 V; stall current is 1.5/1.8 A respectively. These are not continuous operating ratings. Begin with a current-limited bench supply and conservative travel limits.

Pololu warns FT5335M can draw bursts above 9 A at 7.4 V. Consequently the old assumed 20 A servo supply is not validated for several of these actuators. Converter ratings, per-branch protection and battery peak current must be recalculated for the selected joint count. Neither model connects directly to 12 V or the 6S pack.

Example sizing calculation, NOT an assumed robot dimension: a 0.5 kg object held 0.20 m from a shoulder produces 0.981 N m (10 kgf-cm) before arm, gripper and acceleration loads. Add each moving mass times its lever arm, then check duty cycle, dynamic loads and tested thermal limits. Do not pick a servo by matching this static load to its advertised stall torque. Support the Kinect in a bearing-supported bracket, with its tilt axis close to its centre of mass; a small webcam bracket is not a basis for approval.

Sources: [FT5335M manufacturer specification](https://www.pololu.com/file/0J1434/FT5335M-specs.pdf), [FT5335M current warning](https://www.pololu.com/product/3429), [FT5121M manufacturer specification](https://www.pololu.com/file/0J1410/FT5121M-specs.pdf), [ROBOTIS XM430-W350 manual](https://emanual.robotis.com/docs/en/dxl/x/xm430-w350/).

## Power and completion implications

Keep SERVO_POWER_TBD as drawn until the actuator architecture and current demand are settled. For the PWM shortlist, a regulated rail within 6-7.4 V is required; choose a target with tolerance/transient margin. The 6S battery mostly feeds step-down converters. It does not require a buck-boost for every load. Charging from variable solar or a station battery is a separate conversion problem.

The 6S3P battery remains the planning baseline, but the old 28 W average / six-hour runtime is unverified with Kinect, added electronics and arm duty cycles. The original T12 battery stays independent in this revision. A stopped arm may fall when power is removed; mechanical support/braking and the hardware stop design must be resolved before operation.

Next engineering inputs are arm reach, link/gripper masses, payload and joint count. Next electrical work is final converter/protection selection, ESP32 GPIO allocation, power sequencing, hardware stop and a defined PCB boundary. Existing ERC/connectivity results do not validate any of these external systems.
