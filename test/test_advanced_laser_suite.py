"""
Unit tests for Advanced Laser Manufacturing Suite:
- 2D Polygon Nesting (nesting.py)
- 3D Grayscale Laser Relief Engine (relief_3d.py)
- Galvo & Fiber Laser Hatch Patterns (galvo_hatching.py)
- Smart Vectorization & Bezier Curve Fitting (smart_vectorize.py)
"""

import unittest
import numpy as np
from test.bootstrap import bootstrap
from madgrav.svgelements import Path, Color

from madgrav.tools.nesting import nest_elements
from madgrav.tools.relief_3d import generate_3d_laser_relief
from madgrav.tools.galvo_hatching import apply_galvo_hatch
from madgrav.tools.smart_vectorize import vectorize_bitmap_to_bezier


class TestAdvancedLaserSuite(unittest.TestCase):
    def setUp(self):
        self.kernel = bootstrap()
        self.elements = self.kernel.elements

    def test_2d_polygon_nesting(self):
        """Test 2D Polygon Nesting and sheet packing."""
        path1 = Path()
        path1.move(0, 0)
        path1.line(50, 0)
        path1.line(50, 50)
        path1.line(0, 50)
        path1.closed()

        node1 = self.elements.elem_branch.add(type="elem path", path=path1)
        node1.emphasized = True

        packed, eff = nest_elements(self.elements, sheet_width_mm=300.0, sheet_height_mm=200.0, margin_mm=2.0)
        self.assertGreaterEqual(packed, 1)
        self.assertGreater(eff, 0.0)

    def test_2d_polygon_nesting_with_rotation_packs_a_narrow_shape_tighter(self):
        # rotation_steps used to be accepted but never actually used (a
        # dead parameter) -- verify it now really tries alternate
        # orientations by checking the PLACED bbox width directly: a
        # 90x10 plank stays ~90 wide without rotation, but rotation_steps=4
        # must find the 90-degree orientation and place it ~10 wide instead.
        def make_plank():
            path = Path()
            path.move(complex(0, 0))
            path.line(complex(90, 0))
            path.line(complex(90, 10))
            path.line(complex(0, 10))
            path.closed()
            node = self.elements.elem_branch.add(type="elem path", path=path)
            node.emphasized = True
            return node

        node_no_rotate = make_plank()
        nest_elements(self.elements, sheet_width_mm=300.0, sheet_height_mm=300.0, margin_mm=1.0, rotation_steps=1)
        bounds_no_rotate = node_no_rotate.bounds
        self.assertAlmostEqual(bounds_no_rotate[2] - bounds_no_rotate[0], 90.0, delta=1.0)

        node_no_rotate.emphasized = False
        node_rotated = make_plank()
        nest_elements(self.elements, sheet_width_mm=300.0, sheet_height_mm=300.0, margin_mm=1.0, rotation_steps=4)
        bounds_rotated = node_rotated.bounds
        self.assertAlmostEqual(bounds_rotated[2] - bounds_rotated[0], 10.0, delta=1.0,
                                msg="rotation_steps=4 must find the 90-degree orientation for a wide, short plank")

    def test_3d_grayscale_relief_engine(self):
        """Test 3D grayscale heightmap raster generation."""
        img = np.zeros((10, 10), dtype=np.uint8)
        img[2:8, 2:8] = 128

        result = generate_3d_laser_relief(img, max_power_percent=100.0, min_power_percent=10.0)
        self.assertEqual(len(result["scan_lines"]), 10)
        self.assertGreater(result["max_s"], result["min_s"])

    def test_relief_3d_preview_dialog_computes_stats(self):
        """Test the Relief 3D preview dialog's stats-only calculate button."""
        from PyQt6.QtWidgets import QApplication
        app = QApplication.instance()
        if app is None:
            app = QApplication([])

        from madgrav.qt.qt_laser_dialogs import Relief3DPreviewDialog

        # Asymmetric (20 wide x 8 tall) array -- the dialog must report
        # the real width/height/scan-line count, not a square/degenerate one.
        img = np.zeros((8, 20), dtype=np.uint8)
        img[2:6, 5:15] = 200

        dialog = Relief3DPreviewDialog()
        dialog.set_image(img)
        dialog.spin_min_power.setValue(5.0)
        dialog.spin_max_power.setValue(90.0)
        dialog._on_preview()

        report_text = dialog.lbl_report.text()
        self.assertIn("20 x 8", report_text)
        self.assertNotIn("Aucune image", report_text)

    def test_galvo_hatch_patterns(self):
        """Test Galvo laser hatch line generation and wobble vector patterns."""
        # Asymmetric bbox (200 x 60, not square) -- a regression check for
        # the Path.move(x, y)/.line(x, y) scalar-vs-complex(x, y) bug that
        # silently collapsed generated geometry onto the X axis (Y == 0).
        path = Path()
        path.move(complex(0, 0))
        path.line(complex(200, 0))
        path.line(complex(200, 60))
        path.line(complex(0, 60))
        path.closed()

        hatch = apply_galvo_hatch(path, hatch_angle_deg=45.0, line_spacing_mm=1.0, mode="cross")
        self.assertIsInstance(hatch, Path)
        self.assertGreater(len(hatch), 0)
        hbbox = hatch.bbox()
        self.assertIsNotNone(hbbox)
        self.assertGreater(hbbox[3] - hbbox[1], 10.0, "hatch must span the source path's Y extent, not collapse to Y=0")
        self.assertGreater(hbbox[2] - hbbox[0], 10.0)

        wobble_hatch = apply_galvo_hatch(path, mode="wobble")
        self.assertIsInstance(wobble_hatch, Path)
        self.assertGreater(len(wobble_hatch), 0)
        wbbox = wobble_hatch.bbox()
        self.assertIsNotNone(wbbox)
        self.assertGreater(wbbox[3] - wbbox[1], 10.0)

    def test_galvo_hatch_angle_actually_rotates_the_pattern(self):
        # hatch_angle_deg used to be accepted but never used (a dead
        # parameter, same class of bug as nesting's rotation_steps) --
        # verify 0deg and 45deg produce genuinely different first-move
        # coordinates, and that coverage of the original bbox holds at
        # every angle (the hatch area is built from the bbox's
        # half-diagonal specifically so rotation can't leave gaps).
        #
        # Path coordinates must be in NATIVE units (UNITS_PER_MM-scaled),
        # same convention as every real caller (box/gear/qr generators)
        # -- apply_galvo_hatch's line_spacing_mm is converted via
        # UNITS_PER_MM internally, so an unscaled raw-unit test path would
        # make a "small" mm spacing enormous relative to the shape.
        from madgrav.core.units import UNITS_PER_MM

        w, h = 100.0 * UNITS_PER_MM, 40.0 * UNITS_PER_MM
        path = Path()
        path.move(complex(0, 0))
        path.line(complex(w, 0))
        path.line(complex(w, h))
        path.line(complex(0, h))
        path.closed()

        hatch_0 = apply_galvo_hatch(path, hatch_angle_deg=0.0, line_spacing_mm=5.0, mode="cross")
        hatch_45 = apply_galvo_hatch(path, hatch_angle_deg=45.0, line_spacing_mm=5.0, mode="cross")

        first_move_0 = complex(hatch_0[0].end.x, hatch_0[0].end.y)
        first_move_45 = complex(hatch_45[0].end.x, hatch_45[0].end.y)
        self.assertNotAlmostEqual(first_move_0.real, first_move_45.real, places=2)

        # A discrete grid of parallel lines only guarantees AREA coverage,
        # not that a line segment lands exactly at the original rectangle's
        # corner at every angle -- a generous tolerance (relative to the
        # shape's own size) checks "still roughly covers the shape after
        # rotating", not pixel-perfect edge reach.
        tol = 0.25 * w
        for angle in (0.0, 30.0, 45.0, 90.0, 135.0):
            hatch = apply_galvo_hatch(path, hatch_angle_deg=angle, line_spacing_mm=5.0, mode="cross")
            hbbox = hatch.bbox()
            self.assertIsNotNone(hbbox)
            self.assertLessEqual(hbbox[0], tol, f"angle {angle} must still roughly cover the original bbox's left half")
            self.assertGreaterEqual(hbbox[2], w - tol, f"angle {angle} must still roughly cover the original bbox's right half")

    def test_smart_vectorization(self):
        """Test converting bitmap contour arrays into smooth Bezier vector paths."""
        # Asymmetric mask block (20 wide x 60 tall) -- same collapse-bug
        # regression check as above, at the OpenCV-contour input boundary.
        img = np.ones((100, 100), dtype=np.uint8) * 255
        img[20:80, 30:50] = 0

        paths = vectorize_bitmap_to_bezier(img, threshold=128)
        self.assertGreaterEqual(len(paths), 1)
        self.assertIsInstance(paths[0], Path)
        bbox = paths[0].bbox()
        self.assertIsNotNone(bbox)
        self.assertGreater(bbox[3] - bbox[1], 30.0, "traced contour must span its real Y extent, not collapse to Y=0")
        self.assertGreater(bbox[2] - bbox[0], 10.0)

    def test_smart_vectorize_corner_and_tolerance_params_actually_simplify(self):
        # corner_threshold_deg/error_tolerance_mm used to be accepted but
        # silently ignored (a dead pair of parameters). A traced CIRCLE has
        # many gentle-angle vertices along its curve -- a high angle
        # threshold must collapse most of them. A traced SQUARE has four
        # sharp 90-degree corners -- those must all survive regardless.
        import cv2

        circle_img = np.ones((100, 100), dtype=np.uint8) * 255
        cv2.circle(circle_img, (50, 50), 35, 0, thickness=-1)
        loose_paths = vectorize_bitmap_to_bezier(circle_img, threshold=128, corner_threshold_deg=0.0, error_tolerance_mm=0.01)
        tight_paths = vectorize_bitmap_to_bezier(circle_img, threshold=128, corner_threshold_deg=60.0, error_tolerance_mm=0.01)
        self.assertGreaterEqual(len(loose_paths), 1)
        self.assertGreaterEqual(len(tight_paths), 1)
        self.assertLess(
            len(tight_paths[0]), len(loose_paths[0]),
            "a high corner_threshold_deg must simplify away a circle's many gentle-angle vertices",
        )

        square_img = np.ones((100, 100), dtype=np.uint8) * 255
        square_img[20:80, 20:80] = 0
        square_paths = vectorize_bitmap_to_bezier(square_img, threshold=128, corner_threshold_deg=60.0, error_tolerance_mm=0.01)
        self.assertGreaterEqual(len(square_paths), 1)
        square_bbox = square_paths[0].bbox()
        self.assertAlmostEqual(square_bbox[2] - square_bbox[0], 60.0, delta=2.0, msg="sharp 90-degree corners must survive simplification")
        self.assertAlmostEqual(square_bbox[3] - square_bbox[1], 60.0, delta=2.0)


if __name__ == "__main__":
    unittest.main()
