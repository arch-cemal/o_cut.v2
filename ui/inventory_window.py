
"""
Inventory Management Window - UPDATED
"""
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                             QPushButton, QTableWidget, QTableWidgetItem, 
                             QLineEdit, QComboBox, QHeaderView, QDialog, 
                             QFormLayout, QSpinBox, QDoubleSpinBox, QTabWidget,
                             QMessageBox, QFrame)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QColor, QBrush
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from core.database import DatabaseManager, RawMaterial, Offcut

class AddMaterialDialog(QDialog):
    def __init__(self, parent=None, edit_mode=False, material_data=None):
        super().__init__(parent)
        self.edit_mode = edit_mode
        self.material_data = material_data
        self.setWindowTitle("تعديل مادة خام" if edit_mode else "إضافة مادة خام جديدة")
        self.setMinimumWidth(450)
        self.setup_ui()
        if edit_mode and material_data:
            self.load_data()

    def setup_ui(self):
        layout = QFormLayout(self)
        layout.setSpacing(12)

        # Material type dropdown
        self.type_combo = QComboBox()
        self.type_combo.setEditable(True)
        self.type_combo.addItems(["حديد تسليح", "شيلمان", "تيوبات", "ألومنيوم", "خشب", "ستانلس ستيل", "نحاس"])
        self.type_combo.setStyleSheet("""
            QComboBox {
                padding: 10px;
                border: 2px solid #bdc3c7;
                border-radius: 6px;
                font-size: 14px;
                background: white;
            }
        """)
        layout.addRow("نوع المادة*:", self.type_combo)

        self.profile_input = QLineEdit()
        self.profile_input.setPlaceholderText("مثال: Q235-40x40, SHL-30x30")
        self.profile_input.setStyleSheet("padding: 10px; border: 2px solid #bdc3c7; border-radius: 6px; font-size: 14px;")
        layout.addRow("نوع القطاع*:", self.profile_input)

        self.length_spin = QDoubleSpinBox()
        self.length_spin.setRange(100, 20000)
        self.length_spin.setValue(6000)
        self.length_spin.setSuffix(" مم")
        self.length_spin.setStyleSheet("padding: 5px; font-size: 14px;")
        layout.addRow("الطول القياسي*:", self.length_spin)

        self.quantity_spin = QSpinBox()
        self.quantity_spin.setRange(0, 9999)
        self.quantity_spin.setValue(10)
        self.quantity_spin.setStyleSheet("padding: 5px; font-size: 14px;")
        layout.addRow("الكمية*:", self.quantity_spin)

        btn_layout = QHBoxLayout()
        self.save_btn = QPushButton("حفظ التعديلات" if self.edit_mode else "حفظ")
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

        self.cancel_btn = QPushButton("إلغاء")
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

    def load_data(self):
        self.type_combo.setCurrentText(self.material_data['material_name'])
        self.profile_input.setText(self.material_data['profile_type'])
        self.length_spin.setValue(self.material_data['standard_length'])
        self.quantity_spin.setValue(self.material_data['quantity'])

    def validate_and_accept(self):
        if not self.type_combo.currentText().strip():
            QMessageBox.warning(self, "تنبيه", "يرجى تحديد نوع وخامة المعدن أولاً!")
            return
        if not self.profile_input.text().strip():
            QMessageBox.warning(self, "تنبيه", "يرجى إدخال نوع القطاع!")
            return
        self.accept()

    def get_data(self):
        return {
            'material_name': self.type_combo.currentText().strip(),
            'profile_type': self.profile_input.text().strip(),
            'standard_length': self.length_spin.value(),
            'quantity': self.quantity_spin.value()
        }

