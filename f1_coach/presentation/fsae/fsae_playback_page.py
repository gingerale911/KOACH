"""FSAEPlaybackPage — Oynatım sekmesi.

Video ve telemetri grafiğini yan yana gösterir; video oynarken, sync_offset
kullanılarak grafikteki dikey imleç çizgisi telemetri zamanına göre hareket
eder (build_cursor_update_js ile, tüm grafiği yeniden çizmeden).

Bu sayfa yalnızca hem video_file hem sync_offset_seconds ayarlanmış
session'lar için kullanılabilir — eksikse kullanıcıyı Video & Senkron
sekmesine yönlendiren bir uyarı gösterir.

Telemetri Parquet dosyasının okunması BackgroundWorker ile arka plan
thread'inde yapılır — büyük dosyalarda bu işlem UI'ı bloklamasın diye.
"""

from pathlib import Path

from PyQt6.QtCore import QUrl, Qt, pyqtSignal
from PyQt6.QtMultimedia import QAudioOutput, QMediaPlayer
from PyQt6.QtMultimediaWidgets import QVideoWidget
from PyQt6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QScrollArea,
    QSlider,
    QSplitter,
    QVBoxLayout,
    QWidget,
)

from f1_coach.domain.ports.fsae.vehicle_session_repository import VehicleSessionRepository
from f1_coach.infrastructure.logging.logger import get_logger
from f1_coach.infrastructure.storage.fsae.parquet_writer import read_decoded_telemetry
from f1_coach.presentation import theme as theme_module
from f1_coach.presentation.background_worker import BackgroundWorker
from f1_coach.presentation.charts.plotly_chart_widget import PlotlyChartWidget
from f1_coach.presentation.confirm_dialog import notify
from f1_coach.presentation.fsae.charts.fsae_chart_builder import (
    build_cursor_update_js,
    build_multi_channel_html,
    compute_chart_height,
)

logger = get_logger(__name__)

_DIV_ID = "fsae_playback_chart"


def _format_seconds(seconds: float) -> str:
    minutes, secs = divmod(max(0.0, seconds), 60)
    return f"{int(minutes)}:{secs:06.3f}"


