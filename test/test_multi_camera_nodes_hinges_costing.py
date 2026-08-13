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

    def test_parametric_living_hinge_generator(self):
        """Test parametric flex-cut living hinge pattern generation."""
        hinge_straight = generate_living_hinge(width_mm=50.0, height_mm=100.0, pattern="straight")
        self.assertIsInstance(hinge_straight, Path)
        self.assertGreater(len(hinge_straight), 0)

        hinge_wave = generate_living_hinge(width_mm=50.0, height_mm=100.0, pattern="wave")
        self.assertIsInstance(hinge_wave, Path)
        self.assertGreater(len(hinge_wave), 0)

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
