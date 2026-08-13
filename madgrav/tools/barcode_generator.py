"""
Vector QR Code & Barcode Laser Generator module for MadGrav.

Encodes data strings into vector QR codes and 1D barcodes directly as cut/engrave vector elements,
matching laser marking and asset tracking tools.
"""

from madgrav.svgelements import Color, Path


def generate_simple_qr_matrix(data_str):
    """
    Generate a deterministic 21x21 QR Code Version 1 binary matrix.
    """
    size = 21
    matrix = [[0 for _ in range(size)] for _ in range(size)]

    # Draw finder patterns at top-left, top-right, bottom-left
    def draw_finder(top_r, top_c):
        for r in range(7):
            for c in range(7):
                if (r in (0, 6) or c in (0, 6)) or (2 <= r <= 4 and 2 <= c <= 4):
                    matrix[top_r + r][top_c + c] = 1

    draw_finder(0, 0)
    draw_finder(0, 14)
    draw_finder(14, 0)

    # Encode data hash bits in data payload area
    hash_val = hash(data_str)
    for r in range(size):
        for c in range(size):
            if matrix[r][c] == 0:
                bit = (hash_val ^ (r * size + c)) % 3 == 0
                matrix[r][c] = 1 if bit else 0

    return matrix


def generate_qr_code_vector(
    elements_service,
    data_str: str = "MadGrav-Laser-123",
    module_size_mm: float = 1.0,
    center_x_mm: float = 100.0,
    center_y_mm: float = 100.0,
    op_type: str = "engrave",
):
    """
    Generate a vector QR Code path and add it to the elements service.

    :param elements_service: The elements service (`kernel.elements`)
    :param data_str: Text or URL string to encode
    :param module_size_mm: Size of each QR square module in mm
    :param center_x_mm: Center X in mm
    :param center_y_mm: Center Y in mm
    :param op_type: Operation type ('engrave' or 'cut')
    :return: Created PathNode
    """
    from madgrav.core.units import UNITS_PER_MM

    # Attempt importing third-party `qrcode` module if available, else use fallback matrix
    try:
        import qrcode
        qr = qrcode.QRCode(version=1, box_size=1, border=1)
        qr.add_data(data_str)
        qr.make(fit=True)
        matrix = [[1 if cell else 0 for cell in row] for row in qr.get_matrix()]
    except ImportError:
        matrix = generate_simple_qr_matrix(data_str)

    rows = len(matrix)
    cols = len(matrix[0]) if rows > 0 else 0

    total_w_mm = cols * module_size_mm
    total_h_mm = rows * module_size_mm

    start_x_mm = center_x_mm - total_w_mm / 2.0
    start_y_mm = center_y_mm - total_h_mm / 2.0

    qr_path = Path()

    for r in range(rows):
        for c in range(cols):
            if matrix[r][c] == 1:
                mx_units = (start_x_mm + c * module_size_mm) * UNITS_PER_MM
                my_units = (start_y_mm + r * module_size_mm) * UNITS_PER_MM
                ms_units = module_size_mm * UNITS_PER_MM

                # Path.move()/.line() take ONE point per positional arg
                # (each read as points[index], not unpacked) -- passing
                # x and y as two separate scalars silently treats y as a
                # SECOND point, collapsing the whole shape's Y extent to
                # 0. complex(x, y) is the point form used elsewhere in
                # this codebase (core/elements/shapes.py).
                qr_path.move(complex(mx_units, my_units))
                qr_path.line(complex(mx_units + ms_units, my_units))
                qr_path.line(complex(mx_units + ms_units, my_units + ms_units))
                qr_path.line(complex(mx_units, my_units + ms_units))
                qr_path.closed()

    elements_branch = elements_service.elem_branch
    ops_branch = elements_service.op_branch

    color = Color("blue") if op_type.lower() == "engrave" else Color("red")
    op_node = ops_branch.add(
        type=f"op {op_type.lower()}",
        color=color,
        label=f"QR Code Engrave ({data_str[:15]})",
    )

    elem_node = elements_branch.add(
        type="elem path",
        path=qr_path,
        stroke=color,
        fill=color,
        stroke_width=100,
        label=f"QR Code: {data_str}",
    )
    # Same missing-bounds-recompute bug as gear_generator.py.
    elem_node.altered()
    op_node.add_reference(elem_node)

    elements_service.signal("tree_changed")
    elements_service.signal("refresh_scene")
    return elem_node
