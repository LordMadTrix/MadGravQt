"""
Main QMainWindow for MadGrav PyQt6 GUI.
Features top action toolbar, left tool panel, interactive canvas, right dock inspector, and console dock.
"""

import os
import re
import time

from PyQt6.QtCore import QSettings, QSize, Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QAction, QKeySequence
from PyQt6.QtWidgets import (
    QApplication,
    QButtonGroup,
    QComboBox,
    QDockWidget,
    QDoubleSpinBox,
    QFileDialog,
    QFormLayout,
    QGraphicsView,
    QGridLayout,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMenu,
    QMessageBox,
    QPlainTextEdit,
    QProgressBar,
    QPushButton,
    QStatusBar,
    QToolBar,
    QToolButton,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)

from madgrav.qt.qt_canvas import MadGravQtCanvas
from madgrav.qt.qt_theme import (
    MODERN_DARK_QSS,
    MODERN_LIGHT_QSS,
    build_app_icon,
    build_tool_icon,
)

_ANSI_ESCAPE_RE = re.compile(r"\x1b\[[0-9;]*m")


class ConsoleLineEdit(QLineEdit):
    """QLineEdit with Up/Down command history, like a real terminal."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._history = []
        self._history_index = 0
        self._pending_text = ""

    def record(self, command: str):
        if not self._history or self._history[-1] != command:
            self._history.append(command)
        self._history_index = len(self._history)
        self._pending_text = ""

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Up:
            self._navigate_history(-1)
            event.accept()
        elif event.key() == Qt.Key.Key_Down:
            self._navigate_history(1)
            event.accept()
        else:
            super().keyPressEvent(event)

    def _navigate_history(self, direction):
        if not self._history:
            return
        if self._history_index == len(self._history):
            self._pending_text = self.text()
        new_index = max(0, min(len(self._history), self._history_index + direction))
        if new_index == self._history_index:
            return
        self._history_index = new_index
        if new_index == len(self._history):
            self.setText(self._pending_text)
        else:
            self.setText(self._history[new_index])


class MadGravQtMainWindow(QMainWindow):
    """
    Modern PyQt6 Main Window for MadGrav.
    """

    # Kernel signals can arrive on a different thread (the wx-driven
    # scheduler, still running in the background even under --qt). Qt
    # widgets may only be touched from the Qt GUI thread, so the kernel
    # listener below only ever emits this signal; Qt's queued-connection
    # machinery marshals the actual UI update onto the right thread.
    document_changed = pyqtSignal()

    # The kernel can be told to shut down from a non-Qt thread (a telnet
    # consoleserver connection, a background device error, etc.). Same
    # cross-thread rule as document_changed above: emit the signal, let
    # Qt's queued-connection machinery marshal close() onto the GUI thread.
    shutdown_requested = pyqtSignal()

    # The kernel's "console" channel (results, echoed syntax errors, etc.)
    # can be written to from any thread a console command happens to run
    # on. Same cross-thread rule as above: the channel watcher below only
    # emits this signal.
    console_output_received = pyqtSignal(str)

    # The active device can change from anywhere -- the Qt device combo,
    # the device wizard, a typed "device activate" console command, a
    # remote consoleserver connection -- not just Qt-triggered actions
    # (those already call _refresh_device_status() directly). The kernel
    # signals "activate;device" for all of them alike; same cross-thread
    # rule as the signals above.
    device_activated = pyqtSignal()

    # elements.set_emphasis() -- what ANY selection change goes through,
    # Qt's own canvas clicks included -- reliably fires "refresh_tree"
    # (never "refresh_scene", confirmed by direct testing), but does NOT
    # fire it when the change came from Qt's own canvas, which already
    # refreshes itself directly. So this only matters for selection/tree
    # changes from elsewhere: a typed "element* select", a wx Elements
    # tree click, an operation added/removed from a wx panel. Same
    # cross-thread rule as the signals above.
    tree_refresh_needed = pyqtSignal()

    # "pause"/"pipe;running" can fire many times a second while a job is
    # actively spooling -- deliberately routed to a lightweight status-
    # label-only refresh, NOT device_activated's bed-sync-plus-full-
    # canvas-redraw, which would visibly lag the UI during exactly the
    # moment a responsive STOP button matters most. Same cross-thread
    # rule as the signals above.
    device_status_changed = pyqtSignal()

    # Fired by the kernel whenever the undo stack changes -- every mark(),
    # not just Undo/Redo themselves. Same cross-thread rule as above.
    undo_redo_changed = pyqtSignal()

    # Fired by clipboard copy/cut (madgrav/core/elements/clipboard.py) --
    # narrow, clipboard-only signal (verified only those two call sites
    # use it). Same cross-thread rule as above.
    paste_state_changed = pyqtSignal()

    # Fired by arm/disarm from EITHER UI (madgrav/gui/wxmmain.py:
    # arm_laser/disarm_laser, and this window's own _on_toggle_arm) --
    # keeps the two in sync in a mixed wx+Qt session. Same cross-thread
    # rule as above.
    arm_state_changed = pyqtSignal()

    # Fired by coolant_toggle()/coolant_on()/coolant_off() (madgrav/
    # extra/coolant.py) -- from EITHER a manual toggle or the automatic
    # per-operation coolant commands the job plan issues during a run
    # (madgrav/core/cutplan.py), so this button's displayed state stays
    # correct even while a job is actively controlling coolant itself.
    # Same cross-thread rule as above.
    coolant_state_changed = pyqtSignal()

    # Fired by "spooler;queue" (job added/removed from the spooler) and
    # "spooler;completed" (job finished) -- these bracket when a job
    # progress indicator should appear/disappear/refresh immediately.
    # Ongoing in-job progress itself is polled by a QTimer instead of
    # listening to wx's much hotter "driver;position"/"emulator;position"
    # signals (fired on every motion update, many times a second during a
    # burn) -- a 1s poll is plenty for a remaining-time display and avoids
    # flooding the Qt event loop with cross-thread emits. Same cross-
    # thread rule as above.
    job_progress_changed = pyqtSignal()

    _BASE_TITLE = "MadGrav - PyQt6 Modern Laser Workstation"

    def __init__(self, context, path="qt"):
        super().__init__()
        self.context = context
        self.path = path
        self.current_file_path = None
        self._dirty = False
        # Set by _on_kernel_shutdown_requested right before it calls
        # close() -- closeEvent uses this to skip the unsaved-changes
        # prompt for a kernel-initiated shutdown (typed "quit", "-e
        # quit", a remote consoleserver disconnect...). A blocking modal
        # dialog there would hang headless/scripted shutdowns indefinitely
        # instead of the clean, prompt-free exit those already rely on.
        self._closing_from_kernel = False
        self._concerns = []
        # The node the "Dupliquer"/"Supprimer" tree buttons act on -- set
        # from _on_tree_item_clicked()'s own item argument rather than
        # QTreeWidget.currentItem()/itemSelectionChanged, which don't
        # reliably reflect a click here (confirmed: itemClicked always
        # fires, but the tree's internal selection model does not
        # consistently update from it in this app -- matches why every
        # other click handler in this class reads the item passed to the
        # signal directly instead of querying selection state back).
        self._tree_action_node = None
        self._dark_theme = self.context.setting(bool, "qt_dark_theme", True)
        # Service/device startup (e.g. activating the default device) can
        # itself fire a "refresh_scene" signal -- unrelated to any real
        # user edit -- shortly after this window's own kernel listeners
        # register, delivered asynchronously via Qt's cross-thread queued
        # connection so it lands a moment after __init__ returns, not
        # during it. Without this grace window, simply opening the app and
        # immediately closing it (nothing touched) could show the unsaved-
        # changes prompt for a document that was never actually modified.
        self._startup_settling = True

        self._update_window_title()
        app_icon = build_app_icon()
        self.setWindowIcon(app_icon)
        # Also set it at the QApplication level so child dialogs that
        # don't set their own icon (device wizard, message boxes) inherit
        # the same branding instead of Qt's generic default.
        app = QApplication.instance()
        if app is not None:
            app.setWindowIcon(app_icon)
        self.resize(1380, 860)
        self.setAcceptDrops(True)

        # Apply QSS Theme (persisted user choice, default dark)
        self.setStyleSheet(MODERN_DARK_QSS if self._dark_theme else MODERN_LIGHT_QSS)

        self._setup_ui()
        # The canvas paints its own bed/grid colors directly (drawBackground())
        # rather than via the QSS above, which can't reach QGraphicsView
        # content -- apply the same persisted choice there too, or a
        # light-theme session would still start with a dark canvas.
        self.canvas.set_theme(self._dark_theme)
        self._restore_window_state()
        self._update_warnings_indicator()

        # Console-channel messages are coalesced into one appendPlainText()
        # per short window instead of one per message -- a verbose channel
        # relayed into "console" (e.g. "channel open usb" during a job) can
        # fire many times a second, and a widget update per message would
        # visibly lag the UI. Matches the classic wx console panel's own
        # buffering (madgrav/gui/consolepanel.py), just simpler since this
        # dock has no separate real-time toggle.
        self._console_buffer = []
        self._console_flush_timer = QTimer(self)
        self._console_flush_timer.setSingleShot(True)
        self._console_flush_timer.setInterval(50)
        self._console_flush_timer.timeout.connect(self._flush_console_buffer)

        # "refresh_tree" fires on every pure SELECTION change too (a click,
        # a drag-select, arrow-key nudging), not just structural edits --
        # elements.set_emphasis() (madgrav/core/elements/elements.py) signals
        # it whenever any node's emphasized/highlighted/selected/targeted
        # flags change, which is on every click. _refresh_operations_tree()
        # itself does a full clear()+rebuild of every QTreeWidgetItem, which
        # measured ~13ms for a moderately large tree (75 top-level ops,
        # ~800 items total) -- fine for one click, but a rapid burst (drag-
        # select, holding an arrow key) would fire it many times in quick
        # succession. Coalesce those into a single rebuild after the burst
        # settles, same debounce pattern as the console buffer above.
        self._ops_tree_refresh_timer = QTimer(self)
        self._ops_tree_refresh_timer.setSingleShot(True)
        self._ops_tree_refresh_timer.setInterval(60)
        self._ops_tree_refresh_timer.timeout.connect(self._refresh_operations_tree)

        self.document_changed.connect(self._on_document_changed)
        self.shutdown_requested.connect(self._on_kernel_shutdown_requested)
        self.console_output_received.connect(self._on_console_output_received)
        self.device_activated.connect(self._on_device_activated)
        self.tree_refresh_needed.connect(self._on_tree_refresh_needed)
        self.device_status_changed.connect(self._refresh_device_status)
        self.undo_redo_changed.connect(self._update_undo_redo_actions)
        self.paste_state_changed.connect(self._update_paste_action)
        self.arm_state_changed.connect(self._update_arm_button)
        self.coolant_state_changed.connect(self._update_coolant_button)
        self.job_progress_changed.connect(self._update_job_progress)
        self._job_timer = QTimer(self)
        self._job_timer.setInterval(1000)
        self._job_timer.timeout.connect(self._update_job_progress)
        self.context.listen("refresh_scene", self._on_kernel_refresh_scene)
        self.context.listen("refresh_tree", self._on_kernel_refresh_tree)
        # The canonical signal the wx Operations tree itself listens to
        # for a property change (speed, power, label...) on an element or
        # operation -- e.g. from the "Information sur l'Opération" window
        # -- fired far more often than "refresh_tree" itself for this
        # class of change (madgrav/gui/propertypanels/attributes.py).
        # Without this, editing speed/power in a wx panel would leave
        # Qt's operations tree showing the old values indefinitely.
        self.context.listen("element_property_update", self._on_kernel_refresh_tree)
        self.context.listen("activate;device", self._on_kernel_device_activated)
        # A device can also change while it STAYS active -- renamed, or
        # reconfigured (e.g. its bed size edited) via the wx Device
        # Configuration window -- which "activate;device" alone wouldn't
        # catch since no re-activation happens. Same refresh either way.
        self.context.listen("device;modified", self._on_kernel_device_activated)
        self.context.listen("device;renamed", self._on_kernel_device_activated)
        # Job running/paused state -- was previously only visible by
        # opening the wx Spooler window; now reflected live in the
        # existing device-status label.
        self.context.listen("pause", self._on_kernel_device_status_changed)
        self.context.listen("pipe;running", self._on_kernel_device_status_changed)
        self.context.listen("undoredo", self._on_kernel_undoredo_changed)
        self.context.listen("icons", self._on_kernel_paste_state_changed)
        self.context.listen("laser_armed", self._on_kernel_arm_state_changed)
        self.context.listen("coolant_set", self._on_kernel_coolant_state_changed)
        self.context.listen("coolant_changed", self._on_kernel_coolant_changed)
        self.context.listen("spooler;queue", self._on_kernel_job_progress)
        self.context.listen("spooler;completed", self._on_kernel_job_progress)
        self.context.channel("console").watch(self._on_console_channel_message)
        QTimer.singleShot(300, self._end_startup_settling)

    def _on_kernel_refresh_scene(self, origin, *args):
        # Called from the kernel's signal-processing thread -- do not touch
        # Qt widgets here, just hand off to the GUI thread.
        self.document_changed.emit()

    def _on_kernel_shutdown_requested(self):
        # Marks this close as kernel-initiated BEFORE calling close(), so
        # closeEvent skips the unsaved-changes prompt below -- see
        # _closing_from_kernel's own comment in __init__ for why.
        self._closing_from_kernel = True
        self.close()

    def _on_kernel_device_status_changed(self, origin, *args):
        # Called from whatever thread reported the pause/running state
        # change (often the spooler thread) -- do not touch Qt widgets
        # here, just hand off to the GUI thread.
        self.device_status_changed.emit()

    def _on_kernel_undoredo_changed(self, origin, *args):
        # Called from whatever thread mutated the undo stack -- do not
        # touch Qt widgets here, just hand off to the GUI thread.
        self.undo_redo_changed.emit()

    def _on_kernel_paste_state_changed(self, origin, *args):
        # Called from whatever thread performed the clipboard copy/cut --
        # do not touch Qt widgets here, just hand off to the GUI thread.
        self.paste_state_changed.emit()

    def _on_kernel_arm_state_changed(self, origin, *args):
        # Called from whatever thread toggled arm/disarm (a wx panel, in
        # a mixed session) -- do not touch Qt widgets here, just hand off
        # to the GUI thread.
        self.arm_state_changed.emit()

    def _on_kernel_coolant_state_changed(self, origin, *args):
        # Called from whatever thread changed coolant state (a wx panel,
        # or the job plan's own automatic coolant_on/off during a run) --
        # do not touch Qt widgets here, just hand off to the GUI thread.
        self.coolant_state_changed.emit()

    def _on_kernel_coolant_changed(self, origin, *args):
        # Fired when a device's coolant METHOD choice changes (e.g. via
        # the wx Device Configuration window's dropdown) -- claim_coolant
        # only registers a device with the coolant system once, at
        # device construction, using whatever device_coolant value it had
        # *then* (madgrav/grbl/device.py etc.). Changing the setting
        # afterward needs an explicit re-claim, same as the classic wx
        # UI's own handler (madgrav/gui/wxmscene.py: on_coolant_changed),
        # or this button would keep reflecting a stale claim -- wrong, or
        # simply invisible if the device wasn't claimed at all yet.
        # claim_coolant() itself only mutates plain Python state (no Qt
        # widgets), so it's safe to call directly from this thread.
        device = getattr(self.context, "device", None)
        coolant = self._coolant_service()
        if device is not None and coolant is not None and hasattr(device, "device_coolant"):
            coolid = device.device_coolant or None
            coolant.claim_coolant(device, coolid)
        self.coolant_state_changed.emit()

    def _on_kernel_job_progress(self, origin, *args):
        # Called from whatever thread reported the spooler queue change or
        # job completion (often the spooler thread itself) -- do not touch
        # Qt widgets here, just hand off to the GUI thread.
        self.job_progress_changed.emit()

    def _on_kernel_device_activated(self, origin, *args):
        # Called from whatever thread performed the device switch/change --
        # do not touch Qt widgets here, just hand off to the GUI thread.
        self.device_activated.emit()

    def _on_kernel_refresh_tree(self, origin, *args):
        # Called from whatever thread changed the selection/tree -- do not
        # touch Qt widgets here, just hand off to the GUI thread.
        self.tree_refresh_needed.emit()

    def _on_tree_refresh_needed(self):
        self._ops_tree_refresh_timer.start()
        # Fast path (re-style already-rendered items), not a full
        # render_elements() rebuild -- this fires on every selection
        # change and render_elements() alone measured ~110ms for 300
        # elements (see refresh_selection_highlight's own docstring).
        self.canvas.refresh_selection_highlight()
        self._update_selection_dependent_actions()
        self._update_position_panel()

    def _on_device_activated(self):
        # The new device can have different bed dimensions -- without
        # this the canvas keeps drawing the PREVIOUS device's work-area
        # boundary after switching, which is actively misleading for a
        # laser cutter (elements placed "near the edge" of what's shown
        # may not be near the real bed edge at all).
        self.canvas._sync_bed_from_device()
        self.canvas.init_scene()
        self.canvas.render_elements()
        self._refresh_device_status()
        self._update_coolant_button()

    def _on_console_channel_message(self, text):
        # Called from whatever thread issued the console command -- do not
        # touch Qt widgets here, just hand off to the GUI thread.
        self.console_output_received.emit(text)

    def _on_console_output_received(self, text):
        self._console_buffer.append(_ANSI_ESCAPE_RE.sub("", text))
        if not self._console_flush_timer.isActive():
            self._console_flush_timer.start()

    def _flush_console_buffer(self):
        if self._console_buffer:
            self.console_output.appendPlainText("\n".join(self._console_buffer))
            self._console_buffer.clear()

    def _on_document_changed(self):
        self._refresh_operations_tree()
        self.canvas.render_elements()
        # Safety net for the Position/Taille panel and Edit-menu action
        # states: this fires for ANY kernel-side change that emits
        # "refresh_scene" -- console-typed commands, a wx sub-window
        # editing the document, etc. -- not just the toolbar/menu
        # handlers that already call these explicitly.
        self._update_selection_dependent_actions()
        self._update_position_panel()
        self._update_warnings_indicator()
        # "refresh_scene" is the document-CONTENT-changed signal (unlike
        # "refresh_tree", which also fires for pure selection changes) --
        # a simple has-changed-since-last-save flag, not full undo-
        # position matching, same as most document-based apps' "*" marker.
        # Skipped during _startup_settling -- see its own comment in
        # __init__ for why a "refresh_scene" this early isn't a real edit.
        if not self._dirty and not self._startup_settling:
            self._dirty = True
            self._update_window_title()

    def _end_startup_settling(self):
        self._startup_settling = False

    def _restore_window_state(self):
        """Restore window size/position and dock layout from the previous
        session -- same intent as the classic wx UI's "windows_save"."""
        settings = QSettings("MadGrav", "QtGUI")
        geometry = settings.value("window/geometry")
        if geometry is not None:
            self.restoreGeometry(geometry)
        state = settings.value("window/state")
        if state is not None:
            self.restoreState(state)

    def closeEvent(self, event):
        # Kernel-initiated closes (typed "quit", "-e quit", a remote
        # consoleserver disconnect) must exit promptly and unattended --
        # only a user-driven close (the window's own X button, File >
        # Quitter) gets the unsaved-changes prompt.
        if not self._closing_from_kernel and self._dirty:
            answer = QMessageBox.question(
                self,
                "Modifications non enregistrées",
                "Enregistrer les modifications avant de quitter ?",
                QMessageBox.StandardButton.Save
                | QMessageBox.StandardButton.Discard
                | QMessageBox.StandardButton.Cancel,
                QMessageBox.StandardButton.Save,
            )
            if answer == QMessageBox.StandardButton.Cancel:
                event.ignore()
                return
            if answer == QMessageBox.StandardButton.Save:
                self._on_save()
                if self._dirty:
                    # Save was cancelled (e.g. the file-picker) or failed
                    # -- _on_save/_save_to already reported why via a
                    # dialog or the console; don't lose the document on
                    # top of that by closing anyway.
                    event.ignore()
                    return

        settings = QSettings("MadGrav", "QtGUI")
        settings.setValue("window/geometry", self.saveGeometry())
        settings.setValue("window/state", self.saveState())
        self.context.unlisten("refresh_scene", self._on_kernel_refresh_scene)
        self.context.unlisten("refresh_tree", self._on_kernel_refresh_tree)
        self.context.unlisten("element_property_update", self._on_kernel_refresh_tree)
        self.context.unlisten("activate;device", self._on_kernel_device_activated)
        self.context.unlisten("device;modified", self._on_kernel_device_activated)
        self.context.unlisten("device;renamed", self._on_kernel_device_activated)
        self.context.unlisten("pause", self._on_kernel_device_status_changed)
        self.context.unlisten("pipe;running", self._on_kernel_device_status_changed)
        self.context.unlisten("undoredo", self._on_kernel_undoredo_changed)
        self.context.unlisten("icons", self._on_kernel_paste_state_changed)
        self.context.unlisten("laser_armed", self._on_kernel_arm_state_changed)
        self.context.unlisten("coolant_set", self._on_kernel_coolant_state_changed)
        self.context.unlisten("coolant_changed", self._on_kernel_coolant_changed)
        self.context.unlisten("spooler;queue", self._on_kernel_job_progress)
        self.context.unlisten("spooler;completed", self._on_kernel_job_progress)
        self.context.channel("console").unwatch(self._on_console_channel_message)
        self._console_flush_timer.stop()
        self._flush_console_buffer()
        self._job_timer.stop()
        self._ops_tree_refresh_timer.stop()
        super().closeEvent(event)

    def _setup_ui(self):
        # Central Widget & Canvas
        self.canvas = MadGravQtCanvas(self.context, self)
        self.setCentralWidget(self.canvas)

        # Menu Bar
        self._create_menubar()

        # Top Action Toolbar
        self._create_toolbar()

        # Left Tool Palette
        self._create_left_tool_panel()

        # Right Dock Inspector (Operations, Elements, Laser Control)
        self._create_right_docks()

        # Bottom Console Dock
        self._create_console_dock()

        # Status Bar
        self.status_bar = QStatusBar(self)
        self.setStatusBar(self.status_bar)

        self.job_label = QLabel("")
        self.job_label.setVisible(False)
        self.status_bar.addPermanentWidget(self.job_label)

        self.job_progress = QProgressBar(self)
        self.job_progress.setRange(0, 100)
        self.job_progress.setFixedWidth(120)
        self.job_progress.setVisible(False)
        self.status_bar.addPermanentWidget(self.job_progress)

        self.selection_label = QLabel("Aucune sélection")
        self.status_bar.addPermanentWidget(self.selection_label)

        self.pos_label = QLabel("X: 0.00 mm  |  Y: 0.00 mm")
        self.status_bar.addPermanentWidget(self.pos_label)

        self.zoom_label = QLabel("100%")
        self.status_bar.addPermanentWidget(self.zoom_label)

        self.btn_warnings = QPushButton("", self)
        self.btn_warnings.setFlat(True)
        self.btn_warnings.setVisible(False)
        self.btn_warnings.setStyleSheet("color: #e0a030; font-weight: bold;")
        self.btn_warnings.setToolTip("")
        self.btn_warnings.clicked.connect(self._show_warnings_dialog)
        self.status_bar.addPermanentWidget(self.btn_warnings)

        btn_zoom_reset = QPushButton("Réinitialiser (100%)", self)
        btn_zoom_reset.setFlat(True)
        btn_zoom_reset.setToolTip("Réinitialiser le zoom à 100%.")
        btn_zoom_reset.clicked.connect(self.canvas.reset_zoom)
        self.status_bar.addPermanentWidget(btn_zoom_reset)

        self.status_bar.showMessage("Prêt - MadGrav PyQt6 Initialisé", 5000)

        # Connect signals
        self.canvas.cursor_position_changed.connect(self._on_canvas_cursor_moved)
        self.canvas.selection_changed.connect(self._on_selection_changed)
        self.canvas.shape_created.connect(self._on_shape_created)
        self.canvas.zoom_changed.connect(self._on_zoom_changed)
        self.canvas.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.canvas.customContextMenuRequested.connect(self._on_canvas_context_menu)

    def _create_menubar(self):
        menubar = self.menuBar()

        # File
        file_menu = menubar.addMenu("&Fichier")
        act_new = QAction("Nouveau Projet", self)
        act_new.setShortcut(QKeySequence.StandardKey.New)
        act_new.triggered.connect(self._on_new)
        file_menu.addAction(act_new)

        act_open = QAction("Ouvrir Fichier (SVG/DXF)...", self)
        act_open.setShortcut(QKeySequence.StandardKey.Open)
        act_open.triggered.connect(self._on_open_file)
        file_menu.addAction(act_open)

        # Recent files -- stored as context.file0..fileN, the SAME kernel
        # settings keys the classic wx UI uses (madgrav/gui/wxmmain.py:
        # set_file_as_recently_used), so a file opened in one UI shows up
        # as recent in the other.
        self.recent_menu = file_menu.addMenu("Fichiers Récents")
        self._populate_recent_menu()

        file_menu.addSeparator()
        act_save = QAction("Enregistrer Projet...", self)
        act_save.setShortcut(QKeySequence.StandardKey.Save)
        act_save.triggered.connect(self._on_save)
        file_menu.addAction(act_save)

        act_save_as = QAction("Enregistrer Sous...", self)
        act_save_as.setShortcut(QKeySequence.StandardKey.SaveAs)
        act_save_as.triggered.connect(self._on_save_as)
        file_menu.addAction(act_save_as)

        file_menu.addSeparator()
        act_exit = QAction("Quitter", self)
        act_exit.setShortcut(QKeySequence.StandardKey.Quit)
        act_exit.triggered.connect(self.close)
        file_menu.addAction(act_exit)

        # Edit
        edit_menu = menubar.addMenu("&Édition")
        self.act_undo = QAction("Annuler", self)
        self.act_undo.setShortcut(QKeySequence.StandardKey.Undo)
        self.act_undo.triggered.connect(self._on_undo)
        edit_menu.addAction(self.act_undo)

        self.act_redo = QAction("Rétablir", self)
        self.act_redo.setShortcut(QKeySequence.StandardKey.Redo)
        self.act_redo.triggered.connect(self._on_redo)
        edit_menu.addAction(self.act_redo)
        self._update_undo_redo_actions()

        edit_menu.addSeparator()
        act_select_all = QAction("Tout Sélectionner", self)
        act_select_all.setShortcut(QKeySequence.StandardKey.SelectAll)
        act_select_all.triggered.connect(self._on_select_all)
        edit_menu.addAction(act_select_all)

        act_deselect = QAction("Tout Désélectionner", self)
        # QKeySequence.StandardKey.Deselect has no default binding on
        # Windows (resolves to an empty shortcut there) -- Escape is the
        # conventional "clear selection" key in design tools generally.
        # This is a window-level shortcut, so Qt's shortcut map claims a
        # matching Escape press before the canvas's own keyPressEvent ever
        # sees it -- _on_escape_pressed is the single place that decides
        # between "cancel an in-progress draw/rubber-band/move" and
        # "deselect everything" (see MadGravQtCanvas.cancel_in_progress_gesture).
        act_deselect.setShortcut(QKeySequence("Escape"))
        act_deselect.triggered.connect(self._on_escape_pressed)
        edit_menu.addAction(act_deselect)

        act_delete = QAction("Supprimer", self)
        act_delete.setShortcut(QKeySequence.StandardKey.Delete)
        act_delete.triggered.connect(lambda: self.canvas._delete_emphasized())
        edit_menu.addAction(act_delete)

        act_duplicate = QAction("Dupliquer", self)
        act_duplicate.setShortcut(QKeySequence("Ctrl+D"))
        act_duplicate.triggered.connect(self._on_duplicate)
        edit_menu.addAction(act_duplicate)

        edit_menu.addSeparator()
        act_copy = QAction("Copier", self)
        act_copy.setShortcut(QKeySequence.StandardKey.Copy)
        act_copy.triggered.connect(self._on_copy)
        edit_menu.addAction(act_copy)

        act_cut = QAction("Couper", self)
        act_cut.setShortcut(QKeySequence.StandardKey.Cut)
        act_cut.triggered.connect(self._on_cut)
        edit_menu.addAction(act_cut)

        self.act_paste = QAction("Coller", self)
        self.act_paste.setShortcut(QKeySequence.StandardKey.Paste)
        self.act_paste.triggered.connect(self._on_paste)
        edit_menu.addAction(self.act_paste)
        self._update_paste_action()

        edit_menu.addSeparator()
        act_rotate_cw = QAction("Rotation 90° Horaire", self)
        act_rotate_cw.setShortcut(QKeySequence("Ctrl+R"))
        act_rotate_cw.triggered.connect(lambda: self._on_rotate(90))
        edit_menu.addAction(act_rotate_cw)

        act_rotate_ccw = QAction("Rotation 90° Anti-horaire", self)
        act_rotate_ccw.setShortcut(QKeySequence("Ctrl+Shift+R"))
        act_rotate_ccw.triggered.connect(lambda: self._on_rotate(-90))
        edit_menu.addAction(act_rotate_ccw)

        act_mirror_h = QAction("Miroir Horizontal", self)
        act_mirror_h.setShortcut(QKeySequence("Ctrl+H"))
        act_mirror_h.triggered.connect(lambda: self._on_mirror(-1, 1))
        edit_menu.addAction(act_mirror_h)

        act_mirror_v = QAction("Miroir Vertical", self)
        act_mirror_v.setShortcut(QKeySequence("Ctrl+Shift+H"))
        act_mirror_v.triggered.connect(lambda: self._on_mirror(1, -1))
        edit_menu.addAction(act_mirror_v)

        edit_menu.addSeparator()
        act_lock = QAction("Verrouiller", self)
        act_lock.triggered.connect(lambda: self._on_lock(True))
        edit_menu.addAction(act_lock)

        act_unlock = QAction("Déverrouiller", self)
        act_unlock.triggered.connect(lambda: self._on_lock(False))
        edit_menu.addAction(act_unlock)

        edit_menu.addSeparator()
        act_group = QAction("Grouper", self)
        act_group.setShortcut(QKeySequence("Ctrl+G"))
        act_group.triggered.connect(self._on_group)
        edit_menu.addAction(act_group)

        act_ungroup = QAction("Dégrouper", self)
        act_ungroup.setShortcut(QKeySequence("Ctrl+Shift+G"))
        act_ungroup.triggered.connect(self._on_ungroup)
        edit_menu.addAction(act_ungroup)

        # Grid (array) copy -- LightBurn's "Array Copy", one of its most
        # heavily-used tools, was entirely unreachable from this shell
        # despite the backend ("grid" console command, madgrav/core/
        # elements/grid.py) already supporting it fully. Works from a
        # single selected element (tiles copies of it), so it belongs
        # with the single- not multi-selection actions below.
        act_grid_copy = QAction("Copie en Grille...", self)
        act_grid_copy.triggered.connect(self._on_grid_array_copy)
        edit_menu.addAction(act_grid_copy)

        # Radial (circular) array copy -- LightBurn's other Array Copy
        # mode. Same "no Qt path despite an already-complete backend"
        # situation as the grid copy above ("radial" console command,
        # same grid.py module) -- also works from a single element.
        act_radial_copy = QAction("Copie Radiale...", self)
        act_radial_copy.triggered.connect(self._on_radial_array_copy)
        edit_menu.addAction(act_radial_copy)

        # Alignment -- entirely missing from Qt until now, despite being
        # one of the most basic vector-editing operations any selection
        # of 2+ elements needs. Same "align {mode} {direction}" console
        # commands the classic wx UI's own align buttons run for 5 of
        # its 6 directions (madgrav/gui/wxmmain.py -- only "Left" uses a
        # push/pop-wrapped variant there, an inconsistency in wx itself;
        # replicated here using the simpler, dominant form for all six).
        edit_menu.addSeparator()
        align_menu = edit_menu.addMenu("Aligner")
        align_entries = [
            ("Gauche", "left"),
            ("Droite", "right"),
            ("Haut", "top"),
            ("Bas", "bottom"),
            ("Centrer Horizontalement", "centerh"),
            ("Centrer Verticalement", "centerv"),
        ]
        self._align_actions = []
        for label, direction in align_entries:
            act = QAction(label, self)
            act.triggered.connect(lambda checked=False, d=direction: self._on_align(d))
            align_menu.addAction(act)
            self._align_actions.append(act)

        # Boolean/CAG geometry operations -- another basic vector-editing
        # feature entirely missing from Qt. Same "element {op}" command
        # chain the classic wx UI's own buttons run as their always-
        # available fallback (madgrav/extra/cag.py; wx additionally
        # prefers a "clipper {op}" variant when the optional pyclipr
        # package is installed, purely a performance/quality upgrade for
        # complex shapes -- not replicated here to avoid an optional-
        # dependency check for a non-functional difference).
        geometry_menu = edit_menu.addMenu("Géométrie (Union, Différence...)")
        geometry_entries = [
            ("Union", "union"),
            ("Différence", "difference"),
            ("Intersection", "intersection"),
            ("Xor", "xor"),
        ]
        self._geometry_actions = []
        for label, op in geometry_entries:
            act = QAction(label, self)
            act.triggered.connect(lambda checked=False, o=op: self._on_geometry_op(o))
            geometry_menu.addAction(act)
            self._geometry_actions.append(act)

        # Merge/break-apart -- LightBurn's "Merge Path" (Ctrl+Alt+M) and
        # its inverse. Distinct from the boolean CAG ops just above:
        # merge just concatenates the selected shapes' path data into
        # one node (stitching shared endpoints, no geometric union/
        # subtraction), and break-apart is its exact reverse for a
        # compound path. Both console commands declare
        # input_type="elements" (no bare/None form) -- reached only via
        # the "element* {cmd}" pipe, same reasoning already established
        # for _on_device_combo_activated's index-based "device activate".
        edit_menu.addSeparator()
        act_merge_paths = QAction("Fusionner les Chemins", self)
        act_merge_paths.triggered.connect(self._on_merge_paths)
        edit_menu.addAction(act_merge_paths)

        act_break_apart = QAction("Séparer les Sous-Chemins", self)
        act_break_apart.triggered.connect(self._on_break_apart)
        edit_menu.addAction(act_break_apart)

        # Simplify -- LightBurn's "Simplify" (right-click menu), reduces
        # a complex path's node count within a given tolerance. Only
        # meaningful for "elem path" nodes (an ellipse/rect's geometry
        # is parametric, not a literal point list -- the backend command
        # rejects those with "Invalid node for simplify" on its own
        # channel, which _run_console() can't surface since it's not an
        # exception, so the type check happens here first instead).
        act_simplify = QAction("Simplifier le Chemin...", self)
        act_simplify.triggered.connect(self._on_simplify_path)
        edit_menu.addAction(act_simplify)

        # Hatch fill -- one of LightBurn's headline features (fills a
        # closed shape with repeating scan lines for efficient area
        # engraving instead of a slow raster). Backend ("effect-hatch")
        # wraps the selection in a new "effect hatch" tree node rather
        # than mutating it in place -- same append_children()
        # reparenting shape as "group"/"ungroup" already use elsewhere.
        act_hatch = QAction("Remplissage Hachuré...", self)
        act_hatch.triggered.connect(self._on_add_hatch_effect)
        edit_menu.addAction(act_hatch)

        # Offset -- LightBurn's "Offset" tool: grows/shrinks a shape's
        # outline by a fixed distance (positive = outward, negative =
        # inward), commonly used for kerf compensation or a cut line
        # around an engraved area. Backend ("offset", offset_clpr.py /
        # offset_mk.py fallback) creates NEW "elem path" node(s) rather
        # than mutating the source in place -- same non-destructive
        # pattern as Hatch above.
        act_offset = QAction("Décaler (Offset)...", self)
        act_offset.triggered.connect(self._on_add_offset_path)
        edit_menu.addAction(act_offset)

        # Text tools -- "text-anchor"/"text-edit" (madgrav/core/elements/
        # shapes.py) already no-op gracefully on a non-"elem text"
        # selection (silently skip that node, no error), so unlike
        # Simplify these don't need a pre-dispatch type check here.
        edit_menu.addSeparator()
        text_anchor_menu = edit_menu.addMenu("Alignement du Texte")
        text_anchor_entries = [
            ("Gauche", "start"),
            ("Centré", "middle"),
            ("Droite", "end"),
        ]
        self._text_anchor_actions = []
        for label, anchor in text_anchor_entries:
            act = QAction(label, self)
            act.triggered.connect(lambda checked=False, a=anchor: self._on_text_anchor(a))
            text_anchor_menu.addAction(act)
            self._text_anchor_actions.append(act)

        act_text_edit = QAction("Modifier le Texte...", self)
        act_text_edit.triggered.connect(self._on_edit_text_content)
        edit_menu.addAction(act_text_edit)

        # Selection-dependent actions start disabled (nothing is selected
        # at boot) and get toggled from _update_selection_dependent_actions()
        # instead of just silently no-op'ing when clicked with no selection.
        self._single_selection_actions = [
            act_delete, act_duplicate, act_copy, act_cut, act_rotate_cw,
            act_rotate_ccw, act_mirror_h, act_mirror_v, act_lock,
            act_unlock, act_ungroup, act_grid_copy, act_radial_copy,
            act_break_apart, act_simplify, act_hatch, act_offset,
            act_text_edit,
        ] + self._text_anchor_actions
        # Aligning/CAG ops need >= 2 elements too -- the backend itself
        # refuses ("No sense in aligning an element to itself" / "Not
        # enough items selected") for a lone one.
        self._multi_selection_actions = (
            [act_group, act_merge_paths] + self._align_actions + self._geometry_actions
        )
        self._update_selection_dependent_actions()

        edit_menu.addSeparator()
        act_classify = QAction("Classifier Tout (Assigner aux Opérations)", self)
        act_classify.triggered.connect(self._on_classify_all)
        edit_menu.addAction(act_classify)

        # Declassify -- the reverse of Classifier Tout, but scoped to
        # the current selection rather than the whole document (matches
        # what the bare "declassify" console command itself defaults to
        # with no pipe: elements.elems(emphasized=True)). Added to
        # _single_selection_actions after the fact since that list was
        # already finalized above -- act_classify itself isn't
        # selection-gated (it always runs against the whole document),
        # so it stays outside that list.
        act_declassify = QAction("Retirer des Opérations", self)
        act_declassify.setEnabled(False)
        act_declassify.triggered.connect(self._on_declassify_selection)
        edit_menu.addAction(act_declassify)
        self._single_selection_actions.append(act_declassify)

        # View
        view_menu = menubar.addMenu("&Affichage")
        # Stashed so _create_right_docks() (which runs after this method,
        # see _setup_ui) can append its own "Panneaux" submenu once the
        # right-side QDockWidgets it needs actually exist.
        self.view_menu = view_menu
        act_zoom_fit = QAction("Ajuster à la Sélection", self)
        act_zoom_fit.triggered.connect(self._on_zoom_fit)
        view_menu.addAction(act_zoom_fit)

        act_zoom_in = QAction("Zoom Avant", self)
        act_zoom_in.setShortcut(QKeySequence.StandardKey.ZoomIn)
        act_zoom_in.triggered.connect(lambda: self.canvas.zoom_step(1))
        view_menu.addAction(act_zoom_in)

        act_zoom_out = QAction("Zoom Arrière", self)
        act_zoom_out.setShortcut(QKeySequence.StandardKey.ZoomOut)
        act_zoom_out.triggered.connect(lambda: self.canvas.zoom_step(-1))
        view_menu.addAction(act_zoom_out)

        view_menu.addSeparator()
        self.act_light_theme = QAction("Thème Clair", self)
        self.act_light_theme.setCheckable(True)
        self.act_light_theme.setChecked(not self._dark_theme)
        self.act_light_theme.triggered.connect(self._on_toggle_theme)
        view_menu.addAction(self.act_light_theme)

        # Window -- most of MadGrav's feature surface (device config,
        # camera, materials, rotary, etc.) lives in windows that only the
        # classic wx UI exposes buttons for. Until each gets a native Qt
        # rebuild, this menu is how the Qt shell reaches them, instead of
        # requiring the exact console command to be typed by hand.
        window_menu = menubar.addMenu("Fe&nêtre")
        window_entries = [
            ("Gestionnaire de Périphériques...", "DeviceManager"),
            ("Configuration de l'Appareil...", "Configuration"),
            ("Préférences...", "Preferences"),
            None,
            ("Propriétés de l'Élément...", "Properties"),
            ("Informations sur l'Opération...", "OperationInfo"),
            ("Gestionnaire de Matériaux...", "MatManager"),
            None,
            # Caméra intentionnellement absente ici : le service caméra lève
            # une exception non rattrapée quand aucune caméra matérielle
            # n'est configurée (madgrav/camera/plugin.py) -- un bug
            # préexistant, indépendant de Qt, que je ne peux pas vérifier
            # sans matériel réel. Accessible en attendant via la console
            # ("window open CameraInterface").
            ("Simulation...", "Simulation"),
            ("Axe Rotatif...", "Rotary"),
            ("Notes...", "Notes"),
            # Not to be confused with Aide > "Raccourcis clavier..." (a
            # static read-only list of THIS Qt shell's own menu
            # shortcuts) -- wx's Keymap window is a full editor for
            # REMAPPING keys to arbitrary console commands, a different
            # and more powerful feature. Distinct labels so the two don't
            # look like the same thing in two different menus.
            ("Personnaliser les Raccourcis (Keymap)...", "Keymap"),
            ("Éditeur de Wordlist...", "Wordlist"),
        ]
        for entry in window_entries:
            if entry is None:
                window_menu.addSeparator()
                continue
            label, window_name = entry
            act = QAction(label, self)
            act.triggered.connect(lambda checked=False, n=window_name: self._open_window(n))
            window_menu.addAction(act)

        # Help
        help_menu = menubar.addMenu("&Aide")
        act_shortcuts = QAction("Raccourcis clavier...", self)
        act_shortcuts.triggered.connect(self._on_show_shortcuts)
        help_menu.addAction(act_shortcuts)
        help_menu.addSeparator()
        act_about = QAction("À Propos de MadGrav...", self)
        act_about.triggered.connect(self._on_about)
        help_menu.addAction(act_about)

    def _create_toolbar(self):
        toolbar = QToolBar("Actions Principales", self)
        toolbar.setIconSize(QSize(20, 20))
        self.addToolBar(Qt.ToolBarArea.TopToolBarArea, toolbar)

        btn_open = QToolButton(self)
        btn_open.setText("📂 Ouvrir")
        btn_open.setToolTip("Ouvrir un fichier vectoriel ou image (SVG, DXF, PNG, JPG)")
        btn_open.clicked.connect(self._on_open_file)
        toolbar.addWidget(btn_open)

        toolbar.addSeparator()

        self.btn_orig = QToolButton(self)
        self.btn_orig.setText("🎯 Origine (0,0)")
        self.btn_orig.setToolTip("Replacer la tête laser à l'origine (0,0)")
        self.btn_orig.clicked.connect(self._on_home)
        toolbar.addWidget(self.btn_orig)

        self.btn_frame = QToolButton(self)
        self.btn_frame.setText("🔲 Cadre (Frame)")
        self.btn_frame.setToolTip(
            "Trace le contour des éléments sélectionnés au pointeur/laser "
            "(rien ne se passe si aucune sélection)."
        )
        self.btn_frame.clicked.connect(self._on_frame)
        toolbar.addWidget(self.btn_frame)

        toolbar.addSeparator()

        # Optional extra safety confirmation before a job can start --
        # same "laserpane_arm"/"_laser_may_run" mechanism and "laser_armed"
        # signal the classic wx UI's laser panel uses (madgrav/gui/
        # wxmmain.py: arm_laser/disarm_laser/may_run), reused directly so
        # arming state stays in sync between the two UIs. Completely
        # missing from Qt until now -- "Démarrer" only ever checked for
        # burnable content, with no arm gate at all.
        self.btn_arm = QToolButton(self)
        self.btn_arm.setCheckable(True)
        self.btn_arm.clicked.connect(self._on_toggle_arm)
        toolbar.addWidget(self.btn_arm)

        self.btn_start = QToolButton(self)
        self.btn_start.setText("▶ DÉMARRER")
        self.btn_start.setToolTip("Envoyer et démarrer le travail laser")
        self.btn_start.clicked.connect(self._on_start)
        toolbar.addWidget(self.btn_start)

        self.btn_pause = QToolButton(self)
        self.btn_pause.setText("⏸ Pause")
        self.btn_pause.setToolTip("Mettre en pause ou reprendre le travail en cours")
        self.btn_pause.clicked.connect(self._on_pause)
        toolbar.addWidget(self.btn_pause)

        self.btn_stop = QToolButton(self)
        self.btn_stop.setText("⏹ STOP")
        self.btn_stop.setToolTip("ARRÊT D'URGENCE -- interrompt immédiatement le travail en cours")
        self.btn_stop.clicked.connect(self._on_stop)
        toolbar.addWidget(self.btn_stop)

        toolbar.addSeparator()

        # Manual coolant/air-assist toggle -- only shown for a device
        # that actually declares one (madgrav/extra/coolant.py). Separate
        # from the automatic per-operation coolant_on/off the job plan
        # itself issues during a run (madgrav/core/cutplan.py) -- this is
        # for priming/testing airflow before a job, or manual control,
        # same as the classic wx UI's own toggle (madgrav/gui/wxmmain.py:
        # "button/jobstart/Coolant"). Completely missing from Qt until now.
        self.btn_coolant = QToolButton(self)
        self.btn_coolant.setCheckable(True)
        self.btn_coolant.clicked.connect(self._on_toggle_coolant)
        toolbar.addWidget(self.btn_coolant)

        # These 5 buttons carry their OWN inline stylesheet (colored
        # backgrounds a plain QSS class selector can't express per-button)
        # which overrides the app-wide theme QSS entirely -- so unlike
        # every other widget, they need to be told explicitly which theme
        # is active. See _apply_toolbar_button_theme's own docstring.
        self._apply_toolbar_button_theme()

        # Disabled at boot -- no device is active yet -- and kept in sync
        # by _refresh_device_status() from then on, instead of leaving
        # them clickable-but-always-warning-dialog like before.
        for btn in (self.btn_orig, self.btn_frame, self.btn_start, self.btn_pause, self.btn_stop):
            btn.setEnabled(False)
        self._update_arm_button()
        self._update_coolant_button()

    def _apply_toolbar_button_theme(self):
        """(Re-)applies the arm/start/pause/stop/coolant toolbar buttons'
        inline stylesheets for the current self._dark_theme. Called once
        at construction and again from _on_toggle_theme() -- these 5
        buttons set their own background-color per state (a green Start,
        orange Pause, red Stop... a plain QSS class selector can't express
        that), which entirely overrides the app-wide theme stylesheet, so
        they don't pick up the light/dark swap for free like everything
        else does."""
        if self._dark_theme:
            neutral_bg, neutral_fg = "#3A3A4A", "#FFFFFF"
            disabled_bg, disabled_fg = "#2C2C3E", "#6E6E7A"
        else:
            neutral_bg, neutral_fg = "#D6D6DE", "#1C1C22"
            disabled_bg, disabled_fg = "#E4E4EA", "#9A9AA6"

        self.btn_arm.setStyleSheet(
            f"QToolButton {{ background-color: {neutral_bg}; color: {neutral_fg}; font-weight: bold; border-radius: 4px; padding: 3px 10px; }}"
            "QToolButton:checked { background-color: #0A84FF; color: #FFFFFF; }"
        )
        self.btn_coolant.setStyleSheet(
            f"QToolButton {{ background-color: {neutral_bg}; color: {neutral_fg}; font-weight: bold; border-radius: 4px; padding: 3px 10px; }}"
            "QToolButton:checked { background-color: #0A84FF; color: #FFFFFF; }"
        )
        self.btn_start.setStyleSheet(
            "QToolButton { background-color: #248A3D; color: #FFFFFF; font-weight: bold; border-radius: 4px; padding: 3px 10px; }"
            f"QToolButton:disabled {{ background-color: {disabled_bg}; color: {disabled_fg}; }}"
        )
        self.btn_pause.setStyleSheet(
            "QToolButton { background-color: #B25D00; color: #FFFFFF; font-weight: bold; border-radius: 4px; padding: 3px 10px; }"
            f"QToolButton:disabled {{ background-color: {disabled_bg}; color: {disabled_fg}; }}"
        )
        self.btn_stop.setStyleSheet(
            "QToolButton { background-color: #C02B2B; color: #FFFFFF; font-weight: bold; border-radius: 4px; padding: 3px 10px; }"
            f"QToolButton:disabled {{ background-color: {disabled_bg}; color: {disabled_fg}; }}"
        )

    def _apply_tool_icon_theme(self):
        """(Re-)draws the left draw-tool panel's icons for the current
        self._dark_theme -- build_tool_icon() bakes a fixed foreground
        color into the pixmap at draw time (unlike a QSS color, which a
        raster icon can't pick up automatically), so this must be
        called again on every theme toggle, same reasoning as
        _apply_toolbar_button_theme() above."""
        color = "#E2E2E9" if self._dark_theme else "#1C1C22"
        for icon_name, btn in getattr(self, "_tool_buttons", {}).items():
            btn.setIcon(build_tool_icon(icon_name, size=22, color=color))

    def _create_left_tool_panel(self):
        dock_tools = QDockWidget("Outils Dessin", self)
        dock_tools.setAllowedAreas(
            Qt.DockWidgetArea.LeftDockWidgetArea | Qt.DockWidgetArea.RightDockWidgetArea
        )

        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setContentsMargins(6, 6, 6, 6)
        layout.setSpacing(6)

        # Icon-above-text QToolButtons in a 2-column grid -- a real
        # toolbox palette (LightBurn/Illustrator-style) instead of a
        # single column of full-width text buttons. Icons are drawn
        # with build_tool_icon() (qt_theme.py), the same
        # QPainter-primitives approach as the app icon, since neither
        # emoji glyphs nor an external icon set render consistently/
        # crisply across platforms the way flat vector-drawn ones do.
        self.tool_group = QButtonGroup(self)
        self.tool_group.setExclusive(True)
        self._tool_buttons = {}
        icon_grid = QGridLayout()
        icon_grid.setSpacing(4)
        working_tools = [
            ("select", "Sélection", "Outil de sélection (déplacement à la souris)", self._on_tool_select),
            ("pan", "Main", "Déplacer la vue du lit de travail (glisser-déposer)", self._on_tool_pan),
            ("rect", "Rectangle", "Cliquer-glisser pour créer un rectangle (Échap pour annuler)", self._on_tool_rect),
            ("ellipse", "Cercle", "Cliquer-glisser pour créer une ellipse (Échap pour annuler)", self._on_tool_ellipse),
            ("line", "Ligne", "Cliquer-glisser pour créer une ligne (Échap pour annuler)", self._on_tool_line),
            ("text", "Texte", "Cliquer pour placer un texte (Échap pour annuler)", self._on_tool_text),
        ]
        for i, (icon_name, text, tip, handler) in enumerate(working_tools):
            btn = QToolButton(self)
            btn.setText(text)
            btn.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextUnderIcon)
            btn.setIconSize(QSize(22, 22))
            btn.setToolTip(tip)
            btn.setCheckable(True)
            btn.clicked.connect(handler)
            self.tool_group.addButton(btn)
            self._tool_buttons[icon_name] = btn
            icon_grid.addWidget(btn, i // 2, i % 2)
        layout.addLayout(icon_grid)
        # Default tool on startup.
        self.tool_group.buttons()[0].setChecked(True)
        self._apply_tool_icon_theme()

        btn_zoom = QPushButton("🔍 Loupe (Ajuster)", self)
        btn_zoom.setToolTip("Ajuster la vue à la sélection / au contenu")
        btn_zoom.clicked.connect(self._on_zoom_fit)
        layout.addWidget(btn_zoom)

        layout.addStretch()
        dock_tools.setWidget(w)
        self.addDockWidget(Qt.DockWidgetArea.LeftDockWidgetArea, dock_tools)

    def _create_right_docks(self):
        # Dock 1: Operations & Elements Tree
        self.dock_ops = dock_ops = QDockWidget("Arbre des Opérations", self)
        w_ops = QWidget()
        l_ops = QVBoxLayout(w_ops)
        l_ops.setContentsMargins(6, 6, 6, 6)

        self.ops_tree = QTreeWidget(self)
        self.ops_tree.setHeaderLabels(
            ["Opération / Élément", "Vitesse", "Puissance", "Passes"]
        )
        self.ops_tree.header().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        self.ops_tree.itemClicked.connect(self._on_tree_item_clicked)
        self.ops_tree.itemDoubleClicked.connect(self._on_tree_item_double_clicked)

        l_ops.addWidget(self.ops_tree)

        tree_btn_row = QHBoxLayout()
        self.btn_tree_duplicate = QPushButton("Dupliquer", self)
        self.btn_tree_duplicate.setToolTip(
            "Dupliquer l'élément sélectionné dans l'arbre (double-cliquer un "
            "libellé pour le renommer)."
        )
        self.btn_tree_duplicate.clicked.connect(self._on_tree_duplicate_selected)
        tree_btn_row.addWidget(self.btn_tree_duplicate)

        self.btn_tree_delete = QPushButton("Supprimer", self)
        self.btn_tree_delete.setToolTip(
            "Supprimer l'opération ou l'élément sélectionné dans l'arbre."
        )
        self.btn_tree_delete.clicked.connect(self._on_tree_delete_selected)
        tree_btn_row.addWidget(self.btn_tree_delete)
        l_ops.addLayout(tree_btn_row)

        dock_ops.setWidget(w_ops)
        self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, dock_ops)
        self._refresh_operations_tree()
        self._update_tree_action_buttons()

        # Dock 1b: Position & Size -- numeric readout/edit for the single
        # selected element, complementing mouse-drag/nudge placement.
        self.dock_pos = dock_pos = QDockWidget("Position et Taille", self)
        w_pos = QWidget()
        l_pos = QFormLayout(w_pos)
        l_pos.setContentsMargins(6, 6, 6, 6)

        self.pos_x_spin = QDoubleSpinBox(self)
        self.pos_y_spin = QDoubleSpinBox(self)
        for spin in (self.pos_x_spin, self.pos_y_spin):
            spin.setRange(-10000, 10000)
            spin.setDecimals(2)
            spin.setSuffix(" mm")
        self.pos_x_spin.editingFinished.connect(self._on_position_field_edited)
        self.pos_y_spin.editingFinished.connect(self._on_position_field_edited)
        l_pos.addRow("X :", self.pos_x_spin)
        l_pos.addRow("Y :", self.pos_y_spin)

        # "Set Size" -- LightBurn's editable width/height fields in its
        # own position toolbar. Was previously a read-only label here;
        # wired to the existing "resize" console command (madgrav/core/
        # elements/shapes.py), which sets width/height AND position in
        # one call, so this reuses the already-known X/Y from
        # pos_x_spin/pos_y_spin to keep the top-left corner unchanged --
        # a pure resize, not an implicit move.
        self.size_w_spin = QDoubleSpinBox(self)
        self.size_h_spin = QDoubleSpinBox(self)
        for spin in (self.size_w_spin, self.size_h_spin):
            spin.setRange(0.01, 10000)
            spin.setDecimals(2)
            spin.setSuffix(" mm")
        self.size_w_spin.editingFinished.connect(self._on_size_field_edited)
        self.size_h_spin.editingFinished.connect(self._on_size_field_edited)
        l_pos.addRow("Largeur :", self.size_w_spin)
        l_pos.addRow("Hauteur :", self.size_h_spin)

        # Property editing -- same "fill"/"stroke"/"stroke-width" console
        # commands the console dock already exposes, surfaced here so the
        # most common edits don't require typing a command by hand.
        self.btn_fill_color = QPushButton("Choisir...", self)
        self.btn_fill_color.setToolTip("Changer la couleur de remplissage de l'élément sélectionné.")
        self.btn_fill_color.clicked.connect(lambda: self._pick_and_apply_color("fill"))
        l_pos.addRow("Remplissage :", self.btn_fill_color)

        self.btn_stroke_color = QPushButton("Choisir...", self)
        self.btn_stroke_color.setToolTip("Changer la couleur de contour de l'élément sélectionné.")
        self.btn_stroke_color.clicked.connect(lambda: self._pick_and_apply_color("stroke"))
        l_pos.addRow("Contour :", self.btn_stroke_color)

        self.stroke_width_spin = QDoubleSpinBox(self)
        self.stroke_width_spin.setRange(0, 100)
        self.stroke_width_spin.setDecimals(2)
        self.stroke_width_spin.setSuffix(" mm")
        self.stroke_width_spin.editingFinished.connect(self._on_stroke_width_edited)
        l_pos.addRow("Épaisseur trait :", self.stroke_width_spin)

        w_pos.setEnabled(False)  # nothing selected at boot
        self._position_panel = w_pos
        dock_pos.setWidget(w_pos)
        self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, dock_pos)

        # Dock 2: Laser Controller Panel
        self.dock_laser = dock_laser = QDockWidget("Contrôle Laser & Spooler", self)
        w_laser = QWidget()
        l_laser = QVBoxLayout(w_laser)
        l_laser.setContentsMargins(6, 6, 6, 6)

        l_laser.addWidget(QLabel("<b>Statut de la Machine :</b>"))
        self.device_status_lbl = QLabel("...")
        l_laser.addWidget(self.device_status_lbl)

        l_laser.addWidget(QLabel("Machine active :"))
        self.device_combo = QComboBox(self)
        # activated (not currentIndexChanged) only fires on genuine user
        # interaction -- _refresh_device_status() repopulates this combo
        # programmatically and must not re-trigger a switch every time.
        self.device_combo.activated.connect(self._on_device_combo_activated)
        l_laser.addWidget(self.device_combo)

        btn_device_wizard = QPushButton("🧙 Assistant de Configuration...", self)
        btn_device_wizard.setToolTip(
            "Détecter les ports série disponibles et créer/configurer une machine."
        )
        btn_device_wizard.clicked.connect(self._on_open_device_wizard)
        l_laser.addWidget(btn_device_wizard)

        btn_remove_device = QPushButton("🗑 Supprimer cette machine", self)
        btn_remove_device.setToolTip(
            "Supprime la machine sélectionnée ci-dessus (pas la machine active)."
        )
        btn_remove_device.clicked.connect(self._on_remove_device)
        l_laser.addWidget(btn_remove_device)

        btn_spooler = QPushButton("⚡ Ouvrir le Gestionnaire Spooler", self)
        btn_spooler.setToolTip("Voir et gérer la file d'attente des travaux laser envoyés à la machine.")
        btn_spooler.clicked.connect(self._on_open_spooler)
        l_laser.addWidget(btn_spooler)

        l_laser.addStretch()
        dock_laser.setWidget(w_laser)
        self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, dock_laser)
        self._refresh_device_status()

        # Retractable right-side panels -- each QDockWidget already has
        # Qt's default DockWidgetClosable feature (no setFeatures() call
        # anywhere restricts it), so clicking a panel's own title-bar "X"
        # already retracts/hides it; the only missing half was a way to
        # bring it back. dock.toggleViewAction() is the idiomatic Qt
        # answer -- a checkable QAction that shows/hides the dock and
        # stays in sync with its actual visibility (including a manual
        # close via the title bar), so a "Panneaux" submenu of checkable
        # entries covers both retract and re-expand with no custom
        # show/hide bookkeeping of our own to get wrong.
        panels_menu = self.view_menu.addMenu("Panneaux")
        for dock, label in (
            (self.dock_ops, "Arbre des Opérations"),
            (self.dock_pos, "Position et Taille"),
            (self.dock_laser, "Contrôle Laser & Spooler"),
        ):
            action = dock.toggleViewAction()
            action.setText(label)
            panels_menu.addAction(action)

    def _create_console_dock(self):
        dock_console = QDockWidget("Console de Commandes Kernel", self)
        w_con = QWidget()
        l_con = QVBoxLayout(w_con)
        l_con.setContentsMargins(6, 6, 6, 6)

        header_row = QHBoxLayout()
        header_row.addStretch()
        btn_clear_console = QPushButton("🧹 Effacer", self)
        btn_clear_console.setToolTip("Effacer le contenu affiché de la console (n'affecte pas le kernel).")
        btn_clear_console.setFlat(True)
        btn_clear_console.clicked.connect(lambda: self.console_output.clear())
        header_row.addWidget(btn_clear_console)
        l_con.addLayout(header_row)

        self.console_output = QPlainTextEdit(self)
        self.console_output.setReadOnly(True)
        # Bound memory/render cost over a long session -- oldest lines drop
        # automatically once the limit is hit, no unbounded growth.
        self.console_output.setMaximumBlockCount(2000)
        self.console_output.appendPlainText("MadGrav Kernel v0.9.x [PyQt6 Active Session]")
        self.console_output.appendPlainText("Tapez 'help' pour la liste des commandes console.\n")
        l_con.addWidget(self.console_output)

        input_box = ConsoleLineEdit(self)
        input_box.setPlaceholderText(
            "Entrez une commande console (ex: move 10 10) -- ↑/↓ pour l'historique"
        )
        input_box.returnPressed.connect(lambda: self._on_console_command(input_box))
        l_con.addWidget(input_box)

        dock_console.setWidget(w_con)
        self.addDockWidget(Qt.DockWidgetArea.BottomDockWidgetArea, dock_console)

    def _on_canvas_cursor_moved(self, x, y):
        self.pos_label.setText(f"X: {x:.2f} mm  |  Y: {y:.2f} mm")

    def _on_zoom_changed(self, factor):
        self.zoom_label.setText(f"{factor * 100:.0f}%")

    def _on_canvas_context_menu(self, pos):
        elements = getattr(self.context, "elements", None)
        if elements is None:
            return
        # Right-clicking an unselected element selects it first (standard
        # UX in most vector editors) so the menu's actions apply to it.
        # Right-clicking empty space or an already-selected element leaves
        # the current (possibly multi-element) selection untouched.
        item = self.canvas.itemAt(pos)
        node = self.canvas._item_to_node.get(item)
        if node is not None and not getattr(node, "emphasized", False):
            elements.set_emphasis([node])
            self.canvas.refresh_selection_highlight()
            self._on_selection_changed(node)

        menu = QMenu(self)
        for action in self._single_selection_actions:
            menu.addAction(action)
        menu.addSeparator()
        for action in self._multi_selection_actions:
            menu.addAction(action)
        menu.exec(self.canvas.mapToGlobal(pos))

    def _update_undo_redo_actions(self):
        # Same query (elements.undo.has_undo/has_redo) and the same
        # "undoredo" signal the classic wx UI uses to keep its own Undo/
        # Redo controls in sync (madgrav/gui/wxmmain.py) -- previously
        # these stayed permanently clickable here regardless of whether
        # there was actually anything to undo/redo.
        elements = getattr(self.context, "elements", None)
        undo = getattr(elements, "undo", None) if elements is not None else None
        self.act_undo.setEnabled(bool(undo.has_undo()) if undo is not None else False)
        self.act_redo.setEnabled(bool(undo.has_redo()) if undo is not None else False)
        # Same wording the classic wx UI builds on menu-open (madgrav/gui/
        # wxmmain.py: on_menu_open's undo_label/redo_label) -- "Annuler
        # Déplacer" instead of a bare "Annuler" that never says WHAT would
        # be undone. Refreshed live here instead of on menu-open since
        # this already fires on every "undoredo" signal.
        undo_msg = undo.undo_string() if undo is not None else ""
        redo_msg = undo.redo_string() if undo is not None else ""
        self.act_undo.setText(f"Annuler {undo_msg}" if undo_msg else "Annuler")
        self.act_redo.setText(f"Rétablir {redo_msg}" if redo_msg else "Rétablir")

    def _update_paste_action(self):
        # "Coller" doesn't depend on the current SELECTION (unlike Copy/
        # Cut/Delete/...), so it isn't in _single_selection_actions -- it
        # depends on whether the clipboard actually has anything, which
        # nothing previously checked here. Same check and the same
        # "icons" signal (fired by clipboard copy/cut) the classic wx UI
        # uses for this exact rule (madgrav/gui/wxmmain.py:
        # clipboard_filled).
        elements = getattr(self.context, "elements", None)
        filled = False
        try:
            destination = elements._clipboard_default
            filled = len(elements._clipboard[destination]) > 0
        except (AttributeError, TypeError, KeyError):
            pass
        self.act_paste.setEnabled(filled)

    def _update_selection_dependent_actions(self, selected=None):
        """Grey out Edit-menu actions that need a selection instead of
        leaving them clickable-but-silently-no-op like before.

        selected, if given, is the already-computed list of emphasized
        nodes (see _on_selection_changed, which shares one list across
        every _update_*/status-bar step instead of each re-walking the
        whole document separately for the same information)."""
        if selected is None:
            elements = getattr(self.context, "elements", None)
            selected = list(elements.elems(emphasized=True)) if elements is not None else []
        count = len(selected)
        for action in self._single_selection_actions:
            action.setEnabled(count >= 1)
        for action in self._multi_selection_actions:
            action.setEnabled(count >= 2)

    def _update_position_panel(self, selected=None):
        """Populate the Position/Taille dock for exactly one selected
        element; disabled otherwise (a group edit needs different pivot
        semantics than a single element, so it's out of scope here).

        selected: see _update_selection_dependent_actions."""
        if selected is None:
            elements = getattr(self.context, "elements", None)
            selected = list(elements.elems(emphasized=True)) if elements is not None else []
        if len(selected) != 1:
            self._position_panel.setEnabled(False)
            return
        node = selected[0]
        try:
            bounds = node.bounds
        except Exception:
            bounds = None
        if bounds is None:
            self._position_panel.setEnabled(False)
            return
        from madgrav.core.units import Length

        x_mm = Length(amount=bounds[0]).mm
        y_mm = Length(amount=bounds[1]).mm
        w_mm = Length(amount=bounds[2] - bounds[0]).mm
        h_mm = Length(amount=bounds[3] - bounds[1]).mm
        # Block signals while populating so this doesn't itself trigger
        # editingFinished and re-apply the value it was just set to.
        self.pos_x_spin.blockSignals(True)
        self.pos_y_spin.blockSignals(True)
        self.pos_x_spin.setValue(x_mm)
        self.pos_y_spin.setValue(y_mm)
        self.pos_x_spin.blockSignals(False)
        self.pos_y_spin.blockSignals(False)
        self.size_w_spin.blockSignals(True)
        self.size_h_spin.blockSignals(True)
        self.size_w_spin.setValue(max(0.01, w_mm))
        self.size_h_spin.setValue(max(0.01, h_mm))
        self.size_w_spin.blockSignals(False)
        self.size_h_spin.blockSignals(False)
        self._position_panel.setEnabled(not getattr(node, "lock", False))

        # Not every element type carries a stroke width (e.g. images) --
        # disable just this one field rather than the whole panel.
        stroke_width = getattr(node, "stroke_width", None)
        self.stroke_width_spin.setEnabled(stroke_width is not None)
        if stroke_width is not None:
            self.stroke_width_spin.blockSignals(True)
            self.stroke_width_spin.setValue(Length(amount=stroke_width).mm)
            self.stroke_width_spin.blockSignals(False)

    def _pick_and_apply_color(self, kind: str):
        """kind is "fill" or "stroke" -- both existing console commands,
        parsed the same way as _on_position_field_edited's console pipe."""
        elements = getattr(self.context, "elements", None)
        if elements is None or elements.first_emphasized is None:
            return
        from PyQt6.QtWidgets import QColorDialog

        color = QColorDialog.getColor(parent=self, title="Choisir une couleur")
        if not color.isValid():
            return
        if self._run_console(f"{kind} {color.name()}"):
            self.canvas.render_elements()
            verb = "Remplissage" if kind == "fill" else "Contour"
            self.status_bar.showMessage(f"{verb} modifié.", 2000)

    def _on_stroke_width_edited(self):
        elements = getattr(self.context, "elements", None)
        if elements is None or elements.first_emphasized is None:
            return
        width_mm = self.stroke_width_spin.value()
        if self._run_console(f"stroke-width {width_mm}mm"):
            self.canvas.render_elements()
            self.status_bar.showMessage(f"Épaisseur de trait : {width_mm:.2f} mm", 2000)

    def _on_position_field_edited(self):
        elements = getattr(self.context, "elements", None)
        if elements is None or elements.first_emphasized is None:
            return
        x = self.pos_x_spin.value()
        y = self.pos_y_spin.value()
        if self._run_console(f"position {x}mm {y}mm"):
            self.canvas.render_elements()
            self.status_bar.showMessage(f"Position: {x:.2f}, {y:.2f} mm", 2000)

    def _on_size_field_edited(self):
        # "resize <x> <y> <w> <h>" sets width/height AND position in one
        # call -- reusing the current pos_x_spin/pos_y_spin values keeps
        # the top-left corner fixed, so this behaves as a pure resize
        # rather than an implicit move to the origin.
        elements = getattr(self.context, "elements", None)
        if elements is None or elements.first_emphasized is None:
            return
        x = self.pos_x_spin.value()
        y = self.pos_y_spin.value()
        w = self.size_w_spin.value()
        h = self.size_h_spin.value()
        if self._run_console(f"resize {x}mm {y}mm {w}mm {h}mm"):
            self.canvas.render_elements()
            self._update_position_panel()
            self.status_bar.showMessage(f"Taille : {w:.2f} × {h:.2f} mm", 2000)

    def _on_selection_changed(self, node):
        # Compute the emphasized-nodes list once and share it with every
        # step below -- each used to independently re-walk the whole
        # document (elements.elems(emphasized=True) is O(n)) for the same
        # information on every single selection change.
        elements = getattr(self.context, "elements", None)
        selected = list(elements.elems(emphasized=True)) if elements is not None else []
        self._update_selection_dependent_actions(selected)
        self._update_position_panel(selected)
        if node is None:
            self.selection_label.setText("Aucune sélection")
            return
        # The canvas' rubber-band/Shift-click multi-selection only passes
        # its first node through this signal -- check the real emphasized
        # count so a multi-selection doesn't silently look like a
        # single-element one in the status bar.
        if len(selected) > 1:
            self.selection_label.setText(f"Sélection: {len(selected)} éléments")
            return
        label = None
        if hasattr(node, "display_label"):
            label = node.display_label()
        label = label or str(node)
        details = []
        speed = getattr(node, "speed", None)
        if isinstance(speed, (int, float)):
            details.append(f"{speed:.0f} mm/s")
        power = getattr(node, "power", None)
        if isinstance(power, (int, float)):
            details.append(f"{power:.0f} ppi")
        try:
            bounds = node.bounds
            if bounds is not None:
                from madgrav.core.units import Length

                w = Length(amount=bounds[2] - bounds[0]).mm
                h = Length(amount=bounds[3] - bounds[1]).mm
                details.append(f"{w:.1f}×{h:.1f} mm")
        except Exception:
            pass
        suffix = f" ({', '.join(details)})" if details else ""
        self.selection_label.setText(f"Sélection: {label}{suffix}")

    def _on_console_command(self, input_widget: "ConsoleLineEdit"):
        cmd = input_widget.text().strip()
        if not cmd:
            return
        self.console_output.appendPlainText(f"> {cmd}")
        input_widget.record(cmd)
        input_widget.clear()

        # Execute on kernel context if console service is active. Results
        # and syntax errors alike are reported via the "console" channel
        # (see the console_output_received wiring in __init__) -- this
        # call itself always returns None, so there is nothing to display
        # here beyond a genuine Python exception.
        try:
            if self.context and hasattr(self.context, "console"):
                self.context.console(cmd + "\n")
        except Exception as ex:
            self.console_output.appendPlainText(f"Erreur: {ex}")

    def _last_used_directory(self) -> str:
        # The file dialog otherwise always opens at the OS default
        # location (typically Documents) instead of remembering where
        # the user last opened/saved something, unlike most apps.
        if self.current_file_path:
            return os.path.dirname(self.current_file_path)
        recent = getattr(self.context, "file0", None)
        return os.path.dirname(recent) if recent else ""

    def _build_open_file_filter(self) -> str:
        # elements.load_types() (used by the classic wx UI's own Open
        # dialog) builds the SAME data as a wx-style "|"-separated
        # wildcard string, not Qt's ";;"-separated one -- built directly
        # here from the same source (kernel.find("load")) instead of
        # parsing/reformatting that string. Previously hardcoded to just
        # svg/dxf/png/jpg/jpeg/bmp, silently hiding every other genuinely
        # supported format (LightBurn .lbrn, Ruida .rd, G-code, EZCad
        # .ezd, xTool .xcs, K40 .egv...) from the default filter.
        kernel = getattr(self.context, "kernel", None)
        if kernel is None:
            return "Tous les Fichiers (*.*)"
        groups = []
        all_exts = []
        for loader, loader_name, sname in kernel.find("load"):
            for description, extensions, mimetype in loader.load_types():
                exts = " ".join(f"*.{ext}" for ext in extensions)
                groups.append(f"{description} ({exts})")
                all_exts.extend(f"*.{ext}" for ext in extensions)
        if not groups:
            return "Tous les Fichiers (*.*)"
        parts = [f"Tous les fichiers supportés ({' '.join(all_exts)})"]
        parts.extend(groups)
        parts.append("Tous les Fichiers (*.*)")
        return ";;".join(parts)

    def _on_open_file(self):
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Ouvrir un Fichier Vectoriel ou Image",
            self._last_used_directory(),
            self._build_open_file_filter(),
        )
        if path:
            self._load_file(path)
            self._refresh_operations_tree()
            self.canvas.render_elements()
            self._on_zoom_fit()

    def _update_window_title(self):
        # Lets the title bar (and the Windows taskbar/Alt-Tab preview)
        # show which document is open, same convention as most document-
        # based apps -- previously static regardless of what was loaded.
        dirty_marker = "*" if getattr(self, "_dirty", False) else ""
        if self.current_file_path:
            name = os.path.basename(self.current_file_path)
            self.setWindowTitle(f"{dirty_marker}{name} — {self._BASE_TITLE}")
        else:
            self.setWindowTitle(f"{dirty_marker}{self._BASE_TITLE}")

    def _load_file(self, path: str) -> bool:
        """Load a single file into the current document. Returns success."""
        self.status_bar.showMessage(f"Chargement de {path}...", 3000)
        try:
            if not (self.context and hasattr(self.context, "elements")):
                return False
            result = self.context.elements.load(path)
            if result is False:
                self.console_output.appendPlainText(f"Fichier non reconnu: {path}")
                return False
            self.current_file_path = path
            self._dirty = False
            self._update_window_title()
            self.console_output.appendPlainText(f"Fichier chargé: {path}")
            self._add_to_recent_files(path)
            return True
        except Exception as ex:
            self.console_output.appendPlainText(f"Erreur de chargement: {ex}")
            return False

    _MAX_RECENT_FILES = 20

    def _add_to_recent_files(self, pathname):
        # Same storage keys and shift-to-front logic as the classic wx
        # UI's set_file_as_recently_used (madgrav/gui/wxmmain.py).
        context = self.context
        recent = [getattr(context, f"file{i}", None) for i in range(self._MAX_RECENT_FILES)]
        recent = [r for r in recent if r and r != pathname]
        recent.insert(0, pathname)
        for i in range(self._MAX_RECENT_FILES):
            setattr(context, f"file{i}", recent[i] if i < len(recent) else "")
        self._populate_recent_menu()

    def _populate_recent_menu(self):
        self.recent_menu.clear()
        context = self.context
        found_any = False
        for i in range(self._MAX_RECENT_FILES):
            fname = getattr(context, f"file{i}", None)
            if not fname or not os.path.exists(fname):
                continue
            found_any = True
            act = QAction(f"{i + 1}  {os.path.basename(fname)}", self)
            act.setToolTip(fname)
            act.triggered.connect(
                lambda checked=False, f=fname: self._on_open_recent_file(f)
            )
            self.recent_menu.addAction(act)
        self.recent_menu.setEnabled(found_any)
        if found_any:
            self.recent_menu.addSeparator()
            act_clear = QAction("Vider l'historique", self)
            act_clear.triggered.connect(self._on_clear_recent_files)
            self.recent_menu.addAction(act_clear)

    def _on_open_recent_file(self, path):
        if self._load_file(path):
            self._refresh_operations_tree()
            self.canvas.render_elements()
            self._on_zoom_fit()
        else:
            # The file may have moved/been deleted since it was recorded
            # -- drop it from the list instead of leaving a permanently
            # broken entry the user would keep clicking on.
            self._remove_from_recent_files(path)

    def _remove_from_recent_files(self, pathname):
        context = self.context
        recent = [getattr(context, f"file{i}", None) for i in range(self._MAX_RECENT_FILES)]
        recent = [r for r in recent if r and r != pathname]
        for i in range(self._MAX_RECENT_FILES):
            setattr(context, f"file{i}", recent[i] if i < len(recent) else "")
        self._populate_recent_menu()

    def _on_clear_recent_files(self):
        context = self.context
        for i in range(self._MAX_RECENT_FILES):
            setattr(context, f"file{i}", "")
        self._populate_recent_menu()

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
        else:
            super().dragEnterEvent(event)

    def dropEvent(self, event):
        """Accepts one or more dropped files, mirroring the classic wx window's
        multi-file drop handling (madgrav.gui.wxmmain.on_drop_file)."""
        urls = event.mimeData().urls()
        if not urls:
            super().dropEvent(event)
            return
        event.acceptProposedAction()

        rejected = []
        for url in urls:
            path = url.toLocalFile()
            if not path:
                continue
            if not self._load_file(path):
                rejected.append(path)

        self._refresh_operations_tree()
        self.canvas.render_elements()
        self._on_zoom_fit()

        if rejected:
            QMessageBox.warning(
                self,
                "Fichiers non reconnus",
                "Certains fichiers n'ont pas pu être chargés :\n" + "\n".join(rejected),
            )

    def _run_console(self, cmd):
        """Run a kernel console command and echo it to the console dock."""
        self.console_output.appendPlainText(f"> {cmd}")
        try:
            self.context.console(cmd + "\n")
        except Exception as ex:
            self.console_output.appendPlainText(f"Erreur: {ex}")
            return False
        return True

    def _has_active_device(self):
        device = getattr(self.context, "device", None)
        return device is not None and getattr(device, "spooler", None) is not None

    def _needs_arming(self) -> bool:
        # Whether the arm/disarm safety step is required at all -- a user
        # preference (madgrav/gui/wxmmain.py: needs_arming), on by default.
        return bool(self.context.setting(bool, "laserpane_arm", True))

    def _laser_armed(self) -> bool:
        self.context.setting(bool, "_laser_may_run", False)
        return bool(self.context._laser_may_run)

    def _may_start(self) -> bool:
        # Same combined check _on_start() itself enforces on click -- used
        # here to grey out "Démarrer" proactively instead of only warning
        # after the fact, matching wx's may_run().
        if not self._has_active_device():
            return False
        if self._needs_arming() and not self._laser_armed():
            return False
        return True

    def _update_arm_button(self):
        needs_arm = self._needs_arming()
        self.btn_arm.setVisible(needs_arm)
        if needs_arm:
            armed = self._laser_armed()
            self.btn_arm.setChecked(armed)
            if armed:
                self.btn_arm.setText("🔓 Désarmer")
                self.btn_arm.setToolTip("Désarmer le laser (empêche tout démarrage de travail).")
            else:
                self.btn_arm.setText("🔒 Armer")
                self.btn_arm.setToolTip("Armer le laser avant de pouvoir démarrer un travail (sécurité).")
        self.btn_start.setEnabled(self._may_start())

    def _set_armed(self, armed: bool):
        self.context.setting(bool, "_laser_may_run", False)
        self.context._laser_may_run = armed
        # Update immediately for instant feedback rather than waiting on
        # the kernel signal queue's own round-trip; the listener below
        # still keeps this in sync if arming happens from elsewhere (a wx
        # panel, in a mixed wx+Qt session).
        self._update_arm_button()
        self.context.signal("laser_armed", armed)

    def _on_toggle_arm(self):
        self._set_armed(self.btn_arm.isChecked())

    def _coolant_service(self):
        return getattr(self.context.root, "coolant", None) if self.context is not None else None

    def _has_coolant(self) -> bool:
        device = getattr(self.context, "device", None)
        coolant = self._coolant_service()
        if device is None or coolant is None or not hasattr(device, "device_coolant"):
            return False
        return bool(coolant.get_device_coolant(device))

    def _update_coolant_button(self):
        has_cool = self._has_coolant()
        self.btn_coolant.setVisible(has_cool)
        if not has_cool:
            return
        device = self.context.device
        on = bool(self._coolant_service().coolant_state(device))
        self.btn_coolant.setChecked(on)
        if on:
            self.btn_coolant.setText("💧 Coolant (Actif)")
            self.btn_coolant.setToolTip("Désactiver le liquide de refroidissement / air-assist.")
        else:
            self.btn_coolant.setText("💧 Coolant")
            self.btn_coolant.setToolTip("Activer le liquide de refroidissement / air-assist.")

    def _on_toggle_coolant(self):
        device = getattr(self.context, "device", None)
        coolant = self._coolant_service()
        if device is None or coolant is None:
            return
        coolant.coolant_toggle(device)
        # coolant_toggle() itself fires "coolant_set", which the listener
        # below also picks up -- update immediately too for instant
        # feedback, same reasoning as the arm button.
        self._update_coolant_button()

    @staticmethod
    def _format_hms(seconds) -> str:
        from math import isinf

        if isinf(seconds):
            return "∞"
        seconds = max(0, seconds)
        hours, remainder = divmod(seconds, 3600)
        minutes, secs = divmod(remainder, 60)
        return f"{int(hours)}:{int(minutes):02d}:{int(secs):02d}"

    def _update_job_progress(self):
        """Live job-progress indicator in the status bar -- Qt counterpart
        to wx's SimpleInfoWidget (madgrav/gui/statusbarwidgets/
        infowidget.py), simplified to just the currently-running job's
        percentage and elapsed/remaining time (skips the multi-job queue
        totals wx also shows, a lower-value addition on top of the single-
        job case). Polled by self._job_timer rather than wx's much hotter
        driver;position signal -- see job_progress_changed's own comment
        for why."""
        from madgrav.core.laserjob import LaserJob

        device = getattr(self.context, "device", None)
        spooler = getattr(device, "spooler", None) if device is not None else None
        active = None
        if spooler is not None:
            for spool_obj in spooler.queue:
                if isinstance(spool_obj, LaserJob) and spool_obj.is_running():
                    active = spool_obj
                    break

        if active is None:
            self.job_label.setVisible(False)
            self.job_progress.setVisible(False)
            if self._job_timer.isActive():
                self._job_timer.stop()
            return

        if not self._job_timer.isActive():
            self._job_timer.start()

        total = len(active.items)
        pos = active.item_index
        percentage = int(min(100, 100 * pos / total)) if total > 0 else 0
        elapsed = time.time() - active.time_started if active.time_started else 0
        estimate = active.estimate_time()
        remaining = max(0.0, estimate - elapsed) if estimate else 0.0

        self.job_progress.setValue(percentage)
        self.job_progress.setVisible(True)
        self.job_label.setText(
            f"{active.label}: {pos}/{total} -- "
            f"{self._format_hms(elapsed)} écoulé, {self._format_hms(remaining)} restant"
        )
        self.job_label.setVisible(True)

    def _on_home(self):
        if not self._has_active_device():
            QMessageBox.warning(
                self,
                "Origine",
                "Aucun appareil laser actif -- connectez votre graveuse d'abord.",
            )
            return
        if self._run_console("home"):
            self.status_bar.showMessage("Retour à l'origine envoyé.", 3000)

    def _on_frame(self):
        if not self._has_active_device():
            QMessageBox.warning(
                self,
                "Cadre",
                "Aucun appareil laser actif -- connectez votre graveuse d'abord.",
            )
            return
        # "trace" is a no-op with a clean status message if nothing is
        # selected/emphasized -- no separate empty-selection check needed.
        if self._run_console("trace quick"):
            self.status_bar.showMessage("Cadrage envoyé.", 3000)

    def _on_pause(self):
        # "pause" is registered per-device (grbl/balormk/lihuiyu/ruida/
        # moshi each add their own) -- with no active device it isn't a
        # registered command at all, and the kernel reports that via the
        # console channel rather than raising, so _run_console would
        # otherwise report success here with nothing actually sent.
        if not self._has_active_device():
            QMessageBox.warning(
                self,
                "Pause",
                "Aucun appareil laser actif -- connectez votre graveuse d'abord.",
            )
            return
        if self._run_console("pause"):
            self.status_bar.showMessage("Pause / reprise envoyée.", 3000)

    def _on_stop(self):
        # Emergency stop: no confirmation dialog on purpose -- hesitation
        # defeats the point of an e-stop. Same registered-per-device
        # reasoning as _on_pause above -- but a warning dialog here, not a
        # silent no-op, since a user hitting STOP needs to know nothing
        # was actually sent rather than trusting a misleading status
        # message on a safety-critical control.
        if not self._has_active_device():
            QMessageBox.warning(
                self,
                "Arrêt d'urgence",
                "Aucun appareil laser actif -- rien à arrêter.",
            )
            return
        if self._run_console("estop"):
            self.status_bar.showMessage("ARRÊT D'URGENCE envoyé.", 5000)

    def _has_objects_outside_bed(self) -> bool:
        # Same pre-flight check the classic wx UI's own "concerns" system
        # runs before a job (madgrav/gui/gui_mixins.py: has_objects_outside)
        # -- flagged there as CRITICAL, because an element assigned to an
        # active operation but positioned outside the burnable area can
        # send the laser head into the rails. Only replicated this one
        # check here (not wx's full multi-severity concerns system with
        # ~10 different settings-gated checks) -- it's the one with a
        # genuine physical-safety consequence, self-contained enough to
        # verify confidently in this cycle's scope.
        from madgrav.core.units import UNITS_PER_MM

        elements = getattr(self.context, "elements", None)
        if elements is None:
            return False
        wd = self.canvas.bed_width * UNITS_PER_MM
        ht = self.canvas.bed_height * UNITS_PER_MM
        try:
            ops = list(elements.ops())
        except AttributeError:
            return False
        for op in ops:
            if not (hasattr(op, "output") and op.output):
                continue
            for refnode in getattr(op, "children", []):
                node = getattr(refnode, "node", None)
                if node is None:
                    continue
                if op.type in ("op cut", "op engrave"):
                    bb = getattr(node, "bounds", None)
                else:
                    bb = getattr(node, "paint_bounds", None)
                    if bb is None:
                        bb = getattr(node, "bounds", None)
                if bb is None:
                    continue
                if bb[2] > wd or bb[0] < 0 or bb[3] > ht or bb[1] < 0:
                    return True
        return False

    def _has_ambitious_operations(self) -> bool:
        # Simplified version of wx's other CRITICAL pre-flight check
        # (madgrav/gui/gui_mixins.py: has_ambitious_operations) -- too-
        # fast operations risking erratic stepper behaviour/incomplete
        # burns. Only the generic per-device max-speed comparison is
        # replicated here, not wx's additional per-operation-type power/
        # speed "danger zone" tuples (device.dangerlevel_{optype}, an
        # 8-value enable/threshold structure) -- an advanced, rarely-
        # configured feature few devices set at all; the generic check
        # alone already catches the common case with much lower risk of
        # a subtly wrong safety-critical implementation.
        elements = getattr(self.context, "elements", None)
        device = getattr(self.context, "device", None)
        if elements is None or device is None:
            return False
        max_vector_speed = getattr(device, "max_vector_speed", None)
        max_raster_speed = getattr(device, "max_raster_speed", None)
        try:
            ops = list(elements.ops())
        except AttributeError:
            return False
        for op in ops:
            if not (
                hasattr(op, "output")
                and op.output
                and hasattr(op, "speed")
                and len(getattr(op, "children", [])) > 0
            ):
                continue
            if (
                op.type in ("op cut", "op engrave")
                and max_vector_speed is not None
                and op.speed >= max_vector_speed
            ):
                return True
            if (
                op.type in ("op raster", "op image")
                and max_raster_speed is not None
                and op.speed >= max_raster_speed
            ):
                return True
        return False

    def _compute_concerns(self):
        """Non-blocking counterpart to the CRITICAL pre-flight checks above.
        Simplified subset of wx's "concerns" system (gui_mixins.py) --
        NORMAL/LOW severity items that are worth surfacing but shouldn't
        interrupt Start with a confirmation dialog. Skips the DPI and
        raster-close-to-edge/unsupported-optimisation checks, which need
        device.view.dpi_to_steps()/get_raster_instructions() plumbing not
        otherwise used in the Qt shell; those are lower-value than the two
        checks kept here."""
        elements = getattr(self.context, "elements", None)
        if elements is None:
            return []
        concerns = []
        try:
            unassigned, nonburnt = elements.have_unburnable_elements()
        except AttributeError:
            unassigned, nonburnt = False, False
        if unassigned:
            concerns.append(
                "Des éléments ne sont assignés à aucune opération et ne seront pas gravés."
            )
        if nonburnt:
            concerns.append(
                "Des éléments sont assignés uniquement à des opérations désactivées "
                "et ne seront donc pas gravés."
            )
        hidden_count = 0
        for node in elements.elems():
            if getattr(node, "hidden", False):
                hidden_count += 1
        if hidden_count:
            concerns.append(
                f"{hidden_count} élément(s) masqué(s) ne seront pas gravés."
            )
        return concerns

    def _update_warnings_indicator(self):
        concerns = self._compute_concerns()
        self._concerns = concerns
        if concerns:
            self.btn_warnings.setText(f"⚠ {len(concerns)} avertissement(s)")
            self.btn_warnings.setToolTip("\n".join(concerns))
            self.btn_warnings.setVisible(True)
        else:
            self.btn_warnings.setVisible(False)

    def _show_warnings_dialog(self):
        concerns = getattr(self, "_concerns", None) or self._compute_concerns()
        if not concerns:
            return
        QMessageBox.information(
            self,
            "Avertissements",
            "\n\n".join(f"- {c}" for c in concerns),
        )

    def _on_start(self):
        if not self._has_active_device():
            QMessageBox.warning(
                self,
                "Démarrer",
                "Aucun appareil laser actif -- connectez votre graveuse d'abord.",
            )
            return
        if self._needs_arming() and not self._laser_armed():
            QMessageBox.warning(
                self,
                "Démarrer",
                "Le laser n'est pas armé -- cliquez sur « Armer » avant de "
                "démarrer un travail (sécurité).",
            )
            return
        try:
            has_burnable = self.context.elements.have_burnable_elements()
        except AttributeError:
            has_burnable = False
        if not has_burnable:
            QMessageBox.information(
                self,
                "Démarrer",
                "Rien à graver -- les opérations doivent avoir des formes "
                "assignées (vérifiez l'arbre Opérations).",
            )
            return
        try:
            has_unassigned = self.context.elements.have_unassigned_elements()
        except AttributeError:
            has_unassigned = False
        if has_unassigned:
            answer = QMessageBox.question(
                self,
                "Formes non assignées",
                "Certaines formes ne sont assignées à aucune opération et ne "
                "seront pas gravées.\n\nDémarrer quand même ?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No,
            )
            if answer != QMessageBox.StandardButton.Yes:
                return
        if self._has_objects_outside_bed():
            answer = QMessageBox.warning(
                self,
                "Éléments hors de la zone de gravure",
                "Certains éléments assignés à une opération active se trouvent "
                "en dehors de la zone de gravure -- risque de collision de la "
                "tête laser avec les rails.\n\nDémarrer quand même ?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No,
            )
            if answer != QMessageBox.StandardButton.Yes:
                return
        if self._has_ambitious_operations():
            answer = QMessageBox.warning(
                self,
                "Vitesse potentiellement trop élevée",
                "Une ou plusieurs opérations dépassent la vitesse maximale "
                "recommandée pour cet appareil -- risque de comportement "
                "erratique des moteurs ou de gravure incomplète.\n\n"
                "Démarrer quand même ?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No,
            )
            if answer != QMessageBox.StandardButton.Yes:
                return
        prefer_threaded = self.context.setting(bool, "prefer_threaded_mode", True)
        prefix = "threaded " if prefer_threaded else ""
        new_plan = self.context.planner.get_free_plan()
        if self._run_console(
            f"{prefix}plan{new_plan} clear copy preprocess validate blob preopt optimize spool"
        ):
            self.status_bar.showMessage("Travail envoyé au spooler.", 5000)
            if self._needs_arming():
                # Same auto-disarm-after-start the classic wx UI's own
                # run_job() does -- staying armed indefinitely after a
                # job starts would let a second click fire another job
                # with no fresh confirmation.
                self._set_armed(False)

    def _on_save(self):
        if not (self.context and hasattr(self.context, "elements")):
            return
        path = self.current_file_path
        if not path:
            path = self._prompt_save_path()
            if not path:
                return
        self._save_to(path)

    def _on_save_as(self):
        if not (self.context and hasattr(self.context, "elements")):
            return
        path = self._prompt_save_path()
        if not path:
            return
        self._save_to(path)

    def _prompt_save_path(self):
        path, _sel = QFileDialog.getSaveFileName(
            self,
            "Enregistrer le Projet",
            self.current_file_path or self._last_used_directory(),
            "Fichiers SVG (*.svg);;Tous les Fichiers (*.*)",
        )
        return path

    def _save_to(self, path: str):
        try:
            # save() returns False (not an exception) for an unrecognized
            # extension -- e.g. no registered writer matches ".txt". Check
            # it explicitly instead of always reporting success.
            saved = self.context.elements.save(path)
        except Exception as ex:
            QMessageBox.warning(self, "Enregistrer", f"Échec de l'enregistrement:\n{ex}")
            return
        if not saved:
            QMessageBox.warning(
                self,
                "Enregistrer",
                f"Format de fichier non reconnu, rien n'a été enregistré :\n{path}",
            )
            return
        self.current_file_path = path
        self._dirty = False
        self._update_window_title()
        self.status_bar.showMessage(f"Enregistré: {path}", 3000)
        self.console_output.appendPlainText(f"Projet enregistré: {path}")

    def _on_new(self):
        elements = getattr(self.context, "elements", None)
        has_content = bool(elements is not None and list(elements.elem_branch.flat())[1:])
        if has_content:
            answer = QMessageBox.question(
                self,
                "Nouveau Projet",
                "Vider le projet actuel ? Les modifications non enregistrées seront perdues.",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No,
            )
            if answer != QMessageBox.StandardButton.Yes:
                return
        if elements is not None:
            elements.clear_all(ops_too=True)
        self.current_file_path = None
        self._dirty = False
        self._update_window_title()
        self._refresh_operations_tree()
        self.canvas.render_elements()
        self._on_zoom_fit()
        self._update_selection_dependent_actions()
        self._update_position_panel()
        self.status_bar.showMessage("Nouveau projet.", 3000)

    def _on_undo(self):
        if self._run_console("undo"):
            self._refresh_operations_tree()
            self.canvas.render_elements()
            # undo can change which elements exist and what's selected --
            # without this, the Position/Taille panel and the Edit menu's
            # enabled states keep showing whatever was true before the
            # undo until something else happens to trigger a refresh.
            self._update_selection_dependent_actions()
            self._update_position_panel()
            self.status_bar.showMessage("Annulé.", 2000)

    def _on_redo(self):
        if self._run_console("redo"):
            self._refresh_operations_tree()
            self.canvas.render_elements()
            self._update_selection_dependent_actions()
            self._update_position_panel()
            self.status_bar.showMessage("Rétabli.", 2000)

    def _on_select_all(self):
        # Same console chain the classic wx UI binds to Ctrl+A.
        if self._run_console("element* select"):
            self.canvas.refresh_selection_highlight()
            self._update_selection_dependent_actions()
            self._update_position_panel()
            self.status_bar.showMessage("Tout sélectionné.", 2000)

    def _on_escape_pressed(self):
        """The Edit menu's "Escape" shortcut. If the canvas has a
        draw/rubber-band/move gesture in progress, cancel that instead of
        deselecting -- matches what a user pressing Escape mid-gesture
        actually expects."""
        if not self.canvas.cancel_in_progress_gesture():
            self._on_deselect_all()

    def _on_deselect_all(self):
        elements = getattr(self.context, "elements", None)
        if elements is None:
            return
        elements.set_emphasis(None)
        self.canvas.refresh_selection_highlight()
        self._on_selection_changed(None)
        self.status_bar.showMessage("Sélection effacée.", 2000)

    def _on_duplicate(self):
        elements = getattr(self.context, "elements", None)
        if elements is None or elements.first_emphasized is None:
            return
        if self._run_console("element copy"):
            self._refresh_operations_tree()
            self.canvas.render_elements()
            # "element copy" selects the new copy -- without this the
            # Position/Taille panel and Edit-menu action states keep
            # showing whatever was true for the ORIGINAL element.
            self._update_selection_dependent_actions()
            self._update_position_panel()
            self.status_bar.showMessage("Élément dupliqué.", 2000)

    def _on_copy(self):
        elements = getattr(self.context, "elements", None)
        if elements is None or elements.first_emphasized is None:
            return
        if self._run_console("clipboard copy"):
            self.status_bar.showMessage("Copié dans le presse-papiers.", 2000)

    def _on_cut(self):
        elements = getattr(self.context, "elements", None)
        if elements is None or elements.first_emphasized is None:
            return
        if self._run_console("clipboard cut"):
            self._refresh_operations_tree()
            self.canvas.render_elements()
            # Cut empties the selection -- without this the panel/actions
            # keep showing state for an element that no longer exists.
            self._update_selection_dependent_actions()
            self._update_position_panel()
            self.status_bar.showMessage("Coupé dans le presse-papiers.", 2000)

    def _on_paste(self):
        elements = getattr(self.context, "elements", None)
        if elements is None:
            return
        # A small offset so the pasted copy doesn't land exactly on top of
        # what's already there and looks like nothing happened.
        if self._run_console("clipboard paste -x 5mm -y 5mm"):
            self._refresh_operations_tree()
            self.canvas.render_elements()
            # Paste selects the newly-pasted element(s) -- same reasoning
            # as _on_cut above.
            self._update_selection_dependent_actions()
            self._update_position_panel()
            self.status_bar.showMessage("Collé depuis le presse-papiers.", 2000)

    def _on_rotate(self, degrees: int):
        elements = getattr(self.context, "elements", None)
        if elements is None or elements.first_emphasized is None:
            return
        if self._run_console(f"rotate {degrees}deg"):
            self.canvas.render_elements()
            # Rotation changes the selection's bounding box -- without
            # this the Position/Taille panel keeps showing the pre-rotate
            # X/Y/W/H until something else triggers a refresh.
            self._update_position_panel()
            self.status_bar.showMessage(f"Rotation de {degrees}°.", 2000)

    def _on_mirror(self, scale_x: int, scale_y: int):
        elements = getattr(self.context, "elements", None)
        if elements is None or elements.first_emphasized is None:
            return
        # Mirroring is a negative scale about the selection's own center
        # (the "scale" command's default pivot) -- not the wx UI's
        # material-width "double-side flip" (dialog_flip), which needs the
        # physical stock width and repositions relative to its edge.
        if self._run_console(f"scale {scale_x} {scale_y}"):
            self.canvas.render_elements()
            self._update_position_panel()  # same reasoning as _on_rotate
            axis = "horizontal" if scale_x < 0 else "vertical"
            self.status_bar.showMessage(f"Miroir {axis}.", 2000)

    def _on_lock(self, locked: bool):
        elements = getattr(self.context, "elements", None)
        if elements is None or elements.first_emphasized is None:
            return
        # Same direct assignment as the "lock"/"unlock" console commands'
        # own bodies (madgrav/core/elements/branches.py) -- done here
        # directly rather than through the console pipe, since those
        # commands declare input_type="elements" (no bare/None form) and
        # are only meant to be reached by piping, e.g. "element* lock".
        nodes = list(elements.elems(emphasized=True))
        for node in nodes:
            node.lock = locked
        elements.signal("element_property_update", nodes)
        # No canvas refresh needed: lock has no visual representation on the
        # canvas today (no geometry/color change) -- confirmed items and
        # their paths are untouched by this action before wiring it up.
        # The Position/Taille panel DOES need a refresh though: it disables
        # itself for a locked element (setEnabled(not node.lock)), which
        # otherwise wouldn't take effect until the selection changed again
        # -- letting the user edit X/Y on something they just locked.
        self._update_position_panel()
        verb = "verrouillé" if locked else "déverrouillé"
        self.status_bar.showMessage(f"{len(nodes)} élément(s) {verb}.", 2000)

    def _on_group(self):
        elements = getattr(self.context, "elements", None)
        if elements is None or len(list(elements.elems(emphasized=True))) < 2:
            return
        # Same command the wx tree's "Group elements" context-menu entry
        # runs (madgrav/core/elements/element_treeops.py: group_elements).
        # No canvas refresh: grouping only changes tree structure, not any
        # leaf element's geometry (elem_branch.flat() already traverses
        # into groups), so the operations tree is the only thing stale.
        if self._run_console("group"):
            self._refresh_operations_tree()
            # Grouping collapses N selected elements into 1 selected
            # group node -- "Grouper" (needs >=2) and "Dégrouper" (needs
            # >=1) must be re-evaluated against that new composition.
            self._update_selection_dependent_actions()
            self._update_position_panel()
            self.status_bar.showMessage("Éléments groupés.", 2000)

    def _on_ungroup(self):
        elements = getattr(self.context, "elements", None)
        if elements is None or elements.first_emphasized is None:
            return
        if self._run_console("ungroup"):
            self._refresh_operations_tree()
            self._update_selection_dependent_actions()
            self._update_position_panel()
            self.status_bar.showMessage("Groupe dissous.", 2000)

    def _on_merge_paths(self):
        # "merge"/"subpath" (madgrav/core/elements/branches.py) both
        # declare input_type="elements" with no bare/None form -- unlike
        # most commands used elsewhere in this file, they only work
        # piped from an elements-scoping command, hence "element*
        # merge" rather than a bare self._run_console("merge").
        elements = getattr(self.context, "elements", None)
        if elements is None or len(list(elements.elems(emphasized=True))) < 2:
            return
        if self._run_console("element* merge"):
            self._refresh_operations_tree()
            self.canvas.render_elements()
            self._update_selection_dependent_actions()
            self._update_position_panel()
            self.status_bar.showMessage("Chemins fusionnés.", 2000)

    def _on_break_apart(self):
        elements = getattr(self.context, "elements", None)
        if elements is None or elements.first_emphasized is None:
            return
        if self._run_console("element* subpath"):
            self._refresh_operations_tree()
            self.canvas.render_elements()
            self._update_selection_dependent_actions()
            self._update_position_panel()
            self.status_bar.showMessage("Sous-chemins séparés.", 2000)

    def _on_simplify_path(self):
        elements = getattr(self.context, "elements", None)
        if elements is None or elements.first_emphasized is None:
            return
        selected = list(elements.elems(emphasized=True))
        if not any(getattr(n, "type", None) == "elem path" for n in selected):
            self.status_bar.showMessage(
                "Simplifier ne s'applique qu'aux chemins (pas aux formes de base).",
                3000,
            )
            return
        from PyQt6.QtWidgets import QDialog, QDialogButtonBox

        dlg = QDialog(self)
        dlg.setWindowTitle("Simplifier le Chemin")
        form = QFormLayout(dlg)
        tol_spin = QDoubleSpinBox(dlg)
        tol_spin.setRange(0.01, 100)
        tol_spin.setDecimals(2)
        tol_spin.setSuffix(" mm")
        tol_spin.setValue(0.1)
        form.addRow("Tolérance :", tol_spin)
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel,
            dlg,
        )
        buttons.accepted.connect(dlg.accept)
        buttons.rejected.connect(dlg.reject)
        form.addRow(buttons)

        if dlg.exec() != QDialog.DialogCode.Accepted:
            return
        from madgrav.core.units import UNITS_PER_MM

        # "-t" takes a bare native-unit float, not an "Xmm"-suffixed
        # length string like most other commands used in this file.
        tolerance_native = tol_spin.value() * UNITS_PER_MM
        if self._run_console(f"simplify -t {tolerance_native}"):
            self._refresh_operations_tree()
            self.canvas.render_elements()
            self.status_bar.showMessage("Chemin simplifié.", 2000)

    def _on_add_hatch_effect(self):
        elements = getattr(self.context, "elements", None)
        if elements is None or elements.first_emphasized is None:
            return
        from PyQt6.QtWidgets import QDialog, QDialogButtonBox

        dlg = QDialog(self)
        dlg.setWindowTitle("Remplissage Hachuré")
        form = QFormLayout(dlg)
        dist_spin = QDoubleSpinBox(dlg)
        dist_spin.setRange(0.05, 50)
        dist_spin.setDecimals(2)
        dist_spin.setSuffix(" mm")
        dist_spin.setValue(1.0)
        angle_spin = QDoubleSpinBox(dlg)
        angle_spin.setRange(-360, 360)
        angle_spin.setDecimals(1)
        angle_spin.setSuffix(" °")
        angle_spin.setValue(0)
        delta_spin = QDoubleSpinBox(dlg)
        delta_spin.setRange(-360, 360)
        delta_spin.setDecimals(1)
        delta_spin.setSuffix(" °")
        delta_spin.setValue(0)
        form.addRow("Espacement des lignes :", dist_spin)
        form.addRow("Angle :", angle_spin)
        form.addRow("Incrément d'angle :", delta_spin)
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel,
            dlg,
        )
        buttons.accepted.connect(dlg.accept)
        buttons.rejected.connect(dlg.reject)
        form.addRow(buttons)

        if dlg.exec() != QDialog.DialogCode.Accepted:
            return
        cmd = (
            f"effect-hatch -d {dist_spin.value()}mm "
            f"-a {angle_spin.value()}deg -b {delta_spin.value()}deg"
        )
        if self._run_console(cmd):
            self._refresh_operations_tree()
            self.canvas.render_elements()
            self.status_bar.showMessage("Remplissage hachuré ajouté.", 3000)

    def _on_add_offset_path(self):
        elements = getattr(self.context, "elements", None)
        if elements is None or elements.first_emphasized is None:
            return
        from PyQt6.QtWidgets import QDialog, QDialogButtonBox

        dlg = QDialog(self)
        dlg.setWindowTitle("Décaler (Offset)")
        form = QFormLayout(dlg)
        dist_spin = QDoubleSpinBox(dlg)
        dist_spin.setRange(-50, 50)
        dist_spin.setDecimals(2)
        dist_spin.setSuffix(" mm")
        dist_spin.setSingleStep(0.5)
        dist_spin.setValue(2.0)
        form.addRow("Distance (positif = extérieur) :", dist_spin)
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel,
            dlg,
        )
        buttons.accepted.connect(dlg.accept)
        buttons.rejected.connect(dlg.reject)
        form.addRow(buttons)

        if dlg.exec() != QDialog.DialogCode.Accepted:
            return
        distance = dist_spin.value()
        if distance == 0:
            self.status_bar.showMessage("Distance de décalage invalide (0mm).", 3000)
            return
        if self._run_console(f"offset {distance}mm"):
            self._refresh_operations_tree()
            self.canvas.render_elements()
            self.status_bar.showMessage(f"Chemin décalé de {distance:.2f} mm.", 3000)

    def _on_text_anchor(self, anchor: str):
        # "text-anchor" (madgrav/core/elements/shapes.py) silently
        # skips any non-"elem text" node in the selection rather than
        # erroring -- safe to dispatch without a pre-check the way
        # Simplify needs one (that backend hard-rejects instead).
        elements = getattr(self.context, "elements", None)
        if elements is None or elements.first_emphasized is None:
            return
        if self._run_console(f"text-anchor {anchor}"):
            self.canvas.render_elements()
            labels = {"start": "gauche", "middle": "centré", "end": "droite"}
            self.status_bar.showMessage(
                f"Alignement du texte : {labels.get(anchor, anchor)}.", 2000
            )

    def _on_edit_text_content(self):
        elements = getattr(self.context, "elements", None)
        if elements is None or elements.first_emphasized is None:
            return
        selected = list(elements.elems(emphasized=True))
        text_nodes = [n for n in selected if getattr(n, "type", None) == "elem text"]
        if not text_nodes:
            self.status_bar.showMessage(
                "Modifier le Texte ne s'applique qu'à un élément texte.", 3000
            )
            return
        from PyQt6.QtWidgets import QInputDialog

        current_text = getattr(text_nodes[0], "text", "") or ""
        new_text, ok = QInputDialog.getText(
            self, "Modifier le Texte", "Texte :", text=current_text
        )
        if not ok:
            return
        # The console parser has no escape sequence for a literal double
        # quote inside a quoted argument -- same fold-to-single-quote
        # workaround as MadGravQtCanvas._place_text.
        safe_text = new_text.replace('"', "'")
        if self._run_console(f'text-edit "{safe_text}"'):
            self._refresh_operations_tree()
            self.canvas.render_elements()
            self.status_bar.showMessage("Texte modifié.", 2000)

    def _on_grid_array_copy(self):
        # "grid" (madgrav/core/elements/grid.py) always ran with the
        # "-r"/--relative flag here: the two spin fields are the GAP
        # between copies (0mm = edge-to-edge touching), not the raw
        # pitch the console command takes by default -- matches how a
        # user thinks about array spacing (LightBurn's own Array Copy
        # dialog works the same way) more directly than the console
        # command's own "100%"-of-size default would.
        elements = getattr(self.context, "elements", None)
        if elements is None or elements.first_emphasized is None:
            return
        from PyQt6.QtWidgets import QDialog, QDialogButtonBox, QSpinBox

        dlg = QDialog(self)
        dlg.setWindowTitle("Copie en Grille")
        form = QFormLayout(dlg)
        col_spin = QSpinBox(dlg)
        col_spin.setRange(1, 100)
        col_spin.setValue(2)
        row_spin = QSpinBox(dlg)
        row_spin.setRange(1, 100)
        row_spin.setValue(2)
        x_spin = QDoubleSpinBox(dlg)
        x_spin.setRange(0, 1000)
        x_spin.setDecimals(2)
        x_spin.setSuffix(" mm")
        y_spin = QDoubleSpinBox(dlg)
        y_spin.setRange(0, 1000)
        y_spin.setDecimals(2)
        y_spin.setSuffix(" mm")
        form.addRow("Colonnes :", col_spin)
        form.addRow("Lignes :", row_spin)
        form.addRow("Espacement X :", x_spin)
        form.addRow("Espacement Y :", y_spin)
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel,
            dlg,
        )
        buttons.accepted.connect(dlg.accept)
        buttons.rejected.connect(dlg.reject)
        form.addRow(buttons)

        if dlg.exec() != QDialog.DialogCode.Accepted:
            return
        columns = col_spin.value()
        rows = row_spin.value()
        if columns == 1 and rows == 1:
            return  # nothing to copy
        if self._run_console(
            f"grid {columns} {rows} {x_spin.value()}mm {y_spin.value()}mm -r"
        ):
            self._refresh_operations_tree()
            self.canvas.render_elements()
            self.status_bar.showMessage(
                f"Grille {columns}×{rows} créée.", 3000
            )

    def _on_radial_array_copy(self):
        # "radial" (madgrav/core/elements/grid.py) arranges copies on a
        # circular arc around a center offset -radius to the left of
        # the selection (the original stays part of the circle -- see
        # element_radial's own docstring). repeats must be >= 2, which
        # the spinbox range already enforces, avoiding the console
        # command's own CommandSyntaxError path entirely.
        elements = getattr(self.context, "elements", None)
        if elements is None or elements.first_emphasized is None:
            return
        from PyQt6.QtWidgets import QCheckBox, QDialog, QDialogButtonBox, QSpinBox

        dlg = QDialog(self)
        dlg.setWindowTitle("Copie Radiale")
        form = QFormLayout(dlg)
        repeats_spin = QSpinBox(dlg)
        repeats_spin.setRange(2, 360)
        repeats_spin.setValue(6)
        radius_spin = QDoubleSpinBox(dlg)
        radius_spin.setRange(0, 10000)
        radius_spin.setDecimals(2)
        radius_spin.setSuffix(" mm")
        radius_spin.setValue(50)
        start_spin = QDoubleSpinBox(dlg)
        start_spin.setRange(-3600, 3600)
        start_spin.setDecimals(1)
        start_spin.setSuffix(" °")
        start_spin.setValue(0)
        end_spin = QDoubleSpinBox(dlg)
        end_spin.setRange(-3600, 3600)
        end_spin.setDecimals(1)
        end_spin.setSuffix(" °")
        end_spin.setValue(360)
        unrotated_check = QCheckBox(
            "Copies non tournées (garder l'orientation d'origine)", dlg
        )
        form.addRow("Répétitions :", repeats_spin)
        form.addRow("Rayon :", radius_spin)
        form.addRow("Angle de départ :", start_spin)
        form.addRow("Angle de fin :", end_spin)
        form.addRow(unrotated_check)
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel,
            dlg,
        )
        buttons.accepted.connect(dlg.accept)
        buttons.rejected.connect(dlg.reject)
        form.addRow(buttons)

        if dlg.exec() != QDialog.DialogCode.Accepted:
            return
        repeats = repeats_spin.value()
        cmd = (
            f"radial {repeats} {radius_spin.value()}mm "
            f"{start_spin.value()}deg {end_spin.value()}deg"
        )
        if unrotated_check.isChecked():
            cmd += " -u"
        if self._run_console(cmd):
            self._refresh_operations_tree()
            self.canvas.render_elements()
            self.status_bar.showMessage(
                f"{repeats} copies radiales créées.", 3000
            )

    def _on_align(self, direction: str):
        elements = getattr(self.context, "elements", None)
        if elements is None or len(list(elements.elems(emphasized=True))) < 2:
            return
        align_mode = "first" if self.context.setting(bool, "align_first", True) else "last"
        if self._run_console(f"align {align_mode} {direction}"):
            self.canvas.render_elements()
            self._update_position_panel()
            self.status_bar.showMessage("Alignement appliqué.", 2000)

    def _on_geometry_op(self, op: str):
        elements = getattr(self.context, "elements", None)
        if elements is None or len(list(elements.elems(emphasized=True))) < 2:
            return
        if self._run_console(f"element {op}"):
            self._refresh_operations_tree()
            self.canvas.render_elements()
            # The op replaces the selected elements with a single new
            # combined shape -- same reasoning as _on_duplicate/_on_group:
            # the selection composition changed, so the Position/Taille
            # panel and single/multi-selection action states need a
            # refresh, not just the tree/canvas.
            self._update_selection_dependent_actions()
            self._update_position_panel()
            self.status_bar.showMessage("Opération géométrique appliquée.", 2000)

    def _on_classify_all(self):
        elements = getattr(self.context, "elements", None)
        if elements is None:
            return
        # "classify" alone only classifies the current *selection* (and
        # does nothing if nothing is selected) -- "element*" pipes every
        # element in the document into it first, same pattern as
        # "element* select" for Select All. No canvas refresh: classify
        # only reassigns operation membership, never touches geometry.
        if self._run_console("element* classify"):
            self._refresh_operations_tree()
            self.status_bar.showMessage("Éléments assignés aux opérations.", 3000)

    def _on_declassify_selection(self):
        elements = getattr(self.context, "elements", None)
        if elements is None or elements.first_emphasized is None:
            return
        if self._run_console("declassify"):
            self._refresh_operations_tree()
            self.status_bar.showMessage("Éléments retirés des opérations.", 3000)

    def _on_zoom_fit(self):
        target = self.canvas.scene.itemsBoundingRect()
        if target.isEmpty():
            target = self.canvas.sceneRect()
        self.canvas.fitInView(target, Qt.AspectRatioMode.KeepAspectRatio)
        # fitInView() doesn't go through zoom_step()/reset_zoom(), so the
        # zoom_changed signal never fires for it -- sync the label here.
        self._on_zoom_changed(self.canvas.transform().m11())
        self.status_bar.showMessage("Vue ajustée.", 2000)

    def _on_toggle_theme(self):
        self._dark_theme = not self.act_light_theme.isChecked()
        self.context.setting(bool, "qt_dark_theme", True)
        self.context.qt_dark_theme = self._dark_theme
        self.setStyleSheet(MODERN_DARK_QSS if self._dark_theme else MODERN_LIGHT_QSS)
        self.canvas.set_theme(self._dark_theme)
        self._apply_toolbar_button_theme()
        self._apply_tool_icon_theme()
        self.status_bar.showMessage(
            "Thème sombre activé." if self._dark_theme else "Thème clair activé.", 2000
        )

    def _on_show_shortcuts(self):
        # Built from the QActions actually bound at menu-construction time
        # rather than a hardcoded list -- a hand-maintained list would
        # silently drift out of sync the next time a shortcut is added,
        # changed, or removed here (real risk in a file this actively
        # edited this session). QAction.shortcut() also already resolves
        # QKeySequence.StandardKey entries (New, Save, Undo...) to
        # whatever the current platform actually binds, which a hardcoded
        # string wouldn't.
        seen = set()
        rows = []
        for action in self.findChildren(QAction):
            shortcut = action.shortcut()
            if shortcut.isEmpty():
                continue
            label = action.text().replace("&", "").strip()
            if not label:
                continue
            key = (label, shortcut.toString())
            if key in seen:
                continue
            seen.add(key)
            rows.append(key)
        rows.sort(key=lambda r: r[0].lower())
        body = "\n".join(f"{shortcut}\t{label}" for label, shortcut in rows)
        QMessageBox.information(self, "Raccourcis clavier", body)

    def _on_about(self):
        # _run_console()'s only failure signal is a raised exception
        # (see its own docstring/body) -- "window open About" doesn't
        # raise when the wx "window" command itself isn't registered
        # (e.g. wxPython not installed), it just reports the failure on
        # the console channel and returns normally. That silently
        # swallowed the fallback below in exactly the situation it was
        # written for -- checking the registry directly first sidesteps
        # _run_console's blind spot instead of trusting its return value.
        if list(self.context.match("window/About")):
            self._run_console("window open About")
        else:
            QMessageBox.information(
                self,
                "À Propos de MadGrav",
                "MadGrav - Modern Laser Workstation\n"
                "Fork de MeerK40t.\n\n"
                "https://github.com/madgrav/madgrav",
            )

    def _on_open_spooler(self):
        # Same registry check as _on_about -- without it, a click here
        # does nothing at all (no error, no fallback) when wx isn't
        # available, indistinguishable from the button being broken.
        if list(self.context.match("window/JobSpooler")):
            self._open_window("JobSpooler")
        else:
            self.status_bar.showMessage(
                "File d'attente non disponible dans cette configuration.", 3000
            )

    def _on_open_device_wizard(self):
        from madgrav.qt.qt_device_wizard import DeviceSetupWizard

        wizard = DeviceSetupWizard(self.context, self)
        # A fresh instance is created on every click and nothing else ever
        # deletes it -- without this it stays parented to the main window
        # forever once closed, leaking one QWizard (and all its child
        # widgets) per open. WA_DeleteOnClose schedules real cleanup via
        # deleteLater() once it closes; reading created_label right after
        # exec() returns below is still safe since that deletion only
        # happens on the next event-loop iteration, not immediately.
        wizard.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
        if wizard.exec() and wizard.created_label:
            self._refresh_device_status()
            self.status_bar.showMessage(
                f"Machine « {wizard.created_label} » créée et activée.", 5000
            )

    def _open_window(self, window_name: str):
        self._run_console(f"window open {window_name}")

    def _on_tool_select(self):
        self.canvas.set_draw_mode(None)
        self.status_bar.showMessage("Outil: Sélection", 2000)

    def _on_tool_pan(self):
        self.canvas.set_draw_mode(None)
        self.canvas.setDragMode(QGraphicsView.DragMode.ScrollHandDrag)
        self.status_bar.showMessage("Outil: Main (glisser pour déplacer la vue)", 2000)

    def _on_tool_rect(self):
        self.canvas.set_draw_mode("rect")
        self.status_bar.showMessage(
            "Outil: Rectangle (cliquer-glisser pour dessiner, Échap pour annuler)", 3000
        )

    def _on_tool_ellipse(self):
        self.canvas.set_draw_mode("ellipse")
        self.status_bar.showMessage(
            "Outil: Cercle (cliquer-glisser pour dessiner, Échap pour annuler)", 3000
        )

    def _on_tool_line(self):
        self.canvas.set_draw_mode("line")
        self.status_bar.showMessage(
            "Outil: Ligne (cliquer-glisser pour dessiner, Échap pour annuler)", 3000
        )

    def _on_tool_text(self):
        self.canvas.set_draw_mode("text")
        self.status_bar.showMessage(
            "Outil: Texte (cliquer pour placer, Échap pour annuler)", 3000
        )

    def _on_shape_created(self):
        # Draw tools are one-shot: hand control back to the selection tool
        # once a shape has actually been created, matching most vector
        # editors' default behavior.
        self.tool_group.buttons()[0].setChecked(True)
        self._on_tool_select()
        self._refresh_operations_tree()
        self._update_selection_dependent_actions()
        self._update_position_panel()

    def _refresh_operations_tree(self):
        """Populate the operations dock from the real element/operation tree."""
        self.ops_tree.clear()
        elements = getattr(self.context, "elements", None)
        if elements is None:
            return
        try:
            op_branch = elements.op_branch
        except AttributeError:
            return

        def label_of(node):
            if hasattr(node, "display_label"):
                try:
                    result = node.display_label()
                    if result:
                        return result
                except Exception:
                    pass
            return str(node)

        for op in op_branch.children:
            speed = getattr(op, "speed", None)
            power = getattr(op, "power", None)
            speed_txt = f"{speed:.0f} mm/s" if isinstance(speed, (int, float)) else ""
            power_txt = f"{power:.0f}" if isinstance(power, (int, float)) else ""
            # implicit_passes (Parameters mixin) is the effective pass
            # count -- 1 when passes_custom is off, else max(passes, 1) --
            # matching what the engine actually runs, not the raw stored
            # "passes" value which defaults to 0 and is meaningless alone.
            passes_txt = (
                str(op.implicit_passes) if hasattr(op, "implicit_passes") else ""
            )
            op_item = QTreeWidgetItem(
                self.ops_tree, [label_of(op), speed_txt, power_txt, passes_txt]
            )
            op_item.setData(0, Qt.ItemDataRole.UserRole, op)
            for child in getattr(op, "children", []):
                child_item = QTreeWidgetItem(
                    op_item, [f"  {label_of(child)}", "", "", ""]
                )
                # child is usually a reference node; select the real element
                # it points to, matching what clicking it on the canvas does.
                child_item.setData(
                    0, Qt.ItemDataRole.UserRole, getattr(child, "node", child)
                )
        self.ops_tree.expandAll()

    def _on_tree_item_clicked(self, item, _column):
        node = item.data(0, Qt.ItemDataRole.UserRole)
        self._tree_action_node = node
        self._update_tree_action_buttons()
        elements = getattr(self.context, "elements", None)
        if elements is None or node is None:
            return
        elements.set_emphasis([node])
        self.canvas.refresh_selection_highlight()
        self._on_selection_changed(node)

    def _on_tree_item_double_clicked(self, item, column):
        # column 0: rename -- not via a console command, since neither
        # "operation" nor "element" have a bare rename-by-label console
        # verb; label is a plain, always-settable attribute on every
        # Node subclass. columns 1/2: LightBurn's directly-editable
        # per-layer Speed/Power columns -- this shell's tree already
        # DISPLAYED them (_refresh_operations_tree), just never let you
        # change them without opening a separate properties window.
        # item.data(0, ...) is read regardless of which column was
        # double-clicked -- that's the column the node reference was
        # stored on (see _refresh_operations_tree), not per-column data.
        node = item.data(0, Qt.ItemDataRole.UserRole)
        if node is None:
            return
        from PyQt6.QtWidgets import QInputDialog

        if column == 0:
            current_label = getattr(node, "label", None) or item.text(0).strip()
            new_label, ok = QInputDialog.getText(
                self, "Renommer", "Nouveau nom :", text=current_label
            )
            new_label = new_label.strip() if new_label else ""
            if not ok or not new_label or new_label == current_label:
                return
            node.label = new_label
            elements = getattr(self.context, "elements", None)
            if elements is not None:
                elements.signal("element_property_update", [node])
            self._refresh_operations_tree()
            self.status_bar.showMessage(f"Renommé : {new_label}", 2000)
        elif column == 1:
            # Speed is stored directly in mm/s.
            if not hasattr(node, "speed"):
                return
            current_speed = float(getattr(node, "speed", 0) or 0)
            new_speed, ok = QInputDialog.getDouble(
                self, "Vitesse", "Vitesse (mm/s) :", current_speed, 0.1, 5000, 1
            )
            if not ok:
                return
            node.speed = new_speed
            elements = getattr(self.context, "elements", None)
            if elements is not None:
                elements.signal("element_property_update", [node])
            self._refresh_operations_tree()
            self.status_bar.showMessage(f"Vitesse : {new_speed:.0f} mm/s", 2000)
        elif column == 2:
            # Power is stored as a per-mille value (0-1000 = 0-100%,
            # confirmed via op_engrave.py's own "percent" formatter:
            # f"{self.power / 10.0:.0f}%") -- shown/edited here as the
            # familiar 0-100% a user actually thinks in.
            if not hasattr(node, "power"):
                return
            current_power_pct = float(getattr(node, "power", 0) or 0) / 10.0
            new_power_pct, ok = QInputDialog.getDouble(
                self, "Puissance", "Puissance (%) :", current_power_pct, 0, 100, 1
            )
            if not ok:
                return
            node.power = new_power_pct * 10.0
            elements = getattr(self.context, "elements", None)
            if elements is not None:
                elements.signal("element_property_update", [node])
            self._refresh_operations_tree()
            self.status_bar.showMessage(f"Puissance : {new_power_pct:.0f}%", 2000)
        elif column == 3:
            # "passes" alone defaults to 0/unset; the engine only honors
            # it when passes_custom is True (see op_passes console command
            # in elements/branches.py, same convention followed here).
            if not hasattr(node, "passes"):
                return
            current_passes = int(getattr(node, "implicit_passes", 1) or 1)
            new_passes, ok = QInputDialog.getInt(
                self, "Passes", "Nombre de passes :", current_passes, 1, 999, 1
            )
            if not ok:
                return
            node.passes = new_passes
            node.passes_custom = new_passes >= 1
            elements = getattr(self.context, "elements", None)
            if elements is not None:
                elements.signal("element_property_update", [node])
            self._refresh_operations_tree()
            self.status_bar.showMessage(f"Passes : {new_passes}", 2000)

    def _update_tree_action_buttons(self):
        has_selection = self._tree_action_node is not None
        self.btn_tree_duplicate.setEnabled(has_selection)
        self.btn_tree_delete.setEnabled(has_selection)

    def _on_tree_duplicate_selected(self):
        # Only real elements can go through the existing "element copy"
        # duplicate path -- an operation node itself has no equivalent
        # single-node duplicate command wired up in this shell yet.
        node = self._tree_action_node
        elements = getattr(self.context, "elements", None)
        if elements is None or node is None:
            return
        if not hasattr(node, "as_geometry"):
            self.status_bar.showMessage(
                "Seuls les éléments peuvent être dupliqués depuis cet arbre.", 3000
            )
            return
        elements.set_emphasis([node])
        self._on_duplicate()

    def _on_tree_delete_selected(self):
        # node.remove_node() works uniformly for an operation, a group,
        # or an element -- unlike duplicate, deletion doesn't need a
        # type-specific console command.
        node = self._tree_action_node
        elements = getattr(self.context, "elements", None)
        if elements is None or node is None:
            return
        with elements.undoscope("Supprimer"):
            node.remove_node()
        elements.signal("refresh_scene", "Scene")
        self._tree_action_node = None
        self._refresh_operations_tree()
        self.canvas.render_elements()
        self._update_tree_action_buttons()
        self.status_bar.showMessage("Supprimé.", 2000)

    def _refresh_device_status(self):
        if self._has_active_device():
            device = self.context.device
            label = getattr(device, "label", None) or str(device)
            status_text = f"Connecté: {label}"
            status_color = "#30D158"
            # Same state checks the classic wx canvas uses to tint its
            # background while a job runs (madgrav/gui/wxmscene.py:
            # on_driver_mode) -- here reflected in the existing status
            # label instead, since that's already always visible.
            try:
                if device.driver.paused:
                    status_text = f"En pause : {label}"
                    status_color = "#FF9F0A"
                elif device.laser_status == "active":
                    status_text = f"En cours : {label}"
                    status_color = "#FF3B30"
            except AttributeError:
                pass
            self.device_status_lbl.setText(status_text)
            self.device_status_lbl.setStyleSheet(f"color: {status_color}; font-weight: bold;")
        else:
            device = None
            self.device_status_lbl.setText("Aucun appareil actif")
            self.device_status_lbl.setStyleSheet("color: #C02B2B; font-weight: bold;")

        kernel = getattr(self.context, "kernel", None)
        devices = list(kernel.services("device")) if kernel is not None else []
        self.device_combo.blockSignals(True)
        self.device_combo.clear()
        active_index = -1
        for i, svc in enumerate(devices):
            self.device_combo.addItem(getattr(svc, "label", str(svc)), svc)
            if svc is device:
                active_index = i
        if active_index >= 0:
            self.device_combo.setCurrentIndex(active_index)
        self.device_combo.blockSignals(False)

        # Grey out the laser-control toolbar buttons instead of leaving
        # them clickable-but-always-showing-a-warning-dialog when there's
        # no active device, matching how the Edit menu's selection-
        # dependent actions already behave.
        has_device = device is not None
        for btn in (self.btn_orig, self.btn_frame, self.btn_pause, self.btn_stop):
            btn.setEnabled(has_device)
        # "Démarrer" additionally needs the arm gate, not just a device --
        # same reasoning, kept separate from the loop above since arm/
        # disarm is specific to starting a job (matches wx's may_run(),
        # which only gates Start, not Home/Frame/Pause/Stop).
        self.btn_start.setEnabled(self._may_start())

    def _on_device_combo_activated(self, index):
        # "device activate <name>" (madgrav/device/basedevice.py) matches
        # by EXACT string equality against spool.label -- a quote-folding
        # workaround (as used for the canvas's Text tool and the device
        # wizard, where the string only needs to survive the console
        # parser) isn't enough here: folding a literal '"' to "'" avoids
        # a parse error but then searches for a label that doesn't
        # exist, so activation silently fails with nothing but a console
        # message the user never sees -- the combo shows the new
        # selection but the device never actually switches. The same
        # command also matches by plain integer INDEX into
        # kernel.services("device"), which _refresh_device_status()
        # populates this combo from in that exact order with no
        # filtering -- using the index sidesteps quote-escaping
        # entirely instead of trying to patch it further.
        if self._run_console(f"device activate {index}"):
            self._refresh_device_status()
            label = self.device_combo.itemText(index)
            self.status_bar.showMessage(f"Machine active : {label}", 3000)

    def _on_remove_device(self):
        index = self.device_combo.currentIndex()
        if index < 0:
            return
        service = self.device_combo.itemData(index)
        if service is None:
            return
        # Same restriction as the classic wx device panel's own remove
        # button (madgrav/gui/devicepanel.py) -- switch away first.
        if service is getattr(self.context, "device", None):
            QMessageBox.warning(
                self,
                "Supprimer la machine",
                "Impossible de supprimer la machine active. "
                "Activez-en une autre d'abord.",
            )
            return
        label = self.device_combo.itemText(index)
        answer = QMessageBox.question(
            self,
            "Supprimer la machine",
            f"Supprimer « {label} » ? Cette action est irréversible.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if answer != QMessageBox.StandardButton.Yes:
            return
        try:
            service.destroy()
        except AttributeError:
            pass
        self.context.signal("device;modified")
        self._refresh_device_status()
        self.status_bar.showMessage(f"Machine « {label} » supprimée.", 3000)
