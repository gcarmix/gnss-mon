#!/usr/bin/env python3
"""GNSS Monitor - Entry point."""

import sys

from PyQt6.QtWidgets import QApplication
from PyQt6.QtGui import QFont

from gnss_mon.gui.main_window import MainWindow

DARK_STYLESHEET = """
QMainWindow, QWidget {
    background-color: #1e1e2e;
    color: #cdd6f4;
}
QMenuBar {
    background-color: #181825;
    color: #cdd6f4;
    border-bottom: 1px solid #313244;
    font-size: 13px;
    padding: 2px;
}
QMenuBar::item:selected {
    background-color: #45475a;
    border-radius: 4px;
}
QMenu {
    background-color: #1e1e2e;
    color: #cdd6f4;
    border: 1px solid #313244;
    border-radius: 6px;
    padding: 4px;
}
QMenu::item:selected {
    background-color: #45475a;
    border-radius: 4px;
}
QTabWidget::pane {
    border: 1px solid #313244;
    border-radius: 6px;
    background-color: #1e1e2e;
}
QTabBar::tab {
    background-color: #181825;
    color: #a6adc8;
    border: 1px solid #313244;
    border-bottom: none;
    padding: 8px 18px;
    margin-right: 2px;
    border-top-left-radius: 6px;
    border-top-right-radius: 6px;
    font-size: 13px;
}
QTabBar::tab:selected {
    background-color: #1e1e2e;
    color: #cdd6f4;
    font-weight: bold;
}
QTabBar::tab:hover:!selected {
    background-color: #313244;
}
QPushButton {
    background-color: #313244;
    color: #cdd6f4;
    border: 1px solid #45475a;
    border-radius: 6px;
    padding: 5px 12px;
    font-size: 13px;
    font-weight: bold;
}
QPushButton:hover {
    background-color: #45475a;
    border-color: #585b70;
}
QPushButton:pressed {
    background-color: #585b70;
}
QSpinBox, QDoubleSpinBox, QDateTimeEdit {
    background-color: #313244;
    color: #cdd6f4;
    border: 1px solid #45475a;
    border-radius: 6px;
    padding: 4px 8px;
    font-size: 13px;
}
QSpinBox:focus, QDoubleSpinBox:focus, QDateTimeEdit:focus {
    border-color: #89b4fa;
}
QSpinBox::up-button, QSpinBox::down-button,
QDoubleSpinBox::up-button, QDoubleSpinBox::down-button,
QDateTimeEdit::up-button, QDateTimeEdit::down-button {
    background-color: #45475a;
    border: none;
    border-radius: 3px;
    width: 16px;
}
QSpinBox::up-button:hover, QSpinBox::down-button:hover,
QDoubleSpinBox::up-button:hover, QDoubleSpinBox::down-button:hover,
QDateTimeEdit::up-button:hover, QDateTimeEdit::down-button:hover {
    background-color: #585b70;
}
QTableWidget {
    background-color: #1e1e2e;
    alternate-background-color: #181825;
    color: #cdd6f4;
    gridline-color: #313244;
    border: 1px solid #313244;
    border-radius: 6px;
    font-size: 12px;
    selection-background-color: #45475a;
    selection-color: #cdd6f4;
}
QHeaderView::section {
    background-color: #181825;
    color: #a6adc8;
    border: 1px solid #313244;
    padding: 5px 8px;
    font-size: 12px;
    font-weight: bold;
}
QCheckBox {
    spacing: 6px;
    font-size: 13px;
}
QCheckBox::indicator {
    width: 16px;
    height: 16px;
    border: 2px solid #45475a;
    border-radius: 4px;
    background-color: #313244;
}
QCheckBox::indicator:checked {
    background-color: #89b4fa;
    border-color: #89b4fa;
}
QCheckBox::indicator:hover {
    border-color: #89b4fa;
}
QGroupBox {
    color: #cdd6f4;
    border: 1px solid #313244;
    border-radius: 8px;
    margin-top: 12px;
    padding-top: 16px;
    font-size: 14px;
    font-weight: bold;
}
QGroupBox::title {
    subcontrol-origin: margin;
    left: 16px;
    padding: 0 6px;
}
QStatusBar {
    background-color: #181825;
    color: #a6adc8;
    border-top: 1px solid #313244;
    font-size: 12px;
}
QLabel {
    color: #cdd6f4;
}
QScrollBar:vertical {
    background-color: #181825;
    width: 10px;
    border-radius: 5px;
}
QScrollBar::handle:vertical {
    background-color: #45475a;
    border-radius: 5px;
    min-height: 30px;
}
QScrollBar::handle:vertical:hover {
    background-color: #585b70;
}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0px;
}
QScrollBar:horizontal {
    background-color: #181825;
    height: 10px;
    border-radius: 5px;
}
QScrollBar::handle:horizontal {
    background-color: #45475a;
    border-radius: 5px;
    min-width: 30px;
}
QScrollBar::handle:horizontal:hover {
    background-color: #585b70;
}
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {
    width: 0px;
}
QDialog {
    background-color: #1e1e2e;
    color: #cdd6f4;
}
QDialogButtonBox QPushButton {
    min-width: 80px;
}
QMessageBox {
    background-color: #1e1e2e;
}
QCalendarWidget {
    background-color: #1e1e2e;
    color: #cdd6f4;
}
QCalendarWidget QAbstractItemView {
    background-color: #1e1e2e;
    color: #cdd6f4;
    selection-background-color: #45475a;
    selection-color: #cdd6f4;
}
"""


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("GNSS Monitor")
    app.setStyle("Fusion")
    app.setStyleSheet(DARK_STYLESHEET)

    font = QFont("Inter")
    if not font.exactMatch():
        font = QFont("Segoe UI")
        if not font.exactMatch():
            font = QFont("sans-serif")
    font.setPointSize(10)
    app.setFont(font)

    window = MainWindow()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
