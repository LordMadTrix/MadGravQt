import unittest
import sys

from test import bootstrap
from madgrav.device import basedevice
from madgrav.extra import cag

try:
    from PyQt6.QtWidgets import QApplication
    from madgrav.qt.qt_laser_dialogs import RotaryAssistantDialog
    from madgrav.tools.rotary_assistant import calculate_rotary_parameters
    HAS_QT = True
except ImportError:
    HAS_QT = False


@unittest.skipUnless(HAS_QT, "PyQt6 not installed")
class TestQtRotaryAssistant(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication(sys.argv)

    def test_calculate_rotary_parameters(self):
        # Chuck test
        res_chuck = calculate_rotary_parameters(object_diameter_mm=50.0, is_chuck=True)
        self.assertAlmostEqual(res_chuck["circumference_mm"], 157.079, places=2)
        self.assertGreater(res_chuck["pulses_per_mm"], 0)

        # Roller test
        res_roller = calculate_rotary_parameters(object_diameter_mm=50.0, roller_diameter_mm=40.0, is_chuck=False)
        self.assertAlmostEqual(res_roller["circumference_mm"], 157.079, places=2)
        self.assertGreater(res_roller["pulses_per_mm"], 0)

    def test_rotary_assistant_dialog_ui(self):
        dlg = RotaryAssistantDialog()
        self.assertIsNotNone(dlg.diameter_spin)
        self.assertIsNotNone(dlg.chuck_radio)
        self.assertIsNotNone(dlg.roller_radio)
        self.assertIsNotNone(dlg.pulses_label)

        # Change values and trigger calculation
        dlg.diameter_spin.setValue(80.0)
        dlg.chuck_radio.setChecked(True)
        dlg._update_calculations()

        params = dlg.get_parameters()
        self.assertEqual(params["object_diameter_mm"], 80.0)
        self.assertTrue(params["is_chuck"])
        self.assertGreater(params["pulses_per_mm"], 0)
        dlg.close()


if __name__ == "__main__":
    unittest.main()
