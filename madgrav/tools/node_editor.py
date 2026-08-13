"""
Interactive Vector Node Editor & Bezier Handle Manipulation for MadGrav.
Extracts, translates, inserts, and deletes vector path nodes.
"""

from madgrav.svgelements import Path, Point, Line, CubicBezier, Move, Close


class VectorNodeEditor:
    """Helper class for manipulating vector path nodes and Bezier control handles."""

    @staticmethod
    def extract_nodes_and_handles(path):
        """Extract all anchor points and control handles from a Path."""
        nodes = []
        if not path:
            return nodes

        for idx, segment in enumerate(path):
            if hasattr(segment, "end") and segment.end is not None:
                pt = segment.end
                node_data = {
                    "index": idx,
                    "type": type(segment).__name__,
                    "x": float(pt.x),
                    "y": float(pt.y),
                    "control1": None,
                    "control2": None,
                }
                if hasattr(segment, "control1") and segment.control1 is not None:
                    node_data["control1"] = (float(segment.control1.x), float(segment.control1.y))
                if hasattr(segment, "control2") and segment.control2 is not None:
                    node_data["control2"] = (float(segment.control2.x), float(segment.control2.y))
                nodes.append(node_data)
        return nodes

    @staticmethod
    def move_node(path, node_index, new_x, new_y):
        """Move the anchor point of segment at node_index."""
        if not path or node_index < 0 or node_index >= len(path):
            return False

        seg = path[node_index]
        if hasattr(seg, "end") and seg.end is not None:
            seg.end = Point(new_x, new_y)
            return True
        return False

    @staticmethod
    def insert_node(path, segment_index):
        """Insert a midpoint node into the specified segment."""
        if not path or segment_index < 0 or segment_index >= len(path):
            return False

        seg = path[segment_index]
        if hasattr(seg, "point"):
            mid = seg.point(0.5)
            new_line = Line(mid, seg.end)
            seg.end = mid
            path.insert(segment_index + 1, new_line)
            return True
        return False

    @staticmethod
    def delete_node(path, node_index):
        """Delete the node at node_index."""
        if not path or len(path) <= 1 or node_index < 0 or node_index >= len(path):
            return False

        del path[node_index]
        return True
