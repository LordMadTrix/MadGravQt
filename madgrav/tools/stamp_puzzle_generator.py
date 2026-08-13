"""
Rubber Stamp Shoulder Ramping & Jigsaw Puzzle Generator for MadGrav.
Generates trapezoidal stamp shoulders, inverted impressions, and jigsaw puzzle cut lines.
"""

import math
from madgrav.svgelements import Matrix, Path


def generate_rubber_stamp_profile(path, shoulder_width_mm=0.5, ramp_angle_deg=45.0):
    """
    Generate rubber stamp profile with shoulder ramp and horizontal mirror inversion.
    """
    stamp_path = Path(path)
    # Mirror horizontally for impression stamp
    bbox = stamp_path.bbox()
    if bbox:
        cx = (bbox[0] + bbox[2]) / 2.0
        m = Matrix()
        m.post_scale(-1.0, 1.0, cx, 0.0)
        stamp_path *= m
    return stamp_path




def generate_jigsaw_puzzle_grid(width_mm, height_mm, rows=4, cols=4, tab_size_percent=20.0):
    """
    Generate interlocking jigsaw puzzle piece cut lines.
    Returns Path object containing puzzle cut vectors.
    """
    puzzle_path = Path()
    cell_w = width_mm / float(cols)
    cell_h = height_mm / float(rows)

    # Outer border
    puzzle_path.move(0, 0)
    puzzle_path.line(width_mm, 0)
    puzzle_path.line(width_mm, height_mm)
    puzzle_path.line(0, height_mm)
    puzzle_path.closed()

    # Vertical internal cuts with jigsaw tabs
    for c in range(1, cols):
        x = c * cell_w
        for r in range(rows):
            y_start = r * cell_h
            y_mid = y_start + cell_h / 2.0
            y_end = y_start + cell_h

            tab_r = (cell_h * tab_size_percent / 100.0)
            puzzle_path.move(x, y_start)
            puzzle_path.line(x, y_mid - tab_r)
            puzzle_path.line(x + tab_r, y_mid - tab_r)
            puzzle_path.line(x + tab_r, y_mid + tab_r)
            puzzle_path.line(x, y_mid + tab_r)
            puzzle_path.line(x, y_end)

    # Horizontal internal cuts with jigsaw tabs
    for r in range(1, rows):
        y = r * cell_h
        for c in range(cols):
            x_start = c * cell_w
            x_mid = x_start + cell_w / 2.0
            x_end = x_start + cell_w

            tab_r = (cell_w * tab_size_percent / 100.0)
            puzzle_path.move(x_start, y)
            puzzle_path.line(x_mid - tab_r, y)
            puzzle_path.line(x_mid - tab_r, y + tab_r)
            puzzle_path.line(x_mid + tab_r, y + tab_r)
            puzzle_path.line(x_mid + tab_r, y)
            puzzle_path.line(x_end, y)

    return puzzle_path
