# Spécification de Conception : Suite Complète Maker, Vision, Nesting & Workflow Atelier pour MadGravQt

**Date :** 2026-08-14  
**Statut :** Proposé  
**Auteur :** Antigravity & Utilisateur  

---

## 1. Objectif Global

Enrichir MadGravQt d'une suite unifiée de modules avancés couvrant 4 piliers essentiels pour les créateurs, makers et ateliers professionnels de découpe et gravure laser :

1. **Maker & Incrustation (Inlay & Marqueterie, Boîtes à écrous captifs en T)**
2. **Vision & Calage Intelligent (Scrap Finder / Détection de chutes, Print & Cut / Repères fiduciels)**
3. **Optimisation & Matériaux Pro (Nesting 2D True-Shape, Générateur de matrice de test vitesse/puissance)**
4. **Workflow & Atelier (Visualiseur d'accélération & timeline d'exécution, Mode Kiosque tactile)**

---

## 2. Architecture & Nouveaux Composants

### 2.1. Module 1 : Suite Maker & Incrustation
* **`InlayWizardDialog` (`madgrav/qt/qt_laser_dialogs.py`)** :
  * Calcul automatique du décalage de kerf pour la pièce mâle (découpe extérieure décalée de $-k/2$) et la cavité femelle (poche intérieure décalée de $+k/2$).
  * Gestion du jeu mécanique (*clearance*) pour l'insertion (ajustement serré, glissant ou pour colle).
  * Génération directe des tracés vectoriels dans l'arborescence des éléments.
* **`TSlotBoxDialog` (`madgrav/qt/qt_laser_dialogs.py`)** :
  * Générateur paramétrique de boîtes démontables avec fentes en T pour écrous captifs (normes M3, M4, M5).
  * Calcul automatique des encoches pour la tête de vis et de la poche rectangulaire pour l'écrou hexagonal ou carré.
  * Sortie des 6 faces agencées à plat avec repères de montage.

### 2.2. Module 2 : Suite Vision & Alignement Intelligent
* **`ScrapFinderDialog` (`madgrav/qt/qt_laser_dialogs.py`)** :
  * Capture ou importation d'une photo du plateau avec matière résiduelle (chutes).
  * Segmentation d'image (seuillage adaptatif, extraction de contours polygonaux).
  * Détection des polygones convexes et rectangles maximaux exploitables.
  * Création automatique de zones guides ou de masques d'exclusion sur le canvas.
* **`PrintAndCutDialog` (`madgrav/qt/qt_laser_dialogs.py`)** :
  * Module d'alignement pour impression préalable (Print & Cut).
  * Support du calage 2 points (translation, rotation, mise à l'échelle uniforme) et 4 points (déformation affine/perspective).
  * Interface de pointage interactif entre les mires du fichier de conception et les positions laser réelles.

### 2.3. Module 3 : Suite Optimisation & Matériaux Pro
* **`TrueShapeNestingDialog` (`madgrav/qt/qt_laser_dialogs.py`)** :
  * Algorithme d'imbrication 2D multi-formes avec gestion des angles de rotation (0°, 90°, 45°, 15°).
  * Respect des marges matière et des distances de sécurité inter-pièces.
  * Calcul en temps réel du taux d'occupation (surface utile / surface brute) et prévisualisation instantanée.
* **`MaterialMatrixTestDialog` (`madgrav/qt/qt_laser_dialogs.py`)** :
  * Générateur de grille de test paramétrique (X: vitesses, Y: puissances, passes multiples, fréquences).
  * Création automatique des carrés de test avec étiquettes textuelles gravées pour lecture directe du résultat.

### 2.4. Module 4 : Suite Workflow & Ergonomie Atelier
* **`LaserTimelineDialog` (`madgrav/qt/qt_laser_dialogs.py`)** :
  * Calculateur de profil d'accélération trapézoïdale ($a_{max}$, $v_{max}$, temps de plongée et décélération).
  * Graphique interactif de la vitesse et de la puissance le long du parcours G-Code / CutCode.
  * Décomposition du temps total : mouvements rapides (G0), découpe (G1), gravure raster et sauts de couche.
* **`WorkshopKioskWindow` (`madgrav/qt/qt_laser_dialogs.py`)** :
  * Fenêtre dédiée pour écran tactile d'atelier (résolution adaptative, boutons extra-larges).
  * Contrôles principaux : Charger fichier, Cadrage (Frame), Départ (Start), Pause, Arrêt d'urgence (E-Stop), Origine / Home, Tir Laser test (Pulse).
  * Affichage géant du temps restant et du statut machine.

---

## 3. Intégration dans l'Interface Principale (`qt_main.py`)

* Ajout des entrées de menu et boutons dans la barre d'outils / ruban :
  * **Menu Outils / Générateurs :**
    * *Assistant Marqueterie & Incrustation...*
    * *Boîte à écrous captifs (T-Slot)...*
    * *Matrice de test Matériaux Pro...*
  * **Menu Optimisation & Vision :**
    * *Détecteur de Chutes (Scrap Finder)...*
    * *Calage Repères d'Impression (Print & Cut)...*
    * *Imbrication 2D Avancée (True-Shape Nesting)...*
  * **Menu Atelier & Machine :**
    * *Visualiseur Temporel & Accélération...*
    * *Mode Kiosque Atelier Tactile (F11)...*

---

## 4. Stratégie de Test et Validation

1. **Tests unitaires exhaustifs (`test/test_qt_mega_suite.py`)** :
   * Test de calcul géométrique des découpes mâle/femelle et compensation de kerf pour `InlayWizardDialog`.
   * Test de génération des panneaux et découpes en T pour `TSlotBoxDialog`.
   * Test de calcul matriciel 2D/affine pour `PrintAndCutDialog`.
   * Test d'extraction de contours et surfaces exploitables pour `ScrapFinderDialog`.
   * Test de l'algorithme d'agencement et de taux de remplissage pour `TrueShapeNestingDialog`.
   * Test de génération de grille et de labels pour `MaterialMatrixTestDialog`.
   * Test de calcul du profil trapézoïdal et de durée pour `LaserTimelineDialog`.
   * Test d'instanciation et d'actions opérateur pour `WorkshopKioskWindow`.
2. **Validation graphique** :
   * Vérification du respect de la charte graphique sombre élégante (`qt_theme.py`).
   * Vérification de l'absence de régression sur les tests unitaires existants.
