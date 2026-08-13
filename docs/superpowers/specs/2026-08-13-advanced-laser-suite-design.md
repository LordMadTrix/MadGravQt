# Spec Design: Advanced Laser Manufacturing Suite for MadGravQt

**Date:** 2026-08-13
**Status:** Approved

## Overview
This design specification defines 4 next-generation laser manufacturing & PAO features for MadGravQt:
1. **2D Polygon Nesting & Sheet Packing Optimizer** (`madgrav/tools/nesting.py`)
2. **3D Grayscale Laser Relief & Depth Raster Engine** (`madgrav/tools/relief_3d.py`)
3. **Galvo & Fiber Laser Hatching & Wobble Patterns** (`madgrav/tools/galvo_hatching.py`)
4. **Smart Vectorization & Bezier Curve Smoothing** (`madgrav/tools/smart_vectorize.py`)

---

## 1. 2D Polygon Nesting & Sheet Optimizer (`madgrav/tools/nesting.py`)

### 1.1 Architecture & API
- Core function `nest_elements(elements, sheet_width_mm, sheet_height_mm, margin_mm=2.0, rotation_steps=4)`:
  - Takes selected element path nodes.
  - Computes tight oriented bounding boxes and polygonal hulls.
  - Sorts polygons by area descending (largest first).
  - Packs shapes into target sheet dimensions using NFP (No-Fit Polygon) heuristic bin-packing with 0°, 90°, 180°, 270° orientation testing.
  - Updates element matrices with target positions and rotations.
  - Returns count of packed items and efficiency percentage (used area vs sheet area).

---

## 2. 3D Grayscale Laser Relief Engine (`madgrav/tools/relief_3d.py`)

### 2.1 Architecture & API
- Core function `generate_3d_laser_relief(image_np, max_power_percent=100.0, min_power_percent=10.0, invert=False, passes=1)`:
  - Converts grayscale input images to 8-bit heightmaps.
  - Maps pixel luminance values (0–255) linearly to laser PWM power levels (S-values for GRBL / power percentages).
  - Generates bidirectional raster scan lines with power acceleration ramps to eliminate edge burning.
  - Returns `RasterOperation` data structure ready for laser output execution.

---

## 3. Galvo & Fiber Laser Hatch Patterns (`madgrav/tools/galvo_hatching.py`)

### 3.1 Architecture & API
- Core function `apply_galvo_hatch(path, hatch_angle_deg=45.0, line_spacing_mm=0.1, mode="cross", wobble_frequency=50.0, wobble_amplitude_mm=0.2)`:
  - Generates dense vector fill lines inside arbitrary vector paths.
  - Modes:
    - `"line"`: Uni-directional single-angle hatch.
    - `"cross"`: Bi-directional orthogonal cross-hatch (45° / 135°).
    - `"spiral"`: Concentric inward spiral fill.
    - `"wobble"`: High-speed sinusoidal wobble along hatch vectors to widen galvo laser kerf.
  - Returns newly created `Path` node representing the vector hatch geometry.

---

## 4. Smart Vectorization & Curve Smoothing (`madgrav/tools/smart_vectorize.py`)

### 4.1 Architecture & API
- Core function `vectorize_bitmap_to_bezier(image_np, threshold=128, corner_threshold_deg=45.0, error_tolerance_mm=0.1)`:
  - Takes 8-bit image array.
  - Applies Otsu adaptive thresholding and contour extraction (OpenCV `findContours`).
  - Performs Potrace-style cubic Bezier curve fitting to approximate discrete pixel contours with smooth continuous curves.
  - Merges collinear segments and sharp corner detection.
  - Returns list of clean vector `Path` objects.
