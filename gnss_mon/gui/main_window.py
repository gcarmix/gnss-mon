"""Main application window."""

from datetime import datetime, timezone, timedelta
from pathlib import Path

from PyQt6.QtWidgets import (
    QMainWindow, QTabWidget, QVBoxLayout, QWidget, QFileDialog,
    QMessageBox, QStatusBar, QApplication, QLabel,
)
from PyQt6.QtCore import Qt, QSettings, QTimer
from PyQt6.QtGui import QAction

import numpy as np

from gnss_mon.constants import RINEX_PREFIX
from gnss_mon.core.ephemeris import EphemerisStore
from gnss_mon.core.rinex_loader import RinexLoader
from gnss_mon.core.propagator import SatellitePropagator
from gnss_mon.core.coordinates import geodetic_to_ecef, ecef_to_azel

from gnss_mon.gui.time_control import TimeControlWidget
from gnss_mon.gui.skyplot_tab import SkyplotTab
from gnss_mon.gui.ephemeris_tab import EphemerisTab
from gnss_mon.gui.time_systems_tab import TimeSystemsTab
from gnss_mon.gui.observer_dialog import ObserverDialog
from gnss_mon.core.rinex_writer import RinexWriter


class MainWindow(QMainWindow):
    """Main GNSS Monitor window."""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("GNSS Monitor")
        self.setMinimumSize(900, 700)

        # State
        self._store = EphemerisStore()
        self._propagator = SatellitePropagator()
        self._observer_lat = 48.8566
        self._observer_lon = 2.3522
        self._observer_alt = 0.0

        self._settings = QSettings("GNSS-Mon", "GNSS Monitor")
        self._load_settings()

        self._observer_ecef = geodetic_to_ecef(self._observer_lat, self._observer_lon, self._observer_alt)

        self._build_menu()
        self._build_ui()
        self.skyplot_tab.update_observer(self._observer_lat, self._observer_lon, self._observer_alt)

        # Auto-load last RINEX file (deferred so the window is visible first)
        last_file = self._settings.value("last_rinex_file", "")
        if last_file and Path(last_file).is_file():
            self._pending_load = last_file
        else:
            self._pending_load = None
            self.statusBar().showMessage("Ready. Open a RINEX file.")

    def _load_settings(self):
        self._observer_lat = float(self._settings.value("observer_lat", 48.8566))
        self._observer_lon = float(self._settings.value("observer_lon", 2.3522))
        self._observer_alt = float(self._settings.value("observer_alt", 0.0))

    def _save_settings(self):
        self._settings.setValue("observer_lat", self._observer_lat)
        self._settings.setValue("observer_lon", self._observer_lon)
        self._settings.setValue("observer_alt", self._observer_alt)

    def showEvent(self, event):
        super().showEvent(event)
        if self._pending_load:
            filepath = self._pending_load
            self._pending_load = None
            QTimer.singleShot(0, lambda: self._load_rinex(filepath))

    def closeEvent(self, event):
        self._save_settings()
        super().closeEvent(event)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if hasattr(self, "_loading_label"):
            self._loading_label.setGeometry(self.centralWidget().geometry())

    def _build_menu(self):
        menu = self.menuBar()

        file_menu = menu.addMenu("&File")

        open_act = QAction("&Open RINEX File...", self)
        open_act.setShortcut("Ctrl+O")
        open_act.triggered.connect(self._open_file)
        file_menu.addAction(open_act)

        save_synth_act = QAction("&Save Synthetic RINEX...", self)
        save_synth_act.setShortcut("Ctrl+Shift+S")
        save_synth_act.triggered.connect(self._save_synthetic_rinex)
        file_menu.addAction(save_synth_act)

        file_menu.addSeparator()

        observer_act = QAction("Set &Observer Position...", self)
        observer_act.setShortcut("Ctrl+L")
        observer_act.triggered.connect(self._set_observer)
        file_menu.addAction(observer_act)

        file_menu.addSeparator()

        exit_act = QAction("E&xit", self)
        exit_act.setShortcut("Ctrl+Q")
        exit_act.triggered.connect(self.close)
        file_menu.addAction(exit_act)

    def _build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)

        # Tabs
        self.tab_widget = QTabWidget()
        self.skyplot_tab = SkyplotTab()
        self.ephemeris_tab = EphemerisTab()
        self.time_systems_tab = TimeSystemsTab()

        self.tab_widget.addTab(self.skyplot_tab, "Skyplot")
        self.tab_widget.addTab(self.ephemeris_tab, "Ephemeris")
        self.tab_widget.addTab(self.time_systems_tab, "Time Systems")
        layout.addWidget(self.tab_widget)

        # Time control
        self.time_control = TimeControlWidget()
        self.time_control.time_changed.connect(self._on_time_changed)
        layout.addWidget(self.time_control)

        # Loading overlay
        self._loading_label = QLabel("Loading RINEX...", self)
        self._loading_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._loading_label.setStyleSheet(
            "background-color: rgba(24, 24, 37, 220);"
            "color: #89b4fa;"
            "font-size: 20px;"
            "font-weight: bold;"
            "border-radius: 12px;"
        )
        self._loading_label.hide()

    def _open_file(self):
        filepath, _ = QFileDialog.getOpenFileName(
            self, "Open RINEX Navigation File", "",
            "RINEX Files (*.rnx *.nav *.*n *.*p);;All Files (*)"
        )
        if filepath:
            self._load_rinex(filepath)

    def _save_synthetic_rinex(self):
        if len(self._store) == 0:
            QMessageBox.warning(self, "No Data", "Load a RINEX file first.")
            return
        sim_time = self.time_control.current_time()
        filepath, _ = QFileDialog.getSaveFileName(
            self, "Save Synthetic RINEX", "",
            "RINEX Files (*.rnx);;All Files (*)"
        )
        if not filepath:
            return
        try:
            RinexWriter().write(self._store, sim_time, filepath)
            self.statusBar().showMessage(f"Saved synthetic RINEX to {Path(filepath).name}")
        except Exception as e:
            QMessageBox.critical(self, "Save Error", f"Failed to save RINEX:\n{e}")
            self.statusBar().showMessage("Save failed.")

    def _load_rinex(self, filepath: str):
        self._loading_label.setText(f"Loading {Path(filepath).name}...")
        self._loading_label.raise_()
        self._loading_label.show()
        self.statusBar().showMessage(f"Loading {filepath}...")
        QApplication.processEvents()

        try:
            loader = RinexLoader()
            self._store = loader.load(filepath)
        except Exception as e:
            self._loading_label.hide()
            QMessageBox.critical(self, "Load Error", f"Failed to load RINEX file:\n{e}")
            self.statusBar().showMessage("Load failed.")
            return

        self._loading_label.hide()
        self._settings.setValue("last_rinex_file", str(filepath))

        n_sats = len(self._store.get_satellites())
        n_eph = len(self._store)
        self.statusBar().showMessage(
            f"Loaded {n_eph} ephemerides for {n_sats} satellites from {Path(filepath).name}"
        )

        start, end = self._store.time_span
        if start and end:
            self.time_control.set_time_range(start, end)
            # Start at current system time if within (or near) the data range,
            # otherwise use the end of the data range (most recent data).
            now = datetime.now(timezone.utc).replace(microsecond=0)
            if now < start:
                initial = start
            elif now > end:
                initial = end
            else:
                initial = now
            self.time_control.set_current_time(initial)
            self._recompute(initial)

    def _set_observer(self):
        dlg = ObserverDialog(self._observer_lat, self._observer_lon, self._observer_alt, self)
        if dlg.exec():
            self._observer_lat, self._observer_lon, self._observer_alt = dlg.get_position()
            self._observer_ecef = geodetic_to_ecef(
                self._observer_lat, self._observer_lon, self._observer_alt
            )
            self._save_settings()
            self.skyplot_tab.update_observer(self._observer_lat, self._observer_lon, self._observer_alt)
            self.statusBar().showMessage(
                f"Observer: {self._observer_lat:.4f}°, {self._observer_lon:.4f}°, "
                f"{self._observer_alt:.0f}m"
            )
            self._recompute(self.time_control.current_time())

    def _on_time_changed(self, t: datetime):
        self._recompute(t)

    def _recompute(self, utc: datetime):
        """Recompute all satellite positions and update all tabs."""
        sat_data = {}  # sv -> (az, el, constellation)

        for sv in self._store.get_satellites():
            eph = self._store.get_closest(sv, utc)
            if eph is None:
                continue

            pos = self._propagator.propagate(eph, utc)
            if pos is None:
                continue

            az, el = ecef_to_azel(
                self._observer_ecef, pos,
                self._observer_lat, self._observer_lon,
            )
            constellation = eph.constellation
            sat_data[sv] = (az, el, constellation)

        self.skyplot_tab.update_satellites(sat_data)
        self.ephemeris_tab.update_ephemeris(self._store, utc, sat_data)
        self.time_systems_tab.update_time(utc)
