# Spec Design: Bed Measurements Overlay & Center Alignment Action

**Date:** 2026-08-12
**Status:** Approved

## Overview
This design document details displaying real-time laser bed dimensions at the center of the canvas in `MadGravQtCanvas` and adding a "Center to Bed" shortcut action to the quick-align toolbar in `MadGravQtMainWindow`.

---

## 1. Canvas Bed Dimensions Overlay (`madgrav/qt/qt_canvas.py`)

### 1.1 Center Bed Text Overlay
- In `MadGravQtCanvas.drawBackground()`, after painting the bed background rect and grid lines, render a clean, high-contrast watermark text label at the exact center of the bed:
  `[ W.W mm × H.H mm ]` (e.g. `300.0 mm × 200.0 mm`).
- The text uses a subtle semi-transparent accent color (`#0A84FF` with 40% opacity in dark theme, `#0066CC` in light theme) so it remains easily readable without distracting from overlayed vector elements.

---

## 2. Center to Bed & Origin Presets (`madgrav/qt/qt_main.py`)

### 2.1 Center to Bed Action
- Implement `_on_center_to_bed()`:
  Calculates the bounding box midpoint of all selected nodes `(curr_x, curr_y)` and translates them so their midpoint aligns with `(bed_width / 2.0, bed_height / 2.0)`.
- Add a prominent `🎯 Centrer Table` button to the Quick-Align toolbar.

---

## 3. Verification Plan
- Unit tests verifying matrix translation on `_on_center_to_bed()`.
- Empirical verification in `run_qt.py`.
