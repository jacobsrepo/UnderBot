# UnderBot power-distribution PCB r08

**UNROUTED PLACEMENT DRAFT — NOT FOR FABRICATION.** This is the first physical PCB artifact, not a working board. No Gerbers released. All converter modules are external, connected by rated harnesses; this board distributes fused nominal12V. It does not yet mount converters or generate5V/3.3V itself.

## Board and circuit
100 x90 mm outline; two copper layers proposed; four3.2mm mounting holes. Six2-way terminals and four MINI fuse holders. Footprints have assigned nets and schematic references. Ratsnest/unconnected DRC findings are expected because copper routing has deliberately not been finalized before protection/current/connector review. A3 circuit PDF accompanies the PCB.

J1 pin1 = protected input positive; pin2 = ground. NOCO approved accessory cable, external main fuse, disconnect and qualified polarity protection are REQUIRED before J1; this PCB does not implement those yet.

J2 pin1 = positive send to EXTERNAL stop power contact; pin2 = switched positive return. **Neither J2 terminal is ground.** A permanent bridge would defeat the intended stop architecture. The external normally-open contact must have a qualified hardwired manual-reset controller. This circuit does not implement a complete emergency-stop system.

J3 pin1 = fused supply to Pi module, J4 pin1 = fused supply to Kinect conditioner, J5 pin1 = fused supply to Adeept VIN, J6 pin1 = fused supply to auxiliary converter. Pin2 of J3-J6 is ground. Actual auxiliary converter, connector wire sizes and fuse values pending qualification. All auxiliary power (including audio) now stops with arm power, so camera pan/tilt has no live auxiliary bypass. Pi and Kinect remain powered while the external motion contact opens.

T12 remains independent: the board does not stop its wheels. Its separate drive-stop interface must be resolved. Adeept USB VBUS must be blocked without interrupting required data; otherwise Pi USB can bypass arm power interruption.

## Specific component progress
- Six Phoenix1715721 5.08mm screw terminals selected as footprint candidates. Manufacturer nominal current is17.5A under specified conditions; this does NOT rate PCB traces or connected wires.
- Four Keystone3568 MINI fuse holders selected as footprint candidates.
- Littelfuse29732V MINI fuse family selected; exact amperages intentionally not guessed. The linked5A part demonstrates the family, NOT a released fuse choice for all branches.
- Pololu D24V50F5 is a concrete auxiliary5V candidate, specified typical up to5A with thermal limits. Its current USD32.95 listing exceeds the old EUR15 allowance; the shopping budget needs a landed quote before substitution. Do not claim current r07 total includes this price.
- Kinect converter and stop/reset hardware remain open selections.

## Before routing/release
Check mounting envelope and cable exit directions; compare terminal/fuse mechanical drawings; verify input polarity protection; measure NOCO output envelope and interruption behaviour; verify arm revision/backfeed/peaks, Kinect label/startup and pan/tilt load; choose stop power contacts and wire/fuse coordination; then set copper thickness/width/clearance and route. No trace ampacity or total PCB current rating is claimed at placement stage.

Next PCB step is routing once those design inputs are defensible. There are no purchases, fabrication uploads or live hardware changes in this revision.

## Verification result
Schematic exported to PDF; PCB loads and renders;14 footprints with assigned nets and zero routed tracks confirmed. CLI DRC did not finish promptly in either sandboxed or elevated run; both were cancelled. No DRC pass or manufacture readiness is claimed.
