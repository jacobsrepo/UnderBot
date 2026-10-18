# Underbot independent authoring validation

Status: **PASS_WITH_REVIEW_NOTES**

Independent Python authoring validation; no simulator import or dynamics run.

Input: `underbot.portable.urdf`

Tree: 23 links, 22 joints, root `base_link`, 16 independent coordinates.

Estimated total mass: 19.601008 kg. Zero-pose centre of mass in root frame: [-0.0639650552308846, 4.101829906929535e-05, 0.29820547138487047] m.
Each massive-link inertia was checked for finite positive mass, positive principal moments and the principal-moment triangle inequalities. Shape-free fixed reference frames may explicitly declare zero mass and a zero tensor; these contribute no mass and may have no moving descendants.

R08 nominal construction was checked independently: WR141E 558 × 404 × 205 mm published envelope; 200 ×200 mm frame and floors; 204 ×204 mm covered body with external 2 mm sheets; four 500 mm posts; sixteen 160 mm rails; 160 ×160 mm clear opening; black frame/front/sides; upright GB70 body and installation reservation; casing-free camera reservation with 2 mm lateral gaps; wheel contacts, two passive caster joints and arm root datums. The stripped camera module dimensions, optics, retained camera mass, wheel/caster geometry and mounting positions are provisional simulation inputs. These checks establish consistency and fit of declared reservations, not verified hardware fit. Fixed cover/shelf interfaces are checked for penetration independently of inter-link screening. The source register, URDF transforms/colliders and all referenced meshes were checked separately.

## Errors

None.

## Review notes

- base_link.stl: closed oriented visual shells touch at 4 nonmanifold edges; not a unioned physics solid

## Scope limits

- Hardware dimensions, masses, motor limits and contact coefficients are not measured by this validator.
- Collision screening uses primitive oriented bounds; cylinder and mesh candidates may be false positives.
- One-joint sweeps do not prove collision freedom for simultaneous multi-joint motion.

## Collision screening

Oriented bounding box SAT; adjacent links and explicit allowed pairs excluded.

No nonadjacent candidates in the checked poses. This does not prove complete collision freedom.

The JSON report includes link world bounds, pivot/axis directions, optical-frame basis vectors, STL topology, COM and inertia results.
