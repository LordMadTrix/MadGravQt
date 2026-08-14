import unittest
import numpy as np
from PIL import Image
from PyQt6.QtWidgets import QApplication, QDialog

from madgrav.kernel import Kernel
from madgrav.qt.qt_laser_dialogs import (
    HalftoneStudioDialog,
    TopoMapDialog,
    MandalaDialog,
    WebRemoteQrDialog,
)
from madgrav.qt.qt_main import MadGravQtMainWindow


from test import bootstrap
from madgrav.device import basedevice
from madgrav.extra import cag


class TestQtArtAndRemoteDialogs(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.kernel = bootstrap.bootstrap(plugins=[basedevice.plugin, cag.plugin])
        self.root = self.kernel.root
        self.root("service device start dummy 0\n")
        self.win = MadGravQtMainWindow(self.root)
        self.win.show()
        self.app.processEvents()

    def tearDown(self):
        self.win._closing_from_kernel = True
        self.win.close()
        self.kernel()

    def test_halftone_studio_dialog(self):
        dlg = HalftoneStudioDialog(self.win)
        self.assertIsInstance(dlg, QDialog)
        self.assertEqual(dlg.windowTitle(), "Studio Gravure Photo & Demi-Teintes")
        # Provide a synthetic test image
        img = Image.fromarray(np.full((50, 50), 128, dtype=np.uint8), mode="L")
        dlg.current_image = img
        dlg.apply_halftone()
        # Verify elements added to document
        elements = list(self.win.context.elements.flat())
        self.assertGreater(len(elements), 0)

    def test_topo_map_dialog(self):
        dlg = TopoMapDialog(self.win)
        self.assertIsInstance(dlg, QDialog)
        self.assertEqual(dlg.windowTitle(), "Générateur de Cartes Topographiques 3D")
        dlg.spin_layers.setValue(4)
        dlg.apply_topo_map()
        elements = list(self.win.context.elements.flat())
        self.assertGreater(len(elements), 0)

    def test_mandala_dialog(self):
        dlg = MandalaDialog(self.win)
        self.assertIsInstance(dlg, QDialog)
        self.assertEqual(dlg.windowTitle(), "Générateur de Mandalas & Rosaces")
        dlg.spin_symmetry.setValue(8)
        dlg.apply_mandala()
        elements = list(self.win.context.elements.flat())
        self.assertGreater(len(elements), 0)

    def test_web_remote_qr_dialog(self):
        dlg = WebRemoteQrDialog(self.win)
        self.assertIsInstance(dlg, QDialog)
        self.assertEqual(dlg.windowTitle(), "Télécommande Mobile Web")
        self.assertIn("http://", dlg.url_edit.text())
        self.assertIsNotNone(dlg.qr_label.pixmap())
        self.assertFalse(dlg.qr_label.pixmap().isNull())
        self.assertGreater(dlg.qr_label.pixmap().width(), 0)

    def test_menu_actions_exist_and_wired(self):
        from PyQt6.QtGui import QAction
        actions = {a.text(): a for a in self.win.findChildren(QAction)}
        self.assertIn("🖼️ Studio Gravure Photo & Demi-Teintes...", actions)
        self.assertIn("🗺️ Générateur de Cartes Topo 3D...", actions)
        self.assertIn("🌸 Générateur de Mandalas & Rosaces...", actions)
        self.assertIn("📱 Télécommande Mobile Web (QR Code)...", actions)


if __name__ == "__main__":
    unittest.main()
