"""
Guided machine setup wizard for the PyQt6 GUI.

Walks the same "dev_info" registry the classic wx "New Device" dialog
uses (madgrav/gui/devicepanel.py) so every device type any plugin
registers (GRBL, Ruida, Lihuiyu/K40, Balor/Galvo, Moshi, Newly...) shows
up automatically -- nothing here is hardcoded to a specific laser brand.
Creation goes through the same "device add -i <profile> -l <label>"
console command the wx dialog issues, so the result is identical either
way.
"""

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QComboBox,
    QFormLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QVBoxLayout,
    QWizard,
    QWizardPage,
)


def _scan_serial_ports():
    """Best-effort serial port scan. Returns [] (never raises) if
    pyserial isn't installed or nothing is plugged in -- most machines
    this wizard supports (K40/Lihuiyu, Balor/Galvo) are USB-direct and
    have no serial port to detect at all, so an empty result is normal."""
    try:
        import serial.tools.list_ports

        return [(p.device, str(p)) for p in serial.tools.list_ports.comports()]
    except Exception:
        return []


class _MachineSelectPage(QWizardPage):
    """Step 1: pick a machine type from every registered dev_info entry."""

    def __init__(self, context, parent=None):
        super().__init__(parent)
        self.context = context
        self.setTitle("Choisissez votre machine")
        self.setSubTitle(
            "Sélectionnez le modèle qui correspond à votre graveuse/découpeuse laser."
        )
        layout = QVBoxLayout(self)

        self.ports = _scan_serial_ports()
        if self.ports:
            names = ", ".join(display for _device, display in self.ports)
            info_label = QLabel(f"Ports série détectés : {names}")
        else:
            info_label = QLabel(
                "Aucun port série détecté pour l'instant -- normal pour une "
                "machine USB directe (K40, graveuse fibre). Branchez votre "
                "machine avant de continuer si elle utilise un port série."
            )
        info_label.setWordWrap(True)
        layout.addWidget(info_label)

        self.list_widget = QListWidget(self)
        layout.addWidget(self.list_widget)

        dev_infos = list(context.kernel.find("dev_info"))
        dev_infos.sort(key=lambda entry: entry[0].get("priority", 0), reverse=True)
        last_family = None
        for info, name, sname in dev_infos:
            family = info.get("family", "")
            if family != last_family:
                header = QListWidgetItem(f"— {family} —")
                header.setFlags(Qt.ItemFlag.NoItemFlags)
                self.list_widget.addItem(header)
                last_family = family
            item = QListWidgetItem(f"    {info.get('friendly_name', sname)}")
            item.setData(Qt.ItemDataRole.UserRole, (sname, info))
            self.list_widget.addItem(item)

        self.list_widget.currentItemChanged.connect(
            lambda *_args: self.completeChanged.emit()
        )

    def isComplete(self):
        item = self.list_widget.currentItem()
        return item is not None and item.data(Qt.ItemDataRole.UserRole) is not None

    def selected_entry(self):
        """Returns (sname, dev_info_dict) for the highlighted machine, or
        None if nothing selectable is highlighted (e.g. a family header)."""
        item = self.list_widget.currentItem()
        if item is None:
            return None
        return item.data(Qt.ItemDataRole.UserRole)


class _ConnectionPage(QWizardPage):
    """Step 2: name the device and, if relevant, pick its serial port."""

    def __init__(self, select_page, parent=None):
        super().__init__(parent)
        self.select_page = select_page
        self.setTitle("Connexion et nom")
        self.setSubTitle(
            "Confirmez le port (si nécessaire) et donnez un nom à cette machine."
        )

        layout = QFormLayout(self)
        self.label_edit = QLineEdit(self)
        layout.addRow("Nom :", self.label_edit)

        self.port_combo = QComboBox(self)
        self.port_combo.setEditable(True)
        layout.addRow("Port série :", self.port_combo)

        note = QLabel(
            "Laissez vide si la machine se connecte en USB direct (K40, "
            "graveuse fibre) -- seules les machines à port série "
            "(GRBL, Ruida...) en ont besoin."
        )
        note.setWordWrap(True)
        layout.addRow(note)

    def initializePage(self):
        entry = self.select_page.selected_entry()
        if entry is None:
            return
        sname, info = entry
        self.label_edit.setText(info.get("friendly_name", sname))

        self.port_combo.clear()
        self.port_combo.addItem("", None)
        for device_path, display in self.select_page.ports:
            self.port_combo.addItem(display, device_path)
        if self.select_page.ports:
            self.port_combo.setCurrentIndex(1)  # default to the first detected port

    def chosen_label(self):
        return self.label_edit.text().strip()

    def chosen_port(self):
        idx = self.port_combo.currentIndex()
        data = self.port_combo.itemData(idx) if idx >= 0 else None
        if data:
            return data
        return self.port_combo.currentText().strip() or None


