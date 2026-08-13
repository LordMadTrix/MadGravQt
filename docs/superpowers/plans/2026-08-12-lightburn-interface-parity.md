# LightBurn Interface Parity Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Transform the MadGravQt interface to achieve visual and workflow parity with LightBurn Pro (graduated X/Y rulers, white bed, bottom layer color palette, LightBurn laser control panel).

**Architecture:** Render X/Y graduated rulers and white bed styling in `qt_canvas.py`. Implement bottom layer color palette bar and LightBurn laser control panel in `qt_main.py`.

**Tech Stack:** Python 3.6+, PyQt6, unittest.

## Global Constraints
- Python 3.6+ / PyQt6 compatible.
- All 810 unit tests MUST pass cleanly.

---

### Task 1: Graduated X/Y Rulers & LightBurn Bed Styling

**Files:**
- Modify: `madgrav/qt/qt_canvas.py`
- Test: `test/test_qt_main.py`

**Interfaces:**
- Produces: Graduated X/Y rulers along top/left bed edges and crisp white bed background styling in `MadGravQtCanvas`.

- [x] **Step 1: Write test for ruler rendering & bed background colors**
- [x] **Step 2: Implement top X ruler and left Y ruler in `qt_canvas.py`**
- [x] **Step 3: Update bed colors (`#FFFFFF` bed, `#E2E2E8` grid, `#F4F4F6` background)**
- [x] **Step 4: Run unit tests**
- [x] **Step 5: Commit changes**

---

### Task 2: Bottom Layer Color Swatch Palette Bar

**Files:**
- Modify: `madgrav/qt/qt_main.py`
- Test: `test/test_qt_main.py`

**Interfaces:**
- Produces: LightBurn-style layer color swatch bar (`00` to `29`, `T1`, `T2`) applying colors to selected elements.

- [x] **Step 1: Write test for layer color palette actions**
- [x] **Step 2: Add bottom color palette bar in `qt_main.py`**
- [x] **Step 3: Connect color swatch click handlers to selected elements**
- [x] **Step 4: Run unit tests**
- [x] **Step 5: Commit changes**

---

### Task 3: LightBurn Laser Control Panel & Dock Reorganization

**Files:**
- Modify: `madgrav/qt/qt_main.py`
- Test: `test/test_qt_main.py`

**Interfaces:**
- Produces: LightBurn-style Laser panel (`▶ Démarrer`, `⏸ Suspendre`, `⏹ Arrêter`, `🔲 Cadrer`, `🎯 Accéder à l'origine`, mode dropdown, device combo).

- [x] **Step 1: Update Right Dock tabs (`Coupes/Calques`, `Laser`, `Bibliothèque de matériaux`)**
- [x] **Step 2: Add LightBurn control buttons (`Démarrer`, `Suspendre`, `Arrêter`, `Cadrer`, `Origine`)**
- [x] **Step 3: Run unit tests**
- [x] **Step 4: Commit changes**

