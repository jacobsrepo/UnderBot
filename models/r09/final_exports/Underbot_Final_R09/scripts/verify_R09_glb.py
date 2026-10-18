"""Read-only, independent GLB resource, texture and UV audit for Underbot R09.

Uses the GLB bytes directly; does not import or call the Blender construction code.
Requires Python, NumPy and Pillow. No model files are rewritten.
"""
from __future__ import annotations

import argparse
from collections import Counter
import hashlib
from io import BytesIO
import json
from pathlib import Path
import struct

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
DEFAULT = ROOT / "outputs/Underbot_Final_R09"


class Glb:
    def __init__(self, path):
        self.path = path
        self.raw = path.read_bytes()
        magic, version, declared = struct.unpack_from("<4sII", self.raw, 0)
        assert magic == b"glTF" and version == 2 and declared == len(self.raw)
        chunks = []
        offset = 12
        while offset < len(self.raw):
            length, kind = struct.unpack_from("<II", self.raw, offset)
            assert length % 4 == 0
            offset += 8
            assert offset + length <= len(self.raw)
            chunks.append((kind, self.raw[offset:offset + length]))
            offset += length
        assert offset == len(self.raw)
        assert len(chunks) == 2 and chunks[0][0] == 0x4E4F534A and chunks[1][0] == 0x004E4942
        self.doc = json.loads(chunks[0][1])
        self.bin = chunks[1][1]
        assert self.doc["asset"]["version"] == "2.0"
        assert len(self.doc["buffers"]) == 1
        assert "uri" not in self.doc["buffers"][0]
        assert 0 <= len(self.bin) - self.doc["buffers"][0]["byteLength"] <= 3
        for bv in self.doc["bufferViews"]:
            assert bv["buffer"] == 0
            assert 0 <= bv.get("byteOffset", 0)
            assert bv.get("byteOffset", 0) + bv["byteLength"] <= len(self.bin)

    def view(self, index):
        v = self.doc["bufferViews"][index]
        start = v.get("byteOffset", 0)
        return self.bin[start:start + v["byteLength"]]

    def accessor(self, index):
        a = self.doc["accessors"][index]
        assert "sparse" not in a, "Unexpected sparse accessor; extend the reader before accepting."
        assert not a.get("normalized", False), "Unexpected normalized accessor."
        types = {5120: "i1", 5121: "u1", 5122: "<i2", 5123: "<u2", 5125: "<u4", 5126: "<f4"}
        sizes = {"SCALAR": 1, "VEC2": 2, "VEC3": 3, "VEC4": 4, "MAT4": 16}
        dtype = np.dtype(types[a["componentType"]])
        width = sizes[a["type"]]
        view = self.doc["bufferViews"][a["bufferView"]]
        stride = view.get("byteStride", dtype.itemsize * width)
        offset = a.get("byteOffset", 0)
        assert stride >= dtype.itemsize * width
        assert offset + (a["count"] - 1) * stride + width * dtype.itemsize <= view["byteLength"]
        values = np.ndarray((a["count"], width), dtype=dtype, buffer=self.view(a["bufferView"]),
                            offset=offset, strides=(stride, dtype.itemsize)).copy()
        return values[:, 0] if width == 1 else values

    def image_bytes(self, index):
        info = self.doc["images"][index]
        assert "uri" not in info and info.get("mimeType") == "image/png"
        raw = self.view(info["bufferView"])
        assert raw[:8] == b"\x89PNG\r\n\x1a\n"
        return raw

    def texture_image(self, texture_info):
        texture = self.doc["textures"][texture_info["index"]]
        assert texture_info.get("texCoord", 0) == 0
        assert not texture_info.get("extensions"), "Texture transform needs explicit UV audit support."
        assert not texture.get("extensions"), "Texture extension image selection needs explicit support."
        sampler = self.doc.get("samplers", [{}])[texture.get("sampler", 0)]
        assert sampler.get("wrapS", 10497) == 10497 and sampler.get("wrapT", 10497) == 10497
        raw = self.image_bytes(texture["source"])
        with Image.open(BytesIO(raw)) as im:
            assert im.size == (2048, 2048)
            rgb = np.asarray(im.convert("RGB"))
        return raw, rgb, texture["source"]


