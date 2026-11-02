"""FSAEVideoSyncPage — "Video & Senkron" sekmesi.

Video + telemetri arasındaki zaman ofsetini MANUEL olarak belirler.
Kullanıcı:
    1. Video dosyasını yükler
    2. Videoyu oynatıp telemetride de görünen bir olayı (ör. kalkış anı)
       bulup videoyu o kareye getirir, "Video Konumunu İşaretle"ye basar
    3. Aynı olayın telemetride hangi zamana denk geldiğini grafik
       üzerinde fareyle gezinip (Plotly'nin hover tooltip'i) okuyarak
       elle "Telemetri zamanı" kutusuna yazar
    4. "Senkronu Hesapla ve Kaydet" — ofset hesaplanıp VehicleSession'a
       kalıcı olarak yazılır

Grafiğe tıklayarak otomatik doldurma (QWebChannel ile) ileride eklenecek
bir iyileştirme — bkz. proje kararı, şimdilik elle giriş yeterli.

Telemetri Parquet dosyasının okunması BackgroundWorker ile arka plan
thread'inde yapılır — büyük dosyalarda bu işlem UI'ı bloklamasın diye
(bkz. proje kararı).

sync_offset_seconds şu ilişkiyi taşır:
    telemetri_zamanı = video_zamanı + sync_offset_seconds
Oynatım sayfası bu ofseti kullanarak videoyu telemetri imleciyle hizalar.
"""

from pathlib import Path

from PyQt6.QtCore import QUrl, Qt
from PyQt6.QtMultimedia import QAudioOutput, QMediaPlayer
from PyQt6.QtMultimediaWidgets import QVideoWidget
from PyQt6.QtWidgets import (
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QScrollArea,
    QSlider,
    QVBoxLayout,
    QWidget,
)

from f1_coach.domain.ports.fsae.vehicle_session_repository import VehicleSessionRepository
from f1_coach.infrastructure.logging.logger import get_logger
from f1_coach.infrastructure.storage.fsae.parquet_writer import read_decoded_telemetry

from f1_coach.presentation.background_worker import BackgroundWorker
from f1_coach.presentation import theme as theme_module
from f1_coach.presentation.charts.plotly_chart_widget import PlotlyChartWidget
from f1_coach.presentation.confirm_dialog import notify
from f1_coach.presentation.fsae.charts.fsae_chart_builder import build_multi_channel_html, compute_chart_height
from f1_coach.presentation.no_scroll_widgets import NoScrollDoubleSpinBox

logger = get_logger(__name__)


def _format_seconds(seconds: float) -> str:
    minutes, secs = divmod(seconds, 60)
    return f"{int(minutes)}:{secs:06.3f}"


