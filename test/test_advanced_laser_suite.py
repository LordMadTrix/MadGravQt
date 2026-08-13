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

    def test_3d_grayscale_relief_engine(self):
        """Test 3D grayscale heightmap raster generation."""
        img = np.zeros((10, 10), dtype=np.uint8)
        img[2:8, 2:8] = 128

        result = generate_3d_laser_relief(img, max_power_percent=100.0, min_power_percent=10.0)
        self.assertEqual(len(result["scan_lines"]), 10)
        self.assertGreater(result["max_s"], result["min_s"])

    def test_galvo_hatch_patterns(self):
        """Test Galvo laser hatch line generation and wobble vector patterns."""
        path = Path()
        path.move(0, 0)
        path.line(100, 0)
        path.line(100, 100)
        path.line(0, 100)
        path.closed()

        hatch = apply_galvo_hatch(path, hatch_angle_deg=45.0, line_spacing_mm=1.0, mode="cross")
        self.assertIsInstance(hatch, Path)
        self.assertGreater(len(hatch), 0)

        wobble_hatch = apply_galvo_hatch(path, mode="wobble")
        self.assertIsInstance(wobble_hatch, Path)
        self.assertGreater(len(wobble_hatch), 0)

    def test_smart_vectorization(self):
        """Test converting bitmap contour arrays into smooth Bezier vector paths."""
        img = np.ones((100, 100), dtype=np.uint8) * 255
        img[30:70, 30:70] = 0

        paths = vectorize_bitmap_to_bezier(img, threshold=128)
        self.assertGreaterEqual(len(paths), 1)
        self.assertIsInstance(paths[0], Path)


if __name__ == "__main__":
    unittest.main()