def node_matrix(node):
    if "matrix" in node:
        return np.asarray(node["matrix"], dtype=float).reshape(4, 4).T
    x, y, z, w = node.get("rotation", [0, 0, 0, 1])
    rot = np.array([[1 - 2*(y*y+z*z), 2*(x*y-z*w), 2*(x*z+y*w)],
                    [2*(x*y+z*w), 1 - 2*(x*x+z*z), 2*(y*z-x*w)],
                    [2*(x*z-y*w), 2*(y*z+x*w), 1 - 2*(x*x+y*y)]])
    mat = np.eye(4)
    mat[:3, :3] = rot @ np.diag(node.get("scale", [1, 1, 1]))
    mat[:3, 3] = node.get("translation", [0, 0, 0])
    return mat


def audit(package):
    glb_path = package / "models/Underbot_R09_textured.glb"
    g = Glb(glb_path)
    d = g.doc
    library = json.loads((package / "materials.json").read_text(encoding="utf-8"))
    geometry = json.loads((package / "geometry_export_manifest.json").read_text(encoding="utf-8"))
    findings = []

    def check(condition, description):
        if not bool(condition):
            findings.append(description)

    check(not d.get("cameras"), "GLB contains camera definitions.")
    check(not d.get("animations"), "Unexpected animation content in zero-pose assembly.")
    check(not d.get("skins"), "Unexpected skinned mesh content in rigid robot export.")
    check("KHR_lights_punctual" not in d.get("extensions", {}), "GLB contains studio lights.")
    check(not d.get("extensionsRequired"), "GLB has required extensions; baseline geometry fallback should remain usable.")

    actual_materials = {m["name"]: m for m in d["materials"]}
    check(set(actual_materials) == set(library["materials"]), "Exported material library names differ from source library.")
    texture_checks = []
    used_images = set()
    for name, expected in library["materials"].items():
        actual = actual_materials[name]
        if "normalTexture" not in expected:
            continue
        for role, path in (("basecolor", "baseColorTexture"), ("metallicroughness", "metallicRoughnessTexture"), ("normal", "normalTexture")):
            spec = expected[path] if role == "normal" else expected["pbrMetallicRoughness"][path]
            info = actual[path] if role == "normal" else actual["pbrMetallicRoughness"][path]
            embedded_bytes, pixels, image_id = g.texture_image(info)
            used_images.add(image_id)
            source_path = package / spec["uri"]
            with Image.open(source_path) as im:
                source_pixels = np.asarray(im.convert("RGB"))
            # R in metallic-roughness is not consumed by glTF; compare only G/B.
            relevant = slice(1, 3) if role == "metallicroughness" else slice(None)
            delta = np.abs(pixels[..., relevant].astype(np.int16) - source_pixels[..., relevant].astype(np.int16))
            maximum = int(delta.max())
            check(maximum <= 1, f"{name}/{role}: meaningful source texture channels changed by >1/255.")
            rec = {"material": name, "role": role, "image_index": image_id,
                   "embedded_image_sha256": hashlib.sha256(embedded_bytes).hexdigest(),
                   "source_image_sha256": hashlib.sha256(source_path.read_bytes()).hexdigest(),
                   "byte_identical": embedded_bytes == source_path.read_bytes(),
                   "decoded_max_channel_error_8bit": maximum,
                   "decoded_mean_channel_error_8bit": float(delta.mean())}
            if role == "normal":
                normal = pixels.astype(np.float32) / 255 * 2 - 1
                error = float(np.abs(np.linalg.norm(normal, axis=-1) - 1).max())
                check(error < .012 and np.all(normal[..., 2] > 0), f"{name}: invalid decoded tangent normals.")
                check(abs(info.get("scale", 1) - spec.get("scale", 1)) < 1e-6, f"{name}: normal-map strength changed.")
                rec["maximum_normal_unit_length_error"] = error
            if role == "metallicroughness":
                expected_metal = expected["extras"]["fallback_metallicFactor"]
                check(np.all(pixels[..., 2] == round(expected_metal * 255)), f"{name}: metallic B channel incorrect.")
                check(np.ptp(pixels[..., 1]) > 0, f"{name}: roughness texture became constant.")
                pbr = actual["pbrMetallicRoughness"]
                check(pbr.get("metallicFactor", 1) == 1 and pbr.get("roughnessFactor", 1) == 1,
                      f"{name}: unexpected multipliers would alter textured response.")
            texture_checks.append(rec)
        check(actual["pbrMetallicRoughness"].get("baseColorFactor", [1, 1, 1, 1]) == [1, 1, 1, 1],
              f"{name}: base-color texture is unexpectedly multiplied/tinted.")
    check(len(used_images) == len(d["images"]) == 18, "Embedded images include unused content or lack required material maps.")

    pc = actual_materials["polycarbonate"]
    pc_pbr = pc["pbrMetallicRoughness"]
    transmission = pc.get("extensions", {}).get("KHR_materials_transmission", {}).get("transmissionFactor", 0)
    ior = pc.get("extensions", {}).get("KHR_materials_ior", {}).get("ior", 1.5)
    check(abs(transmission - .94) < 1e-6, "Polycarbonate transmission does not match .94.")
    check(abs(ior - 1.586) < 1e-6, "Polycarbonate IOR does not match 1.586.")
    check(abs(pc_pbr.get("roughnessFactor", 1) - .055) < 1e-6, "Polycarbonate roughness does not match .055.")
    check(pc.get("alphaMode", "OPAQUE") == "OPAQUE" and pc_pbr.get("baseColorFactor", [1, 1, 1, 1])[3] == 1,
          "Physical transmission should not be attenuated a second time by low alpha.")
    check("baseColorTexture" not in pc_pbr and pc_pbr.get("metallicFactor", 1) == 0,
          "Transparent polycarbonate must not have an opaque painted/metallic surface map.")

    nodes = d["nodes"]
    parents = {}
    world = {}
    reached = set()

    def walk(index, matrix):
        assert index not in reached, "Scene graph is cyclic or a node has multiple parents."
        reached.add(index)
        node = nodes[index]
        world[index] = matrix @ node_matrix(node)
        check(np.isfinite(world[index]).all(), f"Node {index} has nonfinite transform.")
        check("camera" not in node and "KHR_lights_punctual" not in node.get("extensions", {}),
              f"Node {index} contains studio camera/light.")
        check("studio" not in node.get("name", "").lower(), f"Studio node leaked into robot export: {node.get('name')}")
        for child in node.get("children", []):
            parents[child] = index
            walk(child, world[index])

    check(len(d.get("scenes", [])) == 1, "Expected exactly one exported robot scene.")
    for index in d["scenes"][d.get("scene", 0)]["nodes"]:
        walk(index, np.eye(4))
    check(len(reached) == len(nodes), "GLB contains orphan nodes not reachable from its scene.")
    mesh_nodes = [(i, n) for i, n in enumerate(nodes) if "mesh" in n]
    identities = {(n.get("extras", {}).get("source_link"), n.get("extras", {}).get("source_part_name")): i for i, n in mesh_nodes}
    expected_parts = {(x["link"], x["part"]): x for x in geometry["components"]}
    check(len(identities) == len(mesh_nodes) == len(expected_parts), "Component provenance is missing, duplicated or has unexpected mesh nodes.")
    check(set(identities) == set(expected_parts), "GLB component identity set differs from dimensioned geometry export manifest.")
    mesh_references = Counter(n["mesh"] for _, n in mesh_nodes)
    check(set(mesh_references) == set(range(len(d["meshes"]))), "GLB contains unreferenced mesh resources.")
    check(len(nodes) - len(mesh_nodes) == len(geometry["links"]), "Non-mesh nodes do not match robot link-frame count.")
    link_nodes = {n.get("name") for n in nodes if "mesh" not in n}
    check(link_nodes == set(geometry["links"]), "Non-mesh nodes contain non-robot names or missing link frames.")

    mesh_checks = []
    all_bounds = []
    material_usage = Counter()
    # Rotation from ROS x-forward/y-left/z-up to glTF x-forward/y-up/z-right.
    conversion = np.array([[1., 0, 0], [0, 0, 1.], [0, -1., 0]])
    for (link, part), index in identities.items():
        node = nodes[index]
        mesh = d["meshes"][node["mesh"]]
        object_world_positions = []
        for primitive in mesh["primitives"]:
            check(primitive.get("mode", 4) == 4, f"{link}/{part}: unsupported non-triangle primitive.")
            attributes = primitive["attributes"]
            check({"POSITION", "NORMAL", "TEXCOORD_0"}.issubset(attributes), f"{link}/{part}: missing positions, normals or UVs.")
            positions = g.accessor(attributes["POSITION"]).astype(float)
            normals = g.accessor(attributes["NORMAL"]).astype(float)
            uv = g.accessor(attributes["TEXCOORD_0"]).astype(float)
            indices = g.accessor(primitive["indices"]).astype(int)
            check(indices.size % 3 == 0 and indices.min() >= 0 and indices.max() < len(positions), f"{link}/{part}: invalid triangle indices.")
            check(len(positions) == len(normals) == len(uv), f"{link}/{part}: vertex attributes have inconsistent counts.")
            check(np.isfinite(positions).all() and np.isfinite(normals).all() and np.isfinite(uv).all(), f"{link}/{part}: nonfinite vertex data.")
            check(np.max(np.abs(np.linalg.norm(normals, axis=1) - 1)) < 2e-5, f"{link}/{part}: vertex normals are not unit length.")
            check(np.all(np.ptp(uv, axis=0) > 1e-6), f"{link}/{part}: UVs are constant/collapsed.")
            triangles = indices.reshape(-1, 3)
            p = positions[triangles]
            t = uv[triangles]
            a3 = np.linalg.norm(np.cross(p[:, 1] - p[:, 0], p[:, 2] - p[:, 0]), axis=1)
            degenerate_count = int(np.count_nonzero(a3 < 1e-18))
            check(degenerate_count == 0, f"{link}/{part}: GLB contains degenerate triangles.")
            e1, e2 = t[:, 1] - t[:, 0], t[:, 2] - t[:, 0]
            a2 = np.abs(e1[:, 0] * e2[:, 1] - e1[:, 1] * e2[:, 0])
            meaningful = a3 > 1e-13
            check(np.any(meaningful), f"{link}/{part}: mesh has no measurable triangle area.")
            area_ratio = a2[meaningful] / a3[meaningful]
            check(np.all(area_ratio > 0), f"{link}/{part}: nonzero-area triangles have degenerate UVs.")
            # Dominant-axis projection on a .1 m tile has area ratio 100*|n_axis|.
            # Since |n_axis| is the dominant component, its minimum is 1/sqrt(3).
            check(float(area_ratio.min()) >= 57.0 and float(area_ratio.max()) <= 100.6,
                  f"{link}/{part}: UV scale is inconsistent with a .1 m dominant-plane tile.")
            material = d["materials"][primitive["material"]]["name"]
            expected_material = library["part_assignments"][link][part]
            check(material == expected_material, f"{link}/{part}: material assignment {material} should be {expected_material}.")
            material_usage[material] += 1
            transformed = (world[index] @ np.column_stack((positions, np.ones(len(positions)))).T).T[:, :3]
            object_world_positions.append(transformed)
            mesh_checks.append({"link": link, "part": part, "material": material,
                                "vertices": len(positions), "triangles": len(triangles),
                                "degenerate_triangles": degenerate_count,
                                "uv_min": uv.min(axis=0).tolist(), "uv_max": uv.max(axis=0).tolist(),
                                "uv_to_geometry_area_ratio_min": float(area_ratio.min()),
                                "uv_to_geometry_area_ratio_max": float(area_ratio.max()),
                                "very_small_triangles_excluded_from_ratio": int(np.count_nonzero(~meaningful))})
        world_positions = np.concatenate(object_world_positions)
        bounds = np.stack((world_positions.min(axis=0), world_positions.max(axis=0)))
        all_bounds.append(bounds)
        lo, hi = np.asarray(expected_parts[link, part]["world_bounds_m"])
        expected_corners = np.array([[x, y, z] for x in (lo[0], hi[0]) for y in (lo[1], hi[1]) for z in (lo[2], hi[2])]) @ conversion.T
        expected_bounds = np.stack((expected_corners.min(axis=0), expected_corners.max(axis=0)))
        check(np.max(np.abs(bounds - expected_bounds)) < 2e-6, f"{link}/{part}: actual GLB bounds disagree with export manifest.")

    bbox = np.stack((np.min([x[0] for x in all_bounds], axis=0), np.max([x[1] for x in all_bounds], axis=0)))
    report = {
        "status": "PASS" if not findings else "FAIL",
        "file": "models/Underbot_R09_textured.glb",
        "sha256": hashlib.sha256(g.raw).hexdigest(), "bytes": len(g.raw),
        "audit_method": "Independent CPU parser reads GLB JSON/BIN, PNG pixels and typed vertex/index buffers; no Blender builder code is executed.",
        "glb_version": 2, "generator": d["asset"].get("generator"),
        "counts": {"nodes": len(nodes), "link_frames": len(nodes) - len(mesh_nodes), "mesh_nodes": len(mesh_nodes),
                   "meshes": len(d["meshes"]), "materials": len(d["materials"]), "textures": len(d["textures"]),
                   "embedded_images": len(d["images"]), "triangles": sum(x["triangles"] for x in mesh_checks)},
        "all_resources_embedded": True, "excluded_studio_content": ["lights", "camera", "floor", "background"],
        "coordinate_convention": "glTF metre coordinates, Y up; geometry is rotated from ROS x-forward/y-left/z-up.",
        "assembled_bounds_gltf_m": bbox.tolist(),
        "polycarbonate": {"transmission": transmission, "ior": ior, "roughness": pc_pbr.get("roughnessFactor"),
                           "alpha": pc_pbr["baseColorFactor"][3], "uses_opaque_texture": "baseColorTexture" in pc_pbr},
        "material_usage": dict(material_usage), "texture_checks": texture_checks,
        "mesh_checks": mesh_checks, "errors": findings,
        "notes": [
            "The source library has 24 PNGs because separate roughness maps are provided for authoring; GLB embeds the 18 maps it consumes (base color, normal, packed metallic/roughness for six materials).",
            "Texture byte identity is recorded; correctness uses decoded pixels because an exporter may recompress PNGs or repack an unused channel.",
            "JSON extras contain optional provenance paths; these are not glTF runtime resource dependencies.",
            "Clear polycarbonate uses alpha 1 with transmission instead of the library's alpha .16 basic-viewer fallback; actual sheet thickness remains modeled geometry.",
            "Optical glass tint/roughness/clearcoat and LED emission are artistically adjusted in the render/export; other textured material maps and factors are verified against the supplied library.",
            "The exporter makes materials double-sided. This does not add geometry or change dimensions.",
            "UV ratio excludes triangles with doubled geometric area below 1e-13 m2 to avoid float32 cancellation in tiny bevel geometry.",
            "GLB is a detailed zero-pose visual assembly. Joint dynamics remain in the accompanying URDF package; this check does not certify hardware dimensions or dynamics."
        ]}
    return report


