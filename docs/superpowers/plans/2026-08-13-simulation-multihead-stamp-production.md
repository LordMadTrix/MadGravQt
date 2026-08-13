# 3D Simulation, Multi-Head Calibration, Stamp/Puzzle & Production Queue Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement 3D G-Code Simulation, Dual-Head Laser Calibration, Rubber Stamp Shoulders & Jigsaw Puzzle Generator, and Workshop Production Queue Manager in MadGravQt.

**Architecture:** Create modular tools `madgrav/tools/gcode_previewer.py`, `madgrav/tools/multi_head_wizard.py`, `madgrav/tools/stamp_puzzle_generator.py`, and `madgrav/tools/production_queue.py` with full unit test coverage.

**Tech Stack:** Python 3.6+, NumPy, OpenCV (cv2), PyQt6, unittest.

## Global Constraints
- Python 3.6+ / PyQt6 compatible.
- All unit tests MUST pass cleanly.

---

### Task 1: 3D G-Code & Path Simulation Engine

**Files:**
- Create: `madgrav/tools/gcode_previewer.py`
- Test: `test/test_simulation_multihead_stamp_production.py`

**Interfaces:**
- Produces: `simulate_laser_path_3d(gcode_text_or_ops, travel_speed_mm_s=200.0, cut_speed_mm_s=20.0)`

- [x] **Step 1: Write test for 3D trajectory calculation & G-Code parsing**
- [x] **Step 2: Implement 3D simulation engine in `madgrav/tools/gcode_previewer.py`**
- [x] **Step 3: Run unit tests**

---

### Task 2: Dual-Head Laser Calibration Wizard

**Files:**
- Create: `madgrav/tools/multi_head_wizard.py`
- Test: `test/test_simulation_multihead_stamp_production.py`

**Interfaces:**
- Produces: `calculate_dual_head_offset(test_cut_coords_head1, test_cut_coords_head2)`

- [x] **Step 1: Write test for dual-head laser offset calculation**
- [x] **Step 2: Implement dual-head wizard module in `madgrav/tools/multi_head_wizard.py`**
- [x] **Step 3: Run unit tests**

---

### Task 3: Rubber Stamp Ramping & Jigsaw Puzzle Generator

**Files:**
- Create: `madgrav/tools/stamp_puzzle_generator.py`
- Test: `test/test_simulation_multihead_stamp_production.py`

**Interfaces:**
- Produces: `generate_rubber_stamp_profile(path, shoulder_width_mm=0.5, ramp_angle_deg=45.0)`, `generate_jigsaw_puzzle_grid(width_mm, height_mm, rows=4, cols=4, tab_size_percent=20.0)`

- [x] **Step 1: Write test for rubber stamp shoulder ramp & jigsaw puzzle generation**
- [x] **Step 2: Implement stamp & puzzle module in `madgrav/tools/stamp_puzzle_generator.py`**
- [x] **Step 3: Run unit tests**

---

### Task 4: Production Queue & Workshop Kiosk Manager

**Files:**
- Create: `madgrav/tools/production_queue.py`
- Test: `test/test_simulation_multihead_stamp_production.py`

**Interfaces:**
- Produces: `ProductionQueueManager` class (`add_job`, `get_next_job`, `mark_job_completed`, `lookup_job_by_barcode`, `export_production_summary`)

- [x] **Step 1: Write test for production job queue, barcode lookup & metrics summary**
- [x] **Step 2: Implement `ProductionQueueManager` in `madgrav/tools/production_queue.py`**
- [x] **Step 3: Run unit tests**

