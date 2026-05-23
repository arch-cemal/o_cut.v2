
"""
Cutting Results & Output Window - UPDATED
With Print Support and Scrap/Offcuts Categorization
"""
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                             QPushButton, QTableWidget, QTableWidgetItem, 
                             QGroupBox, QMessageBox, QHeaderView, QScrollArea,
                             QFrame, QSplitter, QSizePolicy, QApplication,
                             QPrinter, QPrintDialog, QFileDialog)
from PyQt6.QtCore import Qt, pyqtSignal, QRectF
from PyQt6.QtGui import QPainter, QColor, QPen, QFont, QBrush, QLinearGradient, QPixmap
import sys
import os
from datetime import datetime
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from core.database import DatabaseManager
from core.optimizer import CuttingOptimizer

class BarChartWidget(QFrame):
    def __init__(self, visual_data, parent=None):
        super().__init__(parent)
        self.visual_data = visual_data
        self.setMinimumHeight(400)
        self.setFrameStyle(QFrame.Shape.StyledPanel | QFrame.Shadow.Sunken)
        self.setStyleSheet("background-color: white; border-radius: 8px; border: 2px solid #dee2e6;")

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        if not self.visual_data:
            painter.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, "لا توجد بيانات للعرض")
            return

        y_offset = 20
        bar_height = 60
        bar_spacing = 80
        left_margin = 180
        right_margin = 50
        available_width = self.width() - left_margin - right_margin

        max_length = max(bar['original_length'] for bar in self.visual_data)
        scale = available_width / max_length if max_length > 0 else 1

        font = QFont("Arial", 9)
        painter.setFont(font)

        for i, bar in enumerate(self.visual_data):
            y = y_offset + i * bar_spacing
            bar_width = bar['original_length'] * scale

            stock_type = "♻️ فضلة" if bar['is_offcut'] else "📦 خام"
            label_text = f"{stock_type} #{bar['stock_id']}\n{bar['material_name']} | {bar['original_length']:,.0f}مم"
            painter.setPen(QPen(QColor("#000000"), 1))
            painter.drawText(10, y + 10, left_margin - 20, bar_height, 
                           Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter, label_text)

            bg_rect = QRectF(left_margin, y, bar_width, bar_height)
            painter.setBrush(QBrush(QColor("#f8f9fa")))
            painter.setPen(QPen(QColor("#dee2e6"), 1))
            painter.drawRect(bg_rect)

            x_pos = left_margin
            for segment in bar['segments']:
                seg_width = segment['length'] * scale

                if segment.get('is_waste'):
                    is_scrap = segment.get('is_scrap', False)
                    color = QColor("#e74c3c") if is_scrap else QColor("#27ae60")
                    painter.setBrush(QBrush(color))
                    painter.setPen(QPen(color.darker(120), 1))
                    waste_rect = QRectF(x_pos, y, seg_width, bar_height)
                    painter.drawRect(waste_rect)

                    painter.setPen(QPen(QColor("white"), 1))
                    label = "هدر تالف" if is_scrap else "فضلة صالحة"
                    painter.drawText(waste_rect, Qt.AlignmentFlag.AlignCenter, 
                                   f"{label}\n{segment['length']:,.0f}مم")
                else:
                    color = QColor(segment['color'])
                    gradient = QLinearGradient(x_pos, y, x_pos, y + bar_height)
                    gradient.setColorAt(0, color.lighter(120))
                    gradient.setColorAt(1, color)
                    painter.setBrush(QBrush(gradient))

                    if segment.get('is_splice'):
                        pen = QPen(QColor("#e74c3c"), 2, Qt.PenStyle.DashLine)
                    else:
                        pen = QPen(color.darker(120), 1)
                    painter.setPen(pen)

                    seg_rect = QRectF(x_pos, y, seg_width, bar_height)
                    painter.drawRect(seg_rect)

                    painter.setPen(QPen(QColor("white"), 1))
                    name_text = segment['name']
                    if len(name_text) > 15:
                        name_text = name_text[:12] + "..."

                    display_text = f"{segment['length']:,.0f}مم\n{name_text}"
                    if segment.get('is_splice'):
                        display_text += f"\n[جزء {segment.get('splice_part', '')}]"

                    painter.drawText(seg_rect, Qt.AlignmentFlag.AlignCenter, display_text)

                x_pos += seg_width

            painter.setPen(QPen(QColor("#6c757d"), 1))
            for marker in [0, bar['original_length']/2, bar['original_length']]:
                mx = left_margin + marker * scale
                painter.drawLine(int(mx), y + bar_height, int(mx), y + bar_height + 10)
                painter.drawText(int(mx - 20), y + bar_height + 25, f"{marker:,.0f}")

        painter.end()

