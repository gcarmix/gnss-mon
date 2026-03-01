"""Polar skyplot tab showing satellite positions."""

import math
from datetime import datetime

import numpy as np
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure

from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QCheckBox, QLabel
from PyQt6.QtCore import Qt

from gnss_mon.constants import (
    CONSTELLATION_COLORS, CONSTELLATION_GPS, CONSTELLATION_GAL,
    CONSTELLATION_GLO, CONSTELLATION_BDS,
)

# Dark theme colors for matplotlib
_BG = "#1e1e2e"
_FG = "#cdd6f4"
_GRID = "#45475a"
_SUBTLE = "#a6adc8"

ALL_CONSTELLATIONS = [CONSTELLATION_GPS, CONSTELLATION_GAL, CONSTELLATION_GLO, CONSTELLATION_BDS]


class SkyplotTab(QWidget):
    """Polar skyplot displaying satellite azimuth/elevation."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._visible = {c: True for c in ALL_CONSTELLATIONS}
        self._sat_data = {}  # sv -> (az_deg, el_deg, constellation)

        layout = QVBoxLayout(self)

        # Matplotlib figure
        self.figure = Figure(figsize=(6, 6), facecolor=_BG)
        self.canvas = FigureCanvas(self.figure)
        layout.addWidget(self.canvas)

        # Constellation toggle checkboxes
        chk_layout = QHBoxLayout()
        self.checkboxes = {}
        for c in ALL_CONSTELLATIONS:
            cb = QCheckBox(c)
            cb.setChecked(True)
            cb.setStyleSheet(f"color: {CONSTELLATION_COLORS[c]}; font-weight: bold;")
            cb.stateChanged.connect(self._on_toggle)
            chk_layout.addWidget(cb)
            self.checkboxes[c] = cb
        chk_layout.addStretch()

        self.observer_label = QLabel("")
        self.observer_label.setStyleSheet(f"color: {_SUBTLE}; font-size: 11px;")
        chk_layout.addWidget(self.observer_label)

        layout.addLayout(chk_layout)

        self._init_plot()

    def _setup_axes(self):
        """Configure polar axes with dark theme."""
        self.figure.clear()
        self.ax = self.figure.add_subplot(111, polar=True)
        self.ax.set_facecolor(_BG)
        self.ax.set_theta_zero_location("N")
        self.ax.set_theta_direction(-1)  # clockwise
        self.ax.set_ylim(0, 90)
        self.ax.set_yticks([0, 15, 30, 45, 60, 75, 90])
        self.ax.set_yticklabels(
            ["90\u00b0", "75\u00b0", "60\u00b0", "45\u00b0", "30\u00b0", "15\u00b0", "0\u00b0"],
            color=_SUBTLE, fontsize=8,
        )
        self.ax.set_xticklabels(
            ["N", "NE", "E", "SE", "S", "SW", "W", "NW"],
            color=_FG, fontsize=10, fontweight="bold",
        )
        self.ax.grid(True, color=_GRID, alpha=0.5, linewidth=0.5)
        self.ax.tick_params(axis="x", colors=_FG)
        self.ax.spines["polar"].set_color(_GRID)

    def _init_plot(self):
        self._setup_axes()
        self.ax.set_title("Satellite Skyplot", pad=15, color=_FG, fontsize=13, fontweight="bold")
        self.canvas.draw()

    def update_observer(self, lat: float, lon: float, alt: float):
        """Update the displayed observer coordinates."""
        self.observer_label.setText(
            f"Observer: {lat:.4f}\u00b0, {lon:.4f}\u00b0, {alt:.0f}m"
        )

    def update_satellites(self, sat_data: dict):
        """Update satellite positions.

        sat_data: dict of sv -> (azimuth_deg, elevation_deg, constellation)
        """
        self._sat_data = sat_data
        self._redraw()

    def _on_toggle(self, state):
        for c, cb in self.checkboxes.items():
            self._visible[c] = cb.isChecked()
        self._redraw()

    def _redraw(self):
        self._setup_axes()

        for sv, (az, el, constellation) in self._sat_data.items():
            if not self._visible.get(constellation, False):
                continue
            if el < 0:
                continue

            theta = math.radians(az)
            r = 90.0 - el  # zenith at center
            color = CONSTELLATION_COLORS.get(constellation, "#7f849c")

            self.ax.plot(theta, r, "o", color=color, markersize=9, alpha=0.9,
                         markeredgecolor="white", markeredgewidth=0.4)
            self.ax.annotate(
                sv,
                xy=(theta, r),
                xytext=(0, 8),
                textcoords="offset points",
                fontsize=7,
                ha="center",
                va="bottom",
                color=color,
                weight="bold",
            )

        # Legend
        from matplotlib.lines import Line2D
        handles = []
        for c in ALL_CONSTELLATIONS:
            if self._visible.get(c, False):
                handles.append(Line2D([0], [0], marker="o", color="none",
                                      markerfacecolor=CONSTELLATION_COLORS[c],
                                      markeredgecolor="white", markeredgewidth=0.4,
                                      markersize=8, label=c))
        if handles:
            leg = self.ax.legend(
                handles=handles, loc="upper right", fontsize=9,
                bbox_to_anchor=(1.18, 1.12), frameon=True,
                facecolor="#313244", edgecolor="#45475a", labelcolor=_FG,
            )

        count = sum(1 for sv, (az, el, c) in self._sat_data.items()
                    if el >= 0 and self._visible.get(c, False))
        self.ax.set_title(
            f"Satellite Skyplot  ({count} visible)", pad=15,
            color=_FG, fontsize=13, fontweight="bold",
        )

        self.canvas.draw()
