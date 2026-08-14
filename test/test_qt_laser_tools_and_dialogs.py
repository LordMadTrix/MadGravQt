"""
Comprehensive integration and UI tests for MadGrav Qt Workstation tools and laser dialogs.
Tests every dialog in qt_laser_dialogs.py and every tool action in qt_main.py.
"""

import math
import os
import unittest
from unittest.mock import patch, MagicMock
import numpy as np

try:
    from PyQt6.QtCore import QPoint, QPointF, QSettings, Qt, QTimer
    from PyQt6.QtGui import QAction, QColor, QImage
    from PyQt6.QtTest import QTest
    from PyQt6.QtWidgets import (
        QApplication,
        QCheckBox,
        QColorDialog,
        QDialog,
        QDoubleSpinBox,
        QFileDialog,
        QGraphicsView,
        QInputDialog,
        QMenu,
        QMessageBox,
        QPushButton,
        QSpinBox,
        QToolBar,
        QToolButton,
    )
    HAS_QT = True
except ImportError:
    HAS_QT = False

from test import bootstrap

if HAS_QT:
    from madgrav.device import basedevice
    from madgrav.extra import cag
    from madgrav.qt.qt_main import MadGravQtMainWindow
    from madgrav.qt.qt_laser_dialogs import (
        BoxGeneratorDialog,
        GearGeneratorDialog,
        JigsawGeneratorDialog,
        MaterialTestDialog,
        GridArrayDialog,
        CircularArrayDialog,
        SlotFitterDialog,
        MaterialLibraryDialog,
        LivingHingesDialog,
        MultiHeadWizardDialog,
        GCodePreviewDialog,
        ProductionQueueDialog,
        NestingDialog,
        JobQuoteDialog,
        SmartVectorizeDialog,
        Relief3DPreviewDialog,
        NodeEditorDialog,
        GalvoHatchDialog,
    )
    from madgrav.svgelements import Path, Rect, Circle
    from PIL import Image


