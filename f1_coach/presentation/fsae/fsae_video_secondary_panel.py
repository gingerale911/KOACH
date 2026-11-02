"""FSAEVideoSecondaryPanel — "Video + Pist Takip" alt uygulamasının sekme çubuğu."""

from PyQt6.QtCore import pyqtSignal
from PyQt6.QtWidgets import QHBoxLayout, QPushButton, QWidget

_PANEL_HEIGHT = 48


class FSAEVideoSecondaryPanel(QWidget):
    """Video + Pist Takip sekmelerini barındıran yatay sekme çubuğu.

    Signals:
        session_select_clicked: "Session Seç" sekmesi seçildi.
        video_sync_clicked:     "Video & Senkron" sekmesi seçildi.
        playback_clicked:       "Oynatım" sekmesi seçildi.
    """

    session_select_clicked = pyqtSignal()
    video_sync_clicked = pyqtSignal()
    playback_clicked = pyqtSignal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setFixedHeight(_PANEL_HEIGHT)
        self.setObjectName("SecondaryPanel")
        self.hide()

        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 8, 16, 8)
        layout.setSpacing(8)

        self._session_select_button = QPushButton("Select Session")
        self._session_select_button.setStyleSheet("font-size: 12px; padding: 5px 12px;")
        self._session_select_button.setObjectName("PrimaryButton")
        self._session_select_button.clicked.connect(self.session_select_clicked.emit)
        layout.addWidget(self._session_select_button)

        self._video_sync_button = QPushButton("Video Sync")
        self._video_sync_button.setStyleSheet("font-size: 12px; padding: 5px 12px;")
        self._video_sync_button.setObjectName("PrimaryButton")
        self._video_sync_button.clicked.connect(self.video_sync_clicked.emit)
        layout.addWidget(self._video_sync_button)

        self._playback_button = QPushButton("Playback")
        self._playback_button.setStyleSheet("font-size: 12px; padding: 5px 12px;")
        self._playback_button.setObjectName("PrimaryButton")
        self._playback_button.clicked.connect(self.playback_clicked.emit)
        layout.addWidget(self._playback_button)

        layout.addStretch(1)

    def open_panel(self) -> None:
        self.show()

    def close_panel(self) -> None:
        self.hide()

    def set_navigation_locked(self, locked: bool) -> None:
        self._video_sync_button.setEnabled(not locked)
        self._playback_button.setEnabled(not locked)