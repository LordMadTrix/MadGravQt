"""
Unit tests for Material Library, Rotary Assistant, and Cost Estimator:
- Material Library Preset database & application
- Rotary Setup parameter calculations
- Laser Job Time & Cost Estimator
"""

import unittest
from test.bootstrap import bootstrap
from madgrav.svgelements import Path, Color

from madgrav.tools.material_library import MaterialLibrary, MaterialPreset, apply_material_preset
from madgrav.tools.rotary_assistant import calculate_rotary_parameters
from madgrav.tools.cost_estimator import estimate_job_cost


class TestMaterialRotaryCost(unittest.TestCase):
    def setUp(self):
        self.kernel = bootstrap()
        self.elements = self.kernel.elements

    def test_material_library(self):
        """Test Material Library default presets and project application."""
        lib = MaterialLibrary()
        self.assertGreater(len(lib.presets), 0)

        preset = lib.get_preset("Wood", 3.0, "cut")
        self.assertIsNotNone(preset)
        self.assertEqual(preset.speed, 20.0)

        # Test applying preset to project operations
        op_node = self.elements.op_branch.add(type="op cut", color=Color("red"), speed=5.0, power=100.0)
        applied = apply_material_preset(self.elements, "Wood", 3.0, "cut")
        self.assertTrue(applied)
        self.assertEqual(op_node.speed, 20.0)

    def test_rotary_assistant(self):
        """Test Rotary Attachment calculations for chuck and roller setups."""
        # Chuck rotary test for a 80mm diameter tumbler
        res_chuck = calculate_rotary_parameters(
            object_diameter_mm=80.0,
            steps_per_rev=200,
            microstepping=16,
            is_chuck=True,
        )

        self.assertAlmostEqual(res_chuck["circumference_mm"], 251.327, delta=0.1)
        self.assertGreater(res_chuck["pulses_per_mm"], 0.0)

        # Roller rotary test
        res_roller = calculate_rotary_parameters(
            object_diameter_mm=80.0,
            roller_diameter_mm=50.0,
            is_chuck=False,
        )
        self.assertGreater(res_roller["pulses_per_mm"], 0.0)

    def test_cost_estimator(self):
        """Test Laser Job duration and cost estimation."""
        path = Path()
        path.move(0, 0)
        path.line(10000, 0)
        path.line(10000, 10000)
        path.line(0, 10000)
        path.closed()

        elem_node = self.elements.elem_branch.add(type="elem path", path=path)
        op_node = self.elements.op_branch.add(type="op cut", speed=20.0, power=800.0)
        op_node.add_reference(elem_node)

        est = estimate_job_cost(
            self.elements,
            hourly_rate_eur=30.0,
            material_cost_sqm_eur=20.0,
            power_kw=0.5,
            electricity_cost_kwh_eur=0.25,
        )

        self.assertGreater(est["total_cut_length_mm"], 0.0)
        self.assertGreater(est["estimated_duration_sec"], 0.0)
        self.assertGreater(est["total_cost_eur"], 0.0)


if __name__ == "__main__":
    unittest.main()
