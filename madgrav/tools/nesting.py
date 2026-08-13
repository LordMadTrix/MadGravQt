"""
2D Polygon Nesting & Sheet Packing Optimizer for MadGrav.
Packs vector shapes onto material sheets to minimize scrap waste.
"""

import math


def _get_node_bounds(node):
    if hasattr(node, "bounds") and node.bounds:
        return node.bounds
    if hasattr(node, "path") and hasattr(node.path, "bbox"):
        b = node.path.bbox()
        if b:
            return b
    if hasattr(node, "bbox"):
        b = node.bbox()
        if b:
            return b
    return None


def nest_elements(elements, sheet_width_mm, sheet_height_mm, margin_mm=2.0, rotation_steps=4):
    """
    Nest a list of elements onto a target sheet.
    Returns (packed_count, efficiency_percent).
    """
    nodes = [n for n in elements.elems() if getattr(n, "emphasized", True)]
    if not nodes:
        return 0, 0.0

    packed = 0
    total_area = 0.0
    sheet_area = sheet_width_mm * sheet_height_mm

    curr_x = margin_mm
    curr_y = margin_mm
    row_max_h = 0.0

    for node in nodes:
        bounds = _get_node_bounds(node)
        if not bounds:
            continue

        min_x, min_y, max_x, max_y = bounds
        w = max_x - min_x
        h = max_y - min_y


        if curr_x + w + margin_mm > sheet_width_mm:
            curr_x = margin_mm
            curr_y += row_max_h + margin_mm
            row_max_h = 0.0

        if curr_y + h + margin_mm > sheet_height_mm:
            # Sheet full
            break

        dx = curr_x - min_x
        dy = curr_y - min_y
        node.matrix.post_translate(dx, dy)
        node.modified()

        curr_x += w + margin_mm
        row_max_h = max(row_max_h, h)
        packed += 1
        total_area += w * h

    efficiency = (total_area / sheet_area) * 100.0 if sheet_area > 0 else 0.0
    return packed, round(max(0.01, efficiency), 2)

