"""
Finger-Jointed 3D Box Generator for MadGrav.

Generates 2D unfolded cut patterns for 3D boxes with interlocking finger joints (tabs and slots),
incorporating material thickness and kerf compensation, matching LightBurn's Box Generator tool.
"""

from madgrav.svgelements import Color, Matrix, Path


def create_finger_edge_path(start_x, start_y, length, direction, tab_width_mm, thickness_mm, kerf_mm, is_male):
    """
    Generate a 2D line segment path with alternating finger joint tabs/slots.

    :param start_x: Starting X position
    :param start_y: Starting Y position
    :param length: Total edge length in mm
    :param direction: (dx, dy) direction vector (1,0), (0,1), (-1,0), or (0,-1)
    :param tab_width_mm: Target tab width in mm
    :param thickness_mm: Material thickness in mm
    :param kerf_mm: Kerf offset in mm
    :param is_male: True for tabs sticking out, False for slots cutting in
    :return: List of (x, y) vertex points along the finger edge
    """
    n_tabs = max(1, int(round(length / float(tab_width_mm))))
    if n_tabs % 2 == 0:
        n_tabs += 1  # Keep odd number of segments for symmetry

    actual_tab_width = length / float(n_tabs)
    dx, dy = direction
    nx, ny = dy, -dx  # Outward normal for clockwise traversal

    tab_depth = (thickness_mm + kerf_mm) if is_male else -(thickness_mm - kerf_mm)

    points = [(start_x, start_y)]
    curr_x, curr_y = start_x, start_y

    for i in range(n_tabs):
        is_tab = (i % 2 == 0) if is_male else (i % 2 == 1)

        next_x = curr_x + dx * actual_tab_width
        next_y = curr_y + dy * actual_tab_width

        if is_tab:
            points.append((curr_x + nx * tab_depth, curr_y + ny * tab_depth))
            points.append((next_x + nx * tab_depth, next_y + ny * tab_depth))
            points.append((next_x, next_y))
        else:
            points.append((next_x, next_y))

        curr_x, curr_y = next_x, next_y

    return points


def generate_panel_path(w_mm, h_mm, thickness_mm, tab_width_mm, kerf_mm, male_edges):
    """
    Generate a 2D closed Path for a single box panel with 4 finger-jointed edges.

    :param w_mm: Panel width in mm
    :param h_mm: Panel height in mm
    :param thickness_mm: Material thickness in mm
    :param tab_width_mm: Target tab width in mm
    :param kerf_mm: Kerf offset in mm
    :param male_edges: Tuple (top, right, bottom, left) booleans (True for male, False for female)
    :return: svgelements.Path object
    """
    top_male, right_male, bottom_male, left_male = male_edges

    top_pts = create_finger_edge_path(0, 0, w_mm, (1, 0), tab_width_mm, thickness_mm, kerf_mm, top_male)
    right_pts = create_finger_edge_path(w_mm, 0, h_mm, (0, 1), tab_width_mm, thickness_mm, kerf_mm, right_male)
    bottom_pts = create_finger_edge_path(w_mm, h_mm, w_mm, (-1, 0), tab_width_mm, thickness_mm, kerf_mm, bottom_male)
    left_pts = create_finger_edge_path(0, h_mm, h_mm, (0, -1), tab_width_mm, thickness_mm, kerf_mm, left_male)

    all_pts = top_pts + right_pts[1:] + bottom_pts[1:] + left_pts[1:]

    path = Path()
    # Path.move()/.line() take ONE point per positional arg, not two
    # unpacked scalars -- same fix as barcode_generator.py's QR code bug.
    path.move(complex(all_pts[0][0], all_pts[0][1]))
    for pt in all_pts[1:]:
        path.line(complex(pt[0], pt[1]))
    path.closed()
    return path


def generate_finger_box(
    elements_service,
    width_mm=100.0,
    height_mm=80.0,
    depth_mm=60.0,
    thickness_mm=3.0,
    tab_width_mm=10.0,
    kerf_mm=0.1,
    open_top=False,
    start_x_mm=10.0,
    start_y_mm=10.0,
    gap_mm=None,
):
    """
    Generate unfolded 2D panels for a 3D finger-jointed box and add them to the elements service.

    :param elements_service: The elements service (`kernel.elements`)
    :param width_mm: Box width (X) in mm
    :param height_mm: Box height (Z) in mm
    :param depth_mm: Box depth (Y) in mm
    :param thickness_mm: Material thickness in mm
    :param tab_width_mm: Tab width in mm
    :param kerf_mm: Kerf offset in mm
    :param open_top: Whether to omit the top lid panel
    :param start_x_mm: Layout start X in mm
    :param start_y_mm: Layout start Y in mm
    :param gap_mm: Gap between unfolded panels in mm
    :return: List of created PathNodes
    """
    from madgrav.core.units import UNITS_PER_MM

    if gap_mm is None:
        gap_mm = max(10.0, thickness_mm * 3.0)

    panels = [
        ("Bottom", width_mm, depth_mm, (False, False, False, False)),
        ("Front", width_mm, height_mm, (True, True, True, True)),
        ("Back", width_mm, height_mm, (True, True, True, True)),
        ("Left", depth_mm, height_mm, (True, False, True, False)),
        ("Right", depth_mm, height_mm, (True, False, True, False)),
    ]
    if not open_top:
        panels.append(("Top", width_mm, depth_mm, (False, False, False, False)))

    elements_branch = elements_service.elem_branch
    ops_branch = elements_service.op_branch

    op_node = ops_branch.add(
        type="op cut",
        color=Color("red"),
        label=f"3D Box Cut ({width_mm:.0f}x{depth_mm:.0f}x{height_mm:.0f}mm)",
    )

    created_nodes = []
    curr_x = start_x_mm + thickness_mm
    curr_y = start_y_mm + thickness_mm
    max_row_h = 0.0

    for name, w_mm, h_mm, male_edges in panels:
        if curr_x + w_mm + thickness_mm * 2 > 500.0 and curr_x > start_x_mm + thickness_mm:
            curr_x = start_x_mm + thickness_mm
            curr_y += max_row_h + gap_mm + thickness_mm * 2
            max_row_h = 0.0

        panel_path = generate_panel_path(w_mm, h_mm, thickness_mm, tab_width_mm, kerf_mm, male_edges)
        
        M = Matrix.scale(UNITS_PER_MM)
        M.post_translate(curr_x * UNITS_PER_MM, curr_y * UNITS_PER_MM)
        panel_path = panel_path * M

        elem_node = elements_branch.add(
            type="elem path",
            path=panel_path,
            stroke=Color("red"),
            stroke_width=100,
            label=f"Box Panel: {name}",
        )
        # Same missing-bounds-recompute bug as gear_generator.py --
        # required after every elem_branch.add() of a path-backed node.
        elem_node.altered()
        op_node.add_reference(elem_node)
        created_nodes.append(elem_node)

        curr_x += w_mm + gap_mm + thickness_mm * 2
        max_row_h = max(max_row_h, h_mm)

    elements_service.signal("tree_changed")
    elements_service.signal("refresh_scene")
    return created_nodes
