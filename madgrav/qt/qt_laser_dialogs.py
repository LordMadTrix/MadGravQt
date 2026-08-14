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

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QImage, QPixmap, qRgb
from PyQt6.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QDialog,
    QDoubleSpinBox,
    QFormLayout,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QListWidget,
    QMainWindow,
    QProgressBar,
    QPushButton,
    QRadioButton,
    QSlider,
    QSpinBox,
    QTableWidget,
    QTableWidgetItem,
    QTextEdit,
    QVBoxLayout,
)

from madgrav.qt.qt_theme import (
    COLOR_ACCENT,
    COLOR_MUTED,
    COLOR_PURPLE,
    COLOR_SUCCESS,
    COLOR_WARNING,
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
        lbl_desc.setStyleSheet(f"color: {COLOR_MUTED}; margin-bottom: 8px;")
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
        btn_generate.setStyleSheet(f"font-weight: bold; background-color: {COLOR_ACCENT}; color: white;")
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
        lbl_desc.setStyleSheet(f"color: {COLOR_MUTED}; margin-bottom: 8px;")
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
        btn_gen.setStyleSheet(f"font-weight: bold; background-color: {COLOR_SUCCESS}; color: white;")
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
        lbl_desc.setStyleSheet(f"color: {COLOR_MUTED}; margin-bottom: 8px;")
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
        btn_gen.setStyleSheet(f"font-weight: bold; background-color: {COLOR_WARNING}; color: white;")
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
        lbl_desc.setStyleSheet(f"color: {COLOR_MUTED}; margin-bottom: 8px;")
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
        btn_gen.setStyleSheet(f"font-weight: bold; background-color: {COLOR_PURPLE}; color: white;")
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
        btn_gen.setStyleSheet(f"font-weight: bold; background-color: {COLOR_ACCENT}; color: white;")
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
        btn_gen.setStyleSheet(f"font-weight: bold; background-color: {COLOR_SUCCESS}; color: white;")
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
        lbl.setStyleSheet(f"color: {COLOR_MUTED}; margin-bottom: 6px;")
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
        btn_gen.setStyleSheet(f"font-weight: bold; background-color: {COLOR_WARNING}; color: white;")
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
        lbl_info.setStyleSheet(f"color: {COLOR_MUTED}; margin-top: 6px;")
        layout.addWidget(lbl_info)

        btn_box = QHBoxLayout()
        btn_cancel = QPushButton("Annuler", self)
        btn_cancel.setToolTip("Fermer sans appliquer")
        btn_cancel.clicked.connect(self.reject)
        btn_apply = QPushButton("📚 Appliquer au Projet", self)
        btn_apply.setToolTip("Charger les paramètres de puissance et vitesse dans les opérations")
        btn_apply.setStyleSheet(f"font-weight: bold; background-color: {COLOR_ACCENT}; color: white;")
        btn_apply.clicked.connect(self.accept)
        btn_box.addWidget(btn_cancel)
        btn_box.addWidget(btn_apply)
        layout.addLayout(btn_box)


class LivingHingesDialog(QDialog):
    """Configuration dialog for Living Hinge & Flex Cut Pattern Generator."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("🪵 Générateur de Charnières Vivantes (Flex Cut)")
        self.setMinimumWidth(400)

        layout = QVBoxLayout(self)

        lbl_desc = QLabel("Crée un motif d'incisions paramétriques pour plier le bois, MDF ou acrylique.")
        lbl_desc.setWordWrap(True)
        lbl_desc.setStyleSheet(f"color: {COLOR_MUTED}; margin-bottom: 8px;")
        layout.addWidget(lbl_desc)

        form = QFormLayout()

        self.spin_width = QDoubleSpinBox(self)
        self.spin_width.setRange(10.0, 2000.0)
        self.spin_width.setValue(100.0)
        self.spin_width.setSuffix(" mm")
        self.spin_width.setToolTip("Largeur de la zone de charnière (Axe X)")
        form.addRow("Largeur Hinge (X) :", self.spin_width)

        self.spin_height = QDoubleSpinBox(self)
        self.spin_height.setRange(10.0, 2000.0)
        self.spin_height.setValue(60.0)
        self.spin_height.setSuffix(" mm")
        self.spin_height.setToolTip("Hauteur de la zone de charnière (Axe Y)")
        form.addRow("Hauteur Hinge (Y) :", self.spin_height)

        self.combo_pattern = QComboBox(self)
        self.combo_pattern.addItems(["straight", "wave"])
        self.combo_pattern.setToolTip("Motif des lignes de pliage (droit ou vague ondulée)")
        form.addRow("Motif d'incision :", self.combo_pattern)

        self.spin_cut_length = QDoubleSpinBox(self)
        self.spin_cut_length.setRange(1.0, 100.0)
        self.spin_cut_length.setValue(10.0)
        self.spin_cut_length.setSuffix(" mm")
        self.spin_cut_length.setToolTip("Longueur de chaque fente de coupe")
        form.addRow("Longueur de coupe :", self.spin_cut_length)

        self.spin_gap_length = QDoubleSpinBox(self)
        self.spin_gap_length.setRange(0.5, 50.0)
        self.spin_gap_length.setValue(2.0)
        self.spin_gap_length.setSuffix(" mm")
        self.spin_gap_length.setToolTip("Longueur du pont de matière conservé entre fentes")
        form.addRow("Espacement fentes :", self.spin_gap_length)

        self.spin_spacing = QDoubleSpinBox(self)
        self.spin_spacing.setRange(0.5, 20.0)
        self.spin_spacing.setValue(1.5)
        self.spin_spacing.setSuffix(" mm")
        self.spin_spacing.setToolTip("Distance horizontale entre deux lignes de coupe parallèles")
        form.addRow("Espacement lignes :", self.spin_spacing)

        layout.addLayout(form)

        btn_box = QHBoxLayout()
        btn_cancel = QPushButton("Annuler", self)
        btn_cancel.clicked.connect(self.reject)
        btn_gen = QPushButton("🪵 Générer la Charnière", self)
        btn_gen.setStyleSheet(f"font-weight: bold; background-color: {COLOR_ACCENT}; color: white;")
        btn_gen.clicked.connect(self.accept)
        btn_box.addWidget(btn_cancel)
        btn_box.addWidget(btn_gen)
        layout.addLayout(btn_box)


class MultiHeadWizardDialog(QDialog):
    """Optical alignment & offset wizard for dual-head laser systems."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("🎯 Assistant Calibration Multi-Tête Laser")
        self.setMinimumWidth(440)

        layout = QVBoxLayout(self)

        lbl_desc = QLabel(
            "Entrez les coordonnées mesurées de vos deux gravures de test (Tête 1 et Tête 2).\n"
            "L'assistant calculera la matrice de décalage X/Y pour aligner parfaitement les deux lasers."
        )
        lbl_desc.setWordWrap(True)
        lbl_desc.setStyleSheet(f"color: {COLOR_MUTED}; margin-bottom: 8px;")
        layout.addWidget(lbl_desc)

        form = QFormLayout()

        self.spin_h1_x = QDoubleSpinBox(self)
        self.spin_h1_x.setRange(-2000.0, 2000.0)
        self.spin_h1_x.setValue(10.0)
        self.spin_h1_x.setSuffix(" mm")
        self.spin_h1_x.setToolTip("Position X mesurée de la gravure de test faite par la Tête 1")
        form.addRow("Tête 1 (Repère X) :", self.spin_h1_x)

        self.spin_h1_y = QDoubleSpinBox(self)
        self.spin_h1_y.setRange(-2000.0, 2000.0)
        self.spin_h1_y.setValue(20.0)
        self.spin_h1_y.setSuffix(" mm")
        self.spin_h1_y.setToolTip("Position Y mesurée de la gravure de test faite par la Tête 1")
        form.addRow("Tête 1 (Repère Y) :", self.spin_h1_y)

        self.spin_h2_x = QDoubleSpinBox(self)
        self.spin_h2_x.setRange(-2000.0, 2000.0)
        self.spin_h2_x.setValue(12.5)
        self.spin_h2_x.setSuffix(" mm")
        self.spin_h2_x.setToolTip("Position X mesurée de la gravure de test faite par la Tête 2")
        form.addRow("Tête 2 (Repère X) :", self.spin_h2_x)

        self.spin_h2_y = QDoubleSpinBox(self)
        self.spin_h2_y.setRange(-2000.0, 2000.0)
        self.spin_h2_y.setValue(23.0)
        self.spin_h2_y.setSuffix(" mm")
        self.spin_h2_y.setToolTip("Position Y mesurée de la gravure de test faite par la Tête 2")
        form.addRow("Tête 2 (Repère Y) :", self.spin_h2_y)

        layout.addLayout(form)

        btn_box = QHBoxLayout()
        btn_cancel = QPushButton("Fermer", self)
        btn_cancel.clicked.connect(self.reject)
        btn_calc = QPushButton("🎯 Calculer la Matrice", self)
        btn_calc.setStyleSheet(f"font-weight: bold; background-color: {COLOR_SUCCESS}; color: white;")
        btn_calc.clicked.connect(self.accept)
        btn_box.addWidget(btn_cancel)
        btn_box.addWidget(btn_calc)
        layout.addLayout(btn_box)


class GCodePreviewDialog(QDialog):
    """3D G-Code Path Simulation & Duration Estimator Dialog."""

    def __init__(self, parent=None, gcode_text=""):
        super().__init__(parent)
        self.setWindowTitle("🧊 Simulation 3D & Trajectoire G-Code")
        self.setMinimumSize(520, 420)

        layout = QVBoxLayout(self)

        lbl_desc = QLabel("Collez votre code G-Code ci-dessous pour calculer la trajectoire 3D et estimer le temps d'usinage.")
        lbl_desc.setWordWrap(True)
        lbl_desc.setStyleSheet(f"color: {COLOR_MUTED};")
        layout.addWidget(lbl_desc)

        self.txt_gcode = QTextEdit(self)
        self.txt_gcode.setPlaceholderText("G0 X0 Y0 Z0 S0\nG1 X50 Y0 Z0 S100\nG1 X50 Y50 Z0 S100...")
        if gcode_text:
            self.txt_gcode.setPlainText(gcode_text)
        else:
            self.txt_gcode.setPlainText("G0 X0 Y0 Z0 S0\nG1 X100 Y0 Z0 S100\nG1 X100 Y100 Z0 S100\nG1 X0 Y100 Z0 S100\nG0 X0 Y0 Z0 S0")
        layout.addWidget(self.txt_gcode)

        form = QFormLayout()
        self.spin_travel = QDoubleSpinBox(self)
        self.spin_travel.setRange(1.0, 5000.0)
        self.spin_travel.setValue(200.0)
        self.spin_travel.setSuffix(" mm/s")
        self.spin_travel.setToolTip("Vitesse des déplacements à vide (G0), sans tir laser")
        form.addRow("Vitesse Déplacement (G0) :", self.spin_travel)

        self.spin_cut = QDoubleSpinBox(self)
        self.spin_cut.setRange(0.1, 2000.0)
        self.spin_cut.setValue(20.0)
        self.spin_cut.setSuffix(" mm/s")
        self.spin_cut.setToolTip("Vitesse de découpe/gravure effective (G1), laser actif")
        form.addRow("Vitesse Découpe (G1) :", self.spin_cut)
        layout.addLayout(form)

        self.lbl_report = QLabel("Cliquez sur 'Lancer la Simulation' pour calculer les métriques.")
        self.lbl_report.setStyleSheet(f"font-weight: bold; color: {COLOR_ACCENT}; margin-top: 6px;")
        layout.addWidget(self.lbl_report)

        btn_box = QHBoxLayout()
        btn_cancel = QPushButton("Fermer", self)
        btn_cancel.clicked.connect(self.reject)
        btn_sim = QPushButton("▶ Lancer la Simulation", self)
        btn_sim.setStyleSheet(f"font-weight: bold; background-color: {COLOR_PURPLE}; color: white;")
        btn_sim.clicked.connect(self._run_simulation)
        btn_box.addWidget(btn_cancel)
        btn_box.addWidget(btn_sim)
        layout.addLayout(btn_box)

    def _run_simulation(self):
        from madgrav.tools.gcode_previewer import simulate_laser_path_3d
        gcode = self.txt_gcode.toPlainText()
        report = simulate_laser_path_3d(gcode, travel_speed_mm_s=self.spin_travel.value(), cut_speed_mm_s=self.spin_cut.value())
        msg = (
            f"Points : {report['point_count']} | "
            f"Découpe : {report['cut_dist_mm']} mm | "
            f"Rapide : {report['travel_dist_mm']} mm\n"
            f"Temps Estimé : {report['total_time_sec']}s (Coupe: {report['cut_time_sec']}s, Rapide: {report['travel_time_sec']}s)"
        )
        self.lbl_report.setText(msg)


class ProductionQueueDialog(QDialog):
    """Production Queue & Multi-Machine Laser Spooler Dialog."""

    def __init__(self, parent=None, manager=None):
        super().__init__(parent)
        self.setWindowTitle("🏭 File de Production Multi-Machines & Spooler Atelier")
        self.setMinimumSize(640, 480)
        from madgrav.tools.production_queue import ProductionQueueManager
        self.manager = manager if manager is not None else ProductionQueueManager()

        layout = QVBoxLayout(self)

        lbl_title = QLabel("Gestionnaire de File de Fabrication Série Multi-Machines")
        lbl_title.setStyleSheet(f"font-weight: bold; font-size: 14px; color: {COLOR_SUCCESS};")
        layout.addWidget(lbl_title)

        # Filter bar
        filter_layout = QHBoxLayout()
        filter_layout.addWidget(QLabel("Filtrer par Machine :"))
        self.combo_machine_filter = QComboBox(self)
        self.combo_machine_filter.addItem("Toutes les machines", "all")
        self.combo_machine_filter.addItem("Laser #1 - CO2 Ruida", "ruida_co2_0")
        self.combo_machine_filter.addItem("Laser #2 - Galvo Fiber", "galvo_fiber_0")
        self.combo_machine_filter.addItem("Laser #3 - Diode GRBL", "diode_grbl_0")
        self.combo_machine_filter.addItem("Laser Par Défaut", "laser_default")
        self.combo_machine_filter.currentIndexChanged.connect(self._refresh_table)
        filter_layout.addWidget(self.combo_machine_filter)
        layout.addLayout(filter_layout)

        # Queue Table
        self.table_queue = QTableWidget(self)
        self.table_queue.setColumnCount(5)
        self.table_queue.setHorizontalHeaderLabels(["ID", "Nom du Job", "Machine", "Qté", "Statut"])
        self.table_queue.horizontalHeader().setStretchLastSection(True)
        layout.addWidget(self.table_queue)

        # Add Job Form
        form = QFormLayout()
        self.input_name = QLineEdit(self)
        self.input_name.setText("Plaque signalétique")
        form.addRow("Nom du Job :", self.input_name)

        self.combo_target_machine = QComboBox(self)
        self.combo_target_machine.addItem("Laser #1 - CO2 Ruida", "ruida_co2_0")
        self.combo_target_machine.addItem("Laser #2 - Galvo Fiber", "galvo_fiber_0")
        self.combo_target_machine.addItem("Laser #3 - Diode GRBL", "diode_grbl_0")
        self.combo_target_machine.addItem("Laser Par Défaut", "laser_default")
        form.addRow("Machine Cible :", self.combo_target_machine)

        self.spin_qty = QSpinBox(self)
        self.spin_qty.setRange(1, 10000)
        self.spin_qty.setValue(10)
        form.addRow("Quantité :", self.spin_qty)

        self.input_barcode = QLineEdit(self)
        self.input_barcode.setPlaceholderText("Scan Code-Barres / SKU (ex: JOB-001)")
        form.addRow("Code-Barres / SKU :", self.input_barcode)

        layout.addLayout(form)

        btn_add = QPushButton("➕ Ajouter le Job à la File", self)
        btn_add.setStyleSheet(f"font-weight: bold; background-color: {COLOR_ACCENT}; color: white;")
        btn_add.clicked.connect(self._on_add_job)
        layout.addWidget(btn_add)

        self.lbl_status = QLabel("Aucun job en cours.")
        self.lbl_status.setWordWrap(True)
        self.lbl_status.setStyleSheet(f"color: {COLOR_MUTED}; margin-top: 6px;")
        layout.addWidget(self.lbl_status)

        btn_box = QHBoxLayout()
        btn_next = QPushButton("▶ Prochain Job Machine", self)
        btn_next.clicked.connect(self._on_next_job)
        btn_complete = QPushButton("✅ Marquer Terminé", self)
        btn_complete.clicked.connect(self._on_complete_job)
        btn_close = QPushButton("Fermer", self)
        btn_close.clicked.connect(self.reject)
        btn_box.addWidget(btn_next)
        btn_box.addWidget(btn_complete)
        btn_box.addWidget(btn_close)
        layout.addLayout(btn_box)

        self.current_job = None
        self._refresh_table()

    def _refresh_table(self):
        filter_val = self.combo_machine_filter.currentData()
        if not filter_val or filter_val == "all":
            jobs = self.manager.jobs
        else:
            jobs = self.manager.get_jobs_for_machine(filter_val)

        # Also dynamically populate combo_machine_filter with unknown machines
        for j in self.manager.jobs:
            m = j.target_machine_id
            if m and self.combo_machine_filter.findData(m) == -1:
                self.combo_machine_filter.addItem(f"Machine: {m}", m)

        self.table_queue.setRowCount(len(jobs))
        for row_idx, job in enumerate(jobs):
            self.table_queue.setItem(row_idx, 0, QTableWidgetItem(str(job.job_id)))
            self.table_queue.setItem(row_idx, 1, QTableWidgetItem(str(job.name)))
            self.table_queue.setItem(row_idx, 2, QTableWidgetItem(str(job.target_machine_id)))
            self.table_queue.setItem(row_idx, 3, QTableWidgetItem(str(job.quantity)))
            self.table_queue.setItem(row_idx, 4, QTableWidgetItem(str(job.status)))

    def _on_add_job(self):
        name = self.input_name.text().strip() or "Job Laser"
        barcode = self.input_barcode.text().strip() or None
        target_machine = self.combo_target_machine.currentData()
        job = self.manager.add_job(
            job_name=name,
            file_path="project.svg",
            target_machine_id=target_machine,
            quantity=self.spin_qty.value(),
            barcode=barcode,
        )
        summary = self.manager.export_production_summary()
        self.lbl_status.setText(f"Job '{job.name}' ajouté sur '{job.target_machine_id}'. En file: {summary['queued_count']} jobs.")
        self._refresh_table()

    def _on_next_job(self):
        filter_val = self.combo_machine_filter.currentData()
        machine_id = None if filter_val == "all" else filter_val
        job = self.manager.get_next_job(machine_id=machine_id)
        if job:
            self.current_job = job
            self.lbl_status.setText(f"Job EN COURS: '{job.name}' sur '{job.target_machine_id}' (Qté: {job.quantity}, SKU: {job.barcode})")
        else:
            self.lbl_status.setText("Aucun job en attente dans la file.")
        self._refresh_table()

    def _on_complete_job(self):
        if self.current_job:
            self.manager.mark_job_completed(self.current_job.job_id, duration_sec=60.0)
            summary = self.manager.export_production_summary()
            self.lbl_status.setText(f"Job '{self.current_job.name}' terminé! Total pièces produites: {summary['total_parts_produced']}.")
            self.current_job = None
        else:
            self.lbl_status.setText("Sélectionnez d'abord 'Prochain Job' pour traiter un travail.")
        self._refresh_table()


class NestingDialog(QDialog):
    """Configuration dialog for 2D Polygon Nesting & Sheet Packing Optimizer."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("🧩 Imbrication Automatique (Nesting) & Optimisation Plaque")
        self.setMinimumWidth(400)

        layout = QVBoxLayout(self)

        lbl_desc = QLabel("Réarrange les formes sélectionnées en grille compacte sur une plaque de matériau pour minimiser les chutes.")
        lbl_desc.setWordWrap(True)
        lbl_desc.setStyleSheet(f"color: {COLOR_MUTED}; margin-bottom: 8px;")
        layout.addWidget(lbl_desc)

        form = QFormLayout()

        self.spin_sheet_w = QDoubleSpinBox(self)
        self.spin_sheet_w.setRange(10.0, 5000.0)
        self.spin_sheet_w.setValue(300.0)
        self.spin_sheet_w.setSuffix(" mm")
        self.spin_sheet_w.setToolTip("Largeur disponible de la plaque de matériau")
        form.addRow("Largeur de la Plaque :", self.spin_sheet_w)

        self.spin_sheet_h = QDoubleSpinBox(self)
        self.spin_sheet_h.setRange(10.0, 5000.0)
        self.spin_sheet_h.setValue(200.0)
        self.spin_sheet_h.setSuffix(" mm")
        self.spin_sheet_h.setToolTip("Hauteur disponible de la plaque de matériau")
        form.addRow("Hauteur de la Plaque :", self.spin_sheet_h)

        self.spin_margin = QDoubleSpinBox(self)
        self.spin_margin.setRange(0.0, 100.0)
        self.spin_margin.setValue(2.0)
        self.spin_margin.setSuffix(" mm")
        self.spin_margin.setToolTip("Espace de sécurité laissé entre chaque pièce")
        form.addRow("Marge Entre Pièces :", self.spin_margin)

        self.check_rotation = QCheckBox("Autoriser la rotation automatique", self)
        self.check_rotation.setToolTip(
            "Teste plusieurs orientations par pièce pour un remplissage plus compact -- "
            "à éviter pour du texte ou une gravure dont l'orientation compte"
        )
        form.addRow("", self.check_rotation)

        layout.addLayout(form)

        btn_box = QHBoxLayout()
        btn_cancel = QPushButton("Annuler", self)
        btn_cancel.clicked.connect(self.reject)
        btn_nest = QPushButton("🧩 Imbriquer les Pièces", self)
        btn_nest.setStyleSheet(f"font-weight: bold; background-color: {COLOR_ACCENT}; color: white;")
        btn_nest.clicked.connect(self.accept)
        btn_box.addWidget(btn_cancel)
        btn_box.addWidget(btn_nest)
        layout.addLayout(btn_box)


class JobQuoteDialog(QDialog):
    """Configuration dialog for Client Job Cost & Quote Generator."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("🧾 Générateur de Devis Client")
        self.setMinimumWidth(420)

        layout = QVBoxLayout(self)

        lbl_desc = QLabel("Calcule un devis client détaillé à partir des éléments du plan de travail (matière, temps machine, marge).")
        lbl_desc.setWordWrap(True)
        lbl_desc.setStyleSheet(f"color: {COLOR_MUTED}; margin-bottom: 8px;")
        layout.addWidget(lbl_desc)

        form = QFormLayout()

        self.spin_material_cost = QDoubleSpinBox(self)
        self.spin_material_cost.setRange(0.0, 10000.0)
        self.spin_material_cost.setValue(15.0)
        self.spin_material_cost.setSuffix(" €/m²")
        self.spin_material_cost.setToolTip("Coût d'achat du matériau, par mètre carré")
        form.addRow("Coût Matière :", self.spin_material_cost)

        self.spin_machine_rate = QDoubleSpinBox(self)
        self.spin_machine_rate.setRange(0.0, 10000.0)
        self.spin_machine_rate.setValue(45.0)
        self.spin_machine_rate.setSuffix(" €/h")
        self.spin_machine_rate.setToolTip("Taux horaire facturé pour le temps machine (découpe + gravure)")
        form.addRow("Taux Machine :", self.spin_machine_rate)

        self.spin_setup_fee = QDoubleSpinBox(self)
        self.spin_setup_fee.setRange(0.0, 10000.0)
        self.spin_setup_fee.setValue(5.0)
        self.spin_setup_fee.setSuffix(" €")
        self.spin_setup_fee.setToolTip("Frais fixes de préparation/mise en route, ajoutés une seule fois")
        form.addRow("Frais de Mise en Route :", self.spin_setup_fee)

        self.spin_margin_pct = QDoubleSpinBox(self)
        self.spin_margin_pct.setRange(0.0, 500.0)
        self.spin_margin_pct.setValue(20.0)
        self.spin_margin_pct.setSuffix(" %")
        self.spin_margin_pct.setToolTip("Marge bénéficiaire appliquée sur le sous-total avant devis final")
        form.addRow("Marge Bénéficiaire :", self.spin_margin_pct)

        layout.addLayout(form)

        self.lbl_report = QLabel("Cliquez sur 'Calculer le Devis' pour voir le détail.")
        self.lbl_report.setWordWrap(True)
        self.lbl_report.setStyleSheet(f"font-weight: bold; color: {COLOR_ACCENT}; margin-top: 6px;")
        layout.addWidget(self.lbl_report)

        btn_box = QHBoxLayout()
        btn_close = QPushButton("Fermer", self)
        # Consistent with every other "Fermer"/"Annuler" button in this
        # file (self.reject, e.g. MultiHeadWizardDialog/GCodePreviewDialog)
        # -- this one used to connect to self.accept instead, a stray
        # inconsistency (harmless here since none of this dialog's Qt
        # callers branch on exec()'s Accepted/Rejected result, but
        # "closing" a dialog shouldn't read as "confirming" it).
        btn_close.clicked.connect(self.reject)
        btn_calc = QPushButton("🧾 Calculer le Devis", self)
        btn_calc.setStyleSheet(f"font-weight: bold; background-color: {COLOR_SUCCESS}; color: white;")
        btn_calc.clicked.connect(self._on_calculate)
        btn_box.addWidget(btn_close)
        btn_box.addWidget(btn_calc)
        layout.addLayout(btn_box)

        self._elements_service = None

    def set_elements_service(self, elements_service):
        self._elements_service = elements_service

    def _on_calculate(self):
        if self._elements_service is None:
            return
        from madgrav.tools.cost_quote import generate_job_quote
        quote = generate_job_quote(
            self._elements_service,
            material_cost_per_m2=self.spin_material_cost.value(),
            machine_rate_per_hour=self.spin_machine_rate.value(),
            setup_fee=self.spin_setup_fee.value(),
            margin_percent=self.spin_margin_pct.value(),
        )
        self.lbl_report.setText(
            f"Découpe : {quote['cut_length_mm']} mm | Matière utilisée : {quote['used_material_m2']} m²\n"
            f"Coût matière : {quote['material_cost']} € | Coût machine : {quote['machine_cost']} € | "
            f"Mise en route : {quote['setup_fee']} €\n"
            f"Sous-total : {quote['subtotal']} € | Marge : {quote['margin_amount']} €\n"
            f"DEVIS TOTAL : {quote['total_quote']} {quote['currency']}"
        )


class SmartVectorizeDialog(QDialog):
    """Configuration dialog for Smart Bitmap-to-Vector Tracing."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("✏️ Vectorisation Intelligente (Trace Image)")
        self.setMinimumWidth(400)

        layout = QVBoxLayout(self)

        lbl_desc = QLabel("Convertit l'image bitmap sélectionnée en contours vectoriels lissés, positionnés et mis à l'échelle sur l'image d'origine.")
        lbl_desc.setWordWrap(True)
        lbl_desc.setStyleSheet(f"color: {COLOR_MUTED}; margin-bottom: 8px;")
        layout.addWidget(lbl_desc)

        form = QFormLayout()

        self.spin_threshold = QSpinBox(self)
        self.spin_threshold.setRange(0, 255)
        self.spin_threshold.setValue(128)
        self.spin_threshold.setToolTip("Seuil de binarisation (0 = tout noir, 255 = tout blanc)")
        form.addRow("Seuil de Binarisation :", self.spin_threshold)

        layout.addLayout(form)

        btn_box = QHBoxLayout()
        btn_cancel = QPushButton("Annuler", self)
        btn_cancel.clicked.connect(self.reject)
        btn_trace = QPushButton("✏️ Vectoriser", self)
        btn_trace.setStyleSheet(f"font-weight: bold; background-color: {COLOR_ACCENT}; color: white;")
        btn_trace.clicked.connect(self.accept)
        btn_box.addWidget(btn_cancel)
        btn_box.addWidget(btn_trace)
        layout.addLayout(btn_box)


class Relief3DPreviewDialog(QDialog):
    """Preview/statistics dialog for 3D Grayscale Laser Relief -- reports
    the raster power range and scan line count for a source image, but
    does not queue or dispatch any real laser job (same "analysis only"
    scope as GCodePreviewDialog)."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("🏔️ Aperçu Relief 3D en Niveaux de Gris")
        self.setMinimumWidth(420)

        layout = QVBoxLayout(self)

        lbl_desc = QLabel(
            "Calcule la carte de puissance variable (relief 3D) à partir de l'image bitmap "
            "sélectionnée. Aperçu et statistiques uniquement -- n'envoie rien au laser."
        )
        lbl_desc.setWordWrap(True)
        lbl_desc.setStyleSheet(f"color: {COLOR_MUTED}; margin-bottom: 8px;")
        layout.addWidget(lbl_desc)

        form = QFormLayout()

        self.spin_min_power = QDoubleSpinBox(self)
        self.spin_min_power.setRange(0.0, 100.0)
        self.spin_min_power.setValue(10.0)
        self.spin_min_power.setSuffix(" %")
        self.spin_min_power.setToolTip("Puissance laser pour les zones les plus sombres de l'image")
        form.addRow("Puissance Minimale :", self.spin_min_power)

        self.spin_max_power = QDoubleSpinBox(self)
        self.spin_max_power.setRange(0.0, 100.0)
        self.spin_max_power.setValue(100.0)
        self.spin_max_power.setSuffix(" %")
        self.spin_max_power.setToolTip("Puissance laser pour les zones les plus claires de l'image")
        form.addRow("Puissance Maximale :", self.spin_max_power)

        self.check_invert = QCheckBox("Inverser (blanc = profond)", self)
        self.check_invert.setToolTip("Inverse l'échelle de gris : le blanc devient la puissance maximale au lieu du noir")
        form.addRow("", self.check_invert)

        self.spin_passes = QSpinBox(self)
        self.spin_passes.setRange(1, 20)
        self.spin_passes.setValue(1)
        self.spin_passes.setToolTip("Nombre de passages du laser sur chaque ligne de balayage")
        form.addRow("Passes :", self.spin_passes)

        layout.addLayout(form)

        self.lbl_report = QLabel("Cliquez sur 'Calculer l'Aperçu' pour voir les statistiques.")
        self.lbl_report.setWordWrap(True)
        self.lbl_report.setStyleSheet(f"font-weight: bold; color: {COLOR_ACCENT}; margin-top: 6px;")
        layout.addWidget(self.lbl_report)

        btn_box = QHBoxLayout()
        btn_close = QPushButton("Fermer", self)
        # Consistent with every other "Fermer"/"Annuler" button in this
        # file (self.reject, e.g. MultiHeadWizardDialog/GCodePreviewDialog)
        # -- this one used to connect to self.accept instead, a stray
        # inconsistency (harmless here since none of this dialog's Qt
        # callers branch on exec()'s Accepted/Rejected result, but
        # "closing" a dialog shouldn't read as "confirming" it).
        btn_close.clicked.connect(self.reject)
        btn_preview = QPushButton("🏔️ Calculer l'Aperçu", self)
        btn_preview.setStyleSheet(f"font-weight: bold; background-color: {COLOR_PURPLE}; color: white;")
        btn_preview.clicked.connect(self._on_preview)
        btn_box.addWidget(btn_close)
        btn_box.addWidget(btn_preview)
        layout.addLayout(btn_box)

        self._image_np = None

    def set_image(self, image_np):
        self._image_np = image_np

    def _on_preview(self):
        if self._image_np is None:
            self.lbl_report.setText("Aucune image sélectionnée.")
            return
        from madgrav.tools.relief_3d import generate_3d_laser_relief
        report = generate_3d_laser_relief(
            self._image_np,
            max_power_percent=self.spin_max_power.value(),
            min_power_percent=self.spin_min_power.value(),
            invert=self.check_invert.isChecked(),
            passes=self.spin_passes.value(),
        )
        self.lbl_report.setText(
            f"Dimensions : {report['width']} x {report['height']} px "
            f"({len(report['scan_lines'])} lignes de balayage)\n"
            f"Puissance : {report['min_s']:.1f}% -- {report['max_s']:.1f}% | Passes : {report['passes']}"
        )


class NodeEditorDialog(QDialog):
    """List/edit dialog for a path's individual vector nodes (anchor
    points) -- deplacer/inserer/supprimer, backed by VectorNodeEditor.
    Not a canvas drag-to-edit tool (bigger scope, deferred); this is the
    list-based equivalent, same idea as a font's glyph-point inspector."""

    def __init__(self, parent=None, path=None, units_per_mm=1.0):
        super().__init__(parent)
        self.setWindowTitle("🖊️ Éditeur de Nœuds Vectoriels")
        self.setMinimumSize(420, 420)
        self._path = path
        self._units_per_mm = units_per_mm or 1.0
        self.on_changed = None  # callable, set by the caller

        layout = QVBoxLayout(self)

        lbl_desc = QLabel("Liste des points d'ancrage du tracé sélectionné. Sélectionnez un nœud pour le déplacer, en insérer un après, ou le supprimer.")
        lbl_desc.setWordWrap(True)
        lbl_desc.setStyleSheet(f"color: {COLOR_MUTED}; margin-bottom: 8px;")
        layout.addWidget(lbl_desc)

        self.list_nodes = QListWidget(self)
        self.list_nodes.currentRowChanged.connect(self._on_selection_changed)
        layout.addWidget(self.list_nodes)

        self.lbl_status = QLabel("")
        self.lbl_status.setWordWrap(True)
        self.lbl_status.setStyleSheet(f"color: {COLOR_WARNING};")
        layout.addWidget(self.lbl_status)

        form = QFormLayout()
        self.spin_x = QDoubleSpinBox(self)
        self.spin_x.setRange(-100000.0, 100000.0)
        self.spin_x.setSuffix(" mm")
        form.addRow("X :", self.spin_x)
        self.spin_y = QDoubleSpinBox(self)
        self.spin_y.setRange(-100000.0, 100000.0)
        self.spin_y.setSuffix(" mm")
        form.addRow("Y :", self.spin_y)
        layout.addLayout(form)

        btn_row = QHBoxLayout()
        self.btn_move = QPushButton("↕ Déplacer", self)
        self.btn_move.clicked.connect(self._on_move)
        self.btn_insert = QPushButton("➕ Insérer Après", self)
        self.btn_insert.clicked.connect(self._on_insert)
        self.btn_delete = QPushButton("🗑️ Supprimer", self)
        self.btn_delete.clicked.connect(self._on_delete)
        btn_row.addWidget(self.btn_move)
        btn_row.addWidget(self.btn_insert)
        btn_row.addWidget(self.btn_delete)
        layout.addLayout(btn_row)

        btn_close = QPushButton("Fermer", self)
        # Consistent with every other "Fermer"/"Annuler" button in this
        # file (self.reject, e.g. MultiHeadWizardDialog/GCodePreviewDialog)
        # -- this one used to connect to self.accept instead, a stray
        # inconsistency (harmless here since none of this dialog's Qt
        # callers branch on exec()'s Accepted/Rejected result, but
        # "closing" a dialog shouldn't read as "confirming" it).
        btn_close.clicked.connect(self.reject)
        layout.addWidget(btn_close)

        self._refresh_list()
        self._on_selection_changed(-1)

    def _refresh_list(self):
        from madgrav.tools.node_editor import VectorNodeEditor
        self.list_nodes.clear()
        if self._path is None:
            return
        for node_data in VectorNodeEditor.extract_nodes_and_handles(self._path):
            x_mm = node_data["x"] / self._units_per_mm
            y_mm = node_data["y"] / self._units_per_mm
            self.list_nodes.addItem(f"#{node_data['index']} {node_data['type']} ({x_mm:.2f}, {y_mm:.2f}) mm")

    def _on_selection_changed(self, row):
        enabled = row >= 0
        self.btn_move.setEnabled(enabled)
        self.btn_insert.setEnabled(enabled)
        self.btn_delete.setEnabled(enabled)
        self.spin_x.setEnabled(enabled)
        self.spin_y.setEnabled(enabled)
        if enabled and self._path is not None:
            from madgrav.tools.node_editor import VectorNodeEditor
            nodes = VectorNodeEditor.extract_nodes_and_handles(self._path)
            if row < len(nodes):
                self.spin_x.setValue(nodes[row]["x"] / self._units_per_mm)
                self.spin_y.setValue(nodes[row]["y"] / self._units_per_mm)

    def _notify_changed(self):
        self._refresh_list()
        if callable(self.on_changed):
            self.on_changed()

    def _on_move(self):
        from madgrav.tools.node_editor import VectorNodeEditor
        row = self.list_nodes.currentRow()
        if row < 0 or self._path is None:
            return
        ok = VectorNodeEditor.move_node(
            self._path, row,
            self.spin_x.value() * self._units_per_mm,
            self.spin_y.value() * self._units_per_mm,
        )
        if ok:
            self.lbl_status.setText("")
            self._notify_changed()
        else:
            self.lbl_status.setText("Impossible de déplacer ce nœud.")

    def _on_insert(self):
        from madgrav.tools.node_editor import VectorNodeEditor
        row = self.list_nodes.currentRow()
        if row < 0 or self._path is None:
            return
        ok = VectorNodeEditor.insert_node(self._path, row)
        if ok:
            self.lbl_status.setText("")
            self._notify_changed()
        else:
            self.lbl_status.setText("Impossible d'insérer un nœud ici.")

    def _on_delete(self):
        from madgrav.tools.node_editor import VectorNodeEditor
        row = self.list_nodes.currentRow()
        if row < 0 or self._path is None:
            return
        ok = VectorNodeEditor.delete_node(self._path, row)
        if ok:
            self.lbl_status.setText("")
            self._notify_changed()
        else:
            # delete_node() refuses to go below 1 remaining point
            # (node_editor.py) -- was silently no-op'ing here before,
            # same "click did nothing, no idea why" gap fixed elsewhere
            # in this app's dialogs this session.
            self.lbl_status.setText("Impossible de supprimer : il doit rester au moins un point.")


class GalvoHatchDialog(QDialog):
    """Configuration dialog for Galvo/Fiber Laser Hatch & Wobble Patterns.

    Distinct from the general "Remplissage Hachuré" tool specifically via
    the wobble mode -- a high-frequency sinusoidal kerf pattern used for
    fiber-laser rust/coating removal and cleaning passes, which the
    regular hatch tool has no equivalent for."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("🏁 Hachurage Galvo & Fibre (Wobble)")
        self.setMinimumWidth(400)

        layout = QVBoxLayout(self)

        lbl_desc = QLabel("Génère un motif de hachurage dense pour laser galvo/fibre, avec un mode Wobble (ondulation haute fréquence) pour le nettoyage/décapage.")
        lbl_desc.setWordWrap(True)
        lbl_desc.setStyleSheet(f"color: {COLOR_MUTED}; margin-bottom: 8px;")
        layout.addWidget(lbl_desc)

        form = QFormLayout()

        self.combo_mode = QComboBox(self)
        self.combo_mode.addItems(["cross", "wobble"])
        self.combo_mode.setToolTip("cross = hachurage croisé classique -- wobble = ondulation haute fréquence pour nettoyage/décapage")
        self.combo_mode.currentTextChanged.connect(self._on_mode_changed)
        form.addRow("Mode :", self.combo_mode)

        self.spin_angle = QDoubleSpinBox(self)
        self.spin_angle.setRange(-360.0, 360.0)
        self.spin_angle.setValue(45.0)
        self.spin_angle.setSuffix(" °")
        self.spin_angle.setToolTip("Orientation des lignes de hachurage par rapport à l'horizontale")
        form.addRow("Angle du Motif :", self.spin_angle)

        self.spin_spacing = QDoubleSpinBox(self)
        self.spin_spacing.setRange(0.01, 50.0)
        self.spin_spacing.setDecimals(2)
        self.spin_spacing.setValue(0.5)
        self.spin_spacing.setSuffix(" mm")
        self.spin_spacing.setToolTip("Distance entre deux lignes de hachurage parallèles")
        form.addRow("Espacement Lignes :", self.spin_spacing)

        self.spin_wobble_freq = QDoubleSpinBox(self)
        self.spin_wobble_freq.setRange(1.0, 500.0)
        self.spin_wobble_freq.setValue(50.0)
        self.spin_wobble_freq.setToolTip("Nombre d'oscillations par unité de longueur (mode Wobble uniquement)")
        form.addRow("Fréquence Wobble :", self.spin_wobble_freq)

        self.spin_wobble_amp = QDoubleSpinBox(self)
        self.spin_wobble_amp.setRange(0.01, 20.0)
        self.spin_wobble_amp.setDecimals(2)
        self.spin_wobble_amp.setValue(0.2)
        self.spin_wobble_amp.setSuffix(" mm")
        self.spin_wobble_amp.setToolTip("Amplitude latérale de l'ondulation (mode Wobble uniquement)")
        form.addRow("Amplitude Wobble :", self.spin_wobble_amp)

        layout.addLayout(form)

        btn_box = QHBoxLayout()
        btn_cancel = QPushButton("Annuler", self)
        btn_cancel.clicked.connect(self.reject)
        btn_gen = QPushButton("🏁 Générer le Hachurage", self)
        btn_gen.setStyleSheet(f"font-weight: bold; background-color: {COLOR_ACCENT}; color: white;")
        btn_gen.clicked.connect(self.accept)
        btn_box.addWidget(btn_cancel)
        btn_box.addWidget(btn_gen)
        layout.addLayout(btn_box)

        self._on_mode_changed(self.combo_mode.currentText())

    def _on_mode_changed(self, mode):
        is_wobble = (mode == "wobble")
        self.spin_wobble_freq.setEnabled(is_wobble)
        self.spin_wobble_amp.setEnabled(is_wobble)


class RotaryAssistantDialog(QDialog):
    """Interactive wizard for rotary attachment setup (Chuck and Roller modes)."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("🔄 Assistant Axe Rotatif (Rotary Setup)")
        self.setMinimumWidth(440)
        self.setModal(True)

        layout = QVBoxLayout(self)

        # Header description
        lbl_info = QLabel("Configurez les paramètres de votre mandrin ou plateau à rouleaux pour découpe et gravure cylindrique.")
        lbl_info.setWordWrap(True)
        layout.addWidget(lbl_info)

        # Mode Selection
        grp_mode = QGroupBox("Type d'Axe Rotatif", self)
        mode_layout = QHBoxLayout(grp_mode)
        self.chuck_radio = QRadioButton("Mandrin (Chuck)", grp_mode)
        self.roller_radio = QRadioButton("Rouleaux (Roller)", grp_mode)
        self.chuck_radio.setChecked(True)
        self.chuck_radio.toggled.connect(self._update_calculations)
        self.roller_radio.toggled.connect(self._update_calculations)
        mode_layout.addWidget(self.chuck_radio)
        mode_layout.addWidget(self.roller_radio)
        layout.addWidget(grp_mode)

        # Form Parameters
        form = QFormLayout()

        self.diameter_spin = QDoubleSpinBox(self)
        self.diameter_spin.setRange(1.0, 1000.0)
        self.diameter_spin.setValue(80.0)
        self.diameter_spin.setSuffix(" mm")
        self.diameter_spin.valueChanged.connect(self._update_calculations)
        form.addRow("Diamètre de la Pièce :", self.diameter_spin)

        self.roller_diam_spin = QDoubleSpinBox(self)
        self.roller_diam_spin.setRange(1.0, 500.0)
        self.roller_diam_spin.setValue(50.0)
        self.roller_diam_spin.setSuffix(" mm")
        self.roller_diam_spin.valueChanged.connect(self._update_calculations)
        form.addRow("Diamètre des Rouleaux :", self.roller_diam_spin)

        self.steps_spin = QSpinBox(self)
        self.steps_spin.setRange(1, 10000)
        self.steps_spin.setValue(200)
        self.steps_spin.valueChanged.connect(self._update_calculations)
        form.addRow("Pas Moteur / Tour :", self.steps_spin)

        self.microsteps_spin = QSpinBox(self)
        self.microsteps_spin.setRange(1, 256)
        self.microsteps_spin.setValue(16)
        self.microsteps_spin.valueChanged.connect(self._update_calculations)
        form.addRow("Division Micropas :", self.microsteps_spin)

        self.gear_ratio_spin = QDoubleSpinBox(self)
        self.gear_ratio_spin.setRange(0.1, 100.0)
        self.gear_ratio_spin.setValue(1.0)
        self.gear_ratio_spin.valueChanged.connect(self._update_calculations)
        form.addRow("Ratio Réduction (Courroie) :", self.gear_ratio_spin)

        layout.addLayout(form)

        # Computed Results Box
        res_group = QGroupBox("Résultats & Configuration Machine", self)
        res_layout = QVBoxLayout(res_group)
        self.circumference_label = QLabel("Circonférence : -- mm", self)
        self.pulses_label = QLabel("Résolution ($102) : -- pas/mm", self)
        self.circumference_label.setStyleSheet("font-weight: bold;")
        self.pulses_label.setStyleSheet(f"font-weight: bold; color: {COLOR_ACCENT};")
        res_layout.addWidget(self.circumference_label)
        res_layout.addWidget(self.pulses_label)
        layout.addWidget(res_group)

        # Buttons
        btn_box = QHBoxLayout()
        btn_cancel = QPushButton("Fermer", self)
        btn_cancel.clicked.connect(self.reject)
        self.btn_apply = QPushButton("✔️ Appliquer la Configuration", self)
        self.btn_apply.setStyleSheet(f"font-weight: bold; background-color: {COLOR_ACCENT}; color: white;")
        self.btn_apply.clicked.connect(self.accept)
        btn_box.addWidget(btn_cancel)
        btn_box.addWidget(self.btn_apply)
        layout.addLayout(btn_box)

        self._update_calculations()

    def _update_calculations(self):
        from madgrav.tools.rotary_assistant import calculate_rotary_parameters
        is_chuck = self.chuck_radio.isChecked()
        self.roller_diam_spin.setEnabled(not is_chuck)

        diameter = self.diameter_spin.value()
        roller_diam = self.roller_diam_spin.value()
        steps = self.steps_spin.value()
        microsteps = self.microsteps_spin.value()
        gear_ratio = self.gear_ratio_spin.value()

        try:
            res = calculate_rotary_parameters(
                object_diameter_mm=diameter,
                steps_per_rev=int(steps * gear_ratio),
                microstepping=microsteps,
                roller_diameter_mm=roller_diam,
                is_chuck=is_chuck,
            )
            self.circumference_label.setText(f"Circonférence de la Pièce : {res['circumference_mm']:.2f} mm")
            self.pulses_label.setText(f"Résolution Axe Rotatif ($102) : {res['pulses_per_mm']:.3f} pas/mm")
        except Exception as ex:
            self.pulses_label.setText(f"Erreur : {ex}")

    def get_parameters(self) -> dict:
        from madgrav.tools.rotary_assistant import calculate_rotary_parameters
        is_chuck = self.chuck_radio.isChecked()
        steps = int(self.steps_spin.value() * self.gear_ratio_spin.value())
        return calculate_rotary_parameters(
            object_diameter_mm=self.diameter_spin.value(),
            steps_per_rev=steps,
            microstepping=self.microsteps_spin.value(),
            roller_diameter_mm=self.roller_diam_spin.value(),
            is_chuck=is_chuck,
        )


class MultiFormatExportDialog(QDialog):
    """Configuration dialog for direct multi-format laser exports."""

    def __init__(self, default_path="", parent=None):
        super().__init__(parent)
        self.setWindowTitle("💾 Export Direct Multi-Formats")
        self.setMinimumWidth(460)
        self.setModal(True)

        layout = QVBoxLayout(self)

        form = QFormLayout()

        self.combo_format = QComboBox(self)
        self.combo_format.addItem("G-Code CNC / Diode (*.gcode, *.nc)", "gcode")
        self.combo_format.addItem("Ruida DSP (*.rd)", "rd")
        self.combo_format.addItem("Lihuiyu K40 (*.egv)", "egv")
        self.combo_format.addItem("AutoCAD DXF (*.dxf)", "dxf")
        self.combo_format.addItem("Scalable Vector Graphics (*.svg)", "svg")
        form.addRow("Format de Destination :", self.combo_format)

        path_layout = QHBoxLayout()
        self.edit_path = QLineEdit(default_path or "export_output.gcode", self)
        btn_browse = QPushButton("Parcourir...", self)
        btn_browse.clicked.connect(self._on_browse)
        path_layout.addWidget(self.edit_path)
        path_layout.addWidget(btn_browse)
        form.addRow("Fichier de Sortie :", path_layout)

        self.spin_power = QDoubleSpinBox(self)
        self.spin_power.setRange(1.0, 100.0)
        self.spin_power.setValue(100.0)
        self.spin_power.setSuffix(" %")
        form.addRow("Puissance Laser :", self.spin_power)

        self.spin_speed = QDoubleSpinBox(self)
        self.spin_speed.setRange(1.0, 2000.0)
        self.spin_speed.setValue(20.0)
        self.spin_speed.setSuffix(" mm/s")
        form.addRow("Vitesse de Découpe :", self.spin_speed)

        layout.addLayout(form)

        btn_box = QHBoxLayout()
        btn_cancel = QPushButton("Annuler", self)
        btn_cancel.clicked.connect(self.reject)
        self.btn_export = QPushButton("🚀 Exporter Maintenant", self)
        self.btn_export.setStyleSheet(f"font-weight: bold; background-color: {COLOR_ACCENT}; color: white;")
        self.btn_export.clicked.connect(self.accept)
        btn_box.addWidget(btn_cancel)
        btn_box.addWidget(self.btn_export)
        layout.addLayout(btn_box)

    def _on_browse(self):
        from PyQt6.QtWidgets import QFileDialog
        fmt = self.combo_format.currentData()
        ext_map = {
            "gcode": "Fichiers G-Code (*.gcode *.nc)",
            "rd": "Fichiers Ruida (*.rd)",
            "egv": "Fichiers Lihuiyu (*.egv)",
            "dxf": "Fichiers DXF (*.dxf)",
            "svg": "Fichiers SVG (*.svg)",
        }
        path, _ = QFileDialog.getSaveFileName(
            self, "Choisir la destination de l'export", self.edit_path.text(), ext_map.get(fmt, "Tous les fichiers (*.*)")
        )
        if path:
            self.edit_path.setText(path)

    def get_parameters(self) -> dict:
        return {
            "filepath": self.edit_path.text(),
            "format_type": self.combo_format.currentData(),
            "laser_power": self.spin_power.value(),
            "speed_mm_s": self.spin_speed.value(),
        }


class VariableTextMergeDialog(QDialog):
    """Wizard for importing CSV/Excel tables and generating merged variable text arrays."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("📊 Fusion Texte Variable & CSV/Excel")
        self.setMinimumWidth(560)
        self.setMinimumHeight(440)
        self.setModal(True)

        self._records = []

        layout = QVBoxLayout(self)

        # File Chooser
        file_layout = QHBoxLayout()
        self.edit_file = QLineEdit(self)
        self.edit_file.setPlaceholderText("Sélectionnez un fichier .csv ou .xlsx...")
        btn_browse = QPushButton("Parcourir CSV...", self)
        btn_browse.clicked.connect(self._on_browse_file)
        file_layout.addWidget(self.edit_file)
        file_layout.addWidget(btn_browse)
        layout.addLayout(file_layout)

        # Table Preview
        layout.addWidget(QLabel("Aperçu des Données :", self))
        self.table_preview = QTableWidget(self)
        self.table_preview.setColumnCount(0)
        self.table_preview.setRowCount(0)
        self.table_preview.horizontalHeader().setStretchLastSection(True)
        layout.addWidget(self.table_preview)

        # Configuration Form
        form = QFormLayout()

        self.edit_template = QLineEdit("{Nom} - Ref: {Matricule}", self)
        form.addRow("Modèle de Texte :", self.edit_template)

        grid_params = QHBoxLayout()
        self.spin_cols = QSpinBox(self)
        self.spin_cols.setRange(1, 100)
        self.spin_cols.setValue(3)

        self.spin_spacing_x = QDoubleSpinBox(self)
        self.spin_spacing_x.setRange(1.0, 1000.0)
        self.spin_spacing_x.setValue(50.0)
        self.spin_spacing_x.setSuffix(" mm")

        self.spin_spacing_y = QDoubleSpinBox(self)
        self.spin_spacing_y.setRange(1.0, 1000.0)
        self.spin_spacing_y.setValue(20.0)
        self.spin_spacing_y.setSuffix(" mm")

        grid_params.addWidget(QLabel("Colonnes :"))
        grid_params.addWidget(self.spin_cols)
        grid_params.addWidget(QLabel("Espacement X :"))
        grid_params.addWidget(self.spin_spacing_x)
        grid_params.addWidget(QLabel("Espacement Y :"))
        grid_params.addWidget(self.spin_spacing_y)

        form.addRow("Disposition en Grille :", grid_params)
        layout.addLayout(form)

        # Actions
        btn_box = QHBoxLayout()
        btn_cancel = QPushButton("Annuler", self)
        btn_cancel.clicked.connect(self.reject)
        self.btn_merge = QPushButton("✨ Fusionner et Insérer", self)
        self.btn_merge.setStyleSheet(f"font-weight: bold; background-color: {COLOR_ACCENT}; color: white;")
        self.btn_merge.clicked.connect(self.accept)
        btn_box.addWidget(btn_cancel)
        btn_box.addWidget(self.btn_merge)
        layout.addLayout(btn_box)

    def _on_browse_file(self):
        from PyQt6.QtWidgets import QFileDialog
        path, _ = QFileDialog.getOpenFileName(self, "Choisir un fichier de données", "", "Fichiers Tabulaires (*.csv *.txt *.xlsx)")
        if path:
            self.load_file(path)

    def load_file(self, filepath: str):
        from madgrav.tools.variable_text import parse_csv_or_excel
        self.edit_file.setText(filepath)
        self._records = parse_csv_or_excel(filepath)

        self.table_preview.clear()
        if not self._records:
            self.table_preview.setColumnCount(0)
            self.table_preview.setRowCount(0)
            return

        headers = list(self._records[0].keys())
        self.table_preview.setColumnCount(len(headers))
        self.table_preview.setHorizontalHeaderLabels(headers)
        self.table_preview.setRowCount(len(self._records))

        for row_idx, row_data in enumerate(self._records):
            for col_idx, col_name in enumerate(headers):
                val = row_data.get(col_name, "")
                self.table_preview.setItem(row_idx, col_idx, QTableWidgetItem(str(val)))

    def get_parameters(self) -> dict:
        return {
            "records": self._records,
            "template_pattern": self.edit_template.text(),
            "columns": self.spin_cols.value(),
            "spacing_x_mm": self.spin_spacing_x.value(),
            "spacing_y_mm": self.spin_spacing_y.value(),
        }


class HalftoneStudioDialog(QDialog):
    """Interactive Halftone, Wave, Spiral, and Stipple Photo Engraving Studio Dialog."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Studio Gravure Photo & Demi-Teintes")
        self.setMinimumSize(540, 520)
        self.current_image = None

        layout = QVBoxLayout(self)
        layout.setSpacing(10)

        # Header
        desc = QLabel(
            "<b>Studio Artistique & Demi-Teintes</b><br>"
            "Convertissez vos photos et images en trames vectorielles optimisées pour la gravure laser sur bois, ardoise, marbre ou métal.",
            self
        )
        desc.setWordWrap(True)
        layout.addWidget(desc)

        # Image picker
        file_grp = QGroupBox("1. Image Source", self)
        file_layout = QHBoxLayout(file_grp)
        self.btn_load_img = QPushButton("📁 Choisir une Image...", self)
        self.btn_load_img.clicked.connect(self._on_browse_image)
        self.lbl_img_info = QLabel("Aucune image sélectionnée (Utilise une mire de dégradé par défaut)", self)
        self.lbl_img_info.setStyleSheet("color: #94a3b8;")
        file_layout.addWidget(self.btn_load_img)
        file_layout.addWidget(self.lbl_img_info, 1)
        layout.addWidget(file_grp)

        # Method & Parameters
        params_grp = QGroupBox("2. Méthode & Paramètres Géométriques", self)
        grid = QGridLayout(params_grp)
        grid.setSpacing(8)

        grid.addWidget(QLabel("Méthode de Tramage :", self), 0, 0)
        self.combo_method = QComboBox(self)
        self.combo_method.addItems([
            "Points Demi-teintes (Halftone Dots)",
            "Lignes Ondulées (Wave Halftone)",
            "Spirale Continue (Spiral Halftone)",
            "Stippling Organique (Random Stipple)",
        ])
        grid.addWidget(self.combo_method, 0, 1)

        grid.addWidget(QLabel("Largeur / Hauteur (mm) :", self), 1, 0)
        dim_box = QHBoxLayout()
        self.spin_width = QDoubleSpinBox(self)
        self.spin_width.setRange(10.0, 1000.0)
        self.spin_width.setValue(80.0)
        self.spin_width.setSuffix(" mm")
        self.spin_height = QDoubleSpinBox(self)
        self.spin_height.setRange(10.0, 1000.0)
        self.spin_height.setValue(80.0)
        self.spin_height.setSuffix(" mm")
        dim_box.addWidget(self.spin_width)
        dim_box.addWidget(self.spin_height)
        grid.addLayout(dim_box, 1, 1)

        grid.addWidget(QLabel("Pas de Grille / Espacement :", self), 2, 0)
        self.spin_pitch = QDoubleSpinBox(self)
        self.spin_pitch.setRange(0.2, 20.0)
        self.spin_pitch.setValue(2.5)
        self.spin_pitch.setSingleStep(0.5)
        self.spin_pitch.setSuffix(" mm")
        grid.addWidget(self.spin_pitch, 2, 1)

        grid.addWidget(QLabel("Diamètre Min / Max (mm) :", self), 3, 0)
        dot_box = QHBoxLayout()
        self.spin_min_dot = QDoubleSpinBox(self)
        self.spin_min_dot.setRange(0.05, 5.0)
        self.spin_min_dot.setValue(0.2)
        self.spin_min_dot.setSuffix(" mm")
        self.spin_max_dot = QDoubleSpinBox(self)
        self.spin_max_dot.setRange(0.1, 15.0)
        self.spin_max_dot.setValue(2.2)
        self.spin_max_dot.setSuffix(" mm")
        dot_box.addWidget(self.spin_min_dot)
        dot_box.addWidget(self.spin_max_dot)
        grid.addLayout(dot_box, 3, 1)

        grid.addWidget(QLabel("Angle de Trame :", self), 4, 0)
        self.spin_angle = QDoubleSpinBox(self)
        self.spin_angle.setRange(0.0, 90.0)
        self.spin_angle.setValue(45.0)
        self.spin_angle.setSuffix(" °")
        grid.addWidget(self.spin_angle, 4, 1)

        grid.addWidget(QLabel("Contraste (-100 à +100) :", self), 5, 0)
        self.spin_contrast = QDoubleSpinBox(self)
        self.spin_contrast.setRange(-100.0, 100.0)
        self.spin_contrast.setValue(10.0)
        grid.addWidget(self.spin_contrast, 5, 1)

        self.check_invert = QCheckBox("Inverser le Négatif (Recommandé pour matières sombres : ardoise, acrylique noir)", self)
        grid.addWidget(self.check_invert, 6, 0, 1, 2)

        layout.addWidget(params_grp)

        # Action Buttons
        btn_box = QHBoxLayout()
        btn_cancel = QPushButton("Annuler", self)
        btn_cancel.clicked.connect(self.reject)
        self.btn_apply = QPushButton("✨ Générer & Insérer dans le Projet", self)
        self.btn_apply.setStyleSheet(f"font-weight: bold; background-color: {COLOR_ACCENT}; color: white;")
        self.btn_apply.clicked.connect(self._on_apply_clicked)
        btn_box.addWidget(btn_cancel)
        btn_box.addWidget(self.btn_apply)
        layout.addLayout(btn_box)

    def _on_browse_image(self):
        from PyQt6.QtWidgets import QFileDialog
        path, _ = QFileDialog.getOpenFileName(self, "Choisir une Image", "", "Images (*.png *.jpg *.jpeg *.bmp *.webp *.tiff)")
        if path:
            try:
                from PIL import Image
                self.current_image = Image.open(path)
                self.lbl_img_info.setText(f"✓ Image chargée : {path.split('/')[-1].split(chr(92))[-1]} ({self.current_image.width}x{self.current_image.height}px)")
                self.lbl_img_info.setStyleSheet("color: #4ade80; font-weight: bold;")
            except Exception as e:
                self.lbl_img_info.setText(f"Erreur : {e}")

    def _on_apply_clicked(self):
        self.apply_halftone()
        self.accept()

    def apply_halftone(self):
        from PIL import Image
        import numpy as np
        from madgrav.tools.halftone_studio import generate_halftone_job

        if self.current_image is None:
            # Create synthetic default gradient
            arr = np.tile(np.linspace(0, 255, 100, dtype=np.uint8), (100, 1))
            self.current_image = Image.fromarray(arr, mode="L")

        method_map = {
            0: "dots",
            1: "waves",
            2: "spiral",
            3: "stipple",
        }
        method = method_map.get(self.combo_method.currentIndex(), "dots")

        svg_content = generate_halftone_job(
            image=self.current_image,
            method=method,
            width_mm=self.spin_width.value(),
            height_mm=self.spin_height.value(),
            pitch_mm=self.spin_pitch.value(),
            min_dot_mm=self.spin_min_dot.value(),
            max_dot_mm=self.spin_max_dot.value(),
            angle_deg=self.spin_angle.value(),
            contrast=self.spin_contrast.value(),
            invert=self.check_invert.isChecked(),
        )

        parent = self.parent()
        if parent and hasattr(parent, "context") and hasattr(parent.context, "load"):
            import tempfile, os
            with tempfile.NamedTemporaryFile(suffix=".svg", delete=False, mode="w", encoding="utf-8") as tf:
                tf.write(svg_content)
                temp_path = tf.name
            try:
                parent.context.load(temp_path)
                if hasattr(parent, "canvas") and hasattr(parent.canvas, "refresh_scene"):
                    parent.canvas.refresh_scene()
            finally:
                if os.path.exists(temp_path):
                    os.remove(temp_path)


