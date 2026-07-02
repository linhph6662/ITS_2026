import os
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QTableWidget, 
                             QTableWidgetItem, QPushButton, QComboBox, 
                             QLabel, QDoubleSpinBox, QHeaderView, QFileDialog, 
                             QLineEdit, QMessageBox, QDateEdit)
from PySide6.QtCore import Qt, Slot, QDate
from PySide6.QtGui import QPixmap, QColor, QIcon

class HistoryWindow(QWidget):
    def __init__(self, db_manager, parent=None):
        super().__init__(parent)
        self.db_manager = db_manager
        self.setWindowTitle("Vehicle Detection History Logs")
        self.resize(1100, 680)
        self.init_ui()
        self.apply_theme()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(15)

        # Title Label
        title_lbl = QLabel("Historical Detection Logs Database")
        title_lbl.setStyleSheet("font-size: 16px; font-weight: bold; color: #00adb5;")
        layout.addWidget(title_lbl)

        # Filters Bar Layout (Horizontal Panel)
        filter_panel = QHBoxLayout()
        filter_panel.setSpacing(10)

        # 1. Search Box
        filter_panel.addWidget(QLabel("Search ID/Video:"))
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search...")
        self.search_input.textChanged.connect(self.load_data)
        filter_panel.addWidget(self.search_input)

        # 2. Date Filters (Start / End Date)
        filter_panel.addWidget(QLabel("Start Date:"))
        self.start_date_edit = QDateEdit()
        self.start_date_edit.setCalendarPopup(True)
        # Set default to 3 months ago
        self.start_date_edit.setDate(QDate.currentDate().addMonths(-3))
        self.start_date_edit.dateChanged.connect(self.load_data)
        filter_panel.addWidget(self.start_date_edit)

        filter_panel.addWidget(QLabel("End Date:"))
        self.end_date_edit = QDateEdit()
        self.end_date_edit.setCalendarPopup(True)
        self.end_date_edit.setDate(QDate.currentDate().addDays(1))
        self.end_date_edit.dateChanged.connect(self.load_data)
        filter_panel.addWidget(self.end_date_edit)

        # 3. Video name Filter
        filter_panel.addWidget(QLabel("Video:"))
        self.video_combo = QComboBox()
        self.video_combo.addItem("All Videos")
        self.video_combo.currentTextChanged.connect(self.load_data)
        filter_panel.addWidget(self.video_combo)

        # 4. Speed Range
        filter_panel.addWidget(QLabel("Min Speed:"))
        self.speed_min = QDoubleSpinBox()
        self.speed_min.setRange(0.0, 250.0)
        self.speed_min.setValue(0.0)
        self.speed_min.valueChanged.connect(self.load_data)
        filter_panel.addWidget(self.speed_min)

        filter_panel.addWidget(QLabel("Max Speed:"))
        self.speed_max = QDoubleSpinBox()
        self.speed_max.setRange(0.0, 250.0)
        self.speed_max.setValue(200.0)
        self.speed_max.valueChanged.connect(self.load_data)
        filter_panel.addWidget(self.speed_max)

        # Reset button
        reset_btn = QPushButton("Reset Filters")
        reset_btn.setObjectName("resetFilterBtn")
        reset_btn.clicked.connect(self.reset_filters)
        filter_panel.addWidget(reset_btn)

        # Export report button
        export_btn = QPushButton("Export Report")
        export_btn.setObjectName("exportReportBtn")
        export_btn.clicked.connect(self.export_report)
        filter_panel.addWidget(export_btn)

        layout.addLayout(filter_panel)

        # Table Setup
        self.table = QTableWidget()
        self.table.setColumnCount(7)
        self.table.setHorizontalHeaderLabels([
            "ID", "Image", "Speed", "DateTime", "Video", "View", "Delete"
        ])
        
        # Sizing headers
        self.table.verticalHeader().setDefaultSectionSize(45)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents) # ID
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents) # Image
        self.table.horizontalHeader().setSectionResizeMode(5, QHeaderView.ResizeMode.ResizeToContents) # View
        self.table.horizontalHeader().setSectionResizeMode(6, QHeaderView.ResizeMode.ResizeToContents) # Delete

        layout.addWidget(self.table)

        # Populates list
        self.populate_video_filter()
        self.load_data()

    def populate_video_filter(self):
        """Extracts unique video names from DB and populates combobox."""
        try:
            records = self.db_manager.get_all()
            unique_videos = set(row.get("video_name") for row in records if row.get("video_name"))
            
            # Temporarily block signals to avoid multiple loads
            self.video_combo.blockSignals(True)
            self.video_combo.clear()
            self.video_combo.addItem("All Videos")
            for video in sorted(unique_videos):
                if video:
                    self.video_combo.addItem(video)
            self.video_combo.blockSignals(False)
        except Exception as e:
            print(f"Error populating video filters: {e}")

    @Slot()
    def load_data(self):
        """Loads records from DB, applies filters, and populates the QTableWidget."""
        try:
            records = self.db_manager.get_all()
        except Exception as e:
            print(f"Error fetching history records: {e}")
            records = []

        # Get active filter parameters
        search_txt = self.search_input.text().lower()
        start_date = self.start_date_edit.date().toPython()
        end_date = self.end_date_edit.date().toPython()
        selected_video = self.video_combo.currentText()
        min_speed = self.speed_min.value()
        max_speed = self.speed_max.value()

        # Apply filters in Python memory (highly responsive)
        filtered_records = []
        for r in records:
            # 1. Search Box
            v_id_str = str(r.get("vehicle_id", ""))
            v_name = r.get("video_name", "").lower()
            if search_txt and (search_txt not in v_id_str and search_txt not in v_name):
                continue
                
            # 2. Date ranges
            dt_str = r.get("datetime", "")
            try:
                # Expecting 'YYYY-MM-DD HH:MM:SS' or 'YYYY-MM-DD'
                r_date_str = dt_str.split(" ")[0]
                year, month, day = map(int, r_date_str.split("-"))
                r_date = QDate(year, month, day).toPython()
                if not (start_date <= r_date <= end_date):
                    continue
            except Exception:
                # If date format is corrupt/unparsable, continue without applying date filter
                pass

            # 3. Video name
            if selected_video != "All Videos" and r.get("video_name") != selected_video:
                continue

            # 4. Speed range
            speed = r.get("speed", 0.0)
            if not (min_speed <= speed <= max_speed):
                continue

            filtered_records.append(r)

        # Render rows
        self.table.setRowCount(0)
        for i, row in enumerate(filtered_records):
            self.table.insertRow(i)

            # Col 0: ID (SQL primary key id)
            primary_id = row.get("id")
            id_item = QTableWidgetItem(str(primary_id))
            id_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.table.setItem(i, 0, id_item)

            # Col 1: Image Thumbnail
            img_label = QLabel()
            img_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            img_label.setStyleSheet("background: transparent;")
            img_path = row.get("image_path")
            
            # Check if file exists, fall back to mock placeholder
            if img_path and os.path.exists(img_path):
                pixmap = QPixmap(img_path)
            else:
                pixmap = QPixmap("history/images/mock_car.jpg")
                
            if not pixmap.isNull():
                img_label.setPixmap(pixmap.scaled(70, 38, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
            self.table.setCellWidget(i, 1, img_label)

            # Col 2: Speed
            speed_val = row.get("speed", 0.0)
            speed_item = QTableWidgetItem(f"{speed_val:.1f} km/h")
            speed_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            if speed_val > 80.0:
                speed_item.setForeground(QColor("#ef4444"))  # High speed warn
            else:
                speed_item.setForeground(QColor("#10b981"))
            self.table.setItem(i, 2, speed_item)

            # Col 3: DateTime
            date_item = QTableWidgetItem(str(row.get("datetime", "")))
            date_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.table.setItem(i, 3, date_item)

            # Col 4: Video source name
            video_item = QTableWidgetItem(str(row.get("video_name", "N/A")))
            video_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.table.setItem(i, 4, video_item)

            # Col 5: View Button
            view_btn = QPushButton("View")
            view_btn.setStyleSheet("""
                QPushButton {
                    background-color: #3b82f6;
                    color: white;
                    border: none;
                    border-radius: 4px;
                    padding: 4px 8px;
                    font-size: 11px;
                }
                QPushButton:hover {
                    background-color: #2563eb;
                }
            """)
            view_btn.clicked.connect(lambda checked=False, r_data=row: self.view_details(r_data))
            self.table.setCellWidget(i, 5, view_btn)

            # Col 6: Delete Button
            del_btn = QPushButton("Delete")
            del_btn.setStyleSheet("""
                QPushButton {
                    background-color: #ef4444;
                    color: white;
                    border: none;
                    border-radius: 4px;
                    padding: 4px 8px;
                    font-size: 11px;
                }
                QPushButton:hover {
                    background-color: #dc2626;
                }
            """)
            del_btn.clicked.connect(lambda checked=False, r_id=primary_id: self.delete_record(r_id))
            self.table.setCellWidget(i, 6, del_btn)

    def reset_filters(self):
        self.search_input.clear()
        self.start_date_edit.setDate(QDate.currentDate().addMonths(-3))
        self.end_date_edit.setDate(QDate.currentDate().addDays(1))
        self.video_combo.setCurrentIndex(0)
        self.speed_min.setValue(0.0)
        self.speed_max.setValue(200.0)
        self.load_data()

    def view_details(self, r_data):
        from ui.detail_window import VehicleDetailWindow
        detail_window = VehicleDetailWindow(r_data, self)
        detail_window.exec()

    def delete_record(self, record_id):
        # Confirm deletion
        confirm = QMessageBox.question(
            self,
            "Delete Record Log?",
            f"Are you sure you want to delete database record ID: {record_id}?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if confirm == QMessageBox.StandardButton.Yes:
            try:
                self.db_manager.delete(record_id)
                self.load_data()  # reload view
            except Exception as e:
                QMessageBox.critical(self, "Deletion Error", f"Failed to delete record: {e}")

    @Slot()
    def export_report(self):
        """Exports the CURRENTLY FILTERED list of vehicle records to CSV/Excel/PDF."""
        os.makedirs("reports", exist_ok=True)
        default_path = os.path.abspath("reports/filtered_traffic_report.csv")
        
        file_path, selected_filter = QFileDialog.getSaveFileName(
            self, 
            "Export Filtered Report Log", 
            default_path, 
            "CSV Files (*.csv);;Excel Files (*.xlsx);;PDF Files (*.pdf)"
        )
        
        if not file_path:
            return

        try:
            records = self.db_manager.get_all()
            search_txt = self.search_input.text().lower()
            start_date = self.start_date_edit.date().toPython()
            end_date = self.end_date_edit.date().toPython()
            selected_video = self.video_combo.currentText()
            min_speed = self.speed_min.value()
            max_speed = self.speed_max.value()

            # Filter data
            filtered_records = []
            for r in records:
                v_id_str = str(r.get("vehicle_id", ""))
                v_name = r.get("video_name", "").lower()
                if search_txt and (search_txt not in v_id_str and search_txt not in v_name):
                    continue
                dt_str = r.get("datetime", "")
                try:
                    r_date_str = dt_str.split(" ")[0]
                    year, month, day = map(int, r_date_str.split("-"))
                    r_date = QDate(year, month, day).toPython()
                    if not (start_date <= r_date <= end_date):
                        continue
                except Exception:
                    pass
                if selected_video != "All Videos" and r.get("video_name") != selected_video:
                    continue
                speed = r.get("speed", 0.0)
                if not (min_speed <= speed <= max_speed):
                    continue
                filtered_records.append(r)

            if not filtered_records:
                QMessageBox.warning(self, "Export Warning", "No records match current filter criteria to export.")
                return

            from utils.exporter import export_to_csv, export_to_excel, export_to_pdf
            success = False
            
            if file_path.endswith(".csv"):
                success = export_to_csv(filtered_records, file_path)
            elif file_path.endswith(".xlsx"):
                success = export_to_excel(filtered_records, file_path)
            elif file_path.endswith(".pdf"):
                success = export_to_pdf(filtered_records, file_path)
                
            if success:
                QMessageBox.information(
                    self, 
                    "Export Successful", 
                    f"Successfully exported {len(filtered_records)} records to:\n{os.path.basename(file_path)}\n\nSaved under reports folder."
                )
            else:
                QMessageBox.critical(self, "Export Failed", "An error occurred while compiling the report file.")
        except Exception as e:
            QMessageBox.critical(self, "Export Error", f"Failed to execute export: {e}")

    def apply_theme(self):
        self.setStyleSheet("""
            QWidget {
                background-color: #121212;
                color: #e0e0e0;
            }
            QLabel {
                color: #a0a0a0;
                font-size: 12px;
                font-weight: bold;
            }
            QLineEdit, QDateEdit, QDoubleSpinBox, QComboBox {
                background-color: #1e1e1e;
                color: #ffffff;
                border: 1px solid #333333;
                border-radius: 6px;
                padding: 6px;
                font-size: 12px;
            }
            QComboBox::drop-down {
                border: none;
            }
            QPushButton {
                background-color: #1e1e1e;
                color: #ffffff;
                border: 1px solid #333333;
                border-radius: 6px;
                padding: 6px 12px;
                font-size: 12px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #2a2a2a;
            }
            QPushButton#resetFilterBtn {
                background-color: #2b2b2b;
                border-color: #555555;
            }
            QPushButton#resetFilterBtn:hover {
                background-color: #3b3b3b;
            }
            QPushButton#exportReportBtn {
                background-color: #00adb5;
                color: #121212;
                border: none;
            }
            QPushButton#exportReportBtn:hover {
                background-color: #008f95;
            }
            QTableWidget {
                background-color: #1e1e1e;
                alternate-background-color: #181818;
                gridline-color: #2a2a2a;
                color: #ffffff;
                border: 1px solid #2a2a2a;
                border-radius: 6px;
            }
            QHeaderView::section {
                background-color: #1a1a1a;
                color: #a0a0a0;
                padding: 8px;
                border: 1px solid #2a2a2a;
                font-weight: bold;
                font-size: 11px;
            }
            QTableWidget::item {
                padding: 4px;
            }
        """)
