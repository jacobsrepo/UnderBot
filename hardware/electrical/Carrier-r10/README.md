# UnderBot converter carrier r10 — routed review

The carrier circuit and copper routing are complete for the connections shown.
KiCad 10.0.6 checks on 2026-10-03 report zero ERC violations, zero DRC violations,
zero unconnected items and zero schematic parity issues. Reports: erc.json and
drc.json. These checks validate connectivity and the configured geometric rules;
they do not establish safe current ratings, hardware compatibility or a complete
robot emergency-stop system. Custom interface symbols have passive pins, so ERC
cannot detect incorrect supply voltages or incompatible interfaces.

## Files and scope

- UnderBot.kicad_pro: open the project in KiCad.
- UnderBot.kicad_sch / Carrier.kicad_sch: linked carrier schematic.
- UnderBot.kicad_pcb: 200 × 180 mm, two copper layers, 43 track segments,
  front/back ground pours, no vias. Routes use plated through-hole connections.
- Carrier-circuit.pdf, routing.svg and index.html: team review views.
- connector-schedule.csv: terminal assignments.
- ../UnderBot-r07/: broader robot architecture; its old converter choices are
  superseded by this revision. This is not a new validated whole-robot schematic.
- ../Carrier-r09/budget-r09.xlsx: existing budget scenarios, not a final quote.

The Pi EP-0225 and Mean Well DDR-60G-12 connect by short harnesses and occupy
reserved mounting areas. The Pololu D24V50F5 daughterboard has a soldered-pin
footprint. The Pi module powers the Pi directly by USB-C. The DDR output returns
through J5 and leaves through J6. T12 retains its independent OEM battery/dock.
Do not connect its battery positive to the NOCO distribution input.

## Before ordering or energizing

1. Finalize fuse values and the upstream fuse/protection circuit against load
   inrush, wire ratings and available fault current. F1–F4 are still explicitly
   marked HOLD. J1 expects externally protected nominal 12 V from the NOCO
   accessory output, never the jump clamps.
2. Validate trace temperature and voltage drop at final continuous/stall loads
   and chosen copper thickness. Widths are 4 mm trunk, 3 mm branches and 1.2 mm
   daughterboard escapes. Width alone is not an ampacity guarantee. Ground uses
   solid pad connections; assembly requires adequate soldering heat.
3. Measure Pi-module mounting holes and the selected DIN rail/backing fixture.
   No guessed holes were drilled. Check enclosure fit, module underside
   clearance, cable access and Mean Well vertical-mount cooling requirements.
4. Complete the external hardwired manual-reset stop circuit connected across
   J2. Both J2 terminals are positive, not positive/ground. It switches arm and
   auxiliary power; the T12 drive needs a separately validated stop interface.
   This board alone is not a complete emergency-stop system.
5. Verify the actual Adeept controller revision, USB VBUS blocking/backfeed,
   Kinect adapter polarity/startup current and NOCO output behavior under load.

No fabrication release, Gerber package, order or purchase has been made.
Earlier revisions are preserved. Rebuild with ../route_carrier_r10.py using
KiCad's bundled Python; it deliberately regenerates the routed review files.
