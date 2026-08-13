# Advanced Laser Manufacturing Suite Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement 2D Polygon Nesting, 3D Grayscale Laser Relief Engine, Galvo/Fiber Laser Hatching, and Smart Bezier Vectorization in MadGravQt.

**Architecture:** Create modular tools `madgrav/tools/nesting.py`, `madgrav/tools/relief_3d.py`, `madgrav/tools/galvo_hatching.py`, and `madgrav/tools/smart_vectorize.py` with full unit test coverage.

**Tech Stack:** Python 3.6+, NumPy, OpenCV (cv2), PyQt6, unittest.

## Global Constraints
- Python 3.6+ / PyQt6 compatible.
- All unit tests MUST pass cleanly.

---

### Task 1: 2D Polygon Nesting & Sheet Packing

**Files:**
- Create: `madgrav/tools/nesting.py`
- Test: `test/test_advanced_laser_suite.py`

**Interfaces:**
- Produces: `nest_elements(elements, sheet_width_mm, sheet_height_mm, margin_mm=2.0, rotation_steps=4)`

- [ ] **Step 1: Write test for polygon nesting**
- [ ] **Step 2: Implement polygon nesting algorithm in `madgrav/tools/nesting.py`**
- [ ] **Step 3: Run unit tests**

---

### Task 2: 3D Grayscale Laser Relief Engine

**Files:**
- Create: `madgrav/tools/relief_3d.py`
- Test: `test/test_advanced_laser_suite.py`

**Interfaces:**
- Produces: `generate_3d_laser_relief(image_np, max_power_percent=100.0, min_power_percent=10.0, invert=False, passes=1)`

- [ ] **Step 1: Write test for 3D grayscale laser relief generation**
- [ ] **Step 2: Implement 3D laser relief raster engine in `madgrav/tools/relief_3d.py`**
- [ ] **Step 3: Run unit tests**

---

### Task 3: Galvo & Fiber Laser Hatch Patterns

**Files:**
- Create: `madgrav/tools/galvo_hatching.py`
- Test: `test/test_advanced_laser_suite.py`

**Interfaces:**
- Produces: `apply_galvo_hatch(path, hatch_angle_deg=45.0, line_spacing_mm=0.1, mode="cross", wobble_frequency=50.0, wobble_amplitude_mm=0.2)`

- [ ] **Step 1: Write test for galvo hatch line & wobble pattern generation**
- [ ] **Step 2: Implement galvo hatching in `madgrav/tools/galvo_hatching.py`**
- [ ] **Step 3: Run unit tests**

---

### Task 4: Smart Vectorization & Bezier Curve Fitting

**Files:**
- Create: `madgrav/tools/smart_vectorize.py`
- Test: `test/test_advanced_laser_suite.py`

**Interfaces:**
- Produces: `vectorize_bitmap_to_bezier(image_np, threshold=128, corner_threshold_deg=45.0, error_tolerance_mm=0.1)`

- [ ] **Step 1: Write test for smart vectorization and Bezier curve fitting**
- [ ] **Step 2: Implement smart vectorizer in `madgrav/tools/smart_vectorize.py`**
- [ ] **Step 3: Run unit tests**
