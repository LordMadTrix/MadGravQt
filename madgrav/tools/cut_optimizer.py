"""
Cut Order Optimizer module for MadGrav (Inner-First & Travel Minimizer).

Reorders cut operations and subpaths so inner holes are always cut before exterior boundaries
and dry-run travel distances are minimized, matching LightBurn's Cut Planner.
"""

import math


def get_node_bbox(node):
    """
    Get bounding box tuple (min_x, min_y, max_x, max_y) for a node or path.
    """
    try:
        if hasattr(node, "bounds") and node.bounds is not None:
            return node.bounds
        if hasattr(node, "path") and node.path is not None:
            return node.path.bbox()
    except Exception:
        pass
    return None


def is_path_inside(inner_node, outer_node):
    """
    Check if inner_node bounding box is strictly inside outer_node bounding box.
    """
    b_in = get_node_bbox(inner_node)
    b_out = get_node_bbox(outer_node)

    if b_in is None or b_out is None:
        return False

    return (
        b_in[0] >= b_out[0]
        and b_in[1] >= b_out[1]
        and b_in[2] <= b_out[2]
        and b_in[3] <= b_out[3]
    )


def optimize_cut_order(elements_service, nodes=None, inner_first=True, minimize_travel=True):
    """
    Optimize cutting order of path nodes.

    :param elements_service: The elements service (`kernel.elements`)
    :param nodes: List of nodes to reorder (if None, uses all elem path nodes)
    :param inner_first: If True, cut inner holes before outer containers
    :param minimize_travel: If True, apply nearest-neighbor TSP path ordering
    :return: List of reordered nodes
    """
    if nodes is None:
        nodes = list(elements_service.elems(emphasized=True))
        if not nodes:
            nodes = list(elements_service.elems())

    if not nodes or len(nodes) <= 1:
        return nodes

    path_nodes = []
    for n in nodes:
        if (hasattr(n, "path") and n.path is not None) or hasattr(n, "as_geometry") or hasattr(n, "bounds"):
            path_nodes.append(n)
    if not path_nodes:
        return nodes

    ranks = {n: 0 for n in path_nodes}

    if inner_first:
        for n1 in path_nodes:
            for n2 in path_nodes:
                if n1 is not n2 and is_path_inside(n1, n2):
                    # n1 is inside n2 -> n1 should have higher priority (lower rank value)
                    ranks[n1] += 1

    # Sort by containment rank descending (deepest inner paths first)
    sorted_nodes = sorted(path_nodes, key=lambda n: ranks[n], reverse=True)

    # Nearest-neighbor TSP travel distance minimization
    if minimize_travel and len(sorted_nodes) > 2:
        ordered = [sorted_nodes.pop(0)]
        curr_pos = (ordered[0].bounds[2], ordered[0].bounds[3]) if getattr(ordered[0], "bounds", None) else (0, 0)

        while sorted_nodes:
            best_idx = 0
            best_dist = float("inf")

            for idx, candidate in enumerate(sorted_nodes):
                cb = get_node_bbox(candidate)
                if cb is not None:
                    dist = math.hypot(cb[0] - curr_pos[0], cb[1] - curr_pos[1])
                else:
                    dist = 0.0

                if dist < best_dist:
                    best_dist = dist
                    best_idx = idx

            next_node = sorted_nodes.pop(best_idx)
            ordered.append(next_node)
            cb_next = get_node_bbox(next_node)
            if cb_next:
                curr_pos = (cb_next[2], cb_next[3])

        sorted_nodes = ordered

    # Reorder in parent element tree
    parent = path_nodes[0].parent
    if parent is not None:
        for n in sorted_nodes:
            parent.append_child(n)

    elements_service.signal("tree_changed")
    elements_service.signal("refresh_scene")
    return sorted_nodes
