"""MainWindow — navigasyon iskeletini birleştiren ana pencere.

Yapı:
    [Sidebar (Katman 1, sabit)] [SecondaryPanel (Katman 2, kayar)] [İçerik alanı]

İçerik alanı bir QStackedWidget'tır; her sayfa bu dosyada bir index'e
sahiptir. Sayfalar arası geçiş yalnızca burada, tek bir yerde yönetilir.

Başlangıç yönlendirmesi (UI dokümanı §2.6):
    Profil varsa  → doğrudan Ana Sayfa
    Profil yoksa  → Profil sayfası (onboarding)
"""
from pathlib import Path

from PyQt6.QtWidgets import QFrame, QHBoxLayout, QLabel, QMainWindow, QStackedWidget, QVBoxLayout, QWidget, QApplication
from PyQt6.QtGui import QIcon

from f1_coach.domain.ports.profile_repository import ProfileRepository

from f1_coach.domain.ports.f125.session_repository import SessionRepository
from f1_coach.domain.ports.f125.car_setup_repository import CarSetupRepository

from f1_coach.domain.ports.fsae.vehicle_session_repository import VehicleSessionRepository
from f1_coach.domain.ports.fsae.channel_mapping_repository import ChannelMappingRepository

from f1_coach.application.f125.coaching_engine import CoachingEngine

from f1_coach.infrastructure.storage.repositories.fsae.sqlite_mapping_profile_repository import (
    SQLiteMappingProfileRepository,
)
from f1_coach.infrastructure.logging.logger import get_logger
from f1_coach.infrastructure.ai.adapter_factory import create_ai_adapter
from f1_coach.infrastructure.security.credential_store import get_api_key
from f1_coach.infrastructure.f125_udp.telemetry_receiver import TelemetryReceiver
from f1_coach.infrastructure.storage.repositories.f125.sqlite_lap_repository import (
    SQLiteLapRepository,
)

from f1_coach.presentation.fsae.fsae_playback_page import FSAEPlaybackPage
from f1_coach.presentation.fsae.fsae_video_secondary_panel import FSAEVideoSecondaryPanel
from f1_coach.presentation.fsae.fsae_video_session_picker_page import FSAEVideoSessionPickerPage
from f1_coach.presentation.fsae.fsae_video_sync_page import FSAEVideoSyncPage

from f1_coach.presentation.fsae.fsae_labeling_page import FSAELabelingPage
from f1_coach.presentation.fsae.fsae_import_page import FSAEImportPage
from f1_coach.presentation.fsae.fsae_landing_page import FSAELandingPage
from f1_coach.presentation.fsae.fsae_secondary_panel import FSAESecondaryPanel
from f1_coach.infrastructure.ac_udp.ac_telemetry_client import AcTelemetryClient
from f1_coach.presentation.fsae.ac_secondary_panel import AcSecondaryPanel
from f1_coach.presentation.fsae.ac_placeholder_pages import (
    make_ac_live_placeholder,
    make_ac_lap_analizi_placeholder,
    make_ac_session_gecmisi_placeholder,
)

from f1_coach.presentation.f125.f1_25_landing_page import F1_25LandingPage
from f1_coach.presentation.f125.session_gecmisi_page import SessionGecmisiPage
from f1_coach.presentation.f125.canli_session_page import CanliSessionPage
from f1_coach.presentation.f125.lap_analizi_page import LapAnaliziPage
from f1_coach.presentation.f125.secondary_panel import SecondaryPanel
from f1_coach.presentation.f125.dashboard import LiveDashboardPage

from f1_coach.presentation.sidebar import Sidebar
from f1_coach.presentation.ayarlar_page import AyarlarPage
from f1_coach.presentation.ana_sayfa_page import AnaSayfaPage
from f1_coach.presentation.profil_page import ProfilPage

logger = get_logger(__name__)
_ASSETS_DIR = Path(__file__).parent / "assets" 
_LOGO_DIR = _ASSETS_DIR / "logos"

