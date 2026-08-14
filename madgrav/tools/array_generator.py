"""
Array Generator module for MadGrav (Grid Array & Circular Array).

Allows repeating selected nodes or newly generated shapes in rectangular grids or polar circular arrays,
matching LightBurn's Array tool suite.
"""

import math
from copy import copy
from madgrav.svgelements import Matrix


def generate_grid_array(
    elements_service,
    nodes=None,
    rows=3,
    cols=3,
    distance_x_mm=10.0,
    distance_y_mm=10.0,
    by_padding=True,
):
    """
    Duplicate selected nodes into a 2D rectangular grid array.

    :param elements_service: The elements service (`kernel.elements`)
    :param nodes: List of nodes to duplicate (if None, uses currently selected elements)
    :param rows: Number of grid rows
    :param cols: Number of grid columns
    :param distance_x_mm: Spacing along X in mm (padding or center-to-center offset)
    :param distance_y_mm: Spacing along Y in mm (padding or center-to-center offset)
    :param by_padding: If True, distance is edge-to-edge gap; if False, center-to-center pitch.
    :return: List of newly created duplicated nodes
    """
    from madgrav.core.units import UNITS_PER_MM

    if nodes is None:
        nodes = list(elements_service.elems(emphasized=True))

    if not nodes:
        return []

    created_nodes = []

    for node in nodes:
        try:
            bounds = node.bounds
        except AttributeError:
            bounds = None

        if bounds is None:
            continue

        min_x, min_y, max_x, max_y = bounds
        width_units = max_x - min_x
        height_units = max_y - min_y

        if by_padding:
            step_x_units = width_units + (distance_x_mm * UNITS_PER_MM)
            step_y_units = height_units + (distance_y_mm * UNITS_PER_MM)
        else:
            step_x_units = distance_x_mm * UNITS_PER_MM
            step_y_units = distance_y_mm * UNITS_PER_MM

        for r in range(rows):
            for c in range(cols):
                if r == 0 and c == 0:
                    continue  # Skip original position

                dx = c * step_x_units
                dy = r * step_y_units

                # Copy node and translate
                copy_node = copy(node)
                if getattr(copy_node, "matrix", None) is not None:
                    copy_node.matrix = Matrix(copy_node.matrix)
                    copy_node.matrix.post_translate(dx, dy)
                else:
                    copy_node.matrix = Matrix.translate(dx, dy)

                copy_node.altered()
                parent = getattr(node, "parent", None)
                if parent is not None:
                    parent.add_node(copy_node)
                else:
                    elements_service.elem_branch.add_node(copy_node)
                created_nodes.append(copy_node)

    elements_service.signal("tree_changed")
    elements_service.signal("refresh_scene")
    return created_nodes


def generate_circular_array(
    elements_service,
    nodes=None,
    count=8,
    center_x_mm=0.0,
    center_y_mm=0.0,
    total_angle_deg=360.0,
    rotate_copies=True,
):
    """
    Duplicate selected nodes into a polar circular array.

    :param elements_service: The elements service (`kernel.elements`)
    :param nodes: List of nodes to duplicate (if None, uses currently selected elements)
    :param count: Total number of copies (including original)
    :param center_x_mm: Center of rotation X in mm
    :param center_y_mm: Center of rotation Y in mm
    :param total_angle_deg: Total span angle in degrees (default 360.0)
    :param rotate_copies: Whether each copy is rotated to face the center
    :return: List of newly created duplicated nodes
    """
    from madgrav.core.units import UNITS_PER_MM

    if nodes is None:
        nodes = list(elements_service.elems(emphasized=True))

    if not nodes or count <= 1:
        return []

    cx_units = center_x_mm * UNITS_PER_MM
    cy_units = center_y_mm * UNITS_PER_MM

    step_angle_deg = total_angle_deg / float(count if total_angle_deg < 360.0 else count)

    created_nodes = []

    for node in nodes:
        for i in range(1, count):
            angle_deg = i * step_angle_deg
            angle_rad = math.radians(angle_deg)

            # Rotation matrix around (cx_units, cy_units)
            M = Matrix.scale(1.0)
            M.post_translate(-cx_units, -cy_units)
            if rotate_copies:
                M.post_rotate(angle_rad)
            M.post_translate(cx_units, cy_units)

            copy_node = copy(node)
            if getattr(copy_node, "matrix", None) is not None:
                copy_node.matrix = Matrix(copy_node.matrix)
                copy_node.matrix *= M
            else:
                copy_node.matrix = Matrix(M)

            copy_node.altered()
            parent = getattr(node, "parent", None)
            if parent is not None:
                parent.add_node(copy_node)
            else:
                elements_service.elem_branch.add_node(copy_node)
            created_nodes.append(copy_node)

    elements_service.signal("tree_changed")
    elements_service.signal("refresh_scene")
    return created_nodes
