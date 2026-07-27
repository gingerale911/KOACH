"""FSAE Landing sayfası — iki ayrı alt uygulamaya giriş noktası.

FSAE modülü, birbirinden bağımsız iki akışa ayrılmış durumda:
    1. CAN Veri Etiketleme — ham log içe aktarma + manuel kanal etiketleme
    2. Video + Pist Takip — etiketlenmiş bir session'ı seçip video ile
       senkronize inceleme

Sol sidebar'daki FSAE logosuna her tıklamada gösterilir.
"""
from pathlib import Path

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QIcon
from PyQt6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from f1_coach.presentation import theme as theme_module
from f1_coach.presentation.theme_manager import ThemeManager

CURRENT_DIR = Path(__file__).resolve().parent.parent
ICONS_DIR = CURRENT_DIR / "assets" / "icons"

_FEATURE_CARDS = [
    ("can_logs.svg", "GREEN", "Ham CAN Log İçe Aktarma",
     "Datalogger'dan USB ile alınan ham CAN log dosyasını (.blf/.asc/.trc/.csv/.mf4) doğrudan içe aktarır. "
     "Dosya python-can kütüphanesiyle okunur, içindeki her CAN ID ve örnek byte içeriği otomatik çıkarılıp "
     "listelenir — hiçbir veri kaybı olmadan ham haliyle diske kaydedilir, çözümleme sonradan yapılır."),
    ("labeling.svg", "ORANGE", "Manuel Kanal Etiketleme",
     "Her CAN ID içindeki sinyalleri kendi elinle etiketlersin — byte aralığı, bit uzunluğu, endianness, ölçek "
     "ve offset gibi bir DBC dosyasının normalde tanımladığı her şeyi arayüzden girersin. Bu, hangi takımın CAN "
     "ağını nasıl tasarladığını bilmeden herhangi bir aracın verisini KOACH'a uyarlayabilmeni sağlar."),
    ("fsae_graph.svg", "BLUE", "Dinamik Kanal Grafikleri",
     "Etiketlenen kanallar session'dan session'a değişebileceği için grafik ekranı sabit bir panel yerine, "
     "kanal listesinden seçtiğin herhangi bir kombinasyonu her biri kendi ölçeğinde ayrı bir satırda çizer — "
     "tek bir düzende onlarca farklı sensör tipini (sıcaklık, basınç, hız, açı) yan yana karşılaştırabilirsin."),
    ("edit.svg", "PURPLE", "Düzeltilebilir Etiketleme",
     "Ham CAN frame'leri, çözümlenmiş veriden ayrı olarak diskte tutulur. Bir kanalı yanlış etiketlediğini fark "
     "ettiğinde, orijinal log dosyasını yeniden yüklemene gerek kalmadan sadece etiketi düzeltip "
     "'Kaydet ve Çözümle'ye basman yeterli — düzeltme anında tüm session için yeniden hesaplanır."),
    ("video_sync.svg", "BLUE", "Video + Pist Takip (Senkronize İnceleme)",
     "Etiketlenmiş bir session'ı araç üstü kamera görüntüsüyle birleştirir. Videoda ve telemetride aynı ana "
     "(ör. kalkış anı) karşılık gelen noktaları elle işaretleyerek bir zaman ofseti hesaplarsın; Oynatım "
     "ekranında video oynarken telemetri grafiğindeki imleç bu ofsete göre otomatik ilerler."),
]


class _AppLauncherCard(QFrame):
    """Tıklanabilir, geniş uygulama başlatma kartı.

    Sol tarafta başlık + açıklama (sola hizalı), sağ tarafta "Başla" butonu.
    Hover'da yalnızca dış çerçeve accent renginde parlar — iç elemanların
    (yazı, buton) rengi hover'dan bağımsız kalır.
    """

    clicked = pyqtSignal()

    def __init__(self, title: str, description: str, accent_key: str) -> None:
        super().__init__()
        self._accent_key = accent_key
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setObjectName("AppLauncherCard")
        self.setMinimumHeight(96)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(24, 18, 24, 18)
        layout.setSpacing(16)

        text_column = QVBoxLayout()
        text_column.setSpacing(4)

        title_label = QLabel(title)
        title_label.setStyleSheet("font-weight: 700; font-size: 16px; background: transparent;")
        text_column.addWidget(title_label)

        desc_label = QLabel(description)
        desc_label.setWordWrap(True)
        desc_label.setStyleSheet(f"color: {theme_module.TEXT_SECONDARY}; font-size: 12px; background: transparent;")
        text_column.addWidget(desc_label)

        layout.addLayout(text_column, stretch=1)

        self._start_button = QPushButton("Başla")
        self._start_button.setObjectName("PrimaryButton")
        self._start_button.clicked.connect(self.clicked.emit)
        layout.addWidget(self._start_button, alignment=Qt.AlignmentFlag.AlignVCenter)

        self.apply_theme()

    def apply_theme(self) -> None:
        color_map = {
            "GREEN": theme_module.GREEN, "BLUE": theme_module.BLUE,
            "ORANGE": theme_module.ORANGE, "PURPLE": theme_module.PURPLE,
        }
        accent = color_map.get(self._accent_key, theme_module.ACCENT_RED)
        self.setStyleSheet(
            f"QFrame#AppLauncherCard {{ background-color: {theme_module.SURFACE}; border: 1px solid {theme_module.BORDER};"
            "  border-radius: 16px; }"
            f"QFrame#AppLauncherCard:hover {{ border: 1px solid {accent}; }}"
        )

    def mousePressEvent(self, event) -> None:  # type: ignore[no-untyped-def]
        self.clicked.emit()
        super().mousePressEvent(event)


