"""
Rubber Stamp & 3D Relief Tool for MadGrav.

Provides artwork inversion, shoulder expansion (pyramidal sloping base), and boundary framing
for rubber stamp making, matching LightBurn's Stamp Mode.
"""

from madgrav.svgelements import Color, Path
from madgrav.tools.kerf_lead import apply_kerf_offset


def generate_stamp_shoulder(path, shoulder_width_mm=0.5, steps=3):
    """
    Generate sloped shoulder paths for rubber stamp characters to prevent bending under pressure.

    :param path: Original svgelements.Path instance
    :param shoulder_width_mm: Shoulder extension width in mm
    :param steps: Number of depth/slope gradient steps
    :return: List of Path instances from inner to outer shoulder
    """
    if not isinstance(path, Path) or len(path) == 0 or shoulder_width_mm <= 0.0:
        return [path]

    step_width_mm = float(shoulder_width_mm) / float(steps)
    shoulder_paths = [path]

    for i in range(1, steps + 1):
        offset_w = i * step_width_mm
        s_path = apply_kerf_offset(path, kerf_mm=offset_w, mode="outer")
        shoulder_paths.append(s_path)

    return shoulder_paths


def apply_stamp_mode(
    elements_service,
    nodes=None,
    shoulder_width_mm=0.5,
    margin_mm=3.0,
    invert=True,
):
    """
    Apply stamp mode to selected vector or text nodes.

    :param elements_service: The elements service (`kernel.elements`)
    :param nodes: List of nodes to process (if None, uses emphasized selection)
    :param shoulder_width_mm: Width of sloped shoulder base in mm
    :param margin_mm: Extra margin around stamp boundary in mm
    :param invert: Whether to invert background and create a boundary box
    :return: List of newly created/modified stamp nodes
    """
    from madgrav.core.units import UNITS_PER_MM

    if nodes is None:
        nodes = list(elements_service.elems(emphasized=True))

    if not nodes:
        return []

    elements_branch = elements_service.elem_branch
    ops_branch = elements_service.op_branch

    op_node = ops_branch.add(
        type="op engrave",
        color=Color("blue"),
        label="Rubber Stamp Engrave",
    )

    created_nodes = []

    for node in nodes:
        if hasattr(node, "path") and node.path is not None:
            orig_path = node.path
            bounds = node.bounds
            if bounds is None:
                continue

            min_x, min_y, max_x, max_y = bounds
            margin_units = margin_mm * UNITS_PER_MM

            # Generate shoulder paths
            shoulders = generate_stamp_shoulder(orig_path, shoulder_width_mm=shoulder_width_mm, steps=3)

            for idx, s_path in enumerate(shoulders):
                alpha = int(255 * (1.0 - idx / len(shoulders)))
                s_node = elements_branch.add(
                    type="elem path",
                    path=s_path,
                    stroke=Color(0, 0, 255, alpha),
                    stroke_width=100,
                    label=f"Stamp Shoulder Level {idx}",
                )
                # Same missing-bounds-recompute bug as gear_generator.py.
                s_node.altered()
                op_node.add_reference(s_node)
                created_nodes.append(s_node)

            # Inverted stamp bounding box
            if invert:
                box_path = Path()
                bx0 = min_x - margin_units
                by0 = min_y - margin_units
                bx1 = max_x + margin_units
                by1 = max_y + margin_units
                # Path.move()/.line() take ONE point per positional arg,
                # not two unpacked scalars -- same fix as the QR code bug.
                box_path.move(complex(bx0, by0))
                box_path.line(complex(bx1, by0))
                box_path.line(complex(bx1, by1))
                box_path.line(complex(bx0, by1))
                box_path.closed()

                box_node = elements_branch.add(
                    type="elem path",
                    path=box_path,
                    stroke=Color("black"),
                    stroke_width=100,
                    label="Stamp Outer Boundary",
                )
                # Same missing-bounds-recompute bug as gear_generator.py.
                box_node.altered()
                op_node.add_reference(box_node)
                created_nodes.append(box_node)

    elements_service.signal("tree_changed")
    elements_service.signal("refresh_scene")
    return created_nodes
