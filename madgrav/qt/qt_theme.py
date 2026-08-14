"""
Modern Dark QSS Theme Stylesheet for MadGrav PyQt6 GUI.
"""

# Shared semantic action colors -- one canonical value per meaning
# (matches the existing #0A84FF accent already used ~40x throughout
# MODERN_DARK_QSS/MODERN_LIGHT_QSS below). Several call sites across
# qt_main.py used to pick their own similar-but-not-identical shade for
# the same "success"/"warning"/"danger" meaning (three different greens
# for "start"/"connected", three different oranges for "warning", two
# different reds for "stop"/"no device") -- reusing these constants
# instead keeps every occurrence of a given meaning visually identical.
COLOR_ACCENT = "#0A84FF"
COLOR_SUCCESS = "#30D158"
COLOR_WARNING = "#FF9F0A"
COLOR_DANGER = "#FF3B30"
COLOR_PURPLE = "#BF5AF2"
COLOR_MUTED = "#8E8E93"


def build_app_icon(size: int = 256):
    """Renders the MadGrav monogram badge (the same design as the classic
    wx UI's window icon, madgrav/gui/icons.py: icon_madgrav) natively in
    Qt, so the Qt window/taskbar carries the same branding instead of the
    generic default icon. The source there is expressed as SVG path
    strings including elliptical-arc commands, but the two "arcs" both
    just trace full circles (4 quarter-arcs back to the start) -- so this
    reproduces the exact same shapes with plain QPainter primitives
    (drawEllipse/QPainterPath) instead of pulling in an SVG-arc parser or
    a wx.Bitmap->QImage conversion for a one-off icon.
    """
    from PyQt6.QtCore import QPointF, Qt
    from PyQt6.QtGui import QBrush, QColor, QIcon, QPainter, QPainterPath, QPen, QPixmap

    design_size = 200.0
    pixmap = QPixmap(size, size)
    pixmap.fill(QColor(0, 0, 0, 0))
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    painter.scale(size / design_size, size / design_size)

    painter.setPen(Qt.PenStyle.NoPen)

    painter.setBrush(QBrush(QColor("#111111")))  # outer ring
    painter.drawEllipse(QPointF(100, 100), 98, 98)

    painter.setBrush(QBrush(QColor("#1f3a5f")))  # inner disc
    painter.drawEllipse(QPointF(100, 100), 90, 90)

    m_path = QPainterPath()  # bold "M" monogram
    m_path.moveTo(55, 145)
    m_path.lineTo(55, 60)
    m_path.lineTo(73, 60)
    m_path.lineTo(100, 108)
    m_path.lineTo(127, 60)
    m_path.lineTo(145, 60)
    m_path.lineTo(145, 145)
    m_path.closeSubpath()
    painter.setBrush(QBrush(QColor("white")))
    painter.drawPath(m_path)

    spark_path = QPainterPath()  # laser-beam spark
    spark_path.moveTo(178, 8)
    spark_path.lineTo(188, 18)
    spark_path.lineTo(178, 28)
    spark_path.lineTo(168, 18)
    spark_path.closeSubpath()
    painter.setBrush(QBrush(QColor("#ff3b30")))
    painter.drawPath(spark_path)

    beam_pen = QPen(QColor("#ff3b30"), 6)  # diagonal laser beam, drawn
    beam_pen.setCapStyle(Qt.PenCapStyle.RoundCap)  # last -- on top, same
    painter.setPen(beam_pen)  # fill-then-stroke order as the wx original
    painter.drawLine(QPointF(15, 175), QPointF(178, 18))

    painter.end()
    return QIcon(pixmap)


