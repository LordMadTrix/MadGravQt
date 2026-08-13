"""
Dual-Head & Multi-Laser Optical Calibration Wizard for MadGrav.
Calculates X/Y offset deltas and angular tilt matrix for multi-head laser systems.
"""

import math
import numpy as np


def calculate_dual_head_offset(test_cut_coords_head1, test_cut_coords_head2):
    """
    Calculate dual-head laser offset matrix from test alignment marks.
    Returns dict containing offset_x, offset_y, and calibration matrix.
    """
    x1, y1 = test_cut_coords_head1
    x2, y2 = test_cut_coords_head2

    delta_x = x2 - x1
    delta_y = y2 - y1

    offset_matrix = [
        [1.0, 0.0, delta_x],
        [0.0, 1.0, delta_y],
        [0.0, 0.0, 1.0]
    ]

    return {
        "delta_x": round(delta_x, 3),
        "delta_y": round(delta_y, 3),
        "distance_mm": round(math.sqrt(delta_x*delta_x + delta_y*delta_y), 3),
        "offset_matrix": offset_matrix
    }
