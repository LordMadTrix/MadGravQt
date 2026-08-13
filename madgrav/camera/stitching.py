"""
Multi-Camera Optical Perspective Warping & Seam Feathering for MadGrav.
Stitches multiple wide-angle camera feeds into a single unified bed overlay.
"""

import cv2
import numpy as np


def stitch_multi_camera_views(camera_images, homography_matrices, target_bed_width_mm=300.0, target_bed_height_mm=200.0, px_per_mm=2.0):
    """
    Warp and blend multiple camera feeds into a unified laser bed image.
    Returns composite RGB image array.
    """
    out_w = int(target_bed_width_mm * px_per_mm)
    out_h = int(target_bed_height_mm * px_per_mm)
    composite = np.zeros((out_h, out_w, 3), dtype=np.float32)
    weight_map = np.zeros((out_h, out_w, 1), dtype=np.float32)

    for img, H in zip(camera_images, homography_matrices):
        if img is None or img.size == 0 or H is None:
            continue
        h_img, w_img = img.shape[:2]

        # Scale homography to target pixel resolution
        S = np.diag([px_per_mm, px_per_mm, 1.0])
        H_scaled = S @ np.array(H, dtype=np.float64)

        warped = cv2.warpPerspective(img, H_scaled, (out_w, out_h), flags=cv2.INTER_LINEAR)
        mask = cv2.warpPerspective(np.ones((h_img, w_img), dtype=np.float32), H_scaled, (out_w, out_h))
        mask = np.expand_dims(mask, axis=2)

        composite += warped.astype(np.float32) * mask
        weight_map += mask

    weight_map[weight_map == 0] = 1.0
    result = (composite / weight_map).clip(0, 255).astype(np.uint8)
    return result
