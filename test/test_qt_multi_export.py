import os
import tempfile
import unittest

from test import bootstrap
from madgrav.device import basedevice
from madgrav.extra import cag

try:
    from PyQt6.QtWidgets import QApplication
    from madgrav.qt.qt_laser_dialogs import MultiFormatExportDialog
    from madgrav.tools.multi_export import export_job_to_file
    from madgrav.svgelements import Rect
    HAS_QT = True
except ImportError:
    HAS_QT = False


@unittest.skipUnless(HAS_QT, "PyQt6 not installed")
class TestQtMultiExport(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.kernel = bootstrap.bootstrap(plugins=[basedevice.plugin, cag.plugin])
        self.root = self.kernel.root
        self.root("service device start dummy 0\n")
        self.root("rect 10mm 10mm 50mm 30mm cut -s 20 -p 1000\n")
        self.elements = self.kernel.elements
        self.temp_dir = tempfile.TemporaryDirectory()

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_export_gcode(self):
        out_path = os.path.join(self.temp_dir.name, "output.gcode")
        res = export_job_to_file(self.elements, out_path, format_type="gcode", laser_power=80.0, speed_mm_s=25.0)
        self.assertTrue(res)
        self.assertTrue(os.path.exists(out_path))
        with open(out_path, "r", encoding="utf-8") as f:
            content = f.read()
            self.assertIn("G21", content)  # Metric units
            self.assertIn("M3", content)   # Laser on
            self.assertIn("M5", content)   # Laser off

    def test_export_rd_and_egv(self):
        rd_path = os.path.join(self.temp_dir.name, "output.rd")
        res_rd = export_job_to_file(self.elements, rd_path, format_type="rd")
        self.assertTrue(res_rd)
        self.assertTrue(os.path.exists(rd_path))

        egv_path = os.path.join(self.temp_dir.name, "output.egv")
        res_egv = export_job_to_file(self.elements, egv_path, format_type="egv")
        self.assertTrue(res_egv)
        self.assertTrue(os.path.exists(egv_path))

    def test_export_dxf_and_svg(self):
        dxf_path = os.path.join(self.temp_dir.name, "output.dxf")
        res_dxf = export_job_to_file(self.elements, dxf_path, format_type="dxf")
        self.assertTrue(res_dxf)
        self.assertTrue(os.path.exists(dxf_path))

        svg_path = os.path.join(self.temp_dir.name, "output.svg")
        res_svg = export_job_to_file(self.elements, svg_path, format_type="svg")
        self.assertTrue(res_svg)
        self.assertTrue(os.path.exists(svg_path))

    def test_multi_format_export_dialog_ui(self):
        dlg = MultiFormatExportDialog()
        self.assertIsNotNone(dlg.combo_format)
        self.assertIsNotNone(dlg.edit_path)
        self.assertIsNotNone(dlg.spin_power)
        self.assertIsNotNone(dlg.spin_speed)

        out_path = os.path.join(self.temp_dir.name, "dialog_test.gcode")
        dlg.edit_path.setText(out_path)
        params = dlg.get_parameters()
        self.assertEqual(params["filepath"], out_path)
        dlg.close()


if __name__ == "__main__":
    unittest.main()
