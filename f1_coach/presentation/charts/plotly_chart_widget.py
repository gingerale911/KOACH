"""QWebEngineView tabanlı, Plotly HTML'i render eden basit widget."""

from PyQt6.QtCore import pyqtSignal
from PyQt6.QtWebEngineWidgets import QWebEngineView
from PyQt6.QtWidgets import QVBoxLayout, QWidget


class PlotlyChartWidget(QWidget):
    """Plotly figürünü göstermek için tek metodu olan sarmalayıcı: render_html().

    Signals:
        chart_ready: Yüklenen HTML sayfası (Plotly.js dahil) tamamen
                    yüklendiğinde yayınlanır.

    run_javascript(), sayfa henüz yüklenmeyi bitirmeden (chart_ready
    yayınlanmadan) çağrılırsa sessizce yok sayılır — "Plotly is not
    defined" / "DOM element ... null" hatalarının kaynağı tam olarak
    bu zamanlama sorunuydu; her çağıranın kendi başına takip etmesi
    yerine bu koruma burada, merkezi olarak yapılıyor.
    """

    chart_ready = pyqtSignal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        self._view = QWebEngineView()
        self._is_ready = False
        self._view.loadFinished.connect(self._on_load_finished)
        layout.addWidget(self._view)

    def render_html(self, html: str) -> None:
        """Yeni bir HTML sayfası yükler — bu, tam bir sayfa yenilemesi
        (navigation) tetikler, bu yüzden hazır olma durumu sıfırlanır."""
        self._is_ready = False
        self._view.setHtml(html)

    def run_javascript(self, script: str) -> None:
        """Yüklü HTML sayfasına JS kodu çalıştırır.

        Sayfa henüz yüklenmeyi bitirmediyse (chart_ready yayınlanmadıysa)
        çağrı sessizce atlanır — çağıranın bunu ayrıca kontrol etmesine
        gerek yok.
        """
        if not self._is_ready:
            return
        self._view.page().runJavaScript(script)

    @property
    def is_ready(self) -> bool:
        return self._is_ready

    def _on_load_finished(self, success: bool) -> None:
        self._is_ready = success
        if success:
            self.chart_ready.emit()