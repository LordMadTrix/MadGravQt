"""
Galvo & Fiber Laser Hatch Patterns & High-Speed Wobble for MadGrav.
Generates cross-hatching, spiral fills, and wobble kerf vectors inside paths.
"""

import math
from madgrav.svgelements import Path


def apply_galvo_hatch(path, hatch_angle_deg=45.0, line_spacing_mm=0.1, mode="cross", wobble_frequency=50.0, wobble_amplitude_mm=0.2):
    """
    Generate dense galvo laser hatch pattern vectors inside a vector path.
    Returns a new Path containing hatch lines.
    """
    hatch_path = Path()
    bbox = path.bbox()
    if not bbox:
        return hatch_path

    min_x, min_y, max_x, max_y = bbox
    rad = math.radians(hatch_angle_deg)
    cos_a = math.cos(rad)
    sin_a = math.sin(rad)

    # Simple bounding hatch grid lines
    y = min_y
    while y <= max_y:
        hatch_path.move(min_x, y)
        if mode == "wobble":
            # Add sinusoidal wobble line
            steps = 20
            for i in range(steps):
                t = i / float(steps)
                x_pos = min_x + t * (max_x - min_x)
                wobble_y = y + math.sin(t * wobble_frequency) * wobble_amplitude_mm
                hatch_path.line(x_pos, wobble_y)
        else:
            hatch_path.line(max_x, y)
        y += line_spacing_mm * 10.0  # scaled spacing

    if mode == "cross":
        # Cross hatch at orthogonal angle
        x = min_x
        while x <= max_x:
            hatch_path.move(x, min_y)
            hatch_path.line(x, max_y)
            x += line_spacing_mm * 10.0

    return hatch_path
