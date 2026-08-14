"""Unit tests for Maker, Vision, Nesting & Workshop Workflow Suite."""

import unittest
import os
import math

from PyQt6.QtWidgets import QApplication

# Initialize offscreen Qt app for testing
os.environ["QT_QPA_PLATFORM"] = "offscreen"
app = QApplication.instance() or QApplication([])

from madgrav.tools.inlay_generator import generate_inlay_paths, offset_polygon
from madgrav.tools.tslot_box_generator import generate_tslot_panels, get_standard_hardware_dims
from madgrav.tools.scrap_finder import find_usable_scrap_zones
from madgrav.tools.print_and_cut import compute_2point_transform, apply_transform_point
from madgrav.tools.trueshape_nesting import pack_shapes_2d
from madgrav.tools.material_matrix import generate_material_test_matrix_data
from madgrav.tools.laser_timeline import calculate_move_time, analyze_job_timeline

from madgrav.qt.qt_laser_dialogs import (
    InlayWizardDialog,
    TSlotBoxDialog,
    ScrapFinderDialog,
    PrintAndCutDialog,
    TrueShapeNestingDialog,
    MaterialMatrixTestDialog,
    LaserTimelineDialog,
    WorkshopKioskWindow,
)


class TestInlayGenerator(unittest.TestCase):
    def test_offset_polygon(self):
        square = [(0.0, 0.0), (10.0, 0.0), (10.0, 10.0), (0.0, 10.0), (0.0, 0.0)]
        offset_pts = offset_polygon(square, 1.0)
        self.assertEqual(len(offset_pts), 5)
        self.assertEqual(offset_pts[0], offset_pts[-1])

    def test_generate_inlay_paths(self):
        star = [(0.0, 0.0), (5.0, 10.0), (10.0, 0.0), (0.0, 0.0)]
        res = generate_inlay_paths(star, kerf_mm=0.2, clearance_mm=0.05, mode="balanced")
        self.assertIn("male_path", res)
        self.assertIn("female_path", res)
        self.assertEqual(res["kerf_mm"], 0.2)
        self.assertEqual(res["clearance_mm"], 0.05)


class TestTSlotBoxGenerator(unittest.TestCase):
    def test_hardware_dims(self):
        m3 = get_standard_hardware_dims("M3")
        self.assertEqual(m3["screw_dia"], 3.2)
        m4 = get_standard_hardware_dims("M4")
        self.assertEqual(m4["screw_dia"], 4.2)
        m5 = get_standard_hardware_dims("M5")
        self.assertEqual(m5["screw_dia"], 5.2)

    def test_generate_tslot_panels(self):
        res = generate_tslot_panels(width=120.0, height=80.0, depth=60.0, thickness=3.0, hardware="M3")
        self.assertEqual(len(res["panels"]), 6)
        self.assertGreater(res["total_width"], 0)
        self.assertGreater(res["total_height"], 0)
        # Check that top/bottom panels exist
        panel_ids = [p["id"] for p in res["panels"]]
        self.assertIn("bottom", panel_ids)
        self.assertIn("top", panel_ids)
        self.assertIn("front", panel_ids)


class TestScrapFinder(unittest.TestCase):
    def test_find_scrap_empty_bed(self):
        zones = find_usable_scrap_zones(800, 600, bed_width_mm=400.0, bed_height_mm=300.0)
        self.assertEqual(len(zones), 1)
        self.assertEqual(zones[0]["area_mm2"], 120000.0)

    def test_find_scrap_with_cutouts(self):
        cutouts = [(50.0, 50.0, 100.0, 100.0)]
        zones = find_usable_scrap_zones(800, 600, bed_width_mm=400.0, bed_height_mm=300.0, cutout_rects=cutouts, min_area_mm2=50.0)
        self.assertGreater(len(zones), 0)
        self.assertTrue(all(z["area_mm2"] >= 50.0 for z in zones))


class TestPrintAndCut(unittest.TestCase):
    def test_compute_2point_transform_identity(self):
        p1 = (10.0, 10.0)
        p2 = (110.0, 10.0)
        tf = compute_2point_transform(p1, p2, p1, p2)
        self.assertAlmostEqual(tf["scale"], 1.0, places=3)
        self.assertAlmostEqual(tf["rotation_deg"], 0.0, places=3)
        self.assertAlmostEqual(tf["tx"], 0.0, places=3)
        self.assertAlmostEqual(tf["ty"], 0.0, places=3)

    def test_apply_transform_translation_and_scale(self):
        src_p1 = (0.0, 0.0)
        src_p2 = (10.0, 0.0)
        dst_p1 = (5.0, 5.0)
        dst_p2 = (25.0, 5.0)  # scale 2.0, tx = 5, ty = 5
        tf = compute_2point_transform(src_p1, src_p2, dst_p1, dst_p2)
        self.assertAlmostEqual(tf["scale"], 2.0, places=3)
        pt_transformed = apply_transform_point((5.0, 0.0), tf)
        self.assertEqual(pt_transformed, (15.0, 5.0))


