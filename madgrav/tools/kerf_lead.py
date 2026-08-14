"""
Kerf Compensation & Lead-In/Out module for MadGrav.

Allows compensating for laser beam width (kerf offset) and adding entry/exit lead-in segments
to prevent pierce marks on cut edges, matching LightBurn's cut settings.
"""

import math
from madgrav.svgelements import Path, Point


def apply_kerf_offset(path, kerf_mm=0.1, mode="outer"):
    """
    Apply kerf offset to a path.

    :param path: svgelements.Path instance
    :param kerf_mm: Beam radius offset in mm (positive for expansion, negative for shrink)
    :param mode: 'outer' (expand exterior), 'inner' (shrink interior holes)
    :return: Offset svgelements.Path
    """
    from madgrav.core.units import UNITS_PER_MM

    if not isinstance(path, Path) or len(path) == 0 or kerf_mm == 0.0:
        return path

    kerf_units = kerf_mm * UNITS_PER_MM
    if mode.lower() == "inner":
        kerf_units = -kerf_units

    try:
        pts = [path.point(k / 50.0) for k in range(51)]
        if len(pts) < 3:
            return path

        new_path = Path()
        n = len(pts)
        is_closed = (pts[0] == pts[-1])

        offset_pts = []
        for i in range(n):
            prev_pt = pts[(i - 1) % n] if is_closed else pts[max(0, i - 1)]
            curr_pt = pts[i]
            next_pt = pts[(i + 1) % n] if is_closed else pts[min(n - 1, i + 1)]

            tx = next_pt[0] - prev_pt[0]
            ty = next_pt[1] - prev_pt[1]
            t_len = math.hypot(tx, ty)

            if t_len == 0:
                offset_pts.append(curr_pt)
                continue

            nx = -ty / t_len
            ny = tx / t_len

            offset_x = curr_pt[0] + nx * kerf_units
            offset_y = curr_pt[1] + ny * kerf_units
            offset_pts.append(Point(offset_x, offset_y))

        new_path.move(offset_pts[0])
        for pt in offset_pts[1:]:
            new_path.line(pt)
        if is_closed:
            new_path.closed()

        return new_path

    except Exception:
        return path


def add_lead_in_out(path, lead_in_len_mm=2.0, lead_out_len_mm=2.0, lead_angle_deg=45.0):
    """
    Add lead-in and lead-out line segments to the start and end of path contours.

    :param path: svgelements.Path instance
    :param lead_in_len_mm: Length of lead-in line in mm
    :param lead_out_len_mm: Length of lead-out line in mm
    :param lead_angle_deg: Angle of approach relative to start tangent in degrees
    :return: Path with lead-in and lead-out segments attached
    """
    from madgrav.core.units import UNITS_PER_MM

    if not isinstance(path, Path) or len(path) == 0:
        return path

    in_len_units = lead_in_len_mm * UNITS_PER_MM
    out_len_units = lead_out_len_mm * UNITS_PER_MM
    angle_rad = math.radians(lead_angle_deg)

    pts = [path.point(k / 30.0) for k in range(31)]
    if len(pts) < 2:
        return path

    p_start = Point(pts[0])
    p_next = Point(pts[1])

    tx = p_next[0] - p_start[0]
    ty = p_next[1] - p_start[1]
    t_angle = math.atan2(ty, tx)

    in_angle = t_angle - angle_rad
    in_x = p_start[0] - math.cos(in_angle) * in_len_units
    in_y = p_start[1] - math.sin(in_angle) * in_len_units
    p_in_start = Point(in_x, in_y)

    p_end = Point(pts[-1])
    p_prev = Point(pts[-2])
    out_tx = p_end[0] - p_prev[0]
    out_ty = p_end[1] - p_prev[1]
    out_t_angle = math.atan2(out_ty, out_tx)

    out_angle = out_t_angle + angle_rad
    out_x = p_end[0] + math.cos(out_angle) * out_len_units
    out_y = p_end[1] + math.sin(out_angle) * out_len_units
    p_out_end = Point(out_x, out_y)

    new_path = Path()
    new_path.move(p_in_start)
    new_path.line(p_start)
    for pt in pts[1:]:
        new_path.line(pt)
    new_path.line(p_out_end)

    return new_path


def apply_kerf_and_lead_to_selection(
    elements_service,
    nodes=None,
    kerf_mm=0.1,
    mode="outer",
    lead_in_mm=2.0,
    lead_out_mm=2.0,
    lead_angle_deg=45.0,
):
    """
    Apply kerf compensation and lead-in/lead-out to selected elements.

    :param elements_service: The elements service (`kernel.elements`)
    :param nodes: Optional list of nodes to process
    :param kerf_mm: Beam radius offset in mm
    :param mode: 'outer' or 'inner'
    :param lead_in_mm: Length of lead-in in mm
    :param lead_out_mm: Length of lead-out in mm
    :param lead_angle_deg: Lead angle in degrees
    :return: Count of updated nodes
    """
    if nodes is None:
        nodes = list(elements_service.elems(emphasized=True))
    updated_count = 0

    for node in nodes:
        node_path = getattr(node, "path", None)
        if node_path is None and hasattr(node, "as_geometry"):
            try:
                node_path = node.as_geometry().as_path()
            except Exception:
                node_path = None

        if node_path is not None:
            if kerf_mm != 0.0:
                node_path = apply_kerf_offset(node_path, kerf_mm=kerf_mm, mode=mode)
            if lead_in_mm > 0.0 or lead_out_mm > 0.0:
                node_path = add_lead_in_out(
                    node_path,
                    lead_in_len_mm=lead_in_mm,
                    lead_out_len_mm=lead_out_mm,
                    lead_angle_deg=lead_angle_deg,
                )

            if hasattr(node, "path"):
                node.path = node_path
            else:
                parent = getattr(node, "parent", None) or elements_service.elem_branch
                new_node = elements_service.elem_branch.add(
                    type="elem path",
                    path=node_path,
                    stroke=getattr(node, "stroke", elements_service.default_stroke),
                    stroke_width=getattr(node, "stroke_width", 1000.0),
                )
                if parent is not None and hasattr(parent, "remove_node"):
                    parent.remove_node(node)
                node = new_node
            node.altered()
            updated_count += 1

    if updated_count > 0:
        elements_service.signal("tree_changed")
        elements_service.signal("refresh_scene")

    return updated_count
