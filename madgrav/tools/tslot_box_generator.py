"""T-Slot & Captive Nut Box Panel Generator.

Generates 6 laser cut box panels with captive nut T-slots for M3/M4/M5 hardware.
"""

from typing import Dict, Any, List
import math


def get_standard_hardware_dims(standard: str = "M3") -> Dict[str, float]:
    """Return screw and nut dimensions for standard hardware."""
    standards = {
        "M3": {
            "screw_dia": 3.2,
            "nut_width": 5.6,
            "nut_thickness": 2.5,
            "screw_len": 12.0,
            "hole_margin": 6.0,
        },
        "M4": {
            "screw_dia": 4.2,
            "nut_width": 7.1,
            "nut_thickness": 3.3,
            "screw_len": 16.0,
            "hole_margin": 8.0,
        },
        "M5": {
            "screw_dia": 5.2,
            "nut_width": 8.1,
            "nut_thickness": 4.1,
            "screw_len": 20.0,
            "hole_margin": 10.0,
        },
    }
    return standards.get(standard.upper(), standards["M3"])


def generate_tslot_panels(
    width: float = 100.0,
    height: float = 80.0,
    depth: float = 60.0,
    thickness: float = 3.0,
    hardware: str = "M3",
    kerf: float = 0.15,
) -> Dict[str, Any]:
    """Generate geometry metadata and SVG paths for 6 T-Slot box panels."""
    hw = get_standard_hardware_dims(hardware)

    # 6 Panels: Top, Bottom, Front, Back, Left, Right
    panels = {
        "bottom": {"w": width, "h": depth, "name": "Fond"},
        "top": {"w": width, "h": depth, "name": "Couvercle"},
        "front": {"w": width, "h": height, "name": "Face Avant"},
        "back": {"w": width, "h": height, "name": "Face Arrière"},
        "left": {"w": depth, "h": height, "name": "Côté Gauche"},
        "right": {"w": depth, "h": height, "name": "Côté Droit"},
    }

    # Generate layout positioning for all 6 panels
    layout_panels = []
    x_offset = 10.0
    y_offset = 10.0
    row_height = 0.0

    for name, p in panels.items():
        w, h = p["w"], p["h"]
        if x_offset + w > width * 3:
            x_offset = 10.0
            y_offset += row_height + 15.0
            row_height = 0.0

        layout_panels.append({
            "id": name,
            "label": p["name"],
            "x": x_offset,
            "y": y_offset,
            "w": w,
            "h": h,
            "t_slots": [
                {
                    "x": x_offset + w / 2.0,
                    "y": y_offset + hw["hole_margin"],
                    "screw_dia": hw["screw_dia"],
                    "nut_w": hw["nut_width"],
                    "nut_t": hw["nut_thickness"],
                }
            ],
        })

        x_offset += w + 15.0
        row_height = max(row_height, h)

    total_width = max(p["x"] + p["w"] for p in layout_panels) + 10.0
    total_height = max(p["y"] + p["h"] for p in layout_panels) + 10.0

    return {
        "dimensions": {"width": width, "height": height, "depth": depth, "thickness": thickness},
        "hardware": hw,
        "hardware_type": hardware,
        "panels": layout_panels,
        "total_width": total_width,
        "total_height": total_height,
        "kerf": kerf,
    }
