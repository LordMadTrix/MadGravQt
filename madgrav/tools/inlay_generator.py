"""Inlay & Marquetry path generator for laser cutting.

Computes kerf and clearance compensated toolpaths for male (insert)
and female (pocket) inlay pieces.
"""

from typing import List, Tuple, Dict, Any
import math


def offset_polygon(points: List[Tuple[float, float]], offset_distance: float) -> List[Tuple[float, float]]:
    """Offset a simple polygon by an offset distance (positive = expand, negative = shrink).
    
    Uses vertex normal bisector offset.
    """
    n = len(points)
    if n < 3:
        return points

    # Check if closed
    is_closed = (points[0] == points[-1])
    pts = points[:-1] if is_closed else list(points)
    num_pts = len(pts)

    new_pts = []
    for i in range(num_pts):
        p_prev = pts[(i - 1 + num_pts) % num_pts]
        p_curr = pts[i]
        p_next = pts[(i + 1) % num_pts]

        # Inward/outward normal vectors for the two adjacent segments
        dx1, dy1 = p_curr[0] - p_prev[0], p_curr[1] - p_prev[1]
        len1 = math.hypot(dx1, dy1) or 1.0
        n1 = (-dy1 / len1, dx1 / len1)

        dx2, dy2 = p_next[0] - p_curr[0], p_next[1] - p_curr[1]
        len2 = math.hypot(dx2, dy2) or 1.0
        n2 = (-dy2 / len2, dx2 / len2)

        # Average normal
        bisector = (n1[0] + n2[0], n1[1] + n2[1])
        b_len = math.hypot(bisector[0], bisector[1])
        if b_len < 1e-4:
            # Opposite normals, use perpendicular
            bisector = n1
            b_len = 1.0

        scale = 1.0 + (n1[0] * n2[0] + n1[1] * n2[1])
        if scale > 0.05:
            # miter limit
            miter_len = min(abs(offset_distance) * 3.0, abs(offset_distance) / math.sqrt(scale / 2.0))
            if offset_distance < 0:
                miter_len = -miter_len
        else:
            miter_len = offset_distance

        nx = bisector[0] / b_len * miter_len
        ny = bisector[1] / b_len * miter_len

        new_pts.append((p_curr[0] + nx, p_curr[1] + ny))

    if is_closed:
        new_pts.append(new_pts[0])

    return new_pts


def generate_inlay_paths(
    shape_points: List[Tuple[float, float]],
    kerf_mm: float = 0.15,
    clearance_mm: float = 0.05,
    mode: str = "balanced"  # 'balanced', 'male_only', 'female_only'
) -> Dict[str, Any]:
    """Generate kerf & clearance compensated toolpaths for Inlay / Marquetry.

    Returns dictionary with 'male_path', 'female_path', 'kerf_applied', 'clearance_applied'.
    """
    half_kerf = kerf_mm / 2.0
    half_clearance = clearance_mm / 2.0

    if mode == "balanced":
        # Male (outer piece) is expanded by half kerf, shrunk by half clearance
        male_offset = (half_kerf - half_clearance)
        # Female (pocket) is shrunk by half kerf, expanded by half clearance
        female_offset = (-half_kerf + half_clearance)
    elif mode == "male_only":
        male_offset = kerf_mm - clearance_mm
        female_offset = 0.0
    else:  # female_only
        male_offset = 0.0
        female_offset = -kerf_mm + clearance_mm

    male_path = offset_polygon(shape_points, male_offset)
    female_path = offset_polygon(shape_points, female_offset)

    return {
        "male_path": male_path,
        "female_path": female_path,
        "kerf_mm": kerf_mm,
        "clearance_mm": clearance_mm,
        "mode": mode
    }
