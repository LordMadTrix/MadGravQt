# Spec Design: Multi-Camera, Node Editing, Living Hinges & Job Costing Suite

**Date:** 2026-08-13
**Status:** Approved

## Overview
This design specification defines 4 major production modules for MadGravQt:
1. **Multi-Camera Optical Stitching & Calibration** (`madgrav/camera/stitching.py`)
2. **Interactive Vector Node Editing & Bezier Control Handles** (`madgrav/tools/node_editor.py`)
3. **Parametric Living Hinge & Flex Cut Pattern Generator** (`madgrav/tools/flex_hinge.py`)
4. **Laser Job Cost Estimator & Client PDF/CSV Quote Generator** (`madgrav/tools/cost_quote.py`)

---

## 1. Multi-Camera Optical Stitching (`madgrav/camera/stitching.py`)

### 1.1 Architecture & API
- Core function `stitch_multi_camera_views(camera_images, homography_matrices, target_bed_width_mm, target_bed_height_mm)`:
  - Takes a list of OpenCV image arrays from 2 or more cameras.
  - Applies homography perspective correction to warp each camera view into bed coordinate space.
  - Blends overlapping camera regions using linear multi-band feathering to eliminate seam boundaries.
  - Returns composite bed image array (RGB) representing the full unified laser bed overlay.

---

## 2. Interactive Vector Node Editor (`madgrav/tools/node_editor.py`)

### 2.1 Architecture & API
- Class `VectorNodeEditor`:
  - Methods:
    - `extract_nodes_and_handles(path)`: Extract all anchor points `(x, y)` and control points `(c1x, c1y, c2x, c2y)` from `Path` segments.
    - `move_node(path, node_index, new_x, new_y)`: Translate anchor point and update connected Bezier segment.
    - `move_handle(path, node_index, handle_index, new_x, new_y)`: Update Bezier control handle position.
    - `insert_node(path, segment_index, t=0.5)`: Split a path segment and insert a new anchor node.
    - `delete_node(path, node_index)`: Remove anchor point and re-connect neighboring nodes.
    - `toggle_smooth_corner(path, node_index)`: Toggle between smooth continuous control handles and sharp corner point.

---

## 3. Parametric Living Hinge Generator (`madgrav/tools/flex_hinge.py`)

### 3.1 Architecture & API
- Core function `generate_living_hinge(width_mm, height_mm, pattern="straight", cut_length_mm=10.0, gap_length_mm=2.0, line_spacing_mm=1.5)`:
  - Generates flex-cut laser kerf lines allowing wood/plywood/MDF/acrylic to bend cleanly.
  - Supported patterns:
    - `"straight"`: Alternating staggered straight cut lines.
    - `"wave"`: Sine wave flex cuts for organic bends.
    - `"diamond"`: Intersecting diamond mesh cuts for multi-axis bending.
  - Returns `Path` object containing all living hinge cut vectors.

---

## 4. Job Cost Estimator & Quote Generator (`madgrav/tools/cost_quote.py`)

### 4.1 Architecture & API
- Core function `generate_job_quote(elements, material_cost_per_m2=15.0, machine_rate_per_hour=45.0, setup_fee=5.0, margin_percent=20.0)`:
  - Calculates total vector cut length (mm), estimated raster area (mm²), and machine job run time (seconds).
  - Computes material cost, machine operational cost, markup/margin, and total price.
  - Exports clean quote report as a dictionary, CSV string, or formatted text invoice.
