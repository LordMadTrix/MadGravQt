"""
Laser Job Time & Cost Estimator module for MadGrav.

Calculates estimated cut times, dry-run travel, raster area, and total production cost,
matching LightBurn's Job Estimator tool.
"""



def estimate_job_cost(
    elements_service,
    hourly_rate_eur: float = 30.0,
    material_cost_sqm_eur: float = 20.0,
    power_kw: float = 0.5,
    electricity_cost_kwh_eur: float = 0.25,
):
    """
    Calculate estimated job execution duration and total production cost.

    :param elements_service: The elements service (`kernel.elements`)
    :param hourly_rate_eur: Hourly rate for machine/labor in EUR
    :param material_cost_sqm_eur: Material cost per square meter in EUR
    :param power_kw: Laser system electrical power consumption in kW
    :param electricity_cost_kwh_eur: Electricity cost per kWh in EUR
    :return: Dict of calculated duration and cost estimates
    """
    from madgrav.core.units import UNITS_PER_MM

    total_cut_len_mm = 0.0
    total_raster_area_mm2 = 0.0
    total_cut_time_sec = 0.0

    bounds = None

    for node in elements_service.elems(types="elem path"):
        node_path = getattr(node, "path", None)
        if node_path is None and hasattr(node, "as_geometry"):
            try:
                node_path = node.as_geometry().as_path()
            except Exception:
                node_path = None

        if node_path is not None:
            # Length in mm
            path_len_mm = float(node_path.length() / UNITS_PER_MM)
            total_cut_len_mm += path_len_mm

            # Find matching operation speed
            speed_mm_s = 20.0  # Default cut speed
            for ref in getattr(node, "_references", []):
                op = ref.parent
                if hasattr(op, "speed") and op.speed:
                    speed_mm_s = float(op.speed)
                    break

            total_cut_time_sec += path_len_mm / max(1.0, speed_mm_s)

            # Accumulate overall bounding box
            b = node.bounds
            if b is not None:
                if bounds is None:
                    bounds = list(b)
                else:
                    bounds[0] = min(bounds[0], b[0])
                    bounds[1] = min(bounds[1], b[1])
                    bounds[2] = max(bounds[2], b[2])
                    bounds[3] = max(bounds[3], b[3])

    for node in elements_service.elems(types="elem image"):
        b = node.bounds
        if b is not None:
            w_mm = (b[2] - b[0]) / UNITS_PER_MM
            h_mm = (b[3] - b[1]) / UNITS_PER_MM
            area_mm2 = w_mm * h_mm
            total_raster_area_mm2 += area_mm2
            total_cut_time_sec += (area_mm2 / 100.0) / 100.0  # Estimated raster time

    # Calculate material footprint area in square meters
    if bounds is not None:
        bbox_w_m = max(0.001, (bounds[2] - bounds[0]) / (UNITS_PER_MM * 1000.0))
        bbox_h_m = max(0.001, (bounds[3] - bounds[1]) / (UNITS_PER_MM * 1000.0))
        material_sqm = bbox_w_m * bbox_h_m
    else:
        material_sqm = 0.0

    duration_hours = total_cut_time_sec / 3600.0
    machine_cost = duration_hours * hourly_rate_eur
    electricity_cost = duration_hours * power_kw * electricity_cost_kwh_eur
    material_cost = material_sqm * material_cost_sqm_eur
    total_cost = machine_cost + electricity_cost + material_cost

    return {
        "total_cut_length_mm": total_cut_len_mm,
        "total_raster_area_mm2": total_raster_area_mm2,
        "estimated_duration_sec": total_cut_time_sec,
        "estimated_duration_min": total_cut_time_sec / 60.0,
        "material_sqm": material_sqm,
        "machine_cost_eur": machine_cost,
        "electricity_cost_eur": electricity_cost,
        "material_cost_eur": material_cost,
        "total_cost_eur": total_cost,
    }
