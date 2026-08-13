"""
Unit tests for Advanced LightBurn Tools:
- Finger-Jointed 3D Box Generator
- Rubber Stamp Mode & 3D Relief Tool
- Inner-First Cut Order Optimizer
"""

import unittest
from test.bootstrap import bootstrap
from madgrav.svgelements import Path, Color

from madgrav.tools.box_generator import generate_finger_box
from madgrav.tools.stamp_mode import apply_stamp_mode
from madgrav.tools.cut_optimizer import optimize_cut_order


class TestAdvancedLightBurnTools(unittest.TestCase):
    def setUp(self):
        self.kernel = bootstrap()
        self.elements = self.kernel.elements

    def test_finger_box_generator(self):
        """Test 3D finger-jointed box 2D panel unfolding generation."""
        nodes = generate_finger_box(
            self.elements,
            width_mm=80.0,
            height_mm=60.0,
            depth_mm=40.0,
            thickness_mm=3.0,
            tab_width_mm=10.0,
            kerf_mm=0.1,
            open_top=False,
        )

        # 6 box panels generated
        self.assertEqual(len(nodes), 6)
        panels_by_label = {n.label: n for n in nodes}
        from madgrav.core.units import UNITS_PER_MM

        def panel_size_mm(label):
            node = panels_by_label[f"Box Panel: {label}"]
            min_x, min_y, max_x, max_y = node.bounds
            return (max_x - min_x) / UNITS_PER_MM, (max_y - min_y) / UNITS_PER_MM

        for node in nodes:
            self.assertEqual(node.type, "elem path")
            self.assertIsNotNone(node.path)

        # Bottom/Top have no finger tabs on their edges (male_edges all
        # False in box_generator.py) so their size is exactly width x
        # depth. Front/Back/Left/Right have tabs protruding outward,
        # so they're larger than their nominal size -- but Front/Back's
        # height must still match Left/Right's height exactly, since
        # those are the mating edges of the assembled box.
        self.assertAlmostEqual(panel_size_mm("Bottom")[0], 80.0, delta=0.5)
        self.assertAlmostEqual(panel_size_mm("Bottom")[1], 40.0, delta=0.5)
        self.assertAlmostEqual(panel_size_mm("Top")[0], 80.0, delta=0.5)
        self.assertAlmostEqual(panel_size_mm("Top")[1], 40.0, delta=0.5)
        front_h = panel_size_mm("Front")[1]
        self.assertGreater(front_h, 60.0)  # tabs add extra height beyond nominal
        self.assertAlmostEqual(panel_size_mm("Back")[1], front_h, delta=0.1)
        self.assertAlmostEqual(panel_size_mm("Left")[1], front_h, delta=0.1)
        self.assertAlmostEqual(panel_size_mm("Right")[1], front_h, delta=0.1)

    def test_stamp_mode(self):
        """Test rubber stamp shoulder expansion and inverted border generation."""
        path = Path()
        path.move(100, 100)
        path.line(200, 100)
        path.line(200, 200)
        path.line(100, 200)
        path.closed()

        node = self.elements.elem_branch.add(type="elem path", path=path)
        node.emphasized = True

        stamp_nodes = apply_stamp_mode(
            self.elements,
            nodes=[node],
            shoulder_width_mm=0.5,
            margin_mm=3.0,
            invert=True,
        )

        self.assertGreater(len(stamp_nodes), 1)

    def test_cut_optimizer_inner_first(self):
        """Test Inner-First cut ordering optimization."""
        # Outer boundary square
        outer_path = Path()
        outer_path.move(0, 0)
        outer_path.line(1000, 0)
        outer_path.line(1000, 1000)
        outer_path.line(0, 1000)
        outer_path.closed()

        # Inner hole square inside outer boundary
        inner_path = Path()
        inner_path.move(200, 200)
        inner_path.line(400, 200)
        inner_path.line(400, 400)
        inner_path.line(200, 400)
        inner_path.closed()

        # Add outer first, inner second
        n_outer = self.elements.elem_branch.add(type="elem path", path=outer_path)
        n_inner = self.elements.elem_branch.add(type="elem path", path=inner_path)

        # Optimize order
        reordered = optimize_cut_order(self.elements, nodes=[n_outer, n_inner], inner_first=True, minimize_travel=True)

        # Inner hole must be sorted first
        self.assertEqual(reordered[0], n_inner)
        self.assertEqual(reordered[1], n_outer)


if __name__ == "__main__":
    unittest.main()
