# Spec Design: Code and UI Optimization for MadGravQt

**Date:** 2026-08-12
**Status:** Draft / Pending Review

## Overview
This specification details the comprehensive performance and UI optimization strategy for MadGravQt. It addresses both canvas rendering responsiveness and UI signal handling throughput, alongside a visual polish of the PyQt6 interface.

---

## 1. Canvas Rendering Optimizations (`madgrav/qt/qt_canvas.py`)

### 1.1 Viewport Update Strategy
- Configure `QGraphicsView.ViewportUpdateMode.BoundingRectViewportUpdate` to constrain redraw operations exclusively to invalidated regions.
- Enable `QGraphicsView.OptimizationFlag.DontSavePainterState` to minimize painter context stack operations during rendering passes.

### 1.2 Interactive Smoothness (Pan & Zoom)
- Dynamically toggle anti-aliasing off during active user interaction (panning or wheel zooming) to maintain a steady 60 FPS frame rate.
- Re-enable anti-aliasing asynchronously via a short single-shot timer once mouse drag / wheel events pause.

### 1.3 Level-of-Detail (LOD) Rendering
- Implement scale-aware item rendering: when view scale is below `0.2`, simplify vector path stroke details and skip high-cost decorative overlays.

### 1.4 Background Grid Caching
- Cache the coordinate workspace grid into a high-density `QPixmap` buffer, updating only when bed dimensions or grid unit settings change, eliminating line-by-line rasterization on every frame.

---

## 2. Code & Signal Handling Optimizations (`madgrav/qt/qt_main.py`)

### 2.1 Signal Debouncing & Throttling
- Wrap high-frequency event listeners (`element_changed`, `tree_changed`, `op_changed`) in a `QTimer`-backed debouncing mechanism (throttle window ~30ms).
- Batch rapid consecutive signals emitted by kernel operations into a single UI tree and scene refresh pass.

### 2.2 Tree Widget Batch Updates
- Freeze visual updates during bulk node insertions or re-orderings in `QTreeWidget` via `setUpdatesEnabled(False)` ... `setUpdatesEnabled(True)`.

### 2.3 Resource Management & Signal Cleanup
- Explicitly disconnect signal listeners and clean up obsolete `QGraphicsItem` handles upon node deletion or tab closure.

---

## 3. UI Styling & Visual Enhancement (`madgrav/qt/qt_theme.py`)

### 3.1 Modern Dark & Light QSS Refinement
- Upgrade `MODERN_DARK_QSS` with a cohesive color palette:
  - Deep dark background: `#1e1e24`
  - Accent / highlight color: `#0a84ff`
  - Container fill: `#2b2b36`
  - Smooth rounded borders (`border-radius: 6px` for buttons, spinboxes, inputs).
- Polish `MODERN_LIGHT_QSS` for high-contrast clarity.

### 3.2 High-DPI & Dock Polish
- Enable high-DPI scaling for toolbars, dock widgets, and status bar elements.
- Refine dock widget titlebars and splitter handles.
