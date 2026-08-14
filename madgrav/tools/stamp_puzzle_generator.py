"""
Rubber Stamp Shoulder Ramping & Jigsaw Puzzle Generator for MadGrav.
Generates trapezoidal stamp shoulders, inverted impressions, and jigsaw puzzle cut lines.
"""

from madgrav.svgelements import Matrix, Path


def generate_rubber_stamp_profile(path, shoulder_width_mm=0.5, ramp_angle_deg=45.0):
    """
    Generate rubber stamp profile with shoulder ramp and horizontal mirror inversion.

    The mirrored outline is the printing edge; shoulder_width_mm/
    ramp_angle_deg add concentric step-offset rings around it (reusing
    kerf_lead.apply_kerf_offset) approximating the beveled support ramp
    real stamp-making cuts as multiple outward passes at increasing
    power/depth. A steeper ramp_angle_deg needs fewer, coarser steps to
    reach the same total width; a shallow angle needs more, finer ones
    for a gentler support slope.
    """
    from madgrav.tools.kerf_lead import apply_kerf_offset

    base_path = Path(path)
    # Mirror horizontally for impression stamp
    bbox = base_path.bbox()
    if bbox:
        cx = (bbox[0] + bbox[2]) / 2.0
        m = Matrix()
        m.post_scale(-1.0, 1.0, cx, 0.0)
        base_path *= m

    stamp_path = Path(base_path)

    if shoulder_width_mm > 0:
        if ramp_angle_deg >= 60.0:
            num_steps = 2
        elif ramp_angle_deg >= 30.0:
            num_steps = 3
        else:
            num_steps = 5

        step_width = shoulder_width_mm / num_steps
        for i in range(1, num_steps + 1):
            # mode="inner", not "outer" -- apply_kerf_offset's outer/inner
            # is winding-direction-dependent, and the horizontal mirror
            # just above always REVERSES base_path's winding order (any
            # mirror is orientation-reversing), so "outer" would actually
            # offset INWARD here (confirmed empirically: shrank the bbox
            # instead of growing it). "inner" is the one that grows
            # outward for this specific already-mirrored path.
            ring = apply_kerf_offset(base_path, kerf_mm=step_width * i, mode="inner")
            stamp_path.extend(ring)

    return stamp_path




def generate_jigsaw_puzzle_grid(width_mm, height_mm, rows=4, cols=4, tab_size_percent=20.0):
    """
    Generate interlocking jigsaw puzzle piece cut lines.
    Returns Path object containing puzzle cut vectors.
    """
    puzzle_path = Path()
    cell_w = width_mm / float(cols)
    cell_h = height_mm / float(rows)

    # Outer border.
    # complex(x, y) required -- two scalar args are read as two separate
    # points and collapse the shape's Y extent to 0.
    puzzle_path.move(complex(0, 0))
    puzzle_path.line(complex(width_mm, 0))
    puzzle_path.line(complex(width_mm, height_mm))
    puzzle_path.line(complex(0, height_mm))
    puzzle_path.closed()

    # Vertical internal cuts with jigsaw tabs
    for c in range(1, cols):
        x = c * cell_w
        for r in range(rows):
            y_start = r * cell_h
            y_mid = y_start + cell_h / 2.0
            y_end = y_start + cell_h

            tab_r = (cell_h * tab_size_percent / 100.0)
            puzzle_path.move(complex(x, y_start))
            puzzle_path.line(complex(x, y_mid - tab_r))
            puzzle_path.line(complex(x + tab_r, y_mid - tab_r))
            puzzle_path.line(complex(x + tab_r, y_mid + tab_r))
            puzzle_path.line(complex(x, y_mid + tab_r))
            puzzle_path.line(complex(x, y_end))

    # Horizontal internal cuts with jigsaw tabs
    for r in range(1, rows):
        y = r * cell_h
        for c in range(cols):
            x_start = c * cell_w
            x_mid = x_start + cell_w / 2.0
            x_end = x_start + cell_w

            tab_r = (cell_w * tab_size_percent / 100.0)
            puzzle_path.move(complex(x_start, y))
            puzzle_path.line(complex(x_mid - tab_r, y))
            puzzle_path.line(complex(x_mid - tab_r, y + tab_r))
            puzzle_path.line(complex(x_mid + tab_r, y + tab_r))
            puzzle_path.line(complex(x_mid + tab_r, y))
            puzzle_path.line(complex(x_end, y))

    return puzzle_path
