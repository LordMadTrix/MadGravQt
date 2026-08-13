"""
Rotary Attachment Setup & Y-Scale Assistant module for MadGrav.

Calculates cylindrical object circumferences, pulse density, and Y-axis scale ratios
for chuck and roller rotary attachments, matching LightBurn's Rotary Setup tool.
"""

import math


def calculate_rotary_parameters(
    object_diameter_mm: float,
    steps_per_rev: int = 200,
    microstepping: int = 16,
    roller_diameter_mm: float = 50.0,
    is_chuck: bool = False,
    bed_height_mm: float = 300.0,
):
    """
    Calculate rotary attachment scale factors and pulse resolutions.

    :param object_diameter_mm: Diameter of workpiece in mm
    :param steps_per_rev: Motor full steps per revolution (e.g. 200 for 1.8 deg stepper)
    :param microstepping: Microstepping driver division (e.g. 8, 16, 32)
    :param roller_diameter_mm: Roller wheel diameter in mm (for roller rotary)
    :param is_chuck: True for chuck rotary, False for roller rotary
    :param bed_height_mm: Flat Y bed height in mm
    :return: Dict containing calculated parameters
    """
    if object_diameter_mm <= 0.0:
        raise ValueError("Object diameter must be positive.")

    circumference_mm = math.pi * object_diameter_mm
    total_steps_per_rev = steps_per_rev * microstepping

    if is_chuck:
        pulses_per_mm = total_steps_per_rev / circumference_mm
    else:
        if roller_diameter_mm <= 0.0:
            roller_diameter_mm = 50.0
        roller_circumference_mm = math.pi * roller_diameter_mm
        pulses_per_mm = total_steps_per_rev / roller_circumference_mm

    y_scale_ratio = circumference_mm / float(bed_height_mm if bed_height_mm > 0 else 300.0)

    return {
        "object_diameter_mm": object_diameter_mm,
        "circumference_mm": circumference_mm,
        "pulses_per_mm": pulses_per_mm,
        "y_scale_ratio": y_scale_ratio,
        "is_chuck": is_chuck,
    }
