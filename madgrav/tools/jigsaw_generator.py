"""
Jigsaw Puzzle Generator module for MadGrav.

Generates 2D vector jigsaw puzzle piece cutting lines with interlocking tabs and blanks,
matching laser cutting puzzle design tools.
"""

import math
import random
from madgrav.svgelements import Color, Matrix, Path


def generate_puzzle_tab(start_x, start_y, end_x, end_y, tab_dir=1.0, tab_size=0.2):
    """
    Generate a 2D bezier-curved interlocking puzzle tab between start and end points.

    :param start_x: Segment start X
    :param start_y: Segment start Y
    :param end_x: Segment end X
    :param end_y: Segment end Y
    :param tab_dir: 1.0 or -1.0 for tab pointing left/right or up/down
    :param tab_size: Relative tab size (0.1 to 0.3)
    :return: List of (x, y) points forming the curved tab
    """
    dx = end_x - start_x
    dy = end_y - start_y
    length = math.hypot(dx, dy)

    if length == 0:
        return [(start_x, start_y), (end_x, end_y)]

    ux, uy = dx / length, dy / length
    nx, ny = -uy * tab_dir, ux * tab_dir

    tab_h = length * tab_size
    tab_w = length * tab_size * 0.8

    # Key points along segment: 0%, 35%, 50%, 65%, 100%
    p0 = (start_x, start_y)
    p1 = (start_x + ux * length * 0.35, start_y + uy * length * 0.35)
    p2 = (start_x + ux * length * 0.40 + nx * tab_h * 0.5, start_y + uy * length * 0.40 + ny * tab_h * 0.5)
    p3 = (start_x + ux * length * 0.50 + nx * tab_h, start_y + uy * length * 0.50 + ny * tab_h)
    p4 = (start_x + ux * length * 0.60 + nx * tab_h * 0.5, start_y + uy * length * 0.60 + ny * tab_h * 0.5)
    p5 = (start_x + ux * length * 0.65, start_y + uy * length * 0.65)
    p6 = (end_x, end_y)

    return [p0, p1, p2, p3, p4, p5, p6]


def generate_jigsaw_puzzle(
    elements_service,
    width_mm: float = 200.0,
    height_mm: float = 150.0,
    rows: int = 4,
    cols: int = 6,
    tab_size_percent: float = 20.0,
    start_x_mm: float = 10.0,
    start_y_mm: float = 10.0,
):
    """
    Generate vector jigsaw puzzle cut lines and add them to the elements service.

    :param elements_service: The elements service (`kernel.elements`)
    :param width_mm: Overall puzzle width in mm
    :param height_mm: Overall puzzle height in mm
    :param rows: Number of puzzle rows
    :param cols: Number of puzzle columns
    :param tab_size_percent: Tab height percentage relative to piece size
    :param start_x_mm: Top-left X position in mm
    :param start_y_mm: Top-left Y position in mm
    :return: List of created PathNodes
    """
    from madgrav.core.units import UNITS_PER_MM

    cell_w = width_mm / float(cols)
    cell_h = height_mm / float(rows)
    tab_scale = tab_size_percent / 100.0

    puzzle_path = Path()

    # Outer border rectangle
    x0, y0 = 0.0, 0.0
    x1, y1 = width_mm, height_mm
    # Path.move()/.line() take ONE point per positional arg, not two
    # unpacked scalars -- same fix as barcode_generator.py's QR code bug.
    puzzle_path.move(complex(x0, y0))
    puzzle_path.line(complex(x1, y0))
    puzzle_path.line(complex(x1, y1))
    puzzle_path.line(complex(x0, y1))
    puzzle_path.closed()

    rnd = random.Random(42)  # Deterministic puzzle layout seed

    # Internal vertical cut lines
    for c in range(1, cols):
        x = c * cell_w
        for r in range(rows):
            y_start = r * cell_h
            y_end = (r + 1) * cell_h
            tab_dir = 1.0 if rnd.random() > 0.5 else -1.0
            pts = generate_puzzle_tab(x, y_start, x, y_end, tab_dir=tab_dir, tab_size=tab_scale)

            puzzle_path.move(complex(pts[0][0], pts[0][1]))
            for pt in pts[1:]:
                puzzle_path.line(complex(pt[0], pt[1]))

    # Internal horizontal cut lines
    for r in range(1, rows):
        y = r * cell_h
        for c in range(cols):
            x_start = c * cell_w
            x_end = (c + 1) * cell_w
            tab_dir = 1.0 if rnd.random() > 0.5 else -1.0
            pts = generate_puzzle_tab(x_start, y, x_end, y, tab_dir=tab_dir, tab_size=tab_scale)

            puzzle_path.move(complex(pts[0][0], pts[0][1]))
            for pt in pts[1:]:
                puzzle_path.line(complex(pt[0], pt[1]))

    # Transform to units and layout position
    M = Matrix.scale(UNITS_PER_MM)
    M.post_translate(start_x_mm * UNITS_PER_MM, start_y_mm * UNITS_PER_MM)
    puzzle_path = puzzle_path * M

    elements_branch = elements_service.elem_branch
    ops_branch = elements_service.op_branch

    op_node = ops_branch.add(
        type="op cut",
        color=Color("red"),
        label=f"Jigsaw Puzzle Cut ({cols}x{rows} pieces)",
    )

    elem_node = elements_branch.add(
        type="elem path",
        path=puzzle_path,
        stroke=Color("red"),
        stroke_width=100,
        label=f"Jigsaw Puzzle {cols}x{rows}",
    )
    # Same missing-bounds-recompute bug as gear_generator.py.
    elem_node.altered()
    op_node.add_reference(elem_node)

    elements_service.signal("tree_changed")
    elements_service.signal("refresh_scene")
    return [elem_node]
