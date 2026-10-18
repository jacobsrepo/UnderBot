# R09 independent textured GLB audit

Status: **PASS**

File: `models/Underbot_R09_textured.glb`
SHA-256: `ad09fdc7719950058ca5b369c6a7fb44c2ef13c3dfb728ec682a57cd37aab64a`

Independent CPU parser reads GLB JSON/BIN, PNG pixels and typed vertex/index buffers; no Blender builder code is executed.

The actual GLB contains 250 component meshes, 23 link frames, 11 materials and 18 embedded 2048 × 2048 PNGs. Total triangles: 223,360.

All consumed images are embedded. Maximum decoded source-map channel difference: 0/255. Normal maps, metallic/roughness channel use, repeating samplers, material assignments, meaningful UVs and 100 mm texture scale are checked. Actual transformed mesh bounds agree with the geometry export manifest within 0.002 mm.

Polycarbonate uses transmission 0.94, IOR 1.586, roughness 0.055 and alpha 1. The file contains no studio floor, camera or lights.

## Interpretation

- The source library has 24 PNGs because separate roughness maps are provided for authoring; GLB embeds the 18 maps it consumes (base color, normal, packed metallic/roughness for six materials).
- Texture byte identity is recorded; correctness uses decoded pixels because an exporter may recompress PNGs or repack an unused channel.
- JSON extras contain optional provenance paths; these are not glTF runtime resource dependencies.
- Clear polycarbonate uses alpha 1 with transmission instead of the library's alpha .16 basic-viewer fallback; actual sheet thickness remains modeled geometry.
- Optical glass tint/roughness/clearcoat and LED emission are artistically adjusted in the render/export; other textured material maps and factors are verified against the supplied library.
- The exporter makes materials double-sided. This does not add geometry or change dimensions.
- UV ratio excludes triangles with doubled geometric area below 1e-13 m2 to avoid float32 cancellation in tiny bevel geometry.
- GLB is a detailed zero-pose visual assembly. Joint dynamics remain in the accompanying URDF package; this check does not certify hardware dimensions or dynamics.
