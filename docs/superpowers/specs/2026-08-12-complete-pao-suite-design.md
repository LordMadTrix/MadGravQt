# Spec Design: Complete PAO & CAD Vector Suite for MadGravQt

**Date:** 2026-08-12
**Status:** Approved

## Overview
This document specifies the complete PAO (Graphic Design & Vector Publishing) and CAD suite for MadGravQt. It integrates Constructive Solid Geometry boolean operations, vector path modifiers (offset/outline, break, combine, simplify), parametric shape generators (finger-joint boxes, spur gears, QR codes), advanced alignment/distribution, image vectorization (trace), and laser rotary assistant into the GUI toolbars and menus.

---

## 1. PAO Toolbar (`pao_tb`) & Menu Integration (`madgrav/qt/qt_main.py`)

### 1.1 PAO Toolbar Actions
Add a dedicated `pao_tb` toolbar with instant 1-click actions:
- **Boolean Operations**:
  - ➕ **Union (Weld/Combine)** (`_on_cag_union`)
  - ➖ **Difference (Subtract)** (`_on_cag_difference`)
  - ✖️ **Intersection** (`_on_cag_intersection`)
  - 🔲 **XOR (Exclude)** (`_on_cag_xor`)
- **Transformations & Mirrors**:
  - ↔️ **Mirror Horizontal** (`_on_mirror_h`)
  - ↕️ **Mirror Vertical** (`_on_mirror_v`)
  - 🔄 **Rotate 90° CW** (`_on_rotate_90_cw`)
  - 🔄 **Rotate 90° CCW** (`_on_rotate_90_ccw`)
- **Distribution & Uniform Size**:
  - ⫴ **Distribute Horizontal** (`_on_distribute_h`)
  - ⫵ **Distribute Vertical** (`_on_distribute_v`)
  - 📐 **Equalize Width** (`_on_match_width`)
  - 📐 **Equalize Height** (`_on_match_height`)
- **Path Modifiers & Generators**:
  - ⭕ **Vector Offset (Outline)** (`_on_open_offset_dialog`)
  - 📦 **Box Generator (Boîtes à encoches)** (`_on_open_box_generator`)
  - ⚙️ **Gear Generator (Engrenages CAO)** (`_on_open_gear_generator`)
  - 📷 **Vectorize Image (Trace Bitmap)** (`_on_open_vector_trace`)
  - 🌀 **Rotary Assistant (Axe Rotaire)** (`_on_open_rotary_assistant`)

---

## 2. Interactive PAO Dialogs (`madgrav/qt/qt_main.py` & `madgrav/tools/`)

### 2.1 Vector Offset / Outline Dialog
- Saisie de la distance d en mm (positif pour contour extérieur, négatif pour intérieur).
- Option de conservation de la forme originale.

### 2.2 Parametric Box & Gear Generators Integration
- Integration of `box_generator.py` and `gear_generator.py` dialogs into `qt_main.py` producing ready-to-cut vector nodes in the active document.

---

## 3. Verification Plan
- Unit tests verifying CAG boolean calls, alignment/distribution calculations, and generator outputs.
- Full 810 unit test suite execution.
