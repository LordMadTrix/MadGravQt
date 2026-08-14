import csv
import datetime
import os
import re
from copy import copy
from madgrav.svgelements import Matrix


def parse_csv_or_excel(filepath: str) -> list[dict[str, str]]:
    """Parse CSV or tabular file into a list of record dicts."""
    if not filepath or not os.path.exists(filepath):
        return []
    records = []
    try:
        with open(filepath, "r", encoding="utf-8-sig") as f:
            sample = f.read(2048)
            f.seek(0)
            delimiter = ","
            try:
                dialect = csv.Sniffer().sniff(sample)
                delimiter = dialect.delimiter
            except Exception:
                if ";" in sample:
                    delimiter = ";"
                elif "\t" in sample:
                    delimiter = "\t"
            reader = csv.DictReader(f, delimiter=delimiter)
            for row in reader:
                clean_row = {k.strip(): str(v).strip() for k, v in row.items() if k is not None}
                records.append(clean_row)
    except Exception:
        pass
    return records


def generate_merged_variable_layout(
    elements_service,
    records,
    template_pattern="{Nom}",
    columns=3,
    spacing_x_mm=50.0,
    spacing_y_mm=20.0,
    start_x_mm=10.0,
    start_y_mm=10.0,
):
    """Generates a grid of merged text nodes based on records."""
    from madgrav.core.units import UNITS_PER_MM
    from madgrav.svgelements import Text
    from madgrav.core.node.elem_text import TextNode

    created_nodes = []
    cols = max(1, int(columns))
    for i, record in enumerate(records):
        col = i % cols
        row = i // cols
        pos_x = (start_x_mm + col * spacing_x_mm) * UNITS_PER_MM
        pos_y = (start_y_mm + row * spacing_y_mm) * UNITS_PER_MM

        text_val = template_pattern
        for k, v in record.items():
            text_val = text_val.replace(f"{{{k}}}", str(v))
        text_val = substitute_variable_text(text_val, index=i, csv_row=record)

        node = TextNode(text=Text(text_val, x=pos_x, y=pos_y))
        if hasattr(elements_service, "elem_branch") and elements_service.elem_branch is not None:
            elements_service.elem_branch.add_node(node)
        elif hasattr(elements_service, "add_node"):
            elements_service.add_node(node)
        created_nodes.append(node)

    if hasattr(elements_service, "signal"):
        elements_service.signal("tree_changed")
        elements_service.signal("refresh_scene")
    return created_nodes


def substitute_variable_text(template_str, index=0, csv_row=None):
    """
    Substitute variable tags in a text string.

    Supported tags:
    - {serial} or {serial:04d} -> incrementing serial number
    - {idx} -> index number
    - {date} -> current ISO date (YYYY-MM-DD)
    - {time} -> current time (HH:MM:SS)
    - {csv:col_name} or {csv:0} -> CSV column value

    :param template_str: Input text template string
    :param index: Current batch index number (0-based)
    :param csv_row: Optional dict or list of CSV row values
    :return: Substituted text string
    """
    if not isinstance(template_str, str) or "{" not in template_str:
        return template_str

    result = template_str
    now = datetime.datetime.now()

    # {date} and {time}
    result = result.replace("{date}", now.strftime("%Y-%m-%d"))
    result = result.replace("{time}", now.strftime("%H:%M:%S"))

    # {idx}
    result = result.replace("{idx}", str(index))

    # {serial} or {serial:format}
    def replace_serial(match):
        fmt = match.group(1)
        if fmt:
            try:
                return f"{index + 1:{fmt}}"
            except ValueError:
                pass
        return str(index + 1)

    result = re.sub(r"\{serial(?::([^}]+))?\}", replace_serial, result)

    # {csv:key} or {csv:index}
    if csv_row is not None:
        def replace_csv(match):
            key = match.group(1).strip()
            if isinstance(csv_row, dict) and key in csv_row:
                return str(csv_row[key])
            if isinstance(csv_row, (list, tuple)):
                try:
                    idx = int(key)
                    if 0 <= idx < len(csv_row):
                        return str(csv_row[idx])
                except ValueError:
                    pass
            return match.group(0)

        result = re.sub(r"\{csv:([^}]+)\}", replace_csv, result)

    return result


def apply_variable_text_serialization(
    elements_service,
    nodes=None,
    csv_rows=None,
    count=5,
    offset_x_mm=0.0,
    offset_y_mm=20.0,
):
    """
    Perform batch variable text substitution and duplication across multiple items.

    :param elements_service: The elements service (`kernel.elements`)
    :param nodes: List of TextNode elements to serialize (if None, scans emphasized text nodes)
    :param csv_rows: Optional list of dicts/lists from CSV
    :param count: Total items to generate if csv_rows is None
    :param offset_x_mm: X offset between serialized items in mm
    :param offset_y_mm: Y offset between serialized items in mm
    :return: List of generated TextNodes
    """
    from madgrav.core.units import UNITS_PER_MM

    if nodes is None:
        nodes = [n for n in elements_service.elems(emphasized=True) if getattr(n, "type", "") == "elem text"]
        if not nodes:
            nodes = [n for n in elements_service.elems(types="elem text")]

    if not nodes:
        return []

    num_items = len(csv_rows) if csv_rows else count
    created_nodes = []

    for i in range(num_items):
        row_data = csv_rows[i] if csv_rows and i < len(csv_rows) else None

        dx = i * offset_x_mm * UNITS_PER_MM
        dy = i * offset_y_mm * UNITS_PER_MM

        for text_node in nodes:
            orig_text = getattr(text_node, "text", "")
            new_text = substitute_variable_text(orig_text, index=i, csv_row=row_data)

            copy_node = copy(text_node)
            copy_node.text = new_text
            if getattr(copy_node, "matrix", None) is not None:
                copy_node.matrix = Matrix(copy_node.matrix)
                copy_node.matrix.post_translate(dx, dy)
            else:
                copy_node.matrix = Matrix.translate(dx, dy)

            copy_node.altered()
            parent = getattr(text_node, "parent", None)
            if parent is not None:
                parent.add_node(copy_node)
            else:
                elements_service.elem_branch.add_node(copy_node)
            created_nodes.append(copy_node)

    elements_service.signal("tree_changed")
    elements_service.signal("refresh_scene")
    return created_nodes
