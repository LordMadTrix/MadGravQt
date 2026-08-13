"""
Parametric Living Hinge & Flex Cut Pattern Generator for MadGrav.
Generates flexible kerf cut lines for bending wood/plywood/MDF/acrylic.
"""

import math
from madgrav.svgelements import Path


def generate_living_hinge(width_mm, height_mm, pattern="straight", cut_length_mm=10.0, gap_length_mm=2.0, line_spacing_mm=1.5):
    """
    Generate parametric living hinge cut lines.
    Returns Path object containing all hinge cut vectors.
    """
    path = Path()

    x = line_spacing_mm
    row_count = int(width_mm / line_spacing_mm)

    for r in range(row_count):
        curr_x = x + r * line_spacing_mm
        if curr_x >= width_mm:
            break

        is_offset = (r % 2 == 1)
        y = gap_length_mm / 2.0 if is_offset else 0.0

        while y < height_mm:
            cut_end = min(y + cut_length_mm, height_mm)
            path.move(curr_x, y)

            if pattern == "wave":
                steps = 10
                for i in range(1, steps + 1):
                    t = i / float(steps)
                    cy = y + t * (cut_end - y)
                    cx = curr_x + math.sin(t * math.pi * 2) * (line_spacing_mm * 0.4)
                    path.line(cx, cy)
            else:
                path.line(curr_x, cut_end)

            y = cut_end + gap_length_mm

    return path