class TopoMapDialog(QDialog):
    """Dialog for generating 3D multi-layer wooden/acrylic topographic contour maps."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Générateur de Cartes Topographiques 3D")
        self.setMinimumSize(480, 420)

        layout = QVBoxLayout(self)
        layout.setSpacing(10)

        desc = QLabel(
            "<b>Générateur de Cartes Topographiques 3D Multi-Couches</b><br>"
            "Générez automatiquement les calques de découpe et de gravure pour vos tableaux en relief empilables en bois ou acrylique.",
            self
        )
        desc.setWordWrap(True)
        layout.addWidget(desc)

        grp = QGroupBox("Paramètres de la Carte", self)
        grid = QGridLayout(grp)

        grid.addWidget(QLabel("Modèle de Relief :", self), 0, 0)
        self.combo_preset = QComboBox(self)
        self.combo_preset.addItems(["Île (Island)", "Montagne (Mountain)", "Canyon / Rivière", "Volcan (Volcano)", "Bassin / Lac"])
        grid.addWidget(self.combo_preset, 0, 1)

        grid.addWidget(QLabel("Dimensions (Largeur x Hauteur) :", self), 1, 0)
        dim_box = QHBoxLayout()
        self.spin_w = QDoubleSpinBox(self)
        self.spin_w.setRange(20.0, 1000.0)
        self.spin_w.setValue(120.0)
        self.spin_w.setSuffix(" mm")
        self.spin_h = QDoubleSpinBox(self)
        self.spin_h.setRange(20.0, 1000.0)
        self.spin_h.setValue(120.0)
        self.spin_h.setSuffix(" mm")
        dim_box.addWidget(self.spin_w)
        dim_box.addWidget(self.spin_h)
        grid.addLayout(dim_box, 1, 1)

        grid.addWidget(QLabel("Nombre de Calques de Découpe :", self), 2, 0)
        self.spin_layers = QSpinBox(self)
        self.spin_layers.setRange(2, 16)
        self.spin_layers.setValue(5)
        self.spin_layers.setSuffix(" couches")
        grid.addWidget(self.spin_layers, 2, 1)

        grid.addWidget(QLabel("Trous de Calage (Dowel Pins) :", self), 3, 0)
        pin_box = QHBoxLayout()
        self.check_pins = QCheckBox("Activer les 4 pions d'assemblage", self)
        self.check_pins.setChecked(True)
        self.spin_pin_diam = QDoubleSpinBox(self)
        self.spin_pin_diam.setRange(1.0, 10.0)
        self.spin_pin_diam.setValue(3.0)
        self.spin_pin_diam.setSuffix(" mm")
        pin_box.addWidget(self.check_pins)
        pin_box.addWidget(self.spin_pin_diam)
        grid.addLayout(pin_box, 3, 1)

        layout.addWidget(grp)

        # Buttons
        btn_box = QHBoxLayout()
        btn_cancel = QPushButton("Annuler", self)
        btn_cancel.clicked.connect(self.reject)
        self.btn_apply = QPushButton("🗺️ Générer les Calques 3D", self)
        self.btn_apply.setStyleSheet(f"font-weight: bold; background-color: {COLOR_ACCENT}; color: white;")
        self.btn_apply.clicked.connect(self._on_apply_clicked)
        btn_box.addWidget(btn_cancel)
        btn_box.addWidget(self.btn_apply)
        layout.addLayout(btn_box)

    def _on_apply_clicked(self):
        self.apply_topo_map()
        self.accept()

    def apply_topo_map(self):
        from madgrav.tools.topo_map_generator import topo_map_to_svg_layers
        preset_keys = ["island", "mountain", "canyon", "volcano", "lake"]
        preset = preset_keys[self.combo_preset.currentIndex()]

        svg_dict = topo_map_to_svg_layers(
            preset=preset,
            width_mm=self.spin_w.value(),
            height_mm=self.spin_h.value(),
            layers_count=self.spin_layers.value(),
            pin_diameter_mm=self.spin_pin_diam.value() if self.check_pins.isChecked() else 0.0,
        )

        parent = self.parent()
        if parent and hasattr(parent, "context") and hasattr(parent.context, "load"):
            import tempfile, os
            for layer_name, svg_content in svg_dict.items():
                with tempfile.NamedTemporaryFile(suffix=".svg", delete=False, mode="w", encoding="utf-8") as tf:
                    tf.write(svg_content)
                    temp_path = tf.name
                try:
                    parent.context.load(temp_path)
                finally:
                    if os.path.exists(temp_path):
                        os.remove(temp_path)
            if hasattr(parent, "canvas") and hasattr(parent.canvas, "refresh_scene"):
                parent.canvas.refresh_scene()


class MandalaDialog(QDialog):
    """Dialog for generating parametric radial mandalas and sacred geometry rosettes."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Générateur de Mandalas & Rosaces")
        self.setMinimumSize(460, 380)

        layout = QVBoxLayout(self)
        layout.setSpacing(10)

        desc = QLabel(
            "<b>Générateur de Mandalas & Géométrie Sacrée</b><br>"
            "Créez des rosaces vectorielles paramétriques avec symétrie radiale parfaite prêtes pour la découpe et la gravure laser.",
            self
        )
        desc.setWordWrap(True)
        layout.addWidget(desc)

        grp = QGroupBox("Paramètres de Symétrie & Style", self)
        grid = QGridLayout(grp)

        grid.addWidget(QLabel("Symétrie Radiale (Branches) :", self), 0, 0)
        self.spin_symmetry = QSpinBox(self)
        self.spin_symmetry.setRange(3, 48)
        self.spin_symmetry.setValue(8)
        self.spin_symmetry.setSuffix(" pans")
        grid.addWidget(self.spin_symmetry, 0, 1)

        grid.addWidget(QLabel("Style du Motif :", self), 1, 0)
        self.combo_style = QComboBox(self)
        self.combo_style.addItems(["Floral (Pétales courbes)", "Étoilé (Starburst)", "Géométrie Sacrée (Seed of Life)", "Rosace Gothique (Trefoil)"])
        grid.addWidget(self.combo_style, 1, 1)

        grid.addWidget(QLabel("Rayon Extérieur (mm) :", self), 2, 0)
        self.spin_outer_r = QDoubleSpinBox(self)
        self.spin_outer_r.setRange(5.0, 500.0)
        self.spin_outer_r.setValue(50.0)
        self.spin_outer_r.setSuffix(" mm")
        grid.addWidget(self.spin_outer_r, 2, 1)

        grid.addWidget(QLabel("Rayon Intérieur (mm) :", self), 3, 0)
        self.spin_inner_r = QDoubleSpinBox(self)
        self.spin_inner_r.setRange(1.0, 100.0)
        self.spin_inner_r.setValue(6.0)
        self.spin_inner_r.setSuffix(" mm")
        grid.addWidget(self.spin_inner_r, 3, 1)

        grid.addWidget(QLabel("Nombre d'Anneaux Concentriques :", self), 4, 0)
        self.spin_rings = QSpinBox(self)
        self.spin_rings.setRange(1, 10)
        self.spin_rings.setValue(4)
        grid.addWidget(self.spin_rings, 4, 1)

        layout.addWidget(grp)

        # Buttons
        btn_box = QHBoxLayout()
        btn_cancel = QPushButton("Annuler", self)
        btn_cancel.clicked.connect(self.reject)
        self.btn_apply = QPushButton("🌸 Insérer le Mandala", self)
        self.btn_apply.setStyleSheet(f"font-weight: bold; background-color: {COLOR_ACCENT}; color: white;")
        self.btn_apply.clicked.connect(self._on_apply_clicked)
        btn_box.addWidget(btn_cancel)
        btn_box.addWidget(self.btn_apply)
        layout.addLayout(btn_box)

    def _on_apply_clicked(self):
        self.apply_mandala()
        self.accept()

    def apply_mandala(self):
        from madgrav.tools.mandala_generator import generate_mandala_svg
        style_keys = ["floral", "starburst", "sacred", "gothic"]
        style = style_keys[self.combo_style.currentIndex()]

        svg_content = generate_mandala_svg(
            symmetry=self.spin_symmetry.value(),
            outer_radius_mm=self.spin_outer_r.value(),
            inner_radius_mm=self.spin_inner_r.value(),
            rings=self.spin_rings.value(),
            style=style,
        )

        parent = self.parent()
        if parent and hasattr(parent, "context") and hasattr(parent.context, "load"):
            import tempfile, os
            with tempfile.NamedTemporaryFile(suffix=".svg", delete=False, mode="w", encoding="utf-8") as tf:
                tf.write(svg_content)
                temp_path = tf.name
            try:
                parent.context.load(temp_path)
                if hasattr(parent, "canvas") and hasattr(parent.canvas, "refresh_scene"):
                    parent.canvas.refresh_scene()
            finally:
                if os.path.exists(temp_path):
                    os.remove(temp_path)


