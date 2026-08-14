import os
import tempfile
import unittest

from test import bootstrap
from madgrav.device import basedevice
from madgrav.extra import cag

try:
    from PyQt6.QtWidgets import QApplication
    from madgrav.qt.qt_laser_dialogs import VariableTextMergeDialog
    from madgrav.tools.variable_text import (
        parse_csv_or_excel,
        generate_merged_variable_layout,
    )
    HAS_QT = True
except ImportError:
    HAS_QT = False


@unittest.skipUnless(HAS_QT, "PyQt6 not installed")
class TestQtVariableTextCsvMerge(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.kernel = bootstrap.bootstrap(plugins=[basedevice.plugin, cag.plugin])
        self.root = self.kernel.root
        self.root("service device start dummy 0\n")
        self.elements = self.kernel.elements
        self.temp_dir = tempfile.TemporaryDirectory()

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_parse_csv(self):
        csv_path = os.path.join(self.temp_dir.name, "badges.csv")
        with open(csv_path, "w", encoding="utf-8") as f:
            f.write("Nom,Prenom,Matricule\n")
            f.write("Dupont,Jean,001\n")
            f.write("Martin,Sophie,002\n")
            f.write("Durand,Paul,003\n")

        records = parse_csv_or_excel(csv_path)
        self.assertEqual(len(records), 3)
        self.assertEqual(records[0]["Nom"], "Dupont")
        self.assertEqual(records[0]["Prenom"], "Jean")
        self.assertEqual(records[0]["Matricule"], "001")

    def test_generate_merged_variable_layout(self):
        records = [
            {"Nom": "Dupont", "ID": "101"},
            {"Nom": "Martin", "ID": "102"},
            {"Nom": "Durand", "ID": "103"},
        ]
        created = generate_merged_variable_layout(
            self.elements,
            records=records,
            template_pattern="{Nom} #{ID}",
            columns=2,
            spacing_x_mm=40.0,
            spacing_y_mm=15.0,
        )
        self.assertEqual(len(created), 3)
        elem_list = list(self.elements.elems())
        self.assertGreaterEqual(len(elem_list), 3)

    def test_variable_text_dialog_ui(self):
        csv_path = os.path.join(self.temp_dir.name, "test_ui.csv")
        with open(csv_path, "w", encoding="utf-8") as f:
            f.write("Item,Serial\n")
            f.write("LaserBadge,A01\n")
            f.write("LaserBadge,A02\n")

        dlg = VariableTextMergeDialog()
        self.assertIsNotNone(dlg.edit_template)
        self.assertIsNotNone(dlg.table_preview)
        self.assertIsNotNone(dlg.spin_cols)

        dlg.load_file(csv_path)
        self.assertEqual(dlg.table_preview.rowCount(), 2)
        params = dlg.get_parameters()
        self.assertEqual(len(params["records"]), 2)
        dlg.close()


if __name__ == "__main__":
    unittest.main()
