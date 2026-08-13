"""
3D G-Code & Path Trajectory Simulation Engine for MadGrav.
Parses G-Code laser sequences, calculates 3D moves, and estimates job duration.
"""

import math


def simulate_laser_path_3d(gcode_text_or_ops, travel_speed_mm_s=200.0, cut_speed_mm_s=20.0):
    """
    Parse G-Code or operations and calculate 3D laser path trajectory & timing.
    Returns simulation report dictionary.
    """
    points = []
    curr_x, curr_y, curr_z = 0.0, 0.0, 0.0
    curr_power = 0.0
    total_travel_dist = 0.0
    total_cut_dist = 0.0

    lines = []
    if isinstance(gcode_text_or_ops, str):
        lines = gcode_text_or_ops.splitlines()
    elif isinstance(gcode_text_or_ops, list):
        lines = [str(item) for item in gcode_text_or_ops]

    for line in lines:
        line_str = line.strip().upper()
        if not line_str or line_str.startswith(";"):
            continue

        parts = line_str.split()
        move_cmd = None
        new_x, new_y, new_z = curr_x, curr_y, curr_z
        new_power = curr_power

        for part in parts:
            if part.startswith("G"):
                if part in ("G0", "G00", "G1", "G01"):
                    move_cmd = part
            elif part.startswith("X"):
                try: new_x = float(part[1:])
                except ValueError: pass
            elif part.startswith("Y"):
                try: new_y = float(part[1:])
                except ValueError: pass
            elif part.startswith("Z"):
                try: new_z = float(part[1:])
                except ValueError: pass
            elif part.startswith("S"):
                try: new_power = float(part[1:])
                except ValueError: pass

        if move_cmd:
            dx = new_x - curr_x
            dy = new_y - curr_y
            dz = new_z - curr_z
            dist = math.sqrt(dx*dx + dy*dy + dz*dz)

            is_cut = (move_cmd in ("G1", "G01") and new_power > 0)
            if is_cut:
                total_cut_dist += dist
            else:
                total_travel_dist += dist

            points.append({
                "x": new_x, "y": new_y, "z": new_z,
                "power": new_power, "type": "cut" if is_cut else "travel",
                "distance": dist
            })

            curr_x, curr_y, curr_z = new_x, new_y, new_z
            curr_power = new_power

    travel_time_sec = total_travel_dist / travel_speed_mm_s if travel_speed_mm_s > 0 else 0
    cut_time_sec = total_cut_dist / cut_speed_mm_s if cut_speed_mm_s > 0 else 0
    total_time_sec = travel_time_sec + cut_time_sec

    return {
        "points": points,
        "point_count": len(points),
        "travel_dist_mm": round(total_travel_dist, 2),
        "cut_dist_mm": round(total_cut_dist, 2),
        "total_dist_mm": round(total_travel_dist + total_cut_dist, 2),
        "travel_time_sec": round(travel_time_sec, 2),
        "cut_time_sec": round(cut_time_sec, 2),
        "total_time_sec": round(total_time_sec, 2)
    }