class FSAEVideoSyncPage(QWidget):
    """Video + telemetri senkron noktası belirleme ekranı."""

    def __init__(self, vehicle_session_repo: VehicleSessionRepository, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._session_repo = vehicle_session_repo
        self._current_session = None
        self._telemetry_df = None
        self._video_sync_seconds: float | None = None
        self._worker: BackgroundWorker | None = None

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

        self._header_label = QLabel("Video & Sync")
        self._header_label.setStyleSheet("font-size: 20px; font-weight: 700;")
        layout.addWidget(self._header_label)

        self._empty_label = QLabel("Select a session from the Select Session tab first.")
        self._empty_label.setStyleSheet(f"color: {theme_module.TEXT_SECONDARY}; font-size: 13px;")
        layout.addWidget(self._empty_label)

        # --- Video dosyası seçimi ---
        video_file_row = QHBoxLayout()
        self._select_video_button = QPushButton("Select Video File")
        self._select_video_button.setObjectName("PrimaryButton")
        self._select_video_button.clicked.connect(self._on_select_video)
        video_file_row.addWidget(self._select_video_button)

        self._video_file_label = QLabel("No video selected yet")
        self._video_file_label.setStyleSheet(f"color: {theme_module.TEXT_SECONDARY}; font-size: 12px;")
        video_file_row.addWidget(self._video_file_label, stretch=1)
        self._video_file_row_frame = QFrame()
        self._video_file_row_frame.setLayout(video_file_row)
        self._video_file_row_frame.hide()
        layout.addWidget(self._video_file_row_frame)

        # --- Video oynatıcı ---
        self._video_widget = QVideoWidget()
        self._video_widget.setMinimumHeight(360)
        self._video_widget.hide()
        layout.addWidget(self._video_widget)

        self._player = QMediaPlayer(self)
        self._audio_output = QAudioOutput(self)
        self._player.setAudioOutput(self._audio_output)
        self._player.setVideoOutput(self._video_widget)

        transport_row = QHBoxLayout()
        self._play_pause_button = QPushButton("▶ Play")
        self._play_pause_button.setObjectName("PrimaryButton")
        self._play_pause_button.clicked.connect(self._on_toggle_play)
        transport_row.addWidget(self._play_pause_button)

        self._position_slider = QSlider(Qt.Orientation.Horizontal)
        self._position_slider.sliderMoved.connect(self._on_slider_moved)
        transport_row.addWidget(self._position_slider, stretch=1)

        self._position_label = QLabel("0:00.000")
        self._position_label.setStyleSheet(f"color: {theme_module.TEXT_SECONDARY}; font-size: 12px;")
        transport_row.addWidget(self._position_label)

        self._transport_row_frame = QFrame()
        self._transport_row_frame.setLayout(transport_row)
        self._transport_row_frame.hide()
        layout.addWidget(self._transport_row_frame)

        self._player.positionChanged.connect(self._on_position_changed)
        self._player.durationChanged.connect(self._on_duration_changed)

        # --- Senkron işaretleme ---
        self._sync_label = QLabel("SYNC POINT")
        self._sync_label.setStyleSheet(f"color: {theme_module.TEXT_SECONDARY}; font-size: 11px; font-weight: 600;")
        self._sync_label.hide()
        layout.addWidget(self._sync_label)

        sync_row = QHBoxLayout()
        self._mark_video_button = QPushButton("Mark Video Position")
        self._mark_video_button.setObjectName("PrimaryButton")
        self._mark_video_button.clicked.connect(self._on_mark_video_position)
        sync_row.addWidget(self._mark_video_button)

        self._video_sync_value_label = QLabel("Video time: —")
        self._video_sync_value_label.setStyleSheet("font-weight: 600; font-size: 12px;")
        sync_row.addWidget(self._video_sync_value_label)

        sync_row.addSpacing(20)
        sync_row.addWidget(QLabel("Telemetry time (s):"))
        self._telemetry_sync_input = NoScrollDoubleSpinBox()
        self._telemetry_sync_input.setRange(0, 100_000)
        self._telemetry_sync_input.setDecimals(3)
        sync_row.addWidget(self._telemetry_sync_input)

        self._calculate_button = QPushButton("Calculate and Save Sync")
        self._calculate_button.setObjectName("PrimaryButton")
        self._calculate_button.clicked.connect(self._on_calculate_sync)
        sync_row.addWidget(self._calculate_button)

        self._sync_row_frame = QFrame()
        self._sync_row_frame.setLayout(sync_row)
        self._sync_row_frame.hide()
        layout.addWidget(self._sync_row_frame)

        self._sync_status_label = QLabel("")
        self._sync_status_label.setWordWrap(True)
        layout.addWidget(self._sync_status_label)

        # --- Referans için telemetri grafiği ---
        self._chart_label = QLabel("TELEMETRY (click on chart to select sync point)")
        self._chart_label.setStyleSheet(f"color: {theme_module.TEXT_SECONDARY}; font-size: 11px; font-weight: 600;")
        self._chart_label.hide()
        layout.addWidget(self._chart_label)

        chart_row = QHBoxLayout()
        self._channel_list = QListWidget()
        self._channel_list.setMaximumWidth(220)
        self._channel_list.itemChanged.connect(self._on_channel_selection_changed)
        chart_row.addWidget(self._channel_list)

        self._chart = PlotlyChartWidget()
        self._chart.chart_clicked.connect(self._on_chart_point_clicked)
        chart_row.addWidget(self._chart, stretch=1)

        self._chart_row_frame = QFrame()
        self._chart_row_frame.setLayout(chart_row)
        self._chart_row_frame.hide()
        layout.addWidget(self._chart_row_frame)

        layout.addStretch(1)

    # ------------------------------------------------------------------
    # Yükleme
    # ------------------------------------------------------------------

    def load_session(self, session_id: int) -> None:
        session = self._session_repo.get_by_id(session_id)
        if session is None or not session.decoded_telemetry_file:
            self._set_empty_state(True)
            return

        self._current_session = session
        self._telemetry_df = None
        self._video_sync_seconds = None
        self._video_sync_value_label.setText("Video time: —")
        self._sync_status_label.setText("")

        self._header_label.setText(f"Video & Sync — {session.name} (loading telemetry...)")
        self._set_empty_state(False)
        self._set_loaded_content_enabled(False)

        self._worker = BackgroundWorker(read_decoded_telemetry, session.decoded_telemetry_file)
        self._worker.finished.connect(self._on_telemetry_loaded)
        self._worker.failed.connect(self._on_telemetry_load_failed)
        self._worker.start()

    def _on_telemetry_loaded(self, df) -> None:
        self._telemetry_df = df
        self._header_label.setText(f"Video & Sync — {self._current_session.name}")

        channels = sorted(self._telemetry_df["channel_name"].unique())
        self._channel_list.blockSignals(True)
        self._channel_list.clear()
        for channel in channels:
            item = QListWidgetItem(channel)
            item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            item.setCheckState(Qt.CheckState.Unchecked)
            self._channel_list.addItem(item)
        self._channel_list.blockSignals(False)

        if self._current_session.video_file and Path(self._current_session.video_file).exists():
            self._load_video(self._current_session.video_file)
        else:
            self._video_file_label.setText("No video selected yet")
            self._video_widget.hide()
            self._transport_row_frame.hide()

        self._set_loaded_content_enabled(True)
        self._render_chart()

    def _on_telemetry_load_failed(self, exc: Exception) -> None:
        logger.error("FSAE telemetri verisi yüklenemedi: %s", exc)
        notify(self, "Loading Error", f"Failed to read telemetry data: {exc}")
        self._set_empty_state(True)

    def _set_empty_state(self, empty: bool) -> None:
        self._empty_label.setVisible(empty)
        for widget in (
            self._video_file_row_frame, self._sync_label, self._sync_row_frame,
            self._chart_label, self._chart_row_frame,
        ):
            widget.setVisible(not empty)
        if empty:
            self._video_widget.hide()
            self._transport_row_frame.hide()

    def _set_loaded_content_enabled(self, enabled: bool) -> None:
        """Telemetri yüklenene kadar etkileşimli alanları kilitler.

        Widget'lar gizlenmiyor, yalnızca devre dışı bırakılıyor — sayfa
        "orada duruyor ama şu an kilitli" hissi versin diye (bkz. proje
        kararı: Etiketleme sayfasındaki aynı desen)."""
        for widget in (
            self._video_file_row_frame, self._sync_row_frame,
            self._chart_label, self._chart_row_frame,
        ):
            widget.setEnabled(enabled)

    # ------------------------------------------------------------------
    # Video
    # ------------------------------------------------------------------

    def _on_select_video(self) -> None:
        if self._current_session is None:
            return
        path, _ = QFileDialog.getOpenFileName(
            self, "Select Video File", "", "Video Files (*.mp4 *.mov *.avi *.mkv);;All Files (*)"
        )
        if not path:
            return

        self._current_session.video_file = path
        self._session_repo.save(self._current_session)
        self._load_video(path)

    def _load_video(self, path: str) -> None:
        self._video_file_label.setText(Path(path).name)
        self._video_widget.show()
        self._transport_row_frame.show()
        self._player.setSource(QUrl.fromLocalFile(path))

    def _on_toggle_play(self) -> None:
        if self._player.playbackState() == QMediaPlayer.PlaybackState.PlayingState:
            self._player.pause()
            self._play_pause_button.setText("▶ Play")
        else:
            self._player.play()
            self._play_pause_button.setText("⏸ Pause")

    def _on_slider_moved(self, value: int) -> None:
        self._player.setPosition(value)

    def _on_position_changed(self, position_ms: int) -> None:
        self._position_slider.blockSignals(True)
        self._position_slider.setValue(position_ms)
        self._position_slider.blockSignals(False)
        self._position_label.setText(_format_seconds(position_ms / 1000.0))

    def _on_duration_changed(self, duration_ms: int) -> None:
        self._position_slider.setRange(0, duration_ms)

    # ------------------------------------------------------------------
    # Senkron
    # ------------------------------------------------------------------

    def _on_mark_video_position(self) -> None:
        position_seconds = self._player.position() / 1000.0
        self._video_sync_seconds = position_seconds
        self._video_sync_value_label.setText(f"Video time: {_format_seconds(position_seconds)}")

    def _on_calculate_sync(self) -> None:
        if self._current_session is None:
            return
        if self._video_sync_seconds is None:
            notify(
                self, "Video position not marked",
                "Seek the video to the desired frame and click 'Mark Video Position' first.",
            )
            return

        telemetry_seconds = self._telemetry_sync_input.value()
        offset = telemetry_seconds - self._video_sync_seconds

        self._current_session.sync_offset_seconds = offset
        self._session_repo.save(self._current_session)

        self._sync_status_label.setStyleSheet(f"color: {theme_module.GREEN}; font-size: 12px;")
        self._sync_status_label.setText(f"✓ Sync saved. Offset: {offset:+.3f} s")

        logger.info(
            "FSAE video senkron kaydedildi: session_id=%d offset=%.3f",
            self._current_session.id, offset,
        )

    # ------------------------------------------------------------------
    # Grafik
    # ------------------------------------------------------------------

    def _on_channel_selection_changed(self, _item: QListWidgetItem) -> None:
        self._render_chart()

    def _selected_channels(self) -> list[str]:
        selected = []
        for row in range(self._channel_list.count()):
            item = self._channel_list.item(row)
            if item.checkState() == Qt.CheckState.Checked:
                selected.append(item.text())
        return selected

    def _render_chart(self) -> None:
        if self._telemetry_df is None:
            return
        selected = self._selected_channels()
        if not selected:
            self._chart.setFixedHeight(200)
            self._chart.render_html("<html><body></body></html>")
            return
        self._chart.setFixedHeight(compute_chart_height(len(selected)))
        html = build_multi_channel_html(self._telemetry_df, selected, enable_click_to_select=True)
        self._chart.render_html(html)

    def shutdown(self) -> None:
        """Uygulama kapanırken çağrılır — oynatıcıyı durdurup kaynağı serbest
        bırakır. FFmpeg tabanlı multimedia backend'i, pencere kapatılırken
        oynatıcı hâlâ bir kaynağa bağlıysa arkada bir iş parçacığı/pencere
        bırakabiliyor, bu da sürecin konsoldan sonlanmasını engelliyor."""
        self._player.stop()
        self._player.setSource(QUrl())

    def hideEvent(self, event) -> None:  # type: ignore[no-untyped-def]
        """Sayfa gizlenince (başka bir sekmeye geçilince) videoyu duraklatır —
        aksi halde QMediaPlayer arka planda oynamaya devam ediyordu, çünkü
        widget'ın görünürlüğü oynatmayı otomatik durdurmuyor."""
        if self._player.playbackState() == QMediaPlayer.PlaybackState.PlayingState:
            self._player.pause()
            self._play_pause_button.setText("▶ Play")
        super().hideEvent(event)

    def _on_chart_point_clicked(self, x_value: float) -> None:
        """Grafikte bir noktaya tıklanınca, o noktanın x (zaman) değerini
        doğrudan telemetri zamanı kutusuna yazar — elle okuma/yazmaya gerek
        kalmaz."""
        self._telemetry_sync_input.setValue(x_value)
        self._sync_status_label.setStyleSheet(f"color: {theme_module.TEXT_SECONDARY}; font-size: 12px;")
        self._sync_status_label.setText(f"Selected from chart: telemetry time = {x_value:.3f} s")