# UnderBot revision 0.5 - selected components

Start with [the linked purchase list](BUY_LIST.html) or [the Markdown list](BUY_LIST.md). [shopping-list.csv](shopping-list.csv) opens in Excel. Open `UnderBot.kicad_pro` for the editable project. The PDF has ten pages: index plus nine circuit sheets. Sheet 09 shows the selected power modules.

## Decisions made

The first prototype uses short, light-duty arms: nominal 70 mm upper link, 70 mm forearm, and up to 50 mm from wrist axis to payload centre. Target payload is 250 g per arm at 190 mm reach. This is a deliberately selected engineering target, not a proven payload rating or the old illustration's 1 kg claim. Use a bearing-supported shoulder and a camera cradle with its tilt axis near the camera centre of mass. No load should be carried solely by an unsupported servo output shaft.

Two FEETECH FT5335M units serve the shoulders. Eight FT5121M units serve the two elbows, two wrists, two grippers and camera pan/tilt. Use the supplied horns: the two servo models have different splines. Two sample servos are the first purchase; remaining quantities follow qualification. The robot will report commanded PWM positions, not measured joint positions. If actual joint feedback is essential, this PWM baseline must change to smart servos or external encoders before buying a complete set.

The FT5121M datasheet gives 17.5 kgf-cm stall torque at 6 V and the FT5335M datasheet gives 35 kgf-cm. These are not continuous ratings. The chosen arm layout estimates about 8.22 kgf-cm at the shoulder and 4.51 kgf-cm at the elbow under the following assumed fully horizontal load: 250 g payload at 190/120 mm, two 40 g links with centres at 35 and 105 mm from the shoulder, elbow servo 60 g at 70 mm, wrist servo 60 g at 140 mm, and gripper assembly 100 g at 165 mm. For the elbow, include the distal link at 35 mm, wrist servo at 70 mm and gripper at 95 mm. These assumptions must become mechanical mass limits; acceleration, friction and heating are not covered. Do not claim a continuous lifting margin from a stall-torque ratio.

