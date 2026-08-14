"""
MadGrav Halftone & Photo Engraving Studio
Converts raster photos into vector dots, line waves, spirals, and stipples for laser engraving & cutting.
"""

from typing import List, Tuple, Union, Optional
import math
import numpy as np
from PIL import Image, ImageEnhance, ImageOps


def _preprocess_image(
    image: Image.Image,
    target_width_px: int,
    target_height_px: int,
    contrast: float = 0.0,
    brightness: float = 0.0,
    invert: bool = False,
) -> np.ndarray:
    """Preprocesses a PIL Image to a normalized 2D grayscale numpy array (0.0=black, 1.0=white)."""
    img = image.convert("L")
    if target_width_px > 0 and target_height_px > 0:
        img = img.resize((max(1, int(target_width_px)), max(1, int(target_height_px))), Image.Resampling.BILINEAR)

    if contrast != 0.0:
        enhancer = ImageEnhance.Contrast(img)
        img = enhancer.enhance(max(0.1, 1.0 + (contrast / 100.0)))

    if brightness != 0.0:
        enhancer = ImageEnhance.Brightness(img)
        img = enhancer.enhance(max(0.1, 1.0 + (brightness / 100.0)))

    if invert:
        img = ImageOps.invert(img)

    arr = np.array(img, dtype=np.float32) / 255.0
    return arr


def generate_halftone_dots(
    image: Image.Image,
    width_mm: float = 100.0,
    height_mm: float = 100.0,
    pitch_mm: float = 2.5,
    min_dot_mm: float = 0.2,
    max_dot_mm: float = 2.2,
    angle_deg: float = 45.0,
    contrast: float = 0.0,
    brightness: float = 0.0,
    invert: bool = False,
) -> List[Tuple[float, float, float]]:
    """
    Generates a list of circles (cx, cy, radius) in mm based on image luminance.
    Darker areas produce larger circles (or vice-versa if invert is True).
    """
    if pitch_mm <= 0.1:
        pitch_mm = 0.1

    cols = max(2, int(math.ceil(width_mm / pitch_mm)))
    rows = max(2, int(math.ceil(height_mm / pitch_mm)))

    arr = _preprocess_image(image, cols, rows, contrast, brightness, invert)
    arr_h, arr_w = arr.shape

    dots = []
    rad_angle = math.radians(angle_deg)
    cos_a = math.cos(rad_angle)
    sin_a = math.sin(rad_angle)
    cx_grid = width_mm / 2.0
    cy_grid = height_mm / 2.0

    for r in range(rows):
        y_norm = (r + 0.5) / rows
        y_mm = y_norm * height_mm
        img_y = min(arr_h - 1, max(0, int(y_norm * arr_h)))

        for c in range(cols):
            x_norm = (c + 0.5) / cols
            x_mm = x_norm * width_mm
            img_x = min(arr_w - 1, max(0, int(x_norm * arr_w)))

            lum = float(arr[img_y, img_x])
            # Darkness factor (0.0 = bright/small dot, 1.0 = dark/large dot)
            darkness = 1.0 - lum

            if darkness <= 0.01:
                continue

            radius_mm = min_dot_mm + darkness * (max_dot_mm - min_dot_mm) / 2.0
            if radius_mm <= 0.05:
                continue

            # Apply rotation around center if angle != 0
            if angle_deg != 0.0:
                dx = x_mm - cx_grid
                dy = y_mm - cy_grid
                rx = cx_grid + (dx * cos_a - dy * sin_a)
                ry = cy_grid + (dx * sin_a + dy * cos_a)
                # Keep within bounding box if desired
                if 0.0 <= rx <= width_mm and 0.0 <= ry <= height_mm:
                    dots.append((round(rx, 3), round(ry, 3), round(radius_mm, 3)))
            else:
                dots.append((round(x_mm, 3), round(y_mm, 3), round(radius_mm, 3)))

    return dots


def generate_line_wave_halftone(
    image: Image.Image,
    width_mm: float = 100.0,
    height_mm: float = 100.0,
    line_spacing_mm: float = 2.0,
    max_amplitude_mm: float = 1.2,
    frequency: float = 3.0,
    samples_per_line: int = 150,
    contrast: float = 0.0,
    brightness: float = 0.0,
    invert: bool = False,
) -> List[List[Tuple[float, float]]]:
    """
    Generates modulated sine-wave polylines where amplitude modulates with image darkness.
    """
    lines_count = max(2, int(math.ceil(height_mm / line_spacing_mm)))
    arr = _preprocess_image(image, samples_per_line, lines_count, contrast, brightness, invert)
    arr_h, arr_w = arr.shape

    polylines = []
    for line_idx in range(lines_count):
        y_base = (line_idx + 0.5) * line_spacing_mm
        img_y = min(arr_h - 1, max(0, int((line_idx / lines_count) * arr_h)))

        pts = []
        for s in range(samples_per_line):
            x_norm = s / (samples_per_line - 1)
            x_mm = x_norm * width_mm
            img_x = min(arr_w - 1, max(0, int(x_norm * arr_w)))

            lum = float(arr[img_y, img_x])
            darkness = 1.0 - lum

            phase = x_norm * math.pi * 2.0 * frequency * (lines_count / 10.0)
            offset_y = math.sin(phase) * (darkness * max_amplitude_mm)
            pts.append((round(x_mm, 3), round(y_base + offset_y, 3)))

        polylines.append(pts)

    return polylines


