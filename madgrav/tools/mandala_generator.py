"""
MadGrav Radial Mandala & Sacred Geometry Generator
Procedural vector generation for floral, starburst, sacred geometry, and gothic rosettes.
"""

from typing import List, Tuple, Dict, Any, Optional
import math


def _rotate_point(x: float, y: float, angle_rad: float, cx: float = 0.0, cy: float = 0.0) -> Tuple[float, float]:
    """Rotates a point (x, y) around center (cx, cy) by angle_rad radians."""
    dx = x - cx
    dy = y - cy
    cos_a = math.cos(angle_rad)
    sin_a = math.sin(angle_rad)
    rx = cx + (dx * cos_a - dy * sin_a)
    ry = cy + (dx * sin_a + dy * cos_a)
    return round(rx, 3), round(ry, 3)


def generate_mandala_paths(
    symmetry: int = 8,
    outer_radius_mm: float = 50.0,
    inner_radius_mm: float = 5.0,
    rings: int = 4,
    style: str = "floral",
    center_x_mm: Optional[float] = None,
    center_y_mm: Optional[float] = None,
) -> List[List[Tuple[float, float]]]:
    """
    Generates a list of 2D polygon paths (loops) with K-fold radial symmetry.
    Styles: "floral", "starburst", "sacred", "gothic"
    """
    symmetry = max(3, min(64, int(symmetry)))
    rings = max(1, min(12, int(rings)))

    cx = outer_radius_mm if center_x_mm is None else center_x_mm
    cy = outer_radius_mm if center_y_mm is None else center_y_mm

    sector_angle = (2.0 * math.pi) / symmetry
    radius_step = (outer_radius_mm - inner_radius_mm) / rings

    all_paths = []

    # Central inner circle
    inner_circle = []
    for s in range(36):
        a = (s / 36.0) * 2.0 * math.pi
        px = cx + inner_radius_mm * math.cos(a)
        py = cy + inner_radius_mm * math.sin(a)
        inner_circle.append((round(px, 3), round(py, 3)))
    inner_circle.append(inner_circle[0])
    all_paths.append(inner_circle)

    # Generate concentric rings of petals / motifs
    for r_idx in range(rings):
        r_inner = inner_radius_mm + r_idx * radius_step
        r_outer = r_inner + radius_step
        r_mid = (r_inner + r_outer) / 2.0

        # Base petal in sector 0
        base_petal = []
        if style == "floral":
            # Curved teardrop/petal
            base_petal = [
                (cx + r_inner * math.cos(0.0), cy + r_inner * math.sin(0.0)),
                (cx + r_mid * math.cos(sector_angle * 0.35), cy + r_mid * math.sin(sector_angle * 0.35)),
                (cx + r_outer * math.cos(sector_angle * 0.5), cy + r_outer * math.sin(sector_angle * 0.5)),
                (cx + r_mid * math.cos(sector_angle * 0.65), cy + r_mid * math.sin(sector_angle * 0.65)),
                (cx + r_inner * math.cos(sector_angle), cy + r_inner * math.sin(sector_angle)),
                (cx + r_inner * math.cos(0.0), cy + r_inner * math.sin(0.0)),
            ]
        elif style == "starburst":
            # Pointed sharp star triangle
            base_petal = [
                (cx + r_inner * math.cos(0.0), cy + r_inner * math.sin(0.0)),
                (cx + r_outer * math.cos(sector_angle * 0.5), cy + r_outer * math.sin(sector_angle * 0.5)),
                (cx + r_inner * math.cos(sector_angle), cy + r_inner * math.sin(sector_angle)),
                (cx + (r_inner + radius_step * 0.2) * math.cos(sector_angle * 0.5),
                 cy + (r_inner + radius_step * 0.2) * math.sin(sector_angle * 0.5)),
                (cx + r_inner * math.cos(0.0), cy + r_inner * math.sin(0.0)),
            ]
        elif style == "gothic":
            # Trefoil / Gothic window arc loop
            half_a = sector_angle * 0.5
            base_petal = [
                (cx + r_inner * math.cos(0.0), cy + r_inner * math.sin(0.0)),
                (cx + r_outer * math.cos(half_a * 0.5), cy + r_outer * math.sin(half_a * 0.5)),
                (cx + (r_outer * 1.05) * math.cos(half_a), cy + (r_outer * 1.05) * math.sin(half_a)),
                (cx + r_outer * math.cos(half_a * 1.5), cy + r_outer * math.sin(half_a * 1.5)),
                (cx + r_inner * math.cos(sector_angle), cy + r_inner * math.sin(sector_angle)),
                (cx + r_inner * math.cos(0.0), cy + r_inner * math.sin(0.0)),
            ]
        else:  # "sacred" (Sacred Geometry interlaced circles / Seed of Life arcs)
            steps = 12
            for s in range(steps + 1):
                t = s / steps
                a = t * sector_angle
                r_var = r_inner + (r_outer - r_inner) * math.sin(t * math.pi)
                base_petal.append((cx + r_var * math.cos(a), cy + r_var * math.sin(a)))
            base_petal.append((cx + r_inner * math.cos(0.0), cy + r_inner * math.sin(0.0)))

        # Replicate base petal around all symmetry sectors
        for k in range(symmetry):
            rot_angle = k * sector_angle
            rotated_petal = []
            for px, py in base_petal:
                rx, ry = _rotate_point(px, py, rot_angle, cx, cy)
                rotated_petal.append((rx, ry))
            all_paths.append(rotated_petal)

        # Concentric dividing ring loop
        ring_poly = []
        for s in range(symmetry * 4):
            a = (s / (symmetry * 4.0)) * 2.0 * math.pi
            ring_poly.append((round(cx + r_outer * math.cos(a), 3), round(cy + r_outer * math.sin(a), 3)))
        ring_poly.append(ring_poly[0])
        all_paths.append(ring_poly)

    return all_paths


def generate_mandala_svg(
    symmetry: int = 8,
    outer_radius_mm: float = 50.0,
    inner_radius_mm: float = 5.0,
    rings: int = 4,
    style: str = "floral",
) -> str:
    """
    Generates a standalone SVG string of the mandala.
    """
    diameter = outer_radius_mm * 2.0 + 10.0
    cx = diameter / 2.0
    cy = diameter / 2.0

    paths = generate_mandala_paths(
        symmetry=symmetry,
        outer_radius_mm=outer_radius_mm,
        inner_radius_mm=inner_radius_mm,
        rings=rings,
        style=style,
        center_x_mm=cx,
        center_y_mm=cy,
    )

    svg_lines = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{diameter}mm" height="{diameter}mm" '
        f'viewBox="0 0 {diameter} {diameter}">'
    ]

    for path in paths:
        if not path:
            continue
        d = f"M {path[0][0]} {path[0][1]}"
        for pt in path[1:]:
            d += f" L {pt[0]} {pt[1]}"
        d += " Z"
        svg_lines.append(f'  <path d="{d}" fill="none" stroke="#000000" stroke-width="0.3" />')

    svg_lines.append("</svg>")
    return "\n".join(svg_lines)