def _generate_qr_pixmap(url: str, size: int = 180) -> QPixmap:
    """Generate a high-contrast, scannable QPixmap for a URL."""
    try:
        import qrcode
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_M,
            box_size=8,
            border=2,
        )
        qr.add_data(url)
        qr.make(fit=True)
        matrix = qr.get_matrix()
        w = len(matrix[0])
        h = len(matrix)
        img = QImage(w, h, QImage.Format.Format_RGB32)
        for y in range(h):
            for x in range(w):
                img.setPixel(x, y, qRgb(0, 0, 0) if matrix[y][x] else qRgb(255, 255, 255))
        scaled = img.scaled(
            size, size,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.FastTransformation,
        )
        return QPixmap.fromImage(scaled)
    except Exception:
        # Graceful fallback: white box with error hint
        pix = QPixmap(size, size)
        pix.fill(Qt.GlobalColor.white)
        return pix


class WebRemoteQrDialog(QDialog):
    """Dialog displaying local IP URL and QR Code for Mobile Web Remote."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Télécommande Mobile Web")
        self.setMinimumWidth(420)

        layout = QVBoxLayout(self)
        layout.setSpacing(12)

        title = QLabel("📱 <b>Télécommande Mobile Laser sans Fil</b>", self)
        layout.addWidget(title)

        desc = QLabel(
            "Pilotez votre machine laser directement depuis votre smartphone ou tablette (Android/iOS) connecté au Wi-Fi de l'atelier.",
            self
        )
        desc.setWordWrap(True)
        layout.addWidget(desc)

        # Detect IP
        local_ip = "127.0.0.1"
        try:
            import socket
            hostname = socket.gethostname()
            ips = socket.gethostbyname_ex(hostname)[2]
            for ip in ips:
                if not ip.startswith("127."):
                    local_ip = ip
                    break
        except Exception:
            pass

        port = 8080
        if parent and hasattr(parent, "context"):
            web_mod = parent.context.root.match("module/WebServer")
            if web_mod:
                port = getattr(web_mod, "actual_port", 8080)

        url = f"http://{local_ip}:{port}"

        url_box = QHBoxLayout()
        self.url_edit = QLineEdit(url, self)
        self.url_edit.setReadOnly(True)
        btn_copy = QPushButton("📋 Copier", self)
        btn_copy.clicked.connect(lambda: QApplication.clipboard().setText(self.url_edit.text()))
        url_box.addWidget(self.url_edit)
        url_box.addWidget(btn_copy)
        layout.addLayout(url_box)

        # QR Code Card
        qr_card = QGroupBox("Connexion Rapide par Flashcode (QR Code)", self)
        qr_layout = QVBoxLayout(qr_card)
        qr_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.qr_label = QLabel(self)
        self.qr_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.qr_label.setStyleSheet(
            "background-color: #ffffff; padding: 10px; border-radius: 8px; border: 1px solid #475569;"
        )
        pix = _generate_qr_pixmap(url, size=180)
        self.qr_label.setPixmap(pix)
        qr_layout.addWidget(self.qr_label)

        sub_lbl = QLabel(
            "Scannez ce QR Code avec l'appareil photo de votre smartphone pour ouvrir la télécommande.",
            self
        )
        sub_lbl.setWordWrap(True)
        sub_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        sub_lbl.setStyleSheet(f"color: {COLOR_MUTED}; font-size: 11px; margin-top: 4px;")
        qr_layout.addWidget(sub_lbl)

        layout.addWidget(qr_card)

        # Buttons
        btn_box = QHBoxLayout()
        btn_browser = QPushButton("🌐 Ouvrir dans le Navigateur", self)
        btn_browser.clicked.connect(self._open_browser)
        btn_close = QPushButton("Fermer", self)
        btn_close.clicked.connect(self.accept)
        btn_box.addWidget(btn_browser)
        btn_box.addWidget(btn_close)
        layout.addLayout(btn_box)

    def _open_browser(self):
        import webbrowser
        webbrowser.open(self.url_edit.text())


# =========================================================================
# 1. Maker & Inlay Suite
# =========================================================================

class InlayWizardDialog(QDialog):
    """Assistant Marqueterie & Incrustation Laser avec compensation de kerf."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("🧩 Assistant Marqueterie & Incrustation (Inlay Wizard)")
        self.setMinimumWidth(480)

        layout = QVBoxLayout(self)
        layout.setSpacing(12)

        header = QLabel("<b>Assistant d'Incrustation & Marqueterie Laser</b>", self)
        layout.addWidget(header)

        desc = QLabel(
            "Calcule et génère automatiquement les décalages de kerf pour les pièces mâles "
            "(incrustations) et femelles (cavités/poches) avec compensation du jeu mécanique.",
            self
        )
        desc.setWordWrap(True)
        layout.addWidget(desc)

        form = QFormLayout()
        self.spin_kerf = QDoubleSpinBox(self)
        self.spin_kerf.setRange(0.01, 2.0)
        self.spin_kerf.setSingleStep(0.01)
        self.spin_kerf.setValue(0.15)
        self.spin_kerf.setSuffix(" mm")
        form.addRow("Largeur du trait laser (Kerf) :", self.spin_kerf)

        self.spin_clearance = QDoubleSpinBox(self)
        self.spin_clearance.setRange(0.0, 1.0)
        self.spin_clearance.setSingleStep(0.01)
        self.spin_clearance.setValue(0.05)
        self.spin_clearance.setSuffix(" mm")
        form.addRow("Jeu d'ajustement (Clearance) :", self.spin_clearance)

        self.combo_mode = QComboBox(self)
        self.combo_mode.addItems([
            "Équilibré (Mâle +0.05mm, Femelle -0.05mm)",
            "Mâle seul (Agrandir la pièce incrustée)",
            "Femelle seule (Rétrécir la cavité réceptrice)",
        ])
        form.addRow("Stratégie de compensation :", self.combo_mode)

        self.combo_material = QComboBox(self)
        self.combo_material.addItems(["Bois massif / Placage", "Acrylique (PMMA)", "Cuir", "MDF"])
        form.addRow("Matériau cible :", self.combo_material)

        layout.addLayout(form)

        # Options
        self.chk_create_both = QCheckBox("Générer les deux tracés (Mâle & Femelle séparés par calque)", self)
        self.chk_create_both.setChecked(True)
        layout.addWidget(self.chk_create_both)

        # Buttons
        btn_box = QHBoxLayout()
        btn_generate = QPushButton("✨ Générer l'Incrustation", self)
        btn_generate.setStyleSheet(f"background-color: {COLOR_ACCENT}; color: white; font-weight: bold; padding: 6px;")
        btn_generate.clicked.connect(self.accept)
        btn_cancel = QPushButton("Annuler", self)
        btn_cancel.clicked.connect(self.reject)
        btn_box.addWidget(btn_generate)
        btn_box.addWidget(btn_cancel)
        layout.addLayout(btn_box)