def build_tool_icon(name: str, size: int = 22, color: str = "#E2E2E9"):
    """Simple flat-line glyph icons for the left-side draw-tool panel
    (Sélection/Main/Rectangle/Cercle/Ligne/Texte), replacing the
    emoji-prefixed text labels those buttons used to carry -- emoji
    render inconsistently across OS font sets and don't reliably read
    as a *tool*, whereas a plain outline glyph (a real PAO-style
    toolbox) does. Same QPainter-primitives approach as build_app_icon
    above, one glyph per name, on a transparent background so it
    matches whatever QToolButton state color surrounds it."""
    from PyQt6.QtCore import QPointF, QRectF, Qt
    from PyQt6.QtGui import QBrush, QColor, QIcon, QPainter, QPen, QPixmap

    design_size = 24.0
    pixmap = QPixmap(size, size)
    pixmap.fill(QColor(0, 0, 0, 0))
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    painter.scale(size / design_size, size / design_size)

    pen = QPen(QColor(color), 1.6)
    pen.setCapStyle(Qt.PenCapStyle.RoundCap)
    pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
    painter.setPen(pen)
    painter.setBrush(Qt.BrushStyle.NoBrush)

    if name == "select":
        # Classic arrow-cursor silhouette.
        from PyQt6.QtGui import QPainterPath

        path = QPainterPath()
        path.moveTo(5, 3)
        path.lineTo(5, 20)
        path.lineTo(9.5, 15.8)
        path.lineTo(12.5, 21.5)
        path.lineTo(15, 20.2)
        path.lineTo(12, 14.5)
        path.lineTo(18, 14)
        path.closeSubpath()
        painter.setBrush(QBrush(QColor(color)))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawPath(path)
    elif name == "pan":
        # Four outward arrowheads on a cross -- the standard "move/pan
        # the view" glyph most vector/CAD apps use.
        painter.drawLine(QPointF(12, 2), QPointF(12, 22))
        painter.drawLine(QPointF(2, 12), QPointF(22, 12))
        for tip, a, b in (
            (QPointF(12, 2), QPointF(9, 6), QPointF(15, 6)),
            (QPointF(12, 22), QPointF(9, 18), QPointF(15, 18)),
            (QPointF(2, 12), QPointF(6, 9), QPointF(6, 15)),
            (QPointF(22, 12), QPointF(18, 9), QPointF(18, 15)),
        ):
            painter.drawLine(tip, a)
            painter.drawLine(tip, b)
    elif name == "rect":
        painter.drawRect(QRectF(3.5, 5.5, 17, 13))
    elif name == "ellipse":
        painter.drawEllipse(QRectF(3, 3, 18, 18))
    elif name == "line":
        painter.drawLine(QPointF(4, 20), QPointF(20, 4))
        painter.setBrush(QBrush(QColor(color)))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawEllipse(QPointF(4, 20), 1.8, 1.8)
        painter.drawEllipse(QPointF(20, 4), 1.8, 1.8)
    elif name == "text":
        painter.drawLine(QPointF(5, 5), QPointF(19, 5))
        painter.drawLine(QPointF(12, 5), QPointF(12, 20))
    elif name == "polygon":
        import math

        from PyQt6.QtGui import QPolygonF

        cx, cy, r = 12.0, 12.0, 9.5
        hexagon = QPolygonF(
            [
                QPointF(
                    cx + r * math.cos(2 * math.pi * i / 6 - math.pi / 2),
                    cy + r * math.sin(2 * math.pi * i / 6 - math.pi / 2),
                )
                for i in range(6)
            ]
        )
        painter.drawPolygon(hexagon)

    painter.end()
    return QIcon(pixmap)


def build_emoji_icon(emoji: str, size: int = 26):
    """Render a single emoji glyph into a crisp QIcon, for the
    generator/production tool buttons (qt_main.py's Générateurs/
    Traitements/Vision groups). A plain QPushButton(emoji) at a small
    fixed font-size renders blurry/clipped on Windows -- drawing it once
    into a properly-sized, antialiased pixmap (matching build_tool_icon's
    approach for the main draw-tool row) is crisp at any DPI and lets the
    button show a real text label alongside it via ToolButtonTextUnderIcon
    instead of emoji-only with no visible label."""
    from PyQt6.QtCore import QRectF, Qt
    from PyQt6.QtGui import QColor, QFont, QIcon, QPainter, QPixmap

    pixmap = QPixmap(size, size)
    pixmap.fill(QColor(0, 0, 0, 0))
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    painter.setRenderHint(QPainter.RenderHint.TextAntialiasing)
    font = QFont()
    font.setPointSize(int(size * 0.62))
    painter.setFont(font)
    painter.drawText(QRectF(0, 0, size, size), Qt.AlignmentFlag.AlignCenter, emoji)
    painter.end()
    return QIcon(pixmap)


