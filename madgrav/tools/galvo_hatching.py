"""
Galvo & Fiber Laser Hatch Patterns & High-Speed Wobble for MadGrav.
Generates cross-hatching, spiral fills, and wobble kerf vectors inside paths.
"""

import math
from madgrav.svgelements import Path


def apply_galvo_hatch(path, hatch_angle_deg=45.0, line_spacing_mm=0.1, mode="cross", wobble_frequency=50.0, wobble_amplitude_mm=0.2):
    """
    Generate dense galvo laser hatch pattern vectors inside a vector path,
    rotated by hatch_angle_deg. Returns a new Path (in native document
    units) containing hatch lines.
    """
    from madgrav.core.units import UNITS_PER_MM

    hatch_path = Path()
    bbox = path.bbox()
    if not bbox:
        return hatch_path

    min_x, min_y, max_x, max_y = bbox
    step = line_spacing_mm * UNITS_PER_MM
    wobble_amplitude = wobble_amplitude_mm * UNITS_PER_MM

    cx = (min_x + max_x) / 2.0
    cy = (min_y + max_y) / 2.0
    # Hatch a square built from the ORIGINAL bbox's half-diagonal, not the
    # bbox itself -- large enough that after rotating by any angle it still
    # fully covers the original (unrotated) area, so hatch_angle_deg can't
    # leave uncovered corners.
    half_diag = math.hypot(max_x - min_x, max_y - min_y) / 2.0 or step
    hmin_x, hmax_x = cx - half_diag, cx + half_diag
    hmin_y, hmax_y = cy - half_diag, cy + half_diag

    rad = math.radians(hatch_angle_deg)
    cos_a, sin_a = math.cos(rad), math.sin(rad)

    def rot(x, y):
        # Path.move()/.line() take ONE point per positional arg (read as
        # points[index], not unpacked) -- passing x and y as two separate
        # scalars silently treats y as a SECOND point, collapsing the
        # whole shape's Y extent to 0. complex(x, y) is the point form
        # used elsewhere in this codebase (core/elements/shapes.py).
        dx, dy = x - cx, y - cy
        return complex(cx + dx * cos_a - dy * sin_a, cy + dx * sin_a + dy * cos_a)

    y = hmin_y
    while y <= hmax_y:
        hatch_path.move(rot(hmin_x, y))
        if mode == "wobble":
            # Add sinusoidal wobble line
            steps = 20
            for i in range(steps):
                t = i / float(steps)
                x_pos = hmin_x + t * (hmax_x - hmin_x)
                wobble_y = y + math.sin(t * wobble_frequency) * wobble_amplitude
                hatch_path.line(rot(x_pos, wobble_y))
        else:
            hatch_path.line(rot(hmax_x, y))
        y += step

    if mode == "cross":
        # Cross hatch at orthogonal angle
        x = hmin_x
        while x <= hmax_x:
            hatch_path.move(rot(x, hmin_y))
            hatch_path.line(rot(x, hmax_y))
            x += step

    return hatch_path
