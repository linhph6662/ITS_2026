import os
import sys
import cv2
import time
from PySide6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                             QLabel, QPushButton, QTableWidget, QTableWidgetItem, 
                             QHeaderView, QFileDialog, QFrame, QSizePolicy, 
                             QSizeGrip, QMessageBox)
from PySide6.QtGui import QImage, QPixmap, QColor, QFont, QPainter, QBrush, QPen
from PySide6.QtCore import Qt, Slot, QSize

from core.video_processor import VideoProcessor
from ui.settings_dialog import SettingsDialog
from ui.history_window import HistoryWindow

class TitleBar(QWidget):
    """Custom premium Dark Theme Title Bar that enables window dragging."""
    def __init__(self, parent):
        super().__init__(parent)
        self.parent = parent
        self.setFixedHeight(40)
        self.drag_position = None
        self.init_ui()

    def init_ui(self):
        self.setStyleSheet("""
            QWidget {
                background-color: #1a1a1a;
                border-top-left-radius: 8px;
                border-top-right-radius: 8px;
            }
            QLabel {
                color: #ffffff;
                font-weight: bold;
                font-size: 13px;
                font-family: 'Segoe UI', Arial, sans-serif;
                padding-left: 15px;
                background-color: transparent;
            }
            QPushButton {
                background-color: transparent;
                border: none;
                color: #a0a0a0;
                font-size: 12px;
                width: 45px;
                height: 40px;
                margin: 0px;
            }
            QPushButton:hover {
                background-color: #2b2b2b;
                color: #ffffff;
            }
            QPushButton#closeBtn:hover {
                background-color: #ef4444;
                color: #ffffff;
            }
        """)
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # Logo Icon and Text
        self.title_label = QLabel(" Highway Vehicle Monitoring System")
        layout.addWidget(self.title_label)
        layout.addStretch()
        
        # Minimize, Maximize, Close Buttons
        self.min_btn = QPushButton("━")
        self.min_btn.clicked.connect(self.parent.showMinimized)
        layout.addWidget(self.min_btn)
        
        self.max_btn = QPushButton("▢")
        self.max_btn.clicked.connect(self.toggle_maximized)
        layout.addWidget(self.max_btn)
        
        self.close_btn = QPushButton("✕")
        self.close_btn.setObjectName("closeBtn")
        self.close_btn.clicked.connect(self.parent.close)
        layout.addWidget(self.close_btn)

    def toggle_maximized(self):
        if self.parent.isMaximized():
            self.parent.showNormal()
            self.max_btn.setText("▢")
        else:
            self.parent.showMaximized()
            self.max_btn.setText("❐")

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.drag_position = event.globalPosition().toPoint() - self.parent.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event):
        if self.drag_position is not None and event.buttons() == Qt.MouseButton.LeftButton:
            self.parent.move(event.globalPosition().toPoint() - self.drag_position)
            event.accept()

    def mouseReleaseEvent(self, event):
        self.drag_position = None


class StatCard(QFrame):
    """Custom Dashboard Card showing a metric name and dynamic value."""
    def __init__(self, title, value, color_hex="#00adb5", parent=None):
        super().__init__(parent)
        self.setObjectName("statCard")
        self.setFrameShape(QFrame.Shape.StyledPanel)
        self.color_hex = color_hex
        self.init_ui(title, value)

    def init_ui(self, title, value):
        self.setStyleSheet(f"""
            QFrame#statCard {{
                background-color: #1e1e1e;
                border-top: 3px solid {self.color_hex};
                border-radius: 8px;
            }}
        """)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 12, 15, 12)
        layout.setSpacing(4)
        
        self.title_lbl = QLabel(title)
        self.title_lbl.setStyleSheet("color: #888888; font-size: 11px; font-weight: bold; text-transform: uppercase; letter-spacing: 1px;")
        
        self.val_lbl = QLabel(value)
        self.val_lbl.setStyleSheet(f"color: #ffffff; font-size: 24px; font-weight: bold; font-family: 'Consolas', monospace;")
        
        layout.addWidget(self.title_lbl)
        layout.addWidget(self.val_lbl)

    def set_value(self, val):
        self.val_lbl.setText(str(val))


