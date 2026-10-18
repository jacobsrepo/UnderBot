# Request for quotation - battery and protected power assembly

Prepared for the UnderBot team, 2 October 2026. This is a specification to send to an assembly supplier, not a claim that any vendor has accepted it. No supplier has been contacted.

## Pack and charger

Please quote one professionally assembled conventional lithium-ion pack using 18 genuine Molicel P42A cells in 6S3P, with balancing BMS, enclosure/insulation, temperature monitoring, wiring and connectors. Nominal arithmetic is 21.6 V / 12.6 Ah with typical 4.2 Ah cells; full charge is 25.2 V. Provide rated minimum capacity, energy, dimensions and mass rather than relying on that typical arithmetic. The original 266 Wh figure is a planning target, not a guaranteed delivered energy rating.

Requirements:

- Protected pack output supporting a requested 30 A continuous discharge rating, subject to the supplier's thermal design and written acceptance. Present robot transient budget is approximately 20 A at 18 V; provide overload duration and protection behaviour.
- BMS overcharge, overdischarge, overcurrent, short-circuit and charge/discharge temperature protections appropriate to this exact cell model. Reject charge below the approved minimum temperature; do not rely on the Pi for pack safety.
- Common protected charge/discharge return preferred, matching schematic revision 0.5. If the supplier uses separate charge/discharge ports, supply pinout and revise the schematic before assembly. Never expose raw cell negative as the user load return.
- A matched Mascot 2440 LI 6-cell 25.2 V charger, or a explicitly documented compatible alternative approved by the pack builder. State exact order code, charge current, tolerance, termination, reverse protection and temperature strategy. The charger temperature option does not replace BMS protection. Include EU mains lead if delivery is in Germany/EU.
- Touch-protected, keyed discharge and charging connections with current-rated mating harnesses; different connector arrangements or mechanical keying to prevent misconnection. Provide a polarity/mating-view drawing. Do not finalize connector by generic name alone.
- Main DC fuse near the pack and service disconnect, coordinated against wire, connector, BMS and fault-current limits. 25 A is a proposed system value; supplier to confirm or revise with fuse curve and DC interrupt rating.
- State any telemetry interface, protocol and logic voltage. Telemetry is useful but must not be required to keep the pack protected.
- Supply applicable transport/test documentation for the delivered pack, approved mounting orientation/clearances, maximum ambient temperature and charging instructions.

Pack is for the new electronics/arms. It will not replace or parallel the Xiaomi T12's original battery in this phase. No raw 6S feed to the T12 dock. Robot load switch is OFF during manual charging; automatic docking and simultaneous chargers are not part of this request.

## Protected distribution and stop assembly

Please quote the engineering and assembly of a protected 18-25.2 V DC input distribution unit, separate always-on electronics and stopped actuator branches, for these loads:

- Electronics: two Pololu D36V50F12 modules, one D36V28F5, with a D24V5F3 downstream of 5 V. Pi branch includes EP-0225 after a 12 V regulator.
- Actuators: two Hobbywing UBEC 25A HV units at 6.0 V. Inputs have separate fuses after the hardware stop. No backup battery connected. Output positives remain independent, with five servo loads per BEC. Validate per-output connector currents and high-current harness distribution.
- Stop operator: Schneider XB5AS8444 (2NC). Provide monitored hardwired stop and manual restart, power-on inhibit, loss-of-heartbeat response, correctly rated normally-open DC contactor(s), feedback and coil suppression. Loss of control power must not leave motion enabled. Specify achieved behaviour and validation, not an unsupported safety certification.
- Resolve input capacitance/inrush and any precharge so no bypass continues energizing actuators after a stop. Specify stop time including converter energy storage and backfeed paths.
- Provide a separately verified stop interface for the independently powered OEM T12 base. Until its interfaces are known, declare base motion commissioning blocked; the new pack contactor cannot stop that base by itself.
- Include an external Kelvin shunt/current-monitor implementation or a documented alternative; the current schematic's INA228 and 1 mOhm shunt are engineering targets. Do not run main current through a small sensor breakout.
- Coordinate branch fuses and per-servo fuses with actual wire, connector and transient measurements. Supply final wire gauges, insulation ratings, connector part numbers and wiring schedule.

Gravity loads can fall when power is removed. Arm mechanical restraint/counterbalance and safe test fixtures are a separate required work item. The assembly supplier must flag this interface; contactor opening alone does not make the robot mechanically safe.

The team can source the selected electronics independently, but should not order an arbitrary latching contactor, BMS, fuse block or connector kit as a substitute for this coordinated assembly.
