# Design Spec - Regroupement des Boutons d'Édition à Gauche & Suppression des Doublons

**Date:** 2026-08-13
**Projet:** MadGravQt UI (PyQt6 Workstation)

## Objectif
Regrouper l'intégralité des outils d'édition et d'alignement vectoriel dans une barre d'outils consolidée sur le **côté gauche** (`LeftToolBarArea`) et supprimer les doublons inutiles de générateurs.

---

## 1. Suppression des Doublons
Retirer les boutons suivants de la barre d'outils vectorielle afin d'éviter la redondance avec le panneau latéral gauche et le menu principal :
- `btn_box` ("📦 Boîtes à encoches")
- `btn_gear` ("⚙️ Engrenages CAO")
- `btn_qr` ("📱 QR Code")
- `btn_hinges` ("🪵 Charnières")

*Raison:* Ces outils de génération possèdent déjà leur section dédiée dans le Dock Gauche ("📦 Générateurs 3D & CAD") et le Menu Supérieur.

---

## 2. Consolidation de la Barre d'Édition Vectorielle sur le Côté Gauche
Fusionner la barre d'alignement rapide (`align_tb`) et la barre d'outils PAO (`pao_tb`) en une barre d'outils unifiée **"Édition & Alignement Vectoriel"** positionnée sur `Qt.ToolBarArea.LeftToolBarArea`.

### Composition de la Barre d'Édition Gauche :
1. **Alignement** :
   - ⬅ Gauche (`_on_align_left`)
   - ↔ Centre H (`_on_align_center_h`)
   - ➡️ Droite (`_on_align_right`)
   - ⬆ Haut (`_on_align_top`)
   - ↕ Centre V (`_on_align_center_v`)
   - ⬇ Bas (`_on_align_bottom`)
   - 🎯 Centrer Table (`_on_center_to_bed`)
2. **Opérations Booléennes (CAG)** :
   - ➕ Unir (`union`)
   - ➖ Soustraire (`difference`)
   - ✖️ Intersecter (`intersection`)
   - 🔲 Exclure (`xor`)
3. **Transformations** :
   - ↔️ Miroir H (`_on_mirror_h`)
   - ↕️ Miroir V (`_on_mirror_v`)
   - 🔄 Pivot 90° (`_on_rotate_90_cw`)
4. **Distribution & Taille** :
   - ⫴ Répartir H (`_on_distribute_h`)
   - ⫵ Répartir V (`_on_distribute_v`)
   - 📐 Égaliser L (`_on_match_width`)
   - 📐 Égaliser H (`_on_match_height`)
5. **Modificateurs de Tracé** :
   - ⭕ Contour (Offset) (`_on_open_offset_dialog`)
   - 🏁 Hachurage (`_on_add_hatch_effect`)

---

## 3. Plan d'Exécution
- Modifier `_create_toolbar` et `_create_pao_toolbar` dans [`madgrav/qt/qt_main.py`](file:///d:/MadGravQt/madgrav/qt/qt_main.py) pour placer la barre unifiée sur `Qt.ToolBarArea.LeftToolBarArea`.
- Exécuter la suite complète de tests unitaire pour vérifier la non-régression.
