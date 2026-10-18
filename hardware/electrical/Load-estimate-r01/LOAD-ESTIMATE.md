# UnderBot preliminary load estimate ? 2 October 2026

**Engineering estimate, not a measurement or a released electrical design.** Current reference configuration: Pi 5, SSD, active cooler, Pi camera, Kinect v2 streaming, one Adeept six-servo arm doing light intermittent work, two IMUs, four ToF, Uno, microphone, intermittent audio and camera pan/tilt. Hailo, roof solar and charging loads excluded. Includes deferred sensors to show the intended robot, not just the current funded phase. T12 retains a separate OEM battery; vacuum/brushes/pump assumed OFF.

| Subsystem | Low average W | Central W | High average W | Source |
|---|---:|---:|---:|---|
| Pi 5 board | 6 | 8 | 12 | GB70 |
| USB SSD | 1 | 2 | 4 | GB70 |
| Pi active cooler | 0.2 | 0.5 | 1 | GB70 |
| Pi Camera Module 3 | 1 | 1.5 | 2 | GB70 |
| Kinect v2 + adapter | 10 | 15 | 20 | GB70 |
| One Adeept arm including controller | 2 | 4 | 10 | GB70 |
| Uno + two IMUs + four ToF + small indicator electronics | 0.5 | 1 | 1.5 | GB70 |
| USB microphone | 0.2 | 0.5 | 1 | GB70 |
| Audio amplifiers + speakers | 0 | 1 | 3 | GB70 |
| Two camera pan/tilt servos | 0 | 0.5 | 1 | GB70 |
| T12 base: wheels + LiDAR + OEM electronics | 10 | 15 | 25 | T12 OEM battery |

GB70-powered delivered load: **34 W central**, approximately **21?56 W** across the stated operating allowances. This is an illustrative envelope, not a confidence interval. T12 adds an estimated **15 W at its battery**, rough range 10?25 W, separately. The 49 W sum mixes delivered accessory power with OEM battery power and is not a measured whole-robot battery drain. With 80% GB70 internal-to-load efficiency assumption, central whole-robot battery drain is 34/0.8 + 15 = **57.5 W** across the two batteries.

## GB70 runtime

NOCO specifies 56 Wh stored energy. Assume 80% combined usable-energy factor (pack cutoff, conversion and wiring) to final robot loads: **44.8 Wh**. This factor is an assumption, not a measured GB70 efficiency. Do not deduct another 20% from these runtimes. Age/cold/high load may reduce usable energy further.

| Configuration | Central delivered load W | Estimated GB70 runtime |
|---|---:|---:|
| One arm, Kinect off | 19 | 141 minutes |
| One arm, Kinect streaming | 34 | 79 minutes |
| Two arms, Kinect streaming | 38 | 71 minutes |

At 21?56 W, GB70 runtime spans roughly **48?128 minutes** for the full one-arm configuration. The central 79-minute result is best communicated as **about 1?1.5 hours**, not a precise prediction. Turning Kinect off gives 19 W central and about 2.4 hours. Reducing Pi processing after disabling depth could improve this, but is not credited here. A second arm adds only 4 W in this LIGHT intermittent scenario; heavy/simultaneous manipulation changes that substantially.

T12 runtime cannot be calculated responsibly without its actual battery-label Wh, health and measured driving draw. Its battery can run out before the GB70; system runtime is limited by whichever source runs out first. No six-hour mobility claim follows from the electronics battery estimate.

## Six-hour energy requirement

At 34 W delivered load: 34 ? 6 = **204 Wh delivered**, or **255 Wh nominal battery energy** with the same 80% factor. Thus a roughly 266 Wh-class pack might support six hours of the upper assembly in this central scenario, with very little margin; it is not guaranteed. T12 needs another **90 Wh usable at its battery** at the assumed 15 W average. Combining both demands gives **345 Wh nominal-equivalent** with these mixed conversion assumptions, before additional reserve; not an instruction to parallel batteries or bypass OEM electronics.

## Peaks and supply sizing

