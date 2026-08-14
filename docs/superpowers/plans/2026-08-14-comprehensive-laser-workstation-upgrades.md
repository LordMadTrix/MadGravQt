# Comprehensive Laser Workstation Upgrades Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement 7 major workstation enhancements for MadGrav Qt: Multi-Document Tabs, Live Camera Bed Overlay, Rotary Cylinder Engraving Wizard, OpenGL Hardware Acceleration, Multi-Format Direct Exporter, Variable Text / Excel-CSV Merge, and Multi-Machine Production Spooler.

**Architecture:** Extend `MadGravQtMainWindow` with a `QTabWidget` central multi-document container; enhance `MadGravQtCanvas` with background camera frame projection and `QOpenGLWidget` viewport option; add modular tools in `madgrav/tools/` and modern interactive dialogs in `madgrav/qt/qt_laser_dialogs.py`.

**Tech Stack:** Python 3.10+, PyQt6, PyQt6-Qt6, PyQt6.QtOpenGLWidgets, numpy, pillow, svgelements, unittest.

---

### Task 1: Multi-Document Tabs (Support Multi-Projets)

**Files:**
- Create: `madgrav/qt/qt_document.py`
- Modify: `madgrav/qt/qt_main.py`
- Test: `test/test_qt_multi_document_tabs.py`

**Interfaces:**
- `DocumentTab`: Encapsulates `canvas`, `file_path`, `is_modified`, `undo_stack` per tab.
- `MadGravQtMainWindow`: Adds `tab_widget: QTabWidget`, `_on_new_document()`, `_on_close_document(index)`, `_on_tab_changed(index)`.

- [ ] **Step 1: Write the failing tests in `test/test_qt_multi_document_tabs.py`**
- [ ] **Step 2: Run test to verify failure**
- [ ] **Step 3: Implement `DocumentTab` and integrate `QTabWidget` in `MadGravQtMainWindow`**
- [ ] **Step 4: Run test to verify it passes**
- [ ] **Step 5: Commit**

---

### Task 2: Live Camera Bed Overlay (Superposition Caméra en Direct)

**Files:**
- Modify: `madgrav/qt/qt_canvas.py`
- Modify: `madgrav/qt/qt_main.py`
- Test: `test/test_qt_camera_bed_overlay.py`

**Interfaces:**
- `MadGravQtCanvas.set_camera_overlay(pixmap, opacity=0.5, visible=True)`
- `MadGravQtMainWindow._on_toggle_camera_overlay()`, `_on_camera_opacity_changed(val)`

- [ ] **Step 1: Write failing tests in `test/test_qt_camera_bed_overlay.py`**
- [ ] **Step 2: Run test to verify failure**
- [ ] **Step 3: Implement camera pixmap background painting and opacity slider in canvas**
- [ ] **Step 4: Run test to verify it passes**
- [ ] **Step 5: Commit**

---

### Task 3: Assistant Découpe & Gravure sur Cylindre (Rotary Assistant)

**Files:**
- Modify: `madgrav/tools/rotary_assistant.py`
- Modify: `madgrav/qt/qt_laser_dialogs.py`
- Modify: `madgrav/qt/qt_main.py`
- Test: `test/test_qt_rotary_assistant.py`

**Interfaces:**
- `calculate_rotary_parameters(object_diameter_mm, is_chuck=True, motor_steps=200, microsteps=16, gear_ratio=2.0, roller_diameter_mm=50.0)`
- `RotaryAssistantDialog(QDialog)`

- [ ] **Step 1: Write failing tests in `test/test_qt_rotary_assistant.py`**
- [ ] **Step 2: Run test to verify failure**
- [ ] **Step 3: Implement full rotary calculator and `RotaryAssistantDialog`**
- [ ] **Step 4: Run test to verify it passes**
- [ ] **Step 5: Commit**

---

### Task 4: Accélération Matérielle OpenGL & QGraphicsView

**Files:**
- Modify: `madgrav/qt/qt_canvas.py`
- Modify: `madgrav/qt/qt_main.py`
- Test: `test/test_qt_opengl_acceleration.py`

**Interfaces:**
- `MadGravQtCanvas.enable_opengl(enabled: bool)`
- Action in View menu: `Activer l'accélération matérielle OpenGL`

- [ ] **Step 1: Write failing tests in `test/test_qt_opengl_acceleration.py`**
- [ ] **Step 2: Run test to verify failure**
- [ ] **Step 3: Implement `QOpenGLWidget` viewport switching in `MadGravQtCanvas`**
- [ ] **Step 4: Run test to verify it passes**
- [ ] **Step 5: Commit**

---

### Task 5: Export Direct Multi-Formats (.gcode, .rd, .egv, .dxf, .svg)

**Files:**
- Create: `madgrav/tools/multi_export.py`
- Modify: `madgrav/qt/qt_laser_dialogs.py`
- Modify: `madgrav/qt/qt_main.py`
- Test: `test/test_qt_multi_export.py`

**Interfaces:**
- `export_job_to_file(elements_service, filepath, format_type='gcode', laser_power=100.0, speed_mm_s=20.0)`
- `MultiFormatExportDialog(QDialog)`

- [ ] **Step 1: Write failing tests in `test/test_qt_multi_export.py`**
- [ ] **Step 2: Run test to verify failure**
- [ ] **Step 3: Implement `multi_export.py` and `MultiFormatExportDialog`**
- [ ] **Step 4: Run test to verify it passes**
- [ ] **Step 5: Commit**

---

### Task 6: Assistant Texte Variable & Fusion CSV / Excel

**Files:**
- Modify: `madgrav/tools/variable_text.py`
- Modify: `madgrav/qt/qt_laser_dialogs.py`
- Modify: `madgrav/qt/qt_main.py`
- Test: `test/test_qt_variable_text_csv_merge.py`

**Interfaces:**
- `parse_csv_or_excel(filepath)`
- `VariableTextMergeDialog(QDialog)`

- [ ] **Step 1: Write failing tests in `test/test_qt_variable_text_csv_merge.py`**
- [ ] **Step 2: Run test to verify failure**
- [ ] **Step 3: Implement CSV parser and `VariableTextMergeDialog`**
- [ ] **Step 4: Run test to verify it passes**
- [ ] **Step 5: Commit**

---

### Task 7: File d'Attente de Production Multi-Machines (Multi-Machine Spooler)

**Files:**
- Modify: `madgrav/tools/production_queue.py`
- Modify: `madgrav/qt/qt_laser_dialogs.py`
- Modify: `madgrav/qt/qt_main.py`
- Test: `test/test_qt_multi_machine_spooler.py`

**Interfaces:**
- `ProductionJob.target_machine_id`
- `ProductionQueueManager.dispatch_job(job_id, machine_id)`
- `ProductionQueueDialog(QDialog)` with machine selector and status monitoring

- [ ] **Step 1: Write failing tests in `test/test_qt_multi_machine_spooler.py`**
- [ ] **Step 2: Run test to verify failure**
- [ ] **Step 3: Implement multi-machine queue logic and UI**
- [ ] **Step 4: Run test to verify it passes**
- [ ] **Step 5: Commit**
