"""Material Test Matrix Generator Pro.

Generates structured parametric test grids (power vs speed vs passes)
with engraved labels for laser parameter calibration.
"""

from typing import List, Dict, Any


def generate_material_test_matrix_data(
    speeds: List[float] = None,
    powers: List[float] = None,
    cell_w: float = 12.0,
    cell_h: float = 12.0,
    gap: float = 3.0,
    origin_x: float = 10.0,
    origin_y: float = 10.0,
) -> Dict[str, Any]:
    """Generate layout and cell parameters for a laser material test matrix."""
    if speeds is None:
        speeds = [10.0, 20.0, 50.0, 100.0, 200.0]
    if powers is None:
        powers = [20.0, 40.0, 60.0, 80.0, 100.0]

    cells = []
    labels = []

    # Label offset
    label_margin = 15.0
    start_x = origin_x + label_margin
    start_y = origin_y + label_margin

    # Generate column labels (Speed)
    for col_idx, spd in enumerate(speeds):
        cx = start_x + col_idx * (cell_w + gap)
        labels.append({
            "text": f"{int(spd)}mm/s",
            "x": cx + cell_w / 2.0,
            "y": origin_y + 8.0,
            "align": "center",
            "type": "speed_header"
        })

    # Generate row labels (Power) & Cells
    for row_idx, pwr in enumerate(powers):
        cy = start_y + row_idx * (cell_h + gap)

        # Row label
        labels.append({
            "text": f"{int(pwr)}%",
            "x": origin_x + 5.0,
            "y": cy + cell_h / 2.0 + 3.0,
            "align": "right",
            "type": "power_header"
        })

        for col_idx, spd in enumerate(speeds):
            cx = start_x + col_idx * (cell_w + gap)
            cells.append({
                "col": col_idx,
                "row": row_idx,
                "x": round(cx, 2),
                "y": round(cy, 2),
                "w": cell_w,
                "h": cell_h,
                "speed": spd,
                "power": pwr,
            })

    total_w = start_x + len(speeds) * (cell_w + gap) + 10.0
    total_h = start_y + len(powers) * (cell_h + gap) + 10.0

    return {
        "speeds": speeds,
        "powers": powers,
        "cell_w": cell_w,
        "cell_h": cell_h,
        "cells": cells,
        "labels": labels,
        "total_width": round(total_w, 2),
        "total_height": round(total_h, 2),
    }
