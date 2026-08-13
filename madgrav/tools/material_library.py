"""
Material Library Service for MadGrav.

Provides a structured material settings database (speed, power, passes, air assist)
organized by material category and thickness, matching LightBurn's Material Library.
"""

import json
from dataclasses import asdict, dataclass
from typing import Dict, List, Optional


@dataclass
class MaterialPreset:
    """Represents preset laser settings for a specific material and thickness."""

    name: str
    material_type: str  # Wood, Acrylic, Leather, Metal, Paper
    thickness_mm: float  # Material thickness in mm
    op_type: str  # 'cut', 'engrave', 'raster'
    speed: float  # Speed in mm/s
    power: float  # Power (0-1000 or %)
    passes: int = 1  # Number of passes
    air_assist: bool = True  # Air assist enabled


class MaterialLibrary:
    """Material Library database manager."""

    def __init__(self):
        self.presets: Dict[str, MaterialPreset] = {}
        self._load_defaults()

    def _load_defaults(self):
        """Populate standard default laser material presets."""
        defaults = [
            MaterialPreset("Birch Plywood 3mm Cut", "Wood", 3.0, "cut", 20.0, 800.0, 1, True),
            MaterialPreset("Birch Plywood 3mm Engrave", "Wood", 3.0, "engrave", 100.0, 400.0, 1, False),
            MaterialPreset("Birch Plywood 5mm Cut", "Wood", 5.0, "cut", 10.0, 950.0, 1, True),
            MaterialPreset("Acrylic Clear 3mm Cut", "Acrylic", 3.0, "cut", 15.0, 850.0, 1, True),
            MaterialPreset("Acrylic Clear 3mm Engrave", "Acrylic", 3.0, "engrave", 150.0, 300.0, 1, False),
            MaterialPreset("Leather 2mm Cut", "Leather", 2.0, "cut", 25.0, 700.0, 1, True),
            MaterialPreset("Anodized Aluminum Engrave", "Metal", 0.0, "engrave", 200.0, 500.0, 1, False),
            MaterialPreset("Cardboard 2mm Cut", "Paper", 2.0, "cut", 40.0, 500.0, 1, True),
        ]
        for p in defaults:
            self.add_preset(p)

    def add_preset(self, preset: MaterialPreset):
        key = f"{preset.material_type.lower()}_{preset.thickness_mm}mm_{preset.op_type.lower()}"
        self.presets[key] = preset

    def get_preset(self, material_type: str, thickness_mm: float, op_type: str) -> Optional[MaterialPreset]:
        key = f"{material_type.lower()}_{thickness_mm}mm_{op_type.lower()}"
        return self.presets.get(key)

    def list_materials(self) -> List[str]:
        return sorted(list({p.material_type for p in self.presets.values()}))

    def export_to_json(self) -> str:
        return json.dumps([asdict(p) for p in self.presets.values()], indent=2)

    def import_from_json(self, json_str: str):
        data = json.loads(json_str)
        for item in data:
            self.add_preset(MaterialPreset(**item))


def apply_material_preset(elements_service, material_type: str, thickness_mm: float, op_type: str = "cut"):
    """
    Apply a material library preset directly to matching operations in the active project.

    :param elements_service: The elements service (`kernel.elements`)
    :param material_type: Material category ('Wood', 'Acrylic', etc.)
    :param thickness_mm: Material thickness in mm
    :param op_type: Operation type ('cut', 'engrave', 'raster')
    :return: True if preset was found and applied
    """
    lib = getattr(elements_service, "material_library", None)
    if lib is None:
        lib = MaterialLibrary()

    preset = lib.get_preset(material_type, thickness_mm, op_type)
    if preset is None:
        return False

    ops_branch = elements_service.op_branch
    target_type = f"op {op_type.lower()}"

    applied_count = 0
    for op in ops_branch.children:
        if getattr(op, "type", "") == target_type:
            op.speed = preset.speed
            op.power = preset.power
            if hasattr(op, "passes"):
                op.passes = preset.passes
            applied_count += 1

    if applied_count > 0:
        elements_service.signal("tree_changed")
        elements_service.signal("refresh_scene")

    return True
