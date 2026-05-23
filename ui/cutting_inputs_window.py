
"""
Cutting Inputs Window - UPDATED
"""
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                             QPushButton, QTableWidget, QTableWidgetItem, 
                             QLineEdit, QComboBox, QHeaderView, QDialog, 
                             QFormLayout, QSpinBox, QDoubleSpinBox, 
                             QColorDialog, QFrame, QCheckBox, QGroupBox)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QColor
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from core.database import DatabaseManager, OrderInput

class AddInputDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("إضافة قطعة جديدة")
        self.setMinimumWidth(450)
        self.selected_color = "#3498db"
        self.setup_ui()

    def setup_ui(self):
        layout = QFormLayout(self)
        layout.setSpacing(12)

        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("مثال: قائم خلفي، عارضة جانبية")
        self.name_input.setStyleSheet("padding: 10px; border: 2px solid #dee2e6; border-radius: 6px; font-size: 14px; color: #000000;")
        layout.addRow("اسم القطعة*:", self.name_input)

        self.length_spin = QDoubleSpinBox()
        self.length_spin.setRange(10, 20000)
        self.length_spin.setValue(1200)
        self.length_spin.setSuffix(" مم")
        self.length_spin.setStyleSheet("padding: 5px; font-size: 14px;")
        layout.addRow("الطول المطلوب*:", self.length_spin)

        self.quantity_spin = QSpinBox()
        self.quantity_spin.setRange(1, 999)
        self.quantity_spin.setValue(1)
        self.quantity_spin.setStyleSheet("padding: 5px; font-size: 14px;")
        layout.addRow("الكمية*:", self.quantity_spin)

        # Material source selection
        source_group = QGroupBox("مصدر المادة")
        source_group.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                color: #000000;
                border: 2px solid #dee2e6;
                border-radius: 6px;
                margin-top: 10px;
                padding-top: 10px;
            }
            QGroupBox::title { subcontrol-origin: margin; left: 10px; padding: 0 5px; }
        """)
        source_layout = QVBoxLayout(source_group)

        self.use_new_material = QCheckBox("✂️ القص من مواد جديدة / أطوال كاملة")
        self.use_new_material.setChecked(True)
        self.use_new_material.setStyleSheet("font-size: 13px; color: #000000; padding: 5px;")
        source_layout.addWidget(self.use_new_material)

        self.use_offcuts = QCheckBox("♻️ أولوية استخدام الفضلات المتوفرة أولاً")
        self.use_offcuts.setChecked(True)
        self.use_offcuts.setStyleSheet("font-size: 13px; color: #000000; padding: 5px;")
        source_layout.addWidget(self.use_offcuts)

        layout.addRow(source_group)

        # Color picker
        color_layout = QHBoxLayout()
        self.color_btn = QPushButton("اختيار اللون")
        self.color_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {self.selected_color};
                color: white;
                padding: 10px;
                border-radius: 5px;
                font-weight: bold;
            }}
        """)
        self.color_btn.clicked.connect(self.pick_color)
        color_layout.addWidget(self.color_btn)
        color_layout.addStretch()
        layout.addRow("لون القطعة:", color_layout)

        btn_layout = QHBoxLayout()
        self.save_btn = QPushButton("💾 حفظ")
        self.save_btn.setStyleSheet("""
            QPushButton {
                background-color: #27ae60;
                color: white;
                padding: 12px 24px;
                border-radius: 6px;
                font-weight: bold;
                font-size: 14px;
            }
            QPushButton:hover { background-color: #229954; }
        """)
        self.save_btn.clicked.connect(self.validate_and_accept)

        self.cancel_btn = QPushButton("❌ إلغاء")
        self.cancel_btn.setStyleSheet("""
            QPushButton {
                background-color: #e74c3c;
                color: white;
                padding: 12px 24px;
                border-radius: 6px;
                font-weight: bold;
                font-size: 14px;
            }
            QPushButton:hover { background-color: #c0392b; }
        """)
        self.cancel_btn.clicked.connect(self.reject)

        btn_layout.addWidget(self.save_btn)
        btn_layout.addWidget(self.cancel_btn)
        layout.addRow(btn_layout)

    def pick_color(self):
        color = QColorDialog.getColor(QColor(self.selected_color), self)
        if color.isValid():
            self.selected_color = color.name()
            self.color_btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: {self.selected_color};
                    color: white;
                    padding: 10px;
                    border-radius: 5px;
                    font-weight: bold;
                }}
            """)

    def validate_and_accept(self):
        if not self.name_input.text().strip():
            from PyQt6.QtWidgets import QMessageBox
            QMessageBox.warning(self, "تنبيه", "يرجى إدخال اسم القطعة!")
            return
        self.accept()

    def get_data(self):
        return {
            'part_name': self.name_input.text().strip(),
            'required_length': self.length_spin.value(),
            'required_quantity': self.quantity_spin.value(),
            'part_color': self.selected_color,
            'use_new_material': self.use_new_material.isChecked(),
            'use_offcuts': self.use_offcuts.isChecked()
        }

class CuttingInputsWindow(QWidget):
    inputs_changed = pyqtSignal()

    def __init__(self, db_manager: DatabaseManager):
        super().__init__()
        self.db = db_manager
        self.setup_ui()
        self.load_inputs()

    def setup_ui(self):
        self.setWindowTitle("مدخلات القص")
        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(15)
        main_layout.setContentsMargins(20, 20, 20, 20)

        title = QLabel("✂️ مدخلات عملية القص")
        title.setStyleSheet("""
            QLabel {
                font-size: 24px;
                font-weight: bold;
                color: #000000;
                padding: 10px;
            }
        """)
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        main_layout.addWidget(title)

        info = QLabel("أدخل الأطوال والكميات المطلوبة للقص. يمكنك تحديد مصدر المادة (جديدة أو فضلات).")
        info.setStyleSheet("color: #495057; font-size: 13px; padding: 5px;")
        info.setAlignment(Qt.AlignmentFlag.AlignCenter)
        info.setWordWrap(True)
        main_layout.addWidget(info)

        toolbar = QHBoxLayout()

        self.add_btn = QPushButton("➕ إضافة قطعة")
        self.add_btn.setStyleSheet(self._button_style("#27ae60"))
        self.add_btn.clicked.connect(self.add_input)
        toolbar.addWidget(self.add_btn)

        self.delete_btn = QPushButton("🗑️ حذف مختار")
        self.delete_btn.setStyleSheet(self._button_style("#e74c3c"))
        self.delete_btn.clicked.connect(self.delete_selected)
        toolbar.addWidget(self.delete_btn)

        self.clear_btn = QPushButton("🧹 مسح الكل")
        self.clear_btn.setStyleSheet(self._button_style("#f39c12"))
        self.clear_btn.clicked.connect(self.clear_all)
        toolbar.addWidget(self.clear_btn)

        toolbar.addStretch()

        self.refresh_btn = QPushButton("🔄 تحديث")
        self.refresh_btn.setStyleSheet(self._button_style("#3498db"))
        self.refresh_btn.clicked.connect(self.load_inputs)
        toolbar.addWidget(self.refresh_btn)

        main_layout.addLayout(toolbar)

        self.table = QTableWidget()
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels([
            "الرقم", "اسم القطعة", "الطول (مم)", "الكمية", "اللون", "المصدر"
        ])
        self.table.setStyleSheet(self._table_style())
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.setAlternatingRowColors(True)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        main_layout.addWidget(self.table)

        self.summary_label = QLabel("إجمالي القطع: 0 | إجمالي الطول المطلوب: 0 مم")
        self.summary_label.setStyleSheet("""
            QLabel {
                font-size: 14px;
                font-weight: bold;
                color: #000000;
                padding: 10px;
                background: #e9ecef;
                border-radius: 8px;
            }
        """)
        self.summary_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        main_layout.addWidget(self.summary_label)

    def _button_style(self, color):
        return f"""
            QPushButton {{
                background-color: {color};
                color: white;
                padding: 10px 20px;
                border-radius: 6px;
                font-weight: bold;
                font-size: 13px;
            }}
            QPushButton:hover {{ background-color: {color}dd; }}
        """

    def _table_style(self):
        return """
            QTableWidget {
                background-color: white;
                border: 2px solid #dee2e6;
                border-radius: 8px;
                gridline-color: #e9ecef;
                font-size: 13px;
                color: #000000;
            }
            QTableWidget::item { padding: 8px; }
            QHeaderView::section {
                background-color: #34495e;
                color: white;
                padding: 10px;
                font-weight: bold;
                border: none;
            }
            QTableWidget::item:selected {
                background-color: #3498db;
                color: white;
            }
        """

    def load_inputs(self):
        try:
            inputs = self.db.get_order_inputs()
            self.table.setRowCount(len(inputs))

            total_pieces = 0
            total_length = 0

            for i, inp in enumerate(inputs):
                self.table.setItem(i, 0, QTableWidgetItem(str(inp.input_id)))
                self.table.setItem(i, 1, QTableWidgetItem(inp.part_name))
                self.table.setItem(i, 2, QTableWidgetItem(f"{inp.required_length:,.0f}"))
                self.table.setItem(i, 3, QTableWidgetItem(str(inp.required_quantity)))

                color_item = QTableWidgetItem("  ●  ")
                color_item.setBackground(QColor(inp.part_color))
                color_item.setForeground(QColor("white"))
                color_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                self.table.setItem(i, 4, color_item)

                source_item = QTableWidgetItem("جديد + فضلات")
                source_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                self.table.setItem(i, 5, source_item)

                total_pieces += inp.required_quantity
                total_length += inp.required_length * inp.required_quantity

            self.summary_label.setText(
                f"📊 إجمالي القطع: {total_pieces} | 📏 إجمالي الطول المطلوب: {total_length:,.0f} مم"
            )
        except Exception as e:
            QMessageBox.critical(self, "خطأ", f"خطأ في تحميل المدخلات:\n{str(e)}")

    def add_input(self):
        try:
            dialog = AddInputDialog(self)
            if dialog.exec() == QDialog.DialogCode.Accepted:
                data = dialog.get_data()
                order_input = OrderInput(
                    input_id=0,
                    required_length=data['required_length'],
                    required_quantity=data['required_quantity'],
                    part_name=data['part_name'],
                    part_color=data['part_color']
                )
                self.db.add_order_input(order_input, data['use_new_material'])
                self.load_inputs()
                self.inputs_changed.emit()
                QMessageBox.information(self, "نجاح", "✅ تم إضافة القطعة بنجاح!")
        except Exception as e:
            QMessageBox.critical(self, "خطأ", f"حدث خطأ أثناء الإضافة:\n{str(e)}")

    def delete_selected(self):
        try:
            selected = self.table.selectedItems()
            if not selected:
                QMessageBox.warning(self, "تنبيه", "يرجى اختيار قطعة للحذف!")
                return

            row = selected[0].row()
            input_id = int(self.table.item(row, 0).text())

            reply = QMessageBox.question(
                self, "تأكيد الحذف",
                "هل أنت متأكد من حذف هذه القطعة؟",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )

            if reply == QMessageBox.StandardButton.Yes:
                self.db.delete_order_input(input_id)
                self.load_inputs()
                self.inputs_changed.emit()
        except Exception as e:
            QMessageBox.critical(self, "خطأ", f"حدث خطأ أثناء الحذف:\n{str(e)}")

    def clear_all(self):
        try:
            reply = QMessageBox.question(
                self, "تأكيد المسح",
                "هل أنت متأكد من مسح جميع المدخلات؟",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )

            if reply == QMessageBox.StandardButton.Yes:
                self.db.clear_order_inputs()
                self.load_inputs()
                self.inputs_changed.emit()
        except Exception as e:
            QMessageBox.critical(self, "خطأ", f"حدث خطأ أثناء المسح:\n{str(e)}")

    def get_all_inputs(self):
        try:
            inputs = self.db.get_order_inputs()
            return [{
                'input_id': inp.input_id,
                'length': inp.required_length,
                'quantity': inp.required_quantity,
                'name': inp.part_name,
                'color': inp.part_color
            } for inp in inputs]
        except Exception as e:
            QMessageBox.critical(self, "خطأ", f"خطأ في جلب المدخلات:\n{str(e)}")
            return []
