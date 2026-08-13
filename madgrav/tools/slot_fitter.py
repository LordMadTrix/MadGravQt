"""
Slot & Notch Auto-Fitter module for MadGrav.

Detects interlocking slots/notches in vector artwork designed for a specific material thickness
and automatically resizes them to fit a new material thickness, matching LightBurn's Slot Fitter tool.
"""

import math
from madgrav.svgelements import Path, Point


def adjust_slot_thickness(path, old_thickness_mm, new_thickness_mm):
    """
    Adjust slot thickness in a path from old_thickness_mm to new_thickness_mm.

    :param path: svgelements.Path instance
    :param old_thickness_mm: Existing material thickness of slots in mm
    :param new_thickness_mm: Target material thickness of slots in mm
    :return: Modified svgelements.Path
    """
    from madgrav.core.units import UNITS_PER_MM

    if not isinstance(path, Path) or len(path) == 0 or old_thickness_mm == new_thickness_mm:
        return path

    old_units = old_thickness_mm * UNITS_PER_MM
    new_units = new_thickness_mm * UNITS_PER_MM
    delta_units = (new_units - old_units) / 2.0

    pts = [path.point(k / 60.0) for k in range(61)]
    if len(pts) < 4:
        return path

    n = len(pts)
    is_closed = (pts[0] == pts[-1])

    new_pts = []

    for i in range(n):
        pt = pts[i]

        # Check distance to opposite points to find slot walls
        adjusted = False
        for j in range(n):
            if abs(i - j) > 2 and abs(i - j) < n - 2:
                opp_pt = pts[j]
                dist = math.hypot(pt[0] - opp_pt[0], pt[1] - opp_pt[1])

                if abs(dist - old_units) < old_units * 0.15:
                    # Parallel slot wall detected, push outward along normal
                    nx = pt[0] - opp_pt[0]
                    ny = pt[1] - opp_pt[1]
                    norm = math.hypot(nx, ny)
                    if norm > 0:
                        shift_x = (nx / norm) * delta_units
                        shift_y = (ny / norm) * delta_units
                        new_pts.append(Point(pt[0] + shift_x, pt[1] + shift_y))
                        adjusted = True
                        break

        if not adjusted:
            new_pts.append(pt)

    res_path = Path()
    res_path.move(new_pts[0])
    for p in new_pts[1:]:
        res_path.line(p)
    if is_closed:
        res_path.closed()

    return res_path


def apply_slot_fitter_to_nodes(elements_service, old_thickness_mm, new_thickness_mm, nodes=None):
    """
    Apply slot thickness fitting to selected path nodes.

    :param elements_service: The elements service (`kernel.elements`)
    :param old_thickness_mm: Existing thickness in mm
    :param new_thickness_mm: Target thickness in mm
    :param nodes: Optional list of nodes (if None, uses emphasized selection)
    :return: Count of updated nodes
    """
    if nodes is None:
        nodes = list(elements_service.elems(emphasized=True))

    updated_count = 0

    for node in nodes:
        if hasattr(node, "path") and node.path is not None:
            node.path = adjust_slot_thickness(node.path, old_thickness_mm, new_thickness_mm)
            node.altered()
            updated_count += 1

    if updated_count > 0:
        elements_service.signal("tree_changed")
        elements_service.signal("refresh_scene")

    return updated_count
