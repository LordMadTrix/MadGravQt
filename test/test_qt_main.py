"""
Regression coverage for the PyQt6 shell's safety-critical checks and core
UX behaviour (madgrav/qt/qt_main.py). Skips cleanly if PyQt6 isn't
installed -- it's not a hard project dependency of every environment this
suite might run in, only of the --qt launch mode itself.
"""

import math
import os
import tempfile
import unittest
from unittest.mock import patch

try:
    from PyQt6.QtCore import QPoint, QPointF, QSettings, Qt, QTimer
    from PyQt6.QtGui import QAction, QColor, QWheelEvent
    from PyQt6.QtTest import QTest
    from PyQt6.QtWidgets import (
        QApplication,
        QCheckBox,
        QColorDialog,
        QDialog,
        QDoubleSpinBox,
        QFileDialog,
        QGraphicsView,
        QInputDialog,
        QMenu,
        QMessageBox,
        QPushButton,
        QSpinBox,
        QToolBar,
        QToolButton,
    )

    HAS_QT = True
except ImportError:
    HAS_QT = False

from test import bootstrap

if HAS_QT:
    from PyQt6 import sip

    from madgrav.device import basedevice
    from madgrav.extra import cag
    from madgrav.qt.plugin import _show_or_create_qt_window
    from madgrav.qt.qt_device_wizard import DeviceSetupWizard, _scan_serial_ports
    from madgrav.qt.qt_theme import build_app_icon, build_tool_icon
    from madgrav.qt.qt_main import ConsoleLineEdit, MadGravQtMainWindow


