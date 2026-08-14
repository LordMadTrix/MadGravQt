import unittest
import numpy as np
from PIL import Image

from madgrav.tools.halftone_studio import (
    generate_halftone_dots,
    generate_line_wave_halftone,
    generate_spiral_halftone,
    generate_stipple_halftone,
    generate_halftone_job,
)


class TestHalftoneStudio(unittest.TestCase):
    def setUp(self):
        # Create a 100x100 grayscale gradient image
        arr = np.tile(np.linspace(0, 255, 100, dtype=np.uint8), (100, 1))
        self.test_img = Image.fromarray(arr, mode="L")

    def test_generate_halftone_dots(self):
        dots = generate_halftone_dots(
            self.test_img,
            width_mm=50.0,
            height_mm=50.0,
            pitch_mm=5.0,
            min_dot_mm=0.5,
            max_dot_mm=4.5,
            angle_deg=45.0,
            invert=False,
        )
        self.assertIsInstance(dots, list)
        self.assertGreater(len(dots), 10)
        # Each dot is a tuple: (cx, cy, radius)
        cx, cy, r = dots[0]
        self.assertIsInstance(cx, float)
        self.assertIsInstance(cy, float)
        self.assertIsInstance(r, float)
        self.assertGreater(r, 0.0)

    def test_generate_line_wave_halftone(self):
        waves = generate_line_wave_halftone(
            self.test_img,
            width_mm=50.0,
            height_mm=50.0,
            line_spacing_mm=2.5,
            max_amplitude_mm=1.0,
            frequency=2.0,
        )
        self.assertIsInstance(waves, list)
        self.assertGreater(len(waves), 5)
        # Each wave is a list of (x, y) points
        first_wave = waves[0]
        self.assertGreater(len(first_wave), 5)
        self.assertEqual(len(first_wave[0]), 2)

    def test_generate_spiral_halftone(self):
        spiral = generate_spiral_halftone(
            self.test_img,
            diameter_mm=50.0,
            ring_spacing_mm=2.0,
            max_dot_mm=3.0,
        )
        self.assertIsInstance(spiral, list)
        self.assertGreater(len(spiral), 10)

    def test_generate_stipple_halftone(self):
        stipples = generate_stipple_halftone(
            self.test_img,
            width_mm=50.0,
            height_mm=50.0,
            point_count=200,
            dot_diameter_mm=1.0,
        )
        self.assertIsInstance(stipples, list)
        self.assertEqual(len(stipples), 200)

    def test_generate_halftone_job_svg(self):
        svg_str = generate_halftone_job(
            self.test_img,
            method="dots",
            width_mm=60.0,
            height_mm=60.0,
            pitch_mm=4.0,
        )
        self.assertIsInstance(svg_str, str)
        self.assertIn("<svg", svg_str)
        self.assertIn("<circle", svg_str)


if __name__ == "__main__":
    unittest.main()