def write_report(report, package):
    folder = package / "validation"
    folder.mkdir(parents=True, exist_ok=True)
    (folder / "textured_export_audit.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    c = report["counts"]
    pixel_max = max(x["decoded_max_channel_error_8bit"] for x in report["texture_checks"])
    lines = ["# R09 independent textured GLB audit", "", f"Status: **{report['status']}**", "",
             f"File: `{report['file']}`", f"SHA-256: `{report['sha256']}`", "",
             report["audit_method"], "",
             f"The actual GLB contains {c['mesh_nodes']} component meshes, {c['link_frames']} link frames, {c['materials']} materials and {c['embedded_images']} embedded 2048 × 2048 PNGs. Total triangles: {c['triangles']:,}.", "",
             f"All consumed images are embedded. Maximum decoded source-map channel difference: {pixel_max}/255. Normal maps, metallic/roughness channel use, repeating samplers, material assignments, meaningful UVs and 100 mm texture scale are checked. Actual transformed mesh bounds agree with the geometry export manifest within 0.002 mm.", "",
             "Polycarbonate uses transmission 0.94, IOR 1.586, roughness 0.055 and alpha 1. The file contains no studio floor, camera or lights.", ""]
    if report["errors"]:
        lines += ["## Findings", ""] + ["- " + x for x in report["errors"]] + [""]
    lines += ["## Interpretation", ""] + ["- " + x for x in report["notes"]]
    (folder / "textured_export_audit.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--package", type=Path, default=DEFAULT)
    args = parser.parse_args()
    result = audit(args.package.resolve())
    write_report(result, args.package.resolve())
    print(json.dumps({"status": result["status"], "sha256": result["sha256"], "counts": result["counts"], "errors": result["errors"]}, indent=2))
    raise SystemExit(0 if result["status"] == "PASS" else 1)
