"""AcSecondaryPanel — Assetto Corsa (AC FSAE) alt uygulamasının sekme çubuğu.

F125'in secondary_panel.py'sine paralel, ama pist haritası özelliği
olmadığı için (proje kararı) yalnızca üç sekme: Canlı Bağlantı,
Lap Analizi, Session Geçmişi.
"""

from PyQt6.QtCore import pyqtSignal
from PyQt6.QtWidgets import QHBoxLayout, QPushButton, QWidget

_PANEL_HEIGHT = 48


class AcSecondaryPanel(QWidget):
    """AC sekmelerini barındıran yatay sekme çubuğu.

    Signals:
        live_clicked:            "Canlı Bağlantı" sekmesi seçildi.
        lap_analysis_clicked:    "Lap Analizi" sekmesi seçildi.
        session_history_clicked: "Session Geçmişi" sekmesi seçildi.
    """

    live_clicked = pyqtSignal()
    lap_analysis_clicked = pyqtSignal()
    session_history_clicked = pyqtSignal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setFixedHeight(_PANEL_HEIGHT)
        self.setObjectName("SecondaryPanel")
        self.hide()

        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 4, 16, 4)
        layout.setSpacing(8)

        self._live_button = QPushButton("Live Connection")
        self._live_button.setObjectName("PrimaryButton")
        self._live_button.clicked.connect(self.live_clicked.emit)
        layout.addWidget(self._live_button)

        self._lap_analysis_button = QPushButton("Lap Analysis")
        self._lap_analysis_button.setObjectName("PrimaryButton")
        self._lap_analysis_button.clicked.connect(self.lap_analysis_clicked.emit)
        layout.addWidget(self._lap_analysis_button)

        self._session_history_button = QPushButton("Session History")
        self._session_history_button.setObjectName("PrimaryButton")
        self._session_history_button.clicked.connect(self.session_history_clicked.emit)
        layout.addWidget(self._session_history_button)

        layout.addStretch(1)

    def open_panel(self) -> None:
        self.show()

    def close_panel(self) -> None:
        self.hide()

    def set_navigation_locked(self, locked: bool) -> None:
        """Canlı kayıt sürerken diğer sekmeleri kilitler — F125'teki aynı desen."""
        self._lap_analysis_button.setEnabled(not locked)
        self._session_history_button.setEnabled(not locked)