def _make_feature_card(icon_filename: str, color: str, title: str, description: str) -> QFrame:
    """Yatay bir kart: solda ikon, sağda başlık + uzun açıklama."""
    card = QFrame()
    card.setStyleSheet(
        f"QFrame#AppLauncherCard {{ background-color: {theme_module.SURFACE}; border: 1px solid {theme_module.BORDER};"
        "  border-radius: 16px; padding: 18px; }"
    )
    layout = QHBoxLayout(card)
    layout.setSpacing(16)

    icon_box = QLabel()
    icon_box.setFixedSize(42, 42)
    icon_box.setAlignment(Qt.AlignmentFlag.AlignCenter)
    icon_box.setStyleSheet(
        f"background-color: {theme_module.rgba(color, 0.14)}; border-radius: 12px;"
    )
    icon = QIcon(str(ICONS_DIR / icon_filename))
    if not icon.isNull():
        icon_box.setPixmap(icon.pixmap(22, 22))
    layout.addWidget(icon_box)

    text_column = QVBoxLayout()
    text_column.setSpacing(4)

    title_label = QLabel(title)
    title_label.setWordWrap(True)
    title_label.setStyleSheet("font-weight: 600; font-size: 14px; background: transparent;")
    text_column.addWidget(title_label)

    desc_label = QLabel(description)
    desc_label.setWordWrap(True)
    desc_label.setStyleSheet(f"color: {theme_module.TEXT_SECONDARY}; font-size: 12px; background: transparent;")
    text_column.addWidget(desc_label)

    layout.addLayout(text_column, stretch=1)

    return card


class FSAELandingPage(QWidget):
    """FSAE karşılama ekranı — iki alt uygulamaya giriş noktası.

    Signals:
        labeling_pressed: "CAN Veri Etiketleme" kartındaki "Başla"ya basıldı.
        video_pressed:    "Video + Pist Takip" kartındaki "Başla"ya basıldı.
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
            "CAN Veri Etiketleme",
            "Ham CAN log dosyasını içe aktar, kanalları elle etiketle ve kaydet.",
            "ORANGE",
        )
        self._labeling_card.clicked.connect(self.labeling_pressed.emit)
        layout.addWidget(self._labeling_card)

        self._video_card = _AppLauncherCard(
            "Video + Pist Takip",
            "Etiketlenmiş bir session seç, video yükle, senkronize incele.",
            "BLUE",
        )
        self._video_card.clicked.connect(self.video_pressed.emit)
        layout.addWidget(self._video_card)

        layout.addSpacing(12)

        # --- Bilgilendirici özellik kartları (dikey liste) ---
        self._grid_label = QLabel("MODÜL ÖZELLİKLERİ")
        self._grid_label.setStyleSheet(f"color: {theme_module.TEXT_SECONDARY}; font-size: 11px; font-weight: 600;")
        layout.addWidget(self._grid_label)

        self._features_column = QVBoxLayout()
        self._features_column.setSpacing(12)
        layout.addLayout(self._features_column)

        layout.addStretch(1)

        ThemeManager.instance().theme_changed.connect(self._apply_theme)
        self._apply_theme()

    def _apply_theme(self) -> None:
        self._labeling_card.apply_theme()
        self._video_card.apply_theme()

        while self._features_column.count():
            item = self._features_column.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        color_map = {
            "GREEN": theme_module.GREEN, "BLUE": theme_module.BLUE,
            "ORANGE": theme_module.ORANGE, "PURPLE": theme_module.PURPLE,
        }
        for icon_filename, color_key, card_title, desc in _FEATURE_CARDS:
            self._features_column.addWidget(
                _make_feature_card(icon_filename, color_map[color_key], card_title, desc)
            )