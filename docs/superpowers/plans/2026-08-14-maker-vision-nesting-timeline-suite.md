# Plan d'Implémentation : Suite Maker, Vision, Nesting & Workflow Atelier

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implémenter la suite complète 4-en-1 pour MadGravQt : Inlay/Marqueterie & Boîtes T-Slot, Scrap Finder & Print & Cut, Nesting 2D & Matrice de test matériaux, Timeline d'accélération & Mode Kiosque tactile.

**Architecture:** Développer les moteurs géométriques et algorithmiques modulaires dans `madgrav/tools/`, les interfaces utilisateur interactives avec prévisualisation vectorielle dans `madgrav/qt/qt_laser_dialogs.py`, intégrer les actions dans `madgrav/qt/qt_main.py`, et valider avec des tests unitaires complets.

**Tech Stack:** Python 3.10+, PyQt6, numpy, svgelements, unittest.

---

### Task 1: Suite Outils Maker & Incrustation (Inlay & T-Slot Box)

**Files:**
- Create: `madgrav/tools/inlay_generator.py`
- Create: `madgrav/tools/tslot_box_generator.py`
- Modify: `madgrav/qt/qt_laser_dialogs.py`
- Test: `test/test_qt_inlay_and_tslot.py`

**Interfaces:**
- `generate_inlay_paths(shape_points, kerf_mm=0.15, clearance_mm=0.05, corner_type='sharp') -> (male_path, female_path)`
- `generate_tslot_box_svg(width, height, depth, thickness, screw_diameter=3.0, nut_width=5.5, nut_thickness=2.4) -> str`
- `InlayWizardDialog(QDialog)`, `TSlotBoxDialog(QDialog)`

- [ ] **Step 1: Write failing tests in `test/test_qt_inlay_and_tslot.py`**
- [ ] **Step 2: Run test to verify failure**
- [ ] **Step 3: Implement `inlay_generator.py`, `tslot_box_generator.py`, `InlayWizardDialog`, `TSlotBoxDialog`**
- [ ] **Step 4: Run test to verify it passes**
- [ ] **Step 5: Commit**

---

### Task 2: Suite Vision & Calage Intelligent (Scrap Finder & Print & Cut)

**Files:**
- Create: `madgrav/tools/scrap_finder.py`
- Create: `madgrav/tools/print_and_cut.py`
- Modify: `madgrav/qt/qt_laser_dialogs.py`
- Test: `test/test_qt_scrap_and_fiducial.py`

**Interfaces:**
- `find_usable_scrap_zones(image_array_or_path, min_area_mm2=100.0, threshold=128) -> list[dict]`
- `compute_fiducial_transform(design_points, camera_points, mode='2point') -> tuple[float, float, float, float]`
- `ScrapFinderDialog(QDialog)`, `PrintAndCutDialog(QDialog)`

- [ ] **Step 1: Write failing tests in `test/test_qt_scrap_and_fiducial.py`**
- [ ] **Step 2: Run test to verify failure**
- [ ] **Step 3: Implement `scrap_finder.py`, `print_and_cut.py`, `ScrapFinderDialog`, `PrintAndCutDialog`**
- [ ] **Step 4: Run test to verify it passes**
- [ ] **Step 5: Commit**

---

### Task 3: Suite Optimisation Pro & Matériaux (Nesting 2D & Material Matrix)

**Files:**
- Create: `madgrav/tools/trueshape_nesting.py`
- Create: `madgrav/tools/material_matrix.py`
- Modify: `madgrav/qt/qt_laser_dialogs.py`
- Test: `test/test_qt_nesting_and_matrix.py`

**Interfaces:**
- `pack_shapes_2d(shapes, sheet_width, sheet_height, margin=5.0, spacing=2.0, rotations=[0, 90, 180, 270]) -> dict`
- `generate_material_test_matrix_elements(speeds, powers, cell_size_mm=10.0, gap_mm=2.0) -> list`
- `TrueShapeNestingDialog(QDialog)`, `MaterialMatrixTestDialog(QDialog)`

- [ ] **Step 1: Write failing tests in `test/test_qt_nesting_and_matrix.py`**
- [ ] **Step 2: Run test to verify failure**
- [ ] **Step 3: Implement `trueshape_nesting.py`, `material_matrix.py`, `TrueShapeNestingDialog`, `MaterialMatrixTestDialog`**
- [ ] **Step 4: Run test to verify it passes**
- [ ] **Step 5: Commit**

---

### Task 4: Suite Workflow & Ergonomie Atelier (Laser Timeline & Mode Kiosque)

**Files:**
- Create: `madgrav/tools/laser_timeline.py`
- Modify: `madgrav/qt/qt_laser_dialogs.py`
- Test: `test/test_qt_timeline_and_kiosk.py`

**Interfaces:**
- `calculate_cutcode_timeline(cutcode_elements, accel_mm_s2=3000.0, rapid_speed=200.0) -> dict`
- `LaserTimelineDialog(QDialog)`
- `WorkshopKioskWindow(QMainWindow)`

- [ ] **Step 1: Write failing tests in `test/test_qt_timeline_and_kiosk.py`**
- [ ] **Step 2: Run test to verify failure**
- [ ] **Step 3: Implement `laser_timeline.py`, `LaserTimelineDialog`, `WorkshopKioskWindow`**
- [ ] **Step 4: Run test to verify it passes**
- [ ] **Step 5: Commit**

---

### Task 5: Intégration dans `MadGravQtMainWindow` & Menus

**Files:**
- Modify: `madgrav/qt/qt_main.py`
- Test: `test/test_qt_mega_suite.py`

**Interfaces:**
- Actions de menu et raccourcis : Inlay Wizard, T-Slot Box, Scrap Finder, Print & Cut, True-Shape Nesting, Material Matrix Test, Laser Timeline, Workshop Kiosk Mode (F11).

- [ ] **Step 1: Write failing test verifying all menu triggers exist and instantiate dialogs**
- [ ] **Step 2: Run test to verify failure**
- [ ] **Step 3: Add menu items, toolbar buttons, keyboard shortcut bindings in `qt_main.py`**
- [ ] **Step 4: Run full test suite to verify 100% PASS**
- [ ] **Step 5: Commit**
