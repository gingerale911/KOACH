"""FSAESecondaryPanel — "CAN Veri Etiketleme" alt uygulamasının sekme çubuğu.

Yalnızca İçe Aktar ve Etiketleme sekmelerini barındırır — Grafik/inceleme
işi artık "Video + Pist Takip" alt uygulamasında (bkz. fsae_video_secondary_panel.py).
"""

from PyQt6.QtCore import pyqtSignal
from PyQt6.QtWidgets import QHBoxLayout, QPushButton, QWidget

_PANEL_HEIGHT = 48


class FSAESecondaryPanel(QWidget):
    """CAN Veri Etiketleme sekmelerini barındıran yatay sekme çubuğu.

    Signals:
        import_clicked:   "İçe Aktar" sekmesi seçildi.
        labeling_clicked: "Etiketleme" sekmesi seçildi.
    """

    import_clicked = pyqtSignal()
    labeling_clicked = pyqtSignal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setFixedHeight(_PANEL_HEIGHT)
        self.setObjectName("SecondaryPanel")
        self.hide()

        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 8, 16, 8)
        layout.setSpacing(8)

        self._import_button = QPushButton("Import")
        self._import_button.setObjectName("PrimaryButton")
        self._import_button.clicked.connect(self.import_clicked.emit)
        layout.addWidget(self._import_button)

        self._labeling_button = QPushButton("Labeling")
        self._labeling_button.setObjectName("PrimaryButton")
        self._labeling_button.clicked.connect(self.labeling_clicked.emit)
        layout.addWidget(self._labeling_button)

        layout.addStretch(1)

    def open_panel(self) -> None:
        self.show()

    def close_panel(self) -> None:
        self.hide()

    def set_navigation_locked(self, locked: bool) -> None:
        self._labeling_button.setEnabled(not locked)