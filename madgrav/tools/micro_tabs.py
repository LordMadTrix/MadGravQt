"""
Micro-Tabs (Tabs & Notches / Holding Bridges) module for MadGrav.

Inserts small interruptions (micro-tabs) into vector paths so cut parts remain attached
to the stock material until manually popped out, matching LightBurn's Tabs/Bridges feature.
"""

from madgrav.svgelements import Path


def add_micro_tabs_to_path(path, tab_count=4, tab_size_mm=0.5, tab_width_mm=None):
    """
    Break a Path into multiple segments with small gap micro-tabs.

    :param path: svgelements.Path instance
    :param tab_count: Number of micro-tabs to insert along closed subpaths
    :param tab_size_mm: Size/length of each micro-tab gap in mm
    :param tab_width_mm: Alias for tab_size_mm
    :return: A new svgelements.Path with micro-tabs inserted
    """
    from madgrav.core.units import UNITS_PER_MM

    if tab_width_mm is not None:
        tab_size_mm = tab_width_mm

    if not isinstance(path, Path) or len(path) == 0:
        return path

    tab_size_units = tab_size_mm * UNITS_PER_MM
    total_length = path.length()

    if total_length <= tab_size_units * tab_count * 2.0 or tab_count <= 0:
        return path

    step_len = total_length / float(tab_count)
    new_path = Path()

    for i in range(tab_count):
        start_dist = i * step_len
        end_dist = start_dist + step_len - tab_size_units

        if end_dist > start_dist:
            t0 = start_dist / total_length
            t1 = end_dist / total_length

            # Sample 20 points along segment slice
            sub_pts = [path.point(t0 + (t1 - t0) * (k / 19.0)) for k in range(20)]
            if len(sub_pts) >= 2:
                new_path.move(sub_pts[0])
                for pt in sub_pts[1:]:
                    new_path.line(pt)

    if len(new_path) == 0:
        return path

    return new_path


def apply_tabs_to_selected_nodes(elements_service, tab_count=4, tab_size_mm=0.5, tab_width_mm=None, nodes=None):
    """
    Apply micro-tabs to all currently selected path nodes.

    :param elements_service: The elements service (`kernel.elements`)
    :param tab_count: Number of tabs per path
    :param tab_size_mm: Tab gap size in mm
    :param tab_width_mm: Alias for tab_size_mm
    :param nodes: Optional list of nodes to process
    """
    if tab_width_mm is not None:
        tab_size_mm = tab_width_mm

    if nodes is None:
        nodes = list(elements_service.elems(emphasized=True))
    updated_count = 0

    for node in nodes:
        node_path = getattr(node, "path", None)
        if node_path is None and hasattr(node, "as_geometry"):
            try:
                node_path = node.as_geometry().as_path()
            except Exception:
                node_path = None

        if node_path is not None:
            new_p = add_micro_tabs_to_path(node_path, tab_count=tab_count, tab_size_mm=tab_size_mm)
            if hasattr(node, "path"):
                node.path = new_p
            else:
                # Replace shape with elem path
                parent = getattr(node, "parent", None) or elements_service.elem_branch
                new_node = elements_service.elem_branch.add(
                    type="elem path",
                    path=new_p,
                    stroke=getattr(node, "stroke", elements_service.default_stroke),
                    stroke_width=getattr(node, "stroke_width", 1000.0),
                )
                if parent is not None and hasattr(parent, "remove_node"):
                    parent.remove_node(node)
                node = new_node
            node.altered()
            updated_count += 1

    if updated_count > 0:
        elements_service.signal("tree_changed")
        elements_service.signal("refresh_scene")

    return updated_count
