"""FSAE Landing sayfası — f125_landing_page.py'nin FSAE karşılığı.

Sol sidebar'daki FSAE logosuna her tıklamada gösterilir. Bu ekran
açıldığında ikincil panel henüz açılmaz — yalnızca "Başla" butonuna
basıldığında MainWindow.on_fsae_start_pressed() tetiklenir ve doğrudan
İçe Aktar sekmesine yönlendirir (F1 25'teki gibi arka planda başlayan bir
dinleyici yok; FSAE akışı tamamen kullanıcı tetiklemeli, offline bir
dosya işleme sürecidir).
"""
from pathlib import Path

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QPixmap
from PyQt6.QtWidgets import (
    QFrame,
    QGridLayout,
    QLabel,
    QVBoxLayout,
    QWidget,
    QScrollArea
)

from f1_coach.presentation import theme as theme_module
from f1_coach.presentation.theme_manager import ThemeManager

CURRENT_DIR = Path(__file__).resolve().parent.parent
ICONS_DIR = CURRENT_DIR / "assets" / "icons"

_FEATURE_CARDS = [
    ("can_logs.svg", "GREEN", "Ham CAN Log İçe Aktarma",
     "Datalogger'dan USB ile alınan ham CAN log dosyasını (.blf/.asc/.trc/.csv) doğrudan içe aktar."),
    ("labeling.svg", "ORANGE", "Manuel Kanal Etiketleme",
     "Her CAN ID içindeki sinyalleri kendi elinle etiketle — ölçek, offset ve birim tanımla, DBC dosyasına ihtiyaç yok."),
    ("fsae_graph.svg", "BLUE", "Dinamik Kanal Grafikleri",
     "Session'a göre değişen kanal setinden istediğin sinyalleri seçip zaman bazlı grafiklerde incele."),
    ("edit.svg", "PURPLE", "Düzeltilebilir Etiketleme",
     "Yanlış etiketlediğin bir kanalı, dosyayı yeniden yüklemeden düzeltip anında yeniden çözümle."),
]

class _AppLauncherCard(QFrame):
    """Tıklanabilir, büyük uygulama başlatma kartı."""

    clicked = pyqtSignal()

    def __init__(self, icon: str, title: str, description: str, accent_key: str) -> None:
        super().__init__()
        self.setObjectName("AppCard") 
        
        self._accent_key = accent_key
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setMinimumHeight(160)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(10)
        layout.setAlignment(Qt.AlignmentFlag.AlignHCenter)

        self._icon_box = QLabel(icon)
        self._icon_box.setFixedSize(52, 52)
        self._icon_box.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self._icon_box, alignment=Qt.AlignmentFlag.AlignHCenter)

        title_label = QLabel(title)
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title_label.setStyleSheet("font-weight: 700; font-size: 16px; background: transparent;")
        layout.addWidget(title_label)

        desc_label = QLabel(description)
        desc_label.setWordWrap(True)
        desc_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        desc_label.setStyleSheet(f"color: {theme_module.TEXT_SECONDARY}; font-size: 12px; background: transparent;")
        layout.addWidget(desc_label)

        self.apply_theme()

    def apply_theme(self) -> None:
        color_map = {
            "GREEN": theme_module.GREEN, "BLUE": theme_module.BLUE,
            "ORANGE": theme_module.ORANGE, "PURPLE": theme_module.PURPLE,
        }
        accent = color_map.get(self._accent_key, theme_module.ACCENT_RED)
        self.setStyleSheet(
            f"#AppCard {{ background-color: {theme_module.SURFACE}; border: 1px solid {theme_module.BORDER};"
            "  border-radius: 16px; }"
            f"#AppCard:hover {{ border: 1px solid {accent}; }}"
        )
        self._icon_box.setStyleSheet(
            f"background-color: {theme_module.rgba(accent, 0.14)}; border-radius: 14px; font-size: 22px;"
        )

    def mousePressEvent(self, event) -> None:  # type: ignore[no-untyped-def]
        self.clicked.emit()
        super().mousePressEvent(event)


