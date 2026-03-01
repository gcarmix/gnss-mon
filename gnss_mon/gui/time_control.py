"""Time control widget - real-time clock with step controls."""

from datetime import datetime, timedelta, timezone

from PyQt6.QtCore import pyqtSignal, Qt, QDateTime
from PyQt6.QtWidgets import (
    QWidget, QHBoxLayout, QVBoxLayout, QPushButton,
    QDateTimeEdit, QSpinBox, QLabel,
)


class TimeControlWidget(QWidget):
    """Real-time clock with step and play controls."""

    time_changed = pyqtSignal(datetime)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._current = datetime.now(timezone.utc).replace(microsecond=0)
        self._step_minutes = 5
        self._playing = False
        self._timer_id = None
        self._data_start = None
        self._data_end = None

        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)

        # Controls row
        ctrl = QHBoxLayout()

        btn_style = "QPushButton { font-size: 15px; padding: 4px 0px; }"
        btn_h = 30

        self.btn_rw = QPushButton("\u25c0\u25c0")
        self.btn_rw.setFixedSize(40, btn_h)
        self.btn_rw.setStyleSheet(btn_style)
        self.btn_rw.setToolTip("Step back (x6)")
        self.btn_rw.clicked.connect(self._step_back_big)
        ctrl.addWidget(self.btn_rw)

        self.btn_back = QPushButton("\u25c0")
        self.btn_back.setFixedSize(40, btn_h)
        self.btn_back.setStyleSheet(btn_style)
        self.btn_back.setToolTip("Step back")
        self.btn_back.clicked.connect(self._step_back)
        ctrl.addWidget(self.btn_back)

        self.btn_play = QPushButton("\u25b6")
        self.btn_play.setFixedSize(40, btn_h)
        self.btn_play.setStyleSheet(btn_style)
        self.btn_play.setToolTip("Play / Stop")
        self.btn_play.clicked.connect(self._toggle_play)
        ctrl.addWidget(self.btn_play)

        self.btn_fwd = QPushButton("\u25b6")
        self.btn_fwd.setFixedSize(40, btn_h)
        self.btn_fwd.setStyleSheet(btn_style)
        self.btn_fwd.setToolTip("Step forward")
        self.btn_fwd.clicked.connect(self._step_fwd)
        ctrl.addWidget(self.btn_fwd)

        self.btn_ff = QPushButton("\u25b6\u25b6")
        self.btn_ff.setFixedSize(40, btn_h)
        self.btn_ff.setStyleSheet(btn_style)
        self.btn_ff.setToolTip("Step forward (x6)")
        self.btn_ff.clicked.connect(self._step_fwd_big)
        ctrl.addWidget(self.btn_ff)

        ctrl.addSpacing(10)

        ctrl.addWidget(QLabel("Step (min):"))
        self.step_spin = QSpinBox()
        self.step_spin.setRange(1, 60)
        self.step_spin.setValue(5)
        self.step_spin.setFixedHeight(btn_h)
        self.step_spin.valueChanged.connect(self._on_step_change)
        ctrl.addWidget(self.step_spin)

        ctrl.addSpacing(10)

        self.dt_edit = QDateTimeEdit()
        self.dt_edit.setDisplayFormat("yyyy-MM-dd HH:mm:ss")
        self.dt_edit.setCalendarPopup(True)
        self.dt_edit.setFixedHeight(btn_h)
        self.dt_edit.dateTimeChanged.connect(self._on_datetime_edit)
        ctrl.addWidget(self.dt_edit)

        self.btn_now = QPushButton("Now")
        self.btn_now.setFixedSize(50, btn_h)
        self.btn_now.clicked.connect(self._go_now)
        ctrl.addWidget(self.btn_now)

        ctrl.addSpacing(10)

        self.time_label = QLabel("")
        self.time_label.setStyleSheet("font-weight: bold; font-size: 15px; color: #89b4fa;")
        ctrl.addWidget(self.time_label)

        ctrl.addStretch()

        self.data_range_label = QLabel("")
        self.data_range_label.setStyleSheet("color: #a6adc8; font-size: 11px;")
        ctrl.addWidget(self.data_range_label)

        layout.addLayout(ctrl)
        self._update_display()

    def set_time_range(self, start: datetime, end: datetime):
        """Store the RINEX data time range for display only."""
        self._data_start = start
        self._data_end = end
        self.data_range_label.setText(
            f"RINEX: {start.strftime('%Y-%m-%d %H:%M')} — {end.strftime('%Y-%m-%d %H:%M')} UTC"
        )

    def set_current_time(self, t: datetime):
        """Set simulation time."""
        self._current = t.replace(microsecond=0)
        self._sync_dt_edit()
        self._update_display()

    def current_time(self) -> datetime:
        return self._current

    def _on_datetime_edit(self, qdt):
        dt = datetime(qdt.date().year(), qdt.date().month(), qdt.date().day(),
                      qdt.time().hour(), qdt.time().minute(), qdt.time().second(),
                      tzinfo=timezone.utc)
        self._current = dt
        self._update_display()
        self.time_changed.emit(self._current)

    def _sync_dt_edit(self):
        self.dt_edit.blockSignals(True)
        t = self._current
        self.dt_edit.setDateTime(QDateTime(t.year, t.month, t.day,
                                           t.hour, t.minute, t.second))
        self.dt_edit.blockSignals(False)

    def _update_display(self):
        self.time_label.setText(
            f"UTC  {self._current.strftime('%Y-%m-%d  %H:%M:%S')}"
        )

    def _step(self, minutes: int):
        self._current += timedelta(minutes=minutes)
        self._sync_dt_edit()
        self._update_display()
        self.time_changed.emit(self._current)

    def _step_back(self):
        self._step(-self._step_minutes)

    def _step_fwd(self):
        self._step(self._step_minutes)

    def _step_back_big(self):
        self._step(-self._step_minutes * 6)

    def _step_fwd_big(self):
        self._step(self._step_minutes * 6)

    def _go_now(self):
        self._current = datetime.now(timezone.utc).replace(microsecond=0)
        self._sync_dt_edit()
        self._update_display()
        self.time_changed.emit(self._current)

    def _on_step_change(self, val):
        self._step_minutes = val

    def _toggle_play(self):
        if self._playing:
            self._playing = False
            self.btn_play.setText("\u25b6")
            if self._timer_id is not None:
                self.killTimer(self._timer_id)
                self._timer_id = None
        else:
            self._playing = True
            self.btn_play.setText("\u25a0")
            self._timer_id = self.startTimer(1000)

    def timerEvent(self, event):
        if self._playing:
            self._step(self._step_minutes)
