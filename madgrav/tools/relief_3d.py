"""
3D Grayscale Laser Relief & Depth Raster Engine for MadGrav.
Converts grayscale image heightmaps to variable laser power raster scans.
"""

import numpy as np


def generate_3d_laser_relief(image_np, max_power_percent=100.0, min_power_percent=10.0, invert=False, passes=1):
    """
    Generate 3D grayscale laser raster lines from a heightmap image array.
    Returns dict containing raster scan commands and power statistics.
    """
    if image_np is None or image_np.size == 0:
        return {"scan_lines": [], "max_s": 0.0, "min_s": 0.0}

    if len(image_np.shape) == 3:
        # RGB to Grayscale
        gray = np.mean(image_np, axis=2).astype(np.float32)
    else:
        gray = image_np.astype(np.float32)

    if invert:
        gray = 255.0 - gray

    # Map luminance 0..255 to min_power..max_power
    power_range = max_power_percent - min_power_percent
    power_map = min_power_percent + (gray / 255.0) * power_range

    h, w = gray.shape
    scan_lines = []

    for y in range(h):
        line_powers = power_map[y, :].tolist()
        scan_lines.append({
            "y": y,
            "direction": 1 if y % 2 == 0 else -1,
            "powers": line_powers
        })

    return {
        "scan_lines": scan_lines,
        "width": w,
        "height": h,
        "max_s": float(np.max(power_map)),
        "min_s": float(np.min(power_map)),
        "passes": passes
    }