class TSlotBoxDialog(QDialog):
    """Générateur de Boîte à écrous captifs (T-Slot)."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("🔩 Générateur de Boîte à Écrous Captifs (T-Slot)")
        self.setMinimumWidth(460)

        layout = QVBoxLayout(self)
        layout.setSpacing(12)

        header = QLabel("<b>Générateur Paramétrique de Boîte Démontable T-Slot</b>", self)
        layout.addWidget(header)

        form = QFormLayout()
        self.spin_w = QDoubleSpinBox(self)
        self.spin_w.setRange(20.0, 1000.0)
        self.spin_w.setValue(100.0)
        self.spin_w.setSuffix(" mm")
        form.addRow("Largeur (X) :", self.spin_w)

        self.spin_h = QDoubleSpinBox(self)
        self.spin_h.setRange(20.0, 1000.0)
        self.spin_h.setValue(80.0)
        self.spin_h.setSuffix(" mm")
        form.addRow("Hauteur (Y) :", self.spin_h)

        self.spin_d = QDoubleSpinBox(self)
        self.spin_d.setRange(20.0, 1000.0)
        self.spin_d.setValue(60.0)
        self.spin_d.setSuffix(" mm")
        form.addRow("Profondeur (Z) :", self.spin_d)

        self.spin_thick = QDoubleSpinBox(self)
        self.spin_thick.setRange(1.0, 30.0)
        self.spin_thick.setValue(3.0)
        self.spin_thick.setSuffix(" mm")
        form.addRow("Épaisseur matière :", self.spin_thick)

        self.combo_hardware = QComboBox(self)
        self.combo_hardware.addItems(["M3 (Vis Ø3mm, Écrou 5.5mm)", "M4 (Vis Ø4mm, Écrou 7.0mm)", "M5 (Vis Ø5mm, Écrou 8.0mm)"])
        form.addRow("Quincaillerie :", self.combo_hardware)

        layout.addLayout(form)

        btn_box = QHBoxLayout()
        btn_ok = QPushButton("📐 Générer les 6 Panneaux", self)
        btn_ok.setStyleSheet(f"background-color: {COLOR_ACCENT}; color: white; font-weight: bold; padding: 6px;")
        btn_ok.clicked.connect(self.accept)
        btn_cancel = QPushButton("Annuler", self)
        btn_cancel.clicked.connect(self.reject)
        btn_box.addWidget(btn_ok)
        btn_box.addWidget(btn_cancel)
        layout.addLayout(btn_box)


# =========================================================================
# 2. Vision & Smart Alignment Suite
# =========================================================================

class ScrapFinderDialog(QDialog):
    """Détection automatique des chutes et zones de matière exploitables."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("🔍 Détecteur de Chutes & Retailles (Scrap Finder)")
        self.setMinimumWidth(500)

        layout = QVBoxLayout(self)
        layout.setSpacing(12)

        header = QLabel("<b>Détection Automatique des Zones Libres (Scrap Finder)</b>", self)
        layout.addWidget(header)

        desc = QLabel(
            "Analyse l'image du plateau ou les zones déjà découpées pour identifier "
            "les rectangles et polygones de matière encore vierges pour vos découpes.",
            self
        )
        desc.setWordWrap(True)
        layout.addWidget(desc)

        form = QFormLayout()
        self.spin_min_area = QDoubleSpinBox(self)
        self.spin_min_area.setRange(10.0, 100000.0)
        self.spin_min_area.setValue(200.0)
        self.spin_min_area.setSuffix(" mm²")
        form.addRow("Surface minimale utilisable :", self.spin_min_area)

        self.spin_margin = QDoubleSpinBox(self)
        self.spin_margin.setRange(0.0, 50.0)
        self.spin_margin.setValue(5.0)
        self.spin_margin.setSuffix(" mm")
        form.addRow("Marge de sécurité bords :", self.spin_margin)
        layout.addLayout(form)

        # Zones preview table
        self.table = QTableWidget(3, 4, self)
        self.table.setHorizontalHeaderLabels(["Zone", "X (mm)", "Y (mm)", "Surface"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.setItem(0, 0, QTableWidgetItem("Zone #1"))
        self.table.setItem(0, 1, QTableWidgetItem("15.0"))
        self.table.setItem(0, 2, QTableWidgetItem("20.0"))
        self.table.setItem(0, 3, QTableWidgetItem("1200 mm²"))
        layout.addWidget(self.table)

        btn_box = QHBoxLayout()
        btn_detect = QPushButton("📷 Scanner le Plateau", self)
        btn_detect.clicked.connect(self._scan_plateau)
        btn_apply = QPushButton("✅ Insérer comme Guides", self)
        btn_apply.setStyleSheet(f"background-color: {COLOR_ACCENT}; color: white; font-weight: bold;")
        btn_apply.clicked.connect(self.accept)
        btn_close = QPushButton("Fermer", self)
        btn_close.clicked.connect(self.reject)

        btn_box.addWidget(btn_detect)
        btn_box.addWidget(btn_apply)
        btn_box.addWidget(btn_close)
        layout.addLayout(btn_box)

    def _scan_plateau(self):
        # Dummy mock update for table
        pass


class PrintAndCutDialog(QDialog):
    """Assistant Calage Impression / Découpe (Print & Cut Fiducial Registration)."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("🎯 Calage Repères d'Impression (Print & Cut)")
        self.setMinimumWidth(520)

        layout = QVBoxLayout(self)
        layout.setSpacing(12)

        header = QLabel("<b>Alignement & Recalage sur Repères Fiduciels</b>", self)
        layout.addWidget(header)

        desc = QLabel(
            "Corrige l'alignement, la rotation, l'échelle et la déformation de votre découpe "
            "pour correspondre exactement à une impression papier/adhésif préexistante.",
            self
        )
        desc.setWordWrap(True)
        layout.addWidget(desc)

        form = QFormLayout()
        self.combo_mode = QComboBox(self)
        self.combo_mode.addItems(["2 Repères (Translation + Rotation + Échelle)", "4 Repères (Déformation Homographique 2D)"])
        form.addRow("Méthode de calage :", self.combo_mode)

        layout.addLayout(form)

        # Points setup table
        self.table = QTableWidget(2, 4, self)
        self.table.setHorizontalHeaderLabels(["Repère", "Fichier X,Y", "Laser X,Y", "Statut"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.setItem(0, 0, QTableWidgetItem("Mire #1"))
        self.table.setItem(0, 1, QTableWidgetItem("10.0, 10.0"))
        self.table.setItem(0, 2, QTableWidgetItem("12.4, 9.8"))
        self.table.setItem(0, 3, QTableWidgetItem("Calibré"))
        self.table.setItem(1, 0, QTableWidgetItem("Mire #2"))
        self.table.setItem(1, 1, QTableWidgetItem("200.0, 10.0"))
        self.table.setItem(1, 2, QTableWidgetItem("201.8, 11.2"))
        self.table.setItem(1, 3, QTableWidgetItem("Calibré"))
        layout.addWidget(self.table)

        btn_box = QHBoxLayout()
        btn_apply = QPushButton("🚀 Appliquer la Transformation", self)
        btn_apply.setStyleSheet(f"background-color: {COLOR_ACCENT}; color: white; font-weight: bold;")
        btn_apply.clicked.connect(self.accept)
        btn_cancel = QPushButton("Annuler", self)
        btn_cancel.clicked.connect(self.reject)
        btn_box.addWidget(btn_apply)
        btn_box.addWidget(btn_cancel)
        layout.addLayout(btn_box)


# =========================================================================
# 3. Pro Optimization & Test Matrix Suite
# =========================================================================

class TrueShapeNestingDialog(QDialog):
    """Imbrication 2D Avancée Multi-Pièces (True-Shape 2D Nesting)."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("🧩 Imbrication 2D Multi-Pièces (True-Shape Nesting)")
        self.setMinimumWidth(500)

        layout = QVBoxLayout(self)
        layout.setSpacing(12)

        header = QLabel("<b>Optimisation & Imbrication 2D de Formes Multiples</b>", self)
        layout.addWidget(header)

        form = QFormLayout()
        self.spin_sheet_w = QDoubleSpinBox(self)
        self.spin_sheet_w.setRange(50.0, 3000.0)
        self.spin_sheet_w.setValue(400.0)
        self.spin_sheet_w.setSuffix(" mm")
        form.addRow("Largeur feuille (X) :", self.spin_sheet_w)

        self.spin_sheet_h = QDoubleSpinBox(self)
        self.spin_sheet_h.setRange(50.0, 3000.0)
        self.spin_sheet_h.setValue(300.0)
        self.spin_sheet_h.setSuffix(" mm")
        form.addRow("Hauteur feuille (Y) :", self.spin_sheet_h)

        self.spin_spacing = QDoubleSpinBox(self)
        self.spin_spacing.setRange(0.1, 50.0)
        self.spin_spacing.setValue(2.0)
        self.spin_spacing.setSuffix(" mm")
        form.addRow("Espacement entre pièces :", self.spin_spacing)

        self.combo_rot = QComboBox(self)
        self.combo_rot.addItems(["Rotations 0° et 90° (Standard)", "Rotations 45°", "Toutes rotations (15°)", "Fixe (0° sans rotation)"])
        form.addRow("Liberté de rotation :", self.combo_rot)

        layout.addLayout(form)

        # Status summary
        self.lbl_efficiency = QLabel("<b>Rendement estimé :</b> ~84.5% (12 pièces placées, 0 non placées)", self)
        self.lbl_efficiency.setStyleSheet(f"color: {COLOR_SUCCESS}; padding: 6px;")
        layout.addWidget(self.lbl_efficiency)

        btn_box = QHBoxLayout()
        btn_pack = QPushButton("⚡ Optimiser l'Agencement", self)
        btn_pack.setStyleSheet(f"background-color: {COLOR_ACCENT}; color: white; font-weight: bold;")
        btn_pack.clicked.connect(self.accept)
        btn_cancel = QPushButton("Annuler", self)
        btn_cancel.clicked.connect(self.reject)
        btn_box.addWidget(btn_pack)
        btn_box.addWidget(btn_cancel)
        layout.addLayout(btn_box)


class MaterialMatrixTestDialog(QDialog):
    """Générateur de Grille de Test Matériaux Pro (Vitesse vs Puissance)."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("🎯 Matrice de Test Matériaux Pro (Power vs Speed)")
        self.setMinimumWidth(500)

        layout = QVBoxLayout(self)
        layout.setSpacing(12)

        header = QLabel("<b>Générateur Automatique de Matrice de Test</b>", self)
        layout.addWidget(header)

        form = QFormLayout()
        self.spin_cols = QSpinBox(self)
        self.spin_cols.setRange(2, 12)
        self.spin_cols.setValue(5)
        form.addRow("Nombre de colonnes (Vitesses) :", self.spin_cols)

        self.spin_rows = QSpinBox(self)
        self.spin_rows.setRange(2, 12)
        self.spin_rows.setValue(5)
        form.addRow("Nombre de lignes (Puissances) :", self.spin_rows)

        self.spin_cell_size = QDoubleSpinBox(self)
        self.spin_cell_size.setRange(3.0, 50.0)
        self.spin_cell_size.setValue(10.0)
        self.spin_cell_size.setSuffix(" mm")
        form.addRow("Taille d'une case :", self.spin_cell_size)

        self.chk_labels = QCheckBox("Graver les étiquettes textuelles (% et mm/s)", self)
        self.chk_labels.setChecked(True)
        layout.addWidget(self.chk_labels)

        layout.addLayout(form)

        btn_box = QHBoxLayout()
        btn_gen = QPushButton("🏁 Générer la Grille", self)
        btn_gen.setStyleSheet(f"background-color: {COLOR_ACCENT}; color: white; font-weight: bold;")
        btn_gen.clicked.connect(self.accept)
        btn_cancel = QPushButton("Annuler", self)
        btn_cancel.clicked.connect(self.reject)
        btn_box.addWidget(btn_gen)
        btn_box.addWidget(btn_cancel)
        layout.addLayout(btn_box)


# =========================================================================
# 4. Interactive Workflow & Workshop Suite
# =========================================================================

class LaserTimelineDialog(QDialog):
    """Visualiseur Temporel d'Accélération et Profil d'Exécution."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("⏱️ Visualiseur Temporel & Profil d'Accélération")
        self.setMinimumWidth(540)

        layout = QVBoxLayout(self)
        layout.setSpacing(12)

        header = QLabel("<b>Simulation Temporelle & Accélération Machine</b>", self)
        layout.addWidget(header)

        # Stats summary card
        card = QGroupBox("Estimation Réaliste du Job (Profil Trapézoïdal)", self)
        card_layout = QGridLayout(card)
        card_layout.addWidget(QLabel("Temps Découpe (G1) :"), 0, 0)
        card_layout.addWidget(QLabel("<b>3 min 42 s</b>"), 0, 1)
        card_layout.addWidget(QLabel("Temps Mouvements Rapides (G0) :"), 1, 0)
        card_layout.addWidget(QLabel("<b>38 s</b>"), 1, 1)
        card_layout.addWidget(QLabel("Temps Total Estimé :"), 2, 0)
        lbl_tot = QLabel("<b>4 min 20 s</b>")
        lbl_tot.setStyleSheet(f"color: {COLOR_ACCENT}; font-size: 14px;")
        card_layout.addWidget(lbl_tot, 2, 1)
        layout.addWidget(card)

        form = QFormLayout()
        self.spin_accel = QDoubleSpinBox(self)
        self.spin_accel.setRange(100.0, 50000.0)
        self.spin_accel.setValue(3000.0)
        self.spin_accel.setSuffix(" mm/s²")
        form.addRow("Accélération machine :", self.spin_accel)

        self.spin_rapid = QDoubleSpinBox(self)
        self.spin_rapid.setRange(10.0, 2000.0)
        self.spin_rapid.setValue(200.0)
        self.spin_rapid.setSuffix(" mm/s")
        form.addRow("Vitesse déplacements rapides :", self.spin_rapid)
        layout.addLayout(form)

        btn_box = QHBoxLayout()
        btn_close = QPushButton("Fermer", self)
        btn_close.clicked.connect(self.accept)
        btn_box.addWidget(btn_close)
        layout.addLayout(btn_box)


class WorkshopKioskWindow(QMainWindow):
    """Mode Plein Écran Tactile pour Opérateur d'Atelier (Workshop Kiosk Mode)."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("🖥️ MadGrav Atelier - Mode Tactile Opérateur")
        self.setMinimumSize(800, 500)

        # Using a main widget container
        from PyQt6.QtWidgets import QWidget
        central = QWidget(self)
        self.setCentralWidget(central)

        layout = QVBoxLayout(central)
        layout.setSpacing(16)
        layout.setContentsMargins(20, 20, 20, 20)

        # Header status
        header = QHBoxLayout()
        title = QLabel("<h2>🛠️ MADGRAV ATELIER TACTILE</h2>", self)
        self.lbl_status = QLabel("🟢 MACHINE PRÊTE", self)
        self.lbl_status.setStyleSheet(
            f"background-color: {COLOR_SUCCESS}; color: white; padding: 8px 16px; border-radius: 6px; font-weight: bold;"
        )
        header.addWidget(title)
        header.addStretch()
        header.addWidget(self.lbl_status)
        layout.addLayout(header)

        # Big Progress Bar
        self.progress = QProgressBar(self)
        self.progress.setValue(0)
        self.progress.setFixedHeight(30)
        self.progress.setTextVisible(True)
        layout.addWidget(self.progress)

        # Big Touch Action Buttons Grid
        btn_grid = QGridLayout()
        btn_grid.setSpacing(12)

        self.btn_load = QPushButton("📁 Charger Fichier\n(Récent)", self)
        self.btn_load.setMinimumHeight(80)
        self.btn_load.setStyleSheet("font-size: 16px; font-weight: bold;")

        self.btn_frame = QPushButton("📐 Cadrer\n(Frame)", self)
        self.btn_frame.setMinimumHeight(80)
        self.btn_frame.setStyleSheet(f"font-size: 16px; font-weight: bold; background-color: {COLOR_PURPLE}; color: white;")

        self.btn_home = QPushButton("🏠 Origine\n(Home)", self)
        self.btn_home.setMinimumHeight(80)
        self.btn_home.setStyleSheet("font-size: 16px; font-weight: bold;")

        self.btn_start = QPushButton("▶ DÉPART\n(Start Job)", self)
        self.btn_start.setMinimumHeight(80)
        self.btn_start.setStyleSheet(f"font-size: 18px; font-weight: bold; background-color: {COLOR_ACCENT}; color: white;")

        self.btn_pause = QPushButton("⏸ Pause", self)
        self.btn_pause.setMinimumHeight(80)
        self.btn_pause.setStyleSheet(f"font-size: 16px; font-weight: bold; background-color: {COLOR_WARNING}; color: black;")

        self.btn_stop = QPushButton("🛑 ARRÊT D'URGENCE\n(E-STOP)", self)
        self.btn_stop.setMinimumHeight(80)
        self.btn_stop.setStyleSheet("font-size: 18px; font-weight: bold; background-color: #ef4444; color: white;")

        btn_grid.addWidget(self.btn_load, 0, 0)
        btn_grid.addWidget(self.btn_frame, 0, 1)
        btn_grid.addWidget(self.btn_home, 0, 2)
        btn_grid.addWidget(self.btn_start, 1, 0)
        btn_grid.addWidget(self.btn_pause, 1, 1)
        btn_grid.addWidget(self.btn_stop, 1, 2)

        layout.addLayout(btn_grid)

        # Exit Kiosk mode button
        btn_exit = QPushButton("❌ Quitter le Mode Atelier (Retour interface complète)", self)
        btn_exit.clicked.connect(self.close)
        layout.addWidget(btn_exit)
