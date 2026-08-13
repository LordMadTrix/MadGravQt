"""
Interactive Laser Tool Dialogs for MadGrav Qt Workstation.

Provides modern, user-friendly QDialog parameter configuration forms for:
- 3D Finger-Jointed Box Generator
- Involute Spur Gear CAD Generator
- Jigsaw Puzzle Generator
- Material Test Grid Matrix Generator
- 2D Grid Array Duplication
- Polar Circular Array Duplication
- Micro-Tabs & Bridges Insertion
- Kerf & Lead-In/Lead-Out Compensation
- Rubber Stamp Mode 45° Shoulder Tool
- Auto Slot & Notch Fitter
- Rotary Attachment Setup Assistant
- Laser Material Settings Preset Library
"""

from PyQt6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDoubleSpinBox,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
)


class BoxGeneratorDialog(QDialog):
    """Configuration dialog for 3D Finger-Jointed Box Generator."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("📦 Générateur de Boîte 3D à Encoches")
        self.setMinimumWidth(420)

        layout = QVBoxLayout(self)

        lbl_desc = QLabel(
            "Configurez les dimensions extérieures et l'épaisseur du matériau.\n"
            "Le générateur dépliera automatiquement les 6 panneaux 2D à découper au laser."
        )
        lbl_desc.setWordWrap(True)
        lbl_desc.setStyleSheet("color: #8E8E93; margin-bottom: 8px;")
        layout.addWidget(lbl_desc)

        form = QFormLayout()

        self.spin_width = QDoubleSpinBox(self)
        self.spin_width.setRange(10.0, 2000.0)
        self.spin_width.setValue(100.0)
        self.spin_width.setSuffix(" mm")
        self.spin_width.setToolTip("Largeur totale extérieure de la boîte (Axe X) en millimètres")
        form.addRow("Largeur (X) :", self.spin_width)

        self.spin_depth = QDoubleSpinBox(self)
        self.spin_depth.setRange(10.0, 2000.0)
        self.spin_depth.setValue(80.0)
        self.spin_depth.setSuffix(" mm")
        self.spin_depth.setToolTip("Profondeur totale extérieure de la boîte (Axe Y) en millimètres")
        form.addRow("Profondeur (Y) :", self.spin_depth)

        self.spin_height = QDoubleSpinBox(self)
        self.spin_height.setRange(10.0, 2000.0)
        self.spin_height.setValue(60.0)
        self.spin_height.setSuffix(" mm")
        self.spin_height.setToolTip("Hauteur totale extérieure de la boîte (Axe Z) en millimètres")
        form.addRow("Hauteur (Z) :", self.spin_height)

        self.spin_thickness = QDoubleSpinBox(self)
        self.spin_thickness.setRange(0.5, 50.0)
        self.spin_thickness.setValue(3.0)
        self.spin_thickness.setSuffix(" mm")
        self.spin_thickness.setToolTip("Épaisseur exacte de votre planche de contreplaqué, acrylique ou MDF")
        form.addRow("Épaisseur Matériau :", self.spin_thickness)

        self.spin_tab_width = QDoubleSpinBox(self)
        self.spin_tab_width.setRange(2.0, 100.0)
        self.spin_tab_width.setValue(12.0)
        self.spin_tab_width.setSuffix(" mm")
        self.spin_tab_width.setToolTip("Largeur cible des créneaux / encoches d'assemblage")
        form.addRow("Taille des Encoches :", self.spin_tab_width)

        self.spin_kerf = QDoubleSpinBox(self)
        self.spin_kerf.setRange(0.0, 2.0)
        self.spin_kerf.setSingleStep(0.05)
        self.spin_kerf.setValue(0.1)
        self.spin_kerf.setSuffix(" mm")
        self.spin_kerf.setToolTip("Jeu du faisceau laser pour un emboîtement serré sans colle (kerf)")
        form.addRow("Kerf (Jeu Laser) :", self.spin_kerf)

        self.chk_open_top = QCheckBox("Boîte ouverte sans couvercle", self)
        self.chk_open_top.setToolTip("Cochez cette option si vous souhaitez une boîte de rangement sans couvercle supérieur")
        form.addRow("", self.chk_open_top)

        layout.addLayout(form)

        btn_box = QHBoxLayout()
        btn_cancel = QPushButton("Annuler", self)
        btn_cancel.setToolTip("Annuler et fermer sans rien générer")
        btn_cancel.clicked.connect(self.reject)
        btn_generate = QPushButton("📦 Générer les Panneaux", self)
        btn_generate.setToolTip("Générer les 6 patrons 2D dépliés sur le plan de travail")
        btn_generate.setStyleSheet("font-weight: bold; background-color: #0A84FF; color: white;")
        btn_generate.clicked.connect(self.accept)
        btn_box.addWidget(btn_cancel)
        btn_box.addWidget(btn_generate)

        layout.addLayout(btn_box)


class GearGeneratorDialog(QDialog):
    """Configuration dialog for Involute Gear Generator."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("⚙️ Générateur d'Engrenage Droit à Évolvente")
        self.setMinimumWidth(380)

        layout = QVBoxLayout(self)

        lbl_desc = QLabel("Crée un engrenage droit avec profil d'évolvente précis et alésage central pour axe motorisé.")
        lbl_desc.setWordWrap(True)
        lbl_desc.setStyleSheet("color: #8E8E93; margin-bottom: 8px;")
        layout.addWidget(lbl_desc)

        form = QFormLayout()

        self.spin_teeth = QSpinBox(self)
        self.spin_teeth.setRange(6, 200)
        self.spin_teeth.setValue(20)
        self.spin_teeth.setToolTip("Nombre total de dents autour de la circonférence")
        form.addRow("Nombre de Dents :", self.spin_teeth)

        self.spin_module = QDoubleSpinBox(self)
        self.spin_module.setRange(0.5, 20.0)
        self.spin_module.setValue(2.0)
        self.spin_module.setSuffix(" mm")
        self.spin_module.setToolTip("Module normalisé définissant la taille des dents et l'entraxe")
        form.addRow("Module (Taille dent) :", self.spin_module)

        self.spin_bore = QDoubleSpinBox(self)
        self.spin_bore.setRange(0.0, 100.0)
        self.spin_bore.setValue(8.0)
        self.spin_bore.setSuffix(" mm")
        self.spin_bore.setToolTip("Diamètre du trou central pour fixer l'axe ou le roulement")
        form.addRow("Trou central (Axe) :", self.spin_bore)

        layout.addLayout(form)

        btn_box = QHBoxLayout()
        btn_cancel = QPushButton("Annuler", self)
        btn_cancel.setToolTip("Annuler la création d'engrenage")
        btn_cancel.clicked.connect(self.reject)
        btn_gen = QPushButton("⚙️ Générer l'Engrenage", self)
        btn_gen.setToolTip("Placer le contour vectoriel de l'engrenage sur le canvas")
        btn_gen.setStyleSheet("font-weight: bold; background-color: #30D158; color: white;")
        btn_gen.clicked.connect(self.accept)
        btn_box.addWidget(btn_cancel)
        btn_box.addWidget(btn_gen)
        layout.addLayout(btn_box)


