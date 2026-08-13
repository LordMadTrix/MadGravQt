# Spec Design: UI Reorganization and New Features for MadGravQt

**Date:** 2026-08-12
**Status:** Approved

## Overview
This design document defines the structural reorganization of the MadGravQt interface (PyQt6) and the addition of quick-action alignment, boolean vector operation tools, and material preset selection.

---

## 1. Quick Align & Boolean Operations Toolbar (`madgrav/qt/qt_main.py`)

A new secondary toolbar `QToolBar` added at the top of the canvas layout containing:
- **Alignment Actions**:
  - `Align Left`: Align selected nodes to the minimum X coordinate of the selection bounding box.
  - `Align Center H`: Center selected nodes horizontally on the average X midpoint.
  - `Align Right`: Align selected nodes to the maximum X coordinate.
  - `Align Top`: Align selected nodes to the minimum Y coordinate.
  - `Align Center V`: Center selected nodes vertically on the average Y midpoint.
  - `Align Bottom`: Align selected nodes to the maximum Y coordinate.
  - `Distribute H / V`: Distribute spacing evenly between selected nodes.
- **Boolean Operations**:
  - `Union`: Merge paths of selected geometry nodes.
  - `Difference`: Subtract overlapping top paths from the base path.
  - `Intersection`: Keep overlapping geometric regions.

---

## 2. Right Inspector Dock Restructuring (`madgrav/qt/qt_main.py`)

Reorganize the right side panel into a clean `QTabWidget`:
- **Tab 1: `⚡ Opérations & Calques`**: Contains the operations tree (`QTreeWidget`), layer controls, and element hierarchy.
- **Tab 2: `📐 Position & Transform`**: Form layout with X, Y, Width, Height spinboxes, aspect-ratio lock toggle, and rotation.
- **Tab 3: `📚 Matériaux & Vitesse`**: Preset material selector dropdown (Plywood 3mm, Acrylic 5mm, Leather, Wood, Cardboard) with an "Appliquer" button that auto-populates speed and power fields.

---

## 3. Canvas Integration (`madgrav/qt/qt_canvas.py`)

- Update `MadGravQtCanvas` to provide helper methods for calculating multi-selection bounding boxes and applying alignment transforms.