class TestTrueShapeNesting(unittest.TestCase):
    def test_pack_shapes_2d(self):
        parts = [
            {"id": 1, "name": "PartA", "w": 50.0, "h": 40.0},
            {"id": 2, "name": "PartB", "w": 30.0, "h": 20.0},
            {"id": 3, "name": "PartC", "w": 60.0, "h": 50.0},
        ]
        res = pack_shapes_2d(parts, sheet_w=200.0, sheet_h=200.0, margin=5.0, spacing=2.0)
        self.assertEqual(res["total_placed"], 3)
        self.assertEqual(res["total_unplaced"], 0)
        self.assertGreater(res["efficiency_pct"], 0.0)


class TestMaterialMatrix(unittest.TestCase):
    def test_generate_material_matrix_data(self):
        speeds = [10.0, 50.0, 100.0]
        powers = [20.0, 50.0, 80.0]
        res = generate_material_test_matrix_data(speeds=speeds, powers=powers, cell_w=10.0, cell_h=10.0)
        self.assertEqual(len(res["cells"]), 9)  # 3 x 3
        self.assertEqual(len(res["labels"]), 6)  # 3 speeds + 3 powers
        self.assertGreater(res["total_width"], 0)
        self.assertGreater(res["total_height"], 0)


class TestLaserTimeline(unittest.TestCase):
    def test_calculate_move_time_trapezoid(self):
        res = calculate_move_time(distance_mm=100.0, target_speed_mm_s=50.0, accel_mm_s2=2500.0)
        self.assertGreater(res["total_time_s"], 0)
        self.assertEqual(res["peak_speed"], 50.0)

    def test_analyze_job_timeline(self):
        moves = [
            {"type": "rapid", "distance_mm": 50.0, "speed": 200.0},
            {"type": "cut", "distance_mm": 100.0, "speed": 20.0, "power": 80.0},
            {"type": "rapid", "distance_mm": 20.0, "speed": 200.0},
        ]
        res = analyze_job_timeline(moves)
        self.assertGreater(res["total_duration_s"], 0)
        self.assertGreater(res["total_cut_time_s"], 0)
        self.assertGreater(res["total_rapid_time_s"], 0)
        self.assertEqual(len(res["timeline"]), 3)


class TestQtMegaSuiteDialogs(unittest.TestCase):
    def test_inlay_dialog(self):
        dlg = InlayWizardDialog()
        self.assertIsNotNone(dlg)
        self.assertEqual(dlg.spin_kerf.value(), 0.15)
        dlg.close()

    def test_tslot_dialog(self):
        dlg = TSlotBoxDialog()
        self.assertIsNotNone(dlg)
        self.assertEqual(dlg.spin_w.value(), 100.0)
        dlg.close()

    def test_scrap_finder_dialog(self):
        dlg = ScrapFinderDialog()
        self.assertIsNotNone(dlg)
        self.assertEqual(dlg.spin_min_area.value(), 200.0)
        dlg.close()

    def test_print_and_cut_dialog(self):
        dlg = PrintAndCutDialog()
        self.assertIsNotNone(dlg)
        self.assertEqual(dlg.combo_mode.count(), 2)
        dlg.close()

    def test_trueshape_nesting_dialog(self):
        dlg = TrueShapeNestingDialog()
        self.assertIsNotNone(dlg)
        self.assertEqual(dlg.spin_sheet_w.value(), 400.0)
        dlg.close()

    def test_material_matrix_dialog(self):
        dlg = MaterialMatrixTestDialog()
        self.assertIsNotNone(dlg)
        self.assertEqual(dlg.spin_cols.value(), 5)
        dlg.close()

    def test_laser_timeline_dialog(self):
        dlg = LaserTimelineDialog()
        self.assertIsNotNone(dlg)
        self.assertEqual(dlg.spin_accel.value(), 3000.0)
        dlg.close()

    def test_workshop_kiosk_window(self):
        win = WorkshopKioskWindow()
        self.assertIsNotNone(win)
        self.assertIsNotNone(win.btn_start)
        self.assertIsNotNone(win.btn_stop)
        win.close()


if __name__ == "__main__":
    unittest.main()
