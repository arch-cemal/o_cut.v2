
"""
Cutting Optimizer - Main Entry Point v2.0
نظام تحسين القص والتوزيع الأمثل
"""
import sys
import os

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont
from ui.main_window import MainWindow

def main():
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )

    app = QApplication(sys.argv)

    # Set global font for Arabic support
    font = QFont("Segoe UI", 10)
    app.setFont(font)

    app.setStyle("Fusion")

    window = MainWindow()
    window.show()

    sys.exit(app.exec())

if __name__ == "__main__":
    main()
