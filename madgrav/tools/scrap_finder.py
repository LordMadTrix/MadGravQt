"""Scrap Material Finder for Laser Cutters.

Analyzes camera bed photos or thresholded images to identify free, usable scrap areas.
"""

from typing import List, Dict, Any, Tuple
import math


def find_usable_scrap_zones(
    image_width: int,
    image_height: int,
    bed_width_mm: float = 400.0,
    bed_height_mm: float = 300.0,
    cutout_rects: List[Tuple[float, float, float, float]] = None,
    min_area_mm2: float = 100.0,
) -> List[Dict[str, Any]]:
    """Compute available rectangular scrap / remnant zones on a sheet given already used cutout zones.

    cutout_rects: list of (x, y, w, h) in mm of cutouts.
    Returns list of free bounding zones with area and position.
    """
    if cutout_rects is None:
        cutout_rects = []

    # If no cutouts, entire bed is available
    if not cutout_rects:
        return [{
            "id": 1,
            "x": 0.0,
            "y": 0.0,
            "w": bed_width_mm,
            "h": bed_height_mm,
            "area_mm2": bed_width_mm * bed_height_mm,
            "is_scrap": False,
        }]

    zones = []
    # Grid subdivision approach to find largest contiguous empty rectangles
    cols = 20
    rows = 20
    cw = bed_width_mm / cols
    ch = bed_height_mm / rows

    grid = [[True for _ in range(cols)] for _ in range(rows)]

    # Mark occupied cells
    for rx, ry, rw, rh in cutout_rects:
        c_min = max(0, int(rx / cw))
        c_max = min(cols, int((rx + rw) / cw) + 1)
        r_min = max(0, int(ry / ch))
        r_max = min(rows, int((ry + rh) / ch) + 1)

        for r in range(r_min, r_max):
            for c in range(c_min, c_max):
                grid[r][c] = False

    # Find free continuous rectangles
    zone_id = 1
    visited = [[False for _ in range(cols)] for _ in range(rows)]

    for r in range(rows):
        for c in range(cols):
            if grid[r][c] and not visited[r][c]:
                # Expand rectangle
                r_end = r
                while r_end < rows and grid[r_end][c] and not visited[r_end][c]:
                    r_end += 1

                c_end = c
                all_valid = True
                while c_end < cols and all_valid:
                    for check_r in range(r, r_end):
                        if not grid[check_r][c_end] or visited[check_r][c_end]:
                            all_valid = False
                            break
                    if all_valid:
                        c_end += 1

                # Mark visited
                for vr in range(r, r_end):
                    for vc in range(c, c_end):
                        visited[vr][vc] = True

                x = c * cw
                y = r * ch
                w = (c_end - c) * cw
                h = (r_end - r) * ch
                area = w * h

                if area >= min_area_mm2:
                    zones.append({
                        "id": zone_id,
                        "x": round(x, 2),
                        "y": round(y, 2),
                        "w": round(w, 2),
                        "h": round(h, 2),
                        "area_mm2": round(area, 2),
                        "is_scrap": True,
                    })
                    zone_id += 1

    # Sort largest areas first
    zones.sort(key=lambda z: z["area_mm2"], reverse=True)
    return zones