MODERN_DARK_QSS = """
QMainWindow {
    background-color: #121216;
    color: #E2E2E9;
    font-family: 'Segoe UI', 'Inter', -apple-system, sans-serif;
    font-size: 13px;
}

QWidget {
    background-color: #121216;
    color: #E2E2E9;
}

QMenuBar {
    background-color: #14141C;
    color: #E2E2E9;
    padding: 2px 6px;
    border-bottom: 1px solid #222230;
    font-size: 12px;
}

QMenuBar::item {
    background-color: transparent;
    padding: 3px 8px;
    border-radius: 4px;
}

QMenuBar::item:selected {
    background-color: #262636;
    color: #0A84FF;
}

QMenu {
    background-color: #1A1A24;
    color: #E2E2E9;
    border: 1px solid #2E2E40;
    border-radius: 6px;
    padding: 4px;
}

QMenu::item {
    padding: 5px 20px 5px 10px;
    border-radius: 4px;
}

QMenu::item:selected {
    background-color: #0A84FF;
    color: #FFFFFF;
}

QToolBar {
    background-color: #14141C;
    border-bottom: 1px solid #222230;
    spacing: 4px;
    padding: 3px 8px;
    min-height: 32px;
    max-height: 36px;
}

QToolButton {
    background-color: #1E1E2B;
    color: #E2E2E9;
    border: 1px solid #2C2C3E;
    border-radius: 5px;
    padding: 3px 8px;
    font-size: 12px;
    font-weight: 500;
}

QToolButton:hover {
    background-color: #0A84FF;
    color: #FFFFFF;
    border-color: #0A84FF;
}

QToolButton:pressed {
    background-color: #0066CC;
    border-color: #0066CC;
}

QToolButton:checked {
    background-color: #0A84FF;
    color: #FFFFFF;
}

QDockWidget {
    titlebar-close-icon: url(close.png);
    titlebar-normal-icon: url(undock.png);
    border: 1px solid #282836;
    border-radius: 8px;
}

QDockWidget::title {
    background-color: #1A1A22;
    padding: 8px 12px;
    border-bottom: 1px solid #282836;
    font-weight: 600;
    color: #0A84FF;
}

QTabWidget::pane {
    border: 1px solid #282836;
    border-radius: 6px;
    background-color: #1A1A22;
}

QTabBar::tab {
    background-color: #181822;
    color: #A0A0B4;
    padding: 8px 16px;
    border-top-left-radius: 6px;
    border-top-right-radius: 6px;
    border: 1px solid #282836;
    margin-right: 2px;
}

QTabBar::tab:selected {
    background-color: #242434;
    color: #0A84FF;
    font-weight: 600;
    border-bottom-color: #242434;
}

QTabBar::tab:hover:!selected {
    background-color: #20202C;
    color: #E2E2E9;
}

QTreeWidget, QListView, QTableView {
    background-color: #16161E;
    border: 1px solid #282836;
    border-radius: 6px;
    color: #E2E2E9;
    padding: 4px;
}

QTreeWidget::item {
    padding: 4px 6px;
    border-radius: 4px;
}

QTreeWidget::item:selected {
    background-color: #0A84FF;
    color: #FFFFFF;
}

QPushButton {
    background-color: #242432;
    color: #E2E2E9;
    border: 1px solid #36364A;
    border-radius: 6px;
    padding: 7px 16px;
    font-weight: 600;
}

QPushButton:hover {
    background-color: #0A84FF;
    color: #FFFFFF;
    border-color: #0A84FF;
}

QPushButton:pressed {
    background-color: #0066CC;
}

QPlainTextEdit {
    background-color: #16161E;
    color: #D4D4DC;
    border: 1px solid #282836;
    border-radius: 6px;
    padding: 6px;
    font-family: 'Cascadia Code', 'Consolas', 'JetBrains Mono', monospace;
    font-size: 12px;
    selection-background-color: #0A84FF;
}

QLineEdit, QSpinBox, QDoubleSpinBox, QComboBox {
    background-color: #181822;
    color: #E2E2E9;
    border: 1px solid #323246;
    border-radius: 6px;
    padding: 6px 10px;
}

QLineEdit:focus, QSpinBox:focus, QDoubleSpinBox:focus, QComboBox:focus {
    border: 1px solid #0A84FF;
}

QStatusBar {
    background-color: #1A1A22;
    color: #8E8E9A;
    border-top: 1px solid #282836;
}

QProgressBar {
    background-color: #16161E;
    color: #E2E2E9;
    border: 1px solid #282836;
    border-radius: 6px;
    text-align: center;
}

QProgressBar::chunk {
    background-color: #0A84FF;
    border-radius: 5px;
}

QGroupBox {
    border: 1px solid #282836;
    border-radius: 6px;
    margin-top: 12px;
    padding-top: 16px;
    font-weight: 600;
    color: #0A84FF;
}

QGroupBox::title {
    subcontrol-origin: margin;
    left: 10px;
    padding: 0 4px;
}

QScrollBar:vertical {
    background-color: #121216;
    width: 12px;
    margin: 0px;
}

QScrollBar::handle:vertical {
    background-color: #2D2D3E;
    min-height: 20px;
    border-radius: 6px;
}

QScrollBar::handle:vertical:hover {
    background-color: #0A84FF;
}

QScrollBar:horizontal {
    background-color: #121216;
    height: 12px;
    margin: 0px;
}

QScrollBar::handle:horizontal {
    background-color: #2D2D3E;
    min-width: 20px;
    border-radius: 6px;
}

QScrollBar::handle:horizontal:hover {
    background-color: #0A84FF;
}

QScrollBar::add-line, QScrollBar::sub-line {
    border: none;
    background: none;
}
"""