class MainWindow(QMainWindow):
    def __init__(self, config, db_manager):
        super().__init__()
        self.config = config
        self.db_manager = db_manager
        
        # Transparent background for custom title bar rounding
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowSystemMenuHint)
        self.setMinimumSize(1200, 800)
        
        self.video_processor = None
        self.history_window = None
        self.selected_video_path = str(self.config.settings["video"]["source"])
        
        self.create_mock_images()
        self.init_ui()
        self.load_initial_history()

    def create_mock_images(self):
        """Creates dummy crop thumbnail for rendering rows inside QTableWidget."""
        os.makedirs("history/images", exist_ok=True)
        path = "history/images/mock_car.jpg"
        if not os.path.exists(path):
            img = QImage(80, 50, QImage.Format.Format_RGB32)
            img.fill(QColor("#1a1a1a"))
            painter = QPainter(img)
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)
            # Body
            painter.setBrush(QBrush(QColor("#00adb5")))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawRect(15, 20, 50, 15)
            # Cabin
            painter.setBrush(QBrush(QColor("#e0e0e0")))
            painter.drawRect(28, 10, 24, 10)
            # Wheels
            painter.setBrush(QBrush(QColor("#000000")))
            painter.drawEllipse(22, 32, 10, 10)
            painter.drawEllipse(48, 32, 10, 10)
            painter.end()
            img.save(path)

    def init_ui(self):
        # Outer base container to implement borders and rounded corners
        self.container = QWidget(self)
        self.container.setObjectName("mainContainer")
        self.setCentralWidget(self.container)
        
        # Global vertical layout
        outer_layout = QVBoxLayout(self.container)
        outer_layout.setContentsMargins(0, 0, 0, 0)
        outer_layout.setSpacing(0)
        
        # Custom Title Bar
        self.title_bar = TitleBar(self)
        outer_layout.addWidget(self.title_bar)

        # Body Widget
        body_widget = QWidget()
        body_layout = QHBoxLayout(body_widget)
        body_layout.setContentsMargins(15, 15, 15, 15)
        body_layout.setSpacing(15)

        # LEFT COLUMN (70%): Dashboard + Video screen
        left_layout = QVBoxLayout()
        left_layout.setSpacing(15)
        
        # Dashboard cards
        self.dash_layout = QHBoxLayout()
        self.dash_layout.setSpacing(10)
        
        self.card_total = StatCard("Total Vehicles", "0", color_hex="#00adb5")
        self.card_tracking = StatCard("Tracking Active", "0", color_hex="#3b82f6")
        self.card_avg_speed = StatCard("Avg Speed", "0.0 km/h", color_hex="#10b981")
        self.card_max_speed = StatCard("Max Speed", "0.0 km/h", color_hex="#ef4444")
        self.card_min_speed = StatCard("Min Speed", "0.0 km/h", color_hex="#8b5cf6")
        
        self.dash_layout.addWidget(self.card_total)
        self.dash_layout.addWidget(self.card_tracking)
        self.dash_layout.addWidget(self.card_avg_speed)
        self.dash_layout.addWidget(self.card_max_speed)
        self.dash_layout.addWidget(self.card_min_speed)
        left_layout.addLayout(self.dash_layout)

        # Video Player Label
        self.video_label = QLabel("Video Feed Display Screen\nSelect video source and click 'Start'")
        self.video_label.setObjectName("videoScreen")
        self.video_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.video_label.setMinimumSize(640, 360)
        self.video_label.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.video_label.setScaledContents(True)
        left_layout.addWidget(self.video_label)
        
        body_layout.addLayout(left_layout, stretch=7)

        # RIGHT COLUMN (30%): Video Info + Controls panel
        right_panel = QVBoxLayout()
        right_panel.setSpacing(15)
        
        # Video Info Panel
        info_frame = QFrame()
        info_frame.setObjectName("panelFrame")
        info_layout = QVBoxLayout(info_frame)
        info_layout.setContentsMargins(15, 15, 15, 15)
        
        info_title = QLabel("Video Information")
        info_title.setObjectName("sectionTitle")
        info_layout.addWidget(info_title)
        
        self.lbl_vname = QLabel("Video Name: N/A")
        self.lbl_vfps = QLabel("FPS: N/A")
        self.lbl_vres = QLabel("Resolution: N/A")
        self.lbl_vduration = QLabel("Duration: N/A")
        
        for lbl in [self.lbl_vname, self.lbl_vfps, self.lbl_vres, self.lbl_vduration]:
            lbl.setObjectName("infoLabel")
            info_layout.addWidget(lbl)
            
        right_panel.addWidget(info_frame)

        # Controls Panel
        ctrl_frame = QFrame()
        ctrl_frame.setObjectName("panelFrame")
        ctrl_layout = QVBoxLayout(ctrl_frame)
        ctrl_layout.setContentsMargins(15, 15, 15, 15)
        ctrl_layout.setSpacing(10)
        
        ctrl_title = QLabel("Controls")
        ctrl_title.setObjectName("sectionTitle")
        ctrl_layout.addWidget(ctrl_title)

        # Video Choose
        self.btn_select = QPushButton("Chọn Video")
        self.btn_select.setObjectName("actionBtn")
        self.btn_select.clicked.connect(self.select_video)
        ctrl_layout.addWidget(self.btn_select)

        # Start / Pause Buttons row
        row1_layout = QHBoxLayout()
        self.btn_start = QPushButton("Start")
        self.btn_start.setObjectName("startBtn")
        self.btn_start.clicked.connect(self.start_processing)
        
        self.btn_pause = QPushButton("Pause")
        self.btn_pause.setObjectName("pauseBtn")
        self.btn_pause.setEnabled(False)
        self.btn_pause.clicked.connect(self.pause_processing)
        
        row1_layout.addWidget(self.btn_start)
        row1_layout.addWidget(self.btn_pause)
        ctrl_layout.addLayout(row1_layout)

        # Resume / Stop Buttons row
        row2_layout = QHBoxLayout()
        self.btn_resume = QPushButton("Resume")
        self.btn_resume.setObjectName("resumeBtn")
        self.btn_resume.setEnabled(False)
        self.btn_resume.clicked.connect(self.resume_processing)
        
        self.btn_stop = QPushButton("Stop")
        self.btn_stop.setObjectName("stopBtn")
        self.btn_stop.setEnabled(False)
        self.btn_stop.clicked.connect(self.stop_processing)
        
        row2_layout.addWidget(self.btn_resume)
        row2_layout.addWidget(self.btn_stop)
        ctrl_layout.addLayout(row2_layout)

        # Reset / Export Buttons row
        row3_layout = QHBoxLayout()
        self.btn_reset = QPushButton("Reset")
        self.btn_reset.setObjectName("resetBtn")
        self.btn_reset.clicked.connect(self.reset_system)
        
        self.btn_export = QPushButton("Export Report")
        self.btn_export.setObjectName("exportBtn")
        self.btn_export.clicked.connect(self.export_report)
        
        row3_layout.addWidget(self.btn_reset)
        row3_layout.addWidget(self.btn_export)
        ctrl_layout.addLayout(row3_layout)
        
        right_panel.addWidget(ctrl_frame)
        
        # Settings trigger
        self.btn_settings = QPushButton("Settings Dialog")
        self.btn_settings.setObjectName("settingsBtn")
        self.btn_settings.clicked.connect(self.open_settings)
        right_panel.addWidget(self.btn_settings)

        body_layout.addLayout(right_panel, stretch=3)
        outer_layout.addWidget(body_widget, stretch=3)

        # Bottom Area: History Table Log
        table_frame = QFrame()
        table_frame.setObjectName("tablePanel")
        table_layout = QVBoxLayout(table_frame)
        table_layout.setContentsMargins(15, 5, 15, 10)
        
        table_lbl = QLabel("History Detection Logs")
        table_lbl.setObjectName("sectionTitle")
        table_layout.addWidget(table_lbl)
        
        self.table = QTableWidget()
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels(["ID", "Vehicle Image", "Speed", "Time", "Video Name", "Action"])
        self.table.verticalHeader().setDefaultSectionSize(45)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(5, QHeaderView.ResizeMode.ResizeToContents)
        table_layout.addWidget(self.table)
        
        outer_layout.addWidget(table_frame, stretch=2)

        # Apply Stylesheet
        self.apply_theme()

    def apply_theme(self):
        self.setStyleSheet("""
            QWidget#mainContainer {
                background-color: #121212;
                border: 1px solid #2a2a2a;
                border-radius: 8px;
            }
            QLabel#videoScreen {
                background-color: #000000;
                color: #888888;
                border: 1px solid #2a2a2a;
                border-radius: 6px;
                font-size: 14px;
                font-weight: 500;
            }
            QFrame#panelFrame {
                background-color: #1e1e1e;
                border: 1px solid #2a2a2a;
                border-radius: 8px;
            }
            QFrame#tablePanel {
                background-color: #121212;
                border-top: 1px solid #2a2a2a;
            }
            QLabel#sectionTitle {
                color: #00adb5;
                font-size: 13px;
                font-weight: bold;
                text-transform: uppercase;
                margin-bottom: 5px;
                letter-spacing: 1px;
            }
            QLabel#infoLabel {
                color: #e0e0e0;
                font-size: 12px;
                padding: 4px 0px;
                font-family: 'Segoe UI', Arial, sans-serif;
            }
            QPushButton {
                background-color: #2b2b2b;
                color: #e0e0e0;
                border: 1px solid #3a3a3a;
                border-radius: 6px;
                padding: 8px 12px;
                font-size: 12px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #3b3b3b;
                border-color: #4a4a4a;
            }
            QPushButton:disabled {
                background-color: #181818;
                color: #555555;
                border-color: #222222;
            }
            QPushButton#actionBtn {
                background-color: #3b82f6;
                color: #ffffff;
                border: none;
            }
            QPushButton#actionBtn:hover {
                background-color: #2563eb;
            }
            QPushButton#startBtn {
                background-color: #10b981;
                color: #ffffff;
                border: none;
            }
            QPushButton#startBtn:hover {
                background-color: #059669;
            }
            QPushButton#stopBtn {
                background-color: #ef4444;
                color: #ffffff;
                border: none;
            }
            QPushButton#stopBtn:hover {
                background-color: #dc2626;
            }
            QPushButton#settingsBtn {
                background-color: transparent;
                border: 1px solid #333333;
                color: #a0a0a0;
            }
            QPushButton#settingsBtn:hover {
                border-color: #00adb5;
                color: #ffffff;
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

    @Slot()
    def select_video(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Chọn Video Source", "", "Video Files (*.mp4 *.avi *.mkv *.mov)")
        if file_path:
            self.selected_video_path = file_path
            # Parse video source details directly or instantiate a temp reader
            self.lbl_vname.setText(f"Video Name: {os.path.basename(file_path)}")
            self.status_bar_msg(f"Source selected: {file_path}")
            
            # Retrieve initial video details
            cap = cv2.VideoCapture(file_path)
            if cap.isOpened():
                fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
                frame_count = cap.get(cv2.CAP_PROP_FRAME_COUNT)
                width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
                height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
                duration_sec = frame_count / fps if fps > 0 else 0
                
                self.lbl_vfps.setText(f"FPS: {fps:.1f}")
                self.lbl_vres.setText(f"Resolution: {width}x{height}")
                h = int(duration_sec // 3600)
                m = int((duration_sec % 3600) // 60)
                s = int(duration_sec % 60)
                self.lbl_vduration.setText(f"Duration: {h:02d}:{m:02d}:{s:02d}")
                cap.release()

    @Slot()
    def start_processing(self):
        if self.video_processor and self.video_processor.isRunning():
            return
            
        self.video_processor = VideoProcessor(
            source=self.selected_video_path,
            detector_model=self.config.settings["detection"]["model_path"],
            line_a_y=self.config.settings["speed_estimation"]["line_a_y"],
            line_b_y=self.config.settings["speed_estimation"]["line_b_y"],
            distance=self.config.settings["speed_estimation"]["line_distance_meters"],
            db_manager=self.db_manager
        )
        
        # Connect signals
        self.video_processor.frame_processed.connect(self.update_video_frame)
        self.video_processor.vehicle_detected.connect(self.on_vehicle_detected)
        self.video_processor.statistics_updated.connect(self.update_stats)
        self.video_processor.metadata_retrieved.connect(self.update_metadata)
        self.video_processor.processing_error.connect(self.on_processing_error)
        
        self.video_processor.start()
        
        self.btn_start.setEnabled(False)
        self.btn_pause.setEnabled(True)
        self.btn_resume.setEnabled(False)
        self.btn_stop.setEnabled(True)
        self.status_bar_msg("Video processing started.")

    @Slot()
    def pause_processing(self):
        if self.video_processor and self.video_processor.isRunning():
            self.video_processor.pause()
            self.btn_pause.setEnabled(False)
            self.btn_resume.setEnabled(True)
            self.status_bar_msg("Video processing paused.")

    @Slot()
    def resume_processing(self):
        if self.video_processor and self.video_processor.isRunning():
            self.video_processor.resume()
            self.btn_pause.setEnabled(True)
            self.btn_resume.setEnabled(False)
            self.status_bar_msg("Video processing resumed.")

    @Slot()
    def stop_processing(self):
        if self.video_processor:
            self.video_processor.stop()
            self.video_processor = None
            
        self.btn_start.setEnabled(True)
        self.btn_pause.setEnabled(False)
        self.btn_resume.setEnabled(False)
        self.btn_stop.setEnabled(False)
        self.video_label.setText("Video Feed Display Screen\nSelect video source and click 'Start'")
        self.card_tracking.set_value(0)
        self.status_bar_msg("Video processing stopped.")

    @Slot()
    def reset_system(self):
        if self.video_processor:
            self.video_processor.reset_stats()
        
        # Clear stats cards
        self.card_total.set_value("0")
        self.card_tracking.set_value("0")
        self.card_avg_speed.set_value("0.0 km/h")
        self.card_max_speed.set_value("0.0 km/h")
        self.card_min_speed.set_value("0.0 km/h")
        
        # Reset table
        self.table.setRowCount(0)
        self.status_bar_msg("Statistics and log table cleared.")

    @Slot()
    def export_report(self):
        # Create reports folder if not exists
        os.makedirs("reports", exist_ok=True)
        default_path = os.path.abspath("reports/traffic_report.csv")
        
        file_path, selected_filter = QFileDialog.getSaveFileName(
            self, 
            "Export Report Log", 
            default_path, 
            "CSV Files (*.csv);;Excel Files (*.xlsx);;PDF Files (*.pdf)"
        )
        
        if not file_path:
            return

        try:
            records = self.db_manager.get_all()
            if not records:
                QMessageBox.warning(self, "Export Warning", "No records found in database to export.")
                return
                
            from utils.exporter import export_to_csv, export_to_excel, export_to_pdf
            success = False
            
            if file_path.endswith(".csv"):
                success = export_to_csv(records, file_path)
            elif file_path.endswith(".xlsx"):
                success = export_to_excel(records, file_path)
            elif file_path.endswith(".pdf"):
                success = export_to_pdf(records, file_path)
                
            if success:
                QMessageBox.information(
                    self, 
                    "Export Successful", 
                    f"Successfully exported {len(records)} records to:\n{os.path.basename(file_path)}\n\nSaved under reports folder."
                )
            else:
                QMessageBox.critical(self, "Export Failed", "An error occurred while compiling the report file.")
        except Exception as e:
            QMessageBox.critical(self, "Export Error", f"Failed to execute export: {e}")

    @Slot(object)
    def update_video_frame(self, frame):
        if frame is None:
            return
        try:
            h, w, ch = frame.shape
            bytes_per_line = ch * w
            rgb_image = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            qt_image = QImage(rgb_image.data, w, h, bytes_per_line, QImage.Format.Format_RGB888).copy()
            self.video_label.setPixmap(QPixmap.fromImage(qt_image))
        except Exception as e:
            print(f"Error rendering video frame: {e}")

    @Slot(dict)
    def on_vehicle_detected(self, vehicle_data):
        # 1. Insert into SQLite traffic.db
        try:
            import datetime
            dt_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            self.db_manager.insert(
                vehicle_id=vehicle_data.get("vehicle_id"),
                image_path=vehicle_data.get("image_path"),
                speed=vehicle_data.get("speed"),
                datetime_str=dt_str,
                video_name=vehicle_data.get("video_name", "Recorded Video")
            )
        except Exception as e:
            print(f"Database insertion failed: {e}")
            
        # 2. Insert into Table View
        self.insert_history_row(vehicle_data)

    def insert_history_row(self, data):
        self.table.insertRow(0)
        
        # Col 0: ID
        id_item = QTableWidgetItem(str(data.get("vehicle_id", "")))
        id_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        self.table.setItem(0, 0, id_item)
        
        # Col 1: Vehicle Image
        img_label = QLabel()
        img_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        img_label.setStyleSheet("background: transparent;")
        pixmap = QPixmap("history/images/mock_car.jpg")
        if not pixmap.isNull():
            img_label.setPixmap(pixmap.scaled(70, 38, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
        self.table.setCellWidget(0, 1, img_label)
        
        # Col 2: Speed
        speed = data.get("speed", 0.0)
        speed_item = QTableWidgetItem(f"{speed:.1f} km/h")
        speed_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        if speed > 80.0:
            speed_item.setForeground(QColor("#ef4444"))  # High speed alert
        else:
            speed_item.setForeground(QColor("#10b981"))
        self.table.setItem(0, 2, speed_item)
        
        # Col 3: Time
        time_item = QTableWidgetItem(str(data.get("timestamp", "")))
        time_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        self.table.setItem(0, 3, time_item)
        
        # Col 4: Video Name
        name_item = QTableWidgetItem(str(data.get("video_name", "N/A")))
        name_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        self.table.setItem(0, 4, name_item)
        
        # Col 5: Action Button
        action_btn = QPushButton("Details")
        action_btn.setStyleSheet("""
            QPushButton {
                background-color: #3b82f6;
                color: #ffffff;
                border: none;
                border-radius: 4px;
                padding: 4px 10px;
                font-size: 11px;
            }
            QPushButton:hover {
                background-color: #2563eb;
            }
        """)
        action_btn.clicked.connect(lambda checked=False, d=data: self.show_vehicle_details(d))
        self.table.setCellWidget(0, 5, action_btn)

    def show_vehicle_details(self, data):
        from ui.detail_window import VehicleDetailWindow
        detail_window = VehicleDetailWindow(data, self)
        detail_window.exec()

    @Slot(dict)
    def update_stats(self, stats):
        self.card_total.set_value(stats.get("total_vehicles", 0))
        self.card_tracking.set_value(stats.get("tracking", 0))
        self.card_avg_speed.set_value(f"{stats.get('avg_speed', 0.0):.1f} km/h")
        self.card_max_speed.set_value(f"{stats.get('max_speed', 0.0):.1f} km/h")
        self.card_min_speed.set_value(f"{stats.get('min_speed', 0.0):.1f} km/h")

    @Slot(dict)
    def update_metadata(self, metadata):
        self.lbl_vname.setText(f"Video Name: {metadata.get('name')}")
        self.lbl_vfps.setText(f"FPS: {metadata.get('fps')}")
        self.lbl_vres.setText(f"Resolution: {metadata.get('resolution')}")
        self.lbl_vduration.setText(f"Duration: {metadata.get('duration')}")

    @Slot(str)
    def on_processing_error(self, err_msg):
        self.status_bar_msg(f"Error: {err_msg}")
        self.stop_processing()

    def status_bar_msg(self, msg):
        print(f"[STATUS] {msg}")

    def load_initial_history(self):
        try:
            records = self.db_manager.get_vehicles(limit=50)
            for row in reversed(records):
                mock_data = {
                    "vehicle_id": row.get("vehicle_id", 0),
                    "timestamp": row.get("timestamp", ""),
                    "type": row.get("type", "car"),
                    "speed": row.get("speed", 0.0),
                    "image_path": row.get("image_path", ""),
                    "video_name": "Recorded Video"
                }
                self.insert_history_row(mock_data)
        except Exception as e:
            print(f"Error loading history: {e}")

    def open_settings(self):
        dialog = SettingsDialog(self.config, self)
        dialog.exec()

    def closeEvent(self, event):
        self.stop_processing()
        if self.history_window:
            self.history_window.close()
        event.accept()
