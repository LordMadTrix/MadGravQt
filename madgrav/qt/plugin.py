"""
Kernel Plugin registering the PyQt6 GUI module for MadGrav.
"""

import sys


def _set_windows_taskbar_identity():
    # Without this, Windows groups the taskbar/pinned icon by the
    # launching executable's AppUserModelID -- for a python.exe/
    # pythonw.exe-launched app that's the generic Python interpreter
    # icon, regardless of what setWindowIcon() sets on the window
    # itself. Must run before the window is created to take effect.
    if sys.platform != "win32":
        return
    try:
        import ctypes

        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(
            "MadGrav.QtWorkstation"
        )
    except Exception:
        pass


def _show_or_create_qt_window(kernel):
    """Returns True if an existing window was reused (just raised to
    front), False if a fresh one still needs to be created. Without this,
    invoking "qtgui" a second time (e.g. after --qt already opened one at
    boot) unconditionally built a duplicate window and overwrote
    kernel.root.qt_main_window -- orphaning the first one: preshutdown
    only ever knows about the CURRENT reference, so the orphaned window's
    kernel signal listeners (activate;device, refresh_tree, etc.) would
    never get unlistened, and the window itself would never be asked to
    close during a real shutdown."""
    existing = getattr(kernel.root, "qt_main_window", None)
    if existing is None:
        return False
    try:
        existing.show()
        existing.raise_()
        existing.activateWindow()
        return True
    except RuntimeError:
        # The existing reference points to a Qt object already torn down
        # at the C/C++ level (e.g. the user closed it directly without
        # going through the kernel's own shutdown path) -- fall through
        # and let the caller create a fresh one.
        kernel.root.qt_main_window = None
        return False


def plugin(kernel, lifecycle=None):
    if lifecycle == "plugins":
        return []

    elif lifecycle == "poststart":
        if hasattr(kernel.args, "qt") and kernel.args.qt:
            if kernel.is_shutdown:
                # A shutdown was already requested earlier in poststart
                # (e.g. "-e quit"). Opening the window now would leave a
                # dead-kernel zombie window with nothing left to drive it.
                return

            _set_windows_taskbar_identity()

            from PyQt6.QtWidgets import QApplication
            from madgrav.qt.qt_main import MadGravQtMainWindow

            app = QApplication.instance()
            if app is None:
                app = QApplication(sys.argv)

            kernel.root.qt_main_window = MadGravQtMainWindow(kernel.root)
            kernel.root.qt_main_window.show()
            app.exec()

    elif lifecycle == "preshutdown":
        # The kernel can be told to shut down from inside the Qt session
        # itself (e.g. typing "quit"/"shutdown" in the console dock, or a
        # remote consoleserver connection) -- and that can happen from a
        # thread other than the Qt GUI thread. Qt widgets may only be
        # closed from their own thread, so this only emits a signal; the
        # window's own queued-connection slot marshals close() onto the
        # GUI thread (see MadGravQtMainWindow.shutdown_requested).
        qt_main_window = getattr(kernel.root, "qt_main_window", None)
        if qt_main_window is not None:
            # The kernel lifecycle can legitimately reach "preshutdown"
            # twice for one shutdown: once via the recursive call that
            # processes "quit", and again when the original call (blocked
            # in app.exec()) resumes once the window actually closes.
            # Clear the reference before emitting so the second pass is a
            # no-op instead of touching an already-destroyed Qt window.
            kernel.root.qt_main_window = None
            try:
                qt_main_window.shutdown_requested.emit()
            except RuntimeError:
                # Rare race: Qt already tore down the underlying C/C++
                # window object (e.g. the user closed it directly) before
                # this shutdown pass got here -- nothing left to signal.
                pass

    elif lifecycle == "register":
        pass

    elif lifecycle == "boot":
        pass

    elif lifecycle == "service":
        pass

    elif lifecycle == "module":
        pass

    elif lifecycle == "command":

        @kernel.console_command("qtgui", help="Démarre l'interface graphique PyQt6 moderne")
        def run_qt_gui(command, channel, _, **kwargs):
            _set_windows_taskbar_identity()

            from PyQt6.QtWidgets import QApplication

            app = QApplication.instance()
            if app is None:
                app = QApplication(sys.argv)

            if not _show_or_create_qt_window(kernel):
                from madgrav.qt.qt_main import MadGravQtMainWindow

                kernel.root.qt_main_window = MadGravQtMainWindow(kernel.root)
                kernel.root.qt_main_window.show()

            if not app.property("is_running"):
                app.setProperty("is_running", True)
                app.exec()
