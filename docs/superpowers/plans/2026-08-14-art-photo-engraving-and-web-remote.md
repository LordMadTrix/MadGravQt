# Art & Photo Engraving Studio and Mobile Web Remote Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement the Halftone Photo Engraving Studio, 3D Multi-Layer Topographic Map Generator, Radial Mandala/Rosette Generator, and Mobile Web Remote Controller with QR Code connection in MadGrav Qt.

**Architecture:** 
- `madgrav/tools/halftone_studio.py`: Algorithms converting photos into vector dot matrices, line waves, spirals, and Voronoi stipples.
- `madgrav/tools/topo_map_generator.py`: Generates procedural or heightmap-based multi-layer contour slices with alignment frames.
- `madgrav/tools/mandala_generator.py`: Procedural $K$-fold radial symmetry vector generator.
- `madgrav/network/web_server.py` & `madgrav/network/web_remote_assets.py`: Mobile-friendly REST API (`/api/status`, `/api/jog`, `/api/control`) and responsive dark-mode touch web application.
- `madgrav/qt/qt_laser_dialogs.py` & `madgrav/qt/qt_main.py`: Interactive Qt6 dialogs with live 2D preview, QR Code modal, and menu integration.

**Tech Stack:** Python 3.10+, PyQt6, Pillow (PIL), NumPy, MadGrav Kernel/Elements/Space APIs.

## Global Constraints
- Target platform: Windows / Cross-platform Python 3.10+ PyQt6.
- All new features must have dedicated test suites in `test/`.
- 100% backward compatibility with all existing 890+ unit tests.

---

### Task 1: Halftone & Photo Engraving Studio Core

**Files:**
- Create: `madgrav/tools/halftone_studio.py`
- Test: `test/test_halftone_studio.py`

**Interfaces:**
- Produces: `generate_halftone_vectors(image_input, method='dots', pitch_mm=2.0, min_dot_mm=0.2, max_dot_mm=1.8, angle_deg=45.0, contrast=0, brightness=0, invert=False)` returning list of geometry objects or SVG string.

- [ ] **Step 1: Write the failing unit test**
Create `test/test_halftone_studio.py` testing circle dots, line waves, spirals, and stipples on synthetic test images.

- [ ] **Step 2: Run test to verify it fails**
Run `.\.venv\Scripts\python.exe -m unittest test.test_halftone_studio`

- [ ] **Step 3: Implement `madgrav/tools/halftone_studio.py`**
Implement grayscale sampling, luminance mapping, coordinate transformations, and circle/wave/spiral/stipple vector generation.

- [ ] **Step 4: Run test to verify it passes**
Run `.\.venv\Scripts\python.exe -m unittest -v test.test_halftone_studio`

---

### Task 2: 3D Multi-Layer Topographic Map Generator Core

**Files:**
- Create: `madgrav/tools/topo_map_generator.py`
- Test: `test/test_topo_map_generator.py`

**Interfaces:**
- Produces: `generate_layered_topo_map(preset='island', custom_image=None, width_mm=150.0, height_mm=150.0, layers=5, add_frame=True, pin_diameter_mm=3.0)` returning `List[Dict[str, Any]]` where each layer contains layer name, contours, pin holes, and labels.

- [ ] **Step 1: Write the failing unit test**
Create `test/test_topo_map_generator.py` validating layer slicing, contour generation, pin alignment holes, and bounding frames.

- [ ] **Step 2: Run test to verify it fails**
Run `.\.venv\Scripts\python.exe -m unittest test.test_topo_map_generator`

- [ ] **Step 3: Implement `madgrav/tools/topo_map_generator.py`**
Implement procedural heightmap synthesis, discrete contour slicing, marching squares vectorization, and alignment frame geometry.

- [ ] **Step 4: Run test to verify it passes**
Run `.\.venv\Scripts\python.exe -m unittest -v test.test_topo_map_generator`

---

### Task 3: Radial Mandala & Sacred Geometry Generator Core

