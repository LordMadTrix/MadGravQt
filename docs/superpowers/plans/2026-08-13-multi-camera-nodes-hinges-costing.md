# Multi-Camera, Node Editing, Living Hinges & Job Costing Suite Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement Multi-Camera Optical Stitching, Interactive Vector Node Editor, Parametric Living Hinges, and Job Costing & Quote Generator in MadGravQt.

**Architecture:** Create modular tools `madgrav/camera/stitching.py`, `madgrav/tools/node_editor.py`, `madgrav/tools/flex_hinge.py`, and `madgrav/tools/cost_quote.py` with full unit test coverage.

**Tech Stack:** Python 3.6+, NumPy, OpenCV (cv2), PyQt6, unittest.

## Global Constraints
- Python 3.6+ / PyQt6 compatible.
- All unit tests MUST pass cleanly.

---

### Task 1: Multi-Camera Optical Stitching

**Files:**
- Create: `madgrav/camera/stitching.py`
- Test: `test/test_multi_camera_nodes_hinges_costing.py`

**Interfaces:**
- Produces: `stitch_multi_camera_views(camera_images, homography_matrices, target_bed_width_mm, target_bed_height_mm)`

- [x] **Step 1: Write test for multi-camera perspective warping & stitching**
- [x] **Step 2: Implement multi-camera stitching in `madgrav/camera/stitching.py`**
- [x] **Step 3: Run unit tests**

---

### Task 2: Interactive Vector Node Editor

**Files:**
- Create: `madgrav/tools/node_editor.py`
- Test: `test/test_multi_camera_nodes_hinges_costing.py`

**Interfaces:**
- Produces: `VectorNodeEditor` class (`extract_nodes_and_handles`, `move_node`, `move_handle`, `insert_node`, `delete_node`, `toggle_smooth_corner`)

- [x] **Step 1: Write test for Bezier node extraction, move, insert, and delete**
- [x] **Step 2: Implement `VectorNodeEditor` in `madgrav/tools/node_editor.py`**
- [x] **Step 3: Run unit tests**

---

### Task 3: Parametric Living Hinge Generator

**Files:**
- Create: `madgrav/tools/flex_hinge.py`
- Test: `test/test_multi_camera_nodes_hinges_costing.py`

**Interfaces:**
- Produces: `generate_living_hinge(width_mm, height_mm, pattern="straight", cut_length_mm=10.0, gap_length_mm=2.0, line_spacing_mm=1.5)`

- [x] **Step 1: Write test for living hinge flex pattern vector generation**
- [x] **Step 2: Implement flex hinge generator in `madgrav/tools/flex_hinge.py`**
- [x] **Step 3: Run unit tests**

---

### Task 4: Job Cost Estimator & Quote Generator

**Files:**
- Create: `madgrav/tools/cost_quote.py`
- Test: `test/test_multi_camera_nodes_hinges_costing.py`

**Interfaces:**
- Produces: `generate_job_quote(elements, material_cost_per_m2=15.0, machine_rate_per_hour=45.0, setup_fee=5.0, margin_percent=20.0)`

- [x] **Step 1: Write test for job cost calculation and CSV/dict quote output**
- [x] **Step 2: Implement job costing module in `madgrav/tools/cost_quote.py`**
- [x] **Step 3: Run unit tests**

