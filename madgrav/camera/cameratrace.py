"""
Camera Trace & Laser Framing module for MadGrav.

Allows directly converting camera-detected objects into workspace vector elements (PathNodes)
and performing live laser framing around detected objects, matching LightBurn's Camera Trace feature.
"""

from madgrav.svgelements import Color, Matrix, Path


def trace_camera_frame_to_elements(
    kernel,
    camera_service=None,
    min_area_mm2=10.0,
    threshold_method="otsu",
    op_type="cut",
):
    """
    Detect objects in the camera live view and convert their contours directly into workspace vector PathNodes.

    :param kernel: The MadGrav kernel
    :param camera_service: Active Camera service (or None for default camera/0)
    :param min_area_mm2: Minimum object area in mm²
    :param threshold_method: Thresholding method ('otsu', 'adaptive', 'canny')
    :param op_type: Target operation type ('cut', 'engrave')
    :return: List of newly added PathNodes
    """
    from madgrav.core.units import UNITS_PER_MM

    if camera_service is None:
        camera_service = getattr(kernel, "camera", None)

    if camera_service is None:
        return []

    detected_objects = camera_service.detect_objects_and_measure(
        min_area_mm2=min_area_mm2, threshold_method=threshold_method
    )

    if not detected_objects:
        return []

    elements_service = kernel.elements
    elements_branch = elements_service.elem_branch
    ops_branch = elements_service.op_branch

    color = Color("red") if op_type.lower() == "cut" else Color("blue")
    op_node = ops_branch.add(
        type=f"op {op_type.lower()}",
        color=color,
        label=f"Camera Trace ({op_type})",
    )

    created_nodes = []

    for obj in detected_objects:
        contour_mm = obj.contour_mm

        path = Path()
        if len(contour_mm) == 0:
            continue

        start_x_units = contour_mm[0][0] * UNITS_PER_MM
        start_y_units = contour_mm[0][1] * UNITS_PER_MM
        path.move(start_x_units, start_y_units)

        for pt in contour_mm[1:]:
            x_units = pt[0] * UNITS_PER_MM
            y_units = pt[1] * UNITS_PER_MM
            path.line(x_units, y_units)

        path.closed()

        elem_node = elements_branch.add(
            type="elem path",
            path=path,
            stroke=color,
            stroke_width=100,
        )
        op_node.add_reference(elem_node)
        created_nodes.append(elem_node)

    elements_service.signal("tree_changed")
    elements_service.signal("refresh_scene")
    return created_nodes


def frame_camera_object(kernel, camera_service=None, object_index=0, frame_type="rect"):
    """
    Perform a red-dot laser framing job around a camera-detected object.

    :param kernel: MadGrav kernel
    :param camera_service: Active Camera service
    :param object_index: Index of detected object to frame (0 for first object)
    :param frame_type: 'rect' (bounding box) or 'contour' (precise contour)
    :return: True if framing command dispatched
    """
    from madgrav.core.units import UNITS_PER_MM

    if camera_service is None:
        camera_service = kernel.camera

    if camera_service is None:
        raise ValueError("No active camera service available.")

    detected_objects = camera_service.detect_objects_and_measure()

    if not detected_objects or object_index < 0 or object_index >= len(detected_objects):
        raise ValueError(f"Target camera object #{object_index} not found.")

    target_obj = detected_objects[object_index]

    if frame_type.lower() == "rect":
        min_x, min_y, w_mm, h_mm = target_obj.bounding_box_mm
        x0 = min_x * UNITS_PER_MM
        y0 = min_y * UNITS_PER_MM
        x1 = (min_x + w_mm) * UNITS_PER_MM
        y1 = (min_y + h_mm) * UNITS_PER_MM

        path = Path()
        path.move(x0, y0)
        path.line(x1, y0)
        path.line(x1, y1)
        path.line(x0, y1)
        path.closed()
    else:
        contour_mm = target_obj.contour_mm
        path = Path()
        path.move(contour_mm[0][0] * UNITS_PER_MM, contour_mm[0][1] * UNITS_PER_MM)
        for pt in contour_mm[1:]:
            path.line(pt[0] * UNITS_PER_MM, pt[1] * UNITS_PER_MM)
        path.closed()

    try:
        device = kernel.device
        if device is not None and hasattr(device, "driver"):
            kernel.console(f"rect {min_x}mm {min_y}mm {w_mm}mm {h_mm}mm\n")
            return True
    except Exception:
        pass

    return False