def generate_spiral_halftone(
    image: Image.Image,
    diameter_mm: float = 100.0,
    ring_spacing_mm: float = 2.0,
    max_dot_mm: float = 3.0,
    contrast: float = 0.0,
    brightness: float = 0.0,
    invert: bool = False,
) -> List[Tuple[float, float, float]]:
    """
    Generates an Archimedean spiral with modulated dot radii along the spiral arm.
    """
    radius_max = diameter_mm / 2.0
    cx = radius_max
    cy = radius_max
    turns = max(2, int(radius_max / ring_spacing_mm))

    arr = _preprocess_image(image, 300, 300, contrast, brightness, invert)
    arr_h, arr_w = arr.shape

    dots = []
    total_steps = turns * 100
    for step in range(1, total_steps):
        theta = step * 0.1
        r = (theta / (total_steps * 0.1)) * radius_max
        if r > radius_max:
            break

        x = cx + r * math.cos(theta)
        y = cy + r * math.sin(theta)

        # Sample pixel
        norm_x = max(0.0, min(1.0, x / diameter_mm))
        norm_y = max(0.0, min(1.0, y / diameter_mm))
        img_x = min(arr_w - 1, max(0, int(norm_x * arr_w)))
        img_y = min(arr_h - 1, max(0, int(norm_y * arr_h)))

        darkness = 1.0 - float(arr[img_y, img_x])
        if darkness > 0.05:
            dot_r = (darkness * max_dot_mm) / 2.0
            dots.append((round(x, 3), round(y, 3), round(dot_r, 3)))

    return dots


def generate_stipple_halftone(
    image: Image.Image,
    width_mm: float = 100.0,
    height_mm: float = 100.0,
    point_count: int = 1500,
    dot_diameter_mm: float = 0.8,
    contrast: float = 0.0,
    brightness: float = 0.0,
    invert: bool = False,
) -> List[Tuple[float, float, float]]:
    """
    Generates density-weighted random stipple dots.
    """
    arr = _preprocess_image(image, 200, 200, contrast, brightness, invert)
    arr_h, arr_w = arr.shape
    darkness_map = 1.0 - arr

    # Rejection sampling
    stipples = []
    rng = np.random.RandomState(42)
    max_attempts = point_count * 20
    attempts = 0

    radius = dot_diameter_mm / 2.0

    while len(stipples) < point_count and attempts < max_attempts:
        attempts += 1
        rx = rng.uniform(0.0, 1.0)
        ry = rng.uniform(0.0, 1.0)
        img_x = min(arr_w - 1, int(rx * arr_w))
        img_y = min(arr_h - 1, int(ry * arr_h))

        prob = float(darkness_map[img_y, img_x])
        if rng.uniform(0.0, 1.0) <= prob:
            x_mm = rx * width_mm
            y_mm = ry * height_mm
            stipples.append((round(x_mm, 3), round(y_mm, 3), round(radius, 3)))

    return stipples


def generate_halftone_job(
    image: Image.Image,
    method: str = "dots",
    width_mm: float = 100.0,
    height_mm: float = 100.0,
    pitch_mm: float = 2.5,
    min_dot_mm: float = 0.2,
    max_dot_mm: float = 2.2,
    angle_deg: float = 45.0,
    contrast: float = 0.0,
    brightness: float = 0.0,
    invert: bool = False,
) -> str:
    """
    Generates an SVG string representation of the halftone artwork.
    """
    svg_elements = []
    svg_elements.append(
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width_mm}mm" height="{height_mm}mm" '
        f'viewBox="0 0 {width_mm} {height_mm}">'
    )

    if method == "waves":
        waves = generate_line_wave_halftone(
            image, width_mm, height_mm, pitch_mm, max_amplitude_mm=pitch_mm * 0.6,
            contrast=contrast, brightness=brightness, invert=invert
        )
        for wave in waves:
            if not wave:
                continue
            path_d = f"M {wave[0][0]} {wave[0][1]}"
            for pt in wave[1:]:
                path_d += f" L {pt[0]} {pt[1]}"
            svg_elements.append(f'  <path d="{path_d}" fill="none" stroke="#000000" stroke-width="0.2" />')

    elif method == "spiral":
        diameter = min(width_mm, height_mm)
        spiral_dots = generate_spiral_halftone(
            image, diameter_mm=diameter, ring_spacing_mm=pitch_mm, max_dot_mm=max_dot_mm,
            contrast=contrast, brightness=brightness, invert=invert
        )
        for cx, cy, r in spiral_dots:
            svg_elements.append(f'  <circle cx="{cx}" cy="{cy}" r="{r}" fill="#000000" stroke="none" />')

    elif method == "stipple":
        stipples = generate_stipple_halftone(
            image, width_mm, height_mm, point_count=int((width_mm * height_mm) / (pitch_mm * pitch_mm)),
            dot_diameter_mm=min_dot_mm * 2.0, contrast=contrast, brightness=brightness, invert=invert
        )
        for cx, cy, r in stipples:
            svg_elements.append(f'  <circle cx="{cx}" cy="{cy}" r="{r}" fill="#000000" stroke="none" />')

    else:  # "dots"
        dots = generate_halftone_dots(
            image, width_mm, height_mm, pitch_mm, min_dot_mm, max_dot_mm, angle_deg,
            contrast, brightness, invert
        )
        for cx, cy, r in dots:
            svg_elements.append(f'  <circle cx="{cx}" cy="{cy}" r="{r}" fill="#000000" stroke="none" />')

    svg_elements.append("</svg>")
    return "\n".join(svg_elements)