class ResultsWindow(QWidget):
    operation_confirmed = pyqtSignal()
    operation_cancelled = pyqtSignal()

    def __init__(self, db_manager: DatabaseManager):
        super().__init__()
        self.db = db_manager
        self.optimizer = None
        self.current_plan = None
        self.current_operation_id = None
        self.visual_data = []
        self.detailed_view = True
        self.setup_ui()

    def setup_ui(self):
        self.setWindowTitle("نتائج القص والتوزيع الأمثل")
        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(15)
        main_layout.setContentsMargins(20, 20, 20, 20)

        title_layout = QHBoxLayout()
        self.title = QLabel("📊 نتائج التوزيع الأمثل للقص")
        self.title.setStyleSheet("""
            QLabel {
                font-size: 24px;
                font-weight: bold;
                color: #000000;
                padding: 10px;
            }
        """)
        title_layout.addWidget(self.title)
        title_layout.addStretch()

        self.toggle_btn = QPushButton("🔍 تبديل العرض")
        self.toggle_btn.setStyleSheet(self._button_style("#9b59b6"))
        self.toggle_btn.clicked.connect(self.toggle_view)
        title_layout.addWidget(self.toggle_btn)

        main_layout.addLayout(title_layout)

        action_layout = QHBoxLayout()

        self.calculate_btn = QPushButton("🧮 حساب التوزيع الأمثل")
        self.calculate_btn.setStyleSheet(self._button_style("#3498db"))
        self.calculate_btn.clicked.connect(self.calculate_cutting)
        action_layout.addWidget(self.calculate_btn)

        self.confirm_btn = QPushButton("✅ تأكيد تنفيذ القص")
        self.confirm_btn.setStyleSheet(self._button_style("#27ae60"))
        self.confirm_btn.clicked.connect(self.confirm_operation)
        self.confirm_btn.setEnabled(False)
        action_layout.addWidget(self.confirm_btn)

        self.cancel_btn = QPushButton("❌ إلغاء العملية")
        self.cancel_btn.setStyleSheet(self._button_style("#e74c3c"))
        self.cancel_btn.clicked.connect(self.cancel_operation)
        self.cancel_btn.setEnabled(False)
        action_layout.addWidget(self.cancel_btn)

        self.print_btn = QPushButton("🖨️ طباعة التقرير")
        self.print_btn.setStyleSheet(self._button_style("#6c757d"))
        self.print_btn.clicked.connect(self.print_report)
        self.print_btn.setEnabled(False)
        action_layout.addWidget(self.print_btn)

        action_layout.addStretch()
        main_layout.addLayout(action_layout)

        self.splitter = QSplitter(Qt.Orientation.Vertical)

        self.chart_scroll = QScrollArea()
        self.chart_scroll.setWidgetResizable(True)
        self.chart_container = QWidget()
        self.chart_layout = QVBoxLayout(self.chart_container)
        self.chart_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.chart_scroll.setWidget(self.chart_container)
        self.splitter.addWidget(self.chart_scroll)

        self.details_widget = QWidget()
        details_layout = QVBoxLayout(self.details_widget)

        self.stats_group = QGroupBox("📈 الإحصائيات")
        self.stats_group.setStyleSheet("""
            QGroupBox {
                font-size: 16px;
                font-weight: bold;
                color: #000000;
                border: 2px solid #3498db;
                border-radius: 8px;
                margin-top: 10px;
                padding-top: 10px;
            }
            QGroupBox::title { subcontrol-origin: margin; left: 10px; padding: 0 5px; }
        """)
        stats_layout = QHBoxLayout(self.stats_group)

        self.stats_labels = {}
        stats_items = [
            ("total_pieces", "إجمالي القطع", "#3498db"),
            ("waste_percentage", "نسبة الهدر", "#e74c3c"),
            ("efficiency", "الكفاءة", "#27ae60"),
            ("raw_used", "الخام المستخدم", "#f39c12"),
            ("offcuts_used", "الفضلات المستخدمة", "#9b59b6"),
            ("spliced", "الموصولة", "#e67e22"),
            ("scrap", "الهدر التالف", "#dc3545"),
            ("reusable", "الفضلات الصالحة", "#28a745"),
        ]

        for key, label, color in stats_items:
            frame = QFrame()
            frame.setStyleSheet(f"""
                QFrame {{
                    background-color: {color}15;
                    border: 2px solid {color};
                    border-radius: 8px;
                    padding: 10px;
                }}
            """)
            frame_layout = QVBoxLayout(frame)

            title = QLabel(label)
            title.setStyleSheet(f"color: {color}; font-weight: bold; font-size: 11px;")
            title.setAlignment(Qt.AlignmentFlag.AlignCenter)
            frame_layout.addWidget(title)

            value = QLabel("0")
            value.setStyleSheet(f"color: {color}; font-size: 18px; font-weight: bold;")
            value.setAlignment(Qt.AlignmentFlag.AlignCenter)
            frame_layout.addWidget(value)

            self.stats_labels[key] = value
            stats_layout.addWidget(frame)

        details_layout.addWidget(self.stats_group)

        # Scrap table
        scrap_group = QGroupBox("🔴 قطع مهدرة (Scrap) - غير صالحة للاستخدام")
        scrap_group.setStyleSheet("""
            QGroupBox {
                font-size: 14px;
                font-weight: bold;
                color: #dc3545;
                border: 2px solid #dc3545;
                border-radius: 8px;
                margin-top: 10px;
                padding-top: 10px;
            }
            QGroupBox::title { subcontrol-origin: margin; left: 10px; padding: 0 5px; }
        """)
        scrap_layout = QVBoxLayout(scrap_group)
        self.scrap_table = QTableWidget()
        self.scrap_table.setColumnCount(4)
        self.scrap_table.setHorizontalHeaderLabels(["المادة", "القطاع", "الطول (مم)", "السبب"])
        self.scrap_table.setStyleSheet(self._table_style())
        self.scrap_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.scrap_table.setMaximumHeight(150)
        scrap_layout.addWidget(self.scrap_table)
        details_layout.addWidget(scrap_group)

        # Reusable offcuts table
        offcut_group = QGroupBox("🟢 فضلات صالحة (Reusable) - للمشاريع القادمة")
        offcut_group.setStyleSheet("""
            QGroupBox {
                font-size: 14px;
                font-weight: bold;
                color: #28a745;
                border: 2px solid #28a745;
                border-radius: 8px;
                margin-top: 10px;
                padding-top: 10px;
            }
            QGroupBox::title { subcontrol-origin: margin; left: 10px; padding: 0 5px; }
        """)
        offcut_layout = QVBoxLayout(offcut_group)
        self.reusable_table = QTableWidget()
        self.reusable_table.setColumnCount(4)
        self.reusable_table.setHorizontalHeaderLabels(["المادة", "القطاع", "الطول (مم)", "الحالة"])
        self.reusable_table.setStyleSheet(self._table_style())
        self.reusable_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.reusable_table.setMaximumHeight(150)
        offcut_layout.addWidget(self.reusable_table)
        details_layout.addWidget(offcut_group)

        # Details table
        self.details_table = QTableWidget()
        self.details_table.setColumnCount(6)
        self.details_table.setHorizontalHeaderLabels([
            "المادة", "القطاع", "الطول الأصلي", "المستخدم", "الهدر", "نوع المصدر"
        ])
        self.details_table.setStyleSheet(self._table_style())
        self.details_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.details_table.setAlternatingRowColors(True)
        self.details_table.setMaximumHeight(250)
        details_layout.addWidget(self.details_table)

        self.splitter.addWidget(self.details_widget)
        self.splitter.setSizes([500, 500])

        main_layout.addWidget(self.splitter)

        self.status_label = QLabel("جاهز للحساب... اضغط 'حساب التوزيع الأمثل' للبدء")
        self.status_label.setStyleSheet("""
            QLabel {
                padding: 10px;
                background: #e9ecef;
                border-radius: 5px;
                color: #495057;
                font-size: 13px;
            }
        """)
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        main_layout.addWidget(self.status_label)

    def _button_style(self, color):
        return f"""
            QPushButton {{
                background-color: {color};
                color: white;
                padding: 12px 24px;
                border-radius: 6px;
                font-weight: bold;
                font-size: 13px;
            }}
            QPushButton:hover {{ background-color: {color}dd; }}
            QPushButton:disabled {{ background-color: #adb5bd; }}
        """

    def _table_style(self):
        return """
            QTableWidget {
                background-color: white;
                border: 2px solid #dee2e6;
                border-radius: 8px;
                gridline-color: #e9ecef;
                font-size: 12px;
                color: #000000;
            }
            QTableWidget::item { padding: 6px; }
            QHeaderView::section {
                background-color: #34495e;
                color: white;
                padding: 8px;
                font-weight: bold;
                border: none;
            }
        """

    def calculate_cutting(self):
        try:
            inputs = self.db.get_order_inputs()
            if not inputs:
                QMessageBox.warning(self, "تنبيه", "لا توجد مدخلات للقص! يرجى إضافة قطع أولاً.")
                return

            required_pieces = [{
                'input_id': inp.input_id,
                'length': inp.required_length,
                'quantity': inp.required_quantity,
                'name': inp.part_name,
                'color': inp.part_color
            } for inp in inputs]

            raw_materials = self.db.get_raw_materials()
            raw_list = [{
                'material_id': mat.material_id,
                'material_name': mat.material_name,
                'profile_type': mat.profile_type,
                'standard_length': mat.standard_length,
                'quantity': mat.quantity,
                'unit_price': 0
            } for mat in raw_materials]

            offcuts = self.db.get_offcuts(status='Available')
            offcut_list = [{
                'offcut_id': off.offcut_id,
                'material_id': off.material_id,
                'material_name': off.material_name,
                'profile_type': off.profile_type,
                'length': off.length,
                'quantity': off.quantity,
                'status': off.status
            } for off in offcuts]

            self.optimizer = CuttingOptimizer(kerf_thickness=3.0, joint_loss=2.0, min_offcut_length=500.0)

            self.current_plan = self.optimizer.optimize(
                required_pieces, raw_list, offcut_list,
                use_offcuts_first=True, use_new_materials=True
            )
            self.visual_data = self.optimizer.generate_visual_data(self.current_plan)
            stats = self.optimizer.calculate_statistics(self.current_plan, raw_list)

            self.current_operation_id = self.db.create_operation(
                kerf=3.0, joint_loss=2.0, min_offcut=500.0, use_offcuts_first=True
            )

            for sp in self.current_plan.stock_pieces:
                if not sp.used:
                    continue
                detail = {
                    'input_id': sp.cuts[0]['input_id'] if sp.cuts else None,
                    'material_id': sp.material_id,
                    'offcut_id': sp.id if sp.is_offcut else None,
                    'source_type': 'Offcut' if sp.is_offcut else 'Raw',
                    'original_length': sp.length,
                    'used_length': sp.length - sp.remaining,
                    'waste_length': sp.remaining,
                    'is_spliced': False
                }
                self.db.add_operation_detail(self.current_operation_id, detail)

            for splice in self.current_plan.spliced_pieces:
                detail = {
                    'input_id': None,
                    'material_id': splice['material_id'],
                    'offcut_id': None,
                    'source_type': 'Spliced',
                    'original_length': splice['total_used'],
                    'used_length': splice['total_used'],
                    'waste_length': 0,
                    'is_spliced': True,
                    'splice_piece_1_id': splice['splice1_id'],
                    'splice_piece_1_length': splice['splice1_length'],
                    'splice_piece_2_id': splice['splice2_id'],
                    'splice_piece_2_length': splice['splice2_length'],
                    'joint_loss_used': splice['joint_loss']
                }
                self.db.add_operation_detail(self.current_operation_id, detail)

            self.update_chart()
            self.update_statistics(stats)
            self.update_details_table()
            self.update_waste_tables()

            self.confirm_btn.setEnabled(True)
            self.cancel_btn.setEnabled(True)
            self.print_btn.setEnabled(True)
            self.status_label.setText(
                f"✅ تم إنشاء خطة القص رقم #{self.current_operation_id} | "
                f"الكفاءة: {stats['efficiency']}% | في انتظار التأكيد"
            )
            self.status_label.setStyleSheet("""
                QLabel {
                    padding: 10px;
                    background: #fff3cd;
                    border-radius: 5px;
                    color: #856404;
                    font-weight: bold;
                    font-size: 13px;
                }
            """)
        except Exception as e:
            QMessageBox.critical(self, "خطأ في الحساب", f"حدث خطأ أثناء حساب التوزيع:\n{str(e)}")

    def update_chart(self):
        while self.chart_layout.count():
            item = self.chart_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        chart = BarChartWidget(self.visual_data)
        self.chart_layout.addWidget(chart)

    def update_statistics(self, stats):
        self.stats_labels['total_pieces'].setText(str(stats['total_pieces']))
        self.stats_labels['waste_percentage'].setText(f"{stats['waste_percentage']}%")
        self.stats_labels['efficiency'].setText(f"{stats['efficiency']}%")
        self.stats_labels['raw_used'].setText(str(stats['raw_materials_used']))
        self.stats_labels['offcuts_used'].setText(str(stats['offcuts_used']))
        self.stats_labels['spliced'].setText(str(stats['spliced_pieces']))
        self.stats_labels['scrap'].setText(f"{stats['scrap_count']} ({stats['scrap_total']:,.0f}مم)")
        self.stats_labels['reusable'].setText(f"{stats['reusable_count']} ({stats['reusable_total']:,.0f}مم)")

    def update_waste_tables(self):
        if not self.current_plan:
            return

        # Scrap table
        scrap_items = self.current_plan.scrap_pieces
        self.scrap_table.setRowCount(len(scrap_items))
        for i, scrap in enumerate(scrap_items):
            self.scrap_table.setItem(i, 0, QTableWidgetItem(scrap['material_name']))
            self.scrap_table.setItem(i, 1, QTableWidgetItem(scrap['profile_type']))
            self.scrap_table.setItem(i, 2, QTableWidgetItem(f"{scrap['length']:,.0f}"))
            self.scrap_table.setItem(i, 3, QTableWidgetItem("أقل من 500مم"))

        # Reusable offcuts table
        reusable_items = self.current_plan.reusable_offcuts
        self.reusable_table.setRowCount(len(reusable_items))
        for i, off in enumerate(reusable_items):
            self.reusable_table.setItem(i, 0, QTableWidgetItem(off['material_name']))
            self.reusable_table.setItem(i, 1, QTableWidgetItem(off['profile_type']))
            self.reusable_table.setItem(i, 2, QTableWidgetItem(f"{off['length']:,.0f}"))
            status = QTableWidgetItem("✅ سيتم حفظها تلقائياً")
            status.setBackground(QBrush(QColor("#d5f5e3")))
            self.reusable_table.setItem(i, 3, status)

    def update_details_table(self):
        if not self.current_plan:
            return

        rows = []
        for sp in self.current_plan.stock_pieces:
            if not sp.used:
                continue
            source_type = "♻️ فضلة" if sp.is_offcut else "📦 خام"
            pieces_names = ", ".join([c['name'] for c in sp.cuts])
            rows.append([
                sp.material_name, sp.profile_type,
                f"{sp.length:,.0f}", f"{sp.length - sp.remaining:,.0f}",
                f"{sp.remaining:,.0f}", source_type
            ])

        self.details_table.setRowCount(len(rows))
        for i, row in enumerate(rows):
            for j, val in enumerate(row):
                item = QTableWidgetItem(str(val))
                if j == 5 and "فضلة" in str(val):
                    item.setBackground(QBrush(QColor("#d5f5e3")))
                self.details_table.setItem(i, j, item)

    def toggle_view(self):
        self.detailed_view = not self.detailed_view
        if self.detailed_view:
            self.details_widget.show()
            self.splitter.setSizes([500, 500])
        else:
            self.details_widget.hide()
            self.splitter.setSizes([900, 0])

    def print_report(self):
        try:
            printer = QPrinter(QPrinter.PrinterMode.HighResolution)
            dialog = QPrintDialog(printer, self)

            if dialog.exec() == QPrintDialog.DialogCode.Accepted:
                painter = QPainter(printer)

                # Print header
                painter.setFont(QFont("Arial", 16, QFont.Weight.Bold))
                painter.drawText(printer.pageRect(), Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignHCenter,
                               "تقرير أمر القص - Cutting Report")

                painter.setFont(QFont("Arial", 10))
                painter.drawText(printer.pageRect().adjusted(0, 40, 0, 0), Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignRight,
                               f"التاريخ: {datetime.now().strftime('%Y-%m-%d %H:%M')}")

                # Print statistics
                y = 80
                painter.setFont(QFont("Arial", 12, QFont.Weight.Bold))
                painter.drawText(50, y, "الإحصائيات:")
                y += 30

                painter.setFont(QFont("Arial", 10))
                for key, label in [("total_pieces", "إجمالي القطع"), ("efficiency", "الكفاءة"), ("waste_percentage", "نسبة الهدر")]:
                    painter.drawText(50, y, f"{label}: {self.stats_labels[key].text()}")
                    y += 25

                painter.end()
                QMessageBox.information(self, "نجاح", "تم إرسال التقرير إلى الطابعة بنجاح!")
        except Exception as e:
            QMessageBox.critical(self, "خطأ في الطباعة", f"حدث خطأ أثناء الطباعة:\n{str(e)}")

    def confirm_operation(self):
        if not self.current_operation_id:
            return

        reply = QMessageBox.question(
            self, "تأكيد العملية",
            "هل أنت متأكد من تنفيذ القص وتحديث المخزن؟\n\n"
            "⚠️ هذا الإجراء لا يمكن التراجع عنه!\n\n"
            "سيتم:\n"
            "• خصم المواد الخام المستهلكة\n"
            "• تحويل الفضلات المستخدمة إلى 'تم الاستخدام'\n"
            "• حفظ الفضلات الصالحة الجديدة في المخزن",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            try:
                self.db.confirm_operation(self.current_operation_id)
                self.confirm_btn.setEnabled(False)
                self.cancel_btn.setEnabled(False)
                self.print_btn.setEnabled(True)
                self.status_label.setText(
                    f"✅ تم تأكيد العملية #{self.current_operation_id} وتحديث المخزن بنجاح!"
                )
                self.status_label.setStyleSheet("""
                    QLabel {
                        padding: 10px;
                        background: #d5f5e3;
                        border-radius: 5px;
                        color: #155724;
                        font-weight: bold;
                        font-size: 13px;
                    }
                """)
                self.operation_confirmed.emit()
                QMessageBox.information(self, "نجاح", 
                    "✅ تم تنفيذ القص وتحديث المخزن بنجاح!\n\n"
                    "• تم خصم المواد الخام\n"
                    "• تم تحديث حالة الفضلات\n"
                    "• تم إضافة الفضلات الصالحة الجديدة")
            except Exception as e:
                QMessageBox.critical(self, "خطأ", f"حدث خطأ أثناء التأكيد:\n{str(e)}")

    def cancel_operation(self):
        if not self.current_operation_id:
            return

        reply = QMessageBox.question(
            self, "إلغاء العملية",
            "هل أنت متأكد من إلغاء العملية؟\n"
            "لن يتم تغيير أي شيء في المخزن.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            try:
                self.db.cancel_operation(self.current_operation_id)
                self.confirm_btn.setEnabled(False)
                self.cancel_btn.setEnabled(False)
                self.print_btn.setEnabled(False)
                self.status_label.setText("❌ تم إلغاء العملية - المخزن لم يتأثر")
                self.status_label.setStyleSheet("""
                    QLabel {
                        padding: 10px;
                        background: #f8d7da;
                        border-radius: 5px;
                        color: #721c24;
                        font-weight: bold;
                        font-size: 13px;
                    }
                """)
                self.operation_cancelled.emit()

                self.current_plan = None
                self.visual_data = []
                while self.chart_layout.count():
                    item = self.chart_layout.takeAt(0)
                    if item.widget():
                        item.widget().deleteLater()
                self.details_table.setRowCount(0)
                self.scrap_table.setRowCount(0)
                self.reusable_table.setRowCount(0)
                for label in self.stats_labels.values():
                    label.setText("0")
            except Exception as e:
                QMessageBox.critical(self, "خطأ", f"حدث خطأ أثناء الإلغاء:\n{str(e)}")
