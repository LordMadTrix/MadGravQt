"""
Unit tests for Multi-Camera, Node Editing, Living Hinges & Job Costing Suite:
- Multi-Camera Optical Stitching (stitching.py)
- Vector Node Editor & Bezier Control Handles (node_editor.py)
- Parametric Living Hinge Generator (flex_hinge.py)
- Job Cost Estimator & Quote Generator (cost_quote.py)
"""

import unittest
import numpy as np
from test.bootstrap import bootstrap
from madgrav.svgelements import Path

from madgrav.camera.stitching import stitch_multi_camera_views
from madgrav.tools.node_editor import VectorNodeEditor
from madgrav.tools.flex_hinge import generate_living_hinge
from madgrav.tools.cost_quote import generate_job_quote


class TestMultiCameraNodesHingesCosting(unittest.TestCase):
    def setUp(self):
        self.kernel = bootstrap()
        self.elements = self.kernel.elements

    def test_multi_camera_stitching(self):
        """Test Multi-Camera perspective warping and seamless view stitching."""
        cam1 = np.ones((100, 100, 3), dtype=np.uint8) * 100
        cam2 = np.ones((100, 100, 3), dtype=np.uint8) * 200

        H1 = np.eye(3).tolist()
        H2 = np.eye(3).tolist()

        composite = stitch_multi_camera_views([cam1, cam2], [H1, H2], target_bed_width_mm=100.0, target_bed_height_mm=100.0)
        self.assertIsInstance(composite, np.ndarray)
        self.assertEqual(composite.shape[:2], (200, 200))

    def test_vector_node_editor(self):
        """Test vector path node extraction, moving, insertion, and deletion."""
        path = Path()
        path.move(0, 0)
        path.line(100, 0)
        path.line(100, 100)
        path.closed()

        nodes = VectorNodeEditor.extract_nodes_and_handles(path)
        self.assertGreaterEqual(len(nodes), 2)

        success = VectorNodeEditor.move_node(path, 1, 120, 0)
        self.assertTrue(success)

        inserted = VectorNodeEditor.insert_node(path, 0)
        self.assertTrue(inserted)

        deleted = VectorNodeEditor.delete_node(path, 1)
        self.assertTrue(deleted)

    def test_node_editor_dialog_lists_and_edits_nodes(self):
        """Test the list-based Node Editor dialog against a real Path."""
        from PyQt6.QtWidgets import QApplication
        app = QApplication.instance()
        if app is None:
            app = QApplication([])

        from madgrav.qt.qt_laser_dialogs import NodeEditorDialog
        from madgrav.core.units import UNITS_PER_MM

        path = Path()
        path.move(complex(0, 0))
        path.line(complex(100 * UNITS_PER_MM, 0))
        path.line(complex(100 * UNITS_PER_MM, 100 * UNITS_PER_MM))
        path.closed()

        dialog = NodeEditorDialog(path=path, units_per_mm=UNITS_PER_MM)
        initial_count = dialog.list_nodes.count()
        self.assertGreaterEqual(initial_count, 2)

        changed = []
        dialog.on_changed = lambda: changed.append(1)

        dialog.list_nodes.setCurrentRow(1)
        dialog.spin_x.setValue(120.0)
        dialog.spin_y.setValue(0.0)
        dialog._on_move()
        self.assertEqual(len(changed), 1)
        self.assertAlmostEqual(path[1].end.x, 120.0 * UNITS_PER_MM, delta=1.0)

        dialog.list_nodes.setCurrentRow(0)
        dialog._on_insert()
        self.assertEqual(dialog.list_nodes.count(), initial_count + 1)

        dialog.list_nodes.setCurrentRow(1)
        dialog._on_delete()
        self.assertEqual(dialog.list_nodes.count(), initial_count)

    def test_node_editor_dialog_gives_feedback_when_delete_is_refused(self):
        # delete_node() refuses to go below 1 remaining point -- the
        # dialog used to silently ignore that (click did nothing, no
        # explanation) instead of telling the user why, same silent-
        # failure class fixed elsewhere in this app's dialogs this
        # session.
        from PyQt6.QtWidgets import QApplication
        app = QApplication.instance()
        if app is None:
            app = QApplication([])

        from madgrav.qt.qt_laser_dialogs import NodeEditorDialog

        # delete_node()'s guard is len(path) <= 1 -- a bare Move with no
        # further segments (not even .closed(), which adds a Close
        # segment of its own) is the actual single-segment case.
        path = Path()
        path.move(complex(0, 0))

        dialog = NodeEditorDialog(path=path, units_per_mm=1.0)
        changed = []
        dialog.on_changed = lambda: changed.append(1)

        dialog.list_nodes.setCurrentRow(0)
        dialog._on_delete()

        self.assertEqual(len(changed), 0, "on_changed must not fire for a refused delete")
        self.assertNotEqual(dialog.lbl_status.text(), "")

    def test_parametric_living_hinge_generator(self):
        """Test parametric flex-cut living hinge pattern generation."""
        from madgrav.core.units import UNITS_PER_MM

        # width_mm != height_mm (50 vs 100) is itself an asymmetric-extent
        # regression check for the Path.move/.line collapse-to-Y=0 bug;
        # the bbox assertion additionally confirms the returned Path is in
        # native document units (UNITS_PER_MM), not raw mm floats -- a
        # second bug that would otherwise make the hinge ~3.8x too small
        # once added to the document.
        hinge_straight = generate_living_hinge(width_mm=50.0, height_mm=100.0, pattern="straight")
        self.assertIsInstance(hinge_straight, Path)
        self.assertGreater(len(hinge_straight), 0)
        bbox = hinge_straight.bbox()
        self.assertIsNotNone(bbox)
        self.assertGreater(bbox[3] - bbox[1], 50.0 * UNITS_PER_MM, "hinge must span most of height_mm in native units, not collapse to Y=0")
        self.assertLessEqual(bbox[2] - bbox[0], 50.0 * UNITS_PER_MM + 1.0)

        hinge_wave = generate_living_hinge(width_mm=50.0, height_mm=100.0, pattern="wave")
        self.assertIsInstance(hinge_wave, Path)
        self.assertGreater(len(hinge_wave), 0)
        wbbox = hinge_wave.bbox()
        self.assertIsNotNone(wbbox)
        self.assertGreater(wbbox[3] - wbbox[1], 50.0 * UNITS_PER_MM)

    def test_job_cost_estimator_and_quote(self):
        """Test job cost breakdown calculation and quote dictionary output."""
        path = Path()
        path.move(0, 0)
        path.line(1000, 0)
        path.line(1000, 1000)
        path.line(0, 1000)
        path.closed()

        node = self.elements.elem_branch.add(type="elem path", path=path)

        quote = generate_job_quote(self.elements, material_cost_per_m2=20.0, machine_rate_per_hour=50.0)
        self.assertIn("total_quote", quote)
        self.assertGreater(quote["total_quote"], 0.0)
        self.assertEqual(quote["currency"], "EUR")


if __name__ == "__main__":
    unittest.main()
