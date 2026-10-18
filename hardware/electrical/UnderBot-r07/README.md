# UnderBot r07 — NOCO + OEM T12

User-approved sources: existing NOCO GB70 accessory output for added robot systems; original T12 battery and dock for OEM base. New 6S pack/BMS/charger removed. One Adeept ADA031 kit is the current baseline; second optional after testing. Kinect v2 is retained. No purchases made.

## Deliverables
- overall.svg: one-page presentation drawing.
- UnderBot.kicad_pro / UnderBot.kicad_sch: fresh four-sheet integration draft plus index. Main/branch fuse topology, module port interfaces, Pi/sensor nets and independent OEM base documented.
- parts.xlsx / parts.csv: original 11 budget columns, current candidates, notes and purchase holds. Hardware funding 564.69 EUR; reserve 35.31 EUR; total 600 EUR. Not a complete quoted shopping basket.
- connector-schedule.csv: proposed harness pin assignments, NOT OEM connector numbering.

## Design holds
1. Adeept official V4 archive includes drive-board documentation specifying VIN6-24V and an arm-board schematic with a GS2678 onboard5V regulator. USB VBUS is shown on the same5V net. The archive filename says V3.0 but schematic title says V2.0: verify purchased board revision before feeding nominal12V to VIN. Prevent USB backfeeding with a qualified data-preserving VBUS-blocking interface; charge-only cables will not work. No separate arm buck is needed for the documented controller. Arm firmware, calibration, USB VBUS backfeed and torque-loss stop behaviour require tests.
2. NOCO output range/transient/low-load shutdown and usable energy. Approved accessory cable only. Charge separately; no charge connector on PCB.
3. Kinect v2 matching adapter voltage/current/polarity and Pi USB3 driver/bandwidth. Dedicated12V conditioning only after deciding whether direct supply is adequate; buck-only regulation cannot hold12V below its dropout input.
4. Pi EP-0225 accepts9–24V, supplies5.15V/5A PD. Use DC input and supplied USB-C output cable. Store and wiki give inconsistent barrel dimensions, so do not order an assumed mating plug.
5. T12 OEM drive/LiDAR access and independent hardwired stop. No guessed GPIO/UART wiring to OEM board. Electrical control interface, payload and stability must be qualified.
6. Auxiliary converter, sensor mux/address handling, I2S/PWM assignments and return paths. Current signal sheet is intentionally incomplete for these interfaces.
7. Fuse/relay/connector SKUs, anti-reversal/transient protection, PCB footprints, trace widths, fault/thermal review. No PCB layout or Gerbers released. E-stop interfaces are requirements blocks, not implemented safety circuits.

## Scope of validation
KiCad parsing/export checks verify file readability. Passive module port symbols do not validate converter pinouts, safety behaviour or hardware suitability. An ERC pass must not be called a fabrication release. Prior r05/r06 parts choices are historical and superseded.

## Sources
- Adeept official tutorial/revision archive: https://www.adeept.com/learn/detail-64.html
- Pi power module store: https://52pi.com/products/52pi-pd-power-extension-adapter-board-for-raspberry-pi-5
- Pi module wiki: https://wiki.52pi.com/index.php?title=EP-0225
- NOCO accessory output: https://no.co/gb70/specs
- T12 manual: https://user-guide2024.cnbj1.mi-fds.com/user-guide2024/Spain/Robot%20Vacuum/Xiaomi%20Robot%20Vacuum%20T12%20User%20Manual.pdf

The actual T12 purchase status has not been newly confirmed: original table had no X, so its EUR50 acquisition allowance remains. If already owned, that money returns to contingency. Existing NOCO charging/accessory equipment must be checked before removing related allowances.
