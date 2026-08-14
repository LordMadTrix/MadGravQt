"""Laser Execution Timeline & Acceleration Profile Calculator.

Calculates realistic motion duration for laser cut/raster/rapid moves
using trapezoidal acceleration profiles.
"""

from typing import List, Dict, Any, Tuple
import math


def calculate_move_time(
    distance_mm: float,
    target_speed_mm_s: float,
    accel_mm_s2: float = 3000.0,
) -> Dict[str, float]:
    """Calculate move duration with trapezoidal acceleration profile."""
    if distance_mm <= 0.0 or target_speed_mm_s <= 0.0:
        return {"total_time_s": 0.0, "accel_time_s": 0.0, "cruise_time_s": 0.0, "decel_time_s": 0.0, "peak_speed": 0.0}

    # Distance required to reach target speed from 0: d = v^2 / (2*a)
    dist_to_peak = (target_speed_mm_s ** 2) / (2.0 * accel_mm_s2)

    if 2.0 * dist_to_peak <= distance_mm:
        # Full trapezoid: reaches target speed
        t_accel = target_speed_mm_s / accel_mm_s2
        t_decel = t_accel
        dist_cruise = distance_mm - 2.0 * dist_to_peak
        t_cruise = dist_cruise / target_speed_mm_s
        peak_speed = target_speed_mm_s
    else:
        # Triangle profile: does not reach target speed
        peak_speed = math.sqrt(distance_mm * accel_mm_s2)
        t_accel = peak_speed / accel_mm_s2
        t_decel = t_accel
        t_cruise = 0.0

    total_time = t_accel + t_cruise + t_decel

    return {
        "total_time_s": round(total_time, 4),
        "accel_time_s": round(t_accel, 4),
        "cruise_time_s": round(t_cruise, 4),
        "decel_time_s": round(t_decel, 4),
        "peak_speed": round(peak_speed, 2),
    }


def analyze_job_timeline(
    moves: List[Dict[str, Any]],
    accel_mm_s2: float = 3000.0,
    rapid_speed: float = 200.0,
) -> Dict[str, Any]:
    """Analyze a series of moves [{'type': 'rapid'|'cut'|'raster', 'distance_mm': float, 'speed': float, 'power': float}]."""
    total_rapid_time = 0.0
    total_cut_time = 0.0
    total_rapid_dist = 0.0
    total_cut_dist = 0.0

    timeline_points = []
    current_time = 0.0

    for idx, mv in enumerate(moves):
        m_type = mv.get("type", "cut")
        dist = float(mv.get("distance_mm", 0.0))
        speed = float(mv.get("speed", rapid_speed if m_type == "rapid" else 20.0))
        power = float(mv.get("power", 0.0 if m_type == "rapid" else 100.0))

        res = calculate_move_time(dist, speed, accel_mm_s2)
        duration = res["total_time_s"]

        if m_type == "rapid":
            total_rapid_time += duration
            total_rapid_dist += dist
        else:
            total_cut_time += duration
            total_cut_dist += dist

        timeline_points.append({
            "index": idx,
            "type": m_type,
            "start_time_s": round(current_time, 3),
            "duration_s": duration,
            "end_time_s": round(current_time + duration, 3),
            "distance_mm": dist,
            "speed": speed,
            "power": power,
        })
        current_time += duration

    total_time = total_rapid_time + total_cut_time

    return {
        "total_duration_s": round(total_time, 2),
        "total_rapid_time_s": round(total_rapid_time, 2),
        "total_cut_time_s": round(total_cut_time, 2),
        "total_rapid_dist_mm": round(total_rapid_dist, 2),
        "total_cut_dist_mm": round(total_cut_dist, 2),
        "timeline": timeline_points,
    }
