"""
Interactive QGraphicsView Canvas for MadGrav PyQt6 GUI.
Renders laser bed grid, laser origin, vector nodes, and interactive element selection.
"""

from PyQt6.QtCore import QLineF, QPointF, QRectF, Qt, pyqtSignal
from PyQt6.QtGui import QBrush, QColor, QPainter, QPainterPath, QPen
from PyQt6.QtWidgets import (
    QGraphicsEllipseItem,
    QGraphicsLineItem,
    QGraphicsRectItem,
    QGraphicsScene,
    QGraphicsView,
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

        self.setRenderHints(
            QPainter.RenderHint.Antialiasing
            | QPainter.RenderHint.SmoothPixmapTransform
            | QPainter.RenderHint.TextAntialiasing
        )

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

        # Colors
        self.bg_color = QColor("#14141A")
        self.bed_color = QColor("#1C1C26")
        self.grid_primary_color = QColor("#2E2E40")
        self.grid_secondary_color = QColor("#222230")
        self.border_color = QColor("#0A84FF")
        self._is_dark_theme = True

        self.zoom_factor = 1.15
        self.is_panning = False
        self.pan_start = QPointF()

        self._element_items = []
        self._item_to_node = {}

        # Draw-tool state (rectangle/ellipse/line rubber-band creation).
        self.draw_mode = None  # None | "rect" | "ellipse" | "line" | "text"
        self._draw_start = None
        self._draw_preview = None

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

        self.init_scene()
        self.render_elements()

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
        self.scene.setBackgroundBrush(QBrush(self.bg_color))

        # Add Bed rectangle
        bed_rect = QRectF(0, 0, self.bed_width, self.bed_height)
        self.bed_item = self.scene.addRect(
            bed_rect,
            QPen(self.border_color, 1.5, Qt.PenStyle.SolidLine),
            QBrush(self.bed_color),
        )

        # Origin indicator
        origin_pen = QPen(QColor("#FF3B30"), 2)
        self.scene.addLine(-5, 0, 15, 0, origin_pen)
        origin_pen_y = QPen(QColor("#30D158"), 2)
        self.scene.addLine(0, -5, 0, 15, origin_pen_y)

        self.setSceneRect(-50, -50, self.bed_width + 100, self.bed_height + 100)

    def set_theme(self, dark: bool):
        """Swap the bed/grid colors the QSS stylesheet can't reach (this
        widget paints its background/grid directly in drawBackground()
        instead of via CSS, since QGraphicsView content isn't styleable
        that way). Called by MadGravQtMainWindow's theme toggle alongside
        setStyleSheet() so the canvas doesn't stay dark while the rest of
        the window goes light, or vice versa."""
        self._is_dark_theme = dark
        if dark:
            self.bg_color = QColor("#14141A")
            self.bed_color = QColor("#1C1C26")
            self.grid_primary_color = QColor("#2E2E40")
            self.grid_secondary_color = QColor("#222230")
        else:
            self.bg_color = QColor("#E8E8ED")
            self.bed_color = QColor("#FFFFFF")
            self.grid_primary_color = QColor("#C4C4CE")
            self.grid_secondary_color = QColor("#E0E0E6")
        # border_color (#0A84FF) is the shared accent blue -- unchanged in
        # both themes, so it isn't reassigned here.
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

    def refresh_selection_highlight(self):
        """
        Re-apply pen/brush to the already-rendered items without touching
        their geometry -- for pure selection changes (click, tree click,
        select all, deselect all), which don't need the full
        render_elements() geometry rebuild (measured ~110ms for 300
        elements; a selection change alone should be near-instant).
        """
        for item, node in self._item_to_node.items():
            pen, brush = self._style_for_node(node)
            item.setPen(pen)
            item.setBrush(brush)
            item.setZValue(11 if getattr(node, "emphasized", False) else 10)

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
        painter.setPen(QPen(self.border_color, 1.5))
        painter.drawRect(bed_rect)

    def wheelEvent(self, event):
        self.zoom_step(1 if event.angleDelta().y() > 0 else -1)

    def zoom_step(self, direction):
        """Zoom in (direction > 0) or out (direction < 0) by one wheel-step."""
        factor = self.zoom_factor if direction > 0 else 1.0 / self.zoom_factor
        self.scale(factor, factor)
        self.zoom_changed.emit(self.transform().m11())

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
        elif event.button() == Qt.MouseButton.LeftButton and self.draw_mode is not None:
            self._start_draw(event.pos())
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
            item = self.itemAt(event.pos())
            if item is not None and item in self._item_to_node:
                node = self._item_to_node[item]
                # Clicking an item that's already part of the (possibly
                # multi-element) selection keeps that selection as-is, so a
                # drag from here moves the whole group. Otherwise select
                # first, same as before.
                if additive or not getattr(node, "emphasized", False):
                    self._select_at(event.pos(), additive=additive)
                if getattr(node, "emphasized", False):
                    self._move_start_scene = self.mapToScene(event.pos())
                    self._move_last_scene = self._move_start_scene
            else:
                # Empty space (or the bed/grid background, neither of
                # which is a selectable element): start a rubber-band drag
                # instead. A plain click-without-drag degrades to a
                # zero-size rect that selects nothing, which still gives
                # the classic "click empty space to deselect" behavior.
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
        item = self.itemAt(pos)
        node = self._item_to_node.get(item)
        if additive:
            current = list(elements.elems(emphasized=True))
            if node is not None:
                if node in current:
                    current.remove(node)
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
                    f"{rect.width()}mm {rect.height()}mm\n"
                )

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
        if elements is None or elements.first_emphasized is None:
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
        if elements is None or elements.first_emphasized is None:
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
