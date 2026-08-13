"""
Unit tests for camera calibration (chessboard + ArUco homography) and real mm object measurement.
"""

import unittest
import cv2
import numpy as np

from madgrav.camera.autocal import (
    calibrate_camera_chessboard,
    compute_aruco_homography,
    detect_aruco_markers,
    find_chessboard_corners,
    get_aruco_dictionary,
    transform_mm_to_pixel,
    transform_pixel_to_mm,
)
from madgrav.camera.measurement import (
    BaseSegmentationModel,
    DetectedObject,
    detect_objects,
    draw_object_measurements,
)


class MockSegmentationModel(BaseSegmentationModel):
    """Mock deep learning segmentation model for testing segmentation hooks."""

    def __init__(self, mask: np.ndarray):
        self.mask = mask

    def predict_masks(self, image: np.ndarray):
        return [self.mask]


class TestCameraCalibrationAndMeasurement(unittest.TestCase):
    def test_chessboard_corners_and_calibration(self):
        """Test chessboard corner detection and camera matrix calibration."""
        checkerboard_size = (6, 9)
        square_size_mm = 25.0

        # Generate 3D object points
        objp = np.zeros((checkerboard_size[0] * checkerboard_size[1], 3), np.float32)
        objp[:, :2] = np.mgrid[0 : checkerboard_size[0], 0 : checkerboard_size[1]].T.reshape(-1, 2)
        objp *= square_size_mm

        # Create a synthetic chessboard pattern image
        canvas = np.ones((800, 1000), dtype=np.uint8) * 255
        sq_w = 60
        sq_h = 60
        start_x, start_y = 100, 100
        for r in range(10):
            for c in range(7):
                if (r + c) % 2 == 0:
                    x0 = start_x + c * sq_w
                    y0 = start_y + r * sq_h
                    canvas[y0 : y0 + sq_h, x0 : x0 + sq_w] = 0

        ret, corners = find_chessboard_corners(canvas, checkerboard_size)
        self.assertTrue(ret, "Chessboard pattern should be detected in synthetic image")
        self.assertEqual(len(corners), checkerboard_size[0] * checkerboard_size[1])

        # Test calibration calculation
        img_points = [corners, corners]
        obj_points = [objp, objp]
        rms, K, dist, rvecs, tvecs = calibrate_camera_chessboard(
            img_points, obj_points, (1000, 800)
        )

        self.assertIsInstance(rms, float)
        self.assertEqual(K.shape, (3, 3))
        self.assertGreaterEqual(dist.shape[1], 4)

    def test_aruco_marker_detection_and_homography(self):
        """Test ArUco marker detection and pixel->mm homography computation."""
        dictionary_id = cv2.aruco.DICT_4X4_50
        dict_aruco = get_aruco_dictionary(dictionary_id)

        canvas = np.ones((600, 800, 3), dtype=np.uint8) * 255

        # Place 4 ArUco markers at known positions in canvas
        # Marker IDs: 0, 1, 2, 3
        # Real bed positions in mm: (0,0), (300,0), (300,200), (0,200)
        marker_positions_px = [
            (100, 100),  # ID 0
            (500, 100),  # ID 1
            (500, 400),  # ID 2
            (100, 400),  # ID 3
        ]
        marker_real_coords = {
            0: (0.0, 0.0),
            1: (300.0, 0.0),
            2: (300.0, 200.0),
            3: (0.0, 200.0),
        }

        sz = 80
        for marker_id, (px, py) in enumerate(marker_positions_px):
            if hasattr(cv2.aruco, "generateImageMarker"):
                m_img = cv2.aruco.generateImageMarker(dict_aruco, marker_id, sz)
            else:
                m_img = cv2.aruco.drawMarker(dict_aruco, marker_id, sz)
            m_bgr = cv2.cvtColor(m_img, cv2.COLOR_GRAY2BGR)
            canvas[py : py + sz, px : px + sz] = m_bgr

        corners, ids, _ = detect_aruco_markers(canvas, dictionary_id)
        self.assertIsNotNone(ids)
        self.assertGreaterEqual(len(ids), 4)

        H, rms_mm, count = compute_aruco_homography(canvas, marker_real_coords, dictionary_id)
        self.assertEqual(H.shape, (3, 3))
        self.assertGreaterEqual(count, 4)
        self.assertLess(rms_mm, 5.0)  # RMS error should be small

        # Test point transformations
        # Center of marker 0 in px is ~ (140, 140) -> real mm ~ (0, 0)
        marker0_center_px = np.array([[140.0, 140.0]])
        mm_pt = transform_pixel_to_mm(marker0_center_px, H)
        self.assertAlmostEqual(mm_pt[0, 0], 0.0, delta=5.0)
        self.assertAlmostEqual(mm_pt[0, 1], 0.0, delta=5.0)

        # Inverse transformation back to pixels
        px_back = transform_mm_to_pixel(mm_pt, H)
        self.assertAlmostEqual(px_back[0, 0], 140.0, delta=1.0)
        self.assertAlmostEqual(px_back[0, 1], 140.0, delta=1.0)

    def test_object_detection_and_real_mm_measurement(self):
        """Test object contour detection and conversion to physical dimensions in mm."""
        canvas = np.ones((500, 500, 3), dtype=np.uint8) * 255

        # Draw a synthetic black rectangle object on canvas
        # Upper-left (100, 100), width=100px, height=60px
        cv2.rectangle(canvas, (100, 100), (200, 160), (0, 0, 0), -1)

        # Define an exact linear homography matrix mapping 2 pixels = 1 mm (scale = 0.5)
        # Pixel (100, 100) -> mm (50, 50)
        # Rectangle width 100px = 50 mm, height 60px = 30 mm, Area = 1500 mm²
        H = np.array([
            [0.5, 0.0, 0.0],
            [0.0, 0.5, 0.0],
            [0.0, 0.0, 1.0]
        ], dtype=np.float64)

        objects = detect_objects(canvas, H, min_area_mm2=10.0, threshold_method="otsu")
        self.assertEqual(len(objects), 1)

        obj = objects[0]
        self.assertIsInstance(obj, DetectedObject)

        min_x, min_y, w_mm, h_mm = obj.bounding_box_mm
        self.assertAlmostEqual(w_mm, 50.0, delta=2.0)
        self.assertAlmostEqual(h_mm, 30.0, delta=2.0)
        self.assertAlmostEqual(obj.area_mm2, 1500.0, delta=100.0)

    def test_segmentation_model_hook(self):
        """Test custom AI segmentation model hook (BaseSegmentationModel / YOLO-seg / SAM)."""
        # Create a synthetic binary mask (circle of radius 40px at center (200, 200))
        mask = np.zeros((400, 400), dtype=np.uint8)
        cv2.circle(mask, (200, 200), 40, 255, -1)

        seg_model = MockSegmentationModel(mask)

        # 1 pixel = 1 mm homography
        H = np.eye(3, dtype=np.float64)

        dummy_img = np.ones((400, 400, 3), dtype=np.uint8) * 255
        objects = detect_objects(dummy_img, H, min_area_mm2=10.0, seg_model=seg_model)

        self.assertEqual(len(objects), 1)
        obj = objects[0]
        # Circle radius 40mm -> diameter 80mm, area ~ pi * 40^2 = 5026 mm²
        _, _, w_mm, h_mm = obj.bounding_box_mm
        self.assertAlmostEqual(w_mm, 80.0, delta=3.0)
        self.assertAlmostEqual(h_mm, 80.0, delta=3.0)
        self.assertAlmostEqual(obj.area_mm2, np.pi * 40**2, delta=300.0)

    def test_draw_object_measurements(self):
        """Test drawing measurements onto image."""
        img = np.ones((200, 200, 3), dtype=np.uint8) * 255
        cnt_px = np.array([[10, 10], [50, 10], [50, 50], [10, 50]], dtype=np.float64)
        cnt_mm = cnt_px * 0.5
        obj = DetectedObject(
            contour_px=cnt_px,
            contour_mm=cnt_mm,
            bounding_box_mm=(5.0, 5.0, 20.0, 20.0),
            rotated_box_mm=((15.0, 15.0), (20.0, 20.0), 0.0),
            area_mm2=400.0,
            perimeter_mm=80.0,
            centroid_mm=(15.0, 15.0),
        )

        annotated = draw_object_measurements(img, [obj])
        self.assertEqual(annotated.shape, (200, 200, 3))
        self.assertFalse(np.array_equal(img, annotated))

    def test_camera_service_integration(self):
        """Test Camera service integration with calibration and object measurement."""
        from test.bootstrap import bootstrap
        from madgrav.camera.camera import Camera

        kernel = bootstrap()
        cam = Camera(kernel, "camera/0")
        kernel.add_service("camera", cam)
        kernel.activate_service_path("camera", "camera/0")

        # Set synthetic frame
        canvas = np.ones((500, 500, 3), dtype=np.uint8) * 255
        cv2.rectangle(canvas, (100, 100), (200, 160), (0, 0, 0), -1)
        cam._last_raw = canvas
        cam._current_raw = canvas

        # Set synthetic alignment homography matrix
        H_px = np.eye(3, dtype=np.float64)
        cam.alignment_homography = H_px.tolist()

        objects = cam.detect_objects_and_measure(min_area_mm2=10.0)
        self.assertGreaterEqual(len(objects), 1)


if __name__ == "__main__":
    unittest.main()
