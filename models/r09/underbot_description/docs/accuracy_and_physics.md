# R08 dimension and physics register

The user specified 200 × 200 mm floors/frame and accepted a 204 × 204 mm covered body, with bare Kinect electronics inside. This replaces the previous 300 × 240 mm tower and full sensor case. Component reservations describe the proposed assembly; they do not establish the dimensions of an unmeasured teardown.

| Item | R08 nominal geometry | Evidence/status |
|---|---|---|
| WR141E envelope |558 L × 404 W × 205 H mm|Published envelope; shell curves/details simplified|
| Tower frame/floor blanks |200 × 200 mm|User requirement|
| Clear post opening |160 × 160 mm|Derived from 20 mm profiles|
| Posts |4 × 20 × 20 × 500 mm, Z205..705|User stock; mounting datum proposed|
| Rails |16 × 160 mm, cut from original 200 mm stock|Derived from 200 mm outside frame|
| Floor blanks |200 × 200 × 3 mm, four20 × 20 mm corner reliefs|User footprint; thickness/material proposed|
| Floor net area |0.0384 m² per plate|200 mm square minus four corner reliefs|
| Ring bottoms |Z205,480,555,685 mm|Reflowed for upright battery|
| Shelf tops |Z228,503,578,708 mm|Ring bottom+20 mm rail+3 mm plate|
| Covers |2 mm, front/sides matte-black plastic; rear clear|External flat sheets; covered envelope 204 × 204 mm|
| Front/back panel planes |X31 /−171 mm;200 mm panel width|Outside the 200 mm frame; sheet inner faces X30 /−170 mm|
| Side panel planes |Y±101 mm;200 mm panel depth|Outside the 200 mm frame; sheet inner faces Y±100 mm|
| Arm roots |X−70,Y±108,Z545 mm|Proposed external metal carriers|
| GB70 body upright |69 D × 99 W × 222 H mm, bottomZ232|Manufacturer body drawing rotated|
| GB70 installation reservation |70 D × 152 W × 222 H mm|Published overall envelope rotated; 4 mm lateral gaps inside160 mm clear|
| GB70 upper envelope |Z454 mm|26 mm below second ring bottom|
| Camera link datum |(−5,0,635) mm|Provisional internal mounting datum|
| Bare camera reservation |70 D × 156 W × 56 H mm, local offset(−1,0,−3.5) mm|Unmeasured packaging assumption; **not a Kinect PCB dimension**|
| Camera PCB / heat-spreader / carrier visuals |150 W × 45 D × 3;100 W × 45 D × 20;154 W × 24 D × 25 mm|Illustrative components, not teardown CAD|
| Optical aperture |156 W × 59.5 H mm, Z603..662.5|Open, without plastic over optics|
| Optical frame offset |(34,69.25,6.5) mm from camera link|Uncalibrated; correct ROS rotation basis|
| Camera tray |156 W × 80 D × 3 mm, topZ601.5|Proposed bracket, with10 mm PCB standoffs|
| Drive wheels |R92.5 × 50 mm, centres(−180,±177,92.5)|Unmeasured proxy,354 mm track|
| Passive caster |Swivel(215,0,110); roller local(−20,0,−70);R40 × 40 mm|Unmeasured proxy|
| Arm lengths |105/90/45/25/50 mm upper/fore/wrist/hand/finger|Budget-kit approximation|
| LiDAR |Ø70 × 45 mm, Z733..778|Unspecified model; placeholder|

Floor corner reliefs clear the vertical posts; three box colliders reproduce each notched plate. Plates have real rail-top support. The 200 mm figure describes the frame and floor bounds. Covers are external, so the covered body is 204 × 204 mm. Floor edges meet the inner cover faces without penetration. Arm carriers, hinges and fastener heads extend locally beyond this body. Cover fasteners, door hinges and attachment details are illustrative; mounting holes and cable routes still need fabrication measurements.

The GB70 tray is156 mm wide and supports the upright body. The second level contains separate power I/O, converter and wiring reservations. The wiring block sits atX−40 mm above the converter and beside the power I/O, without their former overlap. Compute standoffs reach the board; cooler fins remain below the camera PCB. Camera hangers run behind the components between tray and roof.

