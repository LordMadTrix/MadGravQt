"""
MadGrav 3D Multi-Layer Topographic Map Generator
Procedural & Image-based elevation contour slicing with alignment pins and layered frames.
"""

from typing import List, Dict, Tuple, Any, Optional, Union
import math
import numpy as np
from PIL import Image


def generate_procedural_heightmap(
    preset: str = "island",
    grid_res: int = 100,
    seed: int = 42,
) -> np.ndarray:
    """
    Generates a 2D float heightmap array in range [0.0, 1.0].
    Presets: "island", "mountain", "canyon", "volcano", "lake"
    """
    rng = np.random.RandomState(seed)
    x = np.linspace(-1.0, 1.0, grid_res)
    y = np.linspace(-1.0, 1.0, grid_res)
    xx, yy = np.meshgrid(x, y)
    dist = np.sqrt(xx**2 + yy**2)

    # Multi-frequency noise approximation using harmonics
    noise = np.zeros((grid_res, grid_res), dtype=np.float32)
    freqs = [1.5, 3.0, 6.0, 12.0]
    weights = [0.5, 0.25, 0.15, 0.1]

    for f, w in zip(freqs, weights):
        phase_x = rng.uniform(0, 2 * math.pi)
        phase_y = rng.uniform(0, 2 * math.pi)
        noise += w * (
            np.sin(xx * f * math.pi + phase_x) * np.cos(yy * f * math.pi + phase_y)
        )

    # Normalize noise to [0, 1]
    noise = (noise - noise.min()) / (noise.max() - noise.min() + 1e-6)

    if preset == "island":
        # Radial falloff
        falloff = np.clip(1.0 - (dist / 0.9)**2, 0.0, 1.0)
        hm = noise * falloff
    elif preset == "volcano":
        crater = np.exp(-((dist - 0.4)**2) / 0.08)
        hm = crater * 0.7 + noise * 0.3
    elif preset == "canyon":
        river = np.abs(np.sin(xx * 2.0 + yy))
        hm = noise * (0.3 + 0.7 * river)
    elif preset == "lake":
        basin = np.clip((dist / 0.8)**1.5, 0.0, 1.0)
        hm = basin * 0.7 + noise * 0.3
    else:  # "mountain"
        cone = np.clip(1.0 - dist, 0.0, 1.0)
        hm = cone * 0.6 + noise * 0.4

    # Final normalization
    hm = (hm - hm.min()) / (hm.max() - hm.min() + 1e-6)
    return hm.astype(np.float32)


def _extract_contours_for_threshold(
    heightmap: np.ndarray,
    threshold: float,
    width_mm: float,
    height_mm: float,
) -> List[List[Tuple[float, float]]]:
    """
    Extracts 2D iso-contour line loops for a given height threshold using 2D marching grid.
    """
    rows, cols = heightmap.shape
    binary = (heightmap >= threshold).astype(np.uint8)

    contours = []
    # Find boundary pixels of connected regions
    dx_mm = width_mm / cols
    dy_mm = height_mm / rows

    # Simple contour polygon sampling
    for r in range(0, rows - 1, 2):
        in_segment = False
        seg_start = 0
        for c in range(cols):
            val = binary[r, c]
            if val and not in_segment:
                in_segment = True
                seg_start = c
            elif not val and in_segment:
                in_segment = False
                # Closed loop approximation for layer slice
                x1 = seg_start * dx_mm
                x2 = c * dx_mm
                y = r * dy_mm
                contours.append([
                    (round(x1, 2), round(y, 2)),
                    (round(x2, 2), round(y, 2)),
                    (round(x2, 2), round(y + dy_mm * 2, 2)),
                    (round(x1, 2), round(y + dy_mm * 2, 2)),
                    (round(x1, 2), round(y, 2)),
                ])
        if in_segment:
            x1 = seg_start * dx_mm
            x2 = (cols - 1) * dx_mm
            y = r * dy_mm
            contours.append([
                (round(x1, 2), round(y, 2)),
                (round(x2, 2), round(y, 2)),
                (round(x2, 2), round(y + dy_mm * 2, 2)),
                (round(x1, 2), round(y + dy_mm * 2, 2)),
                (round(x1, 2), round(y, 2)),
            ])

    return contours


