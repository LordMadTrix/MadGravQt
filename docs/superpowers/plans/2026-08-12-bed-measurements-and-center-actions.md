# Bed Measurements & Center Alignment Action Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Display bed dimensions at the center of the laser canvas and add a "Center to Bed" shortcut button to the toolbar.

**Architecture:** Render dimension watermark text in `MadGravQtCanvas.drawBackground()` in `qt_canvas.py`. Add `_on_center_to_bed` in `qt_main.py` and register it on the Quick-Align toolbar.

**Tech Stack:** Python 3.6+, PyQt6, unittest.

## Global Constraints
- Python 3.6+ / PyQt6 compatible.
- All unit tests MUST pass cleanly.

---

### Task 1: Bed Measurements Overlay in Canvas

**Files:**
- Modify: `madgrav/qt/qt_canvas.py`
- Test: `test/test_qt_main.py`

**Interfaces:**
- Produces: Center watermark text overlay `[ W mm × H mm ]` in `MadGravQtCanvas.drawBackground()`.

- [x] **Step 1: Implement center bed dimension text rendering in `qt_canvas.py`**
- [x] **Step 2: Verify canvas rendering**

---

### Task 2: Center to Bed Action in Main Window

**Files:**
- Modify: `madgrav/qt/qt_main.py`
- Test: `test/test_qt_main.py`

**Interfaces:**
- Produces: `_on_center_to_bed` method and toolbar button in `qt_main.py`.

- [x] **Step 1: Write `_on_center_to_bed` method**
- [x] **Step 2: Add `🎯 Centrer Table` button to `align_tb` toolbar**
- [x] **Step 3: Run unit tests**
- [x] **Step 4: Commit changes**