Sources: [FT5335M manufacturer specification](https://www.pololu.com/file/0J1434/FT5335M-specs.pdf), [FT5121M manufacturer specification](https://www.pololu.com/file/0J1410/FT5121M-specs.pdf). The supplier warns the larger servo can produce current bursts above 9 A at 7.4 V despite lower values in the older manufacturer sheet; this discrepancy requires sample measurements rather than using the lower number as a guaranteed bound. [Supplier warning](https://www.pololu.com/product/3429).

## Selected power paths

| Path | Selected parts | Output / allocation |
|---|---|---|
| Battery -> Pi | Pololu D36V50F12 #4095 -> 52Pi EP-0225 -> supplied USB-C cable | 12 V intermediate, then Pi-compatible PD output; allocate 30 W upstream of PD board |
| Battery -> Kinect adapter | A second D36V50F12 #4095 | 12 V; 18 W initial load allowance, confirm actual adapter and test |
| Battery -> auxiliaries | Pololu D36V28F5 #3782 | 5 V; initial continuous allocation 2 A |
| Aux -> sensor logic | Pololu D24V5F3 #2842 | 3.3 V; initial allocation 0.2 A |
| Stopped actuator bus -> left group | Hobbywing UBEC 25A HV #30606000 | Set 6.0 V; left arm + camera pan |
| Stopped actuator bus -> right group | Second identical Hobbywing UBEC 25A HV #30606000 | Set 6.0 V; right arm + camera tilt |

The Hobbywing output positives remain separate. Their grounds share the system reference. Both backup input leads remain individually insulated and disconnected: a backup battery can keep actuators energized after the main stop opens. Multiple output connectors must distribute load within their individual contact ratings; the 25 A module rating does not make one servo plug a 25 A connector. No custom high-current harness has yet been released.

For planning, allocate 20 A transient and 8 A continuous output to each BEC group. These are design budgets, not measured servo demand or guaranteed thermal capability. At 6 V, two groups total 240 W transient; adding 30 W Pi, 18 W Kinect and 10 W aux gives 298 W. At 18 V battery and assumed 85% overall efficiency this is approximately 19.5 A input, before safety-controller consumption and additional margin. The 25 A main fuse is still a coordination candidate, not validated protection. F901/F902 and per-servo fuse ratings remain unset pending wire/connector choice and measured surge duration.

EP-0225 accepts only 9-24 V at its DC input: never connect the fully charged 25.2 V pack directly. The 12 V preregulator is part of the selected solution, not optional. The official store and wiki disagree on DC plug dimensions; the current wiki specifies 3.5/1.35 mm, centre positive. Require a matching pigtail from the board supplier and confirm the received revision; do not purchase a cable from the conflicting store measurement. Use only one EP-0225 input. Its output is represented by a complete cable-interface symbol, not a physical single-pin USB connector.

Sources: [Pololu 12 V regulator](https://www.pololu.com/product/4095), [aux regulator](https://www.pololu.com/product/3782), [logic regulator](https://www.pololu.com/product/2842), [52Pi wiki](https://wiki-md.52pi.com/docs/EP-0225), [Hobbywing manual](https://www.hobbywing.com/en/uploads/file/20221108/12f5024346c4952abc96da8c0f2ffc32.pdf).

## Battery, charging and stopping

Keep the 6S3P 21700 architecture, professionally assembled using one cell model. [PACK_REQUEST.md](PACK_REQUEST.md) specifies the pack and matched charger quotation. The selected charger family is Mascot 2440 LI in its 6-cell 25.2 V version, with matching connectors and temperature provisions approved by the pack builder. This replaces the earlier generic 4 A charger assumption; purchase the actual 6-cell variant, not a different voltage or LiFePO4 version. The supplier must state the delivered current and limits on the quote.

Selected stop operator: Schneider XB5AS8444, the 2NC version. This is not the entire emergency-stop circuit. A qualified assembly supplier must provide the stop/reset/watchdog/contactor and coordinated protection assembly described in the request. The independently powered T12 needs a separate verified stop path; stopping the new actuator pack does not stop its wheels. No bypass of the missing stop assembly is authorized by this drawing.

INA228 remains a custom carrier design on sheet 02. Do not order a random breakout and pass main-bus current through it. The finished external-shunt assembly is part of the distribution design, not an interchangeable two-wire accessory. Sensor power sequencing, PCA9685 OE default disable and ADC calibration also remain commissioning work.

## Ordering sequence and honest scope

1. Buy the electronics and the two servo samples listed in the Buy now column; reuse existing Pi, Kinect and T12. Borrow a current-limited lab supply and measurement equipment for first tests if the team already has them.
2. Request the pack/charger and protected stop/distribution assembly quotes using the attached specification. No messages were sent to suppliers.
3. Qualify one supported joint and one balanced camera axis, measure surge/holding current and heating, then order the remaining selected servo and BEC quantities. Confirm base stability and mounting before installing both arms.
4. Finalize harness and protective ratings, then define the small carrier PCB boundary. Solar/dock automation and roof charging are postponed, not silently included in this design.

The ten servo unit-price arithmetic is about US$805 before taxes/shipping or quantity discounts at the supplier pages checked on 2 October 2026; it is not a delivered quote. Stock is not guaranteed, and Pololu regulator pages may show backorders. No budget answer has arrived, so no complete robot cost ceiling is claimed.

`provisional-bom.csv` is the schematic symbol list. It is **not** the shopping list: `shopping-list.csv` controls ordering. Some schematic parts are whole external modules or unresolved engineered assemblies. Previous revisions are retained for history and are superseded by this power architecture.

## Validation

KiCad ERC and exported-netlist checks cover wiring only. Additional checks verify Pi preregulation, separate BEC outputs, correct group assignments and disconnected backup inputs. External module internals, USB-PD behaviour, thermal performance, assembly orientation, mechanics and stop performance require physical testing. The simplified module symbols use labelled functional interfaces, not bare-chip footprints. No hardware test or PCB fabrication release is claimed.

Generator: `../build_schematic_r05.py`; validator: `../check_schematic_r05.py`; purchase list generator: `../build_procurement.py`. Reconcile manual KiCad edits before regenerating.