# Same structure/selectors/spacing as MODERN_DARK_QSS above, just a light
# palette -- kept as a literal sibling stylesheet (not generated from the
# dark one by substitution) so each selector's exact color stays easy to
# read and tweak on its own, same as the dark version. The accent blue
# (#0A84FF) and its pressed/hover shades are unchanged in both themes for
# brand consistency.
MODERN_LIGHT_QSS = """
QMainWindow {
    background-color: #F2F2F5;
    color: #1C1C22;
    font-family: 'Segoe UI', 'Inter', -apple-system, sans-serif;
    font-size: 13px;
}

QWidget {
    background-color: #F2F2F5;
    color: #1C1C22;
}

QMenuBar {
    background-color: #FFFFFF;
    color: #1C1C22;
    padding: 2px 6px;
    border-bottom: 1px solid #DADAE0;
    font-size: 12px;
}

QMenuBar::item {
    background-color: transparent;
    padding: 3px 8px;
    border-radius: 4px;
}

QMenuBar::item:selected {
    background-color: #E4EFFF;
    color: #0A84FF;
}

QMenu {
    background-color: #FFFFFF;
    color: #1C1C22;
    border: 1px solid #D6D6DE;
    border-radius: 6px;
    padding: 4px;
}

QMenu::item {
    padding: 5px 20px 5px 10px;
    border-radius: 4px;
}

QMenu::item:selected {
    background-color: #0A84FF;
    color: #FFFFFF;
}

QToolBar {
    background-color: #FFFFFF;
    border-bottom: 1px solid #DADAE0;
    spacing: 4px;
    padding: 3px 8px;
    min-height: 32px;
    max-height: 36px;
}

QToolButton {
    background-color: #F0F0F4;
    color: #1C1C22;
    border: 1px solid #CFCFD8;
    border-radius: 5px;
    padding: 3px 8px;
    font-size: 12px;
    font-weight: 500;
}

QToolButton:hover {
    background-color: #0A84FF;
    color: #FFFFFF;
    border-color: #0A84FF;
}

QToolButton:pressed {
    background-color: #0066CC;
    border-color: #0066CC;
}

QToolButton:checked {
    background-color: #0A84FF;
    color: #FFFFFF;
}

QDockWidget {
    titlebar-close-icon: url(close.png);
    titlebar-normal-icon: url(undock.png);
    border: 1px solid #D6D6DE;
    border-radius: 8px;
}

QDockWidget::title {
    background-color: #F7F7FA;
    padding: 8px 12px;
    border-bottom: 1px solid #DADAE0;
    font-weight: 600;
    color: #0A84FF;
}

QTabWidget::pane {
    border: 1px solid #D6D6DE;
    border-radius: 6px;
    background-color: #F7F7FA;
}

QTabBar::tab {
    background-color: #ECECF0;
    color: #6E6E7C;
    padding: 8px 16px;
    border-top-left-radius: 6px;
    border-top-right-radius: 6px;
    border: 1px solid #D6D6DE;
    margin-right: 2px;
}

QTabBar::tab:selected {
    background-color: #FFFFFF;
    color: #0A84FF;
    font-weight: 600;
    border-bottom-color: #FFFFFF;
}

QTabBar::tab:hover:!selected {
    background-color: #E4E4EA;
    color: #1C1C22;
}

QTreeWidget, QListView, QTableView {
    background-color: #FFFFFF;
    border: 1px solid #D6D6DE;
    border-radius: 6px;
    color: #1C1C22;
    padding: 4px;
}

QTreeWidget::item {
    padding: 4px 6px;
    border-radius: 4px;
}

QTreeWidget::item:selected {
    background-color: #0A84FF;
    color: #FFFFFF;
}

QPushButton {
    background-color: #F0F0F4;
    color: #1C1C22;
    border: 1px solid #C8C8D2;
    border-radius: 6px;
    padding: 7px 16px;
    font-weight: 600;
}

QPushButton:hover {
    background-color: #0A84FF;
    color: #FFFFFF;
    border-color: #0A84FF;
}

QPushButton:pressed {
    background-color: #0066CC;
}

QPlainTextEdit {
    background-color: #FFFFFF;
    color: #24242C;
    border: 1px solid #D6D6DE;
    border-radius: 6px;
    padding: 6px;
    font-family: 'Cascadia Code', 'Consolas', 'JetBrains Mono', monospace;
    font-size: 12px;
    selection-background-color: #0A84FF;
}

QLineEdit, QSpinBox, QDoubleSpinBox, QComboBox {
    background-color: #FFFFFF;
    color: #1C1C22;
    border: 1px solid #C8C8D2;
    border-radius: 6px;
    padding: 6px 10px;
}

QLineEdit:focus, QSpinBox:focus, QDoubleSpinBox:focus, QComboBox:focus {
    border: 1px solid #0A84FF;
}

QStatusBar {
    background-color: #F7F7FA;
    color: #6E6E7C;
    border-top: 1px solid #DADAE0;
}

QProgressBar {
    background-color: #FFFFFF;
    color: #1C1C22;
    border: 1px solid #D6D6DE;
    border-radius: 6px;
    text-align: center;
}

QProgressBar::chunk {
    background-color: #0A84FF;
    border-radius: 5px;
}

QGroupBox {
    border: 1px solid #D6D6DE;
    border-radius: 6px;
    margin-top: 12px;
    padding-top: 16px;
    font-weight: 600;
    color: #0A84FF;
}

QGroupBox::title {
    subcontrol-origin: margin;
    left: 10px;
    padding: 0 4px;
}

QScrollBar:vertical {
    background-color: #F2F2F5;
    width: 12px;
    margin: 0px;
}

QScrollBar::handle:vertical {
    background-color: #C8C8D2;
    min-height: 20px;
    border-radius: 6px;
}

QScrollBar::handle:vertical:hover {
    background-color: #0A84FF;
}

QScrollBar:horizontal {
    background-color: #F2F2F5;
    height: 12px;
    margin: 0px;
}

QScrollBar::handle:horizontal {
    background-color: #C8C8D2;
    min-width: 20px;
    border-radius: 6px;
}

QScrollBar::handle:horizontal:hover {
    background-color: #0A84FF;
}

QScrollBar::add-line, QScrollBar::sub-line {
    border: none;
    background: none;
}
"""


# Three additional named themes -- same selector structure as
# MODERN_DARK_QSS/MODERN_LIGHT_QSS above (mechanically derived from
# MODERN_DARK_QSS by semantic-role color substitution, not hand-typed,
# so every selector present in the dark theme is guaranteed present
# here too), each with its own accent color and neutral palette:
# "Banc Optique" (instrument-panel amber), "Atelier" (warm studio
# copper), "Plan Technique" (blueprint cyan). See THEME_PALETTES below
# for the matching non-QSS tokens (canvas grid/ruler, toolbar Start/
# Stop/Pause) each theme also needs.

