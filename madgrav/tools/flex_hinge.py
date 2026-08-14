"""
Parametric Living Hinge & Flex Cut Pattern Generator for MadGrav.
Generates flexible kerf cut lines for bending wood/plywood/MDF/acrylic.
"""

import math
from madgrav.svgelements import Path


def generate_living_hinge(width_mm, height_mm, pattern="straight", cut_length_mm=10.0, gap_length_mm=2.0, line_spacing_mm=1.5):
    """
    Generate parametric living hinge cut lines.
    Returns Path object (in native document units) containing all hinge cut vectors.
    """
    from madgrav.core.units import UNITS_PER_MM

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
            # complex(x, y) required -- two scalar args are read as two
            # separate points and collapse the Y extent to 0. Coordinates
            # are converted to native units here (same convention as
            # box_generator.py/gear_generator.py) so the returned Path
            # measures correctly once added to the document.
            path.move(complex(curr_x * UNITS_PER_MM, y * UNITS_PER_MM))

            if pattern == "wave":
                steps = 10
                for i in range(1, steps + 1):
                    t = i / float(steps)
                    cy = y + t * (cut_end - y)
                    cx = curr_x + math.sin(t * math.pi * 2) * (line_spacing_mm * 0.4)
                    path.line(complex(cx * UNITS_PER_MM, cy * UNITS_PER_MM))
            else:
                path.line(complex(curr_x * UNITS_PER_MM, cut_end * UNITS_PER_MM))

            y = cut_end + gap_length_mm

    return path
