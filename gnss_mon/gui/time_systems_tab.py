"""Time systems display tab."""

from datetime import datetime

from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel, QGroupBox, QGridLayout
from PyQt6.QtCore import Qt

from gnss_mon.core.time_systems import TimeConverter


class TimeSystemsTab(QWidget):
    """Display current time across all GNSS time systems."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._converter = TimeConverter()

        layout = QVBoxLayout(self)

        group = QGroupBox("GNSS Time Systems")
        grid = QGridLayout(group)

        self._labels = {}
        systems = [
            ("UTC", "Coordinated Universal Time"),
            ("GPST", "GPS Time (UTC + 18s leap seconds)"),
            ("GST", "Galileo System Time (= GPS Time)"),
            ("BDT", "BeiDou Time (GPST - 14s)"),
            ("GLONASST", "GLONASS Time (UTC + 3h Moscow)"),
        ]

        mono_style = "font-family: 'JetBrains Mono', 'Fira Code', monospace; font-size: 18px; padding: 6px; color: #89b4fa;"
        desc_style = "color: #6c7086; font-size: 11px;"

        for row, (key, desc) in enumerate(systems):
            name_label = QLabel(f"<b>{key}</b>")
            name_label.setMinimumWidth(100)
            grid.addWidget(name_label, row * 2, 0)

            val_label = QLabel("--")
            val_label.setStyleSheet(mono_style)
            val_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
            grid.addWidget(val_label, row * 2, 1)

            desc_label = QLabel(desc)
            desc_label.setStyleSheet(desc_style)
            grid.addWidget(desc_label, row * 2 + 1, 1)

            self._labels[key] = val_label

        grid.setColumnStretch(1, 1)
        layout.addWidget(group)
        layout.addStretch()

    def update_time(self, utc: datetime):
        """Update all time system displays for the given UTC time."""
        times = self._converter.format_all(utc)
        for key, val in times.items():
            if key in self._labels:
                self._labels[key].setText(val)
