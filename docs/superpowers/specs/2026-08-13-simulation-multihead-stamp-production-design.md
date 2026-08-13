# Spec Design: 3D Simulation, Multi-Head Calibration, Stamp/Puzzle & Production Queue Suite

**Date:** 2026-08-13
**Status:** Approved

## Overview
This design specification defines 4 manufacturing & workshop modules for MadGravQt:
1. **3D G-Code & Path Simulation Engine** (`madgrav/tools/gcode_previewer.py`)
2. **Dual-Head & Multi-Laser Optical Calibration Wizard** (`madgrav/tools/multi_head_wizard.py`)
3. **Rubber Stamp Shoulder Ramping & Jigsaw Puzzle Generator** (`madgrav/tools/stamp_puzzle_generator.py`)
4. **Production Queue & Workshop Kiosk Mode Manager** (`madgrav/tools/production_queue.py`)

---

## 1. 3D G-Code & Path Simulation Engine (`madgrav/tools/gcode_previewer.py`)

### 1.1 Architecture & API
- Core function `simulate_laser_path_3d(gcode_text_or_ops, travel_speed_mm_s=200.0, cut_speed_mm_s=20.0)`:
  - Parses G-Code text commands or laser operations sequence.
  - Computes 3D trajectory points `(x, y, z, power, moves_type)`.
  - Calculates estimated execution duration, rapid travel distance vs cut distance, and layer depth steps.
  - Returns `SimulationReport` dict containing 3D polyline paths and time breakdown.

---

## 2. Dual-Head & Multi-Laser Calibration Wizard (`madgrav/tools/multi_head_wizard.py`)

### 2.1 Architecture & API
- Core function `calculate_dual_head_offset(test_cut_coords_head1, test_cut_coords_head2)`:
  - Takes alignment test cut coordinates measured by camera or manual input from Head 1 and Head 2.
  - Computes precise X/Y offset deltas `(delta_x, delta_y)` and angular tilt correction.
  - Generates calibration matrix for dual-head laser machines.
  - Returns updated machine configuration settings.

---

## 3. Rubber Stamp Ramping & Jigsaw Generator (`madgrav/tools/stamp_puzzle_generator.py`)

### 3.1 Architecture & API
- Core functions:
  - `generate_rubber_stamp_profile(path, shoulder_width_mm=0.5, ramp_angle_deg=45.0)`:
    - Creates trapezoidal shoulder offset ramps around vector art for durable rubber stamps.
    - Inverts graphic output horizontally (mirror mode) for impression stamping.
  - `generate_jigsaw_puzzle_grid(width_mm, height_mm, rows=4, cols=4, tab_size_percent=20.0)`:
    - Generates interlocking jigsaw puzzle piece vectors with randomized tab/blank cuts.
    - Returns `Path` object ready for vector cutting.

---

## 4. Production Queue & Workshop Kiosk Manager (`madgrav/tools/production_queue.py`)

### 4.1 Architecture & API
- Class `ProductionQueueManager`:
  - Methods:
    - `add_job(job_name, file_path, quantity=1, priority=1)`: Enqueue a manufacturing job.
    - `get_next_job()`: Fetch highest-priority queued job.
    - `mark_job_completed(job_id, duration_sec)`: Update job status and record production metrics.
    - `lookup_job_by_barcode(barcode_string)`: Retrieve job matching barcode scan.
    - `export_production_summary()`: Return daily job count, runtime, and efficiency metrics.