@unittest.skipUnless(HAS_QT, "PyQt6 not installed")
class TestQtLaserToolsAndDialogs(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        QSettings("MadGrav", "QtGUI").clear()
        self.kernel = bootstrap.bootstrap(plugins=[basedevice.plugin, cag.plugin])
        self.root = self.kernel.root
        self.root("service device start dummy 0\n")
        self.win = MadGravQtMainWindow(self.root)
        self.win.show()
        self.app.processEvents()
        QTest.qWait(50)
        self._orig_warning = QMessageBox.warning
        self._orig_information = QMessageBox.information
        self._orig_question = QMessageBox.question
        QMessageBox.warning = MagicMock(return_value=QMessageBox.StandardButton.Ok)
        QMessageBox.information = MagicMock(return_value=QMessageBox.StandardButton.Ok)
        QMessageBox.question = MagicMock(return_value=QMessageBox.StandardButton.Yes)

    def tearDown(self):
        QMessageBox.warning = self._orig_warning
        QMessageBox.information = self._orig_information
        QMessageBox.question = self._orig_question
        self.win._closing_from_kernel = True
        self.win.close()
        QSettings("MadGrav", "QtGUI").clear()

    def test_box_generator_dialog(self):
        with patch.object(QDialog, 'exec', return_value=QDialog.DialogCode.Accepted):
            self.win._on_box_generator_dialog()
        elements = self.root.elements
        nodes = list(elements.elems())
        self.assertGreater(len(nodes), 0)

    def test_gear_generator_dialog(self):
        with patch.object(QDialog, 'exec', return_value=QDialog.DialogCode.Accepted):
            self.win._on_gear_generator_dialog()
        elements = self.root.elements
        nodes = list(elements.elems())
        self.assertGreater(len(nodes), 0)

    def test_jigsaw_generator_dialog(self):
        with patch.object(QDialog, 'exec', return_value=QDialog.DialogCode.Accepted):
            self.win._on_jigsaw_generator_dialog()
        elements = self.root.elements
        nodes = list(elements.elems())
        self.assertGreater(len(nodes), 0)

    def test_material_test_dialog(self):
        with patch.object(QDialog, 'exec', return_value=QDialog.DialogCode.Accepted):
            self.win._on_material_test_dialog()
        elements = self.root.elements
        nodes = list(elements.elems())
        self.assertGreater(len(nodes), 0)

    def test_grid_and_circular_array(self):
        self.root("rect 0 0 10mm 10mm\n")
        self.root("element* select\n")
        with patch.object(QDialog, 'exec', return_value=QDialog.DialogCode.Accepted):
            self.win._on_grid_array_dialog()
        self.assertGreater(len(list(self.root.elements.elems())), 1)

        with patch.object(QDialog, 'exec', return_value=QDialog.DialogCode.Accepted):
            self.win._on_circular_array_dialog()
        self.assertGreater(len(list(self.root.elements.elems())), 2)

    def test_living_hinges_dialog(self):
        with patch.object(QDialog, 'exec', return_value=QDialog.DialogCode.Accepted):
            self.win._on_living_hinges_dialog()
        self.assertGreater(len(list(self.root.elements.elems())), 0)

    def test_slot_fitter_dialog(self):
        self.root("rect 0 0 20mm 20mm\n")
        self.root("element* select\n")
        with patch.object(QDialog, 'exec', return_value=QDialog.DialogCode.Accepted):
            self.win._on_slot_fitter_dialog()

    def test_material_library_dialog(self):
        self.root("rect 0 0 10mm 10mm cut -s 20 -p 800\n")
        with patch.object(QDialog, 'exec', return_value=QDialog.DialogCode.Accepted):
            self.win._on_material_library_dialog()

    def test_multi_head_wizard_dialog(self):
        with patch.object(QDialog, 'exec', return_value=QDialog.DialogCode.Accepted):
            self.win._on_multi_head_wizard_dialog()

    def test_production_queue_dialog(self):
        with patch.object(QDialog, 'exec', return_value=QDialog.DialogCode.Accepted):
            self.win._on_production_queue_dialog()

    def test_gcode_simulation_dialog(self):
        with patch.object(QDialog, 'exec', return_value=QDialog.DialogCode.Accepted):
            self.win._on_gcode_simulation_dialog()

    def test_job_quote_dialog(self):
        self.root("rect 0 0 20mm 20mm cut -s 20\n")
        with patch.object(QDialog, 'exec', return_value=QDialog.DialogCode.Accepted):
            self.win._on_job_quote_dialog()

    def test_nesting_dialog(self):
        self.root("rect 0 0 10mm 10mm\n")
        self.root("rect 20mm 0 15mm 15mm\n")
        self.root("element* select\n")
        with patch.object(QDialog, 'exec', return_value=QDialog.DialogCode.Accepted):
            self.win._on_nesting_dialog()

    def test_smart_vectorize_and_relief(self):
        # Create an image node
        img = Image.new("RGB", (64, 64), color="white")
        # draw a black square in middle
        for x in range(20, 44):
            for y in range(20, 44):
                img.putpixel((x, y), (0, 0, 0))
        img_node = self.root.elements.elem_branch.add(
            type="elem image",
            image=img,
            matrix=None,
        )
        img_node.emphasized = True
        self.win._update_selection_dependent_actions()

        with patch.object(QDialog, 'exec', return_value=QDialog.DialogCode.Accepted):
            self.win._on_smart_vectorize_dialog()

        with patch.object(QDialog, 'exec', return_value=QDialog.DialogCode.Accepted):
            self.win._on_relief_3d_dialog()

    def test_node_editor_and_galvo_hatch(self):
        self.root("rect 0 0 20mm 20mm\n")
        self.root("element* select\n")
        self.win._update_selection_dependent_actions()

        with patch.object(QDialog, 'exec', return_value=QDialog.DialogCode.Accepted):
            self.win._on_node_editor_dialog()

        with patch.object(QDialog, 'exec', return_value=QDialog.DialogCode.Accepted):
            self.win._on_galvo_hatch_dialog()

    def test_micro_tabs_and_kerf(self):
        self.root("rect 0 0 20mm 20mm\n")
        self.root("element* select\n")
        with patch.object(QDialog, 'exec', return_value=QDialog.DialogCode.Accepted), \
             patch("PyQt6.QtWidgets.QMessageBox.information", return_value=None):
            self.win._on_micro_tabs_dialog()
            self.win._on_kerf_lead_dialog()
            self.win._on_stamp_mode_dialog()
            self.win._on_optimize_cut_order()
            self.win._on_variable_text_dialog()
            self.win._on_rotary_assistant_dialog()
            self.win._on_cost_estimator_dialog()
            self.win._on_measure_objects_dialog()
            self.win._on_print_and_cut_dialog()
            self.win._on_camera_autocal_dialog()
