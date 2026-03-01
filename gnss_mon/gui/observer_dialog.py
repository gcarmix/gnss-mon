"""Observer position input dialog."""

from PyQt6.QtWidgets import (
    QDialog, QFormLayout, QDoubleSpinBox, QDialogButtonBox, QLabel,
)


class ObserverDialog(QDialog):
    """Dialog for setting the observer's geodetic position."""

    def __init__(self, lat=48.8566, lon=2.3522, alt=0.0, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Set Observer Position")
        self.setMinimumWidth(300)

        layout = QFormLayout(self)

        layout.addRow(QLabel("Enter observer geodetic coordinates:"))

        self.lat_spin = QDoubleSpinBox()
        self.lat_spin.setRange(-90.0, 90.0)
        self.lat_spin.setDecimals(6)
        self.lat_spin.setSuffix(" °")
        self.lat_spin.setValue(lat)
        layout.addRow("Latitude:", self.lat_spin)

        self.lon_spin = QDoubleSpinBox()
        self.lon_spin.setRange(-180.0, 180.0)
        self.lon_spin.setDecimals(6)
        self.lon_spin.setSuffix(" °")
        self.lon_spin.setValue(lon)
        layout.addRow("Longitude:", self.lon_spin)

        self.alt_spin = QDoubleSpinBox()
        self.alt_spin.setRange(-1000.0, 100000.0)
        self.alt_spin.setDecimals(1)
        self.alt_spin.setSuffix(" m")
        self.alt_spin.setValue(alt)
        layout.addRow("Altitude:", self.alt_spin)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addRow(buttons)

    def get_position(self) -> tuple[float, float, float]:
        return self.lat_spin.value(), self.lon_spin.value(), self.alt_spin.value()
