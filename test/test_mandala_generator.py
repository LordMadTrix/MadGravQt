import unittest
from madgrav.tools.mandala_generator import (
    generate_mandala_paths,
    generate_mandala_svg,
)


class TestMandalaGenerator(unittest.TestCase):
    def test_generate_mandala_paths_floral(self):
        paths = generate_mandala_paths(
            symmetry=8,
            outer_radius_mm=50.0,
            inner_radius_mm=10.0,
            rings=3,
            style="floral",
        )
        self.assertIsInstance(paths, list)
        self.assertGreater(len(paths), 5)
        # Check coordinates validity
        for path in paths:
            self.assertGreater(len(path), 2)
            for x, y in path:
                self.assertIsInstance(x, float)
                self.assertIsInstance(y, float)

    def test_generate_mandala_paths_starburst_and_gothic(self):
        star_paths = generate_mandala_paths(
            symmetry=12,
            outer_radius_mm=60.0,
            inner_radius_mm=5.0,
            rings=4,
            style="starburst",
        )
        self.assertGreater(len(star_paths), 10)

        gothic_paths = generate_mandala_paths(
            symmetry=6,
            outer_radius_mm=40.0,
            inner_radius_mm=5.0,
            rings=2,
            style="gothic",
        )
        self.assertGreater(len(gothic_paths), 5)

    def test_generate_mandala_svg(self):
        svg_str = generate_mandala_svg(
            symmetry=16,
            outer_radius_mm=75.0,
            inner_radius_mm=8.0,
            rings=4,
            style="sacred",
        )
        self.assertIsInstance(svg_str, str)
        self.assertIn("<svg", svg_str)
        self.assertIn("<path", svg_str)
        self.assertIn("</svg>", svg_str)


if __name__ == "__main__":
    unittest.main()
