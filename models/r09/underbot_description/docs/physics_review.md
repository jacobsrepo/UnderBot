# Independent static physics review

The R08 URDF has internally consistent static gravity calculations for the tested no-payload poses. It uses a 200 ×200 mm frame and floor blanks, a 160 ×160 mm clear opening, and external 2 mm covers giving a 204 ×204 mm covered body. This review does not establish the real robot's payload, actuator capacity, dynamic stability or simulator compatibility. Hardware masses, stripped-camera packaging, arm geometry, wheel contacts and actuator ratings still contain explicitly provisional inputs.

The checked URDF SHA-256 is `805ae58b87af3d3030c201def6d7126b09fd0e907e6bebbdabf9e0db6059e3c7`. Re-run the audit after changing the model; the machine-readable report records the exact source hash.

## Results

The URDF inertials sum to **19.6010078 kg**. Its zero-pose whole-robot COM is approximately **(−63.965, 0.041, 298.205) mm** in base coordinates. The audit used gravity of 9.80665 m/s² and no additional object or payload. It evaluated **2,000 simultaneous arm configurations**, comprising the zero pose, 28 targeted limit probes and a deterministic twelve-dimensional Halton sequence. Both arms, including their coupled jaws, varied within the URDF limits.

For each arm configuration, the audit evaluated 720 evenly spaced caster angles over a complete rotation. A derivative bound covers the intervals between those angles. The smallest sampled distance from the projected whole-robot COM to a support-triangle edge was **101.694 mm**. The conservative lower bound across every caster angle, for these sampled arm configurations, was **101.648 mm**. Thus all these configurations had a positive level-ground static margin in the assumed three-contact geometry. This does not prove the margin over every possible arm configuration.

No tested static holding torque exceeded its declared URDF effort limit. The largest positioning-joint requirements were **0.942630 Nm at the left shoulder** and **0.944059 Nm at the right shoulder**, against the provisional 1.0 Nm effort cap. The right shoulder therefore used **94.4%** of that cap without payload, leaving only about **0.056 Nm** of sampled static margin. That is insufficient evidence for any payload rating or dynamic reserve. Real servo continuous torque, gearbox loss and thermal duty need measured or reliable manufacturer data.

The largest ideal coupled-jaw input torque was **0.003566 Nm** against the provisional 0.3 Nm leader effort. This concerns the gravity of the modelled jaws only; it says nothing about gripping force, object retention or the real linkage's mechanical advantage. Wheel holding moments were zero in the stationary level-ground calculation; acceleration, grade and traction demands were excluded.

An independent central-difference check of gravitational potential energy covered 72 input-coordinate evaluations. Its maximum discrepancy from the analytical holding torques was **1.17 × 10⁻⁸ Nm**. This checks the numerical implementation and mimic-coordinate treatment, not the underlying hardware inputs.

The analytical caster-contact and whole-robot COM circles were also compared against separate complete forward-kinematics calculations at 113 caster angles. Their maximum discrepancies were below **3 × 10⁻¹⁷ m**.

## Calculation

The standalone script reads the URDF directly. It does not import the model generator, its parameter register, the geometry manifest or the authoring validator. Every mass and local COM comes from a link's `<inertial>` element. Joint origins, local axes, limits and effort caps come from their URDF joint elements. Wheel radii and local contact centers come from the URDF collision cylinders. Nonzero-mass inertia tensors must be positive definite; fixed sensor frames may have zero mass and inertia.

Forward kinematics applies each fixed joint-origin transform before the joint motion. For a revolute joint, the no-load holding torque is the negative gravity moment of all descendant link masses projected onto the world-space joint axis:

`holding torque = −axis · Σ[(link COM − joint pivot) × mass × gravity]`.

For a mimicked jaw, ideal virtual work gives the leader input requirement as the sum of its own coordinate torque and the follower coordinate torque multiplied by the mimic multiplier. The report retains individual coordinate torques separately. The finite-difference check differentiates `Σ mass × gravity_magnitude × COM_height` with respect to independent inputs, including mimic motion.

The support triangle joins the two rear wheel contact centers and the front caster contact center. As the caster swivels, both its contact and the moving caster masses rotate around the vertical swivel axis. The script accounts for that change in the complete robot COM.

For an edge from a fixed rear contact `R` to the caster contact `C`, its signed margin is the edge-normal projection of `G − R`, where `G` is the horizontal whole-robot COM. Its angular derivative is bounded by `|G′| + |C′| × |G − R| / |C − R|`. Circular-motion bounds supply finite upper and lower values for those terms. Subtracting that derivative bound times half the angular grid spacing from the sampled minimum gives a conservative continuous-angle lower bound. The rear edge has a fixed normal and the corresponding simpler bound.

## Scope

This is a rigid-body, stationary, level-ground calculation using ideal point contacts at tire-contact centers. It excludes payload, motion, slopes, braking, impact, tire compliance, suspension, traction, cable forces, servo friction, linkage losses, battery sag and temperature. Sampled poses are not screened for simultaneous self-collision by this static audit. They do not establish a usable collision-free workspace.

No Gazebo, Isaac Sim, Isaac Lab, RViz, ros2_control, USD importer or hardware test is executed by this script. Other checks in the package have their own separate scope. The full original mower mass is retained as the stock baseline in the current URDF mass budget; removing hardware requires a new installed mass and COM budget.

The inspected geometry places camera hangers behind the represented PCB and connects them to the shelf and roof. Ten-millimetre standoffs support the PCB. The caster fork extends below its axle, and the front grille leaves vertical clearance above the tyre during a full swivel. The compute-board standoffs connect the shelf top to the board underside. The wiring allowance no longer intersects the power-I/O block. Independent fixed-part checks confirm that the external covers meet the 200 mm shelves and camera shelf without penetrating them. These are internally consistent proposed construction details, not measured WR141E internals or verified component mounting designs.

The camera housing has been removed from the model. Its 70 D ×156 W ×56 H mm internal reservation, 150 mm wide PCB, optics arrangement and 138.5 mm nominal RGB-depth spacing are unmeasured packaging proposals. The original **0.970 kg camera mass allocation is retained as a conservative budget**, not a measured stripped-electronics mass. Removing the casing alone does not establish that actual Kinect boards, optics, heat sink, connectors and wiring fit the 160 mm clear opening. That hardware fit and optical calibration remain to be measured; the validator checks only the declared reservation and its geometric consistency.

## Reproduce

From the package directory, with Python 3 and NumPy available:

```text
python scripts/static_physics_audit.py --samples 2000 --caster-angles 720
```

The script writes `validation/static_physics.json` and `validation/static_physics.md`. It exits nonzero if a sampled input exceeds its URDF effort cap, a positive continuous caster-angle support bound is not established, or an internal verification fails. Passing means only that these particular checks passed for the reported URDF and assumptions.