MODERN_BENCH_QSS = """
QMainWindow {
    background-color: #191B1E;
    color: #E8E6E1;
    font-family: 'Segoe UI', 'Inter', -apple-system, sans-serif;
    font-size: 13px;
}

QWidget {
    background-color: #191B1E;
    color: #E8E6E1;
}

QMenuBar {
    background-color: #141518;
    color: #E8E6E1;
    padding: 2px 6px;
    border-bottom: 1px solid #34373C;
    font-size: 12px;
}

QMenuBar::item {
    background-color: transparent;
    padding: 3px 8px;
    border-radius: 4px;
}

QMenuBar::item:selected {
    background-color: #282A2F;
    color: #D98A2E;
}

QMenu {
    background-color: #1C1E22;
    color: #E8E6E1;
    border: 1px solid #34373C;
    border-radius: 6px;
    padding: 4px;
}

QMenu::item {
    padding: 5px 20px 5px 10px;
    border-radius: 4px;
}

QMenu::item:selected {
    background-color: #D98A2E;
    color: #FFFFFF;
}

QToolBar {
    background-color: #141518;
    border-bottom: 1px solid #34373C;
    spacing: 4px;
    padding: 3px 8px;
    min-height: 32px;
    max-height: 36px;
}

QToolButton {
    background-color: #202226;
    color: #E8E6E1;
    border: 1px solid #26282C;
    border-radius: 5px;
    padding: 3px 8px;
    font-size: 12px;
    font-weight: 500;
}

QToolButton:hover {
    background-color: #D98A2E;
    color: #FFFFFF;
    border-color: #D98A2E;
}

QToolButton:pressed {
    background-color: #B8721E;
    border-color: #B8721E;
}

QToolButton:checked {
    background-color: #D98A2E;
    color: #FFFFFF;
}

QDockWidget {
    titlebar-close-icon: url(close.png);
    titlebar-normal-icon: url(undock.png);
    border: 1px solid #34373C;
    border-radius: 8px;
}

QDockWidget::title {
    background-color: #141518;
    padding: 8px 12px;
    border-bottom: 1px solid #34373C;
    font-weight: 600;
    color: #D98A2E;
}

QTabWidget::pane {
    border: 1px solid #34373C;
    border-radius: 6px;
    background-color: #141518;
}

QTabBar::tab {
    background-color: #1C1E22;
    color: #83817C;
    padding: 8px 16px;
    border-top-left-radius: 6px;
    border-top-right-radius: 6px;
    border: 1px solid #34373C;
    margin-right: 2px;
}

QTabBar::tab:selected {
    background-color: #282A2F;
    color: #D98A2E;
    font-weight: 600;
    border-bottom-color: #282A2F;
}

QTabBar::tab:hover:!selected {
    background-color: #282A2F;
    color: #E8E6E1;
}

QTreeWidget, QListView, QTableView {
    background-color: #141518;
    border: 1px solid #34373C;
    border-radius: 6px;
    color: #E8E6E1;
    padding: 4px;
}

QTreeWidget::item {
    padding: 4px 6px;
    border-radius: 4px;
}

QTreeWidget::item:selected {
    background-color: #D98A2E;
    color: #FFFFFF;
}

QPushButton {
    background-color: #202226;
    color: #E8E6E1;
    border: 1px solid #26282C;
    border-radius: 6px;
    padding: 7px 16px;
    font-weight: 600;
}

QPushButton:hover {
    background-color: #D98A2E;
    color: #FFFFFF;
    border-color: #D98A2E;
}

QPushButton:pressed {
    background-color: #B8721E;
}

QPlainTextEdit {
    background-color: #141518;
    color: #B7B5B0;
    border: 1px solid #34373C;
    border-radius: 6px;
    padding: 6px;
    font-family: 'Cascadia Code', 'Consolas', 'JetBrains Mono', monospace;
    font-size: 12px;
    selection-background-color: #D98A2E;
}

QLineEdit, QSpinBox, QDoubleSpinBox, QComboBox {
    background-color: #1C1E22;
    color: #E8E6E1;
    border: 1px solid #26282C;
    border-radius: 6px;
    padding: 6px 10px;
}

QLineEdit:focus, QSpinBox:focus, QDoubleSpinBox:focus, QComboBox:focus {
    border: 1px solid #D98A2E;
}

QStatusBar {
    background-color: #141518;
    color: #83817C;
    border-top: 1px solid #34373C;
}

QProgressBar {
    background-color: #141518;
    color: #E8E6E1;
    border: 1px solid #34373C;
    border-radius: 6px;
    text-align: center;
}

QProgressBar::chunk {
    background-color: #D98A2E;
    border-radius: 5px;
}

QGroupBox {
    border: 1px solid #34373C;
    border-radius: 6px;
    margin-top: 12px;
    padding-top: 16px;
    font-weight: 600;
    color: #D98A2E;
}

QGroupBox::title {
    subcontrol-origin: margin;
    left: 10px;
    padding: 0 4px;
}

QScrollBar:vertical {
    background-color: #191B1E;
    width: 12px;
    margin: 0px;
}

QScrollBar::handle:vertical {
    background-color: #34373C;
    min-height: 20px;
    border-radius: 6px;
}

QScrollBar::handle:vertical:hover {
    background-color: #D98A2E;
}

QScrollBar:horizontal {
    background-color: #191B1E;
    height: 12px;
    margin: 0px;
}

QScrollBar::handle:horizontal {
    background-color: #34373C;
    min-width: 20px;
    border-radius: 6px;
}

QScrollBar::handle:horizontal:hover {
    background-color: #D98A2E;
}

QScrollBar::add-line, QScrollBar::sub-line {
    border: none;
    background: none;
}
"""