def _make_feature_card(icon: str, color: str, title: str, description: str) -> QFrame:
    card = QFrame()
    card.setObjectName("FeatureCard")
    card.setStyleSheet(
        f"#FeatureCard {{ background-color: {theme_module.SURFACE}; border: 1px solid {theme_module.BORDER};"
        "  border-radius: 16px; padding: 18px; }"
    )
    layout = QVBoxLayout(card)

    icon_box = QLabel(icon)
    icon_box.setFixedSize(42, 42)
    icon_box.setAlignment(Qt.AlignmentFlag.AlignCenter)
    icon_box.setStyleSheet(
        f"background-color: {theme_module.rgba(color, 0.14)}; border-radius: 12px; font-size: 19px;"
    )
    layout.addWidget(icon_box)

    title_label = QLabel(title)
    title_label.setWordWrap(True)
    title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
    title_label.setStyleSheet("font-weight: 600; font-size: 14px; background: transparent;")
    layout.addWidget(title_label)

    desc_label = QLabel(description)
    desc_label.setWordWrap(True)
    desc_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
    desc_label.setStyleSheet(f"color: {theme_module.TEXT_SECONDARY}; font-size: 12px; background: transparent;")
    layout.addWidget(desc_label)

    return card


class FSAELandingPage(QWidget):
    """FSAE karşılama ekranı — iki alt uygulamaya giriş noktası.

    Signals:
        labeling_pressed: "CAN Veri Etiketleme" kartına basıldı.
        video_pressed:    "Video + Pist Takip" kartına basıldı.
    """

    labeling_pressed = pyqtSignal()
    video_pressed = pyqtSignal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)

        outer_layout = QVBoxLayout(self)
        outer_layout.setContentsMargins(0, 0, 0, 0)

        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setFrameShape(QFrame.Shape.NoFrame)
        outer_layout.addWidget(scroll_area)

        content = QWidget()
        scroll_area.setWidget(content)

        layout = QVBoxLayout(content)
        layout.setContentsMargins(48, 56, 48, 48)
        layout.setSpacing(20)

        title = QLabel("FSAE Telemetri Analizi")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setStyleSheet("font-size: 32px; font-weight: 800;")
        layout.addWidget(title)

        subtitle = QLabel("Devam etmek istediğin uygulamayı seç.")
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        subtitle.setStyleSheet(f"color: {theme_module.TEXT_SECONDARY}; font-size: 14px;")
        layout.addWidget(subtitle)

        layout.addSpacing(8)

        # --- İki uygulama kartı ---
        self._labeling_card = _AppLauncherCard(
            "🏷", "CAN Veri Etiketleme",
            "Ham CAN log dosyasını içe aktar, kanalları elle etiketle ve kaydet.",
            "ORANGE",
        )
        self._labeling_card.clicked.connect(self.labeling_pressed.emit)
        layout.addWidget(self._labeling_card)

        self._video_card = _AppLauncherCard(
            "🎥", "Video + Pist Takip",
            "Etiketlenmiş bir session seç, video yükle, senkronize incele.",
            "BLUE",
        )
        self._video_card.clicked.connect(self.video_pressed.emit)
        layout.addWidget(self._video_card)

        layout.addSpacing(12)

        # --- Bilgilendirici özellik kartları ---
        self._grid_label = QLabel("MODÜL ÖZELLİKLERİ")
        self._grid_label.setStyleSheet(f"color: {theme_module.TEXT_SECONDARY}; font-size: 11px; font-weight: 600;")
        layout.addWidget(self._grid_label)

        self._grid = QGridLayout()
        layout.addLayout(self._grid)

        layout.addStretch(1)

        ThemeManager.instance().theme_changed.connect(self._apply_theme)
        self._apply_theme()

    def _apply_theme(self) -> None:
        self._labeling_card.apply_theme()
        self._video_card.apply_theme()

        while self._grid.count():
            item = self._grid.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        color_map = {
            "GREEN": theme_module.GREEN, "BLUE": theme_module.BLUE,
            "ORANGE": theme_module.ORANGE, "PURPLE": theme_module.PURPLE,
        }
        for index, (icon, color_key, card_title, desc) in enumerate(_FEATURE_CARDS):
            row, col = divmod(index, 2)
            self._grid.addWidget(
                _make_feature_card(icon, color_map[color_key], card_title, desc), row, col)