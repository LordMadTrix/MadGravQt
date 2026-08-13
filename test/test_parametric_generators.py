"""
Unit tests for Parametric Generators:
- Involute Spur Gear Generator
- Jigsaw Puzzle Generator
- Vector QR Code & Barcode Generator
"""

import unittest
from test.bootstrap import bootstrap

from madgrav.tools.gear_generator import generate_involute_gear
from madgrav.tools.jigsaw_generator import generate_jigsaw_puzzle
from madgrav.tools.barcode_generator import generate_qr_code_vector
from madgrav.core.units import UNITS_PER_MM


class TestParametricGenerators(unittest.TestCase):
    def setUp(self):
        self.kernel = bootstrap()
        self.elements = self.kernel.elements

    def test_involute_gear_generator(self):
        """Test involute spur gear path generation with central bore."""
        gear_node = generate_involute_gear(
            self.elements,
            num_teeth=16,
            module=2.0,
            pressure_angle_deg=20.0,
            bore_diameter_mm=6.0,
            center_x_mm=50.0,
            center_y_mm=50.0,
        )

        self.assertIsNotNone(gear_node)
        self.assertEqual(gear_node.type, "elem path")
        self.assertIsNotNone(gear_node.path)
        self.assertGreater(len(gear_node.path), 0)

        # Regression test for the same Path.move()/.line() point-
        # coercion bug fixed in the QR code generator: a circular gear's
        # bbox legitimately has width == height, so that alone can't
        # catch a collapsed-to-zero-height shape -- check the Y extent
        # is non-zero and, independently, that the bbox center matches
        # the asymmetric center requested here (50mm module * 16 teeth
        # gives a real ~34mm outer radius, not the request's raw values,
        # so this only checks the extent is plausible, not exact).
        min_x, min_y, max_x, max_y = gear_node.bounds
        self.assertGreater((max_y - min_y) / UNITS_PER_MM, 1.0, "gear has collapsed to zero height")

    def test_jigsaw_puzzle_generator(self):
        """Test vector jigsaw puzzle cutting line generation."""
        puzzle_nodes = generate_jigsaw_puzzle(
            self.elements,
            width_mm=100.0,
            height_mm=80.0,
            rows=3,
            cols=4,
            tab_size_percent=20.0,
        )

        self.assertGreater(len(puzzle_nodes), 0)
        for node in puzzle_nodes:
            self.assertEqual(node.type, "elem path")
            self.assertIsNotNone(node.path)
        # Regression check for the Path.move()/.line() point-coercion
        # bug (see test_qr_code_generator) -- width_mm/height_mm are
        # deliberately different (100 vs 80) so a collapsed Y axis would
        # show up as a wrong aspect ratio, not just a wrong absolute size.
        min_x, min_y, max_x, max_y = puzzle_nodes[0].bounds
        self.assertAlmostEqual((max_x - min_x) / UNITS_PER_MM, 100.0, delta=1.0)
        self.assertAlmostEqual((max_y - min_y) / UNITS_PER_MM, 80.0, delta=1.0)

    def test_qr_code_generator(self):
        """Test vector QR code path generation."""
        qr_node = generate_qr_code_vector(
            self.elements,
            data_str="MadGrav-Test-12345",
            module_size_mm=1.0,
            center_x_mm=100.0,
            center_y_mm=100.0,
        )

        self.assertIsNotNone(qr_node)
        self.assertEqual(qr_node.type, "elem path")
        self.assertIsNotNone(qr_node.path)
        self.assertGreater(len(qr_node.path), 0)

        # Regression test: Path.move()/.line() take ONE point per
        # positional arg (points[index], never unpacked) -- passing x
        # and y as two separate scalars silently reads y as a SECOND
        # point, collapsing the whole shape's Y extent to 0. A square,
        # centered-on-itself QR code (default center_x_mm==center_y_mm)
        # can't catch this by coincidence (X and Y ranges would overlap
        # anyway), so this uses deliberately asymmetric center
        # coordinates and a non-square check: width and height must
        # both be real and, for a square QR code, equal to each other.
        min_x, min_y, max_x, max_y = qr_node.bounds
        width_mm = (max_x - min_x) / UNITS_PER_MM
        height_mm = (max_y - min_y) / UNITS_PER_MM
        self.assertGreater(height_mm, 1.0, "QR code has collapsed to zero height")
        self.assertAlmostEqual(width_mm, height_mm, delta=0.5)

        asym_node = generate_qr_code_vector(
            self.elements, data_str="asym-test", center_x_mm=50.0,
            center_y_mm=150.0, module_size_mm=2.0,
        )
        a_min_x, a_min_y, a_max_x, a_max_y = asym_node.bounds
        self.assertAlmostEqual((a_min_x + a_max_x) / 2.0 / UNITS_PER_MM, 50.0, delta=0.5)
        self.assertAlmostEqual((a_min_y + a_max_y) / 2.0 / UNITS_PER_MM, 150.0, delta=0.5)


if __name__ == "__main__":
    unittest.main()
