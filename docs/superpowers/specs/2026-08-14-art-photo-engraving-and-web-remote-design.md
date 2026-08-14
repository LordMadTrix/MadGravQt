# Design Specification: Art & Photo Engraving Studio and Mobile Web Remote Controller

**Date:** 2026-08-14  
**Author:** Antigravity  
**Status:** Approved by User  

---

## 1. Overview & Objectives

This specification defines the architecture, data structures, algorithms, user interfaces, and test suites for two major high-value feature groups in MadGrav Qt:

1. **Mobile Web Remote Controller (`Web Remote & Touch Jog`)**:
   - Modern, mobile-first responsive web application served on local Wi-Fi.
   - Touch D-Pad for X/Y/Z motion, speed and step sizing (0.1mm, 1mm, 10mm, 50mm).
   - Fast machine actions: Home, Set Origin, Frame Bounding Box, Laser Pulse/Fire, Start, Pause, E-Stop.
   - Real-time polling/SSE or JSON status updates (coordinates, active device, state, progress).
   - QR Code dialog inside Qt (`Affichage > Télécommande Mobile Web (QR Code)...`) allowing instant smartphone connection.

2. **Artistic Design & Photo Engraving Studio**:
   - **Halftone & Photo Engraving Generator (`HalftoneStudio`)**: Converts raster photos into vector dots, line waves, spirals, or Voronoi stipples with customizable pitch, diameter, angle, contrast, brightness, and negative inversion.
   - **3D Multi-Layer Topographic Map Generator (`LayeredTopoGenerator`)**: Generates layered elevation contours for stacked wooden/acrylic art with alignment frames and contour engraving.
   - **Mandala & Rosette Vector Generator (`MandalaGenerator`)**: Procedural radial symmetry vector generator (4 to 24-fold symmetry, petal styles, concentric rings, cut-safe bridging).

---

## 2. Component Architecture

```
madgrav/
├── network/
│   ├── web_server.py                 # Upgraded HTTP server with REST API & Mobile Web App
│   └── web_remote_assets.py          # Embedded modern responsive Mobile UI HTML/CSS/JS
├── tools/
│   ├── halftone_studio.py            # Halftone, wave, spiral, and stipple vector generation
│   ├── topo_map_generator.py         # Multi-layer topographic contour slicing & frame generation
│   └── mandala_generator.py          # Parametric radial mandala & rosette vector generator
└── qt/
    ├── qt_laser_dialogs.py           # HalftoneStudioDialog, TopoMapDialog, MandalaDialog, WebRemoteQrDialog
    └── qt_main.py                    # Menu actions, status bar link, shortcut bindings
```

---

## 3. Detailed Specifications

### 3.1 Mobile Web Remote (`madgrav/network/web_server.py` & `madgrav/network/web_remote_assets.py`)

#### Endpoints
- `GET /` : Serves the responsive mobile dark-mode touch application.
- `GET /api/status` : Returns JSON `{ state, device, x, y, z, progress, speed, power, armed }`.
- `POST /api/jog` : Body `{ axis: 'X'|'Y'|'Z', distance: float, speed: float }` -> executes relative move command.
- `POST /api/control` : Body `{ action: 'home'|'origin'|'frame'|'pulse'|'start'|'pause'|'estop' }` -> executes machine action.
- `POST /api/console` : Body `{ cmd: string }` -> executes arbitrary console command.

#### Qt UI
- `WebRemoteQrDialog` in `qt_laser_dialogs.py`:
  - Detects local network IP addresses.
  - Draws a high-contrast QR Code vector/pixmap.
  - Displays copyable URL (e.g. `http://192.168.1.45:8080`).
  - Toggle button to start/stop the web server.

---

### 3.2 Halftone & Photo Engraving Studio (`madgrav/tools/halftone_studio.py`)

