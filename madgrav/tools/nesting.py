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


def _rotated_bbox_width(bounds, angle_rad):
    """Width of the axis-aligned bbox of `bounds`' 4 corners after
    rotating them by angle_rad around the bbox's own center -- a cheap
    analytic estimate used only to CHOOSE the best trial angle, without
    mutating the node once per candidate."""
    min_x, min_y, max_x, max_y = bounds
    cx = (min_x + max_x) / 2.0
    cy = (min_y + max_y) / 2.0
    cos_a, sin_a = math.cos(angle_rad), math.sin(angle_rad)
    xs = []
    for x, y in ((min_x, min_y), (max_x, min_y), (max_x, max_y), (min_x, max_y)):
        dx, dy = x - cx, y - cy
        xs.append(cx + dx * cos_a - dy * sin_a)
    return max(xs) - min(xs)


def nest_elements(elements, sheet_width_mm, sheet_height_mm, margin_mm=2.0, rotation_steps=1):
    """
    Nest a list of elements onto a target sheet.

    rotation_steps=1 (default) never rotates a piece, matching every
    caller written before this parameter did anything. rotation_steps=N>1
    tries N evenly-spaced orientations per piece and keeps whichever is
    narrowest, packing tighter at the cost of possibly rotating the
    piece's on-bed orientation (skip this for text/engravings where
    orientation matters).

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

        if rotation_steps > 1:
            best_angle = 0.0
            best_width = bounds[2] - bounds[0]
            for i in range(1, rotation_steps):
                angle = i * (2.0 * math.pi / rotation_steps)
                width = _rotated_bbox_width(bounds, angle)
                if width < best_width:
                    best_width, best_angle = width, angle
            if best_angle != 0.0:
                min_x, min_y, max_x, max_y = bounds
                cx = (min_x + max_x) / 2.0
                cy = (min_y + max_y) / 2.0
                node.matrix.post_rotate(best_angle, cx, cy)
                node.modified()
                bounds = node.bounds

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

