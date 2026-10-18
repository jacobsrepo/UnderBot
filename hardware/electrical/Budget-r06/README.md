> **SUPERSEDED by [r07 NOCO + T12](../UnderBot-r07/index.html).** Do not buy the new6S pack or Waveshare arm from this historical budget.

# UnderBot battery-first budget revision

Open [the revised table](UnderBot-budget-r06.html) or [Excel workbook](UnderBot-budget-r06.xlsx).

**Decision:** Battery operation + ONE complete arm prioritized. Kinect v2 confirmed. Six X-marked entries are retained as already owned. No purchases made.

**Budget status:** €589.75 allocated to phase-1 hardware plus €10.25 reserve = €600. This is a conditional funding plan, NOT a verified complete shopping basket. Battery €150, protection €40 and charger €25 are quotation holds. Do not commit arm funds until essential battery/protection quotes fit.

**Meaning of columns:** Exact original 11 headers retained. Qty describes the quantity on each row, including later items; Phase 1 2027 is NEW money allocated now, not automatic subtotal. X rows cost zero new money. Subtotal is row quantity × unit value; deferred rows do not enter phase-1 total. Owned values come from your screenshot. Blank price means no defensible estimate. N/S = maximum not specified/verified.

**Ratings:** Unless stated otherwise ratings are per unit. PSU/converter output capacity is NOT a measured load maximum. Do not sum regulator capacity, battery power and load power as if separate loads. Sensor typical current was not substituted for an unknown maximum.

**Battery correction:** P42A nominal voltage is 3.6 V and typical capacity 4.2 Ah. 6S3P is therefore 21.6 V nominal, 25.2 V fully charged, 12.6 Ah typical; the original 22.2 V/12 Ah/266 Wh describes a different nominal-cell assumption. Supplier must label the finished pack and usable energy. No six-hour guarantee: 28 W from the old component mix is not an established measurement for this robot.

**What phase 1 delivers:** Target: existing Pi/SSD/colour camera plus one complete arm, powered from a new protected 6S pack; T12 retains its own battery/dock. Simple reused structure. Battery/stop integration and base-control qualification remain engineering work. This is not yet a finished autonomous mobile manipulator.

**What is deferred:** Second arm, Kinect v2 and adapter, both IMUs, extra ToF, Hailo, microphone, active audio and camera pan/tilt, telemetry, solar and custom PCB fabrication. Kinect v2 stays the intended depth camera; it has not been silently replaced by the owned colour camera.

**Base integration:** T12 is not a Roomba. It has its own battery and OEM motor controller. Preserve them initially. Its LiDAR/control interface, added payload, tipping stability and independent hardware stop are unqualified. Do not connect 6S to its battery terminals or 20 V dock. If OEM controls cannot be accessed, replacement electronics need additional budget.

**Power structure:** 6S protected pack → main fuse/disconnect → separate fused Pi 5 V converter and actuator-stop-controlled 12 V arm converter. T12 battery → OEM T12 electronics, with separately engineered drive stop. Common signal references only as required by final interfaces; do not parallel battery positives. Pi USB/Wi-Fi → arm controller. Pi CSI → existing camera. Future Kinect USB3 + dedicated 12 V branch. No new servo PWM board required for RoArm.

**Pi supply decision:** The lower-cost proposed Pololu route uses a rated, fused GPIO 5 V/GND harness, not a USB-C PD adapter. Requires polarity/voltage-drop/thermal qualification, no simultaneous USB-C power, and correct firmware current configuration after validating supply capacity. This is a schematic design hold, not beginner wiring instructions. A packaged Pi-compatible PD supply can replace it when budget permits.

**Arm supply and mounting:** RoArm-M2-S is preassembled and accepts 7–12.6 V. Use 12 V; never 6S directly. The DDR-60G-12 proposal matches the 5 A/60 W supplied adapter capacity; test moving/stall transients and temperature before release. Arm reset can cause motion. Stop design must consider falling loads. Payload/space must be checked on the actual base.

**Quote sensitivity:** Example only: battery quote €200 instead of €150, protection €65 instead of €40, and €20 shipping yields €674.75 including those costs (no extra reserve). That is €74.75 over budget before any deferred sensors. The spreadsheet allocation must not conceal this risk.

**Buying order:** First confirm T12 condition/control access and obtain the pack+charger+protection quotes. Then lock delivered costs and arm mounting. Purchase ONE completed arm if the essential total fits. Qualify converters and wiring before battery operation. No supplier contact or order has been made.

**Earlier schematics:** r05 used individually built servo arms and Kinect v1. Those procurement selections are superseded. Its old shopping list must not be used for this new scope. The KiCad circuit has NOT yet been rewired to these new candidates; this deliverable is the budget/component revision.