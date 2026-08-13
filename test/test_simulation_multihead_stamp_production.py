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
        path.move(0, 0)
        path.line(50, 0)
        path.line(50, 50)
        path.closed()

        stamp = generate_rubber_stamp_profile(path)
        self.assertIsInstance(stamp, Path)

        puzzle = generate_jigsaw_puzzle_grid(width_mm=100.0, height_mm=100.0, rows=3, cols=3)
        self.assertIsInstance(puzzle, Path)
        self.assertGreater(len(puzzle), 0)

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


if __name__ == "__main__":
    unittest.main()
