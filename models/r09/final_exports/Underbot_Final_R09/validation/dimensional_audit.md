# R09 independent dimensional audit: PASS

Independent digital geometry, STL integrity, SI/mm transform and unchanged physics audit. No hardware certification.

4730 checks; 0 failures.

- Actual floor and frame envelope: 200 × 200 mm. Accepted covered body: 204 × 204 mm.
- Four posts: 20 × 20 × 500 mm. Sixteen rails: 160 mm cut length.
- Components: 250; assembled STL triangles: 223,360.
- Zero-pose full model envelope: 558.000 × 713.449 × 778.000 mm, including base, arms and LiDAR.
- Individual and assembled CAD STLs are millimetres; URDF visual STLs are metres. Actual triangle vertices were compared after transforms.
- Final joint origins/axes, collision primitives and mass/inertia values match the previously tested R08 model.

## Limits

- The floor/frame dimensions and accepted 204 mm covered body are user requirements. The 3 mm floors and 2 mm covers are proposed material thicknesses.
- WR141E 558 × 404 × 205 mm and upright GB70 body 69 × 99 × 222 mm are published envelopes; detailed chassis and battery contours remain approximations.
- Bare Kinect layout, arm pivots/lengths, wheel/caster geometry, electronics, hardware masses, joint limits and motor ratings remain unmeasured design inputs.
- Closed STL shells may overlap at fasteners/assembly interfaces. A watertight collection of shells is not a Boolean-unioned print-ready solid.