The operating ranges above are NOT electrical maxima. Servo start/stall transients, SSD startup, Kinect initialization and loud audio must be characterized separately. No verified AD002 stall-current specification for the purchased revision was established here. For an illustrative test-planning example ONLY, six servos each reaching 1 A at 5 V would be 30 W for one arm; that is an assumed current, not a measured AD002 value or approval to power the arm board at that voltage. Controller input and servo rail must be checked separately. Do not select final fuses, trace widths or converters from 4 W average arm consumption.

NOCO accessory port is specified 12 V / 15 A (180 W nominal output rating), not 2000 A continuous. Actual combined transient response, output regulation and automatic shutdown behaviour remain bench-test items. Use accessory output, not jump-start clamps. NOCO recommends against simultaneous charging/discharging.

## Measurement needed to replace assumptions

1. Measure GB70 accessory-output volts, amps and accumulated Wh with a correctly rated inline DC meter and fused accessory harness. This measurement already includes downstream converter losses.
2. Log Pi + SSD + camera during the actual ROS/vision workload, then Kinect streaming on/off.
3. Measure arm resting supported, holding the intended object at reach, and moving normally. Capture current transients without deliberately damaging/stalling the arm.
4. Run a representative 30?60 minute task cycle, recording average output watts and Wh. Measure full usable GB70 output energy separately; its 56 Wh internal label is not directly the meter's output Wh.
5. Characterize T12 battery drain separately with vacuum, brushes and pump off, including starts, turns, added payload and LiDAR. Do not modify OEM battery wiring without a rated measurement interface.

## Evidence versus assumptions

- **Pi 5 board:** 6?12 W operating allowance; manufacturer reports around 12 W intensive peak, not measured ROS consumption.
- **USB SSD:** Exact SSD/enclosure unknown; engineering allowance.
- **Pi active cooler:** Fan duty and exact label unknown; allowance.
- **Pi Camera Module 3:** Camera streaming allowance, not published maximum.
- **Kinect v2 + adapter:** Provisional active-load assumption, NOT verified Microsoft rating; must measure exact sensor/adapter. Supply capacity is not operating consumption.
- **One Adeept arm including controller:** Light intermittent manipulation allowance; six servos included. 4 W assumes 80% supported/resting at 2 W, 20% moving at 12 W. Holding a load can use much more. Not a stall-current limit.
- **Uno + two IMUs + four ToF + small indicator electronics:** Combined allowance, arm controller excluded here to avoid double count. Includes future sensors so estimate is broader than funded phase 1.
- **USB microphone:** Optional microphone allowance.
- **Audio amplifiers + speakers:** Quiet/intermittent speech electrical average, not 6 W loudspeaker output rating or full-volume maximum.
- **Two camera pan/tilt servos:** Intermittent light Pi-camera motion average; not Kinect mount or stalled servo peak.
- **T12 base: wheels + LiDAR + OEM electronics:** ROUGH driving estimate with suction, brushes and mop pump OFF; not published no-vacuum data. Includes LiDAR once. 45 W manufacturer nameplate is for original vacuum appliance, not this measured load.

Primary references:
- [Raspberry Pi: Pi 5 introduction, approximately 12 W intensive board load](https://www.raspberrypi.com/news/introducing-raspberry-pi-5/)
- [Adeept arm package: six AD002 servos and controller](https://www.adeept.com/adeept-arduino-compatible-diy-5-dof-robotic-arm-kit-for-arduino-uno-r3-steam-robot-arm-kit-with-arduino-and-processing-code_p0118.html)
- [Xiaomi T12 specifications: 14.8 V nominal, 45 W appliance rating](https://www.mi.com/de/product/xiaomi-robot-vacuum-t12/specs/)
- [NOCO GB70: 56 Wh, 12 V / 15 A output](https://no.co/gb70/specs)
- [NOCO user guide: accessory use and charging limitation](https://no.co/media/wysiwyg/downloads/User_Guides/Boost/GB70-User_Guide_03.07.2025A.pdf)

This estimate does not update the old r05 schematic or convert the conditional r06 procurement allocations into a purchase-ready list.
