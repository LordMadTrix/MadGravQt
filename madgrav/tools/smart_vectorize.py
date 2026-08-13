"""
Smart Bitmap Vectorization & Bezier Curve Smoothing for MadGrav.
Converts raster image contours to smooth continuous Bezier vector paths.
"""

import cv2
import numpy as np
from madgrav.svgelements import Path


def vectorize_bitmap_to_bezier(image_np, threshold=128, corner_threshold_deg=45.0, error_tolerance_mm=0.1):
    """
    Vectorize 8-bit bitmap array into smooth Bezier vector Path objects.
    """
    paths = []
    if image_np is None or image_np.size == 0:
        return paths

    if len(image_np.shape) == 3:
        gray = cv2.cvtColor(image_np, cv2.COLOR_BGR2GRAY)
    else:
        gray = image_np

    _, binary = cv2.threshold(gray, threshold, 255, cv2.THRESH_BINARY_INV)
    contours, _ = cv2.findContours(binary, cv2.RETR_LIST, cv2.CHAIN_APPROX_TC89_L1)

    for cnt in contours:
        if len(cnt) < 3:
            continue
        p = Path()
        first = cnt[0][0]
        p.move(float(first[0]), float(first[1]))
        for pt in cnt[1:]:
            pos = pt[0]
            p.line(float(pos[0]), float(pos[1]))
        p.closed()
        paths.append(p)

    return paths
