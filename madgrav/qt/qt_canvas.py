"""
Interactive QGraphicsView Canvas for MadGrav PyQt6 GUI.
Renders laser bed grid, laser origin, vector nodes, and interactive element selection.
"""

import math

from PyQt6.QtCore import QLineF, QPointF, QRectF, Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QBrush, QColor, QPainter, QPainterPath, QPen
from PyQt6.QtWidgets import (
    QGraphicsEllipseItem,
    QGraphicsItem,
    QGraphicsLineItem,
    QGraphicsRectItem,
    QGraphicsScene,
    QGraphicsView,
    QWidget,
)

# Minimum drag size (mm) before a rect/ellipse/line draw gesture is
# treated as a real shape rather than an accidental click -- avoids
# littering the document with zero-size elements.
_MIN_DRAW_SIZE_MM = 0.5


class MadGravQtCanvas(QGraphicsView):
    """
    Modern QGraphicsView Interactive Laser Bed Canvas.
    """

    cursor_position_changed = pyqtSignal(float, float)
    selection_changed = pyqtSignal(object)  # emits the selected node, or None
    shape_created = pyqtSignal()  # a draw-tool gesture just added a real element
    zoom_changed = pyqtSignal(float)  # current view scale factor (1.0 == 100%)

    def __init__(self, context, parent=None):
        super().__init__(parent)
        self.context = context
        self.scene = QGraphicsScene(self)
        self.setScene(self.scene)

        self.setViewportUpdateMode(QGraphicsView.ViewportUpdateMode.BoundingRectViewportUpdate)
        self.setOptimizationFlags(QGraphicsView.OptimizationFlag.DontSavePainterState)

        self.setRenderHints(
            QPainter.RenderHint.Antialiasing
            | QPainter.RenderHint.SmoothPixmapTransform
            | QPainter.RenderHint.TextAntialiasing
        )

        self._aa_timer = QTimer(self)
        self._aa_timer.setSingleShot(True)
        self._aa_timer.timeout.connect(self._restore_antialiasing)

        self.setDragMode(QGraphicsView.DragMode.NoDrag)
        self.setTransformationAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)
        self.setResizeAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOn)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOn)

        # Bed dimensions -- default 300x200mm, replaced below with the real
        # dimensions of the currently configured device when available.
        self.bed_width = 300.0
        self.bed_height = 200.0
        self._sync_bed_from_device()

        # Colors -- match THEME_PALETTES["dark"] in qt_theme.py (this is
        # just the pre-set_theme() default so a canvas built before the
        # main window's own _theme_name is known still looks right).
        self.bg_color = QColor("#14141A")
        self.bed_color = QColor("#1C1C26")
        self.grid_primary_color = QColor("#2E2E40")
        self.grid_secondary_color = QColor("#222230")
        self.border_color = QColor("#0A84FF")
        self.ruler_color = QColor("#A0A0B0")
        self.watermark_rgb = (10, 132, 255)
        self._is_dark_theme = True

        self.zoom_factor = 1.15
        self.is_panning = False
        self.pan_start = QPointF()

        self._element_items = []
        self._item_to_node = {}
        # Items styled as "emphasized" as of the last refresh_selection_highlight()/
        # render_elements() call -- lets refresh_selection_highlight() only
        # restyle the items whose emphasis actually changed (usually 1-2)
        # instead of every rendered item, on every selection click.
        self._prev_emphasized_items = set()

        # Draw-tool state (rectangle/ellipse/line rubber-band creation).
        self.draw_mode = None  # None | "rect" | "ellipse" | "line" | "text"
        self._draw_start = None
        self._draw_preview = None
        # LightBurn's Rectangle tool has a corner-radius field in its
        # options bar; the "rect" console command already supports it
        # (-x/-y rounded rx/ry), just never wired to this tool before.
        # Set from the tool panel's spinbox (qt_main.py); 0 = sharp
        # corners, matching every rectangle drawn before this feature.
        self.rect_corner_radius_mm = 0.0

        # Camera Overlay
        self.camera_overlay_pixmap = None
        self.camera_overlay_opacity = 0.5
        self.camera_overlay_visible = False
        self.is_opengl_enabled = False

        # Rubber-band multi-selection state (Selection tool, drag on
        # empty space).
        self._rb_start = None
        self._rb_item = None
        self._rb_additive = False

        # Click-drag-to-move state (Selection tool, drag on a selected
        # element).
        self._move_start_scene = None
        self._move_last_scene = None
        self._move_active = False

        # Interactive resize/rotate handles -- shown only for a clean
        # single selection (see _update_selection_handles): 8 small
        # squares at the corners/edge-midpoints for resize, plus one
        # small circle above top-center for free rotation, matching the
        # standard vector-editor convention (LightBurn/Illustrator/
        # Inkscape all use this exact layout). Resize/rotate only show a
        # preview during the drag (dashed rect / live angle) and commit
        # via the existing "resize"/"rotate" console commands on
        # release -- same "preview during drag, commit once" shape as
        # the move-drag above, not a live per-pixel geometry rebuild.
        self._handle_items = {}
        self._active_handle = None
        self._handle_drag_start_rect = None
        self._handle_drag_center = None
        self._handle_drag_start_angle = None
        self._handle_preview_item = None
        self._handle_rotation_live = 0.0

        self.init_scene()
        self.render_elements()

    def enable_opengl(self, enabled: bool) -> bool:
        self.is_opengl_enabled = bool(enabled)
        if self.is_opengl_enabled:
            try:
                from PyQt6.QtOpenGLWidgets import QOpenGLWidget
                self.setViewport(QOpenGLWidget())
                self.setViewportUpdateMode(QGraphicsView.ViewportUpdateMode.FullViewportUpdate)
            except Exception:
                self.setViewport(QWidget())
                self.setViewportUpdateMode(QGraphicsView.ViewportUpdateMode.SmartViewportUpdate)
        else:
            self.setViewport(QWidget())
            self.setViewportUpdateMode(QGraphicsView.ViewportUpdateMode.SmartViewportUpdate)
        self.scene.update()
        self.viewport().update()
        return self.is_opengl_enabled

    def set_camera_overlay(self, pixmap, opacity: float = 0.5, visible: bool = True):
        self.camera_overlay_pixmap = pixmap
        self.camera_overlay_opacity = max(0.0, min(1.0, float(opacity)))
        self.camera_overlay_visible = visible
        self.scene.update()
        self.viewport().update()

    def set_camera_opacity(self, opacity: float):
        self.camera_overlay_opacity = max(0.0, min(1.0, float(opacity)))
        self.scene.update()
        self.viewport().update()

    def toggle_camera_overlay(self, visible=None) -> bool:
        if visible is None:
            self.camera_overlay_visible = not self.camera_overlay_visible
        else:
            self.camera_overlay_visible = bool(visible)
        self.scene.update()
        self.viewport().update()
        return self.camera_overlay_visible

    def set_draw_mode(self, mode):
        """Switch the active draw tool. mode is None (selection), "rect",
        "ellipse", or "line"; call with None to cancel back to plain
        selection."""
        self._cancel_draw()
        self.draw_mode = mode
        self.setDragMode(QGraphicsView.DragMode.NoDrag)
        self.setCursor(
            Qt.CursorShape.CrossCursor if mode else Qt.CursorShape.ArrowCursor
        )

    def init_scene(self):
        self.scene.clear()
        # scene.clear() destroys every QGraphicsItem in the scene at the
        # Qt/C++ level, including whatever was tracked in
        # _element_items/_item_to_node from a prior render_elements()
        # call -- without resetting those here too, a render_elements()
        # call right after this one (device switch, theme toggle) tries
        # to scene.removeItem() references that are already gone,
        # crashing with "wrapped C/C++ object ... has been deleted".
        self._element_items = []
        self._item_to_node = {}
        # Same reasoning as above -- the resize/rotate handle items
        # (added later this session) are just as dead at the C++ level
        # after scene.clear(); confirmed by reproduction via
        # test_device_switch_bed_measurement_feeds_outside_bed_safety_check
        # (a device switch mid-selection triggers init_scene() then
        # render_elements(), which used to try removing already-deleted
        # handle items).
        self._handle_items = {}
        self._active_handle = None
        self._handle_preview_item = None
        # Same reasoning again -- these reference items scene.clear() just
        # destroyed; a stale entry here would make refresh_selection_highlight()
        # try to restyle an already-deleted QGraphicsItem.
        self._prev_emphasized_items = set()
        self.scene.setBackgroundBrush(QBrush(self.bg_color))

        # Add Bed rectangle (transparent so it doesn't cover drawBackground's grid & watermark)
        bed_rect = QRectF(0, 0, self.bed_width, self.bed_height)
        self.bed_item = self.scene.addRect(
            bed_rect,
            QPen(Qt.PenStyle.NoPen),
            QBrush(Qt.BrushStyle.NoBrush),
        )

        # Origin indicator
        origin_pen = QPen(QColor("#FF3B30"), 2)
        self.scene.addLine(-5, 0, 15, 0, origin_pen)
        origin_pen_y = QPen(QColor("#30D158"), 2)
        self.scene.addLine(0, -5, 0, 15, origin_pen_y)

        self.setSceneRect(-50, -50, self.bed_width + 100, self.bed_height + 100)

    def showEvent(self, event):
        super().showEvent(event)
        if not getattr(self, "_initial_fitted", False):
            self._initial_fitted = True
            QTimer.singleShot(50, self.fit_bed)

    def fit_bed(self):
        """Center and fit the laser bed inside the viewport."""
        padding = 15.0
        self.fitInView(
            QRectF(-padding, -padding, self.bed_width + 2 * padding, self.bed_height + 2 * padding),
            Qt.AspectRatioMode.KeepAspectRatio,
        )

    def set_theme(self, palette):
        """Swap the bed/grid/ruler colors the QSS stylesheet can't reach
        (this widget paints its background/grid directly in
        drawBackground() instead of via CSS, since QGraphicsView content
        isn't styleable that way). Called by MadGravQtMainWindow's
        _on_select_theme() alongside setStyleSheet() so the canvas
        doesn't stay on the old theme while the rest of the window
        switches.

        @param palette: one of qt_theme.THEME_PALETTES' dicts (not
            imported directly here to keep this widget decoupled from
            qt_theme.py -- the caller already has it in hand). A bare
            bool is also accepted for backward compatibility with older
            call sites/tests written before this became a 5-theme
            picker (True/False map to the original dark/light values).
        """
        if isinstance(palette, bool):
            palette = {
                "is_dark": palette,
                "canvas_bg": "#14141A" if palette else "#E8E8ED",
                "canvas_bed": "#1C1C26" if palette else "#FFFFFF",
                "canvas_grid_primary": "#2E2E40" if palette else "#C4C4CE",
                "canvas_grid_secondary": "#222230" if palette else "#E0E0E6",
                "canvas_border": "#0A84FF",
                "canvas_ruler": "#A0A0B0" if palette else "#505060",
                "watermark_rgb": (10, 132, 255) if palette else (0, 102, 204),
            }
        self._is_dark_theme = palette["is_dark"]
        self.bg_color = QColor(palette["canvas_bg"])
        self.bed_color = QColor(palette["canvas_bed"])
        self.grid_primary_color = QColor(palette["canvas_grid_primary"])
        self.grid_secondary_color = QColor(palette["canvas_grid_secondary"])
        self.border_color = QColor(palette["canvas_border"])
        self.ruler_color = QColor(palette["canvas_ruler"])
        self.watermark_rgb = palette["watermark_rgb"]
        self.init_scene()
        self.render_elements()

    def _sync_bed_from_device(self):
        """Read the real bed size (in mm) from the active device, if any."""
        try:
            from madgrav.core.units import Length

            view = self.context.device.view
            width = Length(view.width).mm
            height = Length(view.height).mm
            if width > 0 and height > 0:
                self.bed_width = width
                self.bed_height = height
        except (AttributeError, ValueError):
            # No device configured yet, or its view isn't ready -- keep defaults.
            pass

    def render_elements(self):
        """
        Render the real document (context.elements) onto the canvas.

        Converts each element's geometry to a QPainterPath in mm, honoring
        curves (cubic/quadratic beziers) exactly and approximating arcs with
        sampled line segments. Call again after load/undo/redo to refresh.
        """
        for item in self._element_items:
            self.scene.removeItem(item)
        self._element_items = []
        self._item_to_node = {}

        elements = getattr(self.context, "elements", None)
        if elements is None:
            return
        try:
            elem_branch = elements.elem_branch
        except AttributeError:
            return

        from madgrav.core.units import UNITS_PER_MM

        def to_mm(value):
            return value / UNITS_PER_MM

        for node in elem_branch.flat():
            if node is elem_branch or getattr(node, "hidden", False):
                continue
            if not hasattr(node, "as_geometry"):
                continue
            try:
                geometry = node.as_geometry()
                svg_path = geometry.as_path() if geometry is not None else None
            except Exception:
                continue
            if svg_path is None:
                continue

            qpath = QPainterPath()
            for seg in svg_path:
                cls = type(seg).__name__
                if cls == "Move":
                    qpath.moveTo(to_mm(seg.end.x), to_mm(seg.end.y))
                elif cls == "Line":
                    qpath.lineTo(to_mm(seg.end.x), to_mm(seg.end.y))
                elif cls == "Close":
                    qpath.closeSubpath()
                elif cls == "QuadraticBezier":
                    qpath.quadTo(
                        to_mm(seg.control.x),
                        to_mm(seg.control.y),
                        to_mm(seg.end.x),
                        to_mm(seg.end.y),
                    )
                elif cls == "CubicBezier":
                    qpath.cubicTo(
                        to_mm(seg.control1.x),
                        to_mm(seg.control1.y),
                        to_mm(seg.control2.x),
                        to_mm(seg.control2.y),
                        to_mm(seg.end.x),
                        to_mm(seg.end.y),
                    )
                elif cls == "Arc":
                    # No direct Qt equivalent for an SVG elliptical arc --
                    # approximate with sampled line segments.
                    for step in range(1, 25):
                        pt = seg.point(step / 24)
                        qpath.lineTo(to_mm(pt.x), to_mm(pt.y))

            if qpath.isEmpty():
                continue

            pen, brush = self._style_for_node(node)
            item = self.scene.addPath(qpath, pen, brush)
            item.setZValue(11 if getattr(node, "emphasized", False) else 10)
            self._element_items.append(item)
            self._item_to_node[item] = node
        # Every item above was just styled correctly for its CURRENT
        # emphasis state -- seed the cache so a refresh_selection_highlight()
        # right after this rebuild only restyles items whose selection
        # changes AFTER this point, not all of them again.
        self._prev_emphasized_items = {
            item for item, node in self._item_to_node.items()
            if getattr(node, "emphasized", False)
        }
        self._update_selection_handles()

    def _movable_selected_items(self):
        """Items whose node is both selected and actually movable -- the
        set the translate/nudge/drag fast paths are allowed to reposition
        visually, matching exactly what the "translate" console command
        applies to node data (element_translate in madgrav/core/elements/
        shapes.py gates each node with node.can_move(self.lock_allows_move),
        NOT a bare "not locked" check). elements.lock_allows_move defaults
        to True, meaning a locked element is normally still translatable --
        a bare "not node.lock" filter here previously left the on-screen
        item frozen in place while the real node data moved underneath it
        (confirmed by reproduction: nudging a locked element left its
        matrix/bounds updated but its QGraphicsItem never budged)."""
        elements = getattr(self.context, "elements", None)
        lock_allows_move = (
            getattr(elements, "lock_allows_move", True) if elements is not None else True
        )
        return [
            item
            for item, node in self._item_to_node.items()
            if getattr(node, "emphasized", False) and node.can_move(lock_allows_move)
        ]

    _RESIZE_HANDLE_NAMES = ("nw", "n", "ne", "e", "se", "s", "sw", "w")
    _HANDLE_CURSORS = {
        "nw": Qt.CursorShape.SizeFDiagCursor,
        "se": Qt.CursorShape.SizeFDiagCursor,
        "ne": Qt.CursorShape.SizeBDiagCursor,
        "sw": Qt.CursorShape.SizeBDiagCursor,
        "n": Qt.CursorShape.SizeVerCursor,
        "s": Qt.CursorShape.SizeVerCursor,
        "e": Qt.CursorShape.SizeHorCursor,
        "w": Qt.CursorShape.SizeHorCursor,
        "rotate": Qt.CursorShape.CrossCursor,
    }

    def _clear_selection_handles(self):
        for item in self._handle_items.values():
            self.scene.removeItem(item)
        self._handle_items = {}

    def _update_selection_handles(self):
        """(Re)build the resize/rotate handles for the current selection.
        Only shown for a clean single selection -- resizing/rotating a
        multi-selection's combined bounding box would silently distort
        each element's own aspect ratio differently, not a single well-
        defined transform, so multi-select gets no handles (align/CAG
        tools already cover multi-element operations)."""
        self._clear_selection_handles()
        if self._active_handle is not None:
            # Mid-drag: the handles' own positions are intentionally
            # static until the drag commits (see _start_handle_drag) --
            # rebuilding them here would fight the drag.
            return
        elements = getattr(self.context, "elements", None)
        if elements is None:
            return
        emphasized = list(elements.elems(emphasized=True))
        selected_items = self._movable_selected_items()
        if len(emphasized) != 1 or len(selected_items) != 1:
            return
        rect = selected_items[0].sceneBoundingRect()
        if rect.width() <= 0 or rect.height() <= 0:
            return

        anchor_points = {
            "nw": rect.topLeft(),
            "n": QPointF(rect.center().x(), rect.top()),
            "ne": rect.topRight(),
            "e": QPointF(rect.right(), rect.center().y()),
            "se": rect.bottomRight(),
            "s": QPointF(rect.center().x(), rect.bottom()),
            "sw": rect.bottomLeft(),
            "w": QPointF(rect.left(), rect.center().y()),
        }
        for name, pt in anchor_points.items():
            handle = QGraphicsRectItem(-4, -4, 8, 8)
            handle.setPos(pt)
            # ItemIgnoresTransformations keeps the handle a constant
            # on-screen pixel size regardless of zoom -- only its anchor
            # POSITION (set above, in scene/mm coordinates) moves with
            # the shape and view.
            handle.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIgnoresTransformations)
            pen = QPen(QColor("#0A84FF"), 1)
            pen.setCosmetic(True)
            handle.setPen(pen)
            handle.setBrush(QBrush(QColor("#FFFFFF")))
            handle.setZValue(30)
            handle.setCursor(self._HANDLE_CURSORS[name])
            self.scene.addItem(handle)
            self._handle_items[name] = handle

        # Rotate handle -- a small circle offset above the top-center
        # handle, connected by a thin line, the same LightBurn/
        # Illustrator/Inkscape convention for "this one rotates, the
        # others resize." Both are anchored at the top-center scene
        # point but drawn with a local (ignoring-transform) pixel offset
        # so the 24px gap stays constant regardless of zoom, with no
        # scene-distance/zoom-factor math needed.
        top_mid = anchor_points["n"]
        rotate_line = QGraphicsLineItem(0, 0, 0, -24)
        rotate_line.setPos(top_mid)
        rotate_line.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIgnoresTransformations)
        line_pen = QPen(QColor("#0A84FF"), 1)
        line_pen.setCosmetic(True)
        rotate_line.setPen(line_pen)
        rotate_line.setZValue(29)
        self.scene.addItem(rotate_line)
        self._handle_items["rotate_line"] = rotate_line

        rotate_handle = QGraphicsEllipseItem(-5, -29, 10, 10)
        rotate_handle.setPos(top_mid)
        rotate_handle.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIgnoresTransformations)
        rotate_pen = QPen(QColor("#0A84FF"), 1)
        rotate_pen.setCosmetic(True)
        rotate_handle.setPen(rotate_pen)
        rotate_handle.setBrush(QBrush(QColor("#FFFFFF")))
        rotate_handle.setZValue(30)
        rotate_handle.setCursor(self._HANDLE_CURSORS["rotate"])
        self.scene.addItem(rotate_handle)
        self._handle_items["rotate"] = rotate_handle

    def _handle_at(self, pos):
        """Which handle (if any) is under a viewport position -- checked
        before the general item-click logic in mousePressEvent, since
        handles visually overlap the selected item's own edges."""
        items_at = self.items(pos)
        for name, item in self._handle_items.items():
            if name == "rotate_line":
                continue
            if item in items_at:
                return name
        return None

    def _start_handle_drag(self, name, pos):
        selected_items = self._movable_selected_items()
        if not selected_items:
            return
        rect = selected_items[0].sceneBoundingRect()
        self._active_handle = name
        self._handle_drag_start_rect = QRectF(rect)
        self._handle_drag_center = rect.center()
        if name == "rotate":
            scene_pos = self.mapToScene(pos)
            self._handle_drag_start_angle = math.degrees(
                math.atan2(
                    scene_pos.y() - self._handle_drag_center.y(),
                    scene_pos.x() - self._handle_drag_center.x(),
                )
            )
        else:
            pen = QPen(QColor("#0A84FF"), 0, Qt.PenStyle.DashLine)
            pen.setCosmetic(True)
            self._handle_preview_item = QGraphicsRectItem(rect)
            self._handle_preview_item.setPen(pen)
            self._handle_preview_item.setZValue(28)
            self.scene.addItem(self._handle_preview_item)

    def _resize_preview_rect(self, pos):
        rect = QRectF(self._handle_drag_start_rect)
        scene_pos = self.mapToScene(pos)
        if "n" in self._active_handle:
            rect.setTop(scene_pos.y())
        if "s" in self._active_handle:
            rect.setBottom(scene_pos.y())
        if "w" in self._active_handle:
            rect.setLeft(scene_pos.x())
        if "e" in self._active_handle:
            rect.setRight(scene_pos.x())
        return rect.normalized()

    def _update_handle_drag(self, pos):
        if self._active_handle is None:
            return
        if self._active_handle == "rotate":
            scene_pos = self.mapToScene(pos)
            angle_now = math.degrees(
                math.atan2(
                    scene_pos.y() - self._handle_drag_center.y(),
                    scene_pos.x() - self._handle_drag_center.x(),
                )
            )
            delta = angle_now - self._handle_drag_start_angle
            self.cursor_position_changed.emit(scene_pos.x(), scene_pos.y())
            self._handle_rotation_live = delta
            # Live visual rotation of the actual shape during the drag.
            # QGraphicsItem.setRotation() is an ABSOLUTE angle (not
            # incremental), so setting it straight to the total delta
            # each move is correct -- no accumulation needed. This is
            # purely a Qt-level transform on top of the item's already-
            # rendered path; the real node data (and the item itself)
            # only change once, via the "rotate" console command +
            # render_elements() rebuild on release, same "preview during
            # drag, commit once" shape as the resize dashed-rect preview.
            selected_items = self._movable_selected_items()
            if selected_items:
                item = selected_items[0]
                item.setTransformOriginPoint(item.mapFromScene(self._handle_drag_center))
                item.setRotation(delta)
            return
        if self._handle_preview_item is not None:
            self._handle_preview_item.setRect(self._resize_preview_rect(pos))

    def _cancel_handle_drag(self):
        if self._handle_preview_item is not None:
            self.scene.removeItem(self._handle_preview_item)
        self._handle_preview_item = None
        if self._active_handle == "rotate":
            # Snap the live rotation preview back -- nothing was ever
            # committed to the real node data, only the on-screen item's
            # own transform was touched.
            for item in self._movable_selected_items():
                item.setRotation(0)
        self._active_handle = None
        self._handle_drag_start_rect = None
        self._handle_drag_center = None
        self._handle_drag_start_angle = None
        self._update_selection_handles()

    def _finish_handle_drag(self, pos):
        if self._active_handle is None:
            return
        name = self._active_handle
        if name == "rotate":
            scene_pos = self.mapToScene(pos)
            angle_now = math.degrees(
                math.atan2(
                    scene_pos.y() - self._handle_drag_center.y(),
                    scene_pos.x() - self._handle_drag_center.x(),
                )
            )
            delta = angle_now - self._handle_drag_start_angle
            self._active_handle = None
            self._handle_drag_start_rect = None
            self._handle_drag_center = None
            self._handle_drag_start_angle = None
            if abs(delta) < 0.5:
                # Accidental micro-drag (or a plain click on the handle)
                # -- not a real rotate gesture.
                self._update_selection_handles()
                return
            elements = getattr(self.context, "elements", None)
            if elements is None:
                return
            self.context.console(f"rotate {delta}deg\n")
            self.render_elements()
            self.selection_changed.emit(elements.first_emphasized)
            return

        rect = self._resize_preview_rect(pos)
        if self._handle_preview_item is not None:
            self.scene.removeItem(self._handle_preview_item)
        self._handle_preview_item = None
        self._active_handle = None
        self._handle_drag_start_rect = None

        if rect.width() < _MIN_DRAW_SIZE_MM or rect.height() < _MIN_DRAW_SIZE_MM:
            self._update_selection_handles()
            return
        elements = getattr(self.context, "elements", None)
        if elements is None:
            return
        self.context.console(
            f"resize {rect.x()}mm {rect.y()}mm {rect.width()}mm {rect.height()}mm\n"
        )
        self.render_elements()
        self.selection_changed.emit(elements.first_emphasized)

    def get_elements_bounding_rect(self, only_selected=False):
        """
        Calculate scene bounding rect of elements.
        If only_selected is True, bounding rect of selected items.
        If no items match or only_selected is empty, returns rect of all element items.
        If no element items exist, returns bed rect.
        """
        from PyQt6.QtCore import QRectF

        rects = []
        for item in self._element_items:
            if item.scene() is not self.scene:
                continue
            if only_selected and not item.isSelected():
                continue
            r = item.sceneBoundingRect()
            if not r.isEmpty() and r.width() > 0.01 and r.height() > 0.01:
                rects.append(r)

        if not rects and only_selected:
            for item in self._element_items:
                if item.scene() is not self.scene:
                    continue
                r = item.sceneBoundingRect()
                if not r.isEmpty() and r.width() > 0.01 and r.height() > 0.01:
                    rects.append(r)

        if not rects:
            return QRectF(0, 0, float(self.bed_width), float(self.bed_height))

        unified = rects[0]
        for r in rects[1:]:
            unified = unified.united(r)

        pad_x = max(5.0, unified.width() * 0.08)
        pad_y = max(5.0, unified.height() * 0.08)
        return unified.adjusted(-pad_x, -pad_y, pad_x, pad_y)

    def refresh_selection_highlight(self):
        """
        Re-apply pen/brush to the already-rendered items without touching
        their geometry -- for pure selection changes (click, tree click,
        select all, deselect all), which don't need the full
        render_elements() geometry rebuild (measured ~110ms for 300
        elements; a selection change alone should be near-instant).

        Only the items whose emphasis actually flipped (now emphasized,
        or was emphasized before this call) get restyled -- for a normal
        single-item click that's 1-2 items, not every rendered item, since
        every OTHER item's style is by definition unchanged: this method
        is only ever called for a pure selection change (see docstring
        above), so a node that was never emphasized and still isn't has
        nothing else that could have altered its pen/brush/z-value.
        """
        curr_emphasized_items = {
            item for item, node in self._item_to_node.items()
            if getattr(node, "emphasized", False)
        }
        for item in curr_emphasized_items | self._prev_emphasized_items:
            node = self._item_to_node.get(item)
            if node is None:
                continue
            pen, brush = self._style_for_node(node)
            item.setPen(pen)
            item.setBrush(brush)
            item.setZValue(11 if getattr(node, "emphasized", False) else 10)
        self._prev_emphasized_items = curr_emphasized_items
        self._update_selection_handles()

    def _style_for_node(self, node):
        if getattr(node, "emphasized", False):
            pen = QPen(QColor("#0A84FF"))
            pen.setWidth(2)
            pen.setCosmetic(True)  # fixed screen width regardless of zoom
        else:
            stroke = getattr(node, "stroke", None)
            # An explicitly unset/"none" stroke (some SVG imports; rarely
            # the default -- elements.default_stroke is blue, readable on
            # either background) still needs to show up somehow, but a
            # fixed light-gray fallback that reads fine against the dark
            # bed would be nearly invisible against the light theme's
            # white/light-gray one, and vice versa for a dark fallback.
            fallback = QColor("#E0E0E0") if self._is_dark_theme else QColor("#606060")
            pen_color = (
                self._node_color(stroke) if self._color_is_set(stroke) else fallback
            )
            pen = QPen(pen_color)
            pen.setWidth(0)  # cosmetic: always 1px on screen, regardless of zoom

        fill = getattr(node, "fill", None)
        brush = (
            QBrush(self._node_color(fill))
            if self._color_is_set(fill)
            else QBrush(Qt.BrushStyle.NoBrush)
        )
        return pen, brush

    @staticmethod
    def _color_is_set(color) -> bool:
        # svgelements represents an explicit `fill="none"`/unset color as a
        # Color instance whose components are None -- not Python None.
        return color is not None and getattr(color, "red", None) is not None

    @staticmethod
    def _node_color(color) -> QColor:
        alpha = color.alpha
        return QColor(color.red, color.green, color.blue, 255 if alpha is None else alpha)

    def drawBackground(self, painter: QPainter, rect: QRectF):
        super().drawBackground(painter, rect)
        painter.fillRect(rect, self.bg_color)

        # Draw Bed
        bed_rect = QRectF(0, 0, self.bed_width, self.bed_height)
        painter.fillRect(bed_rect, self.bed_color)

        # Draw Camera Overlay if active
        if self.camera_overlay_visible and self.camera_overlay_pixmap and not self.camera_overlay_pixmap.isNull():
            painter.save()
            painter.setOpacity(self.camera_overlay_opacity)
            painter.drawPixmap(bed_rect.toRect(), self.camera_overlay_pixmap)
            painter.restore()

        # Only iterate grid lines that actually fall within the exposed
        # scene rect -- looping the full bed extent on every repaint was
        # wasted work when zoomed in on a large bed (most of those lines
        # land off screen and would just be clipped away by Qt). Lines
        # still span the whole bed width/height once drawn, unchanged
        # visually, just fewer of them get issued.
        visible = rect.intersected(bed_rect)
        if not visible.isEmpty():

            def draw_grid(step, pen):
                painter.setPen(pen)
                x = int(visible.left() // step) * step
                while x <= visible.right():
                    if x >= 0:
                        painter.drawLine(QPointF(x, 0), QPointF(x, self.bed_height))
                    x += step
                y = int(visible.top() // step) * step
                while y <= visible.bottom():
                    if y >= 0:
                        painter.drawLine(QPointF(0, y), QPointF(self.bed_width, y))
                    y += step

            draw_grid(10.0, QPen(self.grid_secondary_color, 0.5))
            draw_grid(50.0, QPen(self.grid_primary_color, 1.0))

        # Outer bed border
        painter.setPen(QPen(self.border_color, 0.75))
        painter.drawRect(bed_rect)

        # Center Bed Measurements Watermark Overlay
        wr, wg, wb = self.watermark_rgb
        painter.setPen(QPen(QColor(wr, wg, wb, 110)))
        font = painter.font()
        font.setPointSize(13)
        font.setBold(True)
        painter.setFont(font)
        dim_text = f"[ {self.bed_width:.1f} mm  ×  {self.bed_height:.1f} mm ]"
        painter.drawText(bed_rect, Qt.AlignmentFlag.AlignCenter, dim_text)

        # LightBurn-Style Graduated Rulers (X Top Ruler & Y Left Ruler)
        ruler_pen = QPen(self.ruler_color, 0.8)
        painter.setPen(ruler_pen)
        ruler_font = painter.font()
        # drawBackground() runs with the painter already scaled by the
        # view's current zoom (unlike QGraphicsItem, which can opt out
        # per-item via ItemIgnoresTransformations) -- a flat point size
        # here gets zoomed right along with the bed grid, so at anything
        # above ~1x zoom the ruler numbers render far larger than an "8pt
        # label" should look. Dividing by the current scale keeps the
        # on-screen size roughly constant regardless of zoom level.
        zoom_scale = self.transform().m11() or 1.0
        ruler_font.setPointSizeF(max(1.0, 9.0 / zoom_scale))
        ruler_font.setBold(False)
        painter.setFont(ruler_font)

        # Top X Ruler (-100 to bed_width + 100)
        start_x = int((rect.left() // 20) * 20) - 20
        end_x = int(rect.right()) + 40
        for x in range(start_x, end_x, 10):
            tick_h = 6 if x % 20 == 0 else 3
            painter.drawLine(QPointF(x, -tick_h), QPointF(x, 0))
            if x % 20 == 0:
                painter.drawText(QRectF(x - 20, -22, 40, 16), Qt.AlignmentFlag.AlignCenter, str(x))

        # Left Y Ruler (-50 to bed_height + 50)
        start_y = int((rect.top() // 20) * 20) - 20
        end_y = int(rect.bottom()) + 40
        for y in range(start_y, end_y, 10):
            tick_w = 6 if y % 20 == 0 else 3
            painter.drawLine(QPointF(-tick_w, y), QPointF(0, y))
            if y % 20 == 0 and y >= 0:
                painter.drawText(QRectF(-35, y - 8, 30, 16), Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter, str(y))

    def _restore_antialiasing(self):
        self.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        self.viewport().update()

    def wheelEvent(self, event):
        self.zoom_step(1 if event.angleDelta().y() > 0 else -1)

    def zoom_step(self, direction):
        """Zoom in (direction > 0) or out (direction < 0) by one wheel-step."""
        # Disable AA during rapid zoom steps to keep frame rate high
        self.setRenderHint(QPainter.RenderHint.Antialiasing, False)
        factor = self.zoom_factor if direction > 0 else 1.0 / self.zoom_factor
        self.scale(factor, factor)
        self.zoom_changed.emit(self.transform().m11())
        self._aa_timer.start(120)

    def reset_zoom(self):
        """Back to 100% (1 scene unit == 1 screen pixel at no extra scale)."""
        self.resetTransform()
        self.zoom_changed.emit(1.0)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.MiddleButton or (
            event.button() == Qt.MouseButton.LeftButton
            and event.modifiers() & Qt.KeyboardModifier.ControlModifier
        ):
            self.is_panning = True
            self.pan_start = event.pos()
            self.setCursor(Qt.CursorShape.ClosedHandCursor)
            event.accept()
        elif event.button() == Qt.MouseButton.LeftButton and self.draw_mode == "text":
            # Text is placed with a single click (a prompt for the string
            # follows) rather than a click-drag rubber-band gesture.
            self._place_text(event.pos())
            event.accept()
        elif event.button() == Qt.MouseButton.LeftButton and self.draw_mode == "polygon":
            # Same single-click-then-dialog shape as Text above -- a
            # regular polygon/star doesn't have a natural drag gesture
            # the way rect/ellipse/line's two-corner drag does (dragging
            # would only set ONE dimension, not sides-count or star-vs-
            # regular), so a dialog after the click fills in the rest.
            self._place_polygon(event.pos())
            event.accept()
        elif event.button() == Qt.MouseButton.LeftButton and self.draw_mode is not None:
            self._start_draw(event.pos())
            event.accept()
        elif (
            event.button() == Qt.MouseButton.LeftButton
            and self.draw_mode is None
            and self._handle_at(event.pos()) is not None
        ):
            # Checked before the general item-click branch below --
            # handles visually overlap the selected item's own edges, so
            # this must win the hit-test first.
            self._start_handle_drag(self._handle_at(event.pos()), event.pos())
            event.accept()
        elif (
            event.button() == Qt.MouseButton.LeftButton
            and self.dragMode() != QGraphicsView.DragMode.ScrollHandDrag
        ):
            # Only claim plain left-click for selection when the "Main
            # (Pan)" tool hasn't put us in ScrollHandDrag -- otherwise this
            # was swallowing the click before Qt's own native pan-drag
            # handling (super().mousePressEvent) ever got a chance to run,
            # making that toolbar button change the cursor but do nothing.
            additive = bool(event.modifiers() & Qt.KeyboardModifier.ShiftModifier)
            items_at_pos = [it for it in self.items(event.pos()) if it in self._item_to_node]
            if items_at_pos:
                item = items_at_pos[0]
                node = self._item_to_node[item]
                if additive or not getattr(node, "emphasized", False):
                    self._select_at(event.pos(), additive=additive)
                if getattr(node, "emphasized", False):
                    self._move_start_scene = self.mapToScene(event.pos())
                    self._move_last_scene = self._move_start_scene
            else:
                self._start_rubber_band(event.pos(), additive=additive)
            event.accept()
        else:
            super().mousePressEvent(event)

    def _select_at(self, pos, additive=False):
        """
        Click-to-select: shares the same node.emphasized state the classic
        wx Scene uses, via elements.set_emphasis() -- so selecting here (or
        in a wx sub-window opened from this same session) stays consistent.

        additive=True (Shift+click) toggles the clicked node in/out of the
        existing selection instead of replacing it.
        """
        elements = getattr(self.context, "elements", None)
        if elements is None:
            return
        node = None
        for item in self.items(pos):
            if item in self._item_to_node:
                node = self._item_to_node[item]
                break
        if additive:
            current = list(elements.elems(emphasized=True))
            if node is not None:
                if any(n is node for n in current):
                    current = [n for n in current if n is not node]
                else:
                    current.append(node)
            elements.set_emphasis(current if current else None)
        else:
            elements.set_emphasis([node] if node is not None else None)
        self.refresh_selection_highlight()
        self.selection_changed.emit(node)

    def _start_rubber_band(self, pos, additive=False):
        self._rb_start = self.mapToScene(pos)
        self._rb_additive = additive
        pen = QPen(QColor("#0A84FF"), 0, Qt.PenStyle.DashLine)
        pen.setCosmetic(True)
        fill = QColor("#0A84FF")
        fill.setAlpha(40)
        self._rb_item = QGraphicsRectItem(QRectF(self._rb_start, self._rb_start))
        self._rb_item.setPen(pen)
        self._rb_item.setBrush(QBrush(fill))
        self._rb_item.setZValue(25)
        self.scene.addItem(self._rb_item)

    def _update_rubber_band(self, pos):
        rect = QRectF(self._rb_start, self.mapToScene(pos)).normalized()
        self._rb_item.setRect(rect)

    def _cancel_rubber_band(self):
        if self._rb_item is not None:
            self.scene.removeItem(self._rb_item)
        self._rb_item = None
        self._rb_start = None

    def _finish_rubber_band(self, pos):
        rect = QRectF(self._rb_start, self.mapToScene(pos)).normalized()
        additive = self._rb_additive
        self._cancel_rubber_band()

        elements = getattr(self.context, "elements", None)
        if elements is None:
            return
        selected = [
            node
            for item, node in self._item_to_node.items()
            if rect.intersects(item.sceneBoundingRect())
        ]
        if additive:
            current = list(elements.elems(emphasized=True))
            for node in selected:
                if node not in current:
                    current.append(node)
            selected = current
        elements.set_emphasis(selected if selected else None)
        self.refresh_selection_highlight()
        self.selection_changed.emit(selected[0] if selected else None)

    def _update_move(self, scene_pos):
        dx = scene_pos.x() - self._move_last_scene.x()
        dy = scene_pos.y() - self._move_last_scene.y()
        if dx == 0 and dy == 0:
            return
        self._move_active = True
        for item in self._movable_selected_items():
            item.moveBy(dx, dy)
        self._move_last_scene = scene_pos

    def _cancel_move(self):
        """Escape mid-drag: snap the dragged item(s) back to where they
        started (nothing has been committed to the real node data yet --
        only their on-screen position moved)."""
        if self._move_active:
            dx = self._move_start_scene.x() - self._move_last_scene.x()
            dy = self._move_start_scene.y() - self._move_last_scene.y()
            for item in self._movable_selected_items():
                item.moveBy(dx, dy)
        self._move_start_scene = None
        self._move_last_scene = None
        self._move_active = False

    def cancel_in_progress_gesture(self) -> bool:
        """Cancel whichever of draw/rubber-band/move is currently active.
        Called from MadGravQtMainWindow's Escape handling (Qt's window-level
        QAction shortcut intercepts Escape before this widget's own
        keyPressEvent ever sees it, so this can't live there). Returns
        True if something was actually cancelled, False if the canvas was
        idle -- the caller falls back to deselecting everything in that case.
        """
        if self._draw_start is not None:
            self._cancel_draw()
            return True
        if self._rb_start is not None:
            self._cancel_rubber_band()
            return True
        if self._move_start_scene is not None:
            self._cancel_move()
            return True
        if self._active_handle is not None:
            self._cancel_handle_drag()
            return True
        return False

    def _finish_move(self):
        if not self._move_active:
            # No real drag happened -- just a click, already handled (the
            # selection itself) at mousePressEvent time.
            self._move_start_scene = None
            self._move_last_scene = None
            return
        total_dx = self._move_last_scene.x() - self._move_start_scene.x()
        total_dy = self._move_last_scene.y() - self._move_start_scene.y()
        self._move_start_scene = None
        self._move_last_scene = None
        self._move_active = False

        elements = getattr(self.context, "elements", None)
        if elements is None:
            return
        # The item(s) are already visually at the right place (moved
        # incrementally during the drag) -- commit the total displacement
        # to the real node data in one command/undo-step, same reasoning
        # as the nudge fast path (no render_elements() rebuild needed).
        self.context.console(f"translate {total_dx}mm {total_dy}mm\n")
        self.selection_changed.emit(elements.first_emphasized)

    def mouseMoveEvent(self, event):
        scene_pos = self.mapToScene(event.pos())
        self.cursor_position_changed.emit(scene_pos.x(), scene_pos.y())

        if self.is_panning:
            delta = event.pos() - self.pan_start
            self.pan_start = event.pos()
            self.horizontalScrollBar().setValue(
                self.horizontalScrollBar().value() - delta.x()
            )
            self.verticalScrollBar().setValue(
                self.verticalScrollBar().value() - delta.y()
            )
            event.accept()
        elif self._draw_start is not None:
            self._update_draw_preview(event.pos())
            event.accept()
        elif self._rb_start is not None:
            self._update_rubber_band(event.pos())
            event.accept()
        elif self._move_start_scene is not None:
            self._update_move(scene_pos)
            event.accept()
        elif self._active_handle is not None:
            self._update_handle_drag(event.pos())
            event.accept()
        else:
            super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.MiddleButton or self.is_panning:
            self.is_panning = False
            self.setCursor(Qt.CursorShape.ArrowCursor)
            event.accept()
        elif event.button() == Qt.MouseButton.LeftButton and self._draw_start is not None:
            self._finish_draw(event.pos())
            event.accept()
        elif event.button() == Qt.MouseButton.LeftButton and self._rb_start is not None:
            self._finish_rubber_band(event.pos())
            event.accept()
        elif event.button() == Qt.MouseButton.LeftButton and self._move_start_scene is not None:
            self._finish_move()
            event.accept()
        elif event.button() == Qt.MouseButton.LeftButton and self._active_handle is not None:
            self._finish_handle_drag(event.pos())
            event.accept()
        else:
            super().mouseReleaseEvent(event)

    def _start_draw(self, pos):
        self._draw_start = self.mapToScene(pos)
        preview_pen = QPen(QColor("#0A84FF"), 0, Qt.PenStyle.DashLine)
        preview_pen.setCosmetic(True)
        if self.draw_mode == "ellipse":
            self._draw_preview = QGraphicsEllipseItem(
                QRectF(self._draw_start, self._draw_start)
            )
        elif self.draw_mode == "line":
            self._draw_preview = QGraphicsLineItem(
                QLineF(self._draw_start, self._draw_start)
            )
        else:
            self._draw_preview = QGraphicsRectItem(
                QRectF(self._draw_start, self._draw_start)
            )
        self._draw_preview.setPen(preview_pen)
        if self.draw_mode != "line":
            self._draw_preview.setBrush(QBrush(Qt.BrushStyle.NoBrush))
        self._draw_preview.setZValue(20)
        self.scene.addItem(self._draw_preview)

    def _update_draw_preview(self, pos):
        current = self.mapToScene(pos)
        if self.draw_mode == "line":
            self._draw_preview.setLine(QLineF(self._draw_start, current))
        else:
            self._draw_preview.setRect(QRectF(self._draw_start, current).normalized())

    def _cancel_draw(self):
        if self._draw_preview is not None:
            self.scene.removeItem(self._draw_preview)
        self._draw_preview = None
        self._draw_start = None

    def _finish_draw(self, pos):
        current = self.mapToScene(pos)
        start = self._draw_start
        mode = self.draw_mode
        self._cancel_draw()

        if mode == "line":
            length = QLineF(start, current).length()
            if length < _MIN_DRAW_SIZE_MM:
                return  # Treat as an accidental click, not a real line.
            command = f"line {start.x()}mm {start.y()}mm {current.x()}mm {current.y()}mm\n"
        else:
            rect = QRectF(start, current).normalized()
            if rect.width() < _MIN_DRAW_SIZE_MM or rect.height() < _MIN_DRAW_SIZE_MM:
                return  # Treat as an accidental click, not a real shape.
            if mode == "ellipse":
                cx = rect.center().x()
                cy = rect.center().y()
                rx = rect.width() / 2
                ry = rect.height() / 2
                command = f"ellipse {cx}mm {cy}mm {rx}mm {ry}mm\n"
            else:
                command = (
                    f"rect {rect.x()}mm {rect.y()}mm "
                    f"{rect.width()}mm {rect.height()}mm"
                )
                # "rect"'s own -x/-y options are the rounded rx/ry corner
                # radii (madgrav/core/elements/shapes.py) -- already fully
                # supported by the backend, just never exposed by this
                # tool before. rect_corner_radius_mm is set from the tool
                # panel's spinbox (qt_main.py), 0 by default (sharp
                # corners), so this only adds the flags when actually
                # asked for.
                if self.rect_corner_radius_mm > 0:
                    command += (
                        f" -x {self.rect_corner_radius_mm}mm"
                        f" -y {self.rect_corner_radius_mm}mm"
                    )
                command += "\n"

        elements = getattr(self.context, "elements", None)
        if elements is None:
            return
        self.context.console(command)
        self.render_elements()
        self.shape_created.emit()

    def _place_text(self, pos):
        # The "text" console command always creates at the origin; chain
        # a "position" command to place it where the user clicked (its
        # target is the bounding-box top-left, not the click point itself,
        # same as every other draw tool here).
        from PyQt6.QtWidgets import QInputDialog

        scene_pos = self.mapToScene(pos)
        text, ok = QInputDialog.getText(self, "Nouveau texte", "Texte :")
        if not ok or not text:
            return  # Cancelled or empty: stay in the Text tool, like an
            # under-sized drag leaves the Rectangle/Cercle/Ligne tools active.
        # The console parser has no escape sequence for a literal double
        # quote inside a quoted argument -- fold it to a single quote
        # rather than let it terminate the string early.
        safe_text = text.replace('"', "'")
        command = f'text "{safe_text}" position {scene_pos.x()}mm {scene_pos.y()}mm\n'
        elements = getattr(self.context, "elements", None)
        if elements is None:
            return
        self.context.console(command)
        self.render_elements()
        self.shape_created.emit()

    def _place_polygon(self, pos):
        # Unlike rect/ellipse/line, a regular polygon/star has no natural
        # two-corner drag gesture -- a drag only fixes one dimension, not
        # the sides count or star-vs-regular choice -- so this follows
        # _place_text's shape instead: one click for the center, then a
        # dialog for the rest. "polygon" (madgrav/core/elements/shapes.py)
        # takes an explicit flat list of point coordinates, not a
        # center+radius+sides convenience form, so the vertices are
        # computed here and passed through as literal points.
        import math

        from PyQt6.QtWidgets import (
            QCheckBox,
            QDialog,
            QDialogButtonBox,
            QDoubleSpinBox,
            QFormLayout,
            QSpinBox,
        )

        scene_pos = self.mapToScene(pos)

        dlg = QDialog(self)
        dlg.setWindowTitle("Nouveau Polygone")
        form = QFormLayout(dlg)
        sides_spin = QSpinBox(dlg)
        sides_spin.setRange(3, 100)
        sides_spin.setValue(6)
        radius_spin = QDoubleSpinBox(dlg)
        radius_spin.setRange(0.1, 1000)
        radius_spin.setDecimals(2)
        radius_spin.setSuffix(" mm")
        radius_spin.setValue(10.0)
        star_check = QCheckBox("Étoile", dlg)
        form.addRow("Côtés / Branches :", sides_spin)
        form.addRow("Rayon :", radius_spin)
        form.addRow(star_check)
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel,
            dlg,
        )
        buttons.accepted.connect(dlg.accept)
        buttons.rejected.connect(dlg.reject)
        form.addRow(buttons)

        if dlg.exec() != QDialog.DialogCode.Accepted:
            return

        sides = sides_spin.value()
        radius = radius_spin.value()
        cx, cy = scene_pos.x(), scene_pos.y()

        points = []
        if star_check.isChecked():
            inner_radius = radius * 0.5
            for i in range(sides * 2):
                r = radius if i % 2 == 0 else inner_radius
                angle = math.pi * i / sides - math.pi / 2
                points.append((cx + r * math.cos(angle), cy + r * math.sin(angle)))
        else:
            for i in range(sides):
                angle = 2 * math.pi * i / sides - math.pi / 2
                points.append((cx + radius * math.cos(angle), cy + radius * math.sin(angle)))

        coords = " ".join(f"{x}mm {y}mm" for x, y in points)
        command = f"polygon {coords}\n"
        elements = getattr(self.context, "elements", None)
        if elements is None:
            return
        self.context.console(command)
        self.render_elements()
        self.shape_created.emit()

    # Arrow key -> (dx, dy) in mm, matching madgrav/core/bindalias.py's
    # "right"/"left"/"up"/"down" bindings (10mm with Shift, like "shift+right" etc.)
    _NUDGE_DIRECTIONS = {
        Qt.Key.Key_Right: (1, 0),
        Qt.Key.Key_Left: (-1, 0),
        Qt.Key.Key_Up: (0, -1),
        Qt.Key.Key_Down: (0, 1),
    }

    def keyPressEvent(self, event):
        # Escape is deliberately NOT handled here: MadGravQtMainWindow's
        # "Tout Desélectionner" menu action has a window-level "Escape"
        # QAction shortcut, and Qt's shortcut map intercepts a matching key
        # press before it ever reaches a focused widget's keyPressEvent --
        # so an Escape branch placed here would never actually run. See
        # MadGravQtMainWindow._on_escape_pressed for the real handler,
        # which cancels an in-progress draw/rubber-band/move here first
        # and only falls back to deselecting everything.
        if event.key() in (Qt.Key.Key_Delete, Qt.Key.Key_Backspace):
            self._delete_emphasized()
            event.accept()
        elif event.key() in self._NUDGE_DIRECTIONS:
            dx, dy = self._NUDGE_DIRECTIONS[event.key()]
            step = 10 if event.modifiers() & Qt.KeyboardModifier.ShiftModifier else 1
            self._nudge_emphasized(dx * step, dy * step)
            event.accept()
        else:
            super().keyPressEvent(event)

    def _nudge_emphasized(self, dx_mm, dy_mm):
        """Fine-move the selection by arrow keys -- same 'translate' console
        command the classic wx UI's arrow-key bindings use."""
        elements = getattr(self.context, "elements", None)
        # NOT elements.first_emphasized is None -- that becomes None
        # whenever MULTIPLE elements are emphasized with no prior single
        # selection (elements.py: "it makes no sense to define a 'first'
        # here, as all are equal"), e.g. right after a rubber-band
        # multi-select. translate/delete apply to the WHOLE selection, so
        # gating on first_emphasized silently broke arrow-key nudge and
        # the Delete key for exactly that (very common) selection style.
        if elements is None or not any(elements.elems(emphasized=True)):
            return
        self.context.console(f"translate {dx_mm}mm {dy_mm}mm\n")
        # Fast path: translate() only moves the node, it doesn't change its
        # shape, so shift the matching graphics item in place instead of
        # rebuilding every element's path from scratch (measured ~110ms for
        # 300 elements -- laggy if the user holds an arrow key down).
        for item in self._movable_selected_items():
            item.moveBy(dx_mm, dy_mm)
        # Keep any numeric position readout (e.g. the Position/Taille dock)
        # in sync with the nudge -- cheap (no geometry rebuild), unlike the
        # fast path above this only touches two spin box values.
        self.selection_changed.emit(elements.first_emphasized)

    def _delete_emphasized(self):
        """Delete the selected element(s) -- same 'element delete' console
        command the classic wx UI's Delete key runs (madgrav/core/bindalias.py)."""
        elements = getattr(self.context, "elements", None)
        # NOT elements.first_emphasized is None -- that becomes None
        # whenever MULTIPLE elements are emphasized with no prior single
        # selection (elements.py: "it makes no sense to define a 'first'
        # here, as all are equal"), e.g. right after a rubber-band
        # multi-select. translate/delete apply to the WHOLE selection, so
        # gating on first_emphasized silently broke arrow-key nudge and
        # the Delete key for exactly that (very common) selection style.
        if elements is None or not any(elements.elems(emphasized=True)):
            return
        deleted_nodes = set(elements.elems(emphasized=True))
        self.context.console("element delete\n")
        # Fast path: remove just the deleted items' graphics instead of
        # rebuilding every remaining element's path from scratch (same
        # reasoning as the nudge/move fast paths -- measured ~110ms for
        # 300 elements). Both _item_to_node and _element_items need to
        # stay in sync, or a later full render_elements() would try to
        # remove these same items from the scene a second time.
        for item, node in list(self._item_to_node.items()):
            if node in deleted_nodes:
                self.scene.removeItem(item)
                del self._item_to_node[item]
                if item in self._element_items:
                    self._element_items.remove(item)
        self.selection_changed.emit(None)