#### Algorithms
1. **Circle Halftone**:
   - Subdivides image into a grid of pitch $P \times P$ mm.
   - Samples average luminance $L \in [0, 1]$ in each cell.
   - Generates vector circle with radius $r = r_{\min} + (1 - L) \times (r_{\max} - r_{\min})$ (or inverted).
   - Supports grid rotation by angle $\theta$ (e.g. 45° standard rosette angle).
2. **Line / Wave Halftone**:
   - Generates horizontal, vertical or sine-wavy lines where line thickness or segment amplitude modulates with image darkness.
3. **Spiral Halftone**:
   - Generates Archimedean spiral $r = a + b\theta$ with modulated stroke width or dot radii.
4. **Voronoi / Random Stippling**:
   - Weighted random point distribution based on darkness density.

#### Qt UI
- `HalftoneStudioDialog`:
  - Image picker & live preview with before/after view.
  - Sliders: Method (Dots, Waves, Spiral, Stipple), Pitch (0.5 to 10 mm), Dot Min/Max (0.1 to 5 mm), Contrast (-100 to +100), Invert.
  - Button "Appliquer au document" creating vector elements into the active document.

---

### 3.3 Multi-Layer Topographic Map Generator (`madgrav/tools/topo_map_generator.py`)

#### Algorithms
- Generates 2D procedural Perlin/Simplex-like heightmaps or takes a grayscale image.
- Slices the heightmap into $N$ discrete threshold layers (e.g. Layer 0 to Layer $N-1$).
- Vectorizes contour lines per layer using marching squares / contour tracing.
- Creates separate grouped nodes in MadGrav elements tree:
  - Outer alignment frame with dowel pin holes.
  - Base layer (solid backing).
  - Intermediate layers (cutouts for water/valleys, engraved contour lines).
  - Top layers (peak contours).

#### Qt UI
- `TopoMapDialog`:
  - Preset shapes: Island, Volcano, Canyon, Mountain Range, Lake Basin, or Custom Image.
  - Layer count spinbox (3 to 12 layers), Dimensions (Width, Height mm).
  - Option to generate alignment pin holes and layer index text.

---

### 3.4 Mandala & Sacred Geometry Generator (`madgrav/tools/mandala_generator.py`)

#### Algorithms
- Configurable number of radial petals $K \in [3, 32]$.
- Concentric rings $R_1, R_2, \dots, R_m$ with customizable petal profiles:
  - Pointed arch, Lotus petal, Geometric star, Clover loop, Celtic knot loops.
- Automatic rotation around $(x_0, y_0)$ by $\frac{2\pi}{K} \times k$ for $k = 0 \dots K-1$.
- Automatic union and closed path validation for clean laser cutting.

#### Qt UI
- `MandalaGeneratorDialog`:
  - Radial Symmetry Slider (4, 6, 8, 12, 16, 24).
  - Ring count, outer diameter mm, inner diameter mm.
  - Style presets: Floral, Sacred Geometry, Starburst, Gothic Rose Window.
  - Live 2D vector preview.

---

## 4. Verification Plan

### Automated Unit Tests
1. `test_halftone_studio.py`:
   - Circle halftone generation from synthetic image.
   - Wave and spiral halftone mathematical continuity.
   - Pitch, contrast, and inversion transformations.
2. `test_topo_map_generator.py`:
   - Heightmap slicing into discrete $N$ layers.
   - Contour polygon extraction and alignment frame generation.
3. `test_mandala_generator.py`:
   - Radial symmetry generation across various $K$-fold symmetries.
   - SVG geometry extraction and node creation.
4. `test_web_remote_controller.py`:
   - REST API endpoints (`/api/status`, `/api/jog`, `/api/control`).
   - CSRF token validation and error handling.
5. `test_qt_art_and_remote_dialogs.py`:
   - Dialog instantiation, parameter modification, and element tree insertion in Qt6.

---

## 5. Self-Review
- No placeholders or ambiguities.
- Complete isolation between modules.
- Full compatibility with existing Kernel, Canvas, and Document Tab infrastructure.
