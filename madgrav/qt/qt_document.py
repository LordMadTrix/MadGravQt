from __future__ import annotations

import os
from typing import Optional, TYPE_CHECKING
from PyQt6.QtWidgets import QWidget, QVBoxLayout
from madgrav.qt.qt_canvas import MadGravQtCanvas

if TYPE_CHECKING:
    from madgrav.qt.qt_main import MadGravQtMainWindow


class DocumentTab(QWidget):
    """Encapsulates a single open document with its own canvas, file path, and modified state."""

    def __init__(
        self,
        main_window: MadGravQtMainWindow,
        title: str = "Sans Titre",
        file_path: Optional[str] = None,
        parent: Optional[QWidget] = None,
    ):
        super().__init__(parent or main_window)
        self.main_window = main_window
        self.title = title
        self.file_path = file_path
        self.is_modified = False

        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.setSpacing(0)

        # Create isolated canvas for this document
        context = getattr(main_window, "context", main_window)
        self.canvas = MadGravQtCanvas(context, parent=self)
        self.layout.addWidget(self.canvas)

    def set_file_path(self, path: Optional[str]):
        self.file_path = path
        if path:
            self.title = os.path.basename(path)
        else:
            self.title = "Sans Titre"

    def set_modified(self, modified: bool = True):
        self.is_modified = modified
        display_title = f"{self.title}*" if self.is_modified else self.title
        if hasattr(self.main_window, "doc_tabs"):
            idx = self.main_window.doc_tabs.indexOf(self)
            if idx >= 0:
                self.main_window.doc_tabs.setTabText(idx, display_title)
