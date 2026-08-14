"""Print and Cut Fiducial Alignment Tool.

Computes rigid (2-point) and affine/homography (4-point) transformations
to align laser cutting paths with pre-printed material.
"""

from typing import List, Tuple, Dict, Any
import math


def compute_2point_transform(
    src_p1: Tuple[float, float],
    src_p2: Tuple[float, float],
    dst_p1: Tuple[float, float],
    dst_p2: Tuple[float, float],
) -> Dict[str, float]:
    """Calculate translation (tx, ty), uniform scale (s), and rotation angle (theta rad).
    
    Transforms src coordinates to dst coordinates: dst = R(theta) * s * (src) + T
    """
    # Source vector
    dx_src = src_p2[0] - src_p1[0]
    dy_src = src_p2[1] - src_p1[1]
    len_src = math.hypot(dx_src, dy_src) or 1.0

    # Dest vector
    dx_dst = dst_p2[0] - dst_p1[0]
    dy_dst = dst_p2[1] - dst_p1[1]
    len_dst = math.hypot(dx_dst, dy_dst) or 1.0

    scale = len_dst / len_src

    ang_src = math.atan2(dy_src, dx_src)
    ang_dst = math.atan2(dy_dst, dx_dst)
    rot_rad = ang_dst - ang_src

    # Calculate translation based on p1
    # dst_p1 = rot(scale * src_p1) + T
    cos_t = math.cos(rot_rad)
    sin_t = math.sin(rot_rad)

    x_rot = scale * (src_p1[0] * cos_t - src_p1[1] * sin_t)
    y_rot = scale * (src_p1[0] * sin_t + src_p1[1] * cos_t)

    tx = dst_p1[0] - x_rot
    ty = dst_p1[1] - y_rot

    return {
        "scale": round(scale, 6),
        "rotation_deg": round(math.degrees(rot_rad), 4),
        "rotation_rad": rot_rad,
        "tx": round(tx, 4),
        "ty": round(ty, 4),
    }


def apply_transform_point(
    pt: Tuple[float, float],
    transform: Dict[str, float],
) -> Tuple[float, float]:
    """Apply computed 2-point transformation to a point (x, y)."""
    s = transform.get("scale", 1.0)
    rot = transform.get("rotation_rad", 0.0)
    tx = transform.get("tx", 0.0)
    ty = transform.get("ty", 0.0)

    cos_t = math.cos(rot)
    sin_t = math.sin(rot)

    nx = s * (pt[0] * cos_t - pt[1] * sin_t) + tx
    ny = s * (pt[0] * sin_t + pt[1] * cos_t) + ty

    return (round(nx, 4), round(ny, 4))


def compute_print_and_cut_transform(
    p1_design: Tuple[float, float],
    p1_real: Tuple[float, float],
    p2_design: Tuple[float, float],
    p2_real: Tuple[float, float],
):
    """Calculate affine transform Matrix for Print & Cut alignment."""
    from madgrav.svgelements import Matrix
    # Design vector
    dx_d = p2_design[0] - p1_design[0]
    dy_d = p2_design[1] - p1_design[1]
    len_d = math.hypot(dx_d, dy_d) or 1.0

    # Real vector
    dx_r = p2_real[0] - p1_real[0]
    dy_r = p2_real[1] - p1_real[1]
    len_r = math.hypot(dx_r, dy_r) or 1.0

    scale = len_r / len_d
    ang_d = math.atan2(dy_d, dx_d)
    ang_r = math.atan2(dy_r, dx_r)
    rot = ang_r - ang_d

    # Matrix: Translate(-p1_d) -> Scale(s) -> Rotate(rot) -> Translate(p1_r)
    M = Matrix()
    M.post_translate(-p1_design[0], -p1_design[1])
    M.post_scale(scale, scale)
    M.post_rotate(rot)
    M.post_translate(p1_real[0], p1_real[1])

    return M


def apply_print_and_cut_alignment(elements, matrix):
    """Apply transform matrix to all selected elements."""
    for node in elements.elems(emphasized=True):
        if hasattr(node, "matrix"):
            node.matrix *= matrix
            node.altered()
    elements.signal("refresh_scene", "Scene")