class MainWindow(QMainWindow):
    """KOACH ana penceresi — tüm navigasyonun birleştiği yer."""

    def __init__(
    self,
        profile_repo: ProfileRepository,
        session_repo: SessionRepository,
        lap_repo: SQLiteLapRepository,
        car_setup_repo: CarSetupRepository,
        telemetry_receiver: TelemetryReceiver,

        vehicle_session_repo: VehicleSessionRepository,
        channel_mapping_repo: ChannelMappingRepository,
        mapping_profile_repo: SQLiteMappingProfileRepository,
        ac_telemetry_client: AcTelemetryClient,

    ) -> None:
        super().__init__()
        self._profile_repo = profile_repo
        self._session_repo = session_repo
        self._lap_repo = lap_repo
        self._car_setup_repo = car_setup_repo
        self._telemetry_receiver = telemetry_receiver
        self._vehicle_session_repo = vehicle_session_repo
        self._channel_mapping_repo = channel_mapping_repo
        self._mapping_profile_repo = mapping_profile_repo
        self._ac_telemetry_client = ac_telemetry_client
        self._active_fsae_session_id: int | None = None

        self.setWindowTitle("KOACH")
        icon_path = Path(__file__).parent / "assets" / "logos" / "koach_siyah.ico"
        if icon_path.exists():
            self.setWindowIcon(QIcon(str(icon_path)))
        self.resize(1280, 900)
        
        icon_path = _LOGO_DIR /"koach_siyah.png"
        if icon_path.exists():
            self.setWindowIcon(QIcon(str(icon_path)))

        central = QWidget()
        self.setCentralWidget(central)
        outer_layout = QVBoxLayout(central)
        outer_layout.setContentsMargins(0, 0, 0, 0)
        outer_layout.setSpacing(0)

        outer_layout.addWidget(self._build_top_bar())

        body = QWidget()
        root_layout = QHBoxLayout(body)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)
        outer_layout.addWidget(body)

        # --- Katman 1: Sidebar ---
        self._sidebar = Sidebar()
        self._sidebar.profile_clicked.connect(self._show_profil)
        self._sidebar.home_clicked.connect(self._show_ana_sayfa)
        self._sidebar.f1_25_clicked.connect(self._show_f1_25_landing)
        self._sidebar.fsae_clicked.connect(self._show_fsae_landing)
        self._sidebar.settings_clicked.connect(self._show_ayarlar)
        root_layout.addWidget(self._sidebar)

        # --- Katman 2: Kayar panel (varsayılan gizli) ---
        self._secondary_panel = SecondaryPanel()
        self._secondary_panel.live_session_clicked.connect(self._show_canli_session)
        self._secondary_panel.live_dashboard_clicked.connect(self._show_live_dashboard)
        self._secondary_panel.lap_analysis_clicked.connect(self._show_lap_analizi)
        self._secondary_panel.session_history_clicked.connect(self._show_session_gecmisi)

        self._fsae_secondary_panel = FSAESecondaryPanel()
        self._fsae_secondary_panel.import_clicked.connect(self._show_fsae_import)
        self._fsae_secondary_panel.labeling_clicked.connect(self._show_fsae_labeling)

        # --- Video Alanı ---
        self._fsae_video_secondary_panel = FSAEVideoSecondaryPanel()
        self._fsae_video_secondary_panel.session_select_clicked.connect(self._show_fsae_video_session_picker)
        self._fsae_video_secondary_panel.video_sync_clicked.connect(self._show_fsae_video_sync)
        self._fsae_video_secondary_panel.playback_clicked.connect(self._show_fsae_playback)

        self._ac_secondary_panel = AcSecondaryPanel()
        self._ac_secondary_panel.live_clicked.connect(self._show_ac_live)
        self._ac_secondary_panel.lap_analysis_clicked.connect(self._show_ac_lap_analizi)
        self._ac_secondary_panel.session_history_clicked.connect(self._show_ac_session_gecmisi)

        # --- İçerik alanı ---
        self._content_stack = QStackedWidget()
        right_column = QWidget()
        right_layout = QVBoxLayout(right_column)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(0)
        right_layout.addWidget(self._ac_secondary_panel)
        right_layout.addWidget(self._secondary_panel)
        right_layout.addWidget(self._fsae_secondary_panel)
        right_layout.addWidget(self._fsae_video_secondary_panel)
        right_layout.addWidget(self._content_stack)
        root_layout.addWidget(right_column)
        
        self._build_pages()
        self._route_on_startup()

    # ------------------------------------------------------------------
    # Sayfa kurulumu
    # ------------------------------------------------------------------

    def _build_top_bar(self) -> QFrame:
        """App.tsx'teki üst bar: logo + KOACH wordmark + F1 25 rozeti."""
        bar = QFrame()
        bar.setObjectName("TopBar")
        bar.setFixedHeight(48)

        layout = QHBoxLayout(bar)
        layout.setContentsMargins(20, 0, 20, 0)
        layout.setSpacing(10)

        title = QLabel("KOACH")
        title.setStyleSheet("font-size: 13px; font-weight: 700")
        layout.addWidget(title)

        return bar
    
    def _build_pages(self) -> None:
        """Her sayfayı stack'e ekler ve index'ini saklar."""
        self._ana_sayfa_page = AnaSayfaPage(self._profile_repo, self._session_repo, self._vehicle_session_repo)
        self._ana_sayfa_page.settings_requested.connect(self._show_ayarlar)
        self._ana_sayfa_page.session_selected.connect(self._open_session_from_history)
        self._ana_sayfa_page.fsae_session_selected.connect(self._open_fsae_session_from_history)
        self._page_ana_sayfa = self._content_stack.addWidget(self._ana_sayfa_page)

        self._f1_25_landing_page = F1_25LandingPage()
        self._f1_25_landing_page.start_pressed.connect(self.on_f1_25_start_pressed)
        self._page_f1_25_landing = self._content_stack.addWidget(self._f1_25_landing_page)

        self._profil_page = ProfilPage(self._profile_repo, self._session_repo)
        self._profil_page.onboarding_completed.connect(self._show_ana_sayfa)
        self._profil_page.profile_saved.connect(self._refresh_profile_badge)
        self._page_profil = self._content_stack.addWidget(self._profil_page)

        self._ayarlar_page = AyarlarPage(self._profile_repo)
        self._ayarlar_page.settings_saved.connect(self._on_settings_saved)
        self._page_ayarlar = self._content_stack.addWidget(self._ayarlar_page)

        self._canli_session_page = CanliSessionPage(self._telemetry_receiver)
        self._canli_session_page.session_ended.connect(self._on_live_session_ended)
        self._canli_session_page.lap_selected.connect(self._open_live_lap_in_analysis)
        self._page_canli_session = self._content_stack.addWidget(self._canli_session_page)

        self._live_dashboard_page = LiveDashboardPage(self._telemetry_receiver, self._profile_repo)
        self._page_live_dashboard = self._content_stack.addWidget(self._live_dashboard_page)
        
        self._lap_analizi_page = LapAnaliziPage(
            self._session_repo, self._lap_repo, coaching_engine=None, car_setup_repo=self._car_setup_repo
        )        
        self._page_lap_analizi = self._content_stack.addWidget(self._lap_analizi_page)       
        
        self._session_gecmisi_page = SessionGecmisiPage(self._session_repo)
        self._session_gecmisi_page.session_selected.connect(self._open_session_from_history)
        self._page_session_gecmisi = self._content_stack.addWidget(self._session_gecmisi_page)

        self._fsae_landing_page = FSAELandingPage()
        self._fsae_landing_page.labeling_pressed.connect(self.on_fsae_labeling_app_pressed)
        self._fsae_landing_page.video_pressed.connect(self.on_fsae_video_app_pressed)
        self._page_fsae_landing = self._content_stack.addWidget(self._fsae_landing_page)

        self._fsae_landing_page.ac_pressed.connect(self.on_ac_app_pressed)
        
        self._fsae_import_page = FSAEImportPage(self._vehicle_session_repo)
        self._fsae_import_page.session_imported.connect(self._on_fsae_session_imported)
        self._page_fsae_import = self._content_stack.addWidget(self._fsae_import_page)

        self._fsae_labeling_page = FSAELabelingPage(self._vehicle_session_repo, self._channel_mapping_repo, self._mapping_profile_repo)
        self._fsae_labeling_page.decoding_completed.connect(self._on_fsae_decoding_completed)
        self._page_fsae_labeling = self._content_stack.addWidget(self._fsae_labeling_page)

        self._fsae_video_session_picker_page = FSAEVideoSessionPickerPage(self._vehicle_session_repo)
        self._fsae_video_session_picker_page.session_selected.connect(self._on_fsae_video_session_selected)
        self._page_fsae_video_session_picker = self._content_stack.addWidget(self._fsae_video_session_picker_page)

        self._ac_live_page = make_ac_live_placeholder()
        self._page_ac_live = self._content_stack.addWidget(self._ac_live_page)

        self._ac_lap_analizi_page = make_ac_lap_analizi_placeholder()
        self._page_ac_lap_analizi = self._content_stack.addWidget(self._ac_lap_analizi_page)

        self._ac_session_gecmisi_page = make_ac_session_gecmisi_placeholder()
        self._page_ac_session_gecmisi = self._content_stack.addWidget(self._ac_session_gecmisi_page)

        self._fsae_video_sync_page = FSAEVideoSyncPage(self._vehicle_session_repo)
        self._page_fsae_video_sync = self._content_stack.addWidget(self._fsae_video_sync_page)

        self._fsae_playback_page = FSAEPlaybackPage(self._vehicle_session_repo)
        self._fsae_playback_page.session_finished.connect(self._on_fsae_video_session_finished)
        self._fsae_playback_page.sync_needed.connect(self._on_fsae_playback_sync_needed)
        self._page_fsae_playback = self._content_stack.addWidget(self._fsae_playback_page)

        self._refresh_coaching_engine()
        self._refresh_profile_badge()

    def _route_on_startup(self) -> None:
        """UI dokümanı §2.6: profil var mı yok mu kontrolü."""
        profile = self._profile_repo.get_current()
        if profile is None:
            logger.info("No profile found — directing to Profile onboarding page.")
            self._show_profil()
        else:
            logger.info("Welcome %s — directing to Home page.", profile.name)
            self._show_ana_sayfa()

    # ------------------------------------------------------------------
    # Sayfa geçişleri
    # ------------------------------------------------------------------
    def _close_all_secondary_panels(self) -> None:
        self._secondary_panel.close_panel()
        self._fsae_secondary_panel.close_panel()
        self._fsae_video_secondary_panel.close_panel()
        self._ac_secondary_panel.close_panel()

    def _show_ana_sayfa(self) -> None:
        self._close_all_secondary_panels()
        self._ana_sayfa_page.refresh()
        self._content_stack.setCurrentIndex(self._page_ana_sayfa)

    def _show_f1_25_landing(self) -> None:
        """F1 25 ikonuna tıklandığında: aktif kayıt varsa canlı ekrana döner, yoksa landing gösterir."""
        if self._telemetry_receiver.is_running:
            self._close_all_secondary_panels()
            self._secondary_panel.open_panel()
            self._show_canli_session()
            return

        self._close_all_secondary_panels()
        self._content_stack.setCurrentIndex(self._page_f1_25_landing)

    def _show_profil(self) -> None:
        self._close_all_secondary_panels()
        self._profil_page.refresh()
        self._content_stack.setCurrentIndex(self._page_profil)

    def _show_ayarlar(self) -> None:
        self._close_all_secondary_panels()
        self._ayarlar_page.refresh()
        self._content_stack.setCurrentIndex(self._page_ayarlar)

    def _show_canli_session(self) -> None:
        self._secondary_panel.set_active_tab("live")
        self._content_stack.setCurrentIndex(self._page_canli_session)

    def _show_live_dashboard(self) -> None:
        self._secondary_panel.set_active_tab("dashboard")
        self._content_stack.setCurrentIndex(self._page_live_dashboard)

    def _show_lap_analizi(self) -> None:
        self._secondary_panel.set_active_tab("analysis")
        self._lap_analizi_page.refresh()
        self._content_stack.setCurrentIndex(self._page_lap_analizi)

    def _show_session_gecmisi(self) -> None:
        self._secondary_panel.set_active_tab("history")
        self._session_gecmisi_page.refresh()
        self._content_stack.setCurrentIndex(self._page_session_gecmisi)

    def _show_fsae_landing(self) -> None:
        """FSAE logosuna her tıklamada gösterilir; ikincil panel henüz açılmaz."""
        self._close_all_secondary_panels()
        self._content_stack.setCurrentIndex(self._page_fsae_landing)

    def _show_fsae_import(self) -> None:
        self._content_stack.setCurrentIndex(self._page_fsae_import)

    def _show_fsae_labeling(self) -> None:
        self._content_stack.setCurrentIndex(self._page_fsae_labeling)

    def _show_fsae_video_session_picker(self) -> None:
        self._fsae_video_session_picker_page.refresh()
        self._content_stack.setCurrentIndex(self._page_fsae_video_session_picker)

    def _show_fsae_video_sync(self) -> None:
        self._content_stack.setCurrentIndex(self._page_fsae_video_sync)

    def _show_fsae_playback(self) -> None:
        if self._active_fsae_session_id is not None:
            self._fsae_playback_page.load_session(self._active_fsae_session_id)
        self._content_stack.setCurrentIndex(self._page_fsae_playback)

    def _show_ac_live(self) -> None:
        self._content_stack.setCurrentIndex(self._page_ac_live)

    def _show_ac_lap_analizi(self) -> None:
        self._content_stack.setCurrentIndex(self._page_ac_lap_analizi)

    def _show_ac_session_gecmisi(self) -> None:
        self._content_stack.setCurrentIndex(self._page_ac_session_gecmisi)

    def _on_fsae_session_imported(self, session_id: int) -> None:
        self._active_fsae_session_id = session_id
        self._fsae_labeling_page.load_session(session_id)
        self._show_fsae_labeling()

    def _on_fsae_decoding_completed(self, session_id: int) -> None:
        """Etiketleme tamamlandığında (onay diyaloğu kapatıldıktan sonra)
        çağrılır — FSAE Landing'e döner; Video + Pist Takip'e oradan geçilir."""
        self._active_fsae_session_id = session_id
        self._show_fsae_landing()

    def _on_fsae_video_session_selected(self, session_id: int) -> None:
        """Session Seç sayfasında bir session'a tıklanınca çağrılır."""
        self._active_fsae_session_id = session_id
        self._fsae_video_sync_page.load_session(session_id)
        self._show_fsae_video_sync()

    def _on_fsae_playback_sync_needed(self, session_id: int) -> None:
        """Oynatım sayfasında 'Video & Senkron'a Git' butonuna basıldığında çağrılır."""
        self._active_fsae_session_id = session_id
        self._fsae_video_sync_page.load_session(session_id)
        self._show_fsae_video_sync()

    def _on_fsae_video_session_finished(self) -> None:
        """Oynatım sayfasındaki 'Session'ı Bitir' butonuna basıldığında çağrılır."""
        self._active_fsae_session_id = None
        self._show_ana_sayfa()

    def on_fsae_labeling_app_pressed(self) -> None:
        """FSAE Landing'deki 'CAN Veri Etiketleme' kartına basıldığında çağrılır."""
        self._fsae_secondary_panel.open_panel()
        self._show_fsae_import()

    def on_fsae_video_app_pressed(self) -> None:
        """FSAE Landing'deki 'Video + Pist Takip' kartına basıldığında çağrılır."""
        self._fsae_video_secondary_panel.open_panel()
        self._show_fsae_video_session_picker()

    def on_ac_app_pressed(self) -> None:
        """FSAE Landing'deki 'Assetto Corsa Simülasyonu' kartına basıldığında çağrılır."""
        self._ac_secondary_panel.open_panel()
        self._show_ac_live()

    def on_f1_25_start_pressed(self) -> None:
        """F1 25 Landing sayfasındaki "Başla" butonu buraya bağlanır."""
        self._telemetry_receiver.start()
        self._secondary_panel.open_panel()
        self._canli_session_page.start_monitoring()
        self._sidebar.set_navigation_locked(False)
        self._secondary_panel.set_navigation_locked(False)
        self._show_live_dashboard()

    def _on_live_session_ended(self) -> None:
        """CanliSessionPage.session_ended sinyali geldiğinde navigasyonun kilidini açar."""
        self._sidebar.set_navigation_locked(False)
        self._secondary_panel.set_navigation_locked(False)
        self._show_lap_analizi()

    def _open_live_lap_in_analysis(self, lap_number: int) -> None:
        """Canlı session ekranında bir tura tıklandığında doğrudan o turun analizini açar."""
        sessions = self._session_repo.get_all()
        if not sessions:
            return
        current_session = sessions[0]
        self._lap_analizi_page.open_lap(current_session.id, lap_number)
        self._secondary_panel.open_panel()
        self._secondary_panel.set_active_tab("analysis")
        self._content_stack.setCurrentIndex(self._page_lap_analizi)

    def _open_session_from_history(self, session_id: int) -> None:
        """Session Geçmişi'nden bir karta tıklanınca o session'ı Lap Analizi'nde açar."""
        self._lap_analizi_page.load_session(session_id)
        self._secondary_panel.open_panel()
        self._secondary_panel.set_active_tab("analysis")
        self._content_stack.setCurrentIndex(self._page_lap_analizi)

    def _open_fsae_session_from_history(self, session_id: int) -> None:
        """Ana Sayfa'daki 'Son FSAE Session'ları' listesinden bir karta
        tıklanınca çağrılır. Etiketlenmemişse CAN Veri Etiketleme uygulamasında
        Etiketleme sekmesine, etiketlenmişse Video + Pist Takip uygulamasında
        Session Seç sekmesine yönlendirir."""
        session = self._vehicle_session_repo.get_by_id(session_id)
        if session is None:
            return

        self._active_fsae_session_id = session_id
        self._close_all_secondary_panels()

        if session.is_labeled:
            self._fsae_video_secondary_panel.open_panel()
            self._show_fsae_video_session_picker()
        else:
            self._fsae_secondary_panel.open_panel()
            self._fsae_labeling_page.load_session(session_id)
            self._show_fsae_labeling()

    def _refresh_coaching_engine(self) -> None:
        """Profildeki AI ayarlarına göre CoachingEngine kurar; eksikse None bırakır."""
        profile = self._profile_repo.get_current()
        if profile is None or not profile.is_ai_configured:
            self._lap_analizi_page.set_coaching_engine(None)
            return

        api_key = get_api_key("gemini")
        if not api_key:
            self._lap_analizi_page.set_coaching_engine(None)
            return

        try:
            adapter = create_ai_adapter(api_key)
            engine = CoachingEngine(self._lap_repo, self._session_repo, adapter, self._car_setup_repo)
            self._lap_analizi_page.set_coaching_engine(engine)
            logger.info("CoachingEngine initialized: provider=gemini")
        except Exception as exc:
            logger.error("CoachingEngine failed to initialize: %s", exc)
            self._lap_analizi_page.set_coaching_engine(None)

    def _on_settings_saved(self) -> None:
        self._refresh_coaching_engine()
        self._ana_sayfa_page.refresh()

    def _refresh_profile_badge(self) -> None:
        """Sidebar'daki profil rozetini güncel isim/fotoğrafla senkronlar."""
        profile = self._profile_repo.get_current()
        if profile is not None:
            self._sidebar.update_profile_badge(profile.name, profile.photo_path)

    def closeEvent(self, event) -> None:  # type: ignore[no-untyped-def]
        """Pencere kapatılırken video oynatıcıları ve UDP alıcısını temiz
        şekilde durdurur — aksi halde FFmpeg tabanlı multimedia backend'i
        arkada bir kaynak bırakabiliyor, süreç konsoldan sonlanmıyor."""
        self._fsae_video_sync_page.shutdown()
        self._fsae_playback_page.shutdown()
        self._telemetry_receiver.stop()
        self._ac_telemetry_client.stop()
        super().closeEvent(event)
        QApplication.instance().quit()