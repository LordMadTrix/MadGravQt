"""
Automatic camera calibration module for MadGrav.

Provides optical distortion calibration (chessboard pattern) and camera-to-bed
homography mapping using ArUco markers or known reference points.
"""

import cv2
import numpy as np


def find_chessboard_corners(gray_image, checkerboard_size=(6, 9), subpix=True):
    """
    Find chessboard corners in a grayscale image.

    :param gray_image: Grayscale numpy image array
    :param checkerboard_size: Tuple (cols, rows) representing inner corner dimensions
    :param subpix: Whether to refine corner positions to sub-pixel accuracy
    :return: (ret, corners) where ret is boolean success flag
    """
    if gray_image.ndim == 3:
        gray_image = cv2.cvtColor(gray_image, cv2.COLOR_BGR2GRAY)

    flags = (
        cv2.CALIB_CB_ADAPTIVE_THRESH
        + cv2.CALIB_CB_FAST_CHECK
        + cv2.CALIB_CB_NORMALIZE_IMAGE
    )
    ret, corners = cv2.findChessboardCorners(gray_image, checkerboard_size, flags)

    if ret and subpix:
        subpix_criteria = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 30, 0.1)
        corners = cv2.cornerSubPix(
            gray_image, corners, (11, 11), (-1, -1), subpix_criteria
        )

    return ret, corners


def calibrate_camera_chessboard(image_points, object_points, image_size):
    """
    Perform standard pinhole camera optical calibration using chessboard points.

    :param image_points: List of N 2D corner point arrays (from find_chessboard_corners)
    :param object_points: List of N 3D object point arrays
    :param image_size: Tuple (width, height) of camera resolution
    :return: (rms, camera_matrix, dist_coeffs, rvecs, tvecs)
    """
    if len(image_points) == 0 or len(image_points) != len(object_points):
        raise ValueError("Equal non-zero number of image and object point sets required.")

    img_pts = [np.asarray(pts, dtype=np.float32) for pts in image_points]
    obj_pts = [np.asarray(pts, dtype=np.float32) for pts in object_points]

    rms, K, dist, rvecs, tvecs = cv2.calibrateCamera(
        obj_pts, img_pts, image_size, None, None
    )

    return float(rms), K, dist, rvecs, tvecs


def get_aruco_dictionary(dictionary_id=None):
    """
    Get ArUco predefined dictionary safely across OpenCV versions.
    """
    if dictionary_id is None:
        dictionary_id = cv2.aruco.DICT_4X4_50
    return cv2.aruco.getPredefinedDictionary(dictionary_id)


def detect_aruco_markers(image, dictionary_id=None):
    """
    Detect ArUco markers in an image, supporting both OpenCV <4.7 and >=4.7 API.

    :param image: Input image (BGR or Grayscale)
    :param dictionary_id: ArUco dictionary ID (default DICT_4X4_50)
    :return: (corners, ids, rejected)
    """
    if image is None:
        return [], None, []

    gray = image
    if gray.ndim == 3:
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

    dict_aruco = get_aruco_dictionary(dictionary_id)
    params = cv2.aruco.DetectorParameters()

    if hasattr(cv2.aruco, "ArucoDetector"):
        detector = cv2.aruco.ArucoDetector(dict_aruco, params)
        corners, ids, rejected = detector.detectMarkers(gray)
    else:
        corners, ids, rejected = cv2.aruco.detectMarkers(
            gray, dict_aruco, parameters=params
        )

    return corners, ids, rejected


def compute_aruco_homography(image, marker_real_coords, dictionary_id=None):
    """
    Detect ArUco markers in image and calculate homography matrix converting
    pixel coordinates -> bed real mm coordinates.

    :param image: Input camera image
    :param marker_real_coords: Dict mapping marker_id (int) to (x_mm, y_mm) center point,
           or mapping marker_id (int) to a 4-element list of (x_mm, y_mm) corner points
           [top-left, top-right, bottom-right, bottom-left].
    :param dictionary_id: ArUco dictionary identifier
    :return: (homography_matrix 3x3, rms_error_mm, detected_count)
    """
    corners, ids, _ = detect_aruco_markers(image, dictionary_id)

    if ids is None or len(ids) == 0:
        raise ValueError("No ArUco markers detected in the image.")

    ids = ids.flatten()
    pixel_pts = []
    real_pts = []

    for i, marker_id in enumerate(ids):
        if marker_id not in marker_real_coords:
            continue

        c = corners[i].reshape(4, 2)  # [TL, TR, BR, BL]
        target = marker_real_coords[marker_id]

        if isinstance(target, (list, tuple)) and len(target) == 4 and isinstance(target[0], (list, tuple)):
            # 4 explicit corners given for this marker
            for px_pt, real_pt in zip(c, target):
                pixel_pts.append(px_pt)
                real_pts.append(real_pt)
        else:
            # Center point specified (x_mm, y_mm)
            center_px = np.mean(c, axis=0)
            pixel_pts.append(center_px)
            real_pts.append(target)

    if len(pixel_pts) < 4:
        raise ValueError(
            f"Not enough matching markers/points detected (found {len(pixel_pts)}, minimum 4 required)."
        )

    src = np.asarray(pixel_pts, dtype=np.float64).reshape(-1, 1, 2)
    dst = np.asarray(real_pts, dtype=np.float64).reshape(-1, 1, 2)

    method = cv2.RANSAC if len(src) > 4 else 0
    H, _mask = cv2.findHomography(src, dst, method=method)

    if H is None:
        raise ValueError("Homography could not be computed from detected marker positions.")

    projected = cv2.perspectiveTransform(src, H)
    residuals = projected.reshape(-1, 2) - dst.reshape(-1, 2)
    rms_error_mm = float(np.sqrt(np.mean(np.sum(residuals**2, axis=1))))

    return H, rms_error_mm, len(pixel_pts)


def transform_pixel_to_mm(pixel_pts, H):
    """
    Transform N (x, y) pixel coordinates to real-world bed mm coordinates using homography.

    :param pixel_pts: Array-like of (x, y) points (Nx2)
    :param H: 3x3 homography matrix
    :return: Nx2 numpy array of (X_mm, Y_mm)
    """
    pts = np.asarray(pixel_pts, dtype=np.float64).reshape(-1, 1, 2)
    transformed = cv2.perspectiveTransform(pts, H)
    return transformed.reshape(-1, 2)


def transform_mm_to_pixel(mm_pts, H):
    """
    Transform N (X_mm, Y_mm) bed coordinates to image pixel coordinates using inverse homography.

    :param mm_pts: Array-like of (X_mm, Y_mm) points (Nx2)
    :param H: 3x3 homography matrix (pixel -> mm)
    :return: Nx2 numpy array of (x_px, y_px)
    """
    H_inv = np.linalg.inv(H)
    pts = np.asarray(mm_pts, dtype=np.float64).reshape(-1, 1, 2)
    transformed = cv2.perspectiveTransform(pts, H_inv)
    return transformed.reshape(-1, 2)
