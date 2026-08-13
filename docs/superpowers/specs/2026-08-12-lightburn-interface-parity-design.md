# Spec Design: LightBurn-Style Interface Parity for MadGravQt

**Date:** 2026-08-12
**Status:** Approved

## Overview
This design specification defines the UI transformation of MadGravQt to achieve visual and workflow parity with LightBurn Pro 2.1. It includes interactive X/Y graduated rulers along the canvas, a white bed background with fine grid lines, a bottom layer color swatch palette, and LightBurn-styled right dock panels (Coupes/Calques, Laser, Bibliothèque de matériaux).

---

## 1. Canvas Rulers & Bed Styling (`madgrav/qt/qt_canvas.py`)

### 1.1 Graduated Rulers (X & Y Axes)
- Add a top horizontal ruler and a left vertical ruler in `MadGravQtCanvas.drawBackground()`.
- Rulers render tick marks and numeric labels every 20mm (`0`, `20`, `40`, `60`, `80`, `100`, `120`... up to `400mm` or active bed dimensions).
- Include subtle cursor position indicator ticks on both rulers following mouse movement.

### 1.2 Bed Color & Grid Styling
- Worktable bed uses a crisp white background (`#FFFFFF`) with thin gray grid lines (`#E2E2E8`) at 10mm secondary / 50mm primary steps.
- Workspace outside the bed uses light gray (`#F4F4F6` in light theme, `#181820` in dark theme).
- Origin point at (0, 0) features Red X-axis and Green Y-axis coordinate indicators.

---

## 2. Bottom Layer Color Swatch Bar (`madgrav/qt/qt_main.py` & `qt_theme.py`)

### 2.1 Color Swatch Buttons
- Create a bottom horizontal palette bar `QHBoxLayout` above the status bar containing the standard LightBurn layer color swatches:
  - `00` (Black `#000000`)
  - `01` (Blue `#0000FF`)
  - `02` (Red `#FF0000`)
  - `03` (Green `#00E000`)
  - `04` (Yellow `#FFE000`)
  - `05` (Orange `#FF8000`)
  - `06` (Cyan `#00E0E0`)
  - `07` (Magenta `#E000E0`)
  - ... up to `29`, plus `T1` (Orange Tool), `T2` (Blue Tool).
- Clicking any color swatch sets the stroke/fill color and layer code of all currently selected canvas elements.

---

## 3. Right Dock Panels & Laser Controller (`madgrav/qt/qt_main.py`)

### 3.1 Tabbed Panels Structure
- **Tab 1: `Coupes/Calques`**: Lists operations/layers with colored swatch badges, layer names, speed, power, and pass count.
- **Tab 2: `Laser`**:
  - Control buttons: `▶ Démarrer`, `⏸ Suspendre`, `⏹ Arrêter`, `🔲 Cadrer (Frame)`, `🎯 Accéder à l'origine`, `Enregistrer GCode`, `Exécuter GCode`.
  - Mode selector dropdown: `Démarrer à partir de : Coordonnées absolues / Origine de la sélection`.
  - Device selector dropdown: `Appareils (GRBL)`.
- **Tab 3: `Bibliothèque de matériaux`**: Material presets list with instant application.
