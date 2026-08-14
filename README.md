# ⚡ MadGravQt - Station de Contrôle Laser Haute Performance & Suite Maker

<div align="center">

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python: 3.10+](https://img.shields.io/badge/Python-3.10+-brightgreen.svg)](https://python.org)
[![Framework: PyQt6](https://img.shields.io/badge/GUI-PyQt6-blueviolet.svg)](https://riverbankcomputing.com/software/pyqt/)
[![Tests: 100% PASS](https://img.shields.io/badge/Tests-Passing-success.svg)](test/)
[![Platform: Win | macOS | Linux](https://img.shields.io/badge/Platform-Windows%20|%20macOS%20|%20Linux-lightgrey.svg)](.)

**Station de découpe et gravure laser open-source de nouvelle génération, multi-machines, avec vision IA, nesting 2D, générateurs paramétriques et télécommande mobile sans fil.**

[🌐 Site Web de Présentation](https://lordmadtrix.github.io/MadGravQt/) • [📖 Documentation](#-documentation--fonctionnalités) • [🚀 Démarrage Rapide](#-démarrage-rapide) • [🔌 Matériel Supporté](#-matériel-supporté)

</div>

---

## 🌟 Présentation

**MadGravQt** est une suite logicielle complète pour les créateurs, makers, fablabs et professionnels du laser. Conçue avec **PyQt6** et une architecture modulaire ultra-rapide, elle offre une expérience moderne et ergonomique pour piloter toutes vos machines laser.

---

## 🚀 Les 4 Piliers & Fonctionnalités Majeures

### 🧩 1. Suite Outils Maker & Incrustation
* **Assistant Marqueterie & Incrustation (*Inlay Wizard*)** : Calcul automatique des décalages de kerf pour pièces mâles et femelles avec compensation du jeu mécanique pour le bois, PMMA ou cuir.
* **Boîtes Démontables à Écrous Captifs (*T-Slot Box*)** : Générateur paramétrique de boîtes 3D avec fentes en T pour vis et écrous normalisés M3, M4 et M5.
* **Charnières Vivantes (*Living Hinges*)** : Motifs de découpe flexibles pour cintrer du bois ou de l'acrylique sans casser.
* **Cartes Topographiques 3D** : Génération de strates vectorielles empilables avec lignes de niveau.
* **Générateur de Mandalas & Rosaces** : Motifs géométriques radiaux paramétriques.
* **Studio Gravure Photo & Demi-Teintes** : Algorithmes de tramage avancés (Floyd-Steinberg, Atkinson, Halftone).

### 👁️ 2. Vision & Calage Intelligent
* **Détecteur de Chutes (*Scrap Finder*)** : Analyse automatique de caméra pour détecter les retailles de matière vierge et y caler des découpes.
* **Repères Fiduciels (*Print & Cut*)** : Calage 2 points et 4 points avec correction de translation, rotation, échelle et déformation perspective pour découper des imprimés.
* **Superposition Caméra en Direct (*Live Bed Overlay*)** : Projection temps réel de l'image de la caméra calibrée (ArUco / Chessboard) sur le canvas.
* **Assistant Multi-Têtes & Galvo** : Calibration géométrique précise pour machines double faisceau et lasers galvo à miroirs.

### ⚡ 3. Optimisation Pro & Matériaux
* **Imbrication 2D Avancée (*True-Shape Nesting*)** : Algorithme de placement multi-pièces avec rotations (0°, 90°, 45°, 15°) pour économiser un maximum de matière.
* **Matrice de Test Matériaux Pro** : Grille paramétrique automatique Vitesse vs Puissance avec valeurs gravées.
* **Optimiseur d'Ordre de Découpe (*Inner-First*)** : Découpe des trous intérieurs avant les contours extérieurs pour éviter les décrochements de pièces.
* **Texte Variable & Fusion CSV/Excel** : Sérialisation et création automatisée de badges, plaques et trophées avec numéros d'incrément et tableurs.

### 📱 4. Workflow Atelier & Télécommande
* **Télécommande Mobile Web (QR Code)** : Flashez le QR Code pour piloter la machine depuis n'importe quel smartphone iOS/Android sans installer d'application.
* **Visualiseur Temporel & Accélération Machine** : Calcul réaliste du temps de découpe via profil d'accélération trapézoïdal.
* **Mode Kiosque Tactile Atelier (F11)** : Interface plein écran à boutons extra-larges pensée pour écrans tactiles et sécurité d'atelier.
* **File d'Attente Multi-Machines (*Spooler*)** : Dispatching de jobs de production sur un parc de plusieurs lasers simultanément.

---

## 🔌 Matériel Supporté

| Contrôleur / Machine | Type de Liaison | Fonctionnalités Clés |
| :--- | :--- | :--- |
| **K40 (Lihuiyu)** | USB (CH341 / LibUSB) | M2-Nano, M3, B1, accélération matérielle raster |
| **GRBL & G-Code** | Série USB / Bluetooth | GRBL 1.1f/h, Smoothieware, Marlin, ESP32 Laser |
| **Ruida DSP** | Réseau UDP / USB | RDC6442G/S, RDC6445, téléchargement de fichiers RD |
| **Galvo Balor** | USB Fibre / CO2 | Balor MK1, balayage galvo miroir ultra-rapide |
| **Moshiboard / Newly** | USB Direct | Contrôleurs MoshiDraw & NewlyDraw |

---

## 📦 Démarrage Rapide

### Prérequis
* Python 3.10 ou supérieur
* Git

### Installation

```bash
# 1. Cloner le dépôt
git clone https://github.com/LordMadTrix/MadGravQt.git
cd MadGravQt

# 2. Créer un environnement virtuel
python -m venv .venv
source .venv/bin/activate  # Sur Linux/macOS
# ou
.venv\Scripts\activate     # Sur Windows

# 3. Installer les dépendances
pip install -e .

# 4. Lancer l'application Qt
python run_qt.py
```

---

## ⌨️ Raccourcis Clavier Utiles

* **F11** : Mode Plein Écran Kiosque Atelier
* **F9** : Activer / Désactiver la Superposition Caméra
* **Ctrl+N** : Nouveau Projet / Nouvel Onglet Document
* **Ctrl+O** : Ouvrir un fichier (SVG, DXF, PNG, JPG, BMP)
* **Ctrl+S** : Enregistrer le projet
* **Espace + Glisser** : Déplacement panoramique de la vue

---

## 🧪 Tests & Qualité

Pour exécuter la suite complète de tests unitaires :

```bash
python -m unittest discover test -v
```

---

## 📄 Licence

Ce projet est distribué sous la licence **MIT**. Voir le fichier [LICENSE](LICENSE) pour plus de détails.
