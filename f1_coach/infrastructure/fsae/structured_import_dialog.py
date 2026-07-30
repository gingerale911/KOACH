"""structured_import_dialog.py — JSON/XLSX'ten doğrudan VehicleSession oluşturma.

CAN etiketleme akışına alternatif, tek adımlı bir yol: takımın elinde
zaten yapılandırılmış telemetri verisi varsa, ham CAN log + manuel
etiketleme sürecinden hiç geçmeden bir VehicleSession oluşturur.
decoded_telemetry_file doğrudan yazılır, raw_can_file boş bırakılır —
bu session'ın "düzeltilebilir" olma özelliği yoktur (ham veri saklanmaz),
çünkü zaten CAN kaynaklı değildir.
"""

import uuid
from pathlib import Path

from PyQt6.QtWidgets import QDialog, QFileDialog, QHBoxLayout, QLabel, QLineEdit, QPushButton, QVBoxLayout

from f1_coach.domain.models.fsae.vehicle_session import VehicleSession
from f1_coach.domain.ports.fsae.vehicle_session_repository import VehicleSessionRepository
from f1_coach.infrastructure.fsae.structured_telemetry_reader import read_structured_telemetry
from f1_coach.infrastructure.logging.logger import get_logger
from f1_coach.infrastructure.storage.fsae.parquet_writer import write_decoded_telemetry
from f1_coach.presentation.background_worker import BackgroundWorker

logger = get_logger(__name__)

_FILE_FILTER = "Telemetri Dosyaları (*.json *.xlsx *.xls);;Tüm Dosyalar (*)"


class _StructuredImportDialog(QDialog):
    """Dosya seçimi + session adı + arka planda okuma/yazma yapan diyalog."""

    def __init__(self, parent, vehicle_session_repo: VehicleSessionRepository) -> None:
        super().__init__(parent)
        self._session_repo = vehicle_session_repo
        self._selected_file_path = ""
        self._worker: BackgroundWorker | None = None
        self.new_session_id: int | None = None

        self.setWindowTitle("Hazır Dosyadan Session Ekle")
        self.setMinimumWidth(420)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(14)

        layout.addWidget(QLabel(
            "JSON ya da Excel (.xlsx) formatında, zaten yapılandırılmış bir "
            "telemetri dosyası seç. Uzun (timestamp/channel_name/value) ya da "
            "geniş (zaman + kanal sütunları) formatlar otomatik algılanır."
        ))

        file_row = QHBoxLayout()
        self._select_button = QPushButton("Dosya Seç")
        self._select_button.setObjectName("PrimaryButton")
        self._select_button.clicked.connect(self._on_select_file)
        file_row.addWidget(self._select_button)

        self._file_label = QLabel("Henüz dosya seçilmedi")
        file_row.addWidget(self._file_label, stretch=1)
        layout.addLayout(file_row)

        layout.addWidget(QLabel("Session Adı:"))
        self._name_input = QLineEdit()
        layout.addWidget(self._name_input)

        self._status_label = QLabel("")
        self._status_label.setWordWrap(True)
        layout.addWidget(self._status_label)

        button_row = QHBoxLayout()
        button_row.addStretch(1)
        self._cancel_button = QPushButton("Vazgeç")
        self._cancel_button.clicked.connect(self.reject)
        button_row.addWidget(self._cancel_button)

        self._import_button = QPushButton("İçe Aktar")
        self._import_button.setObjectName("PrimaryButton")
        self._import_button.setEnabled(False)
        self._import_button.clicked.connect(self._on_import)
        button_row.addWidget(self._import_button)
        layout.addLayout(button_row)

    def _on_select_file(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "Telemetri Dosyası Seç", "", _FILE_FILTER)
        if not path:
            return
        self._selected_file_path = path
        self._file_label.setText(Path(path).name)
        if not self._name_input.text().strip():
            self._name_input.setText(Path(path).stem)
        self._import_button.setEnabled(True)

    def _on_import(self) -> None:
        if not self._selected_file_path:
            return

        self._status_label.setStyleSheet("color: inherit;")
        self._status_label.setText("Dosya okunuyor...")
        self._import_button.setEnabled(False)
        self._select_button.setEnabled(False)

        self._worker = BackgroundWorker(self._read_and_write, self._selected_file_path)
        self._worker.finished.connect(self._on_worker_finished)
        self._worker.failed.connect(self._on_worker_failed)
        self._worker.start()

    def _read_and_write(self, file_path: str):
        """Arka plan thread'inde çalışır — hiçbir widget'a dokunmaz."""
        points = read_structured_telemetry(file_path)
        session_identifier = uuid.uuid4().hex
        decoded_path = write_decoded_telemetry(session_identifier, points)
        return points, decoded_path

    def _on_worker_finished(self, result) -> None:
        points, decoded_path = result

        name = self._name_input.text().strip() or Path(self._selected_file_path).stem
        session = VehicleSession(
            name=name,
            source_filename=Path(self._selected_file_path).name,
            raw_can_file="",
            decoded_telemetry_file=decoded_path,
        )
        self._session_repo.save(session)
        self.new_session_id = session.id

        logger.info(
            "FSAE session hazır dosyadan içe aktarıldı: id=%d name=%s points=%d",
            session.id, session.name, len(points),
        )
        self.accept()

    def _on_worker_failed(self, exc: Exception) -> None:
        logger.error("Hazır dosya içe aktarımı başarısız: %s", exc)
        self._status_label.setStyleSheet("color: #E10600;")
        self._status_label.setText(f"⚠ Hata: {exc}")
        self._import_button.setEnabled(True)
        self._select_button.setEnabled(True)


def import_structured_session(parent, vehicle_session_repo: VehicleSessionRepository) -> int | None:
    """Diyaloğu gösterir, başarılı olursa yeni session'ın id'sini döner."""
    dialog = _StructuredImportDialog(parent, vehicle_session_repo)
    if dialog.exec() == QDialog.DialogCode.Accepted:
        return dialog.new_session_id
    return None