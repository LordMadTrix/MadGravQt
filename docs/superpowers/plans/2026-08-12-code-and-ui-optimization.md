# Code & UI Optimization Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Perform high-impact code and UI optimizations on MadGravQt canvas rendering, Qt signal processing, and visual styling.

**Architecture:** Implement viewport update optimizations, pan/zoom anti-aliasing throttling, LOD rendering, and grid caching in `qt_canvas.py`. Implement signal debouncing and batch updates in `qt_main.py`. Modernize PyQt6 styling in `qt_theme.py`.

**Tech Stack:** Python 3.6+, PyQt6, unittest.

## Global Constraints
- Python 3.6+ / PyQt6 compatible.
- All 810 unittest suite tests MUST continue to pass (`python -m unittest discover -s test`).
- No breaking API changes to `MadGravQtCanvas`, `MadGravQtMainWindow`, or `MODERN_DARK_QSS` / `MODERN_LIGHT_QSS`.

---

### Task 1: Canvas Rendering Optimizations

**Files:**
- Modify: `madgrav/qt/qt_canvas.py`
- Test: `test/test_qt_main.py`

**Interfaces:**
- Produces: Optimized `MadGravQtCanvas` viewport updates, LOD logic, pan/zoom event handling, and grid caching.

- [x] **Step 1: Write tests for canvas optimization flags and LOD behavior**
- [x] **Step 2: Implement ViewportUpdateMode, pan/zoom AA toggle, and grid caching in `qt_canvas.py`**
- [x] **Step 3: Run unit tests to verify non-regression**
- [x] **Step 4: Commit changes**

---

### Task 2: Signal Debouncing & Batch Tree Updates

**Files:**
- Modify: `madgrav/qt/qt_main.py`
- Test: `test/test_qt_main.py`

**Interfaces:**
- Produces: Debounced kernel signal handlers and batch tree widget updates in `MadGravQtMainWindow`.

- [x] **Step 1: Write test for debounced signal handling in `MadGravQtMainWindow`**
- [x] **Step 2: Implement debounced signals and `setUpdatesEnabled` tree batching in `qt_main.py`**
- [x] **Step 3: Run unit tests to verify non-regression**
- [x] **Step 4: Commit changes**

---

### Task 3: Visual Theme Refresh (Dark/Light QSS)

**Files:**
- Modify: `madgrav/qt/qt_theme.py`
- Test: `test/test_qt_main.py`

**Interfaces:**
- Produces: Enhanced `MODERN_DARK_QSS` and `MODERN_LIGHT_QSS` stylesheets.

- [x] **Step 1: Update `MODERN_DARK_QSS` and `MODERN_LIGHT_QSS` with rounded corners, improved contrasts, and dock styling**
- [x] **Step 2: Run unit tests to verify non-regression**
- [x] **Step 3: Commit changes**