class InventoryWindow(QWidget):
    data_changed = pyqtSignal()

    def __init__(self, db_manager: DatabaseManager):
        super().__init__()
        self.db = db_manager
        self.current_filter = 'All'
        self.setup_ui()
        self.load_data()

    def setup_ui(self):
        self.setWindowTitle("إدارة المخزن")
        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(15)
        main_layout.setContentsMargins(20, 20, 20, 20)

        # Title
        title = QLabel("📦 إدارة المخزن والمواد الخام")
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

        # Tabs
        self.tabs = QTabWidget()
        self.tabs.setStyleSheet("""
            QTabWidget::pane { border: 2px solid #dee2e6; border-radius: 8px; background: #F8F9FA; }
            QTabBar::tab {
                background: #e9ecef;
                padding: 12px 24px;
                margin-right: 4px;
                border-top-left-radius: 8px;
                border-top-right-radius: 8px;
                font-weight: bold;
                color: #000000;
                font-size: 13px;
            }
            QTabBar::tab:selected { background: #3498db; color: white; }
            QTabBar::tab:hover { background: #dee2e6; }
        """)

        self.raw_tab = QWidget()
        self.setup_raw_tab()
        self.tabs.addTab(self.raw_tab, "📋 المواد الخام")

        self.offcut_tab = QWidget()
        self.setup_offcut_tab()
        self.tabs.addTab(self.offcut_tab, "♻️ الفضلات")

        main_layout.addWidget(self.tabs)

    def setup_raw_tab(self):
        layout = QVBoxLayout(self.raw_tab)
        layout.setSpacing(15)

        toolbar = QHBoxLayout()

        self.add_material_btn = QPushButton("➕ إضافة مادة خام")
        self.add_material_btn.setStyleSheet(self._button_style("#27ae60"))
        self.add_material_btn.clicked.connect(self.add_material)
        toolbar.addWidget(self.add_material_btn)

        self.edit_btn = QPushButton("✏️ تعديل مختار")
        self.edit_btn.setStyleSheet(self._button_style("#f39c12"))
        self.edit_btn.clicked.connect(self.edit_material)
        toolbar.addWidget(self.edit_btn)

        self.delete_btn = QPushButton("🗑️ حذف مختار")
        self.delete_btn.setStyleSheet(self._button_style("#e74c3c"))
        self.delete_btn.clicked.connect(self.delete_material)
        toolbar.addWidget(self.delete_btn)

        self.refresh_btn = QPushButton("🔄 تحديث")
        self.refresh_btn.setStyleSheet(self._button_style("#3498db"))
        self.refresh_btn.clicked.connect(self.load_data)
        toolbar.addWidget(self.refresh_btn)

        toolbar.addStretch()

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("🔍 بحث في المواد...")
        self.search_input.setStyleSheet("""
            QLineEdit {
                padding: 10px;
                border: 2px solid #dee2e6;
                border-radius: 8px;
                font-size: 14px;
                background: white;
                color: #000000;
            }
        """)
        self.search_input.textChanged.connect(self.filter_raw_table)
        toolbar.addWidget(self.search_input)

        layout.addLayout(toolbar)

        self.raw_table = QTableWidget()
        self.raw_table.setColumnCount(5)
        self.raw_table.setHorizontalHeaderLabels([
            "الرقم", "اسم المادة", "نوع القطاع", "الطول القياسي (مم)", "الكمية"
        ])
        self.raw_table.setStyleSheet(self._table_style())
        self.raw_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.raw_table.setAlternatingRowColors(True)
        self.raw_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        layout.addWidget(self.raw_table)

    def setup_offcut_tab(self):
        layout = QVBoxLayout(self.offcut_tab)
        layout.setSpacing(15)

        filter_bar = QHBoxLayout()

        filter_label = QLabel("🔍 فلترة الحالة:")
        filter_label.setStyleSheet("font-size: 14px; font-weight: bold; color: #000000;")
        filter_bar.addWidget(filter_label)

        self.filter_combo = QComboBox()
        self.filter_combo.addItems(["الكل", "متوفر", "تم الاستخدام"])
        self.filter_combo.setStyleSheet("""
            QComboBox {
                padding: 8px;
                border: 2px solid #dee2e6;
                border-radius: 6px;
                font-size: 14px;
                background: white;
                color: #000000;
                min-width: 150px;
            }
        """)
        self.filter_combo.currentTextChanged.connect(self.on_filter_changed)
        filter_bar.addWidget(self.filter_combo)

        filter_bar.addStretch()

        self.refresh_offcut_btn = QPushButton("🔄 تحديث")
        self.refresh_offcut_btn.setStyleSheet(self._button_style("#3498db"))
        self.refresh_offcut_btn.clicked.connect(self.load_data)
        filter_bar.addWidget(self.refresh_offcut_btn)

        layout.addLayout(filter_bar)

        self.offcut_table = QTableWidget()
        self.offcut_table.setColumnCount(6)
        self.offcut_table.setHorizontalHeaderLabels([
            "الرقم", "المادة", "القطاع", "الطول (مم)", "الكمية", "الحالة"
        ])
        self.offcut_table.setStyleSheet(self._table_style())
        self.offcut_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.offcut_table.setAlternatingRowColors(True)
        self.offcut_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        layout.addWidget(self.offcut_table)

        legend = QHBoxLayout()
        legend.addWidget(self._create_status_label("متوفر", "#27ae60"))
        legend.addWidget(self._create_status_label("تم الاستخدام", "#e74c3c"))
        legend.addStretch()
        layout.addLayout(legend)

    def _create_status_label(self, text, color):
        label = QLabel(f"  {text}  ")
        label.setStyleSheet(f"""
            QLabel {{
                background-color: {color};
                color: white;
                padding: 5px 15px;
                border-radius: 12px;
                font-weight: bold;
                font-size: 12px;
            }}
        """)
        return label

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

    def load_data(self):
        try:
            self.load_raw_materials()
            self.load_offcuts()
        except Exception as e:
            QMessageBox.critical(self, "خطأ", f"حدث خطأ أثناء تحميل البيانات:\n{str(e)}")

    def load_raw_materials(self):
        try:
            materials = self.db.get_raw_materials()
            self.raw_table.setRowCount(len(materials))

            for i, mat in enumerate(materials):
                self.raw_table.setItem(i, 0, QTableWidgetItem(str(mat.material_id)))
                self.raw_table.setItem(i, 1, QTableWidgetItem(mat.material_name))
                self.raw_table.setItem(i, 2, QTableWidgetItem(mat.profile_type))
                self.raw_table.setItem(i, 3, QTableWidgetItem(f"{mat.standard_length:,.0f}"))
                self.raw_table.setItem(i, 4, QTableWidgetItem(str(mat.quantity)))

                if mat.quantity <= 5:
                    for col in range(5):
                        item = self.raw_table.item(i, col)
                        if item:
                            item.setBackground(QBrush(QColor("#ffeaa7")))
        except Exception as e:
            QMessageBox.critical(self, "خطأ", f"خطأ في تحميل المواد الخام:\n{str(e)}")

    def load_offcuts(self):
        try:
            filter_text = self.filter_combo.currentText()
            if filter_text == "متوفر":
                offcuts = self.db.get_offcuts(status='Available')
            elif filter_text == "تم الاستخدام":
                offcuts = self.db.get_offcuts(status='Used')
            else:
                offcuts = self.db.get_offcuts()

            self.offcut_table.setRowCount(len(offcuts))

            for i, off in enumerate(offcuts):
                self.offcut_table.setItem(i, 0, QTableWidgetItem(str(off.offcut_id)))
                self.offcut_table.setItem(i, 1, QTableWidgetItem(off.material_name))
                self.offcut_table.setItem(i, 2, QTableWidgetItem(off.profile_type))
                self.offcut_table.setItem(i, 3, QTableWidgetItem(f"{off.length:,.0f}"))
                self.offcut_table.setItem(i, 4, QTableWidgetItem(str(off.quantity)))

                status_item = QTableWidgetItem(off.status)
                if off.status == 'Available':
                    status_item.setBackground(QBrush(QColor("#d5f5e3")))
                    status_item.setForeground(QBrush(QColor("#27ae60")))
                else:
                    status_item.setBackground(QBrush(QColor("#fadbd8")))
                    status_item.setForeground(QBrush(QColor("#e74c3c")))
                self.offcut_table.setItem(i, 5, status_item)
        except Exception as e:
            QMessageBox.critical(self, "خطأ", f"خطأ في تحميل الفضلات:\n{str(e)}")

    def on_filter_changed(self, text):
        self.load_offcuts()

    def filter_raw_table(self, text):
        for row in range(self.raw_table.rowCount()):
            match = False
            for col in range(self.raw_table.columnCount()):
                item = self.raw_table.item(row, col)
                if item and text.lower() in item.text().lower():
                    match = True
                    break
            self.raw_table.setRowHidden(row, not match)

    def add_material(self):
        try:
            dialog = AddMaterialDialog(self)
            if dialog.exec() == QDialog.DialogCode.Accepted:
                data = dialog.get_data()
                material = RawMaterial(
                    material_id=0,
                    material_name=data['material_name'],
                    profile_type=data['profile_type'],
                    standard_length=data['standard_length'],
                    quantity=data['quantity']
                )
                self.db.add_raw_material(material)
                self.load_raw_materials()
                self.data_changed.emit()
                QMessageBox.information(self, "نجاح", "تم إضافة المادة الخام بنجاح!")
        except Exception as e:
            QMessageBox.critical(self, "خطأ", f"حدث خطأ أثناء الإضافة:\n{str(e)}")

    def edit_material(self):
        try:
            selected = self.raw_table.selectedItems()
            if not selected:
                QMessageBox.warning(self, "تنبيه", "يرجى اختيار مادة خام للتعديل!")
                return

            row = selected[0].row()
            material_id = int(self.raw_table.item(row, 0).text())
            material = self.db.get_raw_material_by_id(material_id)

            if not material:
                QMessageBox.warning(self, "تنبيه", "لم يتم العثور على المادة!")
                return

            dialog = AddMaterialDialog(self, edit_mode=True, material_data={
                'material_name': material.material_name,
                'profile_type': material.profile_type,
                'standard_length': material.standard_length,
                'quantity': material.quantity
            })

            if dialog.exec() == QDialog.DialogCode.Accepted:
                data = dialog.get_data()
                self.db.update_raw_material(
                    material_id, data['material_name'], data['profile_type'],
                    data['standard_length'], data['quantity']
                )
                self.load_raw_materials()
                self.data_changed.emit()
                QMessageBox.information(self, "نجاح", "تم تعديل المادة بنجاح!")
        except Exception as e:
            QMessageBox.critical(self, "خطأ", f"حدث خطأ أثناء التعديل:\n{str(e)}")

    def delete_material(self):
        try:
            selected = self.raw_table.selectedItems()
            if not selected:
                QMessageBox.warning(self, "تنبيه", "يرجى اختيار مادة خام للحذف!")
                return

            row = selected[0].row()
            material_id = int(self.raw_table.item(row, 0).text())
            material_name = self.raw_table.item(row, 1).text()

            reply = QMessageBox.question(
                self, "تأكيد الحذف",
                f"هل أنت متأكد من حذف '{material_name}'؟\nسيتم حذف جميع الفضلات المرتبطة بها أيضاً!",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )

            if reply == QMessageBox.StandardButton.Yes:
                self.db.delete_raw_material(material_id)
                self.load_raw_materials()
                self.data_changed.emit()
                QMessageBox.information(self, "نجاح", "تم الحذف بنجاح!")
        except Exception as e:
            QMessageBox.critical(self, "خطأ", f"حدث خطأ أثناء الحذف:\n{str(e)}")