class JigsawGeneratorDialog(QDialog):
    """Configuration dialog for Vector Jigsaw Puzzle Generator."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("🧩 Générateur de Puzzle Vectoriel")
        self.setMinimumWidth(380)

        layout = QVBoxLayout(self)

        lbl_desc = QLabel("Génère les lignes de coupe ondulées d'un puzzle emboîtable à découper au laser.")
        lbl_desc.setWordWrap(True)
        lbl_desc.setStyleSheet("color: #8E8E93; margin-bottom: 8px;")
        layout.addWidget(lbl_desc)

        form = QFormLayout()

        self.spin_width = QDoubleSpinBox(self)
        self.spin_width.setRange(20.0, 2000.0)
        self.spin_width.setValue(160.0)
        self.spin_width.setSuffix(" mm")
        self.spin_width.setToolTip("Largeur totale de la plaque du puzzle")
        form.addRow("Largeur Totale :", self.spin_width)

        self.spin_height = QDoubleSpinBox(self)
        self.spin_height.setRange(20.0, 2000.0)
        self.spin_height.setValue(120.0)
        self.spin_height.setSuffix(" mm")
        self.spin_height.setToolTip("Hauteur totale de la plaque du puzzle")
        form.addRow("Hauteur Totale :", self.spin_height)

        self.spin_rows = QSpinBox(self)
        self.spin_rows.setRange(1, 50)
        self.spin_rows.setValue(3)
        self.spin_rows.setToolTip("Nombre de pièces verticales")
        form.addRow("Nombre de Lignes :", self.spin_rows)

        self.spin_cols = QSpinBox(self)
        self.spin_cols.setRange(1, 50)
        self.spin_cols.setValue(4)
        self.spin_cols.setToolTip("Nombre de pièces horizontales")
        form.addRow("Nombre de Colonnes :", self.spin_cols)

        layout.addLayout(form)

        btn_box = QHBoxLayout()
        btn_cancel = QPushButton("Annuler", self)
        btn_cancel.setToolTip("Annuler la création de puzzle")
        btn_cancel.clicked.connect(self.reject)
        btn_gen = QPushButton("🧩 Générer le Puzzle", self)
        btn_gen.setToolTip("Créer la grille vectorielle complète du puzzle")
        btn_gen.setStyleSheet("font-weight: bold; background-color: #FF9F0A; color: white;")
        btn_gen.clicked.connect(self.accept)
        btn_box.addWidget(btn_cancel)
        btn_box.addWidget(btn_gen)
        layout.addLayout(btn_box)


class MaterialTestDialog(QDialog):
    """Configuration dialog for Material Test Grid Generator."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("📊 Générateur de Test Matériau Laser")
        self.setMinimumWidth(400)

        layout = QVBoxLayout(self)

        lbl_desc = QLabel("Crée une grille de gravure/découpe pour déterminer la meilleure vitesse et puissance pour votre matériau.")
        lbl_desc.setWordWrap(True)
        lbl_desc.setStyleSheet("color: #8E8E93; margin-bottom: 8px;")
        layout.addWidget(lbl_desc)

        form = QFormLayout()

        self.spin_rows = QSpinBox(self)
        self.spin_rows.setRange(2, 10)
        self.spin_rows.setValue(3)
        self.spin_rows.setToolTip("Nombre de paliers de puissance (Axe vertical Y)")
        form.addRow("Lignes (Puissance) :", self.spin_rows)

        self.spin_cols = QSpinBox(self)
        self.spin_cols.setRange(2, 10)
        self.spin_cols.setValue(3)
        self.spin_cols.setToolTip("Nombre de paliers de vitesse (Axe horizontal X)")
        form.addRow("Colonnes (Vitesse) :", self.spin_cols)

        self.spin_min_speed = QDoubleSpinBox(self)
        self.spin_min_speed.setRange(1.0, 500.0)
        self.spin_min_speed.setValue(10.0)
        self.spin_min_speed.setSuffix(" mm/s")
        self.spin_min_speed.setToolTip("Vitesse la plus lente à tester")
        form.addRow("Vitesse Min :", self.spin_min_speed)

        self.spin_max_speed = QDoubleSpinBox(self)
        self.spin_max_speed.setRange(1.0, 2000.0)
        self.spin_max_speed.setValue(50.0)
        self.spin_max_speed.setSuffix(" mm/s")
        self.spin_max_speed.setToolTip("Vitesse la plus rapide à tester")
        form.addRow("Vitesse Max :", self.spin_max_speed)

        self.spin_min_power = QDoubleSpinBox(self)
        self.spin_min_power.setRange(5.0, 100.0)
        self.spin_min_power.setValue(20.0)
        self.spin_min_power.setSuffix(" %")
        self.spin_min_power.setToolTip("Puissance minimale de la matrice")
        form.addRow("Puissance Min :", self.spin_min_power)

        self.spin_max_power = QDoubleSpinBox(self)
        self.spin_max_power.setRange(5.0, 100.0)
        self.spin_max_power.setValue(80.0)
        self.spin_max_power.setSuffix(" %")
        self.spin_max_power.setToolTip("Puissance maximale de la matrice")
        form.addRow("Puissance Max :", self.spin_max_power)

        layout.addLayout(form)

        btn_box = QHBoxLayout()
        btn_cancel = QPushButton("Annuler", self)
        btn_cancel.setToolTip("Annuler la génération de matrice")
        btn_cancel.clicked.connect(self.reject)
        btn_gen = QPushButton("📊 Générer la Matrice Test", self)
        btn_gen.setToolTip("Créer la matrice de test avec étiquettes de vitesse et puissance")
        btn_gen.setStyleSheet("font-weight: bold; background-color: #BF5AF2; color: white;")
        btn_gen.clicked.connect(self.accept)
        btn_box.addWidget(btn_cancel)
        btn_box.addWidget(btn_gen)
        layout.addLayout(btn_box)