def generate_layered_topo_map(
    preset: str = "island",
    custom_image: Optional[Image.Image] = None,
    width_mm: float = 120.0,
    height_mm: float = 120.0,
    layers_count: int = 5,
    add_frame: bool = True,
    pin_holes: bool = True,
    pin_diameter_mm: float = 3.0,
    frame_margin_mm: float = 8.0,
    seed: int = 42,
) -> List[Dict[str, Any]]:
    """
    Generates multi-layer slice definitions for stacked 3D topographic art.
    """
    if custom_image is not None:
        img_gray = custom_image.convert("L").resize((100, 100))
        hm = np.array(img_gray, dtype=np.float32) / 255.0
    else:
        hm = generate_procedural_heightmap(preset=preset, grid_res=100, seed=seed)

    layers = []
    pin_radius = pin_diameter_mm / 2.0
    half_margin = frame_margin_mm / 2.0

    # 4 corner pin locations
    pins = []
    if pin_holes:
        pins = [
            (half_margin, half_margin, pin_radius),
            (width_mm - half_margin, half_margin, pin_radius),
            (width_mm - half_margin, height_mm - half_margin, pin_radius),
            (half_margin, height_mm - half_margin, pin_radius),
        ]

    for layer_idx in range(layers_count):
        # Layer threshold (0.0 for base, up to 0.85 for peak)
        threshold = (layer_idx / layers_count) * 0.85
        layer_contours = _extract_contours_for_threshold(
            hm, threshold, width_mm, height_mm
        )

        layer_data = {
            "layer_index": layer_idx,
            "layer_name": f"Calque {layer_idx + 1}/{layers_count}",
            "threshold": round(threshold, 2),
            "frame": {
                "x": 0.0,
                "y": 0.0,
                "width": width_mm,
                "height": height_mm,
            } if add_frame else None,
            "pin_holes": pins,
            "contours": layer_contours,
        }
        layers.append(layer_data)

    return layers


def topo_map_to_svg_layers(
    preset: str = "island",
    custom_image: Optional[Image.Image] = None,
    width_mm: float = 120.0,
    height_mm: float = 120.0,
    layers_count: int = 5,
    pin_diameter_mm: float = 3.0,
) -> Dict[str, str]:
    """
    Returns a dictionary of SVG documents { 'Layer_1': svg_str, ... }.
    """
    layers = generate_layered_topo_map(
        preset=preset,
        custom_image=custom_image,
        width_mm=width_mm,
        height_mm=height_mm,
        layers_count=layers_count,
        add_frame=True,
        pin_holes=True,
        pin_diameter_mm=pin_diameter_mm,
    )

    svg_dict = {}
    for layer in layers:
        idx = layer["layer_index"] + 1
        svg_lines = [
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{width_mm}mm" height="{height_mm}mm" '
            f'viewBox="0 0 {width_mm} {height_mm}">'
        ]

        # Outer frame
        if layer["frame"]:
            f = layer["frame"]
            svg_lines.append(
                f'  <rect x="{f["x"]}" y="{f["y"]}" width="{f["width"]}" height="{f["height"]}" '
                f'fill="none" stroke="#FF0000" stroke-width="0.3" />'
            )

        # Alignment Pins
        for px, py, pr in layer["pin_holes"]:
            svg_lines.append(
                f'  <circle cx="{px}" cy="{py}" r="{pr}" fill="none" stroke="#FF0000" stroke-width="0.2" />'
            )

        # Layer contours
        for poly in layer["contours"]:
            if len(poly) > 1:
                d = f"M {poly[0][0]} {poly[0][1]}"
                for pt in poly[1:]:
                    d += f" L {pt[0]} {pt[1]}"
                d += " Z"
                svg_lines.append(f'  <path d="{d}" fill="none" stroke="#0000FF" stroke-width="0.2" />')

        # Layer label text
        svg_lines.append(
            f'  <text x="{width_mm / 2.0}" y="{height_mm - 3.0}" font-size="3" text-anchor="middle" '
            f'fill="#000000">{layer["layer_name"]}</text>'
        )

        svg_lines.append("</svg>")
        svg_dict[f"Layer_{idx}"] = "\n".join(svg_lines)

    return svg_dict