## Bare Kinect status

The 249 mm case has been removed from both visual and collision geometry and is no longer a fit requirement. The proposed bare assembly uses separate board, thermal and optical shapes; these are explicitly provisional. Case removal alone does not measure the PCB, heat sink, cable bends or actual lens locations. The retained 0.970 kg allocation is conservative bookkeeping from the previous assembly, **not a measured bare-electronics mass**. Replace the packaging geometry and mass after arranging/weighing the actual parts. The housing change does not generate calibrated RGB/depth observations or establish thermal/electrical performance.

The optical basis remains X right,Y down,Z forward, with RPY(−π/2,0,−π/2), looking along robot+X. Its position is a provisional depth-lens datum. RGB/depth lens lateral separation retains the previous model's 138.5 mm proposal; it is not a newly verified Kinect calibration. Teardown references establish internal components, not the dimensions used here: [iFixit Xbox One Kinect teardown](https://www.ifixit.com/Teardown/Xbox+One+Kinect+Teardown/19725).

## Joint and mass conventions

Body coordinates are X forward,Y left,Z up. URDF origins apply Rz(yaw) Ry(pitch) Rx(roll) before motion around a local joint axis. The roots are proper rotations(0,−π/2,∓π/2). Left/right base and wrist-roll axis signs are mirrored, with finger names cross-mapped under bilateral reflection. Both rear drive-wheel axes are+Y. Caster swivel is+Z and roll is+Y, without motors.

Per-arm folded origin pitches remain shoulder−150°, elbow+60°, wrist−60°. Conservative command intervals are base±45°, shoulder/elbow±20°, wrist pitch±30°, wrist roll±90°, and gripper0..0.6 rad. Each follower has an opposite axis and mimics its leader with multiplier1,offset0. These are proposed collision-limited ranges, not measured servo hard stops. Simultaneous configurations are not exhaustively collision-checked.

Estimated total mass is19.6010078 kg. Composite inertia rotates component tensors and applies parallel-axis offsets around the COM. Extrusions use assumed linear mass/hollow-section tensors. Mower stock mass is divided into 7.35 kg fixed chassis, two 0.75 kg wheels,0.15 kg fork and0.10 kg roller; the added GB70 is 1.9 kg. The [Worx product specification](https://eu.worx.com/en/robot-mower-landroid-s-robot-mower-for-lawns-up-to-400-m2-wr141e/) lists 9.1 kg with battery, while the older manual lists 8.5 kg machinery weight. Actual retained stock equipment and removed parts must be weighed. Installed COM, material grade and hardware budgets are unmeasured.

Proposed effort caps are 2.5 N·m per drive wheel,1 N·m per arm positioning joint and0.3 N·m per gripper input; speed limits are 4 rad/s wheels and 1 rad/s arms. No hardware torque/payload rating follows from these inputs. The static audit reports gravity torque and the changing caster support triangle. Engine reports record mimic handling, motor caps, contacts and actual achieved motion. The Gazebo wrapper uses estimated controller/friction settings and initially disables self-collision pending application-specific filtering; its ideal drive behavior differs from the torque-capped independent test.

## Sources and remaining measurements

Published references: [Worx dimension guide](https://uk.worx.com/worx-robotic-lawn-mowers-guide/), [WR141E manual](https://cdn2.hubspot.net/hubfs/5237793/User%20Manual/Landroid%20M%202019/User_Manual_WR141E_EN.pdf), [GB70 specifications](https://no.co/gb70/specs), [GB70 body drawing](https://no.co/media/wysiwyg/downloads/brochures/Boost/GB70_Data_Sheet_12.05.2024.pdf), [ROS coordinate conventions](https://www.ros.org/reps/rep-0103.html). The selected budget-arm reference is Tatiy Amazon.de B0B4VKYQ6S; a reliable pivot drawing was not supplied.

Measure the bare camera components/calibration, arm pivots/zeros/limits/effort, wheel/caster contacts, actual plastics, installed masses/COM, bracket mounting holes and cable space. Rebuild and repeat authoring/static/engine checks after changes. Native ROS/RViz2, Gazebo, Isaac Sim/Lab and FreeCAD were unavailable; the package makes no native runtime, fabrication or payload certification claim.
