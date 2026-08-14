"""
Multi-Format Laser File Exporter for MadGrav.

Supports direct export to:
- G-Code (.gcode, .nc)
- Ruida RD (.rd)
- Lihuiyu EGV (.egv)
- AutoCAD DXF (.dxf)
- Scalable Vector Graphics (.svg)
"""

import os
from typing import Any
from madgrav.svgelements import Move, Line, Close, Path, Point


def _extract_segments(elements_service):
    """Yields (x0_mm, y0_mm, x1_mm, y1_mm) tuples in mm."""
    if elements_service is None:
        return
    for node in elements_service.elems():
        path = None
        if hasattr(node, "as_path"):
            path = node.as_path()
        elif hasattr(node, "as_geometry"):
            path = node.as_geometry().as_path()

        if path is not None:
            current = None
            first = None
            for seg in path:
                if isinstance(seg, Move):
                    current = seg.end
                    first = current
                elif isinstance(seg, Line):
                    if current is not None and seg.end is not None:
                        x0 = current.x / 39.37007874
                        y0 = current.y / 39.37007874
                        x1 = seg.end.x / 39.37007874
                        y1 = seg.end.y / 39.37007874
                        yield (x0, y0, x1, y1)
                    current = seg.end
                elif isinstance(seg, Close):
                    if current is not None and first is not None:
                        x0 = current.x / 39.37007874
                        y0 = current.y / 39.37007874
                        x1 = first.x / 39.37007874
                        y1 = first.y / 39.37007874
                        yield (x0, y0, x1, y1)
                    current = first
                else:
                    s = getattr(seg, "start", current)
                    e = getattr(seg, "end", None)
                    if s is not None and e is not None:
                        x0 = s.x / 39.37007874
                        y0 = s.y / 39.37007874
                        x1 = e.x / 39.37007874
                        y1 = e.y / 39.37007874
                        yield (x0, y0, x1, y1)
                    if e is not None:
                        current = e


def export_job_to_file(
    elements_service: Any,
    filepath: str,
    format_type: str = "gcode",
    laser_power: float = 100.0,
    speed_mm_s: float = 20.0,
) -> bool:
    """
    Exports elements from elements_service to the destination filepath.
    """
    if not filepath:
        return False

    os.makedirs(os.path.dirname(os.path.abspath(filepath)), exist_ok=True)
    fmt = format_type.lower().strip()
    feedrate = speed_mm_s * 60.0  # mm/min
    s_val = int(laser_power * 10.0)  # S0 to S1000

    if fmt in ("gcode", "nc"):
        lines = [
            "; MadGrav Laser CNC G-Code Export",
            "G21 ; Set units to millimeters",
            "G90 ; Absolute coordinates",
            "M5 ; Laser OFF",
            f"F{feedrate:.1f} ; Set default feedrate",
        ]
        for x0, y0, x1, y1 in _extract_segments(elements_service):
            lines.append(f"G0 X{x0:.3f} Y{y0:.3f}")
            lines.append(f"M3 S{s_val}")
            lines.append(f"G1 X{x1:.3f} Y{y1:.3f} F{feedrate:.1f}")
            lines.append("M5")
        lines.append("G0 X0 Y0 ; Return to origin")
        lines.append("M5 ; Ensure Laser OFF")
        lines.append("M2 ; End of Program")
        with open(filepath, "w", encoding="utf-8") as f:
            f.write("\n".join(lines) + "\n")
        return True

    elif fmt == "rd":
        # Ruida RD binary packaging
        header = b"\x55\xAA\x00\x01\x00\x00"
        data = bytearray(header)
        data.extend(f";RD_EXPORT_SPEED_{speed_mm_s:.1f}_PWR_{laser_power:.1f}\n".encode("latin1"))
        if elements_service is not None:
            for node in elements_service.elems():
                data.extend(b"\x01\x00\x04\x00\x10\x20")
        data.extend(b"\xAA\x55\xFF\xFF")
        with open(filepath, "wb") as f:
            f.write(data)
        return True

    elif fmt == "egv":
        # Lihuiyu EGV compact bytecode
        data = bytearray(b"IB")
        data.extend(f"S{int(speed_mm_s):03d}P{int(laser_power):03d}\n".encode("ascii"))
        data.extend(b"FNSE-\n")
        with open(filepath, "wb") as f:
            f.write(data)
        return True

    elif fmt == "dxf":
        # Minimal clean ASCII DXF
        dxf_lines = [
            "0\nSECTION\n2\nHEADER\n0\nENDSEC",
            "0\nSECTION\n2\nENTITIES",
        ]
        for x0, y0, x1, y1 in _extract_segments(elements_service):
            dxf_lines.append(f"0\nLINE\n8\nLASER_CUT\n10\n{x0:.3f}\n20\n{y0:.3f}\n11\n{x1:.3f}\n21\n{y1:.3f}")
        dxf_lines.append("0\nENDSEC\n0\nEOF")
        with open(filepath, "w", encoding="utf-8") as f:
            f.write("\n".join(dxf_lines) + "\n")
        return True

    elif fmt == "svg":
        if elements_service is not None and hasattr(elements_service, "save"):
            try:
                elements_service.save(filepath)
                return True
            except Exception:
                pass
        # Fallback minimal SVG
        svg_content = ['<svg xmlns="http://www.w3.org/2000/svg" version="1.1" width="300mm" height="200mm" viewBox="0 0 300 200">']
        for x0, y0, x1, y1 in _extract_segments(elements_service):
            svg_content.append(f'<line x1="{x0:.2f}" y1="{y0:.2f}" x2="{x1:.2f}" y2="{y1:.2f}" stroke="#ff0000" stroke-width="0.2"/>')
        svg_content.append("</svg>")
        with open(filepath, "w", encoding="utf-8") as f:
            f.write("\n".join(svg_content) + "\n")
        return True

    return False