MODERN_ATELIER_QSS = """
QMainWindow {
    background-color: #211D1A;
    color: #F2EBE1;
    font-family: 'Segoe UI', 'Inter', -apple-system, sans-serif;
    font-size: 13px;
}

QWidget {
    background-color: #211D1A;
    color: #F2EBE1;
}

QMenuBar {
    background-color: #1A1613;
    color: #F2EBE1;
    padding: 2px 6px;
    border-bottom: 1px solid #3D362F;
    font-size: 12px;
}

QMenuBar::item {
    background-color: transparent;
    padding: 3px 8px;
    border-radius: 4px;
}

QMenuBar::item:selected {
    background-color: #332B24;
    color: #C96A38;
}

QMenu {
    background-color: #251F1B;
    color: #F2EBE1;
    border: 1px solid #3D362F;
    border-radius: 6px;
    padding: 4px;
}

QMenu::item {
    padding: 5px 20px 5px 10px;
    border-radius: 4px;
}

QMenu::item:selected {
    background-color: #C96A38;
    color: #FFFFFF;
}

QToolBar {
    background-color: #1A1613;
    border-bottom: 1px solid #3D362F;
    spacing: 4px;
    padding: 3px 8px;
    min-height: 32px;
    max-height: 36px;
}

QToolButton {
    background-color: #2A241F;
    color: #F2EBE1;
    border: 1px solid #2D2822;
    border-radius: 5px;
    padding: 3px 8px;
    font-size: 12px;
    font-weight: 500;
}

QToolButton:hover {
    background-color: #C96A38;
    color: #FFFFFF;
    border-color: #C96A38;
}

QToolButton:pressed {
    background-color: #A1552C;
    border-color: #A1552C;
}

QToolButton:checked {
    background-color: #C96A38;
    color: #FFFFFF;
}

QDockWidget {
    titlebar-close-icon: url(close.png);
    titlebar-normal-icon: url(undock.png);
    border: 1px solid #3D362F;
    border-radius: 8px;
}

QDockWidget::title {
    background-color: #1A1613;
    padding: 8px 12px;
    border-bottom: 1px solid #3D362F;
    font-weight: 600;
    color: #C96A38;
}

QTabWidget::pane {
    border: 1px solid #3D362F;
    border-radius: 6px;
    background-color: #1A1613;
}

QTabBar::tab {
    background-color: #251F1B;
    color: #8F8377;
    padding: 8px 16px;
    border-top-left-radius: 6px;
    border-top-right-radius: 6px;
    border: 1px solid #3D362F;
    margin-right: 2px;
}

QTabBar::tab:selected {
    background-color: #332B24;
    color: #C96A38;
    font-weight: 600;
    border-bottom-color: #332B24;
}

QTabBar::tab:hover:!selected {
    background-color: #332B24;
    color: #F2EBE1;
}

QTreeWidget, QListView, QTableView {
    background-color: #1A1613;
    border: 1px solid #3D362F;
    border-radius: 6px;
    color: #F2EBE1;
    padding: 4px;
}

QTreeWidget::item {
    padding: 4px 6px;
    border-radius: 4px;
}

QTreeWidget::item:selected {
    background-color: #C96A38;
    color: #FFFFFF;
}

QPushButton {
    background-color: #2A241F;
    color: #F2EBE1;
    border: 1px solid #2D2822;
    border-radius: 6px;
    padding: 7px 16px;
    font-weight: 600;
}

QPushButton:hover {
    background-color: #C96A38;
    color: #FFFFFF;
    border-color: #C96A38;
}

QPushButton:pressed {
    background-color: #A1552C;
}

QPlainTextEdit {
    background-color: #1A1613;
    color: #C7BCAC;
    border: 1px solid #3D362F;
    border-radius: 6px;
    padding: 6px;
    font-family: 'Cascadia Code', 'Consolas', 'JetBrains Mono', monospace;
    font-size: 12px;
    selection-background-color: #C96A38;
}

QLineEdit, QSpinBox, QDoubleSpinBox, QComboBox {
    background-color: #251F1B;
    color: #F2EBE1;
    border: 1px solid #2D2822;
    border-radius: 6px;
    padding: 6px 10px;
}

QLineEdit:focus, QSpinBox:focus, QDoubleSpinBox:focus, QComboBox:focus {
    border: 1px solid #C96A38;
}

QStatusBar {
    background-color: #1A1613;
    color: #8F8377;
    border-top: 1px solid #3D362F;
}

QProgressBar {
    background-color: #1A1613;
    color: #F2EBE1;
    border: 1px solid #3D362F;
    border-radius: 6px;
    text-align: center;
}

QProgressBar::chunk {
    background-color: #C96A38;
    border-radius: 5px;
}

QGroupBox {
    border: 1px solid #3D362F;
    border-radius: 6px;
    margin-top: 12px;
    padding-top: 16px;
    font-weight: 600;
    color: #C96A38;
}

QGroupBox::title {
    subcontrol-origin: margin;
    left: 10px;
    padding: 0 4px;
}

QScrollBar:vertical {
    background-color: #211D1A;
    width: 12px;
    margin: 0px;
}

QScrollBar::handle:vertical {
    background-color: #3D362F;
    min-height: 20px;
    border-radius: 6px;
}

QScrollBar::handle:vertical:hover {
    background-color: #C96A38;
}

QScrollBar:horizontal {
    background-color: #211D1A;
    height: 12px;
    margin: 0px;
}

QScrollBar::handle:horizontal {
    background-color: #3D362F;
    min-width: 20px;
    border-radius: 6px;
}

QScrollBar::handle:horizontal:hover {
    background-color: #C96A38;
}

QScrollBar::add-line, QScrollBar::sub-line {
    border: none;
    background: none;
}
"""