**Files:**
- Create: `madgrav/tools/mandala_generator.py`
- Test: `test/test_mandala_generator.py`

**Interfaces:**
- Produces: `generate_mandala_vectors(symmetry=8, outer_radius_mm=50.0, inner_radius_mm=5.0, rings=4, style='floral', bridge_cut=True)` returning vector path elements.

- [ ] **Step 1: Write the failing unit test**
Create `test/test_mandala_generator.py` verifying radial rotations, petal generation, geometry validity, and bridge connections.

- [ ] **Step 2: Run test to verify it fails**
Run `.\.venv\Scripts\python.exe -m unittest test.test_mandala_generator`

- [ ] **Step 3: Implement `madgrav/tools/mandala_generator.py`**
Implement radial symmetric math, petal archetypes (floral, star, gothic, knot), ring generation, and unified vector paths.

- [ ] **Step 4: Run test to verify it passes**
Run `.\.venv\Scripts\python.exe -m unittest -v test.test_mandala_generator`

---

### Task 4: Mobile Web Remote Controller Engine & REST API

**Files:**
- Create: `madgrav/network/web_remote_assets.py`
- Modify: `madgrav/network/web_server.py`
- Test: `test/test_web_remote_controller.py`

**Interfaces:**
- Produces: REST endpoints `/api/status`, `/api/jog`, `/api/control`, `/api/console` and mobile dark-mode touch application at `/`.

- [ ] **Step 1: Write the failing unit test**
Create `test/test_web_remote_controller.py` testing GET `/api/status`, POST `/api/jog`, POST `/api/control`, and CSRF protection.

- [ ] **Step 2: Run test to verify it fails**
Run `.\.venv\Scripts\python.exe -m unittest test.test_web_remote_controller`

- [ ] **Step 3: Implement `web_remote_assets.py` and extend `web_server.py`**
Embed responsive touch UI (D-pad, step buttons, status cards, jog commands, action triggers) and implement JSON REST endpoints.

- [ ] **Step 4: Run test to verify it passes**
Run `.\.venv\Scripts\python.exe -m unittest -v test.test_web_remote_controller`

---

### Task 5: Qt GUI Dialogs & MainWindow Integration

**Files:**
- Modify: `madgrav/qt/qt_laser_dialogs.py`
- Modify: `madgrav/qt/qt_main.py`
- Test: `test/test_qt_art_and_remote_dialogs.py`

**Interfaces:**
- Produces: `HalftoneStudioDialog`, `TopoMapDialog`, `MandalaDialog`, `WebRemoteQrDialog` in `qt_laser_dialogs.py` and menu actions in `qt_main.py`.

- [ ] **Step 1: Write the failing unit test**
Create `test/test_qt_art_and_remote_dialogs.py` testing dialog instantiation, live preview updates, document insertion, and QR Code display.

- [ ] **Step 2: Run test to verify it fails**
Run `.\.venv\Scripts\python.exe -m unittest test.test_qt_art_and_remote_dialogs`

- [ ] **Step 3: Implement Dialogs in `qt_laser_dialogs.py` & wire in `qt_main.py`**
Add dialog classes with interactive parameter controls, add QR Code renderer, and wire menu entries in `Outils Laser` and `Affichage`.

- [ ] **Step 4: Run test to verify it passes**
Run `.\.venv\Scripts\python.exe -m unittest -v test.test_qt_art_and_remote_dialogs`

---

### Task 6: Full Regression Verification

- [ ] **Step 1: Run all new and existing tests**
Run: `.\.venv\Scripts\python.exe -m unittest test.test_halftone_studio test.test_topo_map_generator test.test_mandala_generator test.test_web_remote_controller test.test_qt_art_and_remote_dialogs`
- [ ] **Step 2: Run full repository regression test suite**
Run: `.\.venv\Scripts\python.exe -m unittest -v test.test_qt_main test.test_qt_laser_tools_and_dialogs`
