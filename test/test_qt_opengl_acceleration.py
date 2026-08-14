import unittest
import sys

from test import bootstrap
from madgrav.device import basedevice
from madgrav.extra import cag

try:
    from PyQt6.QtWidgets import QApplication
    from madgrav.qt.qt_main import MadGravQtMainWindow
    HAS_QT = True
except ImportError:
    HAS_QT = False


@unittest.skipUnless(HAS_QT, "PyQt6 not installed")
class TestQtOpenGLAcceleration(unittest.TestCase):
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

    def test_opengl_toggle_canvas(self):
        canvas = self.win.canvas
        self.assertIsNotNone(canvas)
        self.assertTrue(hasattr(canvas, "enable_opengl"))

        # Enable OpenGL
        ok = canvas.enable_opengl(True)
        self.assertTrue(canvas.is_opengl_enabled)

        # Disable OpenGL
        canvas.enable_opengl(False)
        self.assertFalse(canvas.is_opengl_enabled)

    def test_main_window_opengl_action(self):
        self.assertTrue(hasattr(self.win, "_on_toggle_opengl"))
        self.win._on_toggle_opengl(True)
        self.assertTrue(self.win.canvas.is_opengl_enabled)
        self.win._on_toggle_opengl(False)
        self.assertFalse(self.win.canvas.is_opengl_enabled)


if __name__ == "__main__":
    unittest.main()