class _ConfirmPage(QWizardPage):
    """Step 3: read-only summary. Nothing here has side effects -- actual
    device creation happens once, in DeviceSetupWizard.accept(), so
    hitting Cancel on this page never leaves a half-created device."""

    def __init__(self, select_page, connection_page, parent=None):
        super().__init__(parent)
        self.select_page = select_page
        self.connection_page = connection_page
        self.setTitle("Vérifier et créer")
        self.setFinalPage(True)
        layout = QVBoxLayout(self)
        self.summary_label = QLabel("")
        self.summary_label.setWordWrap(True)
        layout.addWidget(self.summary_label)

    def initializePage(self):
        entry = self.select_page.selected_entry()
        if entry is None:
            self.summary_label.setText("Aucune machine sélectionnée.")
            return
        _sname, info = entry
        label = self.connection_page.chosen_label() or info.get("friendly_name", "")
        port = self.connection_page.chosen_port()
        lines = [
            f"Machine : {info.get('friendly_name', '')}",
            f"Nom : {label}",
            f"Port série : {port}" if port else "Port série : (aucun -- USB direct)",
            "",
            "Cliquez sur Terminer pour créer et activer cette machine.",
        ]
        self.summary_label.setText("\n".join(lines))


class DeviceSetupWizard(QWizard):
    """Detect-and-configure wizard: creates a real device via the same
    "device add" console command the classic wx UI's New Device dialog
    uses, then applies the chosen serial port if the device has one."""

    def __init__(self, context, parent=None):
        super().__init__(parent)
        self.context = context
        self.setWindowTitle("Assistant de Configuration de Machine")
        self.setMinimumSize(560, 420)

        self.select_page = _MachineSelectPage(context, self)
        self.connection_page = _ConnectionPage(self.select_page, self)
        self.confirm_page = _ConfirmPage(self.select_page, self.connection_page, self)
        self.addPage(self.select_page)
        self.addPage(self.connection_page)
        self.addPage(self.confirm_page)

        self.created_label = None  # set by accept() -- what the caller can report

    def accept(self):
        # Only close the wizard if a device was actually created -- a
        # user who clicks Terminer and sees the wizard vanish has no
        # reason to think anything went wrong, so a silent failure here
        # would be worse than in most places (same class of bug as
        # qt_main.py's _save_to(), which had the identical "looks like
        # success either way" problem).
        if self._create_device():
            super().accept()

    def _create_device(self) -> bool:
        entry = self.select_page.selected_entry()
        if entry is None:
            return False
        sname, info = entry
        label = self.connection_page.chosen_label() or info.get("friendly_name", sname)
        # The console parser has no escape sequence for a literal double
        # quote inside a quoted argument -- fold it to a single quote
        # rather than let it terminate the string early (same fix as the
        # canvas's Text tool).
        safe_label = label.replace('"', "'")
        port = self.connection_page.chosen_port()

        try:
            self.context.console(f'device add -i {sname} -l "{safe_label}"\n')
        except Exception as ex:
            QMessageBox.warning(
                self, "Assistant de Configuration", f"Échec de la création :\n{ex}"
            )
            return False

        # "device add" activates the new device as a side effect (see
        # madgrav/device/basedevice.py's device_start()) -- if that
        # didn't happen, the command failed. The likely failure paths
        # there (invalid device_info entry, missing provider) raise
        # CommandSyntaxError, which the kernel's console dispatcher
        # catches internally and reports via a channel message rather
        # than propagating it back to this console() call -- so the
        # try/except above alone would miss this and report success
        # anyway. Checking the actual resulting state catches it.
        device = getattr(self.context, "device", None)
        if device is None or getattr(device, "label", None) != safe_label:
            QMessageBox.warning(
                self,
                "Assistant de Configuration",
                "La création de la machine a échoué "
                "(profil ou pilote introuvable pour ce type de machine).",
            )
            return False

        if port and hasattr(device, "serial_port"):
            device.serial_port = port

        self.created_label = safe_label
        return True