class FSAEPlaybackPage(QWidget):
    """Video + telemetri senkron oynatım ekranı.

    Signals:
        session_finished: "Session'ı Bitir" butonuna basıldı.
        sync_needed:      Bu session için video/senkron eksik, kullanıcı
                          Video & Senkron sekmesine yönlendirilmeli.
    """

    session_finished = pyqtSignal()
    sync_needed = pyqtSignal(int)

    def __init__(self, vehicle_session_repo: VehicleSessionRepository, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._session_repo = vehicle_session_repo
        self._current_session = None
        self._telemetry_df = None
        self._num_selected_channels = 0
        self._worker: BackgroundWorker | None = None

        layout = QVBoxLayout(self)
        layout.setContentsMargins(32, 24, 32, 24)
        layout.setSpacing(14)

        self._header_label = QLabel("Oynatım")
        self._header_label.setStyleSheet("font-size: 20px; font-weight: 700;")
        layout.addWidget(self._header_label)

        # --- Eksik senkron uyarısı ---
        self._missing_sync_frame = QFrame()
        missing_layout = QVBoxLayout(self._missing_sync_frame)
        missing_label = QLabel(
            "Bu session için video yüklenmemiş ya da senkron noktası belirlenmemiş."
        )
        missing_label.setWordWrap(True)
        missing_layout.addWidget(missing_label)
        self._go_to_sync_button = QPushButton("Video & Senkron'a Git")
        self._go_to_sync_button.setObjectName("PrimaryButton")
        self._go_to_sync_button.clicked.connect(self._on_go_to_sync)
        missing_layout.addWidget(self._go_to_sync_button)
        layout.addWidget(self._missing_sync_frame)

        # --- Yatay bölünmüş alan: sol = video (sabit), sağ = kanal listesi + grafik (kaydırılabilir) ---
        self._splitter = QSplitter(Qt.Orientation.Horizontal)
        layout.addWidget(self._splitter, stretch=1)

        # Sol taraf — video hiçbir zaman kaydırılmaz, her zaman görünür kalır
        video_column = QWidget()
        video_layout = QVBoxLayout(video_column)
        video_layout.setContentsMargins(0, 0, 0, 0)

        self._video_widget = QVideoWidget()
        self._video_widget.setMinimumSize(360, 200)
        video_layout.addWidget(self._video_widget, stretch=1)

        self._player = QMediaPlayer(self)
        self._audio_output = QAudioOutput(self)
        self._player.setAudioOutput(self._audio_output)
        self._player.setVideoOutput(self._video_widget)
        self._player.positionChanged.connect(self._on_position_changed)
        self._player.durationChanged.connect(self._on_duration_changed)

        transport_row = QHBoxLayout()
        self._play_pause_button = QPushButton("▶ Oynat")
        self._play_pause_button.setObjectName("PrimaryButton")
        self._play_pause_button.clicked.connect(self._on_toggle_play)
        transport_row.addWidget(self._play_pause_button)

        self._position_slider = QSlider(Qt.Orientation.Horizontal)
        self._position_slider.sliderMoved.connect(self._on_slider_moved)
        transport_row.addWidget(self._position_slider, stretch=1)

        self._position_label = QLabel("0:00.000")
        self._position_label.setStyleSheet(f"color: {theme_module.TEXT_SECONDARY}; font-size: 12px;")
        transport_row.addWidget(self._position_label)
        video_layout.addLayout(transport_row)

        self._splitter.addWidget(video_column)

        # Sağ taraf — kanal listesi (kendi scrollbar'ı) + grafik (dış QScrollArea ile kaydırılabilir)
        right_column = QWidget()
        right_layout = QHBoxLayout(right_column)
        right_layout.setContentsMargins(0, 0, 0, 0)

        self._channel_list = QListWidget()
        self._channel_list.setMaximumWidth(200)
        self._channel_list.itemChanged.connect(self._on_selection_changed)
        right_layout.addWidget(self._channel_list)

        chart_scroll = QScrollArea()
        chart_scroll.setWidgetResizable(True)
        chart_scroll.setFrameShape(QFrame.Shape.NoFrame)
        self._chart = PlotlyChartWidget()
        chart_scroll.setWidget(self._chart)
        right_layout.addWidget(chart_scroll, stretch=1)

        self._splitter.addWidget(right_column)
        self._splitter.setStretchFactor(0, 0)
        self._splitter.setStretchFactor(1, 1)
        self._splitter.setSizes([480, 800])

        self._finish_button = QPushButton("✓ Session'ı Bitir")
        self._finish_button.setObjectName("PrimaryButton")
        self._finish_button.clicked.connect(self.session_finished.emit)
        layout.addWidget(self._finish_button)

    # ------------------------------------------------------------------
    # Yükleme
    # ------------------------------------------------------------------

    def load_session(self, session_id: int) -> None:
        session = self._session_repo.get_by_id(session_id)
        ready = bool(
            session and session.decoded_telemetry_file
            and session.video_file and Path(session.video_file).exists()
            and session.sync_offset_seconds is not None
        )

        self._missing_sync_frame.setVisible(not ready)
        self._splitter.setVisible(ready)
        self._finish_button.setVisible(ready)

        self._current_session = session
        if not ready:
            return

        self._telemetry_df = None
        self._header_label.setText(f"Oynatım — {session.name} (telemetri yükleniyor...)")
        self._splitter.setEnabled(False)

        self._worker = BackgroundWorker(read_decoded_telemetry, session.decoded_telemetry_file)
        self._worker.finished.connect(self._on_telemetry_loaded)
        self._worker.failed.connect(self._on_telemetry_load_failed)
        self._worker.start()

    def _on_telemetry_loaded(self, df) -> None:
        self._telemetry_df = df
        self._header_label.setText(f"Oynatım — {self._current_session.name}")

        channels = sorted(self._telemetry_df["channel_name"].unique())
        self._channel_list.blockSignals(True)
        self._channel_list.clear()
        for channel in channels:
            item = QListWidgetItem(channel)
            item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            item.setCheckState(Qt.CheckState.Unchecked)
            self._channel_list.addItem(item)
        self._channel_list.blockSignals(False)

        self._player.setSource(QUrl.fromLocalFile(self._current_session.video_file))
        self._splitter.setEnabled(True)
        self._render_chart()

    def _on_telemetry_load_failed(self, exc: Exception) -> None:
        logger.error("FSAE telemetri verisi yüklenemedi: %s", exc)
        notify(self, "Yükleme hatası", f"Telemetri verisi okunamadı: {exc}")
        self._missing_sync_frame.setVisible(True)
        self._splitter.setVisible(False)
        self._finish_button.setVisible(False)

    def _on_go_to_sync(self) -> None:
        if self._current_session is not None:
            self.sync_needed.emit(self._current_session.id)

    # ------------------------------------------------------------------
    # Video kontrolleri
    # ------------------------------------------------------------------

    def _on_toggle_play(self) -> None:
        if self._player.playbackState() == QMediaPlayer.PlaybackState.PlayingState:
            self._player.pause()
            self._play_pause_button.setText("▶ Oynat")
        else:
            self._player.play()
            self._play_pause_button.setText("⏸ Duraklat")

    def _on_slider_moved(self, value: int) -> None:
        self._player.setPosition(value)

    def _on_duration_changed(self, duration_ms: int) -> None:
        self._position_slider.setRange(0, duration_ms)

    def _on_position_changed(self, position_ms: int) -> None:
        self._position_slider.blockSignals(True)
        self._position_slider.setValue(position_ms)
        self._position_slider.blockSignals(False)
        self._position_label.setText(_format_seconds(position_ms / 1000.0))

        if self._current_session is None or self._num_selected_channels == 0:
            return
        if self._current_session.sync_offset_seconds is None:
            return

        telemetry_time = position_ms / 1000.0 + self._current_session.sync_offset_seconds
        self._chart.run_javascript(
            build_cursor_update_js(self._num_selected_channels, telemetry_time, div_id=_DIV_ID)
        )

    # ------------------------------------------------------------------
    # Grafik
    # ------------------------------------------------------------------

    def _on_selection_changed(self, _item: QListWidgetItem) -> None:
        self._render_chart()

    def _selected_channels(self) -> list[str]:
        selected = []
        for row in range(self._channel_list.count()):
            item = self._channel_list.item(row)
            if item.checkState() == Qt.CheckState.Checked:
                selected.append(item.text())
        return selected

    def _render_chart(self) -> None:
        if self._telemetry_df is None or self._current_session is None:
            return
        selected = self._selected_channels()
        self._num_selected_channels = len(selected)
        if not selected:
            self._chart.setFixedHeight(200)
            self._chart.render_html("<html><body></body></html>")
            return

        current_telemetry_time = (
            self._player.position() / 1000.0 + self._current_session.sync_offset_seconds
        )
        self._chart.setFixedHeight(compute_chart_height(len(selected)))
        html = build_multi_channel_html(
            self._telemetry_df, selected, cursor_x=current_telemetry_time, div_id=_DIV_ID
        )
        self._chart.render_html(html)

    def shutdown(self) -> None:
        """Uygulama kapanırken çağrılır — bkz. fsae_video_sync_page.shutdown()."""
        self._player.stop()
        self._player.setSource(QUrl())