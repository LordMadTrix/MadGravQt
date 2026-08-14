import unittest
import sys

from test import bootstrap
from madgrav.device import basedevice
from madgrav.extra import cag

try:
    from PyQt6.QtCore import Qt
    from PyQt6.QtGui import QPixmap, QImage, QColor
    from PyQt6.QtWidgets import QApplication
    from madgrav.qt.qt_main import MadGravQtMainWindow
    HAS_QT = True
except ImportError:
    HAS_QT = False


@unittest.skipUnless(HAS_QT, "PyQt6 not installed")
class TestQtCameraBedOverlay(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication(sys.argv)

    def setUp(self):
        self.kernel = bootstrap.bootstrap(plugins=[basedevice.plugin, cag.plugin])
        self.root = self.kernel.root
        self.root("service device start dummy 0\n")
        self.win = MadGravQtMainWindow(self.root)
        self.win.show()
        self.app.processEvents()

    def tearDown(self):
        if hasattr(self, "win") and self.win:
            self.win.close()

    def test_canvas_camera_overlay_properties(self):
        canvas = self.win.canvas
        self.assertIsNotNone(canvas)

        # Create dummy test image
        img = QImage(300, 200, QImage.Format.Format_RGB32)
        img.fill(QColor(200, 200, 200))
        pixmap = QPixmap.fromImage(img)

        # Test setting camera overlay
        canvas.set_camera_overlay(pixmap, opacity=0.75, visible=True)
        self.assertTrue(canvas.camera_overlay_visible)
        self.assertEqual(canvas.camera_overlay_opacity, 0.75)
        self.assertIsNotNone(canvas.camera_overlay_pixmap)

        # Test opacity change
        canvas.set_camera_opacity(0.3)
        self.assertEqual(canvas.camera_overlay_opacity, 0.3)

        # Test toggle
        canvas.toggle_camera_overlay(False)
        self.assertFalse(canvas.camera_overlay_visible)
        canvas.toggle_camera_overlay(True)
        self.assertTrue(canvas.camera_overlay_visible)

    def test_main_window_camera_actions(self):
        self.assertTrue(hasattr(self.win, "_on_toggle_camera_overlay"))
        self.win._on_toggle_camera_overlay()
        self.assertTrue(self.win.canvas.camera_overlay_visible)
        self.win._on_toggle_camera_overlay()
        self.assertFalse(self.win.canvas.camera_overlay_visible)


if __name__ == "__main__":
    unittest.main()
