"""True-Shape 2D Nesting Optimizer.

Arranges multiple 2D parts/polygons onto a target material sheet
minimizing material waste with optional multi-angle rotations.
"""

from typing import List, Dict, Any, Tuple
import math


def pack_shapes_2d(
    items: List[Dict[str, Any]],
    sheet_w: float = 400.0,
    sheet_h: float = 300.0,
    margin: float = 5.0,
    spacing: float = 2.0,
    rotations: List[int] = None,
) -> Dict[str, Any]:
    """Pack rectangular or bounding-box shapes into sheet.

    items: list of dicts with 'id', 'w', 'h', 'name'
    Returns packing result with placed items, unplaced items, and utilization efficiency.
    """
    if rotations is None:
        rotations = [0, 90]

    # Sort largest items first (Max Area / Max Dimension heuristic)
    sorted_items = sorted(
        items,
        key=lambda item: item.get("w", 10.0) * item.get("h", 10.0),
        reverse=True
    )

    placed = []
    unplaced = []

    # Shelf / Guillotine 2D packing implementation
    curr_x = margin
    curr_y = margin
    curr_row_h = 0.0

    total_parts_area = 0.0

    for item in sorted_items:
        w_orig = float(item.get("w", 10.0))
        h_orig = float(item.get("h", 10.0))
        item_id = item.get("id", len(placed) + 1)
        name = item.get("name", f"Part_{item_id}")

        best_fit = None

        # Try orientations
        for rot in rotations:
            w, h = (h_orig, w_orig) if rot in (90, 270) else (w_orig, h_orig)

            # Check if fits in current row
            if curr_x + w + margin <= sheet_w and curr_y + h + margin <= sheet_h:
                best_fit = (curr_x, curr_y, w, h, rot)
                break
            # Check if fits in next row
            elif margin + w + margin <= sheet_w and curr_y + curr_row_h + spacing + h + margin <= sheet_h:
                next_x = margin
                next_y = curr_y + curr_row_h + spacing
                best_fit = (next_x, next_y, w, h, rot)
                break

        if best_fit:
            x, y, w, h, rot = best_fit
            if y > curr_y:
                curr_x = x
                curr_y = y
                curr_row_h = h
            else:
                curr_row_h = max(curr_row_h, h)

            placed.append({
                "id": item_id,
                "name": name,
                "x": round(x, 2),
                "y": round(y, 2),
                "w": round(w, 2),
                "h": round(h, 2),
                "rotation": rot,
            })

            total_parts_area += (w_orig * h_orig)
            curr_x += w + spacing
        else:
            unplaced.append(item)

    sheet_area = sheet_w * sheet_h
    efficiency_pct = (total_parts_area / sheet_area * 100.0) if sheet_area > 0 else 0.0

    return {
        "sheet": {"w": sheet_w, "h": sheet_h, "area": sheet_area},
        "placed": placed,
        "unplaced": unplaced,
        "efficiency_pct": round(efficiency_pct, 2),
        "total_placed": len(placed),
        "total_unplaced": len(unplaced),
    }
