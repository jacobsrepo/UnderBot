> **SUPERSEDED ? DO NOT ORDER FROM THIS LIST.** See [budget r06](../Budget-r06/README.md): one completed arm, Kinect v2 and battery-first EUR 600 plan. This historical list describes the prior servo-built design.

# UnderBot selected parts - 2 October 2026

Buy the **Buy now** quantities first. Full-robot quantities are the total eventual quantities, not additional quantities. The two servo samples qualify mechanics and power before duplicating the design. Prices, tax, shipping and stock are not guaranteed. Existing Pi, T12 and Kinect are reused.

| Function | Exact selection | Buy now | Full robot | Status |
|---|---|---:|---:|---|
| Controller | [Espressif ESP32-S3-DevKitC-1-N8R8](https://docs.espressif.com/projects/esp-dev-kits/en/latest/esp32s3/esp32-s3-devkitc-1/user_guide_v1.1.html) | 1 | 1 | BUY if not already owned |
| Body + head IMUs | [Adafruit ICM-20948 breakout #4554](https://www.adafruit.com/product/4554) | 2 | 2 | BUY |
| I2C multiplexer | [Adafruit TCA9548A #2717](https://www.adafruit.com/product/2717) | 1 | 1 | BUY |
| PWM controller | [Adafruit PCA9685 #815](https://www.adafruit.com/product/815) | 1 | 1 | BUY |
| Shoulder servos | [FEETECH FT5335M / Pololu #3429](https://www.pololu.com/product/3429) | 1 | 2 | BUY ONE FOR QUALIFICATION |
| Other eight servos | [FEETECH FT5121M / Pololu #3427](https://www.pololu.com/product/3427) | 1 | 8 | BUY ONE FOR QUALIFICATION |
| Servo DC/DC | [Hobbywing UBEC 25A HV #30606000](https://www.hobbywing.com/index.php/products/ubec-25a-hv95.html) | 1 | 2 | BUY ONE FOR QUALIFICATION |
| Pi preregulator + Kinect supply | [Pololu D36V50F12 #4095](https://www.pololu.com/product/4095) | 2 | 2 | BUY |
| Pi USB-C PD source | [52Pi EP-0225](https://52pi.com/products/52pi-pd-power-extension-adapter-board-for-raspberry-pi-5) | 1 | 1 | BUY |
| Auxiliary 5V supply | [Pololu D36V28F5 #3782](https://www.pololu.com/product/3782) | 1 | 1 | BUY |
| Logic 3.3V supply | [Pololu D24V5F3 #2842](https://www.pololu.com/product/2842) | 1 | 1 | BUY |
| Emergency-stop operator | [Schneider Electric XB5AS8444](https://shop.se.com/pro/us/en/product/emergency-stop-switching-off-harmony-xb5-plastic-red-mushroom-40mm-22mm-trigger-latching-turn-to-release-2nc/) | 1 | 1 | BUY |
| Battery assembly | [Custom 6S3P Molicel P42A, assembled and protected](https://enerpower.de/) | 0 | 1 | REQUEST QUOTE |
| Matched mains charger | [Mascot 2440 LI, 6-cell / 25.2V variant](https://www.mascot.no/products/battery-chargers/2440-li) | 0 | 1 | ORDER THROUGH PACK SUPPLIER |
| Kinect adapter | [Xbox 360 Kinect v1 PC USB + power adapter](https://github.com/OpenKinect/libfreenect) | 0 | 1 | REUSE / VERIFY MODEL |
| Pack disconnect / fuse / shunt | Integrated protected distribution assembly | 0 | 1 | ENGINEERED ASSEMBLY QUOTE |
| Stop/reset/contactor assembly | Hardwired manual-reset actuator stop assembly | 0 | 1 | ENGINEERED ASSEMBLY QUOTE |
| Power monitor | [INA228 carrier plus external Kelvin shunt](https://www.ti.com/product/INA228) | 0 | 1 | PCB STAGE |
| Wiring / connectors / brackets | Harness and mechanical kit | 0 | 1 | AFTER PHYSICAL LAYOUT |
| Solar station / roof solar / supercaps | Later phase | 0 | 0 | DO NOT BUY YET |

## Ordering notes

- **Espressif ESP32-S3-DevKitC-1-N8R8:** Official development board; USB data cable matched to board connector. No generic pinout substitution.
- **Adafruit ICM-20948 breakout #4554:** 3.3V VIN; software fusion; one board per mux channel.
- **Adafruit TCA9548A #2717:** A0/A1/A2 high for address 0x77.
- **Adafruit PCA9685 #815:** Bridge A0 for 0x41; V+ unused. OE startup modification must be resolved before powered servo tests.
- **FEETECH FT5335M / Pololu #3429:** Final assignment CH0 and CH4. 17T horn; use supplied horn. External bearing support required.
- **FEETECH FT5121M / Pololu #3427:** Elbow/wrist/gripper on each side plus head pan/tilt; 25T horn. Buy remaining seven after sample test.
- **Hobbywing UBEC 25A HV #30606000:** Set 6.0V. Second identical unit for other group after test. Do not buy UBEC 10A by mistake. No backup battery.
- **Pololu D36V50F12 #4095:** Two separate 12V converters; one feeds EP-0225, one Kinect adapter. Stock/backorder must be checked.
- **52Pi EP-0225:** Feed regulated 12V only; full 6S is above its 24V input limit. Included USB-C output cable.
- **Pololu D36V28F5 #3782:** Prototype continuous load allocation 2A; verify thermal margin.
- **Pololu D24V5F3 #2842:** Input AUX_5V; initial logic budget 0.2A.
- **Schneider Electric XB5AS8444:** Exact 2NC version. This is an operator only, not a complete stop system; never switch servo current through it.
- **Custom 6S3P Molicel P42A, assembled and protected:** Use PACK_REQUEST.md. Do not buy loose cells, generic BMS or a mismatched stock 24V pack.
- **Mascot 2440 LI, 6-cell / 25.2V variant:** Specify exact Li-ion variant and matched connector; request temperature option and system compatibility. Not 2440 LiFe.
- **Xbox 360 Kinect v1 PC USB + power adapter:** Keep original cable/adapter for first streaming test; no Xbox One adapter. Battery conversion only after checking label and polarity.
- **Integrated protected distribution assembly:** 25A main fuse remains a candidate. Supplier must coordinate fuse, switch, terminals, wire and prospective fault current.
- **Hardwired manual-reset actuator stop assembly:** See PACK_REQUEST.md interface requirements; includes separate verified stop for independently powered T12.
- **INA228 carrier plus external Kelvin shunt:** Do not substitute an INA228 breakout with its small onboard shunt in the whole-pack path. Existing bare-IC sheet is a design, not a finished module.
- **Harness and mechanical kit:** Requires rated servo distribution, strain relief, insulated terminals and connector mating drawings; not a Dupont breadboard build.
- **Later phase:** Complete wired charging, base access and measured power budget first.

The supply architecture and mechanical target are documented in [README.md](README.md). The pack supplier request is [PACK_REQUEST.md](PACK_REQUEST.md). No purchases or supplier messages have been sent.