MODERN_BLUEPRINT_QSS = """
QMainWindow {
    background-color: #0F1E33;
    color: #E7EFF7;
    font-family: 'Segoe UI', 'Inter', -apple-system, sans-serif;
    font-size: 13px;
}

QWidget {
    background-color: #0F1E33;
    color: #E7EFF7;
}

QMenuBar {
    background-color: #0B1626;
    color: #E7EFF7;
    padding: 2px 6px;
    border-bottom: 1px solid #2C4666;
    font-size: 12px;
}

QMenuBar::item {
    background-color: transparent;
    padding: 3px 8px;
    border-radius: 4px;
}

QMenuBar::item:selected {
    background-color: #1A3050;
    color: #2E9FC4;
}

QMenu {
    background-color: #122542;
    color: #E7EFF7;
    border: 1px solid #2C4666;
    border-radius: 6px;
    padding: 4px;
}

QMenu::item {
    padding: 5px 20px 5px 10px;
    border-radius: 4px;
}

QMenu::item:selected {
    background-color: #2E9FC4;
    color: #FFFFFF;
}

QToolBar {
    background-color: #0B1626;
    border-bottom: 1px solid #2C4666;
    spacing: 4px;
    padding: 3px 8px;
    min-height: 32px;
    max-height: 36px;
}

QToolButton {
    background-color: #14273F;
    color: #E7EFF7;
    border: 1px solid #1E3350;
    border-radius: 5px;
    padding: 3px 8px;
    font-size: 12px;
    font-weight: 500;
}

QToolButton:hover {
    background-color: #2E9FC4;
    color: #FFFFFF;
    border-color: #2E9FC4;
}

QToolButton:pressed {
    background-color: #25809F;
    border-color: #25809F;
}

QToolButton:checked {
    background-color: #2E9FC4;
    color: #FFFFFF;
}

QDockWidget {
    titlebar-close-icon: url(close.png);
    titlebar-normal-icon: url(undock.png);
    border: 1px solid #2C4666;
    border-radius: 8px;
}

QDockWidget::title {
    background-color: #0B1626;
    padding: 8px 12px;
    border-bottom: 1px solid #2C4666;
    font-weight: 600;
    color: #2E9FC4;
}

QTabWidget::pane {
    border: 1px solid #2C4666;
    border-radius: 6px;
    background-color: #0B1626;
}

QTabBar::tab {
    background-color: #122542;
    color: #6F8BAB;
    padding: 8px 16px;
    border-top-left-radius: 6px;
    border-top-right-radius: 6px;
    border: 1px solid #2C4666;
    margin-right: 2px;
}

QTabBar::tab:selected {
    background-color: #1A3050;
    color: #2E9FC4;
    font-weight: 600;
    border-bottom-color: #1A3050;
}

QTabBar::tab:hover:!selected {
    background-color: #1A3050;
    color: #E7EFF7;
}

QTreeWidget, QListView, QTableView {
    background-color: #0B1626;
    border: 1px solid #2C4666;
    border-radius: 6px;
    color: #E7EFF7;
    padding: 4px;
}

QTreeWidget::item {
    padding: 4px 6px;
    border-radius: 4px;
}

QTreeWidget::item:selected {
    background-color: #2E9FC4;
    color: #FFFFFF;
}

QPushButton {
    background-color: #14273F;
    color: #E7EFF7;
    border: 1px solid #1E3350;
    border-radius: 6px;
    padding: 7px 16px;
    font-weight: 600;
}

QPushButton:hover {
    background-color: #2E9FC4;
    color: #FFFFFF;
    border-color: #2E9FC4;
}

QPushButton:pressed {
    background-color: #25809F;
}

QPlainTextEdit {
    background-color: #0B1626;
    color: #A9C0D8;
    border: 1px solid #2C4666;
    border-radius: 6px;
    padding: 6px;
    font-family: 'Cascadia Code', 'Consolas', 'JetBrains Mono', monospace;
    font-size: 12px;
    selection-background-color: #2E9FC4;
}

QLineEdit, QSpinBox, QDoubleSpinBox, QComboBox {
    background-color: #122542;
    color: #E7EFF7;
    border: 1px solid #1E3350;
    border-radius: 6px;
    padding: 6px 10px;
}

QLineEdit:focus, QSpinBox:focus, QDoubleSpinBox:focus, QComboBox:focus {
    border: 1px solid #2E9FC4;
}

QStatusBar {
    background-color: #0B1626;
    color: #6F8BAB;
    border-top: 1px solid #2C4666;
}

QProgressBar {
    background-color: #0B1626;
    color: #E7EFF7;
    border: 1px solid #2C4666;
    border-radius: 6px;
    text-align: center;
}

QProgressBar::chunk {
    background-color: #2E9FC4;
    border-radius: 5px;
}

QGroupBox {
    border: 1px solid #2C4666;
    border-radius: 6px;
    margin-top: 12px;
    padding-top: 16px;
    font-weight: 600;
    color: #2E9FC4;
}

QGroupBox::title {
    subcontrol-origin: margin;
    left: 10px;
    padding: 0 4px;
}

QScrollBar:vertical {
    background-color: #0F1E33;
    width: 12px;
    margin: 0px;
}

QScrollBar::handle:vertical {
    background-color: #2C4666;
    min-height: 20px;
    border-radius: 6px;
}

QScrollBar::handle:vertical:hover {
    background-color: #2E9FC4;
}

QScrollBar:horizontal {
    background-color: #0F1E33;
    height: 12px;
    margin: 0px;
}

QScrollBar::handle:horizontal {
    background-color: #2C4666;
    min-width: 20px;
    border-radius: 6px;
}

QScrollBar::handle:horizontal:hover {
    background-color: #2E9FC4;
}

QScrollBar::add-line, QScrollBar::sub-line {
    border: none;
    background: none;
}
"""


