# R09 visual revision and R08 physical configuration

R09 adds detailed, dimension-preserving visual meshes and textured viewing exports. The accepted 200 × 200 mm floor/frame bounds, 204 × 204 mm covered body and 500 mm posts remain the reference design. R08 joint origins, rotations, axes, limits, collision shapes and inertial parameters are retained.

The source parameter/geometry manifest still identifies the R08 physical design. R09 visual meshes are built by the Blender source supplied in the final bundle, not by the older simple-mesh generator alone. If dimensions change, rebuild the physical manifest first, rebuild detailed visuals, then repeat validation and refresh the archive.

The current mesh files and their hashes are recorded in the refreshed validation reports. Earlier render/mesh evidence is not used to validate the R09 surfaces. Actual hardware assumptions remain listed in accuracy_and_physics.md.
