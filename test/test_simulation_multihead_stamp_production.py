"""
Unit tests for 3D Simulation, Multi-Head Calibration, Stamp/Puzzle & Production Queue Suite:
- 3D G-Code & Path Simulation Engine (gcode_previewer.py)
- Dual-Head Laser Calibration Wizard (multi_head_wizard.py)
- Rubber Stamp Shoulders & Jigsaw Puzzle Generator (stamp_puzzle_generator.py)
- Production Queue & Workshop Kiosk Mode Manager (production_queue.py)
"""

import unittest
from test.bootstrap import bootstrap
from madgrav.svgelements import Path

from madgrav.tools.gcode_previewer import simulate_laser_path_3d
from madgrav.tools.multi_head_wizard import calculate_dual_head_offset
from madgrav.tools.stamp_puzzle_generator import generate_rubber_stamp_profile, generate_jigsaw_puzzle_grid
from madgrav.tools.production_queue import ProductionQueueManager


class TestSimulationMultiHeadStampProduction(unittest.TestCase):
    def setUp(self):
        self.kernel = bootstrap()
        self.elements = self.kernel.elements

    def test_3d_gcode_simulation_engine(self):
        """Test parsing G-Code text and calculating 3D trajectory & job time."""
        gcode = """
        G0 X0 Y0 Z0 S0
        G1 X10 Y0 Z0 S100
        G1 X10 Y10 Z0 S100
        G1 X0 Y10 Z0 S100
        G0 X0 Y0 Z0 S0
        """
        report = simulate_laser_path_3d(gcode, travel_speed_mm_s=200.0, cut_speed_mm_s=20.0)
        self.assertEqual(report["point_count"], 5)
        self.assertGreater(report["cut_dist_mm"], 0.0)
        self.assertGreater(report["total_time_sec"], 0.0)

    def test_dual_head_laser_calibration(self):
        """Test dual-head laser offset calculation and matrix generation."""
        cal = calculate_dual_head_offset((10.0, 20.0), (12.5, 23.0))
        self.assertEqual(cal["delta_x"], 2.5)
        self.assertEqual(cal["delta_y"], 3.0)
        self.assertGreater(cal["distance_mm"], 0.0)
        self.assertEqual(len(cal["offset_matrix"]), 3)

    def test_stamp_and_jigsaw_generator(self):
        """Test rubber stamp shoulder profiling and parametric jigsaw puzzle generation."""
        path = Path()
        path.move(complex(0, 0))
        path.line(complex(50, 0))
        path.line(complex(50, 50))
        path.closed()

        stamp = generate_rubber_stamp_profile(path)
        self.assertIsInstance(stamp, Path)

        # Asymmetric grid (120 x 80, not square) -- a regression check for
        # the Path.move/.line collapse-to-Y=0 bug in the outer border and
        # tab-cut construction.
        puzzle = generate_jigsaw_puzzle_grid(width_mm=120.0, height_mm=80.0, rows=3, cols=4)
        self.assertIsInstance(puzzle, Path)
        self.assertGreater(len(puzzle), 0)
        bbox = puzzle.bbox()
        self.assertIsNotNone(bbox)
        self.assertAlmostEqual(bbox[2] - bbox[0], 120.0, delta=1.0)
        self.assertAlmostEqual(bbox[3] - bbox[1], 80.0, delta=1.0)

    def test_stamp_shoulder_rings_grow_with_width_and_ramp_angle(self):
        # shoulder_width_mm/ramp_angle_deg used to be accepted but never
        # used (same class of bug as nesting's rotation_steps and galvo's
        # hatch_angle_deg) -- verify a real shoulder now widens the
        # profile's bbox, and that a shallower ramp angle produces more
        # concentric step rings (more segments) than a steep one.
        from madgrav.core.units import UNITS_PER_MM

        w = 50.0 * UNITS_PER_MM
        path = Path()
        path.move(complex(0, 0))
        path.line(complex(w, 0))
        path.line(complex(w, w))
        path.line(complex(0, w))
        path.closed()

        no_shoulder = generate_rubber_stamp_profile(path, shoulder_width_mm=0.0)
        with_shoulder = generate_rubber_stamp_profile(path, shoulder_width_mm=2.0, ramp_angle_deg=45.0)
        no_bbox = no_shoulder.bbox()
        with_bbox = with_shoulder.bbox()
        self.assertGreater(with_bbox[2] - with_bbox[0], no_bbox[2] - no_bbox[0], "a real shoulder must widen the bbox")
        self.assertGreater(len(with_shoulder), len(no_shoulder))

        steep = generate_rubber_stamp_profile(path, shoulder_width_mm=2.0, ramp_angle_deg=75.0)
        shallow = generate_rubber_stamp_profile(path, shoulder_width_mm=2.0, ramp_angle_deg=15.0)
        self.assertLess(len(steep), len(shallow), "a shallower ramp angle must produce more step rings")

    def test_production_queue_manager(self):
        """Test batch production job queue, barcode lookup, and completion metrics."""
        mgr = ProductionQueueManager()
        job = mgr.add_job(job_name="Acrylic Keychain", file_path="keychain.svg", quantity=10, priority=2, barcode="JOB-001")

        found = mgr.lookup_job_by_barcode("JOB-001")
        self.assertIsNotNone(found)
        self.assertEqual(found["name"], "Acrylic Keychain")

        next_job = mgr.get_next_job()
        self.assertEqual(next_job["id"], job["id"])

        success = mgr.mark_job_completed(job["id"], duration_sec=120.0)
        self.assertTrue(success)

        summary = mgr.export_production_summary()
        self.assertEqual(summary["completed_count"], 1)
        self.assertEqual(summary["total_parts_produced"], 10)

    def test_laser_tool_dialogs_instantiation(self):
        """Test instantiation of new Qt laser tool dialog classes."""
        from PyQt6.QtWidgets import QApplication
        app = QApplication.instance()
        if app is None:
            app = QApplication([])

        from madgrav.qt.qt_laser_dialogs import (
            LivingHingesDialog,
            MultiHeadWizardDialog,
            GCodePreviewDialog,
            ProductionQueueDialog,
            NestingDialog,
            JobQuoteDialog,
        )

        dlg_hinge = LivingHingesDialog()
        self.assertEqual(dlg_hinge.spin_width.value(), 100.0)

        dlg_wizard = MultiHeadWizardDialog()
        self.assertEqual(dlg_wizard.spin_h1_x.value(), 10.0)

        dlg_sim = GCodePreviewDialog()
        self.assertIn("G0 X0 Y0", dlg_sim.txt_gcode.toPlainText())

        dlg_queue = ProductionQueueDialog()
        self.assertEqual(dlg_queue.spin_qty.value(), 10)

        dlg_nest = NestingDialog()
        self.assertEqual(dlg_nest.spin_sheet_w.value(), 300.0)

        dlg_quote = JobQuoteDialog()
        self.assertEqual(dlg_quote.spin_margin_pct.value(), 20.0)

    def test_job_quote_dialog_calculates_from_elements(self):
        """Test the Job Quote dialog's live calculate button against real elements."""
        from PyQt6.QtWidgets import QApplication
        app = QApplication.instance()
        if app is None:
            app = QApplication([])

        from madgrav.qt.qt_laser_dialogs import JobQuoteDialog
        from madgrav.svgelements import Path

        path = Path()
        path.move(complex(0, 0))
        path.line(complex(1000, 0))
        path.line(complex(1000, 1000))
        path.line(complex(0, 1000))
        path.closed()
        self.elements.elem_branch.add(type="elem path", path=path)

        dlg = JobQuoteDialog()
        dlg.set_elements_service(self.elements)
        dlg._on_calculate()
        self.assertIn("DEVIS TOTAL", dlg.lbl_report.text())


if __name__ == "__main__":
    unittest.main()

