"""FSAEVideoSessionPickerPage — Video + Pist Takip'in "Session Seç" sekmesi.

Yalnızca etiketlenmiş (is_labeled=True) session'lar listelenir — henüz
etiketlenmemiş bir session'ın grafiğe dökülecek verisi yok.
"""

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import QFrame, QHBoxLayout, QLabel, QScrollArea, QVBoxLayout, QWidget
from PyQt6.QtWidgets import QPushButton

from f1_coach.infrastructure.fsae.structured_import_dialog import import_structured_session
from f1_coach.domain.ports.fsae.vehicle_session_repository import VehicleSessionRepository
from f1_coach.presentation import theme as theme_module


class _SessionRow(QFrame):
    clicked = pyqtSignal(int)

    def __init__(self, session_id: int, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._session_id = session_id
        self.setCursor(Qt.CursorShape.PointingHandCursor)

    def mousePressEvent(self, event) -> None:  # type: ignore[no-untyped-def]
        self.clicked.emit(self._session_id)
        super().mousePressEvent(event)


class FSAEVideoSessionPickerPage(QWidget):
    """Video ile incelenecek, etiketlenmiş bir session seçtiren ekran.

    Signals:
        session_selected: Bir session'a tıklandı, session_id taşır.
    """

    session_selected = pyqtSignal(int)

    def __init__(self, vehicle_session_repo: VehicleSessionRepository, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._session_repo = vehicle_session_repo

        outer_layout = QVBoxLayout(self)
        outer_layout.setContentsMargins(0, 0, 0, 0)

        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setFrameShape(QFrame.Shape.NoFrame)
        outer_layout.addWidget(scroll_area)

        content = QWidget()
        scroll_area.setWidget(content)

        layout = QVBoxLayout(content)
        layout.setContentsMargins(32, 24, 32, 24)
        layout.setSpacing(14)

        title = QLabel("Session Seç")
        title.setStyleSheet("font-size: 20px; font-weight: 700;")
        layout.addWidget(title)

        subtitle = QLabel("Video ile birlikte incelemek istediğin, etiketlenmiş bir session seç.")
        subtitle.setStyleSheet(f"color: {theme_module.TEXT_SECONDARY}; font-size: 12px;")
        layout.addWidget(subtitle)

        self._add_structured_button = QPushButton("Hazır Dosya Ekle")
        self._add_structured_button.setObjectName("PrimaryButton")
        self._add_structured_button.clicked.connect(self._on_add_structured_session)
        layout.addWidget(self._add_structured_button)

        self._empty_label = QLabel("Henüz etiketlenmiş bir FSAE session'ı yok.")
        self._empty_label.setStyleSheet(f"color: {theme_module.TEXT_MUTED}; font-size: 13px;")
        self._empty_label.hide()
        layout.addWidget(self._empty_label)

        self._list_container = QVBoxLayout()
        self._list_container.setSpacing(8)
        layout.addLayout(self._list_container)

        layout.addStretch(1)

    def refresh(self) -> None:
        while self._list_container.count():
            item = self._list_container.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        sessions = [s for s in self._session_repo.get_all() if s.is_labeled]

        self._empty_label.setVisible(not sessions)

        for session in sessions:
            row = _SessionRow(session.id)
            row.setStyleSheet(
                f"QFrame {{ background-color: {theme_module.SURFACE}; border: 1px solid {theme_module.BORDER};"
                "  border-radius: 10px; }"
                "QFrame:hover { border: 1px solid #9B30FF; }"
            )
            row_layout = QHBoxLayout(row)
            row_layout.setContentsMargins(14, 10, 14, 10)

            name_label = QLabel(session.name)
            name_label.setStyleSheet("font-weight: 600; font-size: 13px; background: transparent; border: none;")
            row_layout.addWidget(name_label, stretch=1)

            date_label = QLabel(session.imported_at.strftime("%d.%m.%Y"))
            date_label.setStyleSheet(f"color: {theme_module.TEXT_SECONDARY}; font-size: 12px; background: transparent; border: none;")
            row_layout.addWidget(date_label)

            row.clicked.connect(self.session_selected.emit)
            self._list_container.addWidget(row)

    def _on_add_structured_session(self) -> None:
        new_session_id = import_structured_session(self, self._session_repo)
        if new_session_id is not None:
            self.refresh()
            self.session_selected.emit(new_session_id)