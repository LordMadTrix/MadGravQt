"""
Unit tests for Ultimate LightBurn Features:
- Variable Text Substitution & Serialization
- Print & Cut (2-Point Registration Alignment)
- Slot & Notch Auto-Fitter
"""

import unittest
from test.bootstrap import bootstrap
from madgrav.svgelements import Path, Matrix

from madgrav.tools.variable_text import substitute_variable_text, apply_variable_text_serialization
from madgrav.tools.print_and_cut import compute_print_and_cut_transform, apply_print_and_cut_alignment
from madgrav.tools.slot_fitter import adjust_slot_thickness, apply_slot_fitter_to_nodes


class TestUltimateLightBurnFeatures(unittest.TestCase):
    def setUp(self):
        self.kernel = bootstrap()
        self.elements = self.kernel.elements

    def test_variable_text_substitution_and_serialization(self):
        """Test variable text tag substitution and CSV batch serialization."""
        template = "Item #{serial:04d} - Date: {date} - Val: {csv:value}"
        csv_row = {"value": "ABC-123"}

        res = substitute_variable_text(template, index=4, csv_row=csv_row)
        self.assertIn("Item #0005", res)
        self.assertIn("ABC-123", res)

        # Serialization test
        t_node = self.elements.elem_branch.add(type="elem text", text=template)
        t_node.emphasized = True

        csv_rows = [{"value": "A"}, {"value": "B"}, {"value": "C"}]
        created = apply_variable_text_serialization(self.elements, nodes=[t_node], csv_rows=csv_rows)

        self.assertEqual(len(created), 3)
        self.assertIn("A", created[0].text)
        self.assertIn("B", created[1].text)
        self.assertIn("C", created[2].text)

    def test_print_and_cut_2_point_alignment(self):
        """Test 2-Point Print & Cut registration transform matrix calculation."""
        p1_design = (0.0, 0.0)
        p1_real = (10.0, 20.0)

        p2_design = (100.0, 0.0)
        p2_real = (100.0, 100.0)  # Rotated & scaled

        M = compute_print_and_cut_transform(p1_design, p1_real, p2_design, p2_real)
        self.assertIsInstance(M, Matrix)

        # Test point transformation
        pt1 = M.point_in_matrix_space(p1_design)
        self.assertAlmostEqual(pt1[0], p1_real[0], delta=0.001)
        self.assertAlmostEqual(pt1[1], p1_real[1], delta=0.001)

        pt2 = M.point_in_matrix_space(p2_design)
        self.assertAlmostEqual(pt2[0], p2_real[0], delta=0.001)
        self.assertAlmostEqual(pt2[1], p2_real[1], delta=0.001)

    def test_slot_fitter(self):
        """Test slot and notch thickness adjustment."""
        # Create a rectangular slot path with width 3mm
        path = Path()
        path.move(0, 0)
        path.line(300, 0)
        path.line(300, 1000)
        path.line(0, 1000)
        path.closed()

        res_path = adjust_slot_thickness(path, old_thickness_mm=3.0, new_thickness_mm=5.0)
        self.assertIsInstance(res_path, Path)


if __name__ == "__main__":
    unittest.main()
