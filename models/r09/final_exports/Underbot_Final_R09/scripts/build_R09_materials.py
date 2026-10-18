"""Build original, periodic PBR surface textures for Underbot R09.

All textures are synthesized here, never copied from photographs. Surface response
is an artistic approximation: these maps do not establish measured optical or
manufacturing specifications. Texture height is shading only, never geometry.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import re
import argparse

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "outputs" / "Underbot_Final_R09"
TEX = OUT / "textures"
SOURCE = ROOT / "outputs" / "underbot_description" / "config" / "geometry_manifest.json"
N = 2048
TILE = 0.1


def linear_to_srgb(value):
    value = np.clip(value, 0.0, 1.0)
    return np.where(value <= 0.0031308, value * 12.92,
                    1.055 * np.power(value, 1.0 / 2.4) - 0.055)


def periodic_noise(seed, sigma_y, sigma_x):
    """Fourier Gaussian filtering gives a smooth exactly periodic random field."""
    rng = np.random.default_rng(seed)
    raw = rng.standard_normal((N, N), dtype=np.float32)
    fy = np.fft.fftfreq(N)[:, None]
    fx = np.fft.rfftfreq(N)[None, :]
    kernel = np.exp(-2 * np.pi**2 * (sigma_y**2 * fy**2 + sigma_x**2 * fx**2))
    result = np.fft.irfft2(np.fft.rfft2(raw) * kernel, s=(N, N)).astype(np.float32)
    result -= result.mean()
    result /= result.std()
    # Saturating the outliers prevents isolated glittery dots on black surfaces.
    return np.tanh(result / 2.8) * 2.8


def write_image(name, array, mode="RGB"):
    file = TEX / name
    data = np.rint(np.clip(array, 0.0, 1.0) * 255).astype(np.uint8)
    Image.fromarray(data, mode=mode).save(file, optimize=True)
    return "textures/" + name


def seam_measure(field):
    # A repeat boundary should have the same statistics as adjacent texels within
    # the image; it need not duplicate the final texel at the first texel.
    interior = (np.mean(np.abs(np.diff(field, axis=0))) +
                np.mean(np.abs(np.diff(field, axis=1)))) / 2
    border = (np.mean(np.abs(field[0] - field[-1])) +
              np.mean(np.abs(field[:, 0] - field[:, -1]))) / 2
    return {"boundary_mean_difference": float(border),
            "interior_mean_difference": float(interior),
            "boundary_to_interior_ratio": float(border / max(interior, 1e-10))}


def make_surface(key, color, roughness, metal, height_um, seed, kind="grain"):
    if kind == "brushed":
        fine = periodic_noise(seed, 1.0, 95.0)
        middle = periodic_noise(seed + 1, 2.7, 220.0)
        coarse = periodic_noise(seed + 2, 65.0, 180.0)
        height = (fine * 0.65 + middle * 0.35) * height_um * 1e-6
        rough = np.clip(roughness + 0.019 * fine + 0.009 * middle, 0.06, 0.97)
        tone = 1 + 0.009 * middle + 0.003 * coarse
    else:
        fine = periodic_noise(seed, 1.35, 1.35)
        middle = periodic_noise(seed + 1, 4.5, 4.5)
        coarse = periodic_noise(seed + 2, 70.0, 70.0)
        height = (fine * 0.72 + middle * 0.28) * height_um * 1e-6
        rough = np.clip(roughness + 0.012 * fine + 0.008 * middle + 0.002 * coarse, 0.06, 0.97)
        tone = 1 + 0.010 * middle + 0.003 * coarse

    # UV-v increases upwards; PNG rows increase downwards. Encode OpenGL/glTF +Y.
    pixel_m = TILE / N
    du = (np.roll(height, -1, axis=1) - np.roll(height, 1, axis=1)) / (2 * pixel_m)
    dv = (np.roll(height, 1, axis=0) - np.roll(height, -1, axis=0)) / (2 * pixel_m)
    normal = np.stack((-du, -dv, np.ones_like(height)), axis=-1)
    normal /= np.linalg.norm(normal, axis=-1, keepdims=True)
    base_linear = np.asarray(color, dtype=np.float32)[None, None, :] * tone[..., None]
    base_uri = write_image(key + "_basecolor.png", linear_to_srgb(base_linear))
    normal_uri = write_image(key + "_normal.png", normal * 0.5 + 0.5)
    rough_uri = write_image(key + "_roughness.png", rough, "L")
    packed = np.stack((np.ones_like(rough), rough, np.full_like(rough, metal)), axis=-1)
    packed_uri = write_image(key + "_metallicroughness.png", packed)
    definition = {
        "name": key,
        "pbrMetallicRoughness": {
            "baseColorFactor": [1.0, 1.0, 1.0, 1.0],
            "baseColorTexture": {"uri": base_uri, "texCoord": 0},
            "metallicFactor": 1.0,
            "roughnessFactor": 1.0,
            "metallicRoughnessTexture": {"uri": packed_uri, "texCoord": 0},
        },
        "normalTexture": {"uri": normal_uri, "texCoord": 0, "scale": 1.0},
        "alphaMode": "OPAQUE",
        "doubleSided": False,
        "extras": {
            "tile_size_m": TILE,
            "standalone_roughness_uri": rough_uri,
            "fallback_baseColorFactor_linear": [*color, 1.0],
            "fallback_roughnessFactor": roughness,
            "fallback_metallicFactor": metal,
            "height_rms_m": float(np.std(height)),
            "normal_convention": "OpenGL/glTF tangent space, +Y, RGB linear data",
            "colorspace": {"basecolor": "sRGB", "normal": "linear", "metallicroughness": "linear", "roughness": "linear"},
            "metallic_roughness_channels": {"R": "unused, 1", "G": "roughness", "B": "metallic"},
            "texture_sampler": {"wrapS": 10497, "wrapT": 10497, "magFilter": 9729, "minFilter": 9987},
            "seam_check": seam_measure(height),
        },
    }
    return definition


def solid(key, color, roughness, metallic=0.0, alpha=1.0, extensions=None, emissive=None):
    result = {"name": key, "pbrMetallicRoughness": {
        "baseColorFactor": [*color, alpha], "roughnessFactor": roughness,
        "metallicFactor": metallic}, "alphaMode": "OPAQUE" if alpha == 1 else "BLEND",
        "doubleSided": alpha < 1, "extras": {"tile_size_m": TILE}}
    if extensions:
        result["extensions"] = extensions
    if emissive:
        result["emissiveFactor"] = emissive
    return result


def material_for(part_name, source_material, link_name=""):
    if source_material == "polycarbonate":
        return "polycarbonate"
    if part_name in ("rubber_tyre", "front_wheel"):
        return "tire_rubber"
    if part_name.startswith("front_door_") or re.match(r"^side_-?\d+_", part_name) or "label" in part_name:
        return "matte_black_vinyl"
    if part_name.startswith(("post_", "rail_", "chassis_adapter", "adapter_spacer", "arm_bridge_", "arm_flange_", "battery_retainer_", "camera_vertical_bracket_", "cooler_fin_", "fork_cheek_")) or part_name in ("noco_tray", "camera_shelf", "lidar_pedestal"):
        return "black_painted_aluminium"
    if part_name in ("rgb_lens", "depth_lens", "infrared_emitter_provisional", "display"):
        return "optical_black_glass"
    if part_name.startswith("charge_led_"):
        return "status_led_green"
    return {"aluminium": "brushed_aluminium", "servo_black": "black_abs",
            "matte_black": "black_abs", "pcb_green": "pcb_green",
            "control_red": "control_red", "worx_orange": "worx_orange"}.get(source_material, "black_abs")


def validate_materials(data):
    materials = data["materials"]
    checks = {"status": "PASS", "resolution": [N, N], "map_count": len(data["files"]),
              "normal_convention": "OpenGL +Y", "seam_boundary_to_interior_ratios": {
                  key: val["extras"]["seam_check"]["boundary_to_interior_ratio"]
                  for key, val in materials.items() if "seam_check" in val["extras"]},
              "normal_checks": {}, "checks": [
                  "All texture files decode at 2048 x 2048 and match recorded SHA-256",
                  "All material factors are finite and in range 0..1",
                  "Quantized normal vectors have positive Z and unit error below 0.012",
                  "All texture assignments reference defined materials",
                  "Periodic map construction; boundary statistics match interior",
                  "Packed metallic/roughness G equals standalone roughness; B matches material metallic factor"]}
    for record in data["files"]:
        file = OUT / record["uri"]
        assert hashlib.sha256(file.read_bytes()).hexdigest() == record["sha256"]
        with Image.open(file) as im:
            assert im.size == (N, N)
            im.verify()
    assert all(0.6 < x < 1.5 for x in checks["seam_boundary_to_interior_ratios"].values())
    for key, mat in materials.items():
        mr = mat["pbrMetallicRoughness"]
        factors = mr["baseColorFactor"] + [mr["roughnessFactor"], mr["metallicFactor"]]
        assert all(np.isfinite(x) and 0 <= x <= 1 for x in factors)
        if "normalTexture" not in mat:
            continue
        with Image.open(OUT / mat["normalTexture"]["uri"]) as im:
            normal = np.asarray(im).astype(np.float32) / 255 * 2 - 1
        unit_error = np.abs(np.linalg.norm(normal, axis=-1) - 1)
        assert float(normal[..., 2].min()) > 0
        assert float(unit_error.max()) < 0.012
        checks["normal_checks"][key] = {"maximum_unit_length_error": float(unit_error.max()),
                                        "minimum_normal_z": float(normal[..., 2].min())}
        with Image.open(OUT / mr["metallicRoughnessTexture"]["uri"]) as im:
            packed = np.asarray(im)
        with Image.open(OUT / mat["extras"]["standalone_roughness_uri"]) as im:
            rough = np.asarray(im)
        assert np.array_equal(packed[..., 1], rough)
        assert np.all(packed[..., 2] == round(mat["extras"]["fallback_metallicFactor"] * 255))
        assert np.all(packed[..., 0] == 255)
    for assignments in data["part_assignments"].values():
        assert all(value in materials for value in assignments.values())
    (OUT / "material_checks.json").write_text(json.dumps(checks, indent=2) + "\n", encoding="utf-8")
    return checks


def main():
    TEX.mkdir(parents=True, exist_ok=True)
    surfaces = [
        ("matte_black_vinyl", (0.015, 0.017, 0.019), 0.79, 0.0, 1.20, 3101, "grain"),
        ("black_painted_aluminium", (0.022, 0.024, 0.027), 0.48, 0.0, 0.70, 3105, "grain"),
        ("tire_rubber", (0.009, 0.010, 0.011), 0.90, 0.0, 1.35, 3109, "grain"),
        ("brushed_aluminium", (0.63, 0.67, 0.71), 0.32, 1.0, 0.65, 3113, "brushed"),
        ("black_abs", (0.027, 0.030, 0.034), 0.54, 0.0, 0.75, 3117, "grain"),
        ("pcb_green", (0.012, 0.085, 0.039), 0.39, 0.0, 0.18, 3121, "grain"),
    ]
    materials = {}
    for values in surfaces:
        materials[values[0]] = make_surface(*values)
        print("Built", values[0], flush=True)
    materials["polycarbonate"] = solid("polycarbonate", [0.94, 0.975, 0.99], 0.055, alpha=0.16,
        extensions={"KHR_materials_transmission": {"transmissionFactor": 0.94},
                    "KHR_materials_ior": {"ior": 1.586},
                    "KHR_materials_volume": {"thicknessFactor": 0.003, "attenuationDistance": 3.0,
                                             "attenuationColor": [0.94, 0.98, 0.99]}})
    materials["polycarbonate"]["extras"]["note"] = "Alpha fallback supports basic viewers; use transmission for raytraced rendering. Clear sheet, no opaque surface map. Thickness is representative; model geometry sets sheet thickness."
    materials["optical_black_glass"] = solid("optical_black_glass", [0.004, 0.007, 0.013], 0.075,
        extensions={"KHR_materials_ior": {"ior": 1.52}})
    materials["worx_orange"] = solid("worx_orange", [0.96, 0.22, 0.015], 0.42)
    materials["control_red"] = solid("control_red", [0.65, 0.015, 0.015], 0.44)
    materials["status_led_green"] = solid("status_led_green", [0.015, 0.55, 0.035], 0.28,
        emissive=[0.025, 0.45, 0.03])
    source = json.loads(SOURCE.read_text(encoding="utf-8"))
    assignments = {link: {p["name"]: material_for(p["name"], p["material"], link)
                          for p in value["parts"]} for link, value in source["links"].items()}
    data = {
        "schema": "underbot-pbr-material-library-1.0",
        "revision": "R09",
        "description": "Original procedural PBR surface maps; material appearance is an artistic approximation, not measured material data.",
        "source_geometry_sha256": hashlib.sha256(SOURCE.read_bytes()).hexdigest(),
        "texture_resolution": [N, N], "texture_tile_size_m": TILE,
        "units": "metres",
        "usage": [
            "URIs are relative to this JSON file. Replace texture URI objects with glTF texture indices when packaging GLB.",
            "Planar/box projection uses 1 UV repeat per 0.1 m; preserve consistent right-handed tangent basis.",
            "Base-color PNGs are sRGB. Roughness, metallic-roughness and normal PNGs are linear data.",
            "Textures only affect shading; do not displace or rescale the dimensioned STL meshes.",
            "STL does not support materials; use the accompanying GLB or OBJ/MTL for appearance."
        ],
        "materials": materials,
        "urdf_material_fallbacks": {"matte_black": "matte_black_vinyl", "servo_black": "black_abs",
            "aluminium": "brushed_aluminium", "polycarbonate": "polycarbonate", "pcb_green": "pcb_green",
            "worx_orange": "worx_orange", "control_red": "control_red"},
        "part_assignments": assignments,
        "source_texture_license": "Original procedurally generated textures created for this project; no third-party imagery used.",
    }
    data["files"] = [{"uri": "textures/" + p.name, "bytes": p.stat().st_size,
                      "sha256": hashlib.sha256(p.read_bytes()).hexdigest()}
                     for p in sorted(TEX.glob("*.png"))]
    (OUT / "materials.json").write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    validate_materials(data)
    print(json.dumps({"textures": len(data["files"]), "bytes": sum(x["bytes"] for x in data["files"]), "materials": len(materials)}))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=OUT,
                        help="Destination directory containing materials.json and textures/")
    parser.add_argument("--source", type=Path, default=None,
                        help="Input geometry_manifest.json (for per-part assignments only)")
    parser.add_argument("--validate-only", action="store_true",
                        help="Validate existing output maps and metadata without regenerating them")
    args = parser.parse_args()
    OUT = args.output.resolve()
    TEX = OUT / "textures"
    if args.source:
        SOURCE = args.source.resolve()
    elif not SOURCE.exists():
        candidates = [ROOT / "config/geometry_manifest.json",
                      ROOT / "underbot_description/config/geometry_manifest.json",
                      ROOT / "simulation/underbot_description/config/geometry_manifest.json"]
        SOURCE = next((p for p in candidates if p.exists()), SOURCE)
    if args.validate_only:
        result = validate_materials(json.loads((OUT / "materials.json").read_text(encoding="utf-8")))
        print(json.dumps({"status": result["status"], "map_count": result["map_count"]}))
    else:
        if not SOURCE.is_file():
            parser.error("Cannot locate geometry_manifest.json; provide its path using --source.")
        main()
