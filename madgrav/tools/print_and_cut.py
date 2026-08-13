"""
Print & Cut (2-Point Registration Mark Alignment) module for MadGrav.

Computes exact affine 2D translation, rotation, and scale alignment mapping vector artwork
onto physical pre-printed materials, matching LightBurn's Print & Cut tool.
"""

import math
from madgrav.svgelements import Matrix


def compute_print_and_cut_transform(p1_design, p1_real, p2_design, p2_real):
    """
    Compute 2D alignment matrix mapping p1_design -> p1_real and p2_design -> p2_real.

    :param p1_design: (x, y) coordinates of registration mark 1 in design space
    :param p1_real: (X, Y) coordinates of registration mark 1 on physical bed
    :param p2_design: (x, y) coordinates of registration mark 2 in design space
    :param p2_real: (X, Y) coordinates of registration mark 2 on physical bed
    :return: svgelements.Matrix transformation
    """
    dx_d = p2_design[0] - p1_design[0]
    dy_d = p2_design[1] - p1_design[1]
    dist_d = math.hypot(dx_d, dy_d)

    dx_r = p2_real[0] - p1_real[0]
    dy_r = p2_real[1] - p1_real[1]
    dist_r = math.hypot(dx_r, dy_r)

    if dist_d == 0 or dist_r == 0:
        raise ValueError("Registration points must be distinct.")

    # Uniform scale ratio
    scale = dist_r / dist_d

    # Rotation angle difference
    angle_d = math.atan2(dy_d, dx_d)
    angle_r = math.atan2(dy_r, dx_r)
    angle_diff = angle_r - angle_d

    # Build transformation matrix:
    # 1. Translate design mark 1 to origin
    # 2. Scale uniformly
    # 3. Rotate by angle_diff
    # 4. Translate origin to real mark 1
    M = Matrix.scale(1.0)
    M.post_translate(-p1_design[0], -p1_design[1])
    M.post_scale(scale, scale)
    M.post_rotate(angle_diff)
    M.post_translate(p1_real[0], p1_real[1])

    return M


def apply_print_and_cut_alignment(elements_service, p1_design, p1_real, p2_design, p2_real, nodes=None):
    """
    Apply 2-Point Print & Cut alignment transformation to project elements.

    :param elements_service: The elements service (`kernel.elements`)
    :param p1_design: (x, y) mark 1 design
    :param p1_real: (X, Y) mark 1 real bed
    :param p2_design: (x, y) mark 2 design
    :param p2_real: (X, Y) mark 2 real bed
    :param nodes: Optional list of nodes to align (if None, applies to all elem nodes)
    :return: Transformed svgelements.Matrix
    """
    # Convert coordinates to units if passed in mm
    M = compute_print_and_cut_transform(p1_design, p1_real, p2_design, p2_real)

    if nodes is None:
        nodes = list(elements_service.elem_branch.flat(types="elem path"))

    for node in nodes:
        if hasattr(node, "matrix") and node.matrix is not None:
            node.matrix *= M
        if hasattr(node, "path") and node.path is not None:
            node.path = node.path * M

    elements_service.signal("tree_changed")
    elements_service.signal("refresh_scene")
    return M
