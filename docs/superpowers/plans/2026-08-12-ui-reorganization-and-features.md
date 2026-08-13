# UI Reorganization and New Features Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Reorganize the MadGravQt UI with a 3-tab inspector dock and add a Quick-Align & Boolean toolbar.

**Architecture:** Add alignment/distribution algorithms and toolbar in `qt_main.py`. Reorganize right dock into `QTabWidget` (Operations, Transform, Materials) in `qt_main.py`. Add multi-item bounding box helpers in `qt_canvas.py`.

**Tech Stack:** Python 3.6+, PyQt6, unittest.

## Global Constraints
- Python 3.6+ / PyQt6 compatible.
- All 810 unit tests MUST pass cleanly.
- Maintain full compatibility with existing console commands and canvas events.

---

### Task 1: Quick-Align & Distribution Logic

**Files:**
- Modify: `madgrav/qt/qt_main.py`
- Test: `test/test_qt_main.py`

**Interfaces:**
- Produces: Alignment actions (Left, Center H, Right, Top, Center V, Bottom, Distribute H/V) for selected elements.

- [x] **Step 1: Write tests for alignment algorithms**
- [x] **Step 2: Implement alignment methods in `qt_main.py`**
- [x] **Step 3: Add Quick-Align toolbar in `_create_toolbar()`**
- [x] **Step 4: Run unit tests**
- [x] **Step 5: Commit changes**

---

### Task 2: Right Inspector Dock Restructuring (3 Tabs)

**Files:**
- Modify: `madgrav/qt/qt_main.py`
- Test: `test/test_qt_main.py`

**Interfaces:**
- Produces: 3-Tab inspector dock (`[⚡ Opérations & Calques]`, `[📐 Position & Transform]`, `[📚 Matériaux & Vitesse]`).

- [x] **Step 1: Reorganize right dock panel layout into `QTabWidget`**
- [x] **Step 2: Connect material presets selector to active operation power/speed**
- [x] **Step 3: Run unit tests**
- [x] **Step 4: Commit changes**

