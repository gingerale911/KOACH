"""Plotly figürlerinden HTML üreten yardımcı fonksiyon — FSAE modülü.

Her seçili kanal KENDİ satırında, kendi otomatik ölçekli y-ekseninde
çizilir (paylaşılan x-ekseni ile).

build_multi_channel_html'e opsiyonel bir cursor_x verilirse, her satırın
üzerinden geçen dikey bir "şu an buradayız" çizgisi eklenir — Oynatım
sayfasında video ilerledikçe bu çizginin konumu build_cursor_update_js
ile (tüm grafiği yeniden çizmeden) güncellenir.
"""

import json

import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

_COLOR_PALETTE = [
    "#9B30FF", "#00BFFF", "#2ecc71", "#e74c3c", "#f1c40f",
    "#FF8C00", "#1ABC9C", "#E91E63", "#3498DB", "#8BC34A",
]

_ROW_HEIGHT = 220
_CHART_MARGIN = 80
_DEFAULT_DIV_ID = "fsae_chart"


def compute_chart_height(num_channels: int) -> int:
    if num_channels <= 0:
        return _ROW_HEIGHT
    return num_channels * _ROW_HEIGHT + _CHART_MARGIN


def _strip_internal_scroll(html: str) -> str:
    style_tag = "<style>html,body{margin:0;padding:0;overflow:hidden;}</style>"
    return html.replace("<head>", f"<head>{style_tag}", 1)


def build_multi_channel_html(
    telemetry_df: pd.DataFrame,
    selected_channels: list[str],
    cursor_x: float | None = None,
    div_id: str = _DEFAULT_DIV_ID,
    enable_click_to_select: bool = False,
) -> str:
    """Seçilen her kanalı kendi satırında, kendi ölçeğinde çizen grafik üretir.

    Args:
        telemetry_df:      read_decoded_telemetry() çıktısı.
        selected_channels: Grafiğe dahil edilecek kanal isimleri.
        cursor_x:          Verilirse, bu x konumunda tüm satırları dikey
                           kesen bir "şu an buradayız" çizgisi eklenir
                           (Oynatım sayfası için).
        div_id:            Üretilen HTML'deki grafik div'inin sabit id'si —
                           JS ile sonradan güncelleme yapabilmek için
                           build_cursor_update_js ile eşleşmeli.

    Returns:
        QWebEngineView.setHtml() ile kullanılabilir tam HTML sayfası.
    """
    num_rows = len(selected_channels)
    if num_rows == 0:
        return "<html><body></body></html>"

    spacing = 0.08 if num_rows <= 1 else min(0.08, (1 / (num_rows - 1)) * 0.9)

    fig = make_subplots(
        rows=num_rows, cols=1, shared_xaxes=True,
        subplot_titles=selected_channels, vertical_spacing=spacing,
    )

    for index, channel in enumerate(selected_channels, start=1):
        channel_df = telemetry_df[telemetry_df["channel_name"] == channel].sort_values("timestamp")
        if channel_df.empty:
            continue
        color = _COLOR_PALETTE[(index - 1) % len(_COLOR_PALETTE)]
        fig.add_trace(
            go.Scatter(x=channel_df["timestamp"], y=channel_df["value"], name=channel, line=dict(color=color)),
            row=index, col=1,
        )

    shapes = []
    if cursor_x is not None:
        for index in range(1, num_rows + 1):
            axis_suffix = "" if index == 1 else str(index)
            shapes.append(dict(
                type="line",
                xref=f"x{axis_suffix}",
                yref=f"y{axis_suffix} domain",
                x0=cursor_x, x1=cursor_x, y0=0, y1=1,
                line=dict(color="#FFFFFF", width=2, dash="dot"),
            ))

    fig.update_xaxes(title_text="Zaman (s)", row=num_rows, col=1)
    fig.update_layout(
        height=compute_chart_height(num_rows), showlegend=False,
        margin=dict(l=50, r=20, t=30, b=40), template="plotly_dark",
        shapes=shapes,
    )
    html = _strip_internal_scroll(fig.to_html(include_plotlyjs="cdn", full_html=True, div_id=div_id))
    if enable_click_to_select:
        html = _inject_click_handler(html, div_id)
    return html


def build_cursor_update_js(num_channels: int, x_value: float, div_id: str = _DEFAULT_DIV_ID) -> str:
    """Verilen div_id'deki grafiğin imleç çizgisini yeni x konumuna taşıyan JS üretir.

    Video oynarken periyodik olarak PlotlyChartWidget.run_javascript() ile
    çağrılır — tüm grafiği yeniden çizmek yerine yalnızca çizgi(ler)in
    konumunu güncellediği için hızlıdır.
    """
    updates: dict[str, float] = {}
    for i in range(num_channels):
        updates[f"shapes[{i}].x0"] = x_value
        updates[f"shapes[{i}].x1"] = x_value
    return f"Plotly.relayout(document.getElementById('{div_id}'), {json.dumps(updates)});"

def _inject_click_handler(html: str, div_id: str) -> str:
    """Grafiğe QWebChannel üzerinden tıklama dinleyicisi ekler.

    plotly_click olayını yakalayıp tıklanan noktanın x değerini
    PlotlyChartWidget'taki _ChartBridge.on_chart_clicked'e iletir. Sayfa
    her yeniden yüklendiğinde (render_html çağrıldığında) bu script de
    yeniden çalışır — QWebChannel bağlantısını her seferinde tazeler.
    """
    script = f"""
<script src="qrc:///qtwebchannel/qwebchannel.js"></script>
<script>
window.addEventListener('load', function() {{
    if (typeof QWebChannel === 'undefined' || typeof qt === 'undefined') return;
    new QWebChannel(qt.webChannelTransport, function(channel) {{
        window.pyBridge = channel.objects.bridge;
        var chartDiv = document.getElementById('{div_id}');
        if (chartDiv) {{
            chartDiv.on('plotly_click', function(data) {{
                if (data.points && data.points.length > 0) {{
                    window.pyBridge.on_chart_clicked(data.points[0].x);
                }}
            }});
        }}
    }});
}});
</script>
"""
    return html.replace("</body>", f"{script}</body>", 1)