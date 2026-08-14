"""
Smart Bitmap Vectorization & Corner-Aware Contour Simplification for MadGrav.
Converts raster image contours to simplified, cleaned-up vector paths.
"""

import math

import cv2
from madgrav.svgelements import Path


def _filter_gentle_corners(points, angle_threshold_deg):
    """Drop points whose local turn angle is gentler (closer to straight)
    than angle_threshold_deg, keeping sharp corners intact. points is a
    list of (x, y) tuples for an already distance-simplified contour."""
    if len(points) < 3 or angle_threshold_deg <= 0:
        return points
    kept = [points[0]]
    for i in range(1, len(points) - 1):
        prev = kept[-1]
        curr = points[i]
        nxt = points[i + 1]
        v1 = (curr[0] - prev[0], curr[1] - prev[1])
        v2 = (nxt[0] - curr[0], nxt[1] - curr[1])
        len1 = math.hypot(*v1)
        len2 = math.hypot(*v2)
        if len1 == 0 or len2 == 0:
            continue
        cos_angle = max(-1.0, min(1.0, (v1[0] * v2[0] + v1[1] * v2[1]) / (len1 * len2)))
        turn_deg = math.degrees(math.acos(cos_angle))
        if turn_deg >= angle_threshold_deg:
            kept.append(curr)
    kept.append(points[-1])
    return kept


def vectorize_bitmap_to_bezier(image_np, threshold=128, corner_threshold_deg=45.0, error_tolerance_mm=0.1):
    """
    Vectorize 8-bit bitmap array into simplified vector Path objects.

    error_tolerance_mm controls how aggressively raw pixel-contour noise
    is simplified (cv2.approxPolyDP epsilon, in the same pixel-space units
    as image_np -- the function has no DPI/scale context of its own, so
    despite the "_mm" name this is really a pixel-distance tolerance).
    corner_threshold_deg then drops any remaining vertex whose turn angle
    is gentler than that many degrees, so only real corners survive.
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

    epsilon = max(0.01, error_tolerance_mm)

    for cnt in contours:
        if len(cnt) < 3:
            continue
        simplified = cv2.approxPolyDP(cnt, epsilon, True)
        points = [(float(pt[0][0]), float(pt[0][1])) for pt in simplified]
        points = _filter_gentle_corners(points, corner_threshold_deg)
        if len(points) < 3:
            continue

        p = Path()
        # complex(x, y) is the required single-point form -- two scalar
        # args would be read as two separate points and collapse the
        # contour's Y extent to 0 (see galvo_hatching.py for the same fix).
        p.move(complex(*points[0]))
        for x, y in points[1:]:
            p.line(complex(x, y))
        p.closed()
        paths.append(p)

    return paths
