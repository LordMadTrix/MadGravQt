"""
Material Test Generator for MadGrav.

Generates a grid of test shapes varying Speed (mm/s) across rows/columns and Power (% or ratio)
across columns/rows, creating corresponding Cut/Engrave/Raster operations with those parameters.
"""

from madgrav.svgelements import Color, Matrix, Path


def generate_material_test(
    elements_service,
    op_type="cut",
    min_speed=5.0,
    max_speed=100.0,
    speed_steps=5,
    min_power=100.0,
    max_power=1000.0,
    power_steps=5,
    cell_width_mm=10.0,
    cell_height_mm=10.0,
    gap_mm=3.0,
    start_x_mm=10.0,
    start_y_mm=10.0,
    include_text=True,
):
    """
    Generate a material test matrix grid in elements_service.

    :param elements_service: The elements service (`kernel.elements`)
    :param op_type: Operation type ('cut', 'engrave', 'raster')
    :param min_speed: Minimum speed in mm/s
    :param max_speed: Maximum speed in mm/s
    :param speed_steps: Number of speed steps (rows)
    :param min_power: Minimum power (0 - 1000)
    :param max_power: Maximum power (0 - 1000)
    :param power_steps: Number of power steps (columns)
    :param cell_width_mm: Width of each cell square in mm
    :param cell_height_mm: Height of each cell square in mm
    :param gap_mm: Gap between cells in mm
    :param start_x_mm: Top-left X position in mm
    :param start_y_mm: Top-left Y position in mm
    :param include_text: Whether to generate text labels for speed and power
    """
    from madgrav.core.units import UNITS_PER_MM

    speeds = [
        min_speed + (max_speed - min_speed) * i / max(1, speed_steps - 1)
        for i in range(speed_steps)
    ]
    powers = [
        min_power + (max_power - min_power) * j / max(1, power_steps - 1)
        for j in range(power_steps)
    ]

    elements_branch = elements_service.elem_branch
    ops_branch = elements_service.op_branch

    created_nodes = []

    # Map op_type string to operation creation call
    op_kind = op_type.lower()
    if op_kind not in ("cut", "engrave", "raster"):
        op_kind = "cut"

    for r, speed in enumerate(speeds):
        for c, power in enumerate(powers):
            x_mm = start_x_mm + c * (cell_width_mm + gap_mm)
            y_mm = start_y_mm + r * (cell_height_mm + gap_mm)

            x_units = x_mm * UNITS_PER_MM
            y_units = y_mm * UNITS_PER_MM
            w_units = cell_width_mm * UNITS_PER_MM
            h_units = cell_height_mm * UNITS_PER_MM

            # Create rectangular path
            path = Path()
            # Path.move()/.line() take ONE point per positional arg, not
            # two unpacked scalars -- same fix as the QR code bug.
            path.move(complex(x_units, y_units))
            path.line(complex(x_units + w_units, y_units))
            path.line(complex(x_units + w_units, y_units + h_units))
            path.line(complex(x_units, y_units + h_units))
            path.closed()

            color = Color.distinct(r * power_steps + c)

            elem_node = elements_branch.add(
                type="elem path",
                path=path,
                stroke=color,
                stroke_width=100,
            )
            # Same missing-bounds-recompute bug as gear_generator.py.
            elem_node.altered()
            created_nodes.append(elem_node)

            # Create specific operation for this test cell
            if op_kind == "cut":
                op_node = ops_branch.add(
                    type="op cut",
                    color=color,
                    speed=speed,
                    power=power,
                    label=f"{speed:.1f}mm/s @ {power:.0f}",
                )
            elif op_kind == "engrave":
                op_node = ops_branch.add(
                    type="op engrave",
                    color=color,
                    speed=speed,
                    power=power,
                    label=f"{speed:.1f}mm/s @ {power:.0f}",
                )
            else:
                op_node = ops_branch.add(
                    type="op raster",
                    color=color,
                    speed=speed,
                    power=power,
                    label=f"{speed:.1f}mm/s @ {power:.0f}",
                )

            op_node.add_reference(elem_node)

    # Optional text labels
    if include_text:
        # Speed labels along left side
        for r, speed in enumerate(speeds):
            y_mm = start_y_mm + r * (cell_height_mm + gap_mm) + cell_height_mm / 2.0
            x_mm = max(0.0, start_x_mm - 8.0)
            text_node = elements_branch.add(
                type="elem text",
                text=f"{speed:.0f}mm/s",
                matrix=Matrix.scale(1.0).post_translate(x_mm * UNITS_PER_MM, y_mm * UNITS_PER_MM),
                stroke=Color("black"),
            )
            # Same missing-bounds-recompute bug as gear_generator.py.
            text_node.altered()
            created_nodes.append(text_node)

        # Power labels along top
        for c, power in enumerate(powers):
            x_mm = start_x_mm + c * (cell_width_mm + gap_mm)
            y_mm = max(0.0, start_y_mm - 3.0)
            text_node = elements_branch.add(
                type="elem text",
                text=f"{power:.0f}",
                matrix=Matrix.scale(1.0).post_translate(x_mm * UNITS_PER_MM, y_mm * UNITS_PER_MM),
                stroke=Color("black"),
            )
            # Same missing-bounds-recompute bug as gear_generator.py.
            text_node.altered()
            created_nodes.append(text_node)

    elements_service.signal("tree_changed")
    elements_service.signal("refresh_scene")
    return created_nodes
