import unittest
from madgrav.tools.topo_map_generator import (
    generate_procedural_heightmap,
    generate_layered_topo_map,
    topo_map_to_svg_layers,
)


class TestTopoMapGenerator(unittest.TestCase):
    def test_generate_procedural_heightmap(self):
        hm = generate_procedural_heightmap(
            preset="island",
            grid_res=50,
            seed=1234,
        )
        self.assertEqual(hm.shape, (50, 50))
        self.assertGreaterEqual(hm.min(), 0.0)
        self.assertLessEqual(hm.max(), 1.0)

    def test_generate_layered_topo_map(self):
        layers = generate_layered_topo_map(
            preset="mountain",
            width_mm=100.0,
            height_mm=100.0,
            layers_count=5,
            add_frame=True,
            pin_holes=True,
            pin_diameter_mm=3.0,
            seed=42,
        )
        self.assertIsInstance(layers, list)
        self.assertEqual(len(layers), 5)
        # Each layer dictionary contains layer_index, contours, pin_holes, frame_rect
        for idx, layer in enumerate(layers):
            self.assertEqual(layer["layer_index"], idx)
            self.assertIn("contours", layer)
            self.assertIn("pin_holes", layer)
            self.assertIn("frame", layer)
            self.assertEqual(len(layer["pin_holes"]), 4)  # 4 corner alignment pins

    def test_topo_map_to_svg_layers(self):
        svg_dict = topo_map_to_svg_layers(
            preset="canyon",
            width_mm=120.0,
            height_mm=80.0,
            layers_count=4,
        )
        self.assertIsInstance(svg_dict, dict)
        self.assertEqual(len(svg_dict), 4)
        for name, svg_content in svg_dict.items():
            self.assertIn("<svg", svg_content)
            self.assertIn("</svg>", svg_content)


if __name__ == "__main__":
    unittest.main()