class GridArrayDialog(QDialog):
    """Configuration dialog for 2D Grid Array Duplication."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("🔲 Duplication en Grille 2D")
        self.setMinimumWidth(360)

        layout = QVBoxLayout(self)

        form = QFormLayout()

        self.spin_rows = QSpinBox(self)
        self.spin_rows.setRange(1, 100)
        self.spin_rows.setValue(3)
        self.spin_rows.setToolTip("Nombre de lignes de répétition")
        form.addRow("Nombre de Lignes :", self.spin_rows)

        self.spin_cols = QSpinBox(self)
        self.spin_cols.setRange(1, 100)
        self.spin_cols.setValue(3)
        self.spin_cols.setToolTip("Nombre de colonnes de répétition")
        form.addRow("Nombre de Colonnes :", self.spin_cols)

        self.spin_dist_x = QDoubleSpinBox(self)
        self.spin_dist_x.setRange(0.0, 1000.0)
        self.spin_dist_x.setValue(10.0)
        self.spin_dist_x.setSuffix(" mm")
        self.spin_dist_x.setToolTip("Espace horizontal entre chaque copie")
        form.addRow("Espacement X :", self.spin_dist_x)

        self.spin_dist_y = QDoubleSpinBox(self)
        self.spin_dist_y.setRange(0.0, 1000.0)
        self.spin_dist_y.setValue(10.0)
        self.spin_dist_y.setSuffix(" mm")
        self.spin_dist_y.setToolTip("Espace vertical entre chaque copie")
        form.addRow("Espacement Y :", self.spin_dist_y)

        layout.addLayout(form)

        btn_box = QHBoxLayout()
        btn_cancel = QPushButton("Annuler", self)
        btn_cancel.setToolTip("Annuler la duplication en grille")
        btn_cancel.clicked.connect(self.reject)
        btn_gen = QPushButton("🔲 Créer le Réseau", self)
        btn_gen.setToolTip("Dupliquer l'élément sélectionné selon la grille")
        btn_gen.setStyleSheet("font-weight: bold; background-color: #0A84FF; color: white;")
        btn_gen.clicked.connect(self.accept)
        btn_box.addWidget(btn_cancel)
        btn_box.addWidget(btn_gen)
        layout.addLayout(btn_box)


class CircularArrayDialog(QDialog):
    """Configuration dialog for Polar Circular Array Duplication."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("⭕ Duplication en Réseau Circulaire")
        self.setMinimumWidth(360)

        layout = QVBoxLayout(self)

        form = QFormLayout()

        self.spin_count = QSpinBox(self)
        self.spin_count.setRange(2, 360)
        self.spin_count.setValue(8)
        self.spin_count.setToolTip("Nombre total de répétitions réparties sur 360°")
        form.addRow("Nombre de copies :", self.spin_count)

        layout.addLayout(form)

        btn_box = QHBoxLayout()
        btn_cancel = QPushButton("Annuler", self)
        btn_cancel.setToolTip("Annuler la duplication circulaire")
        btn_cancel.clicked.connect(self.reject)
        btn_gen = QPushButton("⭕ Dupliquer", self)
        btn_gen.setToolTip("Dupliquer l'élément en couronne polaire")
        btn_gen.setStyleSheet("font-weight: bold; background-color: #30D158; color: white;")
        btn_gen.clicked.connect(self.accept)
        btn_box.addWidget(btn_cancel)
        btn_box.addWidget(btn_gen)
        layout.addLayout(btn_box)