# Non-QSS theme tokens -- everything above only covers ordinary QWidget
# CSS. Two things can't be reached by QSS at all and need their own
# per-theme values here: the canvas (a QGraphicsView that paints its bed/
# grid/rulers directly in drawBackground(), see qt_canvas.py's
# set_theme()) and the toolbar's Start/Pause/Stop buttons (qt_main.py's
# _apply_toolbar_button_theme() -- they set their own per-state
# background overriding the app stylesheet, since a plain QSS class
# selector can't express "green when idle, but still grey when
# disabled"). COLOR_SUCCESS/WARNING/DANGER above stay the SAME across
# every theme by design (semantic meaning shouldn't shift with the
# aesthetic) -- only the neutral/background tokens vary here.
THEME_PALETTES = {
    "dark": {
        "label": "Sombre (Classique)",
        "qss": MODERN_DARK_QSS,
        "is_dark": True,
        "accent": "#0A84FF",
        "neutral_bg": "#3A3A4A", "neutral_fg": "#FFFFFF",
        "disabled_bg": "#2C2C3E", "disabled_fg": "#6E6E7A",
        "tool_icon_color": "#E2E2E9",
        "canvas_bg": "#14141A", "canvas_bed": "#1C1C26",
        "canvas_grid_primary": "#2E2E40", "canvas_grid_secondary": "#222230",
        "canvas_border": "#0A84FF", "canvas_ruler": "#A0A0B0",
        "watermark_rgb": (10, 132, 255),
    },
    "light": {
        "label": "Clair (Classique)",
        "qss": MODERN_LIGHT_QSS,
        "is_dark": False,
        "accent": "#0A84FF",
        "neutral_bg": "#D6D6DE", "neutral_fg": "#1C1C22",
        "disabled_bg": "#E4E4EA", "disabled_fg": "#9A9AA6",
        "tool_icon_color": "#1C1C22",
        "canvas_bg": "#E8E8ED", "canvas_bed": "#FFFFFF",
        "canvas_grid_primary": "#C4C4CE", "canvas_grid_secondary": "#E0E0E6",
        "canvas_border": "#0A84FF", "canvas_ruler": "#505060",
        "watermark_rgb": (0, 102, 204),
    },
    "bench": {
        "label": "Banc Optique",
        "qss": MODERN_BENCH_QSS,
        "is_dark": True,
        "accent": "#D98A2E",
        "neutral_bg": "#3A3D42", "neutral_fg": "#FFFFFF",
        "disabled_bg": "#26282C", "disabled_fg": "#6E6E72",
        "tool_icon_color": "#E8E6E1",
        "canvas_bg": "#101114", "canvas_bed": "#1C1E22",
        "canvas_grid_primary": "#34373C", "canvas_grid_secondary": "#26282C",
        "canvas_border": "#D98A2E", "canvas_ruler": "#9A9C9F",
        "watermark_rgb": (217, 138, 46),
    },
    "atelier": {
        "label": "Atelier",
        "qss": MODERN_ATELIER_QSS,
        "is_dark": True,
        "accent": "#C96A38",
        "neutral_bg": "#443B32", "neutral_fg": "#FFFFFF",
        "disabled_bg": "#2D2822", "disabled_fg": "#6E655A",
        "tool_icon_color": "#F2EBE1",
        "canvas_bg": "#181410", "canvas_bed": "#211D1A",
        "canvas_grid_primary": "#3D362F", "canvas_grid_secondary": "#2D2822",
        "canvas_border": "#C96A38", "canvas_ruler": "#A79C8C",
        "watermark_rgb": (201, 106, 56),
    },
    "blueprint": {
        "label": "Plan Technique",
        "qss": MODERN_BLUEPRINT_QSS,
        "is_dark": True,
        "accent": "#2E9FC4",
        "neutral_bg": "#33507A", "neutral_fg": "#FFFFFF",
        "disabled_bg": "#1E3350", "disabled_fg": "#5C7796",
        "tool_icon_color": "#E7EFF7",
        "canvas_bg": "#0A1220", "canvas_bed": "#0F1E33",
        "canvas_grid_primary": "#2C4666", "canvas_grid_secondary": "#1E3350",
        # Lighter than the QSS accent (#2E9FC4, chosen for white-text
        # contrast on interactive widgets) -- the canvas border/ruler
        # never pairs this with white text, so it can use the airier
        # "blueprint linework" cyan from the original mockup instead.
        "canvas_border": "#6FCBE8", "canvas_ruler": "#7FA8C9",
        "watermark_rgb": (111, 203, 232),
    },
}