@unittest.skipUnless(HAS_QT, "PyQt6 not installed")
class TestQtMainWindow(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        # QSettings("MadGrav", "QtGUI") writes to the REAL platform store
        # (the Windows registry, HKEY_CURRENT_USER\Software\MadGrav\QtGUI)
        # -- the SAME key the real installed app uses. A test that shows/
        # hides docks and then closes the window (persisting window/state
        # in closeEvent()) would otherwise leak into the next test run
        # (confirmed: this broke test_arm_step_can_be_disabled_via_
        # preference in isolation after an unrelated dock-visibility test
        # ran first) and, worse, into the real user's actual saved layout.
        # Clear before AND after every test so _restore_window_state()
        # never reads stale state in, and no test leaves residue behind.
        self._clear_persisted_window_state()
        self.kernel = bootstrap.bootstrap(plugins=[basedevice.plugin, cag.plugin])
        self.root = self.kernel.root
        self.root("service device start dummy 0\n")
        self.win = MadGravQtMainWindow(self.root)
        self.win.show()
        self.app.processEvents()
        # Registering kernel listeners in the constructor above can replay
        # an already-queued/last-known signal (e.g. "refresh_scene" from
        # bootstrap's own "service device start dummy 0") once the Qt
        # event loop actually pumps it -- let that startup noise settle
        # before a test starts counting calls, or it gets attributed to
        # whatever the test itself triggers.
        if HAS_QT:
            QTest.qWait(100)
        # Real dialogs would block the test run waiting for a click --
        # every test below monkeypatches whichever QMessageBox entry
        # point it needs to invoke instead of relying on this default.
        self._orig_warning = QMessageBox.warning
        self._orig_information = QMessageBox.information
        self._orig_question = QMessageBox.question
        # Same reasoning for QMenu.exec() -- a real context menu would
        # otherwise block the test run waiting for a click too.
        self._orig_menu_exec = QMenu.exec

    def tearDown(self):
        QMessageBox.warning = self._orig_warning
        QMessageBox.information = self._orig_information
        QMessageBox.question = self._orig_question
        QMenu.exec = self._orig_menu_exec
        self.win._closing_from_kernel = True  # skip the unsaved-changes prompt
        self.win.close()  # closeEvent() persists window/state -- clear it again right after
        self._clear_persisted_window_state()
        self.kernel()  # full (non-partial) call shuts the kernel down

    @staticmethod
    def _clear_persisted_window_state():
        settings = QSettings("MadGrav", "QtGUI")
        settings.remove("window/state")
        settings.remove("window/geometry")
        settings.sync()

    def _add_grbl_device(self, label="TestGRBL"):
        self.root(f'device add -i grbl-generic -l "{label}"\n')
        self.kernel.process_queue()

    # -- Safety: arm/disarm gates Start ---------------------------------

    def test_start_button_disabled_without_arming(self):
        self._add_grbl_device()
        self.win._update_arm_button()
        self.assertFalse(self.win._laser_armed())
        self.assertFalse(self.win._may_start())

    def test_arming_enables_start(self):
        self._add_grbl_device()
        self.win._set_armed(True)
        self.assertTrue(self.win._laser_armed())
        self.assertTrue(self.win._may_start())

    def test_arm_state_does_not_persist_across_a_fresh_session(self):
        # A leading underscore on a setting key ("_laser_may_run") is a
        # deliberate kernel convention (madgrav/kernel/context.py:
        # Context.setting() only reads persistent storage for keys NOT
        # starting with "_") that keeps the arm state session-only --
        # confirmed here directly rather than trusted, since the OTHER
        # direction (arm state surviving a restart) would be a real
        # physical-safety regression: the laser could start ARMED
        # without the user re-confirming. Uses two fully separate
        # bootstrap() kernels against the SAME on-disk test profile,
        # the same mechanism already known (elsewhere in this session)
        # to carry other settings across separate kernel instances --
        # with an explicit flush() in between, to make sure this
        # specific check isn't just passing because nothing was ever
        # written to disk in the first place.
        kernel1 = bootstrap.bootstrap()
        try:
            root1 = kernel1.root
            root1("service device start dummy 0\n")
            win1 = MadGravQtMainWindow(root1)
            win1.show()
            self.app.processEvents()
            try:
                win1._set_armed(True)
                self.assertTrue(win1._laser_armed())
                root1.flush()  # explicitly commit current attrs to disk
            finally:
                win1._closing_from_kernel = True
                win1.close()
        finally:
            kernel1()

        kernel2 = bootstrap.bootstrap()
        try:
            root2 = kernel2.root
            root2("service device start dummy 0\n")
            win2 = MadGravQtMainWindow(root2)
            win2.show()
            self.app.processEvents()
            try:
                self.assertFalse(win2._laser_armed())
            finally:
                win2._closing_from_kernel = True
                win2.close()
        finally:
            kernel2()

    def test_arm_step_can_be_disabled_via_preference(self):
        # "laserpane_arm" (no leading underscore, unlike "_laser_may_run"
        # above -- this one is a genuine user preference meant to persist)
        # lets a user turn the whole arm-safety-step off. Confirms the
        # button correctly hides and Start becomes available without
        # arming when that preference is off, not just that arming still
        # works when it's on.
        self._add_grbl_device()
        self.assertTrue(self.win._needs_arming())
        self.assertTrue(self.win.btn_arm.isVisible())
        self.assertFalse(self.win._may_start())  # needs arming, not armed yet

        self.root.laserpane_arm = False
        self.win._update_arm_button()

        self.assertFalse(self.win._needs_arming())
        self.assertFalse(self.win.btn_arm.isVisible())
        self.assertTrue(self.win._may_start())  # no arming needed anymore

    def test_on_start_happy_path_dispatches_job_without_extra_dialogs(self):
        # _on_start() chains 6 sequential gates (active device, armed,
        # has burnable content, no unassigned elements, nothing outside
        # the bed, nothing too fast) before actually spooling a job --
        # each gate is tested individually elsewhere in this file, but
        # never the full chain together. A regression in how they're
        # sequenced (an early return short-circuiting wrong) wouldn't be
        # caught by testing each helper in isolation. Confirms a
        # thoroughly well-behaved job (inside the bed, fully assigned,
        # armed) sails through with NO confirmation dialogs at all,
        # actually reaches the spooler, and auto-disarms afterward.
        #
        # Deliberately stays on the default "dummy" device rather than
        # calling _add_grbl_device(): actually dispatching
        # "threaded plan...spool" against a real grbl-generic driver
        # spawns a background thread that attempts real driver I/O and
        # never settles in this harness -- it hung the whole test
        # process on first write. "dummy" is the established safe
        # choice used everywhere else this session for exactly this
        # reason. It has no max_vector_speed, so the ambitious-ops
        # check trivially passes here -- that check's positive branch
        # is already covered elsewhere with a real grbl-generic device
        # WITHOUT dispatching a job.
        elements = self.root.elements

        self.root("rect 10mm 10mm 5mm 5mm\n")
        self.kernel.process_queue()
        node = list(elements.elems())[-1]
        op = elements.op_branch.add(type="op engrave", label="TestOp", speed=35)
        op.output = True
        op.add_reference(node)
        self.kernel.process_queue()

        self.assertTrue(elements.have_burnable_elements())
        self.assertFalse(elements.have_unassigned_elements())
        self.assertFalse(self.win._has_objects_outside_bed())
        self.assertFalse(self.win._has_ambitious_operations())

        self.win._set_armed(True)

        called = []
        QMessageBox.warning = staticmethod(lambda *a, **k: called.append("warning"))
        QMessageBox.information = staticmethod(lambda *a, **k: called.append("information"))
        QMessageBox.question = staticmethod(lambda *a, **k: called.append("question"))

        self.win._on_start()
        self.kernel.process_queue()
        self.app.processEvents()

        self.assertEqual(called, [])
        self.assertIn("spooler", self.win.status_bar.currentMessage().lower())
        self.assertFalse(self.win._laser_armed())  # auto-disarmed after start

    def test_on_start_with_no_burnable_content_informs_and_stays_armed(self):
        # Nothing to burn (empty document) must stop at that gate with an
        # informational dialog -- NOT a warning (nothing risky is being
        # overridden) -- and never reach the dispatch/auto-disarm step,
        # so a device armed beforehand stays armed for the user's next
        # real attempt.
        self.win._set_armed(True)
        self.assertFalse(self.root.elements.have_burnable_elements())

        informed = []
        warned = []
        QMessageBox.information = staticmethod(lambda *a, **k: informed.append(1))
        QMessageBox.warning = staticmethod(lambda *a, **k: warned.append(1))

        self.win._on_start()
        self.app.processEvents()

        self.assertEqual(informed, [1])
        self.assertEqual(warned, [])
        self.assertTrue(self.win._laser_armed())

    def test_on_start_warns_without_active_device(self):
        # bootstrap() always activates a "dummy" device (which
        # _has_active_device() counts as active), same as the pause/stop
        # tests -- stubbed directly here rather than trying to reach an
        # unreachable-in-this-harness kernel state.
        self.win._set_armed(True)
        original = self.win._has_active_device
        self.win._has_active_device = lambda: False
        warned = []
        QMessageBox.warning = staticmethod(lambda *a, **k: warned.append(1))
        try:
            self.win._on_start()
            self.assertEqual(warned, [1])
        finally:
            self.win._has_active_device = original

    def test_on_start_unassigned_elements_no_aborts_yes_continues(self):
        # A document with one properly-assigned burnable element AND one
        # genuinely unassigned one (elem_branch.add() directly, bypassing
        # the "rect" command's own auto-classify) exercises the
        # "some shapes aren't assigned, continue anyway?" gate -- No
        # must abort before dispatch (stays armed), Yes must proceed
        # through to the spooler (auto-disarms). Stays on "dummy" for
        # the actual dispatch, same reasoning as the happy-path test.
        elements = self.root.elements
        self.win._set_armed(True)

        self.root("rect 0mm 0mm 5mm 5mm\n")
        self.kernel.process_queue()
        assigned_node = list(elements.elems())[-1]
        op = elements.op_branch.add(type="op engrave", label="TestOp", speed=35)
        op.output = True
        op.add_reference(assigned_node)

        elements.elem_branch.add(
            type="elem rect",
            x="20mm",
            y="20mm",
            width="5mm",
            height="5mm",
            stroke=elements.default_stroke,
        )
        self.kernel.process_queue()

        self.assertTrue(elements.have_burnable_elements())
        self.assertTrue(elements.have_unassigned_elements())

        QMessageBox.question = staticmethod(
            lambda *a, **k: QMessageBox.StandardButton.No
        )
        self.win._on_start()
        self.app.processEvents()
        self.assertTrue(self.win._laser_armed())  # aborted, still armed

        QMessageBox.question = staticmethod(
            lambda *a, **k: QMessageBox.StandardButton.Yes
        )
        self.win._on_start()
        self.kernel.process_queue()
        self.app.processEvents()
        self.assertFalse(self.win._laser_armed())  # dispatched, auto-disarmed

    # -- Safety: CRITICAL pre-flight checks ------------------------------

    def test_ambitious_operations_detected_above_device_max_speed(self):
        self._add_grbl_device()
        elements = self.root.elements
        device = self.root.device
        max_vs = getattr(device, "max_vector_speed", None)
        self.assertIsNotNone(max_vs, "grbl-generic should define max_vector_speed")

        op = elements.op_branch.add(type="op engrave", label="TestOp")
        op.output = True
        rect = elements.elem_branch.add(
            type="elem rect", x=0, y=0, width="5mm", height="5mm"
        )
        op.add_reference(rect)

        op.speed = max_vs - 1
        self.assertFalse(self.win._has_ambitious_operations())

        op.speed = max_vs + 10
        self.assertTrue(self.win._has_ambitious_operations())

        op.output = False
        self.assertFalse(self.win._has_ambitious_operations())

    def test_no_ambitious_operations_on_empty_document(self):
        self._add_grbl_device()
        self.assertFalse(self.win._has_ambitious_operations())

    # -- Non-blocking warnings indicator ---------------------------------

    def test_warnings_indicator_flags_unassigned_element(self):
        elements = self.root.elements
        self.assertFalse(self.win.btn_warnings.isVisible())

        elements.elem_branch.add(
            type="elem rect", x=0, y=0, width="5mm", height="5mm"
        )
        self.win._on_document_changed()
        self.app.processEvents()

        self.assertTrue(self.win.btn_warnings.isVisible())
        self.assertTrue(any("assign" in c for c in self.win._concerns))

    def test_warnings_indicator_flags_hidden_element(self):
        elements = self.root.elements
        rect = elements.elem_branch.add(
            type="elem rect", x=0, y=0, width="5mm", height="5mm"
        )
        op = elements.op_branch.add(type="op engrave", label="TestOp")
        op.output = True
        op.add_reference(rect)
        self.win._on_document_changed()
        self.app.processEvents()
        self.assertFalse(self.win.btn_warnings.isVisible())

        rect.hidden = True
        self.win._on_document_changed()
        self.app.processEvents()
        self.assertTrue(self.win.btn_warnings.isVisible())
        self.assertTrue(any("masqué" in c for c in self.win._concerns))

    def test_show_warnings_dialog_only_opens_when_concerns_exist(self):
        opened = []
        QMessageBox.information = staticmethod(
            lambda *a, **k: opened.append(a[2] if len(a) > 2 else k.get("text"))
        )

        self.win._concerns = []
        self.win._show_warnings_dialog()
        self.assertEqual(opened, [])

        self.win._concerns = ["Concern A", "Concern B"]
        self.win._show_warnings_dialog()
        self.assertEqual(len(opened), 1)
        self.assertIn("Concern A", opened[0])
        self.assertIn("Concern B", opened[0])

        # A falsy self._concerns (e.g. never computed yet) falls back to a
        # fresh _compute_concerns() call rather than opening on stale data.
        opened.clear()
        self.win._concerns = None
        self.win._show_warnings_dialog()
        self.assertEqual(opened, [])

    # -- About / Job Spooler window-availability fallback -------------------

    def test_about_shows_fallback_dialog_when_wx_window_unavailable(self):
        # This test's bootstrap() never loads the wx GUI plugin (headless,
        # no wxPython dependency for this suite), so "window/About" is
        # never registered here -- the same state a real end user hits if
        # wxPython simply isn't installed. _run_console()'s only failure
        # signal is a raised exception, and the kernel doesn't raise for
        # an unrecognized command (it reports on the console channel and
        # returns normally) -- so _on_about() checks the window registry
        # directly first rather than trusting _run_console()'s return
        # value, which used to silently swallow this exact fallback.
        self.assertEqual(list(self.root.match("window/About")), [])
        shown = []
        QMessageBox.information = staticmethod(
            lambda *a, **k: shown.append(a[2] if len(a) > 2 else k.get("text"))
        )

        self.win._on_about()

        self.assertEqual(len(shown), 1)
        self.assertIn("MadGrav", shown[0])
        self.assertIn("MeerK40t", shown[0])

    def test_about_uses_console_path_when_window_is_registered(self):
        self.root.register("window/About", object())
        try:
            shown = []
            QMessageBox.information = staticmethod(lambda *a, **k: shown.append(1))

            self.win._on_about()

            self.assertEqual(shown, [])
            self.assertIn("window open About", self.win.console_output.toPlainText())
        finally:
            self.root.unregister("window/About")

    def test_open_spooler_shows_status_message_when_wx_window_unavailable(self):
        self.assertEqual(list(self.root.match("window/JobSpooler")), [])
        self.win.status_bar.showMessage("")

        self.win._on_open_spooler()

        self.assertNotEqual(self.win.status_bar.currentMessage(), "")
        self.assertNotIn(
            "window open JobSpooler", self.win.console_output.toPlainText()
        )

    # -- "Aligner, Booléens & Modifier" grid (dock_tools) -- this used to
    # be a standalone QToolBar ("Édition & Alignement Vectoriel"). That
    # went through two failed fix attempts before landing here: (1) its
    # 20 QToolButtons were added via addWidget(), which Qt's native "..."
    # overflow popup can't display (a widget can only be shown in one
    # place at a time) -- entries past the visible cut rendered blank
    # ("les 3 points ... rien a faire"); (2) converting to real QAction
    # fixed the popup, but the toolbar still needed an overflow at all
    # whenever it landed in a horizontal area, and a stale saved
    # QSettings position kept restoring it to the top regardless of
    # setAllowedAreas or an explicit post-restore re-pin ("je veux pas la
    # barre ... en haut"). The actual fix: it was never a toolbar's job
    # to hold 20 labeled buttons -- every other such group in this app
    # (Générateurs/Traitements/Vision above) already lives as a wrapping
    # QGridLayout inside the one scrollable dock_tools panel, which can
    # never overflow. Moved here to match. -------------------------------

    def test_align_grid_buttons_exist_in_dock_tools_not_a_separate_toolbar(self):
        self.assertEqual(
            [tb.windowTitle() for tb in self.win.findChildren(QToolBar)
             if tb.windowTitle() == "Édition & Alignement Vectoriel"],
            [],
        )
        expected_labels = {
            "Gauche", "Centre H", "Droite", "Haut", "Centre V", "Bas",
            "Centrer Table", "Unir", "Soustraire", "Intersecter", "Exclure",
            "Miroir H", "Miroir V", "Pivot 90°", "Répartir H", "Répartir V",
            "Égaliser L", "Égaliser H", "Contour", "Hachurage",
        }
        button_labels = {
            btn.text() for btn in self.win.dock_tools.findChildren(QToolButton)
        }
        self.assertTrue(expected_labels.issubset(button_labels))

    def test_align_grid_button_reaches_its_real_handler(self):
        # "Unir" is wired via lambda: self._execute_cag("union") (a
        # fresh self-lookup on every call) rather than a directly-bound
        # method reference like most buttons in this grid -- only the
        # lambda-wrapped style is interceptable by monkeypatching an
        # instance attribute after construction, so it's the one this
        # test can actually observe (same reasoning already established
        # for the CAG entries when this lived in the toolbar).
        union_btn = next(
            btn for btn in self.win.dock_tools.findChildren(QToolButton)
            if btn.text() == "Unir"
        )
        calls = []
        original = self.win._execute_cag
        try:
            self.win._execute_cag = lambda op: calls.append(op)
            QTest.mouseClick(union_btn, Qt.MouseButton.LeftButton)
            self.assertEqual(calls, ["union"])
        finally:
            self.win._execute_cag = original

    # -- Fenêtre menu -- every entry used to call "window open X" which is
    # only ever registered by the wx GUI plugin (never loaded in this
    # Qt-only build, see madgrav/gui/plugin.py's has_feature("wx") gate),
    # so every click silently did nothing (user report: "dans le menu
    # fenetre il y a rien qui marche"). _open_window_or_fallback() now
    # routes to a real Qt handler where one exists, or an honest message
    # otherwise, only using the console path if "window/X" is ever really
    # registered (e.g. a future build with wx available). -------------------

    def test_window_menu_routes_to_qt_handler_when_no_wx_window_registered(self):
        self.assertEqual(list(self.root.match("window/Rotary")), [])
        opened = []
        with patch.object(
            QDialog, "exec", lambda self_dlg: opened.append(type(self_dlg).__name__)
        ):
            self.win._open_window_or_fallback(
                "Rotary", self.win._on_rotary_assistant_dialog, "Axe Rotatif..."
            )

        self.assertEqual(opened, ["RotaryAssistantDialog"])
        self.assertNotIn("window open Rotary", self.win.console_output.toPlainText())

    def test_window_menu_simulation_opens_real_gcode_preview_dialog(self):
        opened = []
        with patch.object(
            QDialog, "exec", lambda self_dlg: opened.append(type(self_dlg).__name__)
        ):
            self.win._open_window_or_fallback(
                "Simulation", self.win._on_gcode_simulation_dialog, "Simulation..."
            )

        self.assertEqual(opened, ["GCodePreviewDialog"])

    def test_window_menu_properties_switches_ops_dock_to_transform_tab(self):
        self.win.dock_ops.setVisible(False)
        self.win.ops_tab_widget.setCurrentIndex(0)

        self.win._open_window_or_fallback(
            "Properties",
            lambda: self.win._show_ops_dock_tab(2),
            "Propriétés de l'Élément...",
        )

        self.assertTrue(self.win.dock_ops.isVisible())
        self.assertEqual(self.win.ops_tab_widget.currentIndex(), 2)

    def test_window_menu_shows_honest_fallback_when_no_qt_handler_exists(self):
        # Preferences/Notes/Keymap/Wordlist have no Qt-native replacement
        # yet -- must say so plainly rather than doing nothing.
        self.assertEqual(list(self.root.match("window/Preferences")), [])
        shown = []
        QMessageBox.information = staticmethod(
            lambda *a, **k: shown.append(a[2] if len(a) > 2 else k.get("text"))
        )

        self.win._open_window_or_fallback("Preferences", None, "Préférences...")

        self.assertEqual(len(shown), 1)
        self.assertIn("pas encore disponible", shown[0])

    def test_window_menu_uses_console_path_when_wx_window_is_registered(self):
        self.root.register("window/Preferences", object())
        try:
            shown = []
            QMessageBox.information = staticmethod(lambda *a, **k: shown.append(1))

            self.win._open_window_or_fallback("Preferences", None, "Préférences...")

            self.assertEqual(shown, [])
            self.assertIn(
                "window open Preferences", self.win.console_output.toPlainText()
            )
        finally:
            self.root.unregister("window/Preferences")

    # -- Job-progress time formatting ---------------------------------------

    def test_format_hms_formats_seconds_as_h_mm_ss(self):
        fmt = self.win._format_hms
        self.assertEqual(fmt(0), "0:00:00")
        self.assertEqual(fmt(59), "0:00:59")
        self.assertEqual(fmt(60), "0:01:00")
        self.assertEqual(fmt(3661), "1:01:01")
        # Fractional seconds are truncated, not rounded.
        self.assertEqual(fmt(7384.9), "2:03:04")

    def test_format_hms_clamps_negative_and_handles_infinity(self):
        fmt = self.win._format_hms
        # A negative "remaining" (e.g. from a slightly-off estimate) must
        # never render as a negative countdown.
        self.assertEqual(fmt(-5), "0:00:00")
        self.assertEqual(fmt(float("inf")), "∞")

    # -- Undo/Redo dynamic labels ------------------------------------------

    def test_undo_label_reflects_pending_action(self):
        elements = self.root.elements
        self.root("circle 3cm 3cm 1cm\n")
        self.kernel.process_queue()
        elements.undo.mark("Créer cercle")
        self.root.signal("undoredo")
        self.kernel.process_queue()
        self.app.processEvents()

        self.assertEqual(self.win.act_undo.text(), "Annuler Créer cercle")
        self.assertTrue(self.win.act_undo.isEnabled())

    def test_undo_redo_and_paste_actions_reach_their_handlers_via_real_trigger(self):
        # Every other test in this file exercises act_undo/act_redo/
        # act_paste by calling _on_undo()/_on_redo()/_on_paste()
        # directly, never through the QAction's own .triggered signal
        # (act_undo.triggered.connect(self._on_undo) etc. in _setup_ui)
        # -- a wrong .connect() target would still pass every one of
        # those while leaving the real Edit-menu item/Ctrl+Z shortcut
        # inert. Paste's effect is asserted concretely (a real pasted
        # element); undo/redo are confirmed via the console echo of the
        # commands they dispatch, since driving elements.undo.mark() from
        # a bare console command (rather than through the GUI's own
        # normal interactive flow) doesn't reliably reproduce a clean
        # single-step undo/redo round trip worth asserting element counts
        # against -- core undo/redo behavior itself already has its own
        # dedicated test files (test/test_undo_*.py); this only needs to
        # confirm the QAction reaches the handler.
        elements = self.root.elements
        self.root("rect 0mm 0mm 5mm 5mm\n")
        self.kernel.process_queue()
        node = list(elements.elems())[-1]
        elements.set_emphasis([node])
        self.kernel.process_queue()
        self.win._on_copy()
        self.win._update_paste_action()
        self.assertTrue(self.win.act_paste.isEnabled())

        count_before = len(list(elements.elems()))
        self.win.act_paste.trigger()
        self.kernel.process_queue()
        self.app.processEvents()
        self.assertEqual(len(list(elements.elems())), count_before + 1)

        self.win.act_undo.setEnabled(True)
        self.win.act_undo.trigger()
        self.assertIn("undo", self.win.console_output.toPlainText())

        self.win.act_redo.setEnabled(True)
        self.win.act_redo.trigger()
        self.assertIn("redo", self.win.console_output.toPlainText())

    def test_frame_selection_is_undoable(self):
        # "frame" (shapes.py) never calls elements.undoscope()/undo.mark()
        # itself -- confirmed empirically (before this fix) that the
        # created rect survived a Ctrl+Z. _on_frame_selection now wraps
        # its console dispatch in elements.undoscope() itself.
        elements = self.root.elements
        self.root("rect 0mm 0mm 10mm 10mm\n")
        self.kernel.process_queue()
        elements.undo.mark("baseline")
        r = list(elements.elems())[-1]
        elements.set_emphasis([r])
        self.kernel.process_queue()

        count_before = len(list(elements.elems()))
        QInputDialog.getDouble = staticmethod(lambda *a, **k: (0.0, True))
        self.win._on_frame_selection()
        self.kernel.process_queue()
        self.assertGreater(len(list(elements.elems())), count_before)

        self.win._on_undo()
        self.kernel.process_queue()
        self.assertEqual(len(list(elements.elems())), count_before, "undo must remove the frame rect it just created")

    def test_box_generator_is_undoable(self):
        # Same undoscope gap as frame, here in a PRE-EXISTING generator
        # (not added this session) -- confirms the fix wasn't just for
        # this session's own additions but the whole class of
        # madgrav/tools/*.py generators, none of which call
        # elements.undoscope()/undo.mark() on their own.
        elements = self.root.elements
        count_before = len(list(elements.elems()))

        def fake_exec(dlg_self):
            return QDialog.DialogCode.Accepted

        QMessageBox.information = lambda *a, **kw: None
        with patch.object(QDialog, "exec", fake_exec):
            self.win._on_box_generator_dialog()
        self.kernel.process_queue()
        self.assertGreater(len(list(elements.elems())), count_before)

        self.win._on_undo()
        self.kernel.process_queue()
        self.assertEqual(len(list(elements.elems())), count_before, "undo must remove the generated box panels")

    # -- Operations-tree refresh debounce (perf) ----------------------------

    def test_ops_tree_refresh_is_debounced_not_synchronous(self):
        # Counts the debounce TIMER's own timeout firings specifically --
        # added as an extra connection alongside the real
        # _refresh_operations_tree slot, not a replacement for it.
        # Monkeypatching _refresh_operations_tree itself (as an earlier
        # version of this test did) conflates two independent trigger
        # paths: the debounce timer under test here, AND
        # _on_document_changed()'s own direct call on "refresh_scene" --
        # a delayed/replayed kernel signal landing during this test's own
        # QTest.qWait() would then get misattributed to the timer,
        # intermittently inflating the count under heavier system load
        # (observed as a rare flake when running the full suite, though
        # not in isolation).
        timer_fired = []
        self.win._ops_tree_refresh_timer.timeout.connect(lambda: timer_fired.append(1))

        self.win._on_tree_refresh_needed()
        self.assertEqual(timer_fired, [])  # no synchronous rebuild

        QTest.qWait(150)
        self.assertEqual(len(timer_fired), 1)  # deferred rebuild still happens

    # -- Job progress indicator ------------------------------------------

    def test_job_progress_indicator_lifecycle(self):
        import time as _time

        from madgrav.core.laserjob import LaserJob

        self.assertFalse(self.win.job_label.isVisible())
        self.assertFalse(self.win.job_progress.isVisible())
        self.assertFalse(self.win._job_timer.isActive())

        device = self.root.device
        spooler = device.spooler
        job = LaserJob("TestJob", list(range(10)), loops=1)
        job._stopped = False
        job.time_started = _time.time() - 5.0
        job.item_index = 4
        job._estimate = 10.0
        spooler.queue.append(job)
        self.root.signal("spooler;queue", len(spooler.queue))
        self.kernel.process_queue()
        self.app.processEvents()

        self.assertTrue(self.win.job_label.isVisible())
        self.assertTrue(self.win.job_progress.isVisible())
        self.assertTrue(self.win._job_timer.isActive())
        self.assertEqual(self.win.job_progress.value(), 40)

        spooler.queue.remove(job)
        self.root.signal("spooler;completed")
        self.kernel.process_queue()
        self.app.processEvents()

        self.assertFalse(self.win.job_label.isVisible())
        self.assertFalse(self.win.job_progress.isVisible())
        self.assertFalse(self.win._job_timer.isActive())

    # -- Undo/Redo enable state -------------------------------------------

    def test_undo_redo_disabled_with_no_history_on_this_action(self):
        # Whatever the persisted profile's undo stack looks like, marking
        # a fresh state must make Undo enabled and Redo's own text/state
        # stay internally consistent with elements.undo's own report.
        elements = self.root.elements
        self.root("rect 0 0 1cm 1cm\n")
        self.kernel.process_queue()
        elements.undo.mark("Créer rectangle")
        self.root.signal("undoredo")
        self.kernel.process_queue()
        self.app.processEvents()

        self.assertTrue(self.win.act_undo.isEnabled())
        self.assertEqual(self.win.act_undo.isEnabled(), bool(elements.undo.has_undo()))
        self.assertEqual(self.win.act_redo.isEnabled(), bool(elements.undo.has_redo()))

    # -- Selection-dependent action gating (thresholds, not just align/geo) -

    def test_selection_dependent_action_thresholds(self):
        # _single_selection_actions (Delete, Duplicate, Copy, Cut, Rotate,
        # Mirror, Lock/Unlock, Ungroup...) need >=1 selected;
        # _multi_selection_actions (Group, Align, Geometry ops) need >=2.
        # The align/geometry-specific test below only covers the >=2
        # gate; this confirms ALL actions in both lists follow the right
        # threshold at 0/1/2 selected, not just one representative pair.
        elements = self.root.elements
        self.win._update_selection_dependent_actions()
        self.assertTrue(all(not a.isEnabled() for a in self.win._single_selection_actions))
        self.assertTrue(all(not a.isEnabled() for a in self.win._multi_selection_actions))

        self.root("rect 0mm 0mm 5mm 5mm\n")
        self.kernel.process_queue()
        node1 = list(elements.elems())[-1]
        elements.set_emphasis([node1])
        self.kernel.process_queue()
        self.win._update_selection_dependent_actions()
        self.assertTrue(all(a.isEnabled() for a in self.win._single_selection_actions))
        self.assertTrue(all(not a.isEnabled() for a in self.win._multi_selection_actions))

        self.root("rect 10mm 0mm 5mm 5mm\n")
        self.kernel.process_queue()
        node2 = list(elements.elems())[-1]
        elements.set_emphasis([node1, node2])
        self.kernel.process_queue()
        self.win._update_selection_dependent_actions()
        self.assertTrue(all(a.isEnabled() for a in self.win._single_selection_actions))
        self.assertTrue(all(a.isEnabled() for a in self.win._multi_selection_actions))

    # -- Align / Geometry actions ------------------------------------------

    def test_align_and_geometry_actions_require_two_elements(self):
        elements = self.root.elements
        self.root("rect 0mm 0mm 5mm 5mm\n")
        self.kernel.process_queue()
        rect1 = list(elements.elems())[-1]

        elements.set_emphasis([rect1])
        self.kernel.process_queue()
        self.win._update_selection_dependent_actions()
        self.assertFalse(self.win._align_actions[0].isEnabled())
        self.assertFalse(self.win._geometry_actions[0].isEnabled())

        self.root("rect 20mm 10mm 5mm 5mm\n")
        self.kernel.process_queue()
        rect2 = list(elements.elems())[-1]
        elements.set_emphasis([rect1, rect2])
        self.kernel.process_queue()
        self.win._update_selection_dependent_actions()
        self.assertTrue(self.win._align_actions[0].isEnabled())
        self.assertTrue(self.win._geometry_actions[0].isEnabled())

    def test_align_and_geometry_menu_actions_pass_the_correct_distinct_argument(self):
        # Each of these 6 align / 4 geometry QActions is built in a loop
        # with act.triggered.connect(lambda checked=False, d=direction:
        # self._on_align(d)) -- the "d=direction" default-argument
        # capture is what avoids Python's classic late-binding closure
        # trap (without it, every action in the loop would close over
        # the SAME final loop variable and all six menu items would
        # trigger the same direction). Confirmed here by triggering each
        # real QAction and recording which argument actually arrived,
        # rather than trusting the source reads correctly.
        original_align = self.win._on_align
        original_geometry_op = self.win._on_geometry_op
        try:
            align_calls = []
            self.win._on_align = lambda d: align_calls.append(d)
            for act in self.win._align_actions:
                act.setEnabled(True)
                act.trigger()
            self.assertEqual(
                align_calls,
                ["left", "right", "top", "bottom", "centerh", "centerv"],
            )

            geometry_calls = []
            self.win._on_geometry_op = lambda o: geometry_calls.append(o)
            for act in self.win._geometry_actions:
                act.setEnabled(True)
                act.trigger()
            self.assertEqual(
                geometry_calls, ["union", "difference", "intersection", "xor"]
            )
        finally:
            self.win._on_align = original_align
            self.win._on_geometry_op = original_geometry_op

    def test_window_menu_actions_pass_the_correct_distinct_name(self):
        # Same closure-capture pattern as align/geometry/recent-files
        # above -- the "Fenêtre" menu's window_entries loop connects each
        # QAction with a lambda closing over (window_name, qt_handler,
        # label) that calls self._open_window_or_fallback(n, h, lbl) --
        # updated from the old self._open_window(n)-only call when that
        # method grew a real-Qt-handler/fallback-message path (see
        # _open_window_or_fallback). window_menu itself is a local
        # variable in _setup_ui, found here via the real menu bar rather
        # than exposed as a self.* attribute.
        window_menu = next(
            m
            for m in self.win.menuBar().findChildren(QMenu)
            if m.title().replace("&", "") == "Fenêtre"
        )
        actions = [a for a in window_menu.actions() if not a.isSeparator()]
        self.assertGreater(len(actions), 5)

        original = self.win._open_window_or_fallback
        try:
            calls = []
            self.win._open_window_or_fallback = lambda n, h, lbl: calls.append(n)
            for act in actions:
                act.trigger()
            self.assertEqual(len(calls), len(actions))
            self.assertEqual(len(set(calls)), len(calls))  # every one distinct
        finally:
            self.win._open_window_or_fallback = original

    def test_edit_menu_actions_reach_their_handlers_via_real_trigger(self):
        # act_delete/act_rotate_cw/act_rotate_ccw/act_mirror_h/
        # act_mirror_v/act_lock/act_unlock are local variables in
        # _setup_ui (not self.* attributes), each wired with a single
        # standalone lambda (e.g. "lambda: self._on_rotate(90)") -- no
        # closure-loop risk like the menus above, but still never
        # triggered for real anywhere in this file. Reached here via
        # their known _single_selection_actions index (documented at
        # that list's own definition: delete, duplicate, copy, cut,
        # rotate_cw, rotate_ccw, mirror_h, mirror_v, lock, unlock,
        # ungroup, in that order).
        elements = self.root.elements
        actions = self.win._single_selection_actions
        act_rotate_cw, act_mirror_h = actions[4], actions[6]
        act_lock, act_unlock, act_delete = actions[8], actions[9], actions[0]

        self.root("rect 10mm 10mm 5mm 5mm\n")
        self.kernel.process_queue()
        node = list(elements.elems())[-1]
        elements.set_emphasis([node])
        self.kernel.process_queue()
        self.win._update_selection_dependent_actions()
        for act in actions:
            act.setEnabled(True)

        m = node.matrix
        before = (m.a, m.b, m.c, m.d)
        act_rotate_cw.trigger()
        self.kernel.process_queue()
        m2 = node.matrix
        after = (m2.a, m2.b, m2.c, m2.d)
        self.assertNotEqual(before, after)

        det_before = m2.a * m2.d - m2.b * m2.c
        act_mirror_h.trigger()
        self.kernel.process_queue()
        m3 = node.matrix
        det_after = m3.a * m3.d - m3.b * m3.c
        self.assertNotEqual(det_before > 0, det_after > 0)  # mirrored

        self.assertFalse(node.lock)
        act_lock.trigger()
        self.assertTrue(node.lock)
        act_unlock.trigger()
        self.assertFalse(node.lock)

        count_before = len(list(elements.elems()))
        act_delete.trigger()
        self.kernel.process_queue()
        self.assertEqual(len(list(elements.elems())), count_before - 1)

    def test_file_view_help_menu_actions_reach_their_handlers_via_real_trigger(self):
        # act_new/act_classify/act_zoom_fit/act_shortcuts/act_about are
        # also local variables in _setup_ui (like the Edit-menu ones
        # above), each with its own standalone .triggered.connect(...) --
        # found here via the real menu structure (findChildren(QAction)
        # by exact label) rather than exposed as self.* attributes.
        def find_action(text):
            return next(a for a in self.win.findChildren(QAction) if a.text() == text)

        elements = self.root.elements
        self.root("rect 0mm 0mm 5mm 5mm\n")
        self.kernel.process_queue()
        self.app.processEvents()

        find_action("Classifier Tout (Assigner aux Opérations)").trigger()
        self.kernel.process_queue()
        self.app.processEvents()
        self.assertNotEqual(self.win.status_bar.currentMessage(), "")

        self.win.zoom_label.setText("999%")
        find_action("Ajuster à la Sélection").trigger()
        self.app.processEvents()
        self.assertNotEqual(self.win.zoom_label.text(), "999%")

        shown = []
        QMessageBox.information = staticmethod(lambda *a, **k: shown.append(1))
        find_action("Raccourcis clavier...").trigger()
        self.app.processEvents()
        self.assertEqual(shown, [1])

        shown.clear()
        find_action("À Propos de MadGrav...").trigger()
        self.app.processEvents()
        self.assertEqual(shown, [1])

        asked = []
        QMessageBox.question = staticmethod(
            lambda *a, **k: (asked.append(1), QMessageBox.StandardButton.Yes)[1]
        )
        count_before = len(list(elements.elems()))
        find_action("Nouveau Projet").trigger()
        self.app.processEvents()
        self.assertEqual(asked, [1])
        self.assertLess(len(list(elements.elems())), count_before)

    def test_zoom_theme_and_group_actions_reach_their_handlers_via_real_trigger(self):
        # act_zoom_in/act_zoom_out are local variables found by label
        # like the ones above; act_light_theme is a self.* attribute
        # (used directly elsewhere in this file); act_group is index 0
        # of _multi_selection_actions. None had been triggered for real.
        canvas = self.win.canvas

        def find_action(text):
            return next(a for a in self.win.findChildren(QAction) if a.text() == text)

        scale_before = canvas.transform().m11()
        find_action("Zoom Avant").trigger()
        self.app.processEvents()
        scale_after_in = canvas.transform().m11()
        self.assertGreater(scale_after_in, scale_before)

        find_action("Zoom Arrière").trigger()
        self.app.processEvents()
        self.assertLess(canvas.transform().m11(), scale_after_in)

        # A checkable QAction's trigger() flips its own checked state
        # before emitting (same as a real click) -- don't pre-flip it.
        was_dark = self.win._dark_theme
        self.win.act_light_theme.trigger()
        self.app.processEvents()
        self.assertNotEqual(self.win._dark_theme, was_dark)

        elements = self.root.elements
        self.root("rect 0mm 0mm 5mm 5mm\n")
        self.root("rect 10mm 0mm 5mm 5mm\n")
        self.kernel.process_queue()
        r1, r2 = list(elements.elems())[-2:]
        elements.set_emphasis([r1, r2])
        self.kernel.process_queue()
        self.win._update_selection_dependent_actions()

        act_group = self.win._multi_selection_actions[0]
        act_group.setEnabled(True)
        group_count_before = sum(
            1 for n in elements.elem_branch.children if n.type == "group"
        )
        act_group.trigger()
        self.kernel.process_queue()
        self.app.processEvents()
        group_count_after = sum(
            1 for n in elements.elem_branch.children if n.type == "group"
        )
        self.assertEqual(group_count_after, group_count_before + 1)

    def test_grid_array_copy_creates_expected_number_of_copies(self):
        # LightBurn's "Array Copy" -- backend already existed ("grid"
        # console command, madgrav/core/elements/grid.py) but had no Qt
        # UI path at all until now. QDialog.exec() is patched with
        # unittest.mock.patch.object(), NOT plain "orig = X.exec; X.exec
        # = new; ...; X.exec = orig" -- confirmed by reproduction that a
        # manual reassign-then-restore leaves QDialog.exec in a broken
        # state (a later real wizard.exec() call raises "first argument
        # of unbound method must have type 'QDialog'") even though the
        # attribute LOOKS restored; QDialog.exec is a SIP-wrapped C++
        # method, not a plain Python function, and doesn't survive a
        # naive round-trip through a plain attribute assignment the way
        # QMessageBox's static methods do elsewhere in this file.
        # mock.patch.object() handles this correctly. QDialog is a
        # widely-shared base class here (the device wizard's QWizard is
        # itself a QDialog subclass), so this isn't a hypothetical risk.
        elements = self.root.elements
        self.root("rect 0mm 0mm 10mm 10mm\n")
        self.kernel.process_queue()
        node = list(elements.elems())[-1]
        elements.set_emphasis([node])
        self.kernel.process_queue()

        def fake_exec(dlg_self):
            spins_int = dlg_self.findChildren(QSpinBox)
            spins_dbl = dlg_self.findChildren(QDoubleSpinBox)
            spins_int[0].setValue(3)  # columns
            spins_int[1].setValue(2)  # rows
            spins_dbl[0].setValue(5)  # x mm
            spins_dbl[1].setValue(0)  # y mm
            return QDialog.DialogCode.Accepted

        with patch.object(QDialog, "exec", fake_exec):
            count_before = len(list(elements.elems()))
            self.win._on_grid_array_copy()
            self.kernel.process_queue()

            # 3x2 grid = 6 total positions, 1 of which is the original
            # (left in place, not duplicated) -- 5 new copies.
            self.assertEqual(len(list(elements.elems())), count_before + 5)

        with patch.object(
            QDialog, "exec", lambda dlg_self: QDialog.DialogCode.Rejected
        ):
            count_before2 = len(list(elements.elems()))
            self.win._on_grid_array_copy()
            self.assertEqual(len(list(elements.elems())), count_before2)

        # No selection -- a safe no-op, must not even open the dialog.
        elements.set_emphasis(None)
        self.kernel.process_queue()
        opened = []
        with patch.object(QDialog, "exec", lambda dlg_self: opened.append(1)):
            self.win._on_grid_array_copy()
            self.assertEqual(opened, [])

    def test_radial_array_copy_creates_expected_number_of_copies(self):
        # LightBurn's other Array Copy mode (circular/radial) -- same
        # "no_selection_still_a_no_op" and mock.patch.object() reasoning
        # as the grid-copy test above.
        elements = self.root.elements
        self.root("rect 0mm 0mm 5mm 5mm\n")
        self.kernel.process_queue()
        node = list(elements.elems())[-1]
        elements.set_emphasis([node])
        self.kernel.process_queue()

        def fake_exec(dlg_self):
            spins_int = dlg_self.findChildren(QSpinBox)
            spins_dbl = dlg_self.findChildren(QDoubleSpinBox)
            spins_int[0].setValue(6)  # repeats
            spins_dbl[0].setValue(30)  # radius mm
            spins_dbl[1].setValue(0)  # start angle
            spins_dbl[2].setValue(360)  # end angle
            return QDialog.DialogCode.Accepted

        with patch.object(QDialog, "exec", fake_exec):
            count_before = len(list(elements.elems()))
            self.win._on_radial_array_copy()
            self.kernel.process_queue()

            # repeats=6 -> 5 new copies (the original stays part of the
            # circle rather than being duplicated a 6th time).
            self.assertEqual(len(list(elements.elems())), count_before + 5)

        with patch.object(
            QDialog, "exec", lambda dlg_self: QDialog.DialogCode.Rejected
        ):
            count_before2 = len(list(elements.elems()))
            self.win._on_radial_array_copy()
            self.assertEqual(len(list(elements.elems())), count_before2)

        elements.set_emphasis(None)
        self.kernel.process_queue()
        opened = []
        with patch.object(QDialog, "exec", lambda dlg_self: opened.append(1)):
            self.win._on_radial_array_copy()
            self.assertEqual(opened, [])

    def test_merge_paths_and_break_apart_round_trip(self):
        # "merge" and "subpath" (madgrav/core/elements/branches.py) both
        # declare input_type="elements" with no bare/None form -- only
        # reachable via the "element* {cmd}" pipe. Neither had a Qt path
        # at all before this. Round-trips two separate rects into one
        # merged "elem path" and back into two elements.
        elements = self.root.elements

        # Merge needs >= 2 -- a no-op (not a crash) below that.
        self.win._on_merge_paths()
        self.root("rect 0mm 0mm 5mm 5mm\n")
        self.kernel.process_queue()
        node1 = list(elements.elems())[-1]
        elements.set_emphasis([node1])
        self.kernel.process_queue()
        self.win._on_merge_paths()
        self.assertEqual(len(list(elements.elems())), 1)

        self.root("rect 20mm 0mm 5mm 5mm\n")
        self.kernel.process_queue()
        node2 = list(elements.elems())[-1]
        elements.set_emphasis([node1, node2])
        self.kernel.process_queue()

        self.win._on_merge_paths()
        self.kernel.process_queue()
        self.assertEqual(len(list(elements.elems())), 1)
        merged = list(elements.elems())[-1]
        self.assertEqual(merged.type, "elem path")

        # Break-apart needs >= 1 -- a no-op with nothing selected.
        elements.set_emphasis(None)
        self.kernel.process_queue()
        self.win._on_break_apart()
        self.assertEqual(len(list(elements.elems())), 1)

        elements.set_emphasis([merged])
        self.kernel.process_queue()
        self.win._on_break_apart()
        self.kernel.process_queue()
        self.assertEqual(len(list(elements.elems())), 2)

    def test_simplify_path_refuses_non_path_and_reduces_segment_count(self):
        # LightBurn's "Simplify" -- reduces a complex path's node count
        # within a tolerance. Only meaningful for "elem path" nodes (an
        # ellipse/rect's geometry is parametric, not a literal point
        # list) -- _on_simplify_path() checks the node TYPE itself
        # before dispatching, since the backend's own rejection
        # ("Invalid node for simplify") only goes to the console
        # channel, which _run_console() can't see (not an exception).
        #
        # geometry.index (not len(geometry.segments)) is the actual
        # used-segment count -- .segments is a fixed-capacity numpy
        # buffer (madgrav/core/geomstr.py), so len() of it never
        # changes; discovered while first writing this test. And the
        # node is simplified IN PLACE (same object identity) -- the
        # "before" count is captured as a plain int before dispatching,
        # not by holding a reference to compare against later (the same
        # aliasing pitfall as the rotate-matrix test elsewhere in this
        # file: holding the object and reading its live value AFTER a
        # mutation just reads the already-mutated state twice).
        elements = self.root.elements

        self.root("rect 0mm 0mm 5mm 5mm\n")
        self.kernel.process_queue()
        rect_node = list(elements.elems())[-1]
        elements.set_emphasis([rect_node])
        self.kernel.process_queue()

        opened = []
        with patch.object(QDialog, "exec", lambda dlg_self: opened.append(1)):
            self.win.status_bar.showMessage("")
            self.win._on_simplify_path()
            self.assertEqual(opened, [])
            self.assertNotEqual(self.win.status_bar.currentMessage(), "")

        # A jagged many-point path -- near-collinear points should
        # collapse well within a 2mm tolerance.
        pts = " L".join(f"{i},{(i % 3) * 0.01}" for i in range(200))
        self.root(f'path "M{pts} Z"\n')
        self.kernel.process_queue()
        path_node = list(elements.elems())[-1]
        elements.set_emphasis([path_node])
        self.kernel.process_queue()
        segments_before = path_node.geometry.index

        def fake_exec(dlg_self):
            spin = dlg_self.findChild(QDoubleSpinBox)
            spin.setValue(2.0)  # mm tolerance
            return QDialog.DialogCode.Accepted

        with patch.object(QDialog, "exec", fake_exec):
            self.win._on_simplify_path()
            self.kernel.process_queue()
            self.assertLess(path_node.geometry.index, segments_before)

        # A cancelled dialog is a no-op.
        segments_before2 = path_node.geometry.index
        with patch.object(
            QDialog, "exec", lambda dlg_self: QDialog.DialogCode.Rejected
        ):
            self.win._on_simplify_path()
            self.assertEqual(path_node.geometry.index, segments_before2)

    def test_add_hatch_effect_wraps_selection_in_a_new_node(self):
        # LightBurn's "Hatch Fill" -- one of its headline features.
        # "effect-hatch" (madgrav/core/elements/shapes.py) doesn't
        # mutate the selected element(s) in place: it creates a new
        # "effect hatch" tree node as a sibling and reparents the
        # selection to become ITS children (same reparenting shape as
        # group/ungroup) -- so this checks elem_branch.children for the
        # new node, not elements.elems() (which still finds the same
        # rect object regardless of where in the tree it's nested).
        elements = self.root.elements

        opened = []
        with patch.object(QDialog, "exec", lambda dlg_self: opened.append(1)):
            self.win._on_add_hatch_effect()  # no selection -- safe no-op
            self.assertEqual(opened, [])

        self.root("rect 0mm 0mm 20mm 20mm\n")
        self.kernel.process_queue()
        node = list(elements.elems())[-1]
        elements.set_emphasis([node])
        self.kernel.process_queue()

        def fake_exec(dlg_self):
            spins = dlg_self.findChildren(QDoubleSpinBox)
            spins[0].setValue(1.0)  # distance mm
            spins[1].setValue(45.0)  # angle deg
            spins[2].setValue(0.0)  # angle delta deg
            return QDialog.DialogCode.Accepted

        with patch.object(QDialog, "exec", fake_exec):
            self.win._on_add_hatch_effect()
            self.kernel.process_queue()

            hatch_nodes = [
                n for n in elements.elem_branch.children if n.type == "effect hatch"
            ]
            self.assertEqual(len(hatch_nodes), 1)
            self.assertIn(node, list(hatch_nodes[0].children))

        # A cancelled dialog adds nothing.
        with patch.object(
            QDialog, "exec", lambda dlg_self: QDialog.DialogCode.Rejected
        ):
            self.win._on_add_hatch_effect()
            hatch_nodes_after = [
                n for n in elements.elem_branch.children if n.type == "effect hatch"
            ]
            self.assertEqual(len(hatch_nodes_after), 1)

    def test_add_offset_path_creates_a_new_node(self):
        # LightBurn's "Offset" tool -- grows/shrinks a shape's outline by
        # a fixed distance. Backend ("offset", offset_clpr.py with a
        # offset_mk.py fallback) creates a NEW "elem path" node rather
        # than mutating the source in place, same non-destructive shape
        # as Hatch above -- so this checks elements.elems() grew by one,
        # not that the original node's geometry changed.
        elements = self.root.elements

        opened = []
        with patch.object(QDialog, "exec", lambda dlg_self: opened.append(1)):
            self.win._on_add_offset_path()  # no selection -- safe no-op
            self.assertEqual(opened, [])

        self.root("rect 0mm 0mm 10mm 10mm\n")
        self.kernel.process_queue()
        before_count = len(list(elements.elems()))
        elements.set_emphasis(list(elements.elems()))
        self.kernel.process_queue()

        def fake_exec(dlg_self):
            spins = dlg_self.findChildren(QDoubleSpinBox)
            spins[0].setValue(2.0)
            return QDialog.DialogCode.Accepted

        with patch.object(QDialog, "exec", fake_exec):
            self.win._on_add_offset_path()
            self.kernel.process_queue()
            self.assertEqual(len(list(elements.elems())), before_count + 1)
            new_node = list(elements.elems())[-1]
            self.assertIn("Offset", str(getattr(new_node, "label", "") or ""))

        # A cancelled dialog adds nothing.
        with patch.object(
            QDialog, "exec", lambda dlg_self: QDialog.DialogCode.Rejected
        ):
            self.win._on_add_offset_path()
            self.assertEqual(len(list(elements.elems())), before_count + 1)

    def test_text_anchor_changes_alignment_and_ignores_non_text_nodes(self):
        # "text-anchor" (madgrav/core/elements/shapes.py) silently skips
        # any non-"elem text" node rather than erroring -- confirmed
        # here as a genuine no-op (status message still shown, no
        # exception) rather than assumed.
        elements = self.root.elements

        self.root("rect 0mm 0mm 5mm 5mm\n")
        self.kernel.process_queue()
        rect_node = list(elements.elems())[-1]
        elements.set_emphasis([rect_node])
        self.kernel.process_queue()
        self.win._on_text_anchor("middle")  # must not raise

        self.root('text "Hello"\n')
        self.kernel.process_queue()
        text_node = list(elements.elems())[-1]
        elements.set_emphasis([text_node])
        self.kernel.process_queue()
        self.assertEqual(text_node.anchor, "start")

        self.win._on_text_anchor("middle")
        self.kernel.process_queue()
        self.assertEqual(text_node.anchor, "middle")

        self.win._on_text_anchor("end")
        self.kernel.process_queue()
        self.assertEqual(text_node.anchor, "end")

    def test_edit_text_content_refuses_non_text_and_updates_selected_text(self):
        elements = self.root.elements

        self.root("rect 0mm 0mm 5mm 5mm\n")
        self.kernel.process_queue()
        rect_node = list(elements.elems())[-1]
        elements.set_emphasis([rect_node])
        self.kernel.process_queue()

        self.win.status_bar.showMessage("")
        self.win._on_edit_text_content()
        self.assertNotEqual(self.win.status_bar.currentMessage(), "")

        self.root('text "Hello"\n')
        self.kernel.process_queue()
        text_node = list(elements.elems())[-1]
        elements.set_emphasis([text_node])
        self.kernel.process_queue()

        QInputDialog.getText = staticmethod(lambda *a, **k: ("Bonjour", True))
        self.win._on_edit_text_content()
        self.kernel.process_queue()
        self.assertEqual(list(elements.elems())[-1].text, "Bonjour")

        # A cancelled dialog (ok=False) is a no-op.
        QInputDialog.getText = staticmethod(lambda *a, **k: ("", False))
        self.win._on_edit_text_content()
        self.assertEqual(list(elements.elems())[-1].text, "Bonjour")

    def test_align_left_moves_elements_to_shared_left_edge(self):
        # Built via the real "rect" console command, not elem_branch.add()
        # directly -- that API stores x/y/width/height completely as-is
        # with no Length parsing, so mixing raw ints with Length strings
        # (a trap some earlier tests in this file avoided only because
        # they never touched .bounds) blows up inside Geomstr.rect() the
        # moment something actually computes real geometry.
        elements = self.root.elements
        self.root("rect 0mm 0mm 5mm 5mm\n")
        self.root("rect 20mm 10mm 5mm 5mm\n")
        self.kernel.process_queue()
        rect1, rect2 = list(elements.elems())[-2:]
        self.assertNotAlmostEqual(rect1.bounds[0], rect2.bounds[0], places=2)

        elements.set_emphasis([rect1, rect2])
        self.kernel.process_queue()
        self.win._on_align("left")
        self.kernel.process_queue()
        self.app.processEvents()

        self.assertAlmostEqual(rect1.bounds[0], rect2.bounds[0], places=2)

    def test_align_left_is_undoable(self):
        # First attempt at this test held onto the ORIGINAL rect1/rect2
        # object references across the undo call and read .bounds off
        # them directly -- looked like a failure (bounds unchanged) but
        # was actually a test bug: undo's backup_tree()/restore_tree()
        # swap in freshly-copied node objects, so a reference held from
        # before undo is a stale, orphaned object that was never touched
        # by the restore at all. RectNode.__copy__ (elem_rect.py) already
        # deep-copies .matrix correctly (confirmed by reading it) -- the
        # bug was in this test's assumption, not in undo itself. Re-query
        # the tree after undo instead of trusting old references, same
        # discipline test_frame_selection_is_undoable already used (count
        # via a fresh elements.elems() call, not a held reference).
        elements = self.root.elements
        self.root("rect 0mm 0mm 5mm 5mm\n")
        self.root("rect 20mm 10mm 5mm 5mm\n")
        self.kernel.process_queue()
        rect1, rect2 = list(elements.elems())[-2:]
        elements.set_emphasis([rect1, rect2])
        self.kernel.process_queue()
        elements.undo.mark("baseline")

        x_before = rect2.bounds[0]
        self.win._on_align_left()
        self.kernel.process_queue()
        self.assertAlmostEqual(rect2.bounds[0], rect1.bounds[0], places=2)

        self.win._on_undo()
        self.kernel.process_queue()
        rect1, rect2 = list(elements.elems())[-2:]  # re-fetch: undo swaps in fresh node objects
        self.assertAlmostEqual(rect2.bounds[0], x_before, places=2, msg="undo must restore rect2's pre-align position")

        # Redo should re-apply the align -- same re-fetch discipline,
        # closing the loop on undo/redo symmetry for this handler.
        self.win._on_redo()
        self.kernel.process_queue()
        rect1, rect2 = list(elements.elems())[-2:]
        self.assertAlmostEqual(rect2.bounds[0], rect1.bounds[0], places=2, msg="redo must re-apply the align")

    def test_align_and_arrange_actions_show_status_message_when_selection_insufficient(self):
        # These used to silently no-op below their minimum selection count
        # (2 for align/match, 3 for distribute, 1 for center/mirror) --
        # every OTHER tool in the app (hatch, offset, nesting, vectorize)
        # already told the user why nothing happened, so these should too.
        self.root.elements.set_emphasis(None)
        self.kernel.process_queue()

        checks = [
            (self.win._on_align_left, "aligner"),
            (self.win._on_align_center_h, "aligner"),
            (self.win._on_align_right, "aligner"),
            (self.win._on_align_top, "aligner"),
            (self.win._on_align_center_v, "aligner"),
            (self.win._on_align_bottom, "aligner"),
            (self.win._on_center_to_bed, "centrer"),
            (self.win._on_mirror_h, "retourner"),
            (self.win._on_mirror_v, "retourner"),
            (self.win._on_distribute_h, "répartir"),
            (self.win._on_distribute_v, "répartir"),
            (self.win._on_match_width, "sélectionnez"),
            (self.win._on_match_height, "sélectionnez"),
            (lambda: self.win._on_align("left"), "aligner"),
            (lambda: self.win._on_geometry_op("union"), "sélectionnez"),
        ]
        for handler, expected_word in checks:
            self.win.status_bar.clearMessage()
            handler()
            msg = self.win.status_bar.currentMessage().lower()
            self.assertIn(expected_word, msg, f"{handler} gave no useful feedback for an empty selection")

    def test_geometry_union_merges_two_overlapping_elements(self):
        elements = self.root.elements
        self.root("rect 0mm 0mm 10mm 10mm\n")
        self.root("rect 5mm 5mm 10mm 10mm\n")
        self.kernel.process_queue()
        r1, r2 = list(elements.elems())[-2:]
        count_before = len(list(elements.elems()))

        elements.set_emphasis([r1, r2])
        self.kernel.process_queue()
        self.win._on_geometry_op("union")
        self.kernel.process_queue()
        self.app.processEvents()

        count_after = len(list(elements.elems()))
        self.assertLess(count_after, count_before)

    # -- Canvas draw-tool gesture (mouse press/move/release pipeline) ------

    def test_canvas_rect_drag_creates_matching_element(self):
        # No prior test in this file (or anywhere else, on inspection)
        # exercises the actual mouse-drag-to-draw pipeline in qt_canvas.py
        # -- everything else calls console commands or public methods
        # directly. This drives real QMouseEvents through the QGraphicsView
        # to confirm mousePressEvent -> _update_draw_preview ->
        # _finish_draw -> the "rect" console command -> a real element,
        # end to end, with the drawn size actually matching the drag.
        canvas = self.win.canvas
        elements = self.root.elements
        count_before = len(list(elements.elems()))

        canvas.set_draw_mode("rect")
        start = QPoint(60, 60)
        end = QPoint(160, 140)
        QTest.mousePress(canvas.viewport(), Qt.MouseButton.LeftButton, pos=start)
        QTest.mouseMove(canvas.viewport(), pos=end)
        QTest.mouseRelease(canvas.viewport(), Qt.MouseButton.LeftButton, pos=end)
        self.app.processEvents()

        self.assertEqual(len(list(elements.elems())), count_before + 1)
        new_node = list(elements.elems())[-1]
        self.assertEqual(new_node.type, "elem rect")

        from madgrav.core.units import UNITS_PER_MM

        scene_start = canvas.mapToScene(start)
        scene_end = canvas.mapToScene(end)
        expected_w = abs(scene_end.x() - scene_start.x())
        expected_h = abs(scene_end.y() - scene_start.y())
        b = new_node.bounds
        actual_w = (b[2] - b[0]) / UNITS_PER_MM
        actual_h = (b[3] - b[1]) / UNITS_PER_MM
        self.assertAlmostEqual(actual_w, expected_w, delta=1.0)
        self.assertAlmostEqual(actual_h, expected_h, delta=1.0)

    def test_rect_corner_radius_spinbox_rounds_the_next_drawn_rectangle(self):
        # LightBurn's Rectangle tool has a corner-radius field in its
        # options bar; "rect" (madgrav/core/elements/shapes.py) already
        # supports rounded corners via its -x/-y options, just never
        # wired to this tool's actual drag gesture before. The spinbox
        # (qt_main.py) writes straight into MadGravQtCanvas.
        # rect_corner_radius_mm, read by _finish_draw() at the moment a
        # drag completes -- default 0 must stay sharp-cornered (no
        # regression for every rectangle drawn before this feature).
        canvas = self.win.canvas
        elements = self.root.elements

        self.assertEqual(canvas.rect_corner_radius_mm, 0.0)

        canvas.set_draw_mode("rect")
        QTest.mousePress(canvas.viewport(), Qt.MouseButton.LeftButton, pos=QPoint(60, 60))
        QTest.mouseMove(canvas.viewport(), pos=QPoint(160, 140))
        QTest.mouseRelease(canvas.viewport(), Qt.MouseButton.LeftButton, pos=QPoint(160, 140))
        self.app.processEvents()
        sharp_node = list(elements.elems())[-1]
        self.assertEqual(sharp_node.rx, 0)
        self.assertEqual(sharp_node.ry, 0)

        self.win.rect_corner_radius_spin.setValue(3.5)
        self.assertEqual(canvas.rect_corner_radius_mm, 3.5)

        canvas.set_draw_mode("rect")
        QTest.mousePress(canvas.viewport(), Qt.MouseButton.LeftButton, pos=QPoint(60, 60))
        QTest.mouseMove(canvas.viewport(), pos=QPoint(160, 140))
        QTest.mouseRelease(canvas.viewport(), Qt.MouseButton.LeftButton, pos=QPoint(160, 140))
        self.app.processEvents()
        rounded_node = list(elements.elems())[-1]
        from madgrav.core.units import UNITS_PER_MM

        self.assertAlmostEqual(rounded_node.rx / UNITS_PER_MM, 3.5, delta=0.01)
        self.assertAlmostEqual(rounded_node.ry / UNITS_PER_MM, 3.5, delta=0.01)

        # Resetting to 0 must not leave rounding stuck on for later draws.
        self.win.rect_corner_radius_spin.setValue(0.0)
        canvas.set_draw_mode("rect")
        QTest.mousePress(canvas.viewport(), Qt.MouseButton.LeftButton, pos=QPoint(60, 60))
        QTest.mouseMove(canvas.viewport(), pos=QPoint(160, 140))
        QTest.mouseRelease(canvas.viewport(), Qt.MouseButton.LeftButton, pos=QPoint(160, 140))
        self.app.processEvents()
        reset_node = list(elements.elems())[-1]
        self.assertEqual(reset_node.rx, 0)
        self.assertEqual(reset_node.ry, 0)

    def test_canvas_ellipse_and_line_drag_create_matching_elements(self):
        # Rectangle's drag pipeline is covered above -- Ellipse and Line
        # take genuinely different branches in _finish_draw() (ellipse
        # computes a center+radii command from the drag rect; line uses
        # its own length-based minimum-size check instead of width/
        # height), with no prior real-mouse coverage for either.
        from madgrav.core.units import UNITS_PER_MM

        canvas = self.win.canvas
        elements = self.root.elements

        canvas.set_draw_mode("ellipse")
        count_before = len(list(elements.elems()))
        start, end = QPoint(60, 60), QPoint(160, 140)
        QTest.mousePress(canvas.viewport(), Qt.MouseButton.LeftButton, pos=start)
        QTest.mouseMove(canvas.viewport(), pos=end)
        QTest.mouseRelease(canvas.viewport(), Qt.MouseButton.LeftButton, pos=end)
        self.app.processEvents()
        self.assertEqual(len(list(elements.elems())), count_before + 1)
        enode = list(elements.elems())[-1]
        self.assertEqual(enode.type, "elem ellipse")
        scene_start, scene_end = canvas.mapToScene(start), canvas.mapToScene(end)
        expected_w = abs(scene_end.x() - scene_start.x())
        expected_h = abs(scene_end.y() - scene_start.y())
        b = enode.bounds
        self.assertAlmostEqual((b[2] - b[0]) / UNITS_PER_MM, expected_w, delta=1.0)
        self.assertAlmostEqual((b[3] - b[1]) / UNITS_PER_MM, expected_h, delta=1.0)

        canvas.set_draw_mode("line")
        count_before2 = len(list(elements.elems()))
        start2, end2 = QPoint(60, 60), QPoint(200, 200)
        QTest.mousePress(canvas.viewport(), Qt.MouseButton.LeftButton, pos=start2)
        QTest.mouseMove(canvas.viewport(), pos=end2)
        QTest.mouseRelease(canvas.viewport(), Qt.MouseButton.LeftButton, pos=end2)
        self.app.processEvents()
        self.assertEqual(len(list(elements.elems())), count_before2 + 1)
        self.assertEqual(list(elements.elems())[-1].type, "elem line")

    def test_canvas_zero_distance_drag_is_treated_as_an_accidental_click(self):
        # A press-and-release at the same point (no real drag) must not
        # create a degenerate zero-size element for any draw tool --
        # matches "an under-sized drag leaves the tool active" from the
        # cancel-related tests, but here confirmed for all three
        # rect/ellipse/line branches of _finish_draw() specifically.
        canvas = self.win.canvas
        elements = self.root.elements
        for mode in ("rect", "ellipse", "line"):
            canvas.set_draw_mode(mode)
            count_before = len(list(elements.elems()))
            p = QPoint(60, 60)
            QTest.mousePress(canvas.viewport(), Qt.MouseButton.LeftButton, pos=p)
            QTest.mouseRelease(canvas.viewport(), Qt.MouseButton.LeftButton, pos=p)
            self.app.processEvents()
            self.assertEqual(
                len(list(elements.elems())), count_before, f"{mode} tool"
            )

    def test_canvas_text_tool_click_prompts_and_places_element(self):
        # Text is placed with a single click (a QInputDialog.getText()
        # prompt follows) rather than a click-drag gesture like the other
        # draw tools -- no prior coverage of this path at all. Confirms
        # the happy path creates a real "elem text" node, a cancelled/
        # empty-string dialog is a no-op that leaves the Text tool active
        # (matching an under-sized drag leaving Rectangle/Cercle/Ligne
        # active), and a literal double quote in the typed text is folded
        # to a single quote rather than breaking the chained console
        # command's quoting (madgrav/qt/qt_canvas.py: _place_text's own
        # comment -- the console parser has no escape for a literal ").
        canvas = self.win.canvas
        elements = self.root.elements
        count_before = len(list(elements.elems()))

        canvas.set_draw_mode("text")
        QInputDialog.getText = staticmethod(lambda *a, **k: ("Hello World", True))
        QTest.mouseClick(canvas.viewport(), Qt.MouseButton.LeftButton, pos=QPoint(80, 80))
        self.app.processEvents()
        self.kernel.process_queue()

        self.assertEqual(len(list(elements.elems())), count_before + 1)
        new_node = list(elements.elems())[-1]
        self.assertEqual(new_node.type, "elem text")
        self.assertEqual(new_node.text, "Hello World")
        self.assertIsNone(canvas.draw_mode)  # reverts to Select, like other tools

        canvas.set_draw_mode("text")
        QInputDialog.getText = staticmethod(lambda *a, **k: ("", False))
        count_before2 = len(list(elements.elems()))
        QTest.mouseClick(canvas.viewport(), Qt.MouseButton.LeftButton, pos=QPoint(80, 80))
        self.app.processEvents()
        self.assertEqual(len(list(elements.elems())), count_before2)
        self.assertEqual(canvas.draw_mode, "text")  # cancel leaves tool active

        QInputDialog.getText = staticmethod(lambda *a, **k: ('He said "hi"', True))
        QTest.mouseClick(canvas.viewport(), Qt.MouseButton.LeftButton, pos=QPoint(100, 100))
        self.app.processEvents()
        self.kernel.process_queue()
        newest = list(elements.elems())[-1]
        self.assertEqual(newest.text, "He said 'hi'")

    def test_canvas_polygon_tool_click_prompts_and_places_element(self):
        # Same single-click-then-dialog shape as the Text tool above --
        # a regular polygon/star has no natural two-corner drag (it would
        # only fix one dimension, not sides-count or star-vs-regular), so
        # a QDialog (not QInputDialog, since it needs 3 fields) follows
        # the click instead. "polygon" (madgrav/core/elements/shapes.py)
        # creates an "elem polyline" node from an explicit point list --
        # this confirms the vertex COUNT matches sides (or sides*2 for a
        # star), a cancelled dialog is a no-op that leaves the tool
        # active, and clicking with no selection doesn't just no-op the
        # whole thing (unlike most Edit-menu actions, this tool creates
        # NEW content, it never needs an existing selection).
        canvas = self.win.canvas
        elements = self.root.elements
        count_before = len(list(elements.elems()))

        canvas.set_draw_mode("polygon")

        def fake_exec_hexagon(dlg_self):
            dlg_self.findChildren(QSpinBox)[0].setValue(6)
            dlg_self.findChildren(QDoubleSpinBox)[0].setValue(10.0)
            return QDialog.DialogCode.Accepted

        with patch.object(QDialog, "exec", fake_exec_hexagon):
            QTest.mouseClick(canvas.viewport(), Qt.MouseButton.LeftButton, pos=QPoint(80, 80))
            self.app.processEvents()
            self.kernel.process_queue()

        self.assertEqual(len(list(elements.elems())), count_before + 1)
        new_node = list(elements.elems())[-1]
        self.assertEqual(new_node.type, "elem polyline")
        # PolylineNode.shape (madgrav/core/node/elem_polyline.py) rebuilds
        # from self.geometry.as_points(), not the original point list --
        # a closed shape's geometry carries an explicit closing segment
        # back to the first vertex, so a real N-sided polygon reads back
        # as N+1 points (last == first). Confirmed here rather than just
        # asserted, since it's not obvious from the console command alone.
        shape_points = list(new_node.shape)
        self.assertEqual(len(shape_points), 7)
        self.assertAlmostEqual(shape_points[0].x, shape_points[-1].x, places=6)
        self.assertAlmostEqual(shape_points[0].y, shape_points[-1].y, places=6)
        self.assertIsNone(canvas.draw_mode)  # reverts to Select, like other tools

        canvas.set_draw_mode("polygon")

        def fake_exec_star(dlg_self):
            dlg_self.findChildren(QSpinBox)[0].setValue(5)
            dlg_self.findChildren(QDoubleSpinBox)[0].setValue(8.0)
            dlg_self.findChildren(QCheckBox)[0].setChecked(True)
            return QDialog.DialogCode.Accepted

        with patch.object(QDialog, "exec", fake_exec_star):
            QTest.mouseClick(canvas.viewport(), Qt.MouseButton.LeftButton, pos=QPoint(120, 120))
            self.app.processEvents()
            self.kernel.process_queue()

        star_node = list(elements.elems())[-1]
        # 5 branches -> 10 vertices, +1 duplicated closing point (see above).
        self.assertEqual(len(list(star_node.shape)), 11)

        # A cancelled dialog is a no-op that leaves the tool active.
        canvas.set_draw_mode("polygon")
        count_before3 = len(list(elements.elems()))
        with patch.object(QDialog, "exec", lambda dlg_self: QDialog.DialogCode.Rejected):
            QTest.mouseClick(canvas.viewport(), Qt.MouseButton.LeftButton, pos=QPoint(60, 60))
            self.app.processEvents()
        self.assertEqual(len(list(elements.elems())), count_before3)
        self.assertEqual(canvas.draw_mode, "polygon")

    def test_drawing_a_shape_auto_reverts_to_the_select_tool(self):
        # Draw tools are one-shot (_on_shape_created, wired to the
        # canvas's shape_created signal): matches most vector editors'
        # default of handing control back to Select once a shape has
        # actually been created, instead of staying in draw mode ready
        # to start a second shape on the next click. Goes through the
        # real Rectangle button (not canvas.set_draw_mode() directly) so
        # the tool_group's checked state is exercised too, same reasoning
        # as test_tool_panel_buttons_are_wired_to_the_right_handler.
        canvas = self.win.canvas
        buttons = self.win.tool_group.buttons()
        select_btn, rect_btn = buttons[0], buttons[2]

        QTest.mouseClick(rect_btn, Qt.MouseButton.LeftButton)
        self.assertEqual(canvas.draw_mode, "rect")
        self.assertTrue(rect_btn.isChecked())

        QTest.mousePress(canvas.viewport(), Qt.MouseButton.LeftButton, pos=QPoint(60, 60))
        QTest.mouseMove(canvas.viewport(), pos=QPoint(160, 140))
        QTest.mouseRelease(canvas.viewport(), Qt.MouseButton.LeftButton, pos=QPoint(160, 140))
        self.app.processEvents()

        self.assertIsNone(canvas.draw_mode)
        self.assertTrue(select_btn.isChecked())
        self.assertFalse(rect_btn.isChecked())

    # -- Resize/rotate selection handles -------------------------------------

    def test_selection_handles_appear_only_for_a_single_selection(self):
        elements = self.root.elements
        canvas = self.win.canvas

        # No selection -> no handles.
        canvas._update_selection_handles()
        self.assertEqual(canvas._handle_items, {})

        self.root("rect 0mm 0mm 10mm 10mm\n")
        self.kernel.process_queue()
        canvas.render_elements()
        node_a = list(elements.elems())[-1]
        elements.set_emphasis([node_a])
        canvas.refresh_selection_highlight()
        # 8 resize handles + the rotate handle + its connecting line.
        self.assertEqual(len(canvas._handle_items), 10)

        self.root("rect 20mm 0mm 10mm 10mm\n")
        self.kernel.process_queue()
        canvas.render_elements()
        node_b = list(elements.elems())[-1]
        elements.set_emphasis([node_a, node_b])
        canvas.refresh_selection_highlight()
        self.assertEqual(
            canvas._handle_items, {}, "multi-selection must not show handles"
        )

    def test_refresh_selection_highlight_only_restyles_the_changed_delta(self):
        # refresh_selection_highlight() used to restyle every rendered
        # item on every selection change; it now only touches the items
        # whose emphasis flipped (tracked via _prev_emphasized_items).
        # Correctness check: switching selection from A to B must still
        # leave A looking unselected and B looking selected, and the
        # cache must track exactly what's currently emphasized.
        elements = self.root.elements
        canvas = self.win.canvas

        self.root("rect 0mm 0mm 10mm 10mm\n")
        self.root("rect 20mm 0mm 10mm 10mm\n")
        self.kernel.process_queue()
        canvas.render_elements()
        node_a, node_b = list(elements.elems())[-2:]
        item_a = next(i for i, n in canvas._item_to_node.items() if n is node_a)
        item_b = next(i for i, n in canvas._item_to_node.items() if n is node_b)

        elements.set_emphasis([node_a])
        canvas.refresh_selection_highlight()
        self.assertEqual(canvas._prev_emphasized_items, {item_a})
        self.assertEqual(item_a.zValue(), 11)
        self.assertEqual(item_b.zValue(), 10)

        # Switch selection to B -- A must revert (it's in the delta as a
        # "was emphasized, no longer is" item) and B must now highlight.
        elements.set_emphasis([node_b])
        canvas.refresh_selection_highlight()
        self.assertEqual(canvas._prev_emphasized_items, {item_b})
        self.assertEqual(item_a.zValue(), 10, "previously-selected item must revert")
        self.assertEqual(item_b.zValue(), 11)

        # Deselect entirely -- delta is just {item_b} (the "was" side).
        elements.set_emphasis(None)
        canvas.refresh_selection_highlight()
        self.assertEqual(canvas._prev_emphasized_items, set())
        self.assertEqual(item_a.zValue(), 10)
        self.assertEqual(item_b.zValue(), 10)

    def test_dragging_a_corner_handle_resizes_the_element(self):
        from madgrav.core.units import UNITS_PER_MM

        elements = self.root.elements
        canvas = self.win.canvas

        self.root("rect 0mm 0mm 10mm 10mm\n")
        self.kernel.process_queue()
        canvas.render_elements()
        node = list(elements.elems())[-1]
        elements.set_emphasis([node])
        canvas.refresh_selection_highlight()

        se_handle = canvas._handle_items["se"]
        start_pos = canvas.mapFromScene(se_handle.pos())

        canvas._start_handle_drag("se", start_pos)
        self.assertEqual(canvas._active_handle, "se")

        # Drag the SE corner out to (20mm, 20mm) -- doubles the shape to
        # 20x20mm, anchored at its unmoved NW corner (0, 0).
        end_pos = canvas.mapFromScene(QPointF(20.0, 20.0))
        canvas._update_handle_drag(end_pos)
        canvas._finish_handle_drag(end_pos)
        self.kernel.process_queue()

        self.assertIsNone(canvas._active_handle)
        # "resize" applies a matrix scale rather than rewriting the
        # node's raw width/height attributes (those stay the pre-
        # transform local shape size) -- .bounds is the real, effective
        # (transformed) bounding box, same as every other geometry
        # assertion this session (QR code / gear / jigsaw generators).
        # delta=2.0: the drag position round-trips through
        # mapFromScene()/mapToScene() (pixel <-> mm), which loses
        # sub-pixel precision at whatever zoom level the test window
        # happens to be at -- a real user drag has the exact same
        # rounding, so this is expected imprecision, not a bug (the
        # resize command itself, confirmed via the "resize -1.0mm
        # -1.0mm 21.09mm 21.09mm" console echo, applies exactly what
        # it's given).
        min_x, min_y, max_x, max_y = node.bounds
        self.assertAlmostEqual((max_x - min_x) / UNITS_PER_MM, 20.0, delta=2.0)
        self.assertAlmostEqual((max_y - min_y) / UNITS_PER_MM, 20.0, delta=2.0)
        self.assertAlmostEqual(min_x / UNITS_PER_MM, 0.0, delta=2.0)
        self.assertAlmostEqual(min_y / UNITS_PER_MM, 0.0, delta=2.0)

    def test_dragging_the_rotate_handle_rotates_the_element(self):
        elements = self.root.elements
        canvas = self.win.canvas

        self.root("rect 0mm 0mm 10mm 10mm\n")
        self.kernel.process_queue()
        canvas.render_elements()
        node = list(elements.elems())[-1]
        elements.set_emphasis([node])
        canvas.refresh_selection_highlight()

        before_rotation = node.matrix.rotation

        rotate_handle = canvas._handle_items["rotate"]
        start_pos = canvas.mapFromScene(rotate_handle.pos())
        canvas._start_handle_drag("rotate", start_pos)
        self.assertEqual(canvas._active_handle, "rotate")

        # The rotate handle starts due north of the shape's center; drag
        # it due east instead -- a clean, unambiguous ~90 degree turn.
        center = canvas._handle_drag_center
        east_scene = QPointF(center.x() + 20.0, center.y())
        end_pos = canvas.mapFromScene(east_scene)
        canvas._update_handle_drag(end_pos)
        canvas._finish_handle_drag(end_pos)
        self.kernel.process_queue()

        self.assertIsNone(canvas._active_handle)
        after_rotation = node.matrix.rotation
        self.assertNotAlmostEqual(float(after_rotation), float(before_rotation), delta=0.01)

        # A cancelled/negligible drag (release ~where it started) must
        # not rotate anything.
        elements.set_emphasis([node])
        canvas.refresh_selection_highlight()
        rotate_handle = canvas._handle_items["rotate"]
        start_pos = canvas.mapFromScene(rotate_handle.pos())
        canvas._start_handle_drag("rotate", start_pos)
        rotation_before_noop = node.matrix.rotation
        canvas._finish_handle_drag(start_pos)
        self.assertAlmostEqual(
            float(node.matrix.rotation), float(rotation_before_noop), delta=0.01
        )

    # -- Light/Dark theme toggle -------------------------------------------

    def test_theme_toggle_changes_canvas_colors_and_persists(self):
        self.assertTrue(self.win._dark_theme)
        self.assertFalse(self.win.act_light_theme.isChecked())

        # Not viewport (2, 2) -- that corner sits inside drawBackground()'s
        # ruler-drawing zone (X-ruler ticks span scene y in [-22, 0],
        # Y-ruler ticks/text span scene x in [-35, 0], both hugging the
        # origin near the top-left corner), not the plain bed background.
        # The ruler pen is deliberately INVERTED for contrast against its
        # own theme (dark theme's #A0A0B0 pen is lighter than light
        # theme's #505060 pen -- exactly backwards from the background
        # trend this test checks), so a sample landing there fails this
        # assertion regardless of whether the real background recolored
        # correctly. Confirmed by hand: dark=160/light=80 red are exactly
        # those two pens' red channels, not background fill colors.
        # Whether (2, 2) actually lands in that zone depends on the
        # canvas's exact pixel size at construction time (where the
        # bed's 0,0 origin maps to in the viewport) -- fragile to any
        # layout change elsewhere in the window, which is exactly what
        # exposed this. Sampling well inside the viewport instead (offset
        # from center, not dead-center, to dodge the bed-dimensions
        # watermark text) is robust regardless of window/dock geometry.
        viewport = self.win.canvas.viewport()
        sample_point = (viewport.width() // 2 + 30, viewport.height() // 2 + 30)
        dark_pixel = viewport.grab().toImage().pixelColor(*sample_point)

        self.win.act_light_theme.setChecked(True)
        self.win._on_toggle_theme()
        self.app.processEvents()

        self.assertFalse(self.win._dark_theme)
        self.assertFalse(self.root.qt_dark_theme)
        light_pixel = viewport.grab().toImage().pixelColor(*sample_point)
        self.assertNotEqual(light_pixel, dark_pixel)
        self.assertGreater(light_pixel.red(), dark_pixel.red())  # lighter

        # A fresh window must pick up the persisted choice.
        self.win._closing_from_kernel = True
        self.win.close()
        win2 = MadGravQtMainWindow(self.root)
        win2.show()
        self.app.processEvents()
        try:
            self.assertFalse(win2._dark_theme)
            self.assertTrue(win2.act_light_theme.isChecked())
        finally:
            win2._closing_from_kernel = True
            win2.close()

    def test_theme_toggle_with_rendered_elements_does_not_crash(self):
        # Same underlying bug as
        # test_device_switch_with_rendered_elements_does_not_crash:
        # set_theme() also calls canvas.init_scene() then
        # canvas.render_elements(), so the theme toggle crashed exactly
        # the same way as a device switch whenever the canvas had any
        # rendered elements -- silent in the OTHER theme tests above
        # because none of them ever added an element to the document
        # first.
        self.root("rect 0mm 0mm 5mm 5mm\n")
        self.kernel.process_queue()
        self.win.canvas.render_elements()
        self.assertEqual(len(self.win.canvas._element_items), 1)

        self.win.act_light_theme.setChecked(True)
        self.win._on_toggle_theme()  # previously raised RuntimeError
        self.app.processEvents()

        self.assertEqual(len(self.win.canvas._element_items), 1)
        self.assertEqual(len(list(self.root.elements.elems())), 1)

    def test_selection_highlight_survives_theme_toggle(self):
        # Companion to the crash-fix above: init_scene() + render_elements()
        # rebuild every QGraphicsItem from scratch, but the underlying
        # node.emphasized state lives on the kernel-side node, untouched
        # by that rebuild -- confirms a selected element's blue highlight
        # pen actually gets correctly re-applied to its FRESH graphics
        # item after a theme toggle, not silently dropped.
        elements = self.root.elements
        self.root("rect 0mm 0mm 5mm 5mm\n")
        self.kernel.process_queue()
        node = list(elements.elems())[-1]
        elements.set_emphasis([node])
        self.kernel.process_queue()
        self.win.canvas.render_elements()
        self.app.processEvents()

        def pen_color_for(node):
            for item, n in self.win.canvas._item_to_node.items():
                if n is node:
                    return item.pen().color().name()
            return None

        self.assertEqual(pen_color_for(node), "#0a84ff")

        self.win.act_light_theme.setChecked(True)
        self.win._on_toggle_theme()
        self.app.processEvents()

        self.assertEqual(pen_color_for(node), "#0a84ff")
        self.assertTrue(node.emphasized)

    def test_theme_toggle_updates_toolbar_button_inline_styles(self):
        # btn_arm/btn_coolant/btn_start/btn_pause/btn_stop each carry their
        # own inline stylesheet (colored backgrounds a plain QSS class
        # selector can't express) which entirely overrides the app-wide
        # theme QSS -- confirms _apply_toolbar_button_theme() actually
        # re-styles them on toggle instead of leaving dark-theme colors
        # behind (e.g. a dark disabled-Start button on an otherwise light
        # window).
        def corner_pixel(widget):
            img = widget.grab().toImage()
            return img.pixelColor(min(4, img.width() - 1), min(4, img.height() - 1))

        dark_arm = corner_pixel(self.win.btn_arm)
        self.assertEqual((dark_arm.red(), dark_arm.green(), dark_arm.blue()), (58, 58, 74))

        self.win.act_light_theme.setChecked(True)
        self.win._on_toggle_theme()
        self.app.processEvents()

        light_arm = corner_pixel(self.win.btn_arm)
        self.assertEqual(
            (light_arm.red(), light_arm.green(), light_arm.blue()), (214, 214, 222)
        )

        self.win.btn_start.setEnabled(False)
        self.app.processEvents()
        light_disabled_start = corner_pixel(self.win.btn_start)
        self.assertEqual(
            (light_disabled_start.red(), light_disabled_start.green(), light_disabled_start.blue()),
            (228, 228, 234),
        )

    def test_theme_toggle_updates_unstroked_element_fallback_color(self):
        # Elements with an explicitly unset/"none" stroke (some SVG
        # imports; elements.default_stroke itself is blue, so this is an
        # edge case, not the common path) fall back to a fixed color in
        # qt_canvas.py's _style_for_node(). A light-gray fallback tuned
        # for the dark theme's near-black bed is nearly invisible against
        # the light theme's white bed -- confirms the fallback itself is
        # theme-aware, with an actual contrast check against the bed
        # color, not just "it changed to *some* other color".
        elements = self.root.elements
        canvas = self.win.canvas
        self.root("rect 0mm 0mm 5mm 5mm\n")
        self.kernel.process_queue()
        node = list(elements.elems())[-1]
        node.stroke = None
        elements.set_emphasis(None)
        self.kernel.process_queue()

        pen_dark, _ = canvas._style_for_node(node)
        self.assertEqual(
            (pen_dark.color().red(), pen_dark.color().green(), pen_dark.color().blue()),
            (0xE0, 0xE0, 0xE0),
        )

        self.win.act_light_theme.setChecked(True)
        self.win._on_toggle_theme()
        self.app.processEvents()

        pen_light, _ = canvas._style_for_node(node)
        light_rgb = (
            pen_light.color().red(),
            pen_light.color().green(),
            pen_light.color().blue(),
        )
        self.assertEqual(light_rgb, (0x60, 0x60, 0x60))
        # Contrast against the light theme's white bed (#FFFFFF).
        stroke_luminance = sum(light_rgb) / 3
        self.assertGreater(255 - stroke_luminance, 100)

    def test_style_for_node_fill_color_and_alpha(self):
        # Companion to the stroke-fallback test above -- confirms the
        # FILL side of _style_for_node(): no fill set at all renders as
        # a transparent outline (NoBrush), an explicit fill color
        # renders as a real matching brush, and partial transparency
        # (alpha) carries through correctly rather than being dropped.
        from PyQt6.QtCore import Qt as QtCore
        from madgrav.svgelements import Color

        elements = self.root.elements
        canvas = self.win.canvas
        node = elements.elem_branch.add(
            type="elem rect",
            x=0,
            y=0,
            width="5mm",
            height="5mm",
            stroke=elements.default_stroke,
        )
        self.kernel.process_queue()

        _pen, brush = canvas._style_for_node(node)
        self.assertEqual(brush.style(), QtCore.BrushStyle.NoBrush)

        node.fill = Color("red")
        _pen2, brush2 = canvas._style_for_node(node)
        c = brush2.color()
        self.assertNotEqual(brush2.style(), QtCore.BrushStyle.NoBrush)
        self.assertEqual((c.red(), c.green(), c.blue()), (255, 0, 0))

        node.fill = Color(0, 255, 0, 128)
        _pen3, brush3 = canvas._style_for_node(node)
        c3 = brush3.color()
        self.assertEqual((c3.red(), c3.green(), c3.blue(), c3.alpha()), (0, 255, 0, 128))

    def test_style_for_node_treats_svg_none_color_as_unset(self):
        # _color_is_set()'s own comment: svgelements represents an
        # explicit fill="none"/stroke="none" (a real SVG import, not
        # this test harness's own "no fill assigned at all" case above)
        # as a Color instance whose components are None -- NOT Python
        # None. The tests above only ever assigned real Python None or a
        # real color, never this in-between case, which needs its own
        # `.red is not None` check to fall back correctly instead of
        # crashing or rendering a garbage color.
        from PyQt6.QtCore import Qt as QtCore
        from madgrav.svgelements import Color

        elements = self.root.elements
        canvas = self.win.canvas
        node = elements.elem_branch.add(
            type="elem rect", x=0, y=0, width="5mm", height="5mm"
        )
        self.kernel.process_queue()

        none_color = Color("none")
        self.assertIsNotNone(none_color)
        self.assertIsNone(none_color.red)
        self.assertFalse(canvas._color_is_set(none_color))

        node.fill = none_color
        _pen, brush = canvas._style_for_node(node)
        self.assertEqual(brush.style(), QtCore.BrushStyle.NoBrush)

        node.stroke = none_color
        pen2, _brush2 = canvas._style_for_node(node)
        c = pen2.color()
        self.assertEqual((c.red(), c.green(), c.blue()), (0xE0, 0xE0, 0xE0))

    def test_canvas_arrow_key_nudge_and_delete(self):
        # Another interactive-gesture path with no prior coverage: real
        # key events through the canvas widget (not calling
        # _nudge_emphasized()/_delete_emphasized() directly), confirming
        # keyPressEvent's key-to-action dispatch actually works and that
        # Shift+arrow moves 10x further than a plain arrow (madgrav/core/
        # bindalias.py's "right"/"shift+right" convention).
        elements = self.root.elements
        canvas = self.win.canvas
        self.root("rect 0mm 0mm 5mm 5mm\n")
        self.kernel.process_queue()
        node = list(elements.elems())[-1]
        elements.set_emphasis([node])
        self.kernel.process_queue()
        self.app.processEvents()

        x0 = node.bounds[0]
        canvas.setFocus()
        QTest.keyClick(canvas, Qt.Key.Key_Right)
        self.app.processEvents()
        x1 = node.bounds[0]
        self.assertGreater(x1, x0)
        plain_delta = x1 - x0

        QTest.keyClick(canvas, Qt.Key.Key_Right, Qt.KeyboardModifier.ShiftModifier)
        self.app.processEvents()
        x2 = node.bounds[0]
        shift_delta = x2 - x1
        self.assertGreater(shift_delta, plain_delta * 5)  # 10mm vs 1mm step

        count_before = len(list(elements.elems()))
        QTest.keyClick(canvas, Qt.Key.Key_Delete)
        self.app.processEvents()
        self.assertEqual(len(list(elements.elems())), count_before - 1)

    def test_nudge_on_locked_element_moves_the_visual_item_in_sync(self):
        # Regression test for a real bug found via this test:
        # _movable_selected_items() (madgrav/qt/qt_canvas.py) filtered
        # out any selected node with node.lock set, on the theory that
        # the "translate" console command "silently skips locked nodes".
        # It doesn't -- element_translate (madgrav/core/elements/
        # shapes.py) gates each node with node.can_move(self.
        # lock_allows_move), and elements.lock_allows_move defaults to
        # True, so a locked element is normally still translatable by
        # design (lock only blocks GUI drag-move). The bare "not locked"
        # filter left the on-screen QGraphicsItem frozen in place while
        # the real node's matrix/bounds moved underneath it -- confirmed
        # by nudging a locked element and finding its bounds changed but
        # its item.pos() didn't. Fixed by using node.can_move(lock_
        # allows_move) instead, matching the real permission check
        # exactly (both when it allows and when it forbids the move).
        elements = self.root.elements
        canvas = self.win.canvas
        self.root("rect 10mm 10mm 5mm 5mm\n")
        self.kernel.process_queue()
        node = list(elements.elems())[-1]
        elements.set_emphasis([node])
        self.kernel.process_queue()
        canvas.render_elements()
        self.app.processEvents()
        node.lock = True
        self.assertTrue(elements.lock_allows_move)  # the documented default
        item = next(it for it, n in canvas._item_to_node.items() if n is node)
        pos_before = item.pos()

        canvas._nudge_emphasized(20, 0)
        self.kernel.process_queue()
        self.app.processEvents()

        pos_after = item.pos()
        self.assertNotEqual(pos_after, pos_before)
        self.assertAlmostEqual(pos_after.x() - pos_before.x(), 20, delta=0.01)

        # With lock_allows_move explicitly disabled, a locked element
        # really can't be moved at all -- the item must stay put.
        elements.lock_allows_move = False
        pos_before2 = item.pos()
        canvas._nudge_emphasized(20, 0)
        self.kernel.process_queue()
        self.app.processEvents()
        self.assertEqual(item.pos(), pos_before2)

    def test_nudge_and_delete_work_with_a_fresh_multi_selection(self):
        # Same first_emphasized-is-None bug as the qt_main.py handlers
        # fixed earlier this session, here in the canvas' own arrow-key
        # nudge and Delete key -- among the most common interactions in
        # the app, and exactly the ones a rubber-band multi-select (no
        # prior single click) would hit.
        elements = self.root.elements
        canvas = self.win.canvas
        self.root("rect 0mm 0mm 5mm 5mm\n")
        self.root("rect 20mm 0mm 5mm 5mm\n")
        self.kernel.process_queue()
        r1, r2 = list(elements.elems())[-2:]
        canvas.render_elements()

        elements.set_emphasis([r1, r2])
        self.kernel.process_queue()
        item1 = next(it for it, n in canvas._item_to_node.items() if n is r1)
        pos_before = item1.pos()
        canvas._nudge_emphasized(15, 0)
        self.kernel.process_queue()
        self.assertAlmostEqual(item1.pos().x() - pos_before.x(), 15, delta=0.01)

        elements.set_emphasis([r1, r2])
        self.kernel.process_queue()
        count_before = len(list(elements.elems()))
        canvas._delete_emphasized()
        self.kernel.process_queue()
        self.assertLess(len(list(elements.elems())), count_before)

    def test_selection_label_shows_count_for_a_fresh_multi_selection(self):
        # Same bug, in the status-bar selection label: node=None (the
        # canvas' selection_changed signal payload) used to be checked
        # BEFORE the real selected-count, showing "Aucune sélection" for
        # a valid multi-selection just because no single element had been
        # clicked first.
        elements = self.root.elements
        self.root("rect 0mm 0mm 5mm 5mm\n")
        self.root("rect 20mm 0mm 5mm 5mm\n")
        self.kernel.process_queue()
        r1, r2 = list(elements.elems())[-2:]

        elements.set_emphasis([r1, r2])
        self.kernel.process_queue()
        self.win._on_selection_changed(elements.first_emphasized)

        self.assertNotIn("Aucune", self.win.selection_label.text())
        self.assertIn("2", self.win.selection_label.text())

    def test_canvas_click_and_shift_click_select_toggle(self):
        # The most basic canvas interaction -- clicking an element to
        # select it, Shift-clicking to add/remove from the selection --
        # had no real-mouse-event coverage anywhere in this file (the
        # rubber-band/drag test below is drag-based, and the context-menu
        # tests set emphasis manually rather than clicking to get there).
        elements = self.root.elements
        canvas = self.win.canvas
        self.root("rect 0mm 0mm 20mm 20mm\n")
        self.root("rect 40mm 0mm 20mm 20mm\n")
        self.kernel.process_queue()
        node_a, node_b = list(elements.elems())[-2:]
        canvas.render_elements()
        self.app.processEvents()

        def pos_for(node):
            item = next(it for it, n in canvas._item_to_node.items() if n is node)
            return canvas.viewport().mapFromGlobal(canvas.mapToGlobal(canvas.mapFromScene(item.sceneBoundingRect().center())))

        QTest.mouseClick(canvas.viewport(), Qt.MouseButton.LeftButton, pos=pos_for(node_a))
        self.app.processEvents()
        self.assertEqual(set(elements.elems(emphasized=True)), {node_a})

        QTest.mouseClick(
            canvas.viewport(),
            Qt.MouseButton.LeftButton,
            Qt.KeyboardModifier.ShiftModifier,
            pos=pos_for(node_b),
        )
        self.app.processEvents()
        self.assertEqual(set(elements.elems(emphasized=True)), {node_a, node_b})

        # Shift-clicking an already-selected item toggles it back out.
        QTest.mouseClick(
            canvas.viewport(),
            Qt.MouseButton.LeftButton,
            Qt.KeyboardModifier.ShiftModifier,
            pos=pos_for(node_a),
        )
        self.app.processEvents()
        self.assertEqual(set(elements.elems(emphasized=True)), {node_b})

        # A plain click on empty space deselects everything.
        QTest.mouseClick(
            canvas.viewport(),
            Qt.MouseButton.LeftButton,
            pos=canvas.viewport().rect().topLeft(),
        )
        self.app.processEvents()
        self.assertEqual(set(elements.elems(emphasized=True)), set())

    def test_canvas_rubber_band_selects_and_drag_moves_selection(self):
        # The two remaining mouse-gesture paths in qt_canvas.py with no
        # prior coverage: rubber-band multi-select (drag on empty space)
        # and click-drag-to-move a selection. Real QMouseEvents through
        # the QGraphicsView, not calling the private helpers directly.
        elements = self.root.elements
        canvas = self.win.canvas
        self.root("rect 0mm 0mm 5mm 5mm\n")
        self.root("rect 10mm 0mm 5mm 5mm\n")
        self.kernel.process_queue()
        r1, r2 = list(elements.elems())[-2:]
        elements.set_emphasis(None)
        self.kernel.process_queue()
        # A raw console "rect" doesn't push through the Qt cross-thread
        # signal chain the way a real running app's own event loop would
        # in this test process -- render explicitly, same as every other
        # test in this file that needs the canvas's _item_to_node
        # populated for hit-testing (most others only check kernel-side
        # node data and never needed this).
        canvas.render_elements()
        self.app.processEvents()

        from madgrav.core.units import UNITS_PER_MM

        b1 = [v / UNITS_PER_MM for v in r1.bounds]
        b2 = [v / UNITS_PER_MM for v in r2.bounds]
        margin = 2.0  # mm
        top_left = canvas.mapFromScene(
            min(b1[0], b2[0]) - margin, min(b1[1], b2[1]) - margin
        )
        bottom_right = canvas.mapFromScene(
            max(b1[2], b2[2]) + margin, max(b1[3], b2[3]) + margin
        )

        QTest.mousePress(canvas.viewport(), Qt.MouseButton.LeftButton, pos=top_left)
        QTest.mouseMove(canvas.viewport(), pos=bottom_right)
        QTest.mouseRelease(canvas.viewport(), Qt.MouseButton.LeftButton, pos=bottom_right)
        self.app.processEvents()

        selected = list(elements.elems(emphasized=True))
        self.assertEqual(len(selected), 2)
        self.assertIn(r1, selected)
        self.assertIn(r2, selected)

        center1 = canvas.mapFromScene((b1[0] + b1[2]) / 2, (b1[1] + b1[3]) / 2)
        target = QPoint(center1.x() + 30, center1.y() + 20)
        x0_before = r1.bounds[0] / UNITS_PER_MM

        QTest.mousePress(canvas.viewport(), Qt.MouseButton.LeftButton, pos=center1)
        QTest.mouseMove(canvas.viewport(), pos=target)
        QTest.mouseRelease(canvas.viewport(), Qt.MouseButton.LeftButton, pos=target)
        self.app.processEvents()

        x0_after = r1.bounds[0] / UNITS_PER_MM
        self.assertGreater(abs(x0_after - x0_before), 1.0)

    def test_canvas_shift_drag_rubber_band_adds_to_existing_selection(self):
        # The rubber-band test above only exercises the plain (replacing)
        # case -- Shift-dragging on empty space starts an ADDITIVE
        # rubber-band (_finish_rubber_band's additive branch), which
        # merges the newly-enclosed nodes into the current selection
        # instead of replacing it. No prior coverage of that branch.
        elements = self.root.elements
        canvas = self.win.canvas
        self.root("rect 0mm 0mm 5mm 5mm\n")
        self.root("rect 10mm 0mm 5mm 5mm\n")
        self.root("rect 60mm 60mm 5mm 5mm\n")  # far away, pre-selected separately
        self.kernel.process_queue()
        r1, r2, r3 = list(elements.elems())[-3:]
        canvas.render_elements()
        self.app.processEvents()

        elements.set_emphasis([r3])
        self.kernel.process_queue()

        from madgrav.core.units import UNITS_PER_MM

        b1 = [v / UNITS_PER_MM for v in r1.bounds]
        b2 = [v / UNITS_PER_MM for v in r2.bounds]
        margin = 2.0
        top_left = canvas.mapFromScene(
            min(b1[0], b2[0]) - margin, min(b1[1], b2[1]) - margin
        )
        bottom_right = canvas.mapFromScene(
            max(b1[2], b2[2]) + margin, max(b1[3], b2[3]) + margin
        )

        QTest.mousePress(
            canvas.viewport(),
            Qt.MouseButton.LeftButton,
            Qt.KeyboardModifier.ShiftModifier,
            pos=top_left,
        )
        QTest.mouseMove(canvas.viewport(), pos=bottom_right)
        QTest.mouseRelease(
            canvas.viewport(),
            Qt.MouseButton.LeftButton,
            Qt.KeyboardModifier.ShiftModifier,
            pos=bottom_right,
        )
        self.app.processEvents()

        self.assertEqual(set(elements.elems(emphasized=True)), {r1, r2, r3})

    def test_canvas_wheel_zoom_and_middle_button_pan(self):
        canvas = self.win.canvas

        scale_before = canvas.transform().m11()
        wheel_up = QWheelEvent(
            QPointF(200, 200), QPointF(200, 200), QPoint(0, 0), QPoint(0, 120),
            Qt.MouseButton.NoButton, Qt.KeyboardModifier.NoModifier,
            Qt.ScrollPhase.NoScrollPhase, False,
        )
        canvas.wheelEvent(wheel_up)
        scale_after_up = canvas.transform().m11()
        self.assertGreater(scale_after_up, scale_before)  # scroll up = zoom in

        wheel_down = QWheelEvent(
            QPointF(200, 200), QPointF(200, 200), QPoint(0, 0), QPoint(0, -120),
            Qt.MouseButton.NoButton, Qt.KeyboardModifier.NoModifier,
            Qt.ScrollPhase.NoScrollPhase, False,
        )
        canvas.wheelEvent(wheel_down)
        self.assertLess(canvas.transform().m11(), scale_after_up)  # scroll down = zoom out

        # Middle-button pan needs the scene to actually exceed the
        # viewport (non-zero scrollbar range) -- at default zoom the
        # whole bed fits the viewport with room to spare, so a pan delta
        # would have nothing to move and this would trivially pass for
        # the wrong reason (nothing to scroll, not "pan works").
        for _ in range(15):
            canvas.zoom_step(1)
        self.assertGreater(canvas.horizontalScrollBar().maximum(), 0)

        h_before = canvas.horizontalScrollBar().value()
        v_before = canvas.verticalScrollBar().value()
        start = QPoint(200, 200)
        end = QPoint(150, 160)
        QTest.mousePress(canvas.viewport(), Qt.MouseButton.MiddleButton, pos=start)
        QTest.mouseMove(canvas.viewport(), pos=end)
        QTest.mouseRelease(canvas.viewport(), Qt.MouseButton.MiddleButton, pos=end)
        self.app.processEvents()

        self.assertNotEqual(
            (canvas.horizontalScrollBar().value(), canvas.verticalScrollBar().value()),
            (h_before, v_before),
        )
        self.assertFalse(canvas.is_panning)  # released cleanly

    def test_reset_zoom_button_restores_100_percent(self):
        # canvas.reset_zoom() itself was never exercised anywhere in this
        # file -- via the real status-bar button (a local variable in
        # _setup_ui, not a self.* attribute, so found here by its text)
        # rather than calling reset_zoom() directly, matching this file's
        # established preference for driving real widgets over private
        # methods when a wiring bug could otherwise slip through.
        canvas = self.win.canvas
        canvas.zoom_step(1)
        canvas.zoom_step(1)
        canvas.zoom_step(1)
        self.assertNotAlmostEqual(canvas.transform().m11(), 1.0, places=2)

        btn = next(
            b
            for b in self.win.status_bar.findChildren(QPushButton)
            if "100%" in b.text()
        )
        QTest.mouseClick(btn, Qt.MouseButton.LeftButton)
        self.app.processEvents()

        self.assertAlmostEqual(canvas.transform().m11(), 1.0, places=6)
        self.assertEqual(self.win.zoom_label.text(), "100%")

    # -- Coolant / air-assist toggle ---------------------------------------

    def test_coolant_button_visibility_and_toggle(self):
        self._add_grbl_device()
        device = self.root.device

        self.assertFalse(self.win._has_coolant())
        self.assertFalse(self.win.btn_coolant.isVisible())

        # Matches the real trigger: a wx settings panel changing
        # device_coolant fires "coolant_changed" so claim_coolant() gets
        # re-run with the new value (madgrav/grbl/device.py only claims
        # once, at construction, with whatever value it had *then*).
        device.device_coolant = "gcode_m7"
        self.root.signal("coolant_changed")
        self.kernel.process_queue()
        self.app.processEvents()

        self.assertTrue(self.win._has_coolant())
        self.assertTrue(self.win.btn_coolant.isVisible())
        self.assertFalse(self.win.btn_coolant.isChecked())

        coolant = self.win._coolant_service()
        self.win._on_toggle_coolant()
        self.assertTrue(coolant.coolant_state(device))
        self.assertTrue(self.win.btn_coolant.isChecked())

        self.win._on_toggle_coolant()
        self.assertFalse(coolant.coolant_state(device))
        self.assertFalse(self.win.btn_coolant.isChecked())

    # -- Unsaved-changes tracking / close prompt -----------------------

    def test_window_title_reflects_file_path_and_dirty_state(self):
        # All 4 combinations of (no file / a file) x (clean / dirty),
        # confirming the "*" dirty marker and the "filename — base title"
        # format independently, not just one state or the other.
        self.win.current_file_path = None
        self.win._dirty = False
        self.win._update_window_title()
        self.assertEqual(self.win.windowTitle(), self.win._BASE_TITLE)

        self.win._dirty = True
        self.win._update_window_title()
        self.assertEqual(self.win.windowTitle(), "*" + self.win._BASE_TITLE)

        self.win.current_file_path = r"C:\Users\test\design.svg"
        self.win._dirty = False
        self.win._update_window_title()
        self.assertEqual(
            self.win.windowTitle(), f"design.svg — {self.win._BASE_TITLE}"
        )

        self.win._dirty = True
        self.win._update_window_title()
        self.assertEqual(
            self.win.windowTitle(), f"*design.svg — {self.win._BASE_TITLE}"
        )

    def test_fresh_window_does_not_start_dirty(self):
        # Bug found while writing this test: a fresh, untouched document
        # could still end up marked dirty (title "*", close-confirmation
        # prompt) purely from startup-time signal noise -- device/service
        # activation firing "refresh_scene" once, delivered asynchronously
        # via Qt's cross-thread queued connection shortly AFTER __init__
        # returns, not during it (so resetting _dirty at the end of
        # __init__ wouldn't have caught it). Now suppressed by
        # self._startup_settling for a short grace window after
        # construction. setUp()'s own 100ms settle wait isn't long enough
        # for this specific 300ms window, hence the extra wait here.
        QTest.qWait(350)
        self.assertFalse(self.win._dirty)
        self.assertFalse(self.win._startup_settling)

        # A real edit AFTER settling must still correctly mark dirty.
        elements = self.root.elements
        elements.elem_branch.add(type="elem rect", x=0, y=0, width=100, height=100)
        self.root.signal("refresh_scene", "Scene")
        self.kernel.process_queue()
        self.app.processEvents()
        self.assertTrue(self.win._dirty)

    def test_close_prompt_cancel_keeps_window_open_discard_closes(self):
        QTest.qWait(350)
        self.win._dirty = True

        QMessageBox.question = staticmethod(
            lambda *a, **k: QMessageBox.StandardButton.Cancel
        )
        self.win.close()
        self.assertTrue(self.win.isVisible())  # Cancel -> stays open

        QMessageBox.question = staticmethod(
            lambda *a, **k: QMessageBox.StandardButton.Discard
        )
        self.win.close()
        self.assertFalse(self.win.isVisible())  # Discard -> closes

    def test_kernel_initiated_shutdown_skips_unsaved_prompt_even_when_dirty(self):
        # _on_kernel_shutdown_requested (wired to shutdown_requested, which
        # madgrav/qt/plugin.py's "preshutdown" lifecycle emits for a
        # kernel-initiated close -- typed "quit", "-e quit", a remote
        # consoleserver disconnect) must exit promptly and unattended: a
        # real QMessageBox.question popup here would hang any headless/
        # scripted shutdown waiting for a click that never comes. Only a
        # user-driven close (the window's own X button) gets the prompt --
        # confirmed by making it fire (StandardButton.Cancel, which would
        # normally keep the window open) and checking it's simply never
        # invoked on this path.
        QTest.qWait(350)
        self.win._dirty = True
        asked = []
        QMessageBox.question = staticmethod(
            lambda *a, **k: (asked.append(1), QMessageBox.StandardButton.Cancel)[1]
        )
        self.assertFalse(self.win._closing_from_kernel)

        self.win._on_kernel_shutdown_requested()
        self.app.processEvents()

        self.assertEqual(asked, [])
        self.assertFalse(self.win.isVisible())
        self.assertTrue(self.win._closing_from_kernel)

    def test_close_prompt_save_choice_saves_then_closes(self):
        QTest.qWait(350)
        self.win._dirty = True
        self.win.current_file_path = None
        QMessageBox.question = staticmethod(
            lambda *a, **k: QMessageBox.StandardButton.Save
        )
        tmpdir = tempfile.mkdtemp(prefix="madgrav_close_save_test_")
        try:
            path = os.path.join(tmpdir, "a.svg")
            QFileDialog.getSaveFileName = staticmethod(lambda *a, **k: (path, ""))

            self.win.close()
            self.app.processEvents()

            self.assertFalse(self.win.isVisible())
            self.assertFalse(self.win._dirty)
            self.assertTrue(os.path.exists(path))
        finally:
            import shutil

            shutil.rmtree(tmpdir, ignore_errors=True)

    def test_close_prompt_save_choice_with_cancelled_picker_keeps_window_open(self):
        # If the user picks "Save" but then cancels the file picker (no
        # current_file_path yet, so one has to be prompted), the document
        # stays dirty -- closing anyway would silently discard unsaved
        # work despite the user explicitly having chosen "Save" over
        # "Discard" a moment earlier.
        QTest.qWait(350)
        self.win._dirty = True
        self.win.current_file_path = None
        QMessageBox.question = staticmethod(
            lambda *a, **k: QMessageBox.StandardButton.Save
        )
        QFileDialog.getSaveFileName = staticmethod(lambda *a, **k: ("", ""))

        self.win.close()
        self.app.processEvents()

        self.assertTrue(self.win.isVisible())
        self.assertTrue(self.win._dirty)

    # -- Open-file dialog filter / last-used directory ----------------------

    def test_open_file_filter_lists_all_registered_loaders(self):
        # Previously hardcoded to just svg/dxf/png/jpg/jpeg/bmp, silently
        # hiding every other genuinely supported format from the default
        # Open dialog filter -- confirms it's now built from the real
        # registered loaders (kernel.find("load")) in Qt's ";;"-separated
        # format, not wx's "|"-separated one.
        filt = self.win._build_open_file_filter()
        self.assertIn(";;", filt)
        self.assertIn("*.svg", filt)
        self.assertIn("*.dxf", filt)
        self.assertIn("Tous les Fichiers (*.*)", filt)
        self.assertTrue(filt.startswith("Tous les fichiers supportés"))

    def test_last_used_directory_prefers_current_file_then_recent(self):
        self.assertEqual(self.win._last_used_directory(), "")

        self.win.current_file_path = r"C:\Users\test\Documents\design.svg"
        self.assertEqual(
            self.win._last_used_directory(), r"C:\Users\test\Documents"
        )

        self.win.current_file_path = None
        self.root.file0 = r"C:\Users\other\recent.svg"
        self.assertEqual(self.win._last_used_directory(), r"C:\Users\other")

    # -- Console input: real command submission -----------------------------

    def test_console_input_submits_echoes_and_records_history(self):
        elements = self.root.elements
        input_box = self.win.findChildren(ConsoleLineEdit)[0]
        count_before = len(list(elements.elems()))

        input_box.setText("rect 0mm 0mm 5mm 5mm")
        QTest.keyClick(input_box, Qt.Key.Key_Return)
        self.kernel.process_queue()
        self.app.processEvents()

        self.assertEqual(input_box.text(), "")
        self.assertIn("> rect 0mm 0mm 5mm 5mm", self.win.console_output.toPlainText())
        self.assertEqual(len(list(elements.elems())), count_before + 1)

        QTest.keyClick(input_box, Qt.Key.Key_Up)
        self.assertEqual(input_box.text(), "rect 0mm 0mm 5mm 5mm")

    def test_console_input_ignores_empty_submission(self):
        input_box = self.win.findChildren(ConsoleLineEdit)[0]
        text_before = self.win.console_output.toPlainText()

        input_box.setText("   ")
        QTest.keyClick(input_box, Qt.Key.Key_Return)
        self.app.processEvents()

        self.assertEqual(self.win.console_output.toPlainText(), text_before)

    # -- Console output buffering (coalescing + ANSI stripping) -----------

    def test_console_output_coalesces_and_strips_ansi(self):
        # A verbose channel relayed into "console" (e.g. "channel open
        # usb" during a job) can fire many times a second -- messages are
        # buffered and flushed as one appendPlainText() call per short
        # window instead of one per message, or a widget update per
        # message would visibly lag the UI.
        before = self.win.console_output.toPlainText()

        self.win._on_console_output_received("\x1b[34mline one\x1b[0m")
        self.win._on_console_output_received("line two")
        self.win._on_console_output_received("\x1b[31mline three\x1b[0m")

        # Nothing appended to the visible widget yet -- still buffered.
        QTest.qWait(10)  # faster than the 50ms flush interval
        self.assertEqual(self.win.console_output.toPlainText(), before)

        QTest.qWait(100)  # past the flush interval
        after = self.win.console_output.toPlainText()
        tail = after[len(before):]
        self.assertIn("line one", tail)
        self.assertIn("line two", tail)
        self.assertIn("line three", tail)
        self.assertNotIn("\x1b", tail)
        self.assertNotIn("[34m", tail)

    # -- Select All / Deselect / Escape ------------------------------------

    def test_select_all_and_deselect(self):
        elements = self.root.elements
        self.root("rect 0mm 0mm 5mm 5mm\n")
        self.root("rect 10mm 0mm 5mm 5mm\n")
        self.kernel.process_queue()

        self.win._on_select_all()
        self.kernel.process_queue()
        self.app.processEvents()
        self.assertEqual(len(list(elements.elems(emphasized=True))), 2)

        self.win._on_escape_pressed()
        self.kernel.process_queue()
        self.app.processEvents()
        self.assertEqual(len(list(elements.elems(emphasized=True))), 0)

    def test_escape_cancels_in_progress_gesture_instead_of_deselecting(self):
        # The Edit menu's "Escape" shortcut cancels a draw/rubber-band/
        # move gesture in progress instead of deselecting -- matches
        # what a user pressing Escape mid-gesture actually expects.
        elements = self.root.elements
        self.root("rect 0mm 0mm 5mm 5mm\n")
        self.kernel.process_queue()
        self.win._on_select_all()
        self.kernel.process_queue()
        self.assertEqual(len(list(elements.elems(emphasized=True))), 1)

        self.win.canvas.set_draw_mode("rect")
        self.win.canvas._start_draw(QPoint(60, 60))
        self.assertIsNotNone(self.win.canvas._draw_start)

        self.win._on_escape_pressed()
        self.app.processEvents()

        self.assertIsNone(self.win.canvas._draw_start)
        # Selection must be untouched -- the gesture cancel took priority.
        self.assertEqual(len(list(elements.elems(emphasized=True))), 1)

    def test_cancel_in_progress_gesture_handles_rubber_band_and_move(self):
        # cancel_in_progress_gesture() (qt_canvas.py) has three branches
        # -- draw (covered above), rubber-band, and move -- plus the
        # "nothing active" False fallback (covered by
        # test_select_all_and_deselect, which relies on it to fall
        # through to a plain deselect). This covers the other two.
        elements = self.root.elements
        canvas = self.win.canvas
        self.root("rect 0mm 0mm 5mm 5mm\n")
        self.kernel.process_queue()

        canvas._start_rubber_band(QPoint(10, 10))
        self.assertIsNotNone(canvas._rb_start)
        self.assertTrue(canvas.cancel_in_progress_gesture())
        self.assertIsNone(canvas._rb_start)
        self.assertIsNone(canvas._rb_item)

        node = list(elements.elems())[-1]
        elements.set_emphasis([node])
        self.kernel.process_queue()
        canvas.render_elements()
        self.app.processEvents()
        item = next(it for it, n in canvas._item_to_node.items() if n is node)
        start_pos = item.pos()

        canvas._move_start_scene = canvas.mapToScene(QPoint(20, 20))
        canvas._move_last_scene = canvas._move_start_scene
        canvas._update_move(canvas.mapToScene(QPoint(50, 50)))  # a real drag
        self.assertTrue(canvas._move_active)
        self.assertNotEqual(item.pos(), start_pos)

        self.assertTrue(canvas.cancel_in_progress_gesture())
        self.assertIsNone(canvas._move_start_scene)
        # Nothing was committed to the node's real data yet -- only the
        # on-screen item moved, so cancelling snaps it back visually.
        self.assertAlmostEqual(item.pos().x(), start_pos.x(), delta=0.01)
        self.assertAlmostEqual(item.pos().y(), start_pos.y(), delta=0.01)
        self.assertTrue(node.emphasized)  # selection untouched by either cancel

        self.assertFalse(canvas.cancel_in_progress_gesture())  # idle -> False

    # -- Classify (Edit > Assigner les éléments aux opérations) -----------

    def test_classify_all_assigns_unassigned_element(self):
        # Added directly via elem_branch.add() with an explicit stroke
        # color (matching elements.default_stroke, what the "rect"
        # console command would naturally produce) to get a genuinely
        # unassigned-but-classifiable element -- one built with no
        # stroke at all has nothing for classify to match against.
        elements = self.root.elements
        node = elements.elem_branch.add(
            type="elem rect",
            x=0,
            y=0,
            width="5mm",
            height="5mm",
            stroke=elements.default_stroke,
        )
        self.kernel.process_queue()
        self.assertEqual(len(node._references), 0)

        self.win._on_classify_all()
        self.kernel.process_queue()
        self.app.processEvents()

        self.assertGreater(len(node._references), 0)

    def test_declassify_removes_selection_from_operations_without_deleting_it(self):
        # The reverse of Classifier Tout, but scoped to the current
        # SELECTION (matches what the bare "declassify" console command
        # defaults to with no pipe) rather than the whole document.
        elements = self.root.elements
        self.assertFalse(self.win._single_selection_actions[-1].isEnabled())

        node = elements.elem_branch.add(
            type="elem rect",
            x=0,
            y=0,
            width="5mm",
            height="5mm",
            stroke=elements.default_stroke,
        )
        self.kernel.process_queue()
        self.win._on_classify_all()
        self.kernel.process_queue()
        self.assertGreater(len(node._references), 0)

        elements.set_emphasis([node])
        self.kernel.process_queue()
        self.win._update_selection_dependent_actions()
        self.assertTrue(self.win._single_selection_actions[-1].isEnabled())

        self.win._on_declassify_selection()
        self.kernel.process_queue()
        self.app.processEvents()

        self.assertEqual(len(node._references), 0)
        self.assertIn(node, list(elements.elems()))  # element itself untouched

        # No selection -- a safe no-op.
        elements.set_emphasis(None)
        self.kernel.process_queue()
        self.win._on_declassify_selection()

    # -- Z-order (bring to front / send to back) --------------------------

    def test_bring_to_front_and_send_to_back_reorder_siblings(self):
        # The document's own child order among siblings already IS the
        # canvas paint order (render_elements() adds scene items in
        # elem_branch.flat() order, and non-emphasized items share one
        # Z-value) -- this confirms the actual sibling list order
        # changes, which is what drives the real visual stacking, not
        # just that the action runs without crashing.
        elements = self.root.elements
        node_a = elements.elem_branch.add(
            type="elem rect", x=0, y=0, width="5mm", height="5mm",
            stroke=elements.default_stroke,
        )
        node_b = elements.elem_branch.add(
            type="elem rect", x=10, y=0, width="5mm", height="5mm",
            stroke=elements.default_stroke,
        )
        node_c = elements.elem_branch.add(
            type="elem rect", x=20, y=0, width="5mm", height="5mm",
            stroke=elements.default_stroke,
        )
        self.kernel.process_queue()
        siblings = elements.elem_branch.children
        self.assertEqual(
            [n for n in siblings if n in (node_a, node_b, node_c)],
            [node_a, node_b, node_c],
        )

        # Bring the FIRST node to front -> it must now be LAST.
        elements.set_emphasis([node_a])
        self.win._on_bring_to_front()
        self.kernel.process_queue()
        siblings = elements.elem_branch.children
        self.assertEqual(
            [n for n in siblings if n in (node_a, node_b, node_c)],
            [node_b, node_c, node_a],
        )

        # Send that same node back to the back -> it must now be FIRST.
        elements.set_emphasis([node_a])
        self.win._on_send_to_back()
        self.kernel.process_queue()
        siblings = elements.elem_branch.children
        self.assertEqual(
            [n for n in siblings if n in (node_a, node_b, node_c)],
            [node_a, node_b, node_c],
        )

        # Already at the front/back -- a safe no-op, not a crash.
        elements.set_emphasis([node_a])
        self.win._on_send_to_back()
        siblings = elements.elem_branch.children
        self.assertEqual(
            [n for n in siblings if n in (node_a, node_b, node_c)],
            [node_a, node_b, node_c],
        )

        # No selection -- a safe no-op.
        elements.set_emphasis(None)
        self.win._on_bring_to_front()
        self.win._on_send_to_back()

    def test_raise_and_lower_one_step_swap_adjacent_siblings(self):
        # One-step version of bring-to-front/send-to-back above -- swaps
        # a node with its immediate neighbor rather than moving it all
        # the way to either end.
        elements = self.root.elements
        node_a = elements.elem_branch.add(
            type="elem rect", x=0, y=0, width="5mm", height="5mm",
            stroke=elements.default_stroke,
        )
        node_b = elements.elem_branch.add(
            type="elem rect", x=10, y=0, width="5mm", height="5mm",
            stroke=elements.default_stroke,
        )
        node_c = elements.elem_branch.add(
            type="elem rect", x=20, y=0, width="5mm", height="5mm",
            stroke=elements.default_stroke,
        )
        self.kernel.process_queue()

        def order():
            return [
                n for n in elements.elem_branch.children
                if n in (node_a, node_b, node_c)
            ]

        self.assertEqual(order(), [node_a, node_b, node_c])

        # Raise the MIDDLE node -> swaps with its next neighbor (C).
        elements.set_emphasis([node_b])
        self.win._on_raise_one()
        self.kernel.process_queue()
        self.assertEqual(order(), [node_a, node_c, node_b])

        # Lower it back down -> swaps with C again, restoring order.
        elements.set_emphasis([node_b])
        self.win._on_lower_one()
        self.kernel.process_queue()
        self.assertEqual(order(), [node_a, node_b, node_c])

        # Already frontmost/backmost -- safe no-ops.
        elements.set_emphasis([node_c])
        self.win._on_raise_one()
        self.assertEqual(order(), [node_a, node_b, node_c])

        elements.set_emphasis([node_a])
        self.win._on_lower_one()
        self.assertEqual(order(), [node_a, node_b, node_c])

        # No selection -- a safe no-op.
        elements.set_emphasis(None)
        self.win._on_raise_one()
        self.win._on_lower_one()

    def test_smart_vectorize_dialog_traces_and_positions_image(self):
        # vectorize_bitmap_to_bezier() works in pixel space; the handler
        # must scale+translate each new node's matrix onto the SOURCE
        # image's own bed position/size, not leave it sitting at raw
        # pixel coordinates near the origin.
        from PIL import Image, ImageDraw
        from madgrav.core.node.elem_image import ImageNode
        from madgrav.core.units import UNITS_PER_MM
        from madgrav.svgelements import Matrix

        img = Image.new("L", (100, 50), 255)
        draw = ImageDraw.Draw(img)
        draw.rectangle((20, 10, 80, 40), fill=0)

        target_x_mm, target_y_mm, target_w_mm, target_h_mm = 30.0, 40.0, 20.0, 10.0
        matrix = Matrix.scale(
            target_w_mm * UNITS_PER_MM / 100.0, target_h_mm * UNITS_PER_MM / 50.0
        )
        matrix.post_translate(target_x_mm * UNITS_PER_MM, target_y_mm * UNITS_PER_MM)
        image_node = ImageNode(image=img, matrix=matrix)
        self.root.elements.elem_branch.add_node(image_node)
        self.root.elements.set_emphasis([image_node])
        self.kernel.process_queue()

        def fake_exec(dlg_self):
            dlg_self.spin_threshold.setValue(128)
            return QDialog.DialogCode.Accepted

        # The closing QMessageBox.information(...) is itself a QDialog
        # subclass, so patching QDialog.exec alone would route it through
        # fake_exec too (which expects a spin_threshold that a message box
        # doesn't have) -- patch it separately as a no-op, matching the
        # setUp()-documented convention for this test file.
        QMessageBox.information = lambda *a, **kw: None
        with patch.object(QDialog, "exec", fake_exec):
            self.win._on_smart_vectorize_dialog()
        self.kernel.process_queue()

        traced = [
            n for n in self.root.elements.elem_branch.children
            if getattr(n, "label", None) == "Trace Vectorielle"
        ]
        self.assertGreaterEqual(len(traced), 1)
        bbox = traced[0].bounds
        self.assertIsNotNone(bbox)
        img_bounds_x0 = target_x_mm * UNITS_PER_MM
        img_bounds_x1 = (target_x_mm + target_w_mm) * UNITS_PER_MM
        img_bounds_y0 = target_y_mm * UNITS_PER_MM
        img_bounds_y1 = (target_y_mm + target_h_mm) * UNITS_PER_MM
        # The traced contour must land within (a small tolerance around)
        # the image's own bed rectangle, not near the pixel-space origin.
        self.assertGreaterEqual(bbox[0], img_bounds_x0 - 1.0)
        self.assertLessEqual(bbox[2], img_bounds_x1 + 1.0)
        self.assertGreaterEqual(bbox[1], img_bounds_y0 - 1.0)
        self.assertLessEqual(bbox[3], img_bounds_y1 + 1.0)

    def test_node_editor_dialog_handler_moves_a_node_and_updates_bounds(self):
        # _on_node_editor_dialog wires NodeEditorDialog.on_changed to call
        # path_node.altered() -- verify the document's own cached bounds
        # (not just the dialog's own list) actually reflect a mutation
        # made through the dialog, the same stale-cache class of bug as
        # the array-generator fix earlier this session.
        from madgrav.core.units import UNITS_PER_MM
        from madgrav.svgelements import Path

        path = Path()
        path.move(complex(0, 0))
        path.line(complex(50 * UNITS_PER_MM, 0))
        path.line(complex(50 * UNITS_PER_MM, 50 * UNITS_PER_MM))
        path.closed()
        elements = self.root.elements
        path_node = elements.elem_branch.add(type="elem path", path=path, stroke=elements.default_stroke)
        path_node.altered()
        original_bounds = path_node.bounds  # forces caching
        elements.set_emphasis([path_node])
        self.kernel.process_queue()

        def fake_exec(dlg_self):
            dlg_self.list_nodes.setCurrentRow(1)
            dlg_self.spin_x.setValue(200.0)
            dlg_self.spin_y.setValue(0.0)
            dlg_self._on_move()
            return QDialog.DialogCode.Accepted

        with patch.object(QDialog, "exec", fake_exec):
            self.win._on_node_editor_dialog()
        self.kernel.process_queue()

        new_bounds = path_node.bounds
        self.assertNotEqual(new_bounds, original_bounds, "moving a node through the dialog must update the document's cached bounds")
        self.assertGreater(new_bounds[2] - new_bounds[0], 199.0 * UNITS_PER_MM)

    def test_galvo_hatch_dialog_handler_adds_hatch_pattern_for_selected_path(self):
        from madgrav.core.units import UNITS_PER_MM
        from madgrav.svgelements import Path

        w = 40.0 * UNITS_PER_MM
        path = Path()
        path.move(complex(0, 0))
        path.line(complex(w, 0))
        path.line(complex(w, w))
        path.line(complex(0, w))
        path.closed()
        elements = self.root.elements
        path_node = elements.elem_branch.add(type="elem path", path=path, stroke=elements.default_stroke)
        path_node.altered()
        elements.set_emphasis([path_node])
        self.kernel.process_queue()
        count_before = len(list(elements.elems()))

        def fake_exec(dlg_self):
            dlg_self.combo_mode.setCurrentText("cross")
            dlg_self.spin_angle.setValue(30.0)
            dlg_self.spin_spacing.setValue(2.0)
            return QDialog.DialogCode.Accepted

        with patch.object(QDialog, "exec", fake_exec):
            self.win._on_galvo_hatch_dialog()
        self.kernel.process_queue()

        hatched = [
            n for n in elements.elem_branch.children
            if getattr(n, "label", None) == "Hachurage Galvo"
        ]
        self.assertEqual(len(hatched), 1)
        self.assertEqual(len(list(elements.elems())), count_before + 1)
        hbbox = hatched[0].bounds
        self.assertIsNotNone(hbbox)
        self.assertGreater(hbbox[2] - hbbox[0], 1.0)
        self.assertGreater(hbbox[3] - hbbox[1], 1.0)

    def test_core_editing_actions_work_with_a_fresh_multi_selection(self):
        # Same bug class as frame/nesting above, batch-fixed across every
        # handler in this file that used elements.first_emphasized is
        # None as a plain "anything selected?" gate -- representative
        # spot check on two of them (lock, duplicate) with a FRESH
        # multi-selection (no prior single-click), the exact scenario
        # that used to collapse first_emphasized to None and silently
        # no-op the whole action.
        elements = self.root.elements
        self.root("rect 0mm 0mm 10mm 10mm\n")
        self.root("rect 20mm 0mm 10mm 10mm\n")
        self.kernel.process_queue()
        r1, r2 = list(elements.elems())[-2:]

        elements.set_emphasis([r1, r2])
        self.kernel.process_queue()
        self.win._on_lock(True)
        self.assertTrue(r1.lock)
        self.assertTrue(r2.lock)

        elements.set_emphasis([r1, r2])
        self.kernel.process_queue()
        count_before = len(list(elements.elems()))
        self.win._on_duplicate()
        self.kernel.process_queue()
        self.assertGreater(len(list(elements.elems())), count_before)

    def test_frame_selection_draws_a_rect_around_the_bounding_box(self):
        # "frame" is a pre-existing kernel console command (shapes.py)
        # that draws a real rect around the selection's bounding box --
        # never wired to the Qt UI before. No selection must give clear
        # feedback (status bar), not a silent no-op.
        elements = self.root.elements
        self.root("rect 0mm 0mm 10mm 10mm\n")
        self.root("rect 30mm 0mm 10mm 10mm\n")
        self.kernel.process_queue()
        r1, r2 = list(elements.elems())[-2:]

        elements.set_emphasis(None)
        self.kernel.process_queue()
        self.win._on_frame_selection()
        self.assertIn("sélectionner", self.win.status_bar.currentMessage().lower())

        elements.set_emphasis([r1, r2])
        self.kernel.process_queue()
        count_before = len(list(elements.elems()))
        QInputDialog.getDouble = staticmethod(lambda *a, **k: (5.0, True))
        self.win._on_frame_selection()
        self.kernel.process_queue()

        framed = [n for n in elements.elem_branch.children if str(getattr(n, "label", "")).startswith("Frame around")]
        self.assertEqual(len(framed), 1, f"console_output: {self.win.console_output.toPlainText()!r}")
        self.assertEqual(len(list(elements.elems())), count_before + 1)
        fbbox = framed[0].bounds
        self.assertIsNotNone(fbbox)
        # 5mm margin on both sides of a combined 0..40mm-wide selection.
        from madgrav.core.units import UNITS_PER_MM
        self.assertLess(fbbox[0], -1.0 * UNITS_PER_MM)
        self.assertGreater(fbbox[2], 41.0 * UNITS_PER_MM)

        # A cancelled dialog (ok=False) must not add a frame.
        QInputDialog.getDouble = staticmethod(lambda *a, **k: (5.0, False))
        count_before2 = len(list(elements.elems()))
        self.win._on_frame_selection()
        self.assertEqual(len(list(elements.elems())), count_before2)

    def test_nesting_dialog_handler_works_with_a_fresh_multi_selection(self):
        # Same class of bug as frame selection above: nest_elements is
        # fundamentally a multi-shape operation, but the handler used to
        # gate on elements.first_emphasized is None -- which is also None
        # right after a single set_emphasis([a, b, ...]) call with no
        # prior single-element selection (confirmed: this is exactly the
        # "no sense in a 'first' when all are equal" case in elements.py).
        # A freshly-drawn rubber-band multi-select hits this path.
        elements = self.root.elements
        self.root("rect 0mm 0mm 10mm 10mm\n")
        self.root("rect 20mm 0mm 10mm 10mm\n")
        self.kernel.process_queue()
        r1, r2 = list(elements.elems())[-2:]

        elements.set_emphasis([r1, r2])
        self.kernel.process_queue()

        def fake_exec(dlg_self):
            dlg_self.spin_sheet_w.setValue(300.0)
            dlg_self.spin_sheet_h.setValue(200.0)
            dlg_self.spin_margin.setValue(2.0)
            return QDialog.DialogCode.Accepted

        # The closing QMessageBox.information(...) is itself a QDialog
        # subclass -- same reasoning as test_smart_vectorize_dialog_
        # traces_and_positions_image, patch it as a no-op separately.
        QMessageBox.information = lambda *a, **kw: None
        with patch.object(QDialog, "exec", fake_exec):
            self.win._on_nesting_dialog()
        self.kernel.process_queue()

        self.assertNotIn("sélectionner", self.win.status_bar.currentMessage().lower())

    # -- Load file over an already-rendered document ---------------------

    def test_load_file_merges_into_already_rendered_document(self):
        # elements.load() MERGES into the current document rather than
        # replacing it -- confirms canvas.render_elements() (called by
        # every _load_file() caller right after) correctly keeps the
        # canvas's own graphics-item tracking in sync with the merged
        # kernel-side node count when the canvas already had real,
        # rendered elements from BEFORE the load, not just an empty
        # scene. Same "verify both sides" lesson as the init_scene()
        # crash and the New Project canvas-cleanup test above.
        elements = self.root.elements
        tmpdir = tempfile.mkdtemp(prefix="madgrav_load_test_")
        try:
            svg_path = os.path.join(tmpdir, "other.svg")
            self.root("rect 50mm 50mm 5mm 5mm\n")
            self.root("circle 60mm 60mm 3mm\n")
            self.kernel.process_queue()
            elements.save(svg_path)

            elements.clear_all(ops_too=True)
            self.root("rect 0mm 0mm 5mm 5mm\n")
            self.kernel.process_queue()
            self.win.canvas.render_elements()
            self.app.processEvents()
            self.assertEqual(len(self.win.canvas._element_items), 1)

            ok = self.win._load_file(svg_path)
            self.win.canvas.render_elements()
            self.app.processEvents()

            self.assertTrue(ok)
            elem_count = len(list(elements.elems()))
            self.assertGreaterEqual(elem_count, 3)  # 1 original + 2 loaded
            self.assertEqual(len(self.win.canvas._element_items), elem_count)
        finally:
            import shutil

            shutil.rmtree(tmpdir, ignore_errors=True)

    # -- Recent Files ---------------------------------------------------

    def test_recent_files_order_dedup_and_stale_removal(self):
        # context.file0..19 are kernel-profile-scoped (this test's own
        # throwaway bootstrap() profile), not the real OS-level QSettings
        # store used for window geometry -- safe to exercise freely here.
        tmpdir = tempfile.mkdtemp(prefix="madgrav_recent_test_")
        try:
            path_a = os.path.join(tmpdir, "a.svg")
            path_b = os.path.join(tmpdir, "b.svg")
            for p in (path_a, path_b):
                with open(p, "w") as f:
                    f.write("<svg></svg>")

            self.win._on_clear_recent_files()
            self.assertEqual(self.win.recent_menu.actions(), [])

            self.win._add_to_recent_files(path_a)
            self.win._add_to_recent_files(path_b)
            # Most-recent-first.
            self.assertEqual(self.root.file0, path_b)
            self.assertEqual(self.root.file1, path_a)

            # Re-adding an existing entry moves it to front, no duplicate.
            self.win._add_to_recent_files(path_a)
            self.assertEqual(self.root.file0, path_a)
            self.assertEqual(self.root.file1, path_b)

            # Opening a since-deleted file fails to load and auto-drops
            # it from the list instead of leaving a permanently broken
            # entry the user would keep clicking on.
            os.remove(path_b)
            self.win._on_open_recent_file(path_b)
            self.app.processEvents()
            remaining = [
                getattr(self.root, f"file{i}", None) for i in range(20)
            ]
            remaining = [r for r in remaining if r]
            self.assertNotIn(path_b, remaining)
            self.assertIn(path_a, remaining)

            self.win._on_clear_recent_files()
            self.assertEqual(self.win.recent_menu.actions(), [])
        finally:
            import shutil

            shutil.rmtree(tmpdir, ignore_errors=True)

    def test_recent_files_menu_actions_pass_the_correct_distinct_path(self):
        # Same closure-capture pattern as the align/geometry menus (
        # lambda checked=False, f=fname: self._on_open_recent_file(f) in
        # _populate_recent_menu) -- verified here by triggering each real
        # recent-file QAction and confirming it opens ITS OWN path, not
        # whichever file happened to be last in the loop.
        tmpdir = tempfile.mkdtemp(prefix="madgrav_recent_trigger_test_")
        try:
            path_a = os.path.join(tmpdir, "a.svg")
            path_b = os.path.join(tmpdir, "b.svg")
            for p in (path_a, path_b):
                with open(p, "w") as f:
                    f.write("<svg></svg>")

            self.win._on_clear_recent_files()
            self.win._add_to_recent_files(path_a)
            self.win._add_to_recent_files(path_b)

            original = self.win._on_open_recent_file
            try:
                calls = []
                self.win._on_open_recent_file = lambda p: calls.append(p)
                actions = [
                    a
                    for a in self.win.recent_menu.actions()
                    if a.toolTip() in (path_a, path_b)
                ]
                self.assertEqual(len(actions), 2)
                for act in actions:
                    expected_path = act.toolTip()
                    act.trigger()
                    self.assertEqual(calls[-1], expected_path)
            finally:
                self.win._on_open_recent_file = original
        finally:
            import shutil

            shutil.rmtree(tmpdir, ignore_errors=True)

    # -- Pause / emergency-stop guards -------------------------------------

    def test_pause_and_stop_warn_without_active_device(self):
        # "pause"/"estop" are registered per-device (grbl/balormk/
        # lihuiyu/ruida/moshi each add their own) -- with no active
        # device they aren't registered commands at all, and the kernel
        # reports that via the console channel rather than raising, so
        # _run_console would otherwise silently report "success" with
        # nothing actually sent. bootstrap() always activates a "dummy"
        # device (which _has_active_device() counts as active, same as
        # a real one), so the no-device branch is stubbed directly here
        # rather than trying to reach an unreachable-in-this-harness
        # kernel state.
        warned = []
        QMessageBox.warning = staticmethod(lambda *a, **k: warned.append(1))
        original = self.win._has_active_device
        self.win._has_active_device = lambda: False
        try:
            self.win._on_pause()
            self.assertEqual(warned, [1])
            warned.clear()

            self.win._on_stop()
            self.assertEqual(warned, [1])
        finally:
            self.win._has_active_device = original

    def test_pause_and_stop_dispatch_with_active_device(self):
        self._add_grbl_device()
        warned = []
        QMessageBox.warning = staticmethod(lambda *a, **k: warned.append(1))

        self.win._on_pause()
        self.assertEqual(warned, [])
        self.assertIn("pause", self.win.console_output.toPlainText())

        self.win._on_stop()
        self.assertEqual(warned, [])
        self.assertIn("estop", self.win.console_output.toPlainText())

    # -- Home / Frame ---------------------------------------------------------

    def test_home_and_frame_warn_without_active_device(self):
        # Same reasoning as test_pause_and_stop_warn_without_active_device
        # above: bootstrap() always activates a "dummy" device, so the
        # no-device branch is stubbed directly rather than trying to
        # reach an unreachable-in-this-harness kernel state.
        warned = []
        QMessageBox.warning = staticmethod(lambda *a, **k: warned.append(1))
        original = self.win._has_active_device
        self.win._has_active_device = lambda: False
        try:
            self.win.status_bar.showMessage("")
            self.win._on_home()
            self.assertEqual(warned, [1])
            self.assertEqual(self.win.status_bar.currentMessage(), "")
            warned.clear()

            self.win.status_bar.showMessage("")
            self.win._on_frame()
            self.assertEqual(warned, [1])
            self.assertEqual(self.win.status_bar.currentMessage(), "")
        finally:
            self.win._has_active_device = original

    def test_home_and_frame_dispatch_with_active_device(self):
        warned = []
        QMessageBox.warning = staticmethod(lambda *a, **k: warned.append(1))

        self.win._on_home()
        self.assertEqual(warned, [])
        self.assertIn("home", self.win.console_output.toPlainText())

        self.win._on_frame()
        self.assertEqual(warned, [])
        self.assertIn("trace quick", self.win.console_output.toPlainText())

    def test_machine_control_buttons_are_wired_to_the_right_handler(self):
        # Every test elsewhere in this file exercises _on_home/_on_frame/
        # _on_pause/_on_stop/_on_start/_on_toggle_arm by calling them
        # directly -- none had ever clicked the real toolbar buttons
        # (btn_orig/btn_frame/btn_pause/btn_stop/btn_start/btn_arm),
        # despite these being the most safety-critical controls in the
        # whole app. A wrong .clicked.connect() target here (a real risk
        # given how many near-identical buttons this toolbar has) would
        # still pass every other test in this file while leaving the
        # actual button silently inert for a real user.
        self.assertFalse(self.win._laser_armed())
        QTest.mouseClick(self.win.btn_arm, Qt.MouseButton.LeftButton)
        self.assertTrue(self.win._laser_armed())

        # Armed now, but nothing burnable -- _on_start()'s own next gate.
        shown = []
        QMessageBox.information = staticmethod(lambda *a, **k: shown.append(1))
        QTest.mouseClick(self.win.btn_start, Qt.MouseButton.LeftButton)
        self.assertEqual(shown, [1])

        QTest.mouseClick(self.win.btn_orig, Qt.MouseButton.LeftButton)
        self.assertIn("home", self.win.console_output.toPlainText())

        QTest.mouseClick(self.win.btn_frame, Qt.MouseButton.LeftButton)
        self.assertIn("trace quick", self.win.console_output.toPlainText())

        QTest.mouseClick(self.win.btn_pause, Qt.MouseButton.LeftButton)
        self.assertIn("pause", self.win.console_output.toPlainText())

        QTest.mouseClick(self.win.btn_stop, Qt.MouseButton.LeftButton)
        self.assertIn("estop", self.win.console_output.toPlainText())

    # -- Duplicate / Copy / Cut / Paste ------------------------------------

    def test_paste_action_reflects_real_clipboard_state(self):
        # "Coller" doesn't depend on the current selection (unlike Copy/
        # Cut/Delete) -- it depends on whether the clipboard actually has
        # anything, confirmed against elements._clipboard directly rather
        # than assuming an empty starting state (a persisted test
        # profile could already have clipboard content from an earlier
        # run, same class of persistence found elsewhere this session).
        elements = self.root.elements
        self.win._update_paste_action()
        destination = getattr(elements, "_clipboard_default", None)
        real_filled = bool(
            destination is not None and len(elements._clipboard.get(destination, [])) > 0
        )
        self.assertEqual(self.win.act_paste.isEnabled(), real_filled)

        self.root("rect 0mm 0mm 5mm 5mm\n")
        self.kernel.process_queue()
        node = list(elements.elems())[-1]
        elements.set_emphasis([node])
        self.kernel.process_queue()

        self.win._on_copy()
        self.win._update_paste_action()
        self.assertTrue(self.win.act_paste.isEnabled())

    def test_duplicate_adds_a_new_element(self):
        elements = self.root.elements
        self.root("rect 0mm 0mm 5mm 5mm\n")
        self.kernel.process_queue()
        node = list(elements.elems())[-1]
        elements.set_emphasis([node])
        self.kernel.process_queue()

        count_before = len(list(elements.elems()))
        self.win._on_duplicate()
        self.kernel.process_queue()
        self.app.processEvents()

        self.assertEqual(len(list(elements.elems())), count_before + 1)
        self.assertTrue(any(e is not node for e in elements.elems()))

    def test_lock_disables_position_panel_and_unlock_restores_it(self):
        elements = self.root.elements
        self.root("rect 0mm 0mm 5mm 5mm\n")
        self.kernel.process_queue()
        node = list(elements.elems())[-1]
        elements.set_emphasis([node])
        self.kernel.process_queue()
        self.win._update_position_panel()
        self.assertFalse(bool(node.lock))
        self.assertTrue(self.win._position_panel.isEnabled())

        self.win._on_lock(True)
        self.assertTrue(node.lock)
        # _update_position_panel() disables editing for a locked node --
        # without the explicit refresh call in _on_lock() this wouldn't
        # take effect until the selection changed again, letting the
        # user edit X/Y on something they just locked.
        self.assertFalse(self.win._position_panel.isEnabled())

        self.win._on_lock(False)
        self.assertFalse(node.lock)
        self.assertTrue(self.win._position_panel.isEnabled())

    def test_lock_with_no_selection_is_a_safe_no_op(self):
        elements = self.root.elements
        elements.set_emphasis(None)
        self.kernel.process_queue()
        self.win._on_lock(True)  # must not raise with nothing selected

    def test_deselect_all_clears_emphasis_and_selection_ui(self):
        elements = self.root.elements
        self.root("rect 0mm 0mm 5mm 5mm\n")
        self.kernel.process_queue()
        node = list(elements.elems())[-1]
        elements.set_emphasis([node])
        self.kernel.process_queue()
        self.assertIsNotNone(elements.first_emphasized)

        self.win._on_deselect_all()
        self.app.processEvents()

        self.assertIsNone(elements.first_emphasized)
        self.assertTrue(all(not a.isEnabled() for a in self.win._single_selection_actions))

    def test_copy_then_paste_creates_offset_copy(self):
        from madgrav.core.units import UNITS_PER_MM

        elements = self.root.elements
        self.root("rect 0mm 0mm 5mm 5mm\n")
        self.kernel.process_queue()
        node = list(elements.elems())[-1]
        elements.set_emphasis([node])
        self.kernel.process_queue()

        count_before = len(list(elements.elems()))
        self.win._on_copy()
        self.win._on_paste()
        self.kernel.process_queue()
        self.app.processEvents()

        self.assertEqual(len(list(elements.elems())), count_before + 1)
        pasted = list(elements.elems(emphasized=True))
        self.assertEqual(len(pasted), 1)
        # A small offset so the pasted copy doesn't land exactly on top
        # of the original and look like nothing happened.
        b_orig = node.bounds
        b_pasted = pasted[0].bounds
        dx = (b_pasted[0] - b_orig[0]) / UNITS_PER_MM
        dy = (b_pasted[1] - b_orig[1]) / UNITS_PER_MM
        self.assertAlmostEqual(dx, 5.0, delta=0.5)
        self.assertAlmostEqual(dy, 5.0, delta=0.5)

    def test_cut_removes_element_and_paste_restores_it(self):
        elements = self.root.elements
        self.root("rect 0mm 0mm 5mm 5mm\n")
        self.kernel.process_queue()
        node = list(elements.elems())[-1]
        elements.set_emphasis([node])
        self.kernel.process_queue()

        count_before = len(list(elements.elems()))
        self.win._on_cut()
        self.kernel.process_queue()
        self.app.processEvents()
        self.assertEqual(len(list(elements.elems())), count_before - 1)

        self.win._on_paste()
        self.kernel.process_queue()
        self.app.processEvents()
        self.assertEqual(len(list(elements.elems())), count_before)

    # -- Save / New project -------------------------------------------------

    def test_save_to_writes_real_file_and_clears_dirty(self):
        self.root("rect 0mm 0mm 5mm 5mm\n")
        self.kernel.process_queue()

        tmpdir = tempfile.mkdtemp(prefix="madgrav_save_test_")
        try:
            svg_path = os.path.join(tmpdir, "out.svg")
            self.win._dirty = True
            self.win._save_to(svg_path)
            self.app.processEvents()

            self.assertTrue(os.path.exists(svg_path))
            self.assertEqual(self.win.current_file_path, svg_path)
            self.assertFalse(self.win._dirty)

            # save() returns False (not an exception) for an
            # unrecognized extension -- must warn and leave state
            # untouched rather than silently reporting success.
            warned = []
            QMessageBox.warning = staticmethod(lambda *a, **k: warned.append(1))
            bad_path = os.path.join(tmpdir, "out.txt")
            self.win.current_file_path = None
            self.win._save_to(bad_path)
            self.app.processEvents()

            self.assertEqual(warned, [1])
            self.assertIsNone(self.win.current_file_path)
            self.assertFalse(os.path.exists(bad_path))
        finally:
            import shutil

            shutil.rmtree(tmpdir, ignore_errors=True)

    def test_save_prompts_only_when_no_current_path_then_reuses_it(self):
        # _on_save() must only pop the file dialog the first time (no
        # current_file_path yet) -- a subsequent save should reuse that
        # path silently, the whole point of "Save" vs "Save As". Static
        # QFileDialog.getSaveFileName is monkeypatched (not restored via
        # tearDown, unlike QMessageBox/QMenu -- no other test in this
        # file calls a save/open dialog after this one runs).
        self.root("rect 0mm 0mm 10mm 10mm\n")
        self.kernel.process_queue()

        tmpdir = tempfile.mkdtemp(prefix="madgrav_save_test_")
        try:
            path_a = os.path.join(tmpdir, "a.svg")
            calls = []
            QFileDialog.getSaveFileName = staticmethod(
                lambda *a, **k: (calls.append(1), (path_a, ""))[1]
            )

            self.assertFalse(self.win.current_file_path)
            self.win._on_save()
            self.app.processEvents()

            self.assertEqual(len(calls), 1)
            self.assertEqual(self.win.current_file_path, path_a)
            self.assertTrue(os.path.exists(path_a))

            calls.clear()
            self.win._on_save()
            self.app.processEvents()
            self.assertEqual(calls, [])
        finally:
            import shutil

            shutil.rmtree(tmpdir, ignore_errors=True)

    def test_save_as_always_prompts_and_a_cancelled_dialog_is_a_no_op(self):
        self.root("rect 0mm 0mm 10mm 10mm\n")
        self.kernel.process_queue()

        tmpdir = tempfile.mkdtemp(prefix="madgrav_save_test_")
        try:
            path_a = os.path.join(tmpdir, "a.svg")
            self.win._save_to(path_a)
            self.app.processEvents()
            self.assertEqual(self.win.current_file_path, path_a)

            path_b = os.path.join(tmpdir, "b.svg")
            calls = []
            QFileDialog.getSaveFileName = staticmethod(
                lambda *a, **k: (calls.append(1), (path_b, ""))[1]
            )
            self.win._on_save_as()
            self.app.processEvents()
            self.assertEqual(len(calls), 1)
            self.assertEqual(self.win.current_file_path, path_b)

            # An empty path (dialog cancelled) must leave everything as-is.
            calls.clear()
            QFileDialog.getSaveFileName = staticmethod(
                lambda *a, **k: (calls.append(1), ("", ""))[1]
            )
            self.win._on_save_as()
            self.app.processEvents()
            self.assertEqual(len(calls), 1)
            self.assertEqual(self.win.current_file_path, path_b)
        finally:
            import shutil

            shutil.rmtree(tmpdir, ignore_errors=True)

    def test_open_file_loads_document_and_a_cancelled_dialog_is_a_no_op(self):
        elements = self.root.elements
        count_before = len(list(elements.elems()))

        tmpdir = tempfile.mkdtemp(prefix="madgrav_open_test_")
        try:
            svg_path = os.path.join(tmpdir, "in.svg")
            with open(svg_path, "w") as f:
                f.write(
                    '<svg xmlns="http://www.w3.org/2000/svg" '
                    'width="10mm" height="10mm">'
                    '<rect x="0" y="0" width="10mm" height="10mm"/></svg>'
                )
            calls = []
            QFileDialog.getOpenFileName = staticmethod(
                lambda *a, **k: (calls.append(1), (svg_path, ""))[1]
            )

            self.win._on_open_file()
            self.app.processEvents()
            self.kernel.process_queue()

            self.assertEqual(len(calls), 1)
            self.assertGreater(len(list(elements.elems())), count_before)

            # An empty path (dialog cancelled) must leave the document
            # untouched, not e.g. attempt to load an empty filename.
            calls.clear()
            QFileDialog.getOpenFileName = staticmethod(
                lambda *a, **k: (calls.append(1), ("", ""))[1]
            )
            count_before2 = len(list(elements.elems()))
            self.win._on_open_file()
            self.app.processEvents()
            self.assertEqual(len(calls), 1)
            self.assertEqual(len(list(elements.elems())), count_before2)
        finally:
            import shutil

            shutil.rmtree(tmpdir, ignore_errors=True)

    def test_new_project_prompts_and_clears_on_confirm(self):
        # Checks both the kernel-side document AND the canvas's own
        # graphics-item tracking (_element_items/_item_to_node) --
        # exactly the two that fell out of sync in the init_scene()
        # crash fixed a couple of cycles ago. render_elements() must
        # correctly drop every graphics item for a now-cleared document,
        # not just the kernel-side node list.
        elements = self.root.elements
        self.root("rect 0mm 0mm 5mm 5mm\n")
        self.root("circle 10mm 10mm 3mm\n")
        self.kernel.process_queue()
        self.win.canvas.render_elements()
        self.win.current_file_path = "/some/prior/path.svg"
        count_before = len(list(elements.elems()))
        self.assertGreater(count_before, 0)
        self.assertEqual(len(self.win.canvas._element_items), count_before)

        QMessageBox.question = staticmethod(
            lambda *a, **k: QMessageBox.StandardButton.No
        )
        self.win._on_new()
        self.app.processEvents()
        self.assertEqual(len(list(elements.elems())), count_before)

        QMessageBox.question = staticmethod(
            lambda *a, **k: QMessageBox.StandardButton.Yes
        )
        self.win._on_new()
        self.app.processEvents()
        self.assertEqual(len(list(elements.elems())), 0)
        self.assertIsNone(self.win.current_file_path)
        self.assertEqual(self.win.canvas._element_items, [])
        self.assertEqual(self.win.canvas._item_to_node, {})

    # -- Group / Ungroup ----------------------------------------------------

    def test_group_and_ungroup_round_trip(self):
        elements = self.root.elements
        self.root("rect 0mm 0mm 5mm 5mm\n")
        self.root("rect 10mm 0mm 5mm 5mm\n")
        self.kernel.process_queue()
        r1, r2 = list(elements.elems())[-2:]
        elements.set_emphasis([r1, r2])
        self.kernel.process_queue()
        self.assertNotEqual(r1.parent.type, "group")

        self.win._on_group()
        self.kernel.process_queue()
        self.app.processEvents()

        self.assertIs(r1.parent, r2.parent)
        self.assertEqual(r1.parent.type, "group")

        group_node = r1.parent
        elements.set_emphasis([group_node])
        self.kernel.process_queue()

        self.win._on_ungroup()
        self.kernel.process_queue()
        self.app.processEvents()

        self.assertNotEqual(r1.parent.type, "group")
        self.assertNotEqual(r2.parent.type, "group")

    # -- Rotate / Mirror --------------------------------------------------

    def test_rotate_90_swaps_bounding_box_dimensions(self):
        from madgrav.core.units import UNITS_PER_MM

        elements = self.root.elements
        self.root("rect 0mm 0mm 20mm 10mm\n")
        self.kernel.process_queue()
        node = list(elements.elems())[-1]
        elements.set_emphasis([node])
        self.kernel.process_queue()

        b = node.bounds
        self.assertAlmostEqual((b[2] - b[0]) / UNITS_PER_MM, 20.0, delta=0.1)
        self.assertAlmostEqual((b[3] - b[1]) / UNITS_PER_MM, 10.0, delta=0.1)

        self.win._on_rotate(90)
        self.kernel.process_queue()
        self.app.processEvents()

        b2 = node.bounds
        self.assertAlmostEqual((b2[2] - b2[0]) / UNITS_PER_MM, 10.0, delta=0.5)
        self.assertAlmostEqual((b2[3] - b2[1]) / UNITS_PER_MM, 20.0, delta=0.5)

    def test_mirror_flips_transform_determinant_sign(self):
        # Mirroring is a negative scale about the selection's own center
        # (madgrav's "scale" command) -- a reflection, unlike a plain
        # scale, flips the orientation, which shows up as the transform
        # matrix's determinant changing sign. This holds for any shape
        # (unlike checking bounding-box coordinates, which wouldn't
        # change at all for a symmetric shape like a rect mirrored about
        # its own center).
        elements = self.root.elements
        self.root("rect 0mm 0mm 20mm 10mm\n")
        self.kernel.process_queue()
        node = list(elements.elems())[-1]
        elements.set_emphasis([node])
        self.kernel.process_queue()

        m = node.matrix
        det_before = m.a * m.d - m.b * m.c
        self.assertGreater(det_before, 0)

        self.win._on_mirror(-1, 1)
        self.kernel.process_queue()
        self.app.processEvents()

        m2 = node.matrix
        det_after = m2.a * m2.d - m2.b * m2.c
        self.assertLess(det_after, 0)

    # -- Position panel: editing X/Y moves the selected element ---------

    def test_position_field_edit_moves_selected_element(self):
        from madgrav.core.units import UNITS_PER_MM

        elements = self.root.elements
        self.root("rect 10mm 10mm 5mm 5mm\n")
        self.kernel.process_queue()
        node = list(elements.elems())[-1]
        elements.set_emphasis([node])
        self.kernel.process_queue()
        self.app.processEvents()
        self.assertAlmostEqual(node.bounds[0] / UNITS_PER_MM, 10.0, delta=0.1)

        self.win.pos_x_spin.setValue(50.0)
        self.win.pos_y_spin.setValue(30.0)
        self.win._on_position_field_edited()
        self.kernel.process_queue()
        self.app.processEvents()

        self.assertAlmostEqual(node.bounds[0] / UNITS_PER_MM, 50.0, delta=0.1)
        self.assertAlmostEqual(node.bounds[1] / UNITS_PER_MM, 30.0, delta=0.1)

    def test_size_field_edit_resizes_selected_element_keeping_top_left_fixed(self):
        # LightBurn's editable width/height fields ("Set Size") --
        # size_w_spin/size_h_spin were previously read-only labels.
        # "resize <x> <y> <w> <h>" sets width/height AND position in one
        # call, so _on_size_field_edited() feeds back the CURRENT pos_x/
        # pos_y_spin values to keep the top-left corner fixed rather
        # than implicitly moving the element to the origin.
        from madgrav.core.units import UNITS_PER_MM

        elements = self.root.elements
        self.root("rect 10mm 10mm 5mm 5mm\n")
        self.kernel.process_queue()
        node = list(elements.elems())[-1]
        elements.set_emphasis([node])
        self.kernel.process_queue()
        self.win._update_position_panel()
        self.assertAlmostEqual(self.win.size_w_spin.value(), 5.0, delta=0.01)
        self.assertAlmostEqual(self.win.size_h_spin.value(), 5.0, delta=0.01)

        self.win.size_w_spin.setValue(10.0)
        self.win.size_h_spin.setValue(20.0)
        self.win._on_size_field_edited()
        self.kernel.process_queue()

        b = node.bounds
        self.assertAlmostEqual((b[2] - b[0]) / UNITS_PER_MM, 10.0, delta=0.05)
        self.assertAlmostEqual((b[3] - b[1]) / UNITS_PER_MM, 20.0, delta=0.05)
        self.assertAlmostEqual(b[0] / UNITS_PER_MM, 10.0, delta=0.05)  # top-left kept
        self.assertAlmostEqual(b[1] / UNITS_PER_MM, 10.0, delta=0.05)

        # The panel re-populates to reflect the committed size.
        self.assertAlmostEqual(self.win.size_w_spin.value(), 10.0, delta=0.05)
        self.assertAlmostEqual(self.win.size_h_spin.value(), 20.0, delta=0.05)

        # No selection -- a safe no-op.
        elements.set_emphasis(None)
        self.kernel.process_queue()
        self.win._on_size_field_edited()

    def test_position_field_edit_on_locked_element_moves_it_without_corruption(self):
        # Regression test for a real core bug found via this test: the
        # "position" console command (madgrav/core/elements/shapes.py:
        # element_position) computed its reference bounds with
        # Node.union_bounds(data), which defaults to ignore_locked=True.
        # Locking an element doesn't block repositioning by default
        # (elements.lock_allows_move defaults to True -- lock only blocks
        # GUI drag-move), but with every selected node locked, that
        # default silently excluded them all from their own reference
        # bounds, leaving it at union_bounds()'s empty-set sentinel
        # (inf, inf, -inf, -inf). dx/dy then came out +-infinity and
        # got written straight into the node's transform matrix,
        # permanently wrecking its geometry (bounds collapsed to -inf).
        # Fixed by passing ignore_locked=False at that call site.
        from madgrav.core.units import UNITS_PER_MM

        elements = self.root.elements
        self.root("rect 10mm 10mm 5mm 5mm\n")
        self.kernel.process_queue()
        node = list(elements.elems())[-1]
        elements.set_emphasis([node])
        self.kernel.process_queue()
        self.win._on_lock(True)
        self.assertTrue(node.lock)

        self.win.pos_x_spin.setValue(80.0)
        self.win.pos_y_spin.setValue(80.0)
        self.win._on_position_field_edited()
        self.kernel.process_queue()
        self.app.processEvents()

        bounds_mm = [b / UNITS_PER_MM for b in node.bounds]
        self.assertTrue(all(math.isfinite(b) for b in bounds_mm), bounds_mm)
        self.assertAlmostEqual(bounds_mm[0], 80.0, delta=0.1)
        self.assertAlmostEqual(bounds_mm[1], 80.0, delta=0.1)

    # -- Device combo: switch and remove ---------------------------------

    def _combo_index_for(self, service):
        for i in range(self.win.device_combo.count()):
            if self.win.device_combo.itemData(i) is service:
                return i
        return None

    def test_device_combo_switches_by_index_even_with_quoted_label(self):
        # "device activate <name>" (madgrav/device/basedevice.py) matches
        # by EXACT string equality against spool.label. A label
        # containing a literal double quote (settable via a properties
        # panel text field -- not something a user has to type console
        # escapes for) used to break this: folding '"' to "'" avoided a
        # console parse error but then searched for a label that no
        # longer matched anything, so activation silently failed --
        # the combo showed the new selection but the device never
        # actually switched. Fixed by activating by INDEX instead
        # (which the same command also supports), sidestepping quote-
        # escaping entirely.
        device1 = self.root.device
        self._add_grbl_device()
        device2 = self.root.device
        self.assertIsNot(device2, device1)
        self.win._refresh_device_status()
        self.app.processEvents()

        idx1 = self._combo_index_for(device1)
        self.win._on_device_combo_activated(idx1)
        self.kernel.process_queue()
        self.app.processEvents()
        self.assertIs(self.root.device, device1)

        device2.label = 'Machine "A"'
        self.win._refresh_device_status()
        self.app.processEvents()
        idx2 = self._combo_index_for(device2)
        self.win._on_device_combo_activated(idx2)
        self.kernel.process_queue()
        self.app.processEvents()
        self.assertIs(self.root.device, device2)

    def test_device_combo_real_activated_signal_switches_device(self):
        # The test above calls _on_device_combo_activated() directly --
        # this instead emits the combo's own real "activated" Qt signal
        # (device_combo.activated.connect(self._on_device_combo_activated)
        # in _setup_ui), confirming that connection is actually wired up
        # rather than just the slot's own logic being correct. A wrong
        # signal name here (e.g. currentIndexChanged instead of
        # activated, an easy mix-up on QComboBox) would still pass every
        # test that calls the slot directly while leaving the real combo
        # non-functional for an actual user.
        device1 = self.root.device
        self._add_grbl_device()
        device2 = self.root.device
        self.assertIsNot(device2, device1)
        self.win._refresh_device_status()
        self.app.processEvents()

        idx1 = self._combo_index_for(device1)
        self.win.device_combo.activated.emit(idx1)
        self.kernel.process_queue()
        self.app.processEvents()
        self.assertIs(self.root.device, device1)

    def test_cannot_remove_active_device_but_can_remove_inactive_one(self):
        device1 = self.root.device
        self._add_grbl_device()
        device2 = self.root.device  # "device add" activates it
        self.win._refresh_device_status()
        self.app.processEvents()

        warned = []
        QMessageBox.warning = staticmethod(lambda *a, **k: warned.append(1))

        idx2 = self._combo_index_for(device2)
        self.win.device_combo.setCurrentIndex(idx2)
        count_before = self.win.device_combo.count()
        self.win._on_remove_device()  # device2 is the active one
        self.assertEqual(warned, [1])
        self.assertEqual(self.win.device_combo.count(), count_before)
        warned.clear()

        idx1 = self._combo_index_for(device1)
        self.win._on_device_combo_activated(idx1)
        self.kernel.process_queue()
        self.app.processEvents()
        self.win.device_combo.setCurrentIndex(self._combo_index_for(device2))
        QMessageBox.question = staticmethod(
            lambda *a, **k: QMessageBox.StandardButton.Yes
        )
        count_before2 = self.win.device_combo.count()
        self.win._on_remove_device()
        self.app.processEvents()
        self.assertEqual(self.win.device_combo.count(), count_before2 - 1)
        self.assertEqual(warned, [])

    # -- Device wizard: no leak on close ---------------------------------

    def test_device_wizard_does_not_leak_after_close(self):
        # A fresh DeviceSetupWizard is created on every "Nouvelle
        # Machine..." click with no other code ever deleting it --
        # without WA_DeleteOnClose it would stay parented to the main
        # window forever once closed, leaking one QWizard (and all its
        # child widgets) per open. _on_open_device_wizard() calls the
        # real blocking .exec(), so this arms a queued callback to find
        # and close the wizard from inside that nested event loop, the
        # same pattern used to test real modal-dialog usage elsewhere
        # this session.
        wizard_ref = []

        def close_wizard():
            wizards = self.win.findChildren(DeviceSetupWizard)
            self.assertEqual(len(wizards), 1)
            wizard_ref.append(wizards[0])
            wizards[0].reject()

        QTimer.singleShot(50, close_wizard)
        self.win._on_open_device_wizard()  # blocks until closed above
        self.app.processEvents()  # let the deferred deleteLater() run

        self.assertEqual(len(wizard_ref), 1)
        self.assertTrue(sip.isdeleted(wizard_ref[0]))
        self.assertEqual(self.win.findChildren(DeviceSetupWizard), [])

    def test_device_wizard_actually_creates_a_device(self):
        # The leak test above only exercises closing the wizard --
        # confirms the OTHER half: picking a real machine entry and
        # finishing actually creates and activates a real device via
        # _create_device(), the same "device add -i <profile> -l
        # <label>" console command the classic wx "New Device" dialog
        # issues. Drives the wizard's pages directly instead of the
        # blocking .exec() (already covered by the leak test).
        wizard = DeviceSetupWizard(self.root, self.win)
        try:
            lw = wizard.select_page.list_widget
            target_row = None
            for i in range(lw.count()):
                item = lw.item(i)
                if item.data(Qt.ItemDataRole.UserRole) is not None:
                    target_row = i
                    break
            self.assertIsNotNone(target_row)
            lw.setCurrentRow(target_row)
            self.assertIsNotNone(wizard.select_page.selected_entry())

            wizard.connection_page.initializePage()
            wizard.connection_page.label_edit.setText("TestMachine")

            self.assertTrue(wizard._create_device())
            self.assertEqual(wizard.created_label, "TestMachine")
            self.assertEqual(self.root.device.label, "TestMachine")
        finally:
            wizard.close()

    def test_device_wizard_folds_quoted_label_consistently(self):
        # Unlike the earlier device-combo bug (folded the label for the
        # console command but then searched using the UNFOLDED original),
        # _create_device() compares device.label against the SAME folded
        # value it used to build the command -- confirms that stays
        # self-consistent and a label with a literal double quote still
        # creates successfully instead of reporting a false failure.
        wizard = DeviceSetupWizard(self.root, self.win)
        try:
            lw = wizard.select_page.list_widget
            target_row = next(
                i
                for i in range(lw.count())
                if lw.item(i).data(Qt.ItemDataRole.UserRole) is not None
            )
            lw.setCurrentRow(target_row)
            wizard.connection_page.initializePage()
            wizard.connection_page.label_edit.setText('Machine "B"')

            self.assertTrue(wizard._create_device())
            self.assertEqual(wizard.created_label, "Machine 'B'")
            self.assertEqual(self.root.device.label, "Machine 'B'")
        finally:
            wizard.close()

    def test_device_wizard_page_gating_and_confirm_summary(self):
        # _MachineSelectPage.isComplete() gates the wizard's Next/Finish
        # button -- must stay disabled with nothing selected or a family
        # header row highlighted (those carry no usable data), and only
        # enable once a real, selectable machine entry is current. Also
        # confirms the read-only summary page (step 3) actually reflects
        # the chosen label before the user commits to "Terminer".
        wizard = DeviceSetupWizard(self.root, self.win)
        try:
            lw = wizard.select_page.list_widget
            self.assertFalse(wizard.select_page.isComplete())

            header_row = next(
                i
                for i in range(lw.count())
                if lw.item(i).data(Qt.ItemDataRole.UserRole) is None
            )
            target_row = next(
                i
                for i in range(lw.count())
                if lw.item(i).data(Qt.ItemDataRole.UserRole) is not None
            )

            lw.setCurrentRow(header_row)
            self.assertFalse(wizard.select_page.isComplete())

            lw.setCurrentRow(target_row)
            self.assertTrue(wizard.select_page.isComplete())

            wizard.connection_page.initializePage()
            wizard.connection_page.label_edit.setText("MyTestMachine")
            wizard.confirm_page.initializePage()
            summary = wizard.confirm_page.summary_label.text()
            self.assertIn("MyTestMachine", summary)
            self.assertIn("Terminer", summary)
        finally:
            wizard.close()

    def test_device_wizard_chosen_port_reads_custom_typed_text(self):
        # port_combo is editable -- a user can type a port not present in
        # the detected-ports dropdown (e.g. a machine plugged in after
        # the scan ran) and chosen_port() must still pick that up, not
        # just whatever was auto-selected from the scan.
        wizard = DeviceSetupWizard(self.root, self.win)
        try:
            lw = wizard.select_page.list_widget
            target_row = next(
                i
                for i in range(lw.count())
                if lw.item(i).data(Qt.ItemDataRole.UserRole) is not None
            )
            lw.setCurrentRow(target_row)
            wizard.connection_page.initializePage()

            self.assertIsNone(wizard.connection_page.chosen_port())

            wizard.connection_page.port_combo.setCurrentText("COM7")
            self.assertEqual(wizard.connection_page.chosen_port(), "COM7")
        finally:
            wizard.close()

    def test_device_wizard_port_dropdown_populates_and_auto_selects_first(self):
        # select_page.ports is captured once at construction (this test
        # environment naturally has none plugged in) -- simulated here
        # to verify the connection page's dropdown population and
        # auto-select-first-detected-port behavior, which nothing else
        # in this file exercises.
        wizard = DeviceSetupWizard(self.root, self.win)
        try:
            lw = wizard.select_page.list_widget
            target_row = next(
                i
                for i in range(lw.count())
                if lw.item(i).data(Qt.ItemDataRole.UserRole) is not None
            )
            lw.setCurrentRow(target_row)

            wizard.select_page.ports = [
                ("COM3", "COM3 - USB Serial Device"),
                ("COM5", "COM5 - Arduino Uno"),
            ]
            wizard.connection_page.initializePage()

            combo = wizard.connection_page.port_combo
            self.assertEqual(combo.count(), 3)  # blank + 2 detected ports
            self.assertEqual(
                [combo.itemText(i) for i in range(combo.count())],
                ["", "COM3 - USB Serial Device", "COM5 - Arduino Uno"],
            )
            self.assertEqual(combo.currentIndex(), 1)  # auto-selects the first
            self.assertEqual(wizard.connection_page.chosen_port(), "COM3")
        finally:
            wizard.close()

    # -- Device switch: canvas bed size sync ---------------------------

    def test_device_switch_resizes_canvas_bed(self):
        # Without this, the canvas keeps drawing the PREVIOUS device's
        # work-area boundary after switching devices -- actively
        # misleading for a laser cutter, since elements placed "near the
        # edge" of what's shown may not be near the real bed edge at all.
        # dummy (310x210mm) and grbl-generic (235x235mm) have genuinely
        # different bed sizes, confirmed via Length(device.view.width).
        canvas = self.win.canvas
        self.assertAlmostEqual(canvas.bed_width, 310.0, delta=0.5)
        self.assertAlmostEqual(canvas.bed_height, 210.0, delta=0.5)

        self._add_grbl_device()
        self.win._on_device_activated()
        self.app.processEvents()

        self.assertAlmostEqual(canvas.bed_width, 235.0, delta=0.5)
        self.assertAlmostEqual(canvas.bed_height, 235.0, delta=0.5)
        # The bed graphics item itself (init_scene() rebuild) must
        # reflect the new size too, not just the tracked attributes.
        rect = canvas.bed_item.rect()
        self.assertAlmostEqual(rect.width(), 235.0, delta=0.5)
        self.assertAlmostEqual(rect.height(), 235.0, delta=0.5)

    def test_device_switch_bed_measurement_feeds_outside_bed_safety_check(self):
        # Found via manual review: the bed-measurement sync above and the
        # CRITICAL "objects outside bed" pre-flight check
        # (_has_objects_outside_bed()) both read canvas.bed_width/
        # bed_height, but nothing previously exercised them TOGETHER with
        # real elements on the canvas -- which is exactly what surfaced a
        # genuine crash (see test_device_switch_with_rendered_elements_
        # does_not_crash below): _on_device_activated() calls
        # canvas.init_scene() then canvas.render_elements(), and
        # init_scene()'s scene.clear() destroys every QGraphicsItem
        # without clearing the tracking lists render_elements() then
        # tries to remove a second time. This test covers the actual
        # SAFETY semantics: an element within the larger dummy bed
        # (310x210mm) but outside the smaller grbl-generic bed
        # (235x235mm) must correctly flip the safety check's verdict
        # after switching.
        elements = self.root.elements
        self.root("rect 250mm 100mm 5mm 5mm\n")
        self.kernel.process_queue()
        node = list(elements.elems())[-1]
        op = elements.op_branch.add(type="op engrave", label="TestOp")
        op.output = True
        op.add_reference(node)

        self.assertFalse(self.win._has_objects_outside_bed())

        self._add_grbl_device()
        self.win._on_device_activated()
        self.app.processEvents()

        self.assertAlmostEqual(self.win.canvas.bed_width, 235.0, delta=0.5)
        self.assertTrue(self.win._has_objects_outside_bed())

    def test_device_switch_with_rendered_elements_does_not_crash(self):
        # The crash itself, isolated: canvas.init_scene() (called by
        # _on_device_activated() on every device switch) used to leave
        # _element_items/_item_to_node pointing at QGraphicsItems that
        # scene.clear() had already destroyed at the Qt/C++ level. The
        # very next canvas.render_elements() call -- also inside
        # _on_device_activated() -- then tried to scene.removeItem() an
        # already-deleted object: "RuntimeError: wrapped C/C++ object of
        # type QGraphicsPathItem has been deleted". Silent in every
        # earlier test in this file because none of them had actual
        # elements rendered on the canvas before switching devices.
        self.root("rect 0mm 0mm 5mm 5mm\n")
        self.kernel.process_queue()
        self.win.canvas.render_elements()
        self.assertEqual(len(self.win.canvas._element_items), 1)

        self._add_grbl_device()
        self.win._on_device_activated()  # previously raised RuntimeError
        self.app.processEvents()

        self.assertEqual(len(self.win.canvas._element_items), 1)
        self.assertEqual(len(list(self.root.elements.elems())), 1)

    def test_ops_tree_refresh_burst_coalesces_to_one_rebuild(self):
        # See test_ops_tree_refresh_is_debounced_not_synchronous's comment
        # for why this counts the timer's own signal instead of
        # monkeypatching _refresh_operations_tree.
        timer_fired = []
        self.win._ops_tree_refresh_timer.timeout.connect(lambda: timer_fired.append(1))

        for _ in range(10):
            self.win._on_tree_refresh_needed()
            QTest.qWait(5)  # faster than the debounce interval
        self.assertEqual(timer_fired, [])

        QTest.qWait(150)
        self.assertEqual(len(timer_fired), 1)

    def test_tree_item_click_selects_referenced_element_not_the_op_node(self):
        # A child row under an operation is a reference node whose real
        # target is set as its UserRole data (getattr(child, "node",
        # child) in _refresh_operations_tree) -- clicking it must select
        # the actual element, not the reference wrapper. Clicking the
        # operation's own top-level row (whose UserRole IS the op node
        # itself, not an element) must not crash even though that node
        # will never show up in elements.elems(emphasized=True).
        elements = self.root.elements
        self.root("rect 0mm 0mm 10mm 10mm\n")
        self.kernel.process_queue()
        rect_node = list(elements.elems())[-1]
        op = elements.op_branch.add(type="op engrave", label="TreeClickTestOp")
        op.output = True
        op.add_reference(rect_node)
        self.win._refresh_operations_tree()
        self.app.processEvents()

        op_item = next(
            self.win.ops_tree.topLevelItem(i)
            for i in range(self.win.ops_tree.topLevelItemCount())
            if self.win.ops_tree.topLevelItem(i).data(0, Qt.ItemDataRole.UserRole) is op
        )
        self.assertEqual(op_item.childCount(), 1)
        child_item = op_item.child(0)

        self.win._on_tree_item_clicked(child_item, 0)
        self.app.processEvents()
        self.assertTrue(rect_node.emphasized)

        elements.set_emphasis(None)
        self.kernel.process_queue()
        self.win._on_tree_item_clicked(op_item, 0)  # must not raise
        self.app.processEvents()
        self.assertEqual(list(elements.elems(emphasized=True)), [])

    def test_ops_tree_real_click_reaches_the_handler(self):
        # The test above calls _on_tree_item_clicked() directly -- this
        # drives a real QTest.mouseClick() on the tree widget's viewport
        # instead, confirming the itemClicked signal is actually wired to
        # it (a wrong signal name or missing .connect() wouldn't be
        # caught by calling the slot directly).
        #
        # Fixed two real gaps found while writing a companion test for
        # the tree's Dupliquer/Supprimer buttons: (1) this window's
        # default (unresized) size squeezes ops_tree's viewport down to
        # a handful of pixels once several right-side docks stack up --
        # visualItemRect() still reports the item's position in the full
        # scrollable content, which commonly falls outside that sliver,
        # so the synthetic click below previously landed nowhere real
        # without an explicit scrollToItem() first; (2) the assertion
        # was checking rect_node.emphasized, but a freshly-drawn "rect"
        # is already emphasized at creation time (established elsewhere
        # in this file) -- meaning this assertion could pass even if the
        # click hit nothing at all. Deselecting first closes that gap.
        elements = self.root.elements
        self.root("rect 0mm 0mm 10mm 10mm\n")
        self.kernel.process_queue()
        rect_node = list(elements.elems())[-1]
        op = elements.op_branch.add(type="op engrave", label="RealClickTestOp")
        op.output = True
        op.add_reference(rect_node)
        elements.set_emphasis(None)
        self.kernel.process_queue()
        self.win._refresh_operations_tree()
        self.app.processEvents()

        op_item = next(
            self.win.ops_tree.topLevelItem(i)
            for i in range(self.win.ops_tree.topLevelItemCount())
            if self.win.ops_tree.topLevelItem(i).data(0, Qt.ItemDataRole.UserRole) is op
        )
        self.win.ops_tree.expandItem(op_item)
        self.app.processEvents()
        child_item = op_item.child(0)
        self.win.ops_tree.scrollToItem(child_item)
        self.app.processEvents()
        # visualItemRect() spans the full (now 4-column) row -- its
        # center can fall past the dock's squeezed visible width even
        # after scrollToItem(), which only guarantees column 0 is
        # on-screen. Click near the rect's left edge (column 0) instead
        # of its horizontal center, so this stays robust regardless of
        # how many columns the row ends up spanning.
        rect = self.win.ops_tree.visualItemRect(child_item)
        pos = rect.topLeft() + QPoint(5, rect.height() // 2)

        self.assertFalse(rect_node.emphasized)
        QTest.mouseClick(self.win.ops_tree.viewport(), Qt.MouseButton.LeftButton, pos=pos)
        self.app.processEvents()

        self.assertTrue(rect_node.emphasized)

    def _tree_item_for(self, node):
        for i in range(self.win.ops_tree.topLevelItemCount()):
            top = self.win.ops_tree.topLevelItem(i)
            if top.data(0, Qt.ItemDataRole.UserRole) is node:
                return top
            for j in range(top.childCount()):
                child = top.child(j)
                if child.data(0, Qt.ItemDataRole.UserRole) is node:
                    return child
        return None

    def test_tree_item_rename_via_double_click(self):
        # node.label is a plain attribute on every Node subclass -- no
        # console verb renames a node by label directly, so this is set
        # on the node itself and then re-synced into the kernel via the
        # same "element_property_update" signal _on_lock() already uses
        # for a comparable direct-attribute change.
        elements = self.root.elements
        self.root("rect 0mm 0mm 5mm 5mm\n")
        self.kernel.process_queue()
        node = list(elements.elems())[-1]
        self.win._refresh_operations_tree()
        item = self._tree_item_for(node)
        self.assertIsNotNone(item)

        QInputDialog.getText = staticmethod(lambda *a, **k: ("MonRectangle", True))
        self.win._on_tree_item_double_clicked(item, 0)
        self.assertEqual(node.label, "MonRectangle")

        # Cancelling (ok=False) leaves the label untouched.
        self.win._refresh_operations_tree()
        item2 = self._tree_item_for(node)
        QInputDialog.getText = staticmethod(lambda *a, **k: ("", False))
        self.win._on_tree_item_double_clicked(item2, 0)
        self.assertEqual(node.label, "MonRectangle")

        # A click in a non-label column (speed/power) must not rename.
        QInputDialog.getText = staticmethod(lambda *a, **k: ("Should Not Apply", True))
        self.win._on_tree_item_double_clicked(item2, 1)
        self.assertEqual(node.label, "MonRectangle")

    def test_tree_speed_and_power_columns_editable_via_double_click(self):
        # LightBurn's directly-editable per-layer Speed/Power columns --
        # this shell's tree already DISPLAYED them (_refresh_operations_
        # tree), just never let you change them. Power is stored as a
        # per-mille value (0-1000 == 0-100%, confirmed via op_engrave.
        # py's own "percent" formatter) but edited here as the familiar
        # 0-100% a user actually thinks in.
        elements = self.root.elements
        op = elements.op_branch.add(type="op engrave", label="SpeedPowerTestOp")
        op.speed = 35.0
        op.power = 1000.0
        self.win._refresh_operations_tree()

        def find_op_item():
            return next(
                self.win.ops_tree.topLevelItem(i)
                for i in range(self.win.ops_tree.topLevelItemCount())
                if self.win.ops_tree.topLevelItem(i).data(0, Qt.ItemDataRole.UserRole) is op
            )

        QInputDialog.getDouble = staticmethod(lambda *a, **k: (60.0, True))
        self.win._on_tree_item_double_clicked(find_op_item(), 1)
        self.assertEqual(op.speed, 60.0)

        QInputDialog.getDouble = staticmethod(lambda *a, **k: (50.0, True))
        self.win._on_tree_item_double_clicked(find_op_item(), 2)
        self.assertEqual(op.power, 500.0)

        # A cancelled dialog (ok=False) is a no-op.
        QInputDialog.getDouble = staticmethod(lambda *a, **k: (999.0, False))
        self.win._on_tree_item_double_clicked(find_op_item(), 1)
        self.assertEqual(op.speed, 60.0)

        # An element-child row (not an operation) has no speed/power
        # attributes -- a safe no-op, not a crash.
        self.root("rect 0mm 0mm 5mm 5mm\n")
        self.kernel.process_queue()
        rect_node = list(elements.elems())[-1]
        op.add_reference(rect_node)
        self.win._refresh_operations_tree()
        child_item = find_op_item().child(0)
        self.win._on_tree_item_double_clicked(child_item, 1)
        self.win._on_tree_item_double_clicked(child_item, 2)

    def test_tree_passes_column_editable_via_double_click(self):
        # LightBurn parity continued: a "Passes" column next to Speed/
        # Power, directly editable the same way. The engine only honors
        # the raw "passes" attribute when passes_custom is True (see the
        # "passes" console command in elements/branches.py) -- the
        # displayed/edited value is implicit_passes (Parameters mixin),
        # which is 1 when not customized, matching what actually runs.
        elements = self.root.elements
        op = elements.op_branch.add(type="op engrave", label="PassesTestOp")
        op.passes = 0
        op.passes_custom = False
        self.win._refresh_operations_tree()

        def find_op_item():
            return next(
                self.win.ops_tree.topLevelItem(i)
                for i in range(self.win.ops_tree.topLevelItemCount())
                if self.win.ops_tree.topLevelItem(i).data(0, Qt.ItemDataRole.UserRole) is op
            )

        self.assertEqual(find_op_item().text(3), "1")

        QInputDialog.getInt = staticmethod(lambda *a, **k: (4, True))
        self.win._on_tree_item_double_clicked(find_op_item(), 3)
        self.assertEqual(op.passes, 4)
        self.assertTrue(op.passes_custom)
        self.assertEqual(find_op_item().text(3), "4")

        # A cancelled dialog (ok=False) is a no-op.
        QInputDialog.getInt = staticmethod(lambda *a, **k: (999, False))
        self.win._on_tree_item_double_clicked(find_op_item(), 3)
        self.assertEqual(op.passes, 4)

        # An element-child row (not an operation) has no "passes"
        # attribute -- a safe no-op, not a crash.
        self.root("rect 0mm 0mm 5mm 5mm\n")
        self.kernel.process_queue()
        rect_node = list(elements.elems())[-1]
        op.add_reference(rect_node)
        self.win._refresh_operations_tree()
        child_item = find_op_item().child(0)
        self.win._on_tree_item_double_clicked(child_item, 3)

    def test_time_estimate_label_sums_enabled_ops_and_skips_disabled_ones(self):
        # LightBurn shows an "Estimated Time" readout prominently near
        # its operations list; every op_*.py node class already computes
        # its own time_estimate() ("H:MM:SS" string) but nothing summed
        # them into a whole-job total before. A disabled operation
        # (output=False) must not count -- it won't actually fire in a
        # real job, so including it would make the total misleading
        # rather than just incomplete.
        elements = self.root.elements
        from madgrav.core.units import UNITS_PER_MM

        def hms_to_seconds(text):
            h, m, s = text.split(":")
            return int(h) * 3600 + int(m) * 60 + int(s)

        # elem_branch.add() directly (not the "rect" console command) --
        # bypasses classify_new's auto-classification into whatever
        # default operation already exists, so each rect below ends up
        # ONLY in the operation this test explicitly references it into.
        # x/y/width/height are raw native-unit floats here, not "Nmm"
        # strings -- unlike the "rect" console command (which parses
        # Length strings itself before calling elem_branch.add()), the
        # node constructor does no such parsing and does real arithmetic
        # on these at as_geometry() time (x + width, etc).
        rect_a = elements.elem_branch.add(
            type="elem rect",
            x=0.0,
            y=0.0,
            width=10 * UNITS_PER_MM,
            height=10 * UNITS_PER_MM,
        )
        op_enabled = elements.op_branch.add(type="op engrave", label="EnabledOp")
        # Deliberately slow: a small square's perimeter at a normal
        # engrave speed (e.g. 100mm/s) can round down to "0:00:00" once
        # time_estimate() truncates to whole seconds -- a slow speed
        # keeps its own contribution a comfortably non-zero, measurable
        # delta below.
        op_enabled.speed = 1.0
        op_enabled.output = True
        op_enabled.add_reference(rect_a)
        self.win._refresh_operations_tree()

        # Baseline BEFORE adding the disabled op -- compares deltas
        # rather than an absolute total, so this stays correct even if
        # setUp() or a sibling op ever contributes its own baseline time.
        def shown_seconds():
            text = self.win.time_estimate_lbl.text()
            self.assertTrue(text.startswith("Temps estimé : "))
            return hms_to_seconds(text.split(": ", 1)[1])

        baseline_seconds = shown_seconds()

        rect_b = elements.elem_branch.add(
            type="elem rect",
            x=20 * UNITS_PER_MM,
            y=0.0,
            width=10 * UNITS_PER_MM,
            height=10 * UNITS_PER_MM,
        )
        op_disabled = elements.op_branch.add(type="op engrave", label="DisabledOp")
        op_disabled.speed = 1.0
        op_disabled.output = False
        op_disabled.add_reference(rect_b)
        self.win._refresh_operations_tree()

        # A disabled op must not move the total at all.
        self.assertEqual(shown_seconds(), baseline_seconds)

        # Re-enabling it must add exactly its own contribution.
        op_disabled.output = True
        self.win._refresh_operations_tree()
        disabled_op_seconds = hms_to_seconds(op_disabled.time_estimate())
        self.assertGreater(disabled_op_seconds, 0)  # sanity: a real, non-zero cut path
        self.assertEqual(shown_seconds(), baseline_seconds + disabled_op_seconds)

    def test_tree_duplicate_and_delete_buttons(self):
        # Regression test for a real bug found via this test: the
        # buttons originally read QTreeWidget.currentItem()/
        # itemSelectionChanged to decide whether something was
        # selected -- but a click on this tree does not reliably update
        # Qt's internal selection model in this app (confirmed by
        # reproduction: itemClicked always fires and correctly drives
        # canvas selection, but currentItem() stayed None right after).
        # Every other click handler in this class already reads the
        # item passed directly to its signal instead of querying
        # selection state back, for the same underlying reason. Fixed
        # by tracking the clicked node explicitly via
        # _on_tree_item_clicked() into self._tree_action_node, so this
        # test drives it the same way -- through the click handler, not
        # QTreeWidget.setCurrentItem() (which doesn't fire itemClicked
        # at all and would silently validate the wrong mechanism).
        elements = self.root.elements
        self.assertFalse(self.win.btn_tree_duplicate.isEnabled())
        self.assertFalse(self.win.btn_tree_delete.isEnabled())

        self.root("rect 0mm 0mm 5mm 5mm\n")
        self.kernel.process_queue()
        node = list(elements.elems())[-1]
        self.win._refresh_operations_tree()
        item = self._tree_item_for(node)
        self.win._on_tree_item_clicked(item, 0)

        self.assertTrue(self.win.btn_tree_duplicate.isEnabled())
        self.assertTrue(self.win.btn_tree_delete.isEnabled())

        count_before = len(list(elements.elems()))
        self.win._on_tree_duplicate_selected()
        self.kernel.process_queue()
        self.assertEqual(len(list(elements.elems())), count_before + 1)

        self.win._refresh_operations_tree()
        item2 = self._tree_item_for(node)
        self.win._on_tree_item_clicked(item2, 0)
        count_before_delete = len(list(elements.elems()))
        self.win._on_tree_delete_selected()
        self.kernel.process_queue()
        self.assertEqual(len(list(elements.elems())), count_before_delete - 1)

        # No selection -- buttons disabled, and calling the handlers
        # directly (as a stray signal/timing edge case might) is a safe
        # no-op rather than a crash.
        self.win._tree_action_node = None
        self.win._update_tree_action_buttons()
        self.assertFalse(self.win.btn_tree_duplicate.isEnabled())
        self.assertFalse(self.win.btn_tree_delete.isEnabled())
        self.win._on_tree_duplicate_selected()
        self.win._on_tree_delete_selected()

    def test_tree_action_buttons_enable_from_a_real_tree_click(self):
        # Companion to the test above: drives an actual QTest.mouseClick
        # on the tree widget's viewport (same pattern already proven
        # reliable by test_ops_tree_real_click_reaches_the_handler)
        # rather than calling _on_tree_item_clicked() directly, to
        # confirm the real itemClicked signal is what enables these
        # buttons for an actual user, not just the slot's own logic.
        elements = self.root.elements
        self.root("rect 0mm 0mm 10mm 10mm\n")
        self.kernel.process_queue()
        node = list(elements.elems())[-1]
        op = elements.op_branch.add(type="op engrave", label="TreeActionRealClickOp")
        op.output = True
        op.add_reference(node)
        self.win._refresh_operations_tree()
        self.app.processEvents()

        op_item = next(
            self.win.ops_tree.topLevelItem(i)
            for i in range(self.win.ops_tree.topLevelItemCount())
            if self.win.ops_tree.topLevelItem(i).data(0, Qt.ItemDataRole.UserRole) is op
        )
        self.win.ops_tree.expandItem(op_item)
        self.app.processEvents()
        child_item = op_item.child(0)
        # The dock stack squeezes ops_tree's viewport down to a handful
        # of visible pixels at this window's default (unresized) size --
        # visualItemRect() still reports the item's position within the
        # full scrollable content, which can fall well outside that tiny
        # visible area and make a synthetic click land nowhere real.
        # scrollToItem() is what actually brings it on-screen first (a
        # real user scrolling to it before clicking, in effect).
        self.win.ops_tree.scrollToItem(child_item)
        self.app.processEvents()
        # See test_ops_tree_real_click_reaches_the_handler for why this
        # clicks near the rect's left edge rather than its horizontal
        # center: the row now spans 4 columns and can be wider than the
        # dock's squeezed visible width, even after scrollToItem().
        rect = self.win.ops_tree.visualItemRect(child_item)
        pos = rect.topLeft() + QPoint(5, rect.height() // 2)

        QTest.mouseClick(self.win.ops_tree.viewport(), Qt.MouseButton.LeftButton, pos=pos)
        self.app.processEvents()

        self.assertIs(self.win._tree_action_node, node)
        self.assertTrue(self.win.btn_tree_duplicate.isEnabled())
        self.assertTrue(self.win.btn_tree_delete.isEnabled())

    def test_tree_duplicate_refuses_on_a_pure_operation_node(self):
        # An operation's top-level row resolves (via UserRole) to the
        # operation node itself, not an element -- element-only
        # "duplicate" has no equivalent for it in this shell yet.
        elements = self.root.elements
        op = elements.op_branch.add(type="op engrave", label="OpOnlyTest")
        self.win._refresh_operations_tree()
        item = self._tree_item_for(op)
        self.assertIsNotNone(item)
        self.win._on_tree_item_clicked(item, 0)

        count_before = len(list(elements.elems()))
        self.win._on_tree_duplicate_selected()
        self.assertEqual(len(list(elements.elems())), count_before)
        self.assertNotEqual(self.win.status_bar.currentMessage(), "")

    def test_position_panel_fill_and_stroke_color_pickers(self):
        elements = self.root.elements
        self.root("rect 0mm 0mm 5mm 5mm\n")
        self.kernel.process_queue()
        node = list(elements.elems())[-1]
        elements.set_emphasis([node])
        self.kernel.process_queue()
        self.win._update_position_panel()

        QColorDialog.getColor = staticmethod(lambda *a, **k: QColor(255, 0, 0))
        self.win._pick_and_apply_color("fill")
        self.kernel.process_queue()
        self.assertEqual(
            (node.fill.red, node.fill.green, node.fill.blue), (255, 0, 0)
        )

        QColorDialog.getColor = staticmethod(lambda *a, **k: QColor(0, 255, 0))
        self.win._pick_and_apply_color("stroke")
        self.kernel.process_queue()
        self.assertEqual(
            (node.stroke.red, node.stroke.green, node.stroke.blue), (0, 255, 0)
        )

        # A cancelled QColorDialog returns an invalid QColor() -- must be
        # a no-op, not applied as e.g. opaque black.
        fill_before = node.fill.hexrgb
        QColorDialog.getColor = staticmethod(lambda *a, **k: QColor())
        self.win._pick_and_apply_color("fill")
        self.kernel.process_queue()
        self.assertEqual(node.fill.hexrgb, fill_before)

    def test_position_panel_stroke_width_field_edits_and_populates(self):
        from madgrav.core.units import UNITS_PER_MM

        elements = self.root.elements
        self.root("rect 0mm 0mm 5mm 5mm\n")
        self.kernel.process_queue()
        node = list(elements.elems())[-1]
        elements.set_emphasis([node])
        self.kernel.process_queue()
        self.win._update_position_panel()
        self.assertTrue(self.win.stroke_width_spin.isEnabled())

        self.win.stroke_width_spin.setValue(2.5)
        self.win._on_stroke_width_edited()
        self.kernel.process_queue()
        self.assertAlmostEqual(node.stroke_width / UNITS_PER_MM, 2.5, delta=0.01)

        # Re-populating the panel (e.g. selecting the node again) must
        # reflect the new value back into the field.
        self.win.stroke_width_spin.setValue(0)
        self.win._update_position_panel()
        self.assertAlmostEqual(self.win.stroke_width_spin.value(), 2.5, delta=0.01)

    # -- Canvas right-click context menu -----------------------------------

    def test_context_menu_selects_unselected_item_before_opening(self):
        # Right-clicking an unselected element selects it first (standard
        # UX in most vector editors) so the menu's Delete/Group/etc.
        # actions apply to it -- QMenu.exec() is monkeypatched to avoid
        # actually blocking the test on a real modal popup, same
        # reasoning as monkeypatching QMessageBox elsewhere in this file.
        exec_calls = []
        QMenu.exec = lambda self, *a, **k: exec_calls.append(1)

        elements = self.root.elements
        self.root("rect 0mm 0mm 30mm 30mm\n")
        self.kernel.process_queue()
        node = list(elements.elems())[-1]
        self.win.canvas.render_elements()
        self.app.processEvents()
        elements.set_emphasis(None)
        self.kernel.process_queue()

        item = next(
            it for it, n in self.win.canvas._item_to_node.items() if n is node
        )
        view_pos = self.win.canvas.mapFromScene(item.sceneBoundingRect().center())

        self.assertFalse(getattr(node, "emphasized", False))
        self.win._on_canvas_context_menu(view_pos)
        self.assertTrue(node.emphasized)
        self.assertEqual(len(exec_calls), 1)

    def test_context_menu_on_already_selected_item_leaves_selection_alone(self):
        exec_calls = []
        QMenu.exec = lambda self, *a, **k: exec_calls.append(1)

        elements = self.root.elements
        self.root("rect 0mm 0mm 30mm 30mm\n")
        self.root("rect 40mm 0mm 30mm 30mm\n")
        self.kernel.process_queue()
        nodes = list(elements.elems())[-2:]
        self.win.canvas.render_elements()
        self.app.processEvents()
        elements.set_emphasis(nodes)  # both already selected
        self.kernel.process_queue()

        item = next(
            it for it, n in self.win.canvas._item_to_node.items() if n is nodes[0]
        )
        view_pos = self.win.canvas.mapFromScene(item.sceneBoundingRect().center())

        self.win._on_canvas_context_menu(view_pos)
        self.assertEqual(
            {n for n in elements.elems(emphasized=True)}, set(nodes)
        )
        self.assertEqual(len(exec_calls), 1)

    def test_context_menu_on_empty_canvas_does_not_raise(self):
        exec_calls = []
        QMenu.exec = lambda self, *a, **k: exec_calls.append(1)

        self.win._on_canvas_context_menu(self.win.canvas.viewport().rect().topLeft())
        self.assertEqual(len(exec_calls), 1)

    # -- Zoom to fit ------------------------------------------------------------

    def test_zoom_fit_on_empty_document_does_not_raise(self):
        # itemsBoundingRect() is empty with nothing on the canvas --
        # _on_zoom_fit() falls back to sceneRect() instead of fitting an
        # empty/degenerate rect, which fitInView() can't handle sensibly.
        self.win._on_zoom_fit()
        self.assertTrue(self.win.zoom_label.text().endswith("%"))
        self.assertNotEqual(self.win.status_bar.currentMessage(), "")

    def test_zoom_fit_syncs_zoom_label_after_fitting_content(self):
        # fitInView() doesn't route through zoom_step()/reset_zoom(), so
        # the canvas's own zoom_changed signal never fires for it --
        # _on_zoom_fit() calls _on_zoom_changed() directly afterwards to
        # keep the status-bar label in sync with the new transform.
        self.root("rect 0mm 0mm 50mm 50mm\n")
        self.kernel.process_queue()

        self.win.zoom_label.setText("999%")
        self.win._on_zoom_fit()

        self.assertNotEqual(self.win.zoom_label.text(), "999%")
        expected = f"{self.win.canvas.transform().m11() * 100:.0f}%"
        self.assertEqual(self.win.zoom_label.text(), expected)

    # -- Draw-tool selection --------------------------------------------------

    def test_tool_actions_set_draw_mode_and_pan_toggles_drag_mode(self):
        # set_draw_mode() (qt_canvas.py) always resets QGraphicsView's
        # DragMode back to NoDrag as part of switching tools -- _on_tool_pan
        # relies on that ordering, calling set_draw_mode(None) *then*
        # overriding to ScrollHandDrag, so a later tool switch back to
        # Select must not be left stuck in pan's drag mode.
        canvas = self.win.canvas

        self.win._on_tool_rect()
        self.assertEqual(canvas.draw_mode, "rect")
        self.assertEqual(canvas.dragMode(), QGraphicsView.DragMode.NoDrag)

        self.win._on_tool_ellipse()
        self.assertEqual(canvas.draw_mode, "ellipse")

        self.win._on_tool_line()
        self.assertEqual(canvas.draw_mode, "line")

        self.win._on_tool_text()
        self.assertEqual(canvas.draw_mode, "text")

        self.win._on_tool_pan()
        self.assertIsNone(canvas.draw_mode)
        self.assertEqual(canvas.dragMode(), QGraphicsView.DragMode.ScrollHandDrag)

        self.win._on_tool_select()
        self.assertIsNone(canvas.draw_mode)
        self.assertEqual(canvas.dragMode(), QGraphicsView.DragMode.NoDrag)

    def test_tool_panel_buttons_are_wired_to_the_right_handler(self):
        # The test above calls _on_tool_*() directly -- a real regression
        # in this method (e.g. a copy-paste mistake wiring "Rectangle"'s
        # button to _on_tool_ellipse) wouldn't be caught that way. This
        # drives the actual QPushButtons via QTest.mouseClick() instead,
        # and also checks the QButtonGroup's exclusivity (only the
        # clicked tool stays checked).
        buttons = self.win.tool_group.buttons()
        self.assertEqual(len(buttons), 7)
        expected_modes = {
            "Sélection": None,
            "Rectangle": "rect",
            "Cercle": "ellipse",
            "Ligne": "line",
            "Texte": "text",
            "Polygone": "polygon",
        }
        checked_texts = {b.text() for b in buttons}
        self.assertTrue(set(expected_modes).issubset(checked_texts))

        for btn in buttons:
            mode = expected_modes.get(btn.text())
            if mode is None and btn.text() not in expected_modes:
                continue  # the Pan button -- checked separately below
            QTest.mouseClick(btn, Qt.MouseButton.LeftButton)
            self.assertEqual(self.win.canvas.draw_mode, mode)
            self.assertTrue(btn.isChecked())
            self.assertEqual([b for b in buttons if b.isChecked()], [btn])

        pan_btn = next(b for b in buttons if b.text() not in expected_modes)
        QTest.mouseClick(pan_btn, Qt.MouseButton.LeftButton)
        self.assertIsNone(self.win.canvas.draw_mode)
        self.assertEqual(
            self.win.canvas.dragMode(), QGraphicsView.DragMode.ScrollHandDrag
        )
        self.assertTrue(pan_btn.isChecked())

    def test_tool_panel_icons_render_and_survive_theme_toggle(self):
        # _apply_tool_icon_theme() bakes a fixed foreground color into
        # each icon's pixmap at draw time (unlike a QSS color, a raster
        # icon can't recolor itself) -- it must be called again on every
        # theme toggle, same as _apply_toolbar_button_theme() already is
        # for the arm/start/pause/stop/coolant buttons.
        buttons = self.win.tool_group.buttons()
        self.assertEqual(len(buttons), 7)
        for btn in buttons:
            self.assertFalse(btn.icon().isNull(), btn.text())

        self.win.act_light_theme.trigger()
        self.app.processEvents()
        for btn in buttons:
            self.assertFalse(btn.icon().isNull(), btn.text())

    # -- Retractable right-side panels ---------------------------------------

    def test_right_docks_are_retractable_and_reopenable_via_panels_menu(self):
        # Every dock (tool palette, inspector, console) now starts
        # hidden -- each stays one click away via Affichage > Panneaux
        # instead of occupying screen space unasked. Each QDockWidget
        # already has Qt's default DockWidgetClosable feature (no
        # setFeatures() call anywhere restricts it) -- clicking a
        # panel's own title-bar "X" retracts/hides it once shown; the
        # matching re-show half is dock.toggleViewAction(), a checkable
        # QAction that both triggers and reflects the dock's actual
        # visibility, surfaced in the "Panneaux" submenu of Affichage.
        for dock in (self.win.dock_tools, self.win.dock_ops, self.win.dock_console):
            self.assertFalse(dock.isVisible(), f"{dock.windowTitle()} should start hidden")

        action = self.win.dock_ops.toggleViewAction()
        self.assertFalse(action.isChecked())

        action.trigger()
        self.assertTrue(self.win.dock_ops.isVisible())

        self.win.dock_ops.close()
        self.assertFalse(self.win.dock_ops.isVisible())
        self.assertFalse(action.isChecked(), "toggle action must track a manual close")

        action.trigger()
        self.assertTrue(self.win.dock_ops.isVisible())

        panels_menu = None
        for menu_action in self.win.view_menu.actions():
            if menu_action.menu() is not None and menu_action.text() == "Panneaux":
                panels_menu = menu_action.menu()
                break
        self.assertIsNotNone(panels_menu)
        entry_texts = {a.text() for a in panels_menu.actions() if not a.isSeparator()}
        self.assertEqual(
            entry_texts,
            {
                "Outils Laser & Dessin", "Inspecteur & Contrôle", "Console de Commandes",
                "🔄 Réinitialiser la Disposition des Panneaux",
            },
        )

    def test_reset_panel_layout_restores_the_default_hidden_state(self):
        # A user who drags/resizes docks into a confusing state needs a
        # way back to the known-good just-constructed layout -- same
        # "Reset Layout" convenience every professional app offers.
        self.win.dock_ops.toggleViewAction().trigger()
        self.win.dock_tools.toggleViewAction().trigger()
        self.assertTrue(self.win.dock_ops.isVisible())
        self.assertTrue(self.win.dock_tools.isVisible())

        self.win._on_reset_panel_layout()
        self.app.processEvents()

        self.assertFalse(self.win.dock_ops.isVisible(), "reset must restore the default hidden state")
        self.assertFalse(self.win.dock_tools.isVisible())

    # -- Keyboard shortcuts dialog -------------------------------------------

    def test_show_shortcuts_dialog_lists_sorted_deduped_bindings(self):
        # Built from the QActions actually bound at menu-construction time
        # rather than a hand-maintained list (see _on_show_shortcuts's own
        # comment) -- this locks in the three real invariants that give
        # that approach: no duplicate (label, shortcut) rows even though
        # the same QAction can appear in more than one menu/toolbar, every
        # row sorted case-insensitively by label, and actions with no
        # shortcut bound are skipped rather than showing a blank key.
        shown = []
        QMessageBox.information = staticmethod(
            lambda *a, **k: shown.append(a[2] if len(a) > 2 else k.get("text"))
        )

        self.win._on_show_shortcuts()

        self.assertEqual(len(shown), 1)
        lines = [ln for ln in shown[0].split("\n") if ln]
        self.assertTrue(lines)
        self.assertEqual(len(lines), len(set(lines)), "duplicate shortcut rows")
        labels = [ln.split("\t", 1)[1] for ln in lines]
        self.assertEqual(labels, sorted(labels, key=str.lower))
        self.assertTrue(all("\t" in ln for ln in lines))

    # -- Console input dock --------------------------------------------------

    def test_console_input_dispatches_echoes_and_records_history(self):
        input_box = self.win.findChild(ConsoleLineEdit)
        self.assertIsNotNone(input_box)

        elements = self.root.elements
        count_before = len(list(elements.elems()))

        QTest.keyClicks(input_box, "rect 0mm 0mm 5mm 5mm")
        QTest.keyClick(input_box, Qt.Key.Key_Return)
        self.kernel.process_queue()
        self.app.processEvents()

        self.assertEqual(input_box.text(), "")
        self.assertIn("> rect 0mm 0mm 5mm 5mm", self.win.console_output.toPlainText())
        self.assertGreater(len(list(elements.elems())), count_before)

        # Recorded into history -- Up arrow recalls the exact command.
        QTest.keyClick(input_box, Qt.Key.Key_Up)
        self.assertEqual(input_box.text(), "rect 0mm 0mm 5mm 5mm")

        # An empty/whitespace-only command is a no-op: nothing dispatched,
        # nothing new echoed.
        input_box.clear()
        before_len = len(self.win.console_output.toPlainText())
        QTest.keyClick(input_box, Qt.Key.Key_Return)
        self.app.processEvents()
        self.assertEqual(len(self.win.console_output.toPlainText()), before_len)


@unittest.skipUnless(HAS_QT, "PyQt6 not installed")
class TestSingletonQtWindowGuard(unittest.TestCase):
    """_show_or_create_qt_window (madgrav/qt/plugin.py): without this,
    invoking "qtgui" a second time (e.g. after --qt already opened one at
    boot) unconditionally built a duplicate window and overwrote
    kernel.root.qt_main_window -- orphaning the first one, whose kernel
    signal listeners would never get unlistened and which would never be
    asked to close during a real shutdown. Doesn't need the full
    setUp/tearDown window fixture the other tests in this file use, so
    it's a separate lightweight class."""

    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def test_no_existing_window_returns_false(self):
        kernel = bootstrap.bootstrap()
        try:
            kernel.root.qt_main_window = None
            self.assertFalse(_show_or_create_qt_window(kernel))
        finally:
            kernel()

    def test_live_window_is_reused_and_raised(self):
        kernel = bootstrap.bootstrap()
        try:
            kernel.root("service device start dummy 0\n")
            win = MadGravQtMainWindow(kernel.root)
            win.hide()
            kernel.root.qt_main_window = win
            try:
                self.assertTrue(_show_or_create_qt_window(kernel))
                self.assertTrue(win.isVisible())
            finally:
                win._closing_from_kernel = True
                win.close()
        finally:
            kernel()

    def test_destroyed_reference_is_cleared_and_reports_false(self):
        # The reference points to a Qt object already torn down at the
        # C/C++ level (e.g. the user closed it directly, bypassing the
        # kernel's own shutdown path) -- must not crash, must clear the
        # stale reference so the caller creates a fresh window instead.
        kernel = bootstrap.bootstrap()
        try:
            kernel.root("service device start dummy 0\n")
            win = MadGravQtMainWindow(kernel.root)
            kernel.root.qt_main_window = win
            # Flush any signal still queued from construction/the console
            # command above BEFORE destroying the C++ object -- otherwise
            # a stray later delivery hits the now-dead window and prints
            # an unrelated (harmless, but noisy) RuntimeError traceback
            # from Qt's own slot exception hook.
            kernel.process_queue()
            self.app.processEvents()
            sip.delete(win)

            self.assertFalse(_show_or_create_qt_window(kernel))
            self.assertIsNone(kernel.root.qt_main_window)
        finally:
            kernel()


@unittest.skipUnless(HAS_QT, "PyQt6 not installed")
class TestConsoleLineEditHistory(unittest.TestCase):
    """ConsoleLineEdit (madgrav/qt/qt_main.py): Up/Down command history
    for the console dock's input field, like a real terminal. Doesn't
    need a kernel or the full window fixture -- a self-contained widget,
    so it gets its own lightweight test class."""

    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def test_up_down_walks_history_oldest_to_newest(self):
        edit = ConsoleLineEdit()
        edit.record("rect 0 0 5mm 5mm")
        edit.record("circle 3cm 3cm 1cm")
        edit.record("help")

        QTest.keyClick(edit, Qt.Key.Key_Up)
        self.assertEqual(edit.text(), "help")
        QTest.keyClick(edit, Qt.Key.Key_Up)
        self.assertEqual(edit.text(), "circle 3cm 3cm 1cm")
        QTest.keyClick(edit, Qt.Key.Key_Up)
        self.assertEqual(edit.text(), "rect 0 0 5mm 5mm")
        # One more Up past the oldest entry -> clamped, stays put.
        QTest.keyClick(edit, Qt.Key.Key_Up)
        self.assertEqual(edit.text(), "rect 0 0 5mm 5mm")

        QTest.keyClick(edit, Qt.Key.Key_Down)
        QTest.keyClick(edit, Qt.Key.Key_Down)
        QTest.keyClick(edit, Qt.Key.Key_Down)
        self.assertEqual(edit.text(), "")

    def test_pending_text_preserved_across_history_navigation(self):
        # Text typed but not yet submitted must survive a trip through
        # history and back, so Down-ing all the way past the newest
        # entry restores exactly what the user was typing.
        edit = ConsoleLineEdit()
        edit.record("help")
        edit.setText("not yet submitted")

        QTest.keyClick(edit, Qt.Key.Key_Up)
        self.assertEqual(edit.text(), "help")
        QTest.keyClick(edit, Qt.Key.Key_Down)
        self.assertEqual(edit.text(), "not yet submitted")

    def test_consecutive_duplicate_command_not_recorded_twice(self):
        edit = ConsoleLineEdit()
        edit.record("rect 0 0 5mm 5mm")
        edit.record("help")
        edit.record("help")

        QTest.keyClick(edit, Qt.Key.Key_Up)
        self.assertEqual(edit.text(), "help")
        QTest.keyClick(edit, Qt.Key.Key_Up)
        self.assertEqual(edit.text(), "rect 0 0 5mm 5mm")


@unittest.skipUnless(HAS_QT, "PyQt6 not installed")
class TestAppIcon(unittest.TestCase):
    """build_app_icon() (madgrav/qt/qt_theme.py): renders the MadGrav
    monogram natively via QPainter primitives (no external image file),
    used for the window/taskbar icon. Pure function, no kernel needed."""

    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def test_icon_renders_at_multiple_sizes_with_real_content(self):
        for size in (16, 64, 256):
            icon = build_app_icon(size)
            self.assertFalse(icon.isNull())
            pm = icon.pixmap(size, size)
            self.assertEqual((pm.width(), pm.height()), (size, size))

            # Not just a blank/transparent square -- some sampled pixel
            # must have real (non-zero-alpha) content, confirming the
            # monogram was actually drawn, not an empty canvas.
            img = pm.toImage()
            step = max(1, size // 8)
            has_content = any(
                img.pixelColor(x, y).alpha() > 0
                for x in range(0, size, step)
                for y in range(0, size, step)
            )
            self.assertTrue(has_content, f"no visible content at size={size}")


@unittest.skipUnless(HAS_QT, "PyQt6 not installed")
class TestBuildToolIcon(unittest.TestCase):
    """build_tool_icon() (madgrav/qt/qt_theme.py): the left draw-tool
    panel's flat-line glyph icons (select/pan/rect/ellipse/line/text),
    replacing the emoji-prefixed text labels those buttons used to
    carry. Pure function, no kernel needed."""

    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def test_every_known_glyph_renders_real_content(self):
        for name in ("select", "pan", "rect", "ellipse", "line", "text"):
            icon = build_tool_icon(name, size=22, color="#E2E2E9")
            self.assertFalse(icon.isNull(), name)
            pm = icon.pixmap(22, 22)
            self.assertEqual((pm.width(), pm.height()), (22, 22), name)
            img = pm.toImage()
            has_content = any(
                img.pixelColor(x, y).alpha() > 0
                for x in range(22)
                for y in range(22)
            )
            self.assertTrue(has_content, f"no visible content for glyph={name}")

    def test_unknown_name_yields_a_blank_but_valid_icon(self):
        # No "else" branch raises for an unrecognized name -- just an
        # empty transparent icon rather than a crash, matching how a
        # typo'd/future-removed tool key should fail (silently, not
        # by breaking panel construction).
        icon = build_tool_icon("not-a-real-tool", size=22)
        self.assertFalse(icon.isNull())
        pm = icon.pixmap(22, 22)
        img = pm.toImage()
        self.assertTrue(all(img.pixelColor(x, y).alpha() == 0 for x in range(22) for y in range(22)))

    def test_glyph_color_is_actually_applied(self):
        icon_red = build_tool_icon("rect", size=22, color="#FF0000")
        img = icon_red.pixmap(22, 22).toImage()
        colored_pixels = [
            img.pixelColor(x, y)
            for x in range(22)
            for y in range(22)
            if img.pixelColor(x, y).alpha() > 0
        ]
        self.assertTrue(colored_pixels)
        self.assertTrue(all(c.red() > c.green() and c.red() > c.blue() for c in colored_pixels))


@unittest.skipUnless(HAS_QT, "PyQt6 not installed")
class TestScanSerialPorts(unittest.TestCase):
    """_scan_serial_ports() (madgrav/qt/qt_device_wizard.py): the
    docstring promises it "Returns [] (never raises)" even if pyserial
    isn't installed or a real scan fails -- verified directly here
    rather than trusting that claim. Pure function, no Qt widgets
    touched, so no QApplication needed."""

    def test_real_scan_returns_a_list_without_raising(self):
        result = _scan_serial_ports()
        self.assertIsInstance(result, list)

    def test_returns_empty_list_when_comports_raises(self):
        import serial.tools.list_ports as list_ports_mod

        original = list_ports_mod.comports
        list_ports_mod.comports = lambda: (_ for _ in ()).throw(OSError("boom"))
        try:
            self.assertEqual(_scan_serial_ports(), [])
        finally:
            list_ports_mod.comports = original


if __name__ == "__main__":
    unittest.main()
