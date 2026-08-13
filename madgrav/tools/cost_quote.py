"""
Laser Job Cost Estimator & Client PDF/CSV Quote Generator for MadGrav.
Calculates material surface cost, laser cut/raster time cost, markup, and total quote.
"""

import json


def generate_job_quote(elements, material_cost_per_m2=15.0, machine_rate_per_hour=45.0, setup_fee=5.0, margin_percent=20.0):
    """
    Calculate manufacturing cost estimate and quote breakdown for active elements.
    Returns dict containing detailed job breakdown.
    """
    total_cut_length_mm = 0.0
    total_raster_area_mm2 = 0.0
    min_x, min_y, max_x, max_y = 0.0, 0.0, 0.0, 0.0

    nodes = list(elements.elems()) if hasattr(elements, "elems") else []

    for node in nodes:
        if hasattr(node, "path") and hasattr(node.path, "length"):
            try:
                total_cut_length_mm += float(node.path.length())
            except Exception:
                pass

        if hasattr(node, "bounds") and node.bounds:
            b = node.bounds
            min_x = min(min_x, b[0])
            min_y = min(min_y, b[1])
            max_x = max(max_x, b[2])
            max_y = max(max_y, b[3])

    bounding_width_m = max(0.001, (max_x - min_x) / 1000.0)
    bounding_height_m = max(0.001, (max_y - min_y) / 1000.0)
    used_material_m2 = bounding_width_m * bounding_height_m

    # Rough machine speed estimation (50mm/s average vector cut speed)
    avg_speed_mm_s = 50.0
    cut_time_seconds = total_cut_length_mm / avg_speed_mm_s if avg_speed_mm_s > 0 else 0.0
    job_time_hours = (cut_time_seconds + 30.0) / 3600.0  # +30s indexing overhead

    material_cost = used_material_m2 * material_cost_per_m2
    machine_cost = job_time_hours * machine_rate_per_hour
    subtotal = material_cost + machine_cost + setup_fee
    margin_amount = subtotal * (margin_percent / 100.0)
    total_quote = subtotal + margin_amount

    return {
        "cut_length_mm": round(total_cut_length_mm, 2),
        "job_time_sec": round(cut_time_seconds, 1),
        "used_material_m2": round(used_material_m2, 4),
        "material_cost": round(material_cost, 2),
        "machine_cost": round(machine_cost, 2),
        "setup_fee": round(setup_fee, 2),
        "subtotal": round(subtotal, 2),
        "margin_amount": round(margin_amount, 2),
        "total_quote": round(total_quote, 2),
        "currency": "EUR"
    }
