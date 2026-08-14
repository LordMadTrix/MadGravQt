import unittest
import os
import sys

os.environ["QT_QPA_PLATFORM"] = "offscreen"
from test import bootstrap
from madgrav.device import basedevice
from madgrav.extra import cag

try:
    from PyQt6.QtWidgets import QApplication
    from PyQt6.QtTest import QTest
    from madgrav.qt.qt_main import MadGravQtMainWindow
    from madgrav.qt.qt_document import DocumentTab
    HAS_QT = True
except ImportError:
    HAS_QT = False


@unittest.skipUnless(HAS_QT, "PyQt6 not installed")
class TestQtMultiDocumentTabs(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication(sys.argv)

    def setUp(self):
        self.kernel = bootstrap.bootstrap(plugins=[basedevice.plugin, cag.plugin])
        self.root = self.kernel.root
        self.root("service device start dummy 0\n")
        self.main_window = MadGravQtMainWindow(self.root)
        self.main_window.show()
        self.app.processEvents()

    def tearDown(self):
        if hasattr(self, "main_window") and self.main_window:
            self.main_window.close()

    def test_document_tab_creation_and_isolation(self):
        doc1 = DocumentTab(self.main_window, title="Document 1")
        self.assertIsNotNone(doc1.canvas)
        self.assertEqual(doc1.title, "Document 1")
        self.assertIsNone(doc1.file_path)
        self.assertFalse(doc1.is_modified)

        doc2 = DocumentTab(self.main_window, title="Document 2")
        self.assertNotEqual(doc1.canvas, doc2.canvas)

    def test_main_window_tab_widget_interaction(self):
        self.assertIsNotNone(self.main_window.doc_tabs)
        initial_count = self.main_window.doc_tabs.count()
        self.assertGreaterEqual(initial_count, 1)

        # Create a new document tab
        new_tab = self.main_window.create_new_document(title="Projet Test 2")
        self.assertEqual(self.main_window.doc_tabs.count(), initial_count + 1)
        self.assertEqual(self.main_window.current_document(), new_tab)
        self.assertEqual(self.main_window.canvas, new_tab.canvas)

        # Switch tabs
        self.main_window.doc_tabs.setCurrentIndex(0)
        self.assertNotEqual(self.main_window.current_document(), new_tab)

        # Close tab
        self.main_window.close_document_tab(initial_count)
        self.assertEqual(self.main_window.doc_tabs.count(), initial_count)


if __name__ == "__main__":
    unittest.main()
