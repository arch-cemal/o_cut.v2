
"""
Main Application Window - UPDATED
With Ivory/Light Gray Theme and Black Text
"""
from PyQt6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                             QPushButton, QLabel, QStackedWidget, QFrame,
                             QApplication, QMessageBox)
from PyQt6.QtCore import Qt, QSize
from PyQt6.QtGui import QFont
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from core.database import DatabaseManager
from ui.inventory_window import InventoryWindow
from ui.cutting_inputs_window import CuttingInputsWindow
from ui.results_window import ResultsWindow

class SidebarButton(QPushButton):
    def __init__(self, text, icon_text, parent=None):
        super().__init__(f"{icon_text}  {text}", parent)
        self.setMinimumHeight(60)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                color: #ecf0f1;
                border: none;
                border-radius: 8px;
                padding: 15px 20px;
                font-size: 15px;
                font-weight: bold;
                text-align: right;
            }
            QPushButton:hover {
                background-color: #34495e;
            }
            QPushButton:checked {
                background-color: #3498db;
                color: white;
            }
        """)
        self.setCheckable(True)

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("نظام تحسين القص والتوزيع - Cutting Optimizer v2.0")
        self.setMinimumSize(1400, 900)

        self.db = DatabaseManager("cutting_optimizer.db")

        try:
            materials = self.db.get_raw_materials()
            if not materials:
                self.db.ensure_default_materials()
        except Exception as e:
            print(f"Warning: Could not load materials: {e}")

        self.setup_ui()
        self.apply_global_styles()

    def apply_global_styles(self):
        """Apply global stylesheet for consistent ivory background and black text"""
        self.setStyleSheet("""
            QMainWindow {
                background-color: #F8F9FA;
            }
            QWidget {
                background-color: #F8F9FA;
                color: #000000;
            }
            QLineEdit {
                background-color: white;
                color: #000000;
                border: 2px solid #dee2e6;
                border-radius: 6px;
                padding: 8px;
                font-size: 13px;
            }
            QLineEdit:focus {
                border: 2px solid #3498db;
            }
            QComboBox {
                background-color: white;
                color: #000000;
                border: 2px solid #dee2e6;
                border-radius: 6px;
                padding: 8px;
                font-size: 13px;
            }
            QComboBox QAbstractItemView {
                background-color: white;
                color: #000000;
                selection-background-color: #3498db;
                selection-color: white;
            }
            QSpinBox, QDoubleSpinBox {
                background-color: white;
                color: #000000;
                border: 2px solid #dee2e6;
                border-radius: 6px;
                padding: 5px;
            }
            QGroupBox {
                color: #000000;
                font-weight: bold;
                border: 2px solid #dee2e6;
                border-radius: 8px;
                margin-top: 10px;
                padding-top: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px;
                color: #000000;
            }
            QScrollArea {
                border: none;
                background-color: #F8F9FA;
            }
            QLabel {
                color: #000000;
            }
            QMessageBox {
                background-color: #F8F9FA;
            }
            QMessageBox QLabel {
                color: #000000;
            }
        """)

    def setup_ui(self):
        central = QWidget()
        self.setCentralWidget(central)

        main_layout = QHBoxLayout(central)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Sidebar
        self.sidebar = QFrame()
        self.sidebar.setFixedWidth(280)
        self.sidebar.setStyleSheet("""
            QFrame {
                background-color: #2c3e50;
                border-right: 3px solid #34495e;
            }
        """)
        sidebar_layout = QVBoxLayout(self.sidebar)
        sidebar_layout.setSpacing(10)
        sidebar_layout.setContentsMargins(15, 20, 15, 20)

        logo = QLabel("🔧 Cutting\nOptimizer")
        logo.setStyleSheet("""
            QLabel {
                color: #3498db;
                font-size: 22px;
                font-weight: bold;
                padding: 20px 10px;
            }
        """)
        logo.setAlignment(Qt.AlignmentFlag.AlignCenter)
        sidebar_layout.addWidget(logo)

        version = QLabel("v2.0 - Professional Edition")
        version.setStyleSheet("color: #7f8c8d; font-size: 11px;")
        version.setAlignment(Qt.AlignmentFlag.AlignCenter)
        sidebar_layout.addWidget(version)

        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setStyleSheet("background-color: #34495e;")
        sep.setFixedHeight(2)
        sidebar_layout.addWidget(sep)
        sidebar_layout.addSpacing(20)

        self.nav_buttons = []

        self.btn_inventory = SidebarButton("إدارة المخزن", "📦")
        self.btn_inventory.clicked.connect(lambda: self.switch_view(0))
        sidebar_layout.addWidget(self.btn_inventory)
        self.nav_buttons.append(self.btn_inventory)

        self.btn_inputs = SidebarButton("مدخلات القص", "✂️")
        self.btn_inputs.clicked.connect(lambda: self.switch_view(1))
        sidebar_layout.addWidget(self.btn_inputs)
        self.nav_buttons.append(self.btn_inputs)

        self.btn_results = SidebarButton("النتائج والتقارير", "📊")
        self.btn_results.clicked.connect(lambda: self.switch_view(2))
        sidebar_layout.addWidget(self.btn_results)
        self.nav_buttons.append(self.btn_results)

        sidebar_layout.addStretch()

        # System info footer
        footer_frame = QFrame()
        footer_frame.setStyleSheet("background-color: #1a252f; border-radius: 8px;")
        footer_layout = QVBoxLayout(footer_frame)

        db_label = QLabel("🗄️ SQLite Local DB")
        db_label.setStyleSheet("color: #7f8c8d; font-size: 11px;")
        db_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        footer_layout.addWidget(db_label)

        status_label = QLabel("✅ النظام جاهز")
        status_label.setStyleSheet("color: #27ae60; font-size: 11px;")
        status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        footer_layout.addWidget(status_label)

        sidebar_layout.addWidget(footer_frame)

        main_layout.addWidget(self.sidebar)

        # Content area with ivory background
        self.content = QStackedWidget()
        self.content.setStyleSheet("background-color: #F8F9FA;")

        self.inventory_window = InventoryWindow(self.db)
        self.inputs_window = CuttingInputsWindow(self.db)
        self.results_window = ResultsWindow(self.db)

        self.inventory_window.data_changed.connect(self.on_data_changed)
        self.inputs_window.inputs_changed.connect(self.on_data_changed)
        self.results_window.operation_confirmed.connect(self.on_operation_confirmed)
        self.results_window.operation_cancelled.connect(self.on_operation_cancelled)

        self.content.addWidget(self.inventory_window)
        self.content.addWidget(self.inputs_window)
        self.content.addWidget(self.results_window)

        main_layout.addWidget(self.content, 1)

        self.switch_view(0)

    def switch_view(self, index):
        self.content.setCurrentIndex(index)
        for i, btn in enumerate(self.nav_buttons):
            btn.setChecked(i == index)

        if index == 0:
            self.inventory_window.load_data()
        elif index == 1:
            self.inputs_window.load_inputs()

    def on_data_changed(self):
        pass

    def on_operation_confirmed(self):
        self.inventory_window.load_data()
        self.inputs_window.load_inputs()

    def on_operation_cancelled(self):
        pass

    def closeEvent(self, event):
        reply = QMessageBox.question(
            self, "خروج",
            "هل أنت متأكد من الخروج من البرنامج؟\n"
            "تأكد من حفظ عملك قبل الخروج.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            event.accept()
        else:
            event.ignore()
