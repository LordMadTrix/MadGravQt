"""
Involute Spur Gear Generator module for MadGrav.

Generates precise 2D vector spur gears with involute tooth profiles and central bore holes,
matching professional CAD gear generators.
"""

import math
from madgrav.svgelements import Color, Matrix, Path


def generate_involute_gear(
    elements_service,
    num_teeth: int = 20,
    module: float = 2.0,
    pressure_angle_deg: float = 20.0,
    bore_diameter_mm: float = 8.0,
    center_x_mm: float = 100.0,
    center_y_mm: float = 100.0,
):
    """
    Generate a mathematically precise involute spur gear path and add it to the elements service.

    :param elements_service: The elements service (`kernel.elements`)
    :param num_teeth: Number of teeth N (>= 6)
    :param module: Metric gear module m in mm (pitch diameter / N)
    :param pressure_angle_deg: Pressure angle phi in degrees (typically 20.0)
    :param bore_diameter_mm: Central shaft bore hole diameter in mm (0 for solid)
    :param center_x_mm: Gear center X in mm
    :param center_y_mm: Gear center Y in mm
    :return: Created PathNode
    """
    from madgrav.core.units import UNITS_PER_MM

    if num_teeth < 6:
        num_teeth = 6

    phi_rad = math.radians(pressure_angle_deg)
    Rp = (module * num_teeth) / 2.0  # Pitch radius
    Rb = Rp * math.cos(phi_rad)       # Base radius
    Ra = Rp + module                  # Outer (tip) radius
    Rr = max(1.0, Rp - 1.25 * module) # Root radius

    inv_phi = math.tan(phi_rad) - phi_rad
    half_tooth = math.pi / (2.0 * num_teeth)
    tooth_pitch = 2.0 * math.pi / float(num_teeth)

    points = []
    steps = 8

    for i in range(num_teeth):
        a0 = i * tooth_pitch

        # 1. Root fillet / straight segment up to base radius if Rr < Rb
        if Rr < Rb:
            a_root_left = a0 - half_tooth - inv_phi
            points.append((Rr * math.cos(a_root_left), Rr * math.sin(a_root_left)))

        # 2. Left involute flank (root -> tip)
        r_start = max(Rr, Rb)
        for s in range(steps + 1):
            r = r_start + (s / float(steps)) * (Ra - r_start)
            phi_r = math.acos(Rb / r) if r > Rb else 0.0
            theta_r = math.tan(phi_r) - phi_r
            a_left = a0 - half_tooth - inv_phi + theta_r
            points.append((r * math.cos(a_left), r * math.sin(a_left)))

        # 3. Tip land arc (left tip -> right tip)
        a_left_tip = a0 - half_tooth - inv_phi + (math.tan(math.acos(Rb / Ra)) - math.acos(Rb / Ra) if Ra > Rb else 0.0)
        a_right_tip = a0 + half_tooth + inv_phi - (math.tan(math.acos(Rb / Ra)) - math.acos(Rb / Ra) if Ra > Rb else 0.0)
        tip_steps = 3
        for t in range(1, tip_steps):
            a_tip = a_left_tip + (t / float(tip_steps)) * (a_right_tip - a_left_tip)
            points.append((Ra * math.cos(a_tip), Ra * math.sin(a_tip)))

        # 4. Right involute flank (tip -> root)
        for s in range(steps, -1, -1):
            r = r_start + (s / float(steps)) * (Ra - r_start)
            phi_r = math.acos(Rb / r) if r > Rb else 0.0
            theta_r = math.tan(phi_r) - phi_r
            a_right = a0 + half_tooth + inv_phi - theta_r
            points.append((r * math.cos(a_right), r * math.sin(a_right)))

        # 5. Root fillet / straight segment down from base radius if Rr < Rb
        if Rr < Rb:
            a_root_right = a0 + half_tooth + inv_phi
            points.append((Rr * math.cos(a_root_right), Rr * math.sin(a_root_right)))

        # 6. Root valley land arc to next tooth
        a_next_left_root = (i + 1) * tooth_pitch - half_tooth - inv_phi
        root_steps = 3
        for r_s in range(1, root_steps):
            a_root = a_root_right if Rr < Rb else (a0 + half_tooth + inv_phi - (math.tan(math.acos(Rb / r_start)) - math.acos(Rb / r_start) if r_start > Rb else 0.0))
            a_val = a_root + (r_s / float(root_steps)) * (a_next_left_root - a_root)
            points.append((Rr * math.cos(a_val), Rr * math.sin(a_val)))

    gear_path = Path()
    # Path.move()/.line() take ONE point per positional arg, not two
    # unpacked scalars -- same fix as barcode_generator.py's QR code bug.
    gear_path.move(complex(points[0][0], points[0][1]))
    for pt in points[1:]:
        gear_path.line(complex(pt[0], pt[1]))
    gear_path.closed()

    # Add central bore hole if requested
    if bore_diameter_mm > 0.0:
        bore_radius = bore_diameter_mm / 2.0
        b_pts = 32
        gear_path.move(complex(bore_radius, 0.0))
        for b in range(1, b_pts + 1):
            ba = (b / float(b_pts)) * 2.0 * math.pi
            gear_path.line(complex(bore_radius * math.cos(ba), bore_radius * math.sin(ba)))
        gear_path.closed()

    # Transform to units and center position
    M = Matrix.scale(UNITS_PER_MM)
    M.post_translate(center_x_mm * UNITS_PER_MM, center_y_mm * UNITS_PER_MM)
    gear_path = gear_path * M

    elements_branch = elements_service.elem_branch
    ops_branch = elements_service.op_branch

    op_node = ops_branch.add(
        type="op cut",
        color=Color("red"),
        label=f"Spur Gear (N={num_teeth}, m={module}mm)",
    )

    elem_node = elements_branch.add(
        type="elem path",
        path=gear_path,
        stroke=Color("red"),
        stroke_width=100,
        label=f"Involute Gear N={num_teeth}",
    )
    # Without this, the node's cached bounds/geometry never get
    # recomputed from the real path -- confirmed via reproduction: the
    # Position panel showed a degenerate 0.01mm bounding box instead of
    # the gear's real ~44mm size. Every established shape-creation path
    # in core/elements/shapes.py calls this immediately after add().
    elem_node.altered()
    op_node.add_reference(elem_node)

    elements_service.signal("tree_changed")
    elements_service.signal("refresh_scene")
    return elem_node
