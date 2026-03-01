"""Ephemeris tables tab with per-constellation sub-tabs."""

from datetime import datetime

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QTabWidget, QTableWidget, QTableWidgetItem, QHeaderView,
)
from PyQt6.QtCore import Qt

from gnss_mon.constants import (
    CONSTELLATION_GPS, CONSTELLATION_GAL, CONSTELLATION_GLO, CONSTELLATION_BDS,
)
from gnss_mon.core.ephemeris import KeplerianEphemeris, GlonassEphemeris, EphemerisStore


ALL_CONSTELLATIONS = [CONSTELLATION_GPS, CONSTELLATION_GAL, CONSTELLATION_GLO, CONSTELLATION_BDS]

KEPLER_COLUMNS = [
    "SV", "Epoch", "Az (°)", "El (°)", "sqrtA", "Eccentricity", "M0", "omega", "Omega0",
    "Io", "DeltaN", "IDOT", "OmegaDot", "Cus", "Cuc", "Crs", "Crc",
    "Cis", "Cic", "Toe", "Week",
]

GLONASS_COLUMNS = [
    "SV", "Epoch", "Az (°)", "El (°)", "X (m)", "Y (m)", "Z (m)",
    "dX (m/s)", "dY (m/s)", "dZ (m/s)",
    "dX2 (m/s²)", "dY2 (m/s²)", "dZ2 (m/s²)",
    "ClkBias", "ClkDrift",
]


class EphemerisTab(QWidget):
    """Tabbed ephemeris tables for each constellation."""

    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)

        self.tabs = QTabWidget()
        self.tables = {}

        for c in ALL_CONSTELLATIONS:
            table = QTableWidget()
            table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
            table.setAlternatingRowColors(True)
            table.setSortingEnabled(True)
            cols = GLONASS_COLUMNS if c == CONSTELLATION_GLO else KEPLER_COLUMNS
            table.setColumnCount(len(cols))
            table.setHorizontalHeaderLabels(cols)
            table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
            self.tables[c] = table
            self.tabs.addTab(table, c)

        layout.addWidget(self.tabs)

    def update_ephemeris(self, store: EphemerisStore, t: datetime, sat_azel: dict):
        """Populate tables with the closest ephemeris for each SV at time t.

        sat_azel: dict of sv -> (azimuth_deg, elevation_deg, constellation)
        """
        for constellation in ALL_CONSTELLATIONS:
            table = self.tables[constellation]
            table.setSortingEnabled(False)
            table.setRowCount(0)

            svs = store.get_constellation_satellites(constellation)
            row = 0
            for sv in svs:
                eph = store.get_latest(sv)
                if eph is None:
                    continue

                az_str = ""
                el_str = ""
                if sv in sat_azel:
                    az, el, _ = sat_azel[sv]
                    az_str = f"{az:.1f}"
                    el_str = f"{el:.1f}"

                if constellation == CONSTELLATION_GLO and isinstance(eph, GlonassEphemeris):
                    self._fill_glonass_row(table, row, eph, az_str, el_str)
                elif isinstance(eph, KeplerianEphemeris):
                    self._fill_kepler_row(table, row, eph, az_str, el_str)
                else:
                    continue
                row += 1

            table.setSortingEnabled(True)

    def _fill_kepler_row(self, table: QTableWidget, row: int,
                         eph: KeplerianEphemeris, az_str: str, el_str: str):
        table.setRowCount(row + 1)
        vals = [
            eph.sv,
            eph.epoch.strftime("%H:%M:%S"),
            az_str,
            el_str,
            f"{eph.sqrtA:.6f}",
            f"{eph.Eccentricity:.10e}",
            f"{eph.M0:.10e}",
            f"{eph.omega:.10e}",
            f"{eph.Omega0:.10e}",
            f"{eph.Io:.10e}",
            f"{eph.DeltaN:.10e}",
            f"{eph.IDOT:.10e}",
            f"{eph.OmegaDot:.10e}",
            f"{eph.Cus:.10e}",
            f"{eph.Cuc:.10e}",
            f"{eph.Crs:.6f}",
            f"{eph.Crc:.6f}",
            f"{eph.Cis:.10e}",
            f"{eph.Cic:.10e}",
            f"{eph.Toe:.0f}",
            str(eph.week),
        ]
        for col, val in enumerate(vals):
            item = QTableWidgetItem(val)
            item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            table.setItem(row, col, item)

    def _fill_glonass_row(self, table: QTableWidget, row: int,
                          eph: GlonassEphemeris, az_str: str, el_str: str):
        table.setRowCount(row + 1)
        vals = [
            eph.sv,
            eph.epoch.strftime("%H:%M:%S"),
            az_str,
            el_str,
            f"{eph.X:.3f}",
            f"{eph.Y:.3f}",
            f"{eph.Z:.3f}",
            f"{eph.dX:.6f}",
            f"{eph.dY:.6f}",
            f"{eph.dZ:.6f}",
            f"{eph.dX2:.9f}",
            f"{eph.dY2:.9f}",
            f"{eph.dZ2:.9f}",
            f"{eph.SVclockBias:.12e}",
            f"{eph.SVclockDrift:.12e}",
        ]
        for col, val in enumerate(vals):
            item = QTableWidgetItem(val)
            item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            table.setItem(row, col, item)