class SlotFitterDialog(QDialog):
    """Configuration dialog for Slot & Notch Auto-Fitter."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("🔧 Ajusteur d'Épaisseur d'Encoches")
        self.setMinimumWidth(380)

        layout = QVBoxLayout(self)

        lbl = QLabel("Ajuste automatiquement toutes les fentes et encoches du dessin d'une ancienne épaisseur de matériau vers une nouvelle épaisseur.")
        lbl.setWordWrap(True)
        lbl.setStyleSheet("color: #8E8E93; margin-bottom: 6px;")
        layout.addWidget(lbl)

        form = QFormLayout()

        self.spin_old_thickness = QDoubleSpinBox(self)
        self.spin_old_thickness.setRange(0.5, 50.0)
        self.spin_old_thickness.setValue(3.0)
        self.spin_old_thickness.setSuffix(" mm")
        self.spin_old_thickness.setToolTip("Épaisseur actuelle des fentes dans le fichier vectoriel à modifier")
        form.addRow("Ancienne Épaisseur :", self.spin_old_thickness)

        self.spin_new_thickness = QDoubleSpinBox(self)
        self.spin_new_thickness.setRange(0.5, 50.0)
        self.spin_new_thickness.setValue(5.0)
        self.spin_new_thickness.setSuffix(" mm")
        self.spin_new_thickness.setToolTip("Nouvelle épaisseur de votre planche réelle à adapter")
        form.addRow("Nouvelle Épaisseur :", self.spin_new_thickness)

        layout.addLayout(form)

        btn_box = QHBoxLayout()
        btn_cancel = QPushButton("Annuler", self)
        btn_cancel.setToolTip("Annuler la réadaptation d'encoches")
        btn_cancel.clicked.connect(self.reject)
        btn_gen = QPushButton("🔧 Adapter les Encoches", self)
        btn_gen.setToolTip("Redimensionner automatiquement les encoches de la sélection")
        btn_gen.setStyleSheet("font-weight: bold; background-color: #FF9F0A; color: white;")
        btn_gen.clicked.connect(self.accept)
        btn_box.addWidget(btn_cancel)
        btn_box.addWidget(btn_gen)
        layout.addLayout(btn_box)


class MaterialLibraryDialog(QDialog):
    """Configuration dialog for Laser Material Preset Library."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("📚 Bibliothèque de Matériaux Laser")
        self.setMinimumWidth(420)

        layout = QVBoxLayout(self)

        form = QFormLayout()

        self.combo_material = QComboBox(self)
        self.combo_material.addItems([
            "Wood",
            "Plywood 5mm",
            "Acrylic",
            "MDF 4mm",
            "Leather",
        ])
        self.combo_material.setToolTip("Sélectionnez le matériau dans la base de préréglages laser")
        form.addRow("Matériau Préréglé :", self.combo_material)

        self.combo_mode = QComboBox(self)
        self.combo_mode.addItems(["cut", "line", "raster"])
        self.combo_mode.setToolTip("Mode de travail : découpe (cut), marquage (line) ou gravure d'image (raster)")
        form.addRow("Mode d'opération :", self.combo_mode)

        layout.addLayout(form)

        lbl_info = QLabel("Les vitesses, puissances et nombre de passes seront appliqués automatiquement à l'arbre des opérations.")
        lbl_info.setWordWrap(True)
        lbl_info.setStyleSheet("color: #8E8E93; margin-top: 6px;")
        layout.addWidget(lbl_info)

        btn_box = QHBoxLayout()
        btn_cancel = QPushButton("Annuler", self)
        btn_cancel.setToolTip("Fermer sans appliquer")
        btn_cancel.clicked.connect(self.reject)
        btn_apply = QPushButton("📚 Appliquer au Projet", self)
        btn_apply.setToolTip("Charger les paramètres de puissance et vitesse dans les opérations")
        btn_apply.setStyleSheet("font-weight: bold; background-color: #0A84FF; color: white;")
        btn_apply.clicked.connect(self.accept)
        btn_box.addWidget(btn_cancel)
        btn_box.addWidget(btn_apply)
        layout.addLayout(btn_box)
