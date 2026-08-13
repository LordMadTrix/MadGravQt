# Complete PAO & CAD Vector Suite Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement the complete PAO (Graphic Design & Vector Publishing) and CAD suite in MadGravQt (Boolean CAG operations, Vector Offset, Mirrors/Rotation, Distribution, Box & Gear Generators, Rotary Assistant).

**Architecture:** Add `_create_pao_toolbar()` and handler methods (`_on_cag_union`, `_on_cag_difference`, `_on_mirror_h`, `_on_distribute_h`, `_on_open_offset_dialog`, `_on_open_box_generator`, `_on_open_gear_generator`) in `qt_main.py`.

**Tech Stack:** Python 3.6+, PyQt6, unittest.

## Global Constraints
- Python 3.6+ / PyQt6 compatible.
- All unit tests MUST pass cleanly.

---

### Task 1: PAO Toolbar & CAG Boolean Operations

**Files:**
- Modify: `madgrav/qt/qt_main.py`
- Test: `test/test_qt_main.py`

**Interfaces:**
- Produces: `_create_pao_toolbar()`, `_on_cag_union()`, `_on_cag_difference()`, `_on_cag_intersection()`, `_on_cag_xor()`.

- [x] **Step 1: Write test for CAG boolean handlers**
- [x] **Step 2: Implement CAG boolean handlers in `qt_main.py`**
- [x] **Step 3: Run unit tests**

---

### Task 2: Advanced Alignment, Distribution & Mirrors

**Files:**
- Modify: `madgrav/qt/qt_main.py`
- Test: `test/test_qt_main.py`

**Interfaces:**
- Produces: `_on_mirror_h()`, `_on_mirror_v()`, `_on_rotate_90_cw()`, `_on_distribute_h()`, `_on_distribute_v()`, `_on_match_width()`, `_on_match_height()`.

- [x] **Step 1: Write test for distribution & mirror handlers**
- [x] **Step 2: Implement distribution & mirror methods in `qt_main.py`**
- [x] **Step 3: Run unit tests**

---

### Task 3: Vector Offset & Parametric Generators (Box & Gear)

**Files:**
- Modify: `madgrav/qt/qt_main.py`
- Test: `test/test_qt_main.py`

**Interfaces:**
- Produces: `_on_open_offset_dialog()`, `_on_open_box_generator()`, `_on_open_gear_generator()`.

- [x] **Step 1: Implement Offset & Generator dialog launchers in `qt_main.py`**
- [x] **Step 2: Add PAO toolbar to main window layout**
- [x] **Step 3: Run unit tests**

