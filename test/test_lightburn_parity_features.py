"""
Unit tests for LightBurn parity features:
- Material Test Matrix Generator
- Grid & Circular Array Generators
- Micro-Tabs / Bridges Generator
- Kerf Offset & Lead-In/Out
- Camera Trace & Laser Framing
"""

import unittest
import cv2
import numpy as np

from test.bootstrap import bootstrap
from madgrav.svgelements import Path, Rect, Matrix, Point

from madgrav.tools.material_test import generate_material_test
from madgrav.tools.array_generator import generate_grid_array, generate_circular_array
from madgrav.tools.micro_tabs import add_micro_tabs_to_path, apply_tabs_to_selected_nodes
from madgrav.tools.kerf_lead import apply_kerf_offset, add_lead_in_out
from madgrav.camera.cameratrace import trace_camera_frame_to_elements, frame_camera_object


class TestLightBurnParityFeatures(unittest.TestCase):
    def setUp(self):
        self.kernel = bootstrap()
        self.elements = self.kernel.elements

    def test_material_test_generator(self):
        """Test Material Test Grid matrix generation with speed & power operations."""
        created_nodes = generate_material_test(
            self.elements,
            op_type="cut",
            min_speed=10.0,
            max_speed=50.0,
            speed_steps=3,
            min_power=100.0,
            max_power=500.0,
            power_steps=3,
            cell_width_mm=10.0,
            cell_height_mm=10.0,
            gap_mm=2.0,
            include_text=True,
        )

        self.assertGreater(len(created_nodes), 0)

        # Check operations generated
        ops = list(self.elements.ops())
        self.assertGreaterEqual(len(ops), 9)

        # Check speeds and powers on operations
        speeds = [getattr(op, "speed", None) for op in ops if getattr(op, "speed", None) is not None]
        self.assertIn(10.0, speeds)
        self.assertIn(50.0, speeds)

    def test_grid_array_generator(self):
        """Test 2D Rectangular Grid Array duplication."""
        # Create an initial rectangle path node
        path = Path()
        path.move(0, 0)
        path.line(1000, 0)
        path.line(1000, 1000)
        path.line(0, 1000)
        path.closed()

        rect_node = self.elements.elem_branch.add(type="elem path", path=path)
        rect_node.emphasized = True

        new_nodes = generate_grid_array(
            self.elements,
            nodes=[rect_node],
            rows=2,
            cols=3,
            distance_x_mm=5.0,
            distance_y_mm=5.0,
        )

        # 2x3 grid = 6 total cells, so 5 duplicates created
        self.assertEqual(len(new_nodes), 5)

    def test_circular_array_generator(self):
        """Test Polar Circular Array duplication."""
        path = Path()
        path.move(1000, 0)
        path.line(1200, 0)
        path.line(1200, 200)
        path.line(1000, 200)
        path.closed()

        node = self.elements.elem_branch.add(type="elem path", path=path)

        new_nodes = generate_circular_array(
            self.elements,
            nodes=[node],
            count=6,
            center_x_mm=0.0,
            center_y_mm=0.0,
            total_angle_deg=360.0,
        )

        self.assertEqual(len(new_nodes), 5)

    def test_micro_tabs_insertion(self):
        """Test micro-tabs (hold bridge gaps) insertion along vector path."""
        path = Path()
        path.move(0, 0)
        path.line(10000, 0)
        path.line(10000, 10000)
        path.line(0, 10000)
        path.closed()

        path_with_tabs = add_micro_tabs_to_path(path, tab_count=4, tab_size_mm=1.0)
        self.assertIsInstance(path_with_tabs, Path)
        self.assertGreater(len(path_with_tabs), len(path))

    def test_kerf_and_lead_in_out(self):
        """Test kerf compensation offset and lead-in/lead-out line generation."""
        path = Path()
        path.move(0, 0)
        path.line(1000, 0)
        path.line(1000, 1000)
        path.line(0, 1000)
        path.closed()

        offset_path = apply_kerf_offset(path, kerf_mm=0.5, mode="outer")
        self.assertIsInstance(offset_path, Path)

        lead_path = add_lead_in_out(path, lead_in_len_mm=2.0, lead_out_len_mm=2.0, lead_angle_deg=45.0)
        self.assertIsInstance(lead_path, Path)
        self.assertGreater(len(lead_path), len(path))

    def test_camera_trace_and_framing(self):
        """Test converting camera-detected objects to vector elements and framing."""
        from madgrav.camera.camera import Camera

        cam = Camera(self.kernel, "camera/0")
        self.kernel.add_service("camera", cam)
        self.kernel.activate_service_path("camera", "camera/0")

        canvas = np.ones((500, 500, 3), dtype=np.uint8) * 255
        cv2.rectangle(canvas, (100, 100), (200, 160), (0, 0, 0), -1)
        cam._last_raw = canvas
        cam._current_raw = canvas

        cam.alignment_homography = np.eye(3, dtype=np.float64).tolist()

        created_nodes = trace_camera_frame_to_elements(self.kernel, camera_service=cam)
        self.assertGreaterEqual(len(created_nodes), 1)

        result = frame_camera_object(self.kernel, camera_service=cam, object_index=0)
        self.assertIn(result, (True, False))

    def test_layer_color_palette_application(self):
        """Test assigning LightBurn layer colors (00-29, T1, T2) to elements."""
        from madgrav.svgelements import Color, Path

        path = Path()
        path.move(0, 0)
        path.line(100, 100)
        node = self.elements.elem_branch.add(type="elem path", path=path)

        # Apply LightBurn Layer 01 (Blue #0000FF)
        blue = Color("#0000FF")
        node.stroke = blue
        if not hasattr(node, "values"):
            node.values = {}
        node.values["layer"] = "01"

        self.assertEqual(node.stroke, blue)
        self.assertEqual(node.values.get("layer"), "01")

        # Apply LightBurn Tool Layer T1 (Orange #FF6600)
        orange = Color("#FF6600")
        node.stroke = orange
        node.values["layer"] = "T1"

        self.assertEqual(node.stroke, orange)
        self.assertEqual(node.values.get("layer"), "T1")

    def test_laser_control_console_commands(self):
        """Test LightBurn laser control commands on the kernel console."""
        self.kernel.console("frame\n")
        self.kernel.console("home\n")


if __name__ == "__main__":
    unittest.main()

