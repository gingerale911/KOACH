"""AC (Assetto Corsa) için geçici placeholder sayfalar.

Her biri gerçek ekran yazıldığında bu dosyadan silinip kendi modülüne
taşınacak — F125/FSAE'nin placeholder desenleriyle aynı geçici amaç.
"""

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QLabel, QVBoxLayout, QWidget


def _make_placeholder(title: str) -> QWidget:
    widget = QWidget()
    layout = QVBoxLayout(widget)
    label = QLabel(title)
    label.setAlignment(Qt.AlignmentFlag.AlignCenter)
    label.setStyleSheet("font-size: 20px; color: #888;")
    layout.addWidget(label)
    return widget


def make_ac_live_placeholder() -> QWidget:
    return _make_placeholder("Live Connection (Under Construction)")


def make_ac_lap_analizi_placeholder() -> QWidget:
    return _make_placeholder("Lap Analysis (Under Construction)")


def make_ac_session_gecmisi_placeholder() -> QWidget:
    return _make_placeholder("Session History (Under Construction)")