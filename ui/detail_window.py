import os
from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
                             QPushButton, QScrollArea, QSlider, QFormLayout, QFrame)
from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap, QColor

class VehicleDetailWindow(QDialog):
    """Custom Dialog window displaying cropped vehicle image and data with zoom controls."""
    def __init__(self, record_data, parent=None):
        super().__init__(parent)
        self.record_data = record_data
        self.zoom_factor = 1.0
        self.original_pixmap = None
        
        self.setWindowTitle(f"Vehicle Detection Detail - ID {self.record_data.get('vehicle_id')}")
        self.resize(750, 520)
        self.init_ui()
        self.apply_theme()

    def init_ui(self):
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(15, 15, 15, 15)
        main_layout.setSpacing(15)

        # Left Column: Image Viewer Panel
        left_layout = QVBoxLayout()
        left_layout.setSpacing(10)
        
        # Scroll area enclosing image QLabel to enable panning/scrollbars when zoomed
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.scroll_area.setStyleSheet("background-color: #0b0b0b; border: 1px solid #2d2d2d; border-radius: 6px;")
        
        self.image_label = QLabel()
        self.image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.image_label.setStyleSheet("background: transparent;")
        
        # Load cropped image or default mock silhouette
        img_path = self.record_data.get("image_path")
        if img_path and os.path.exists(img_path):
            self.original_pixmap = QPixmap(img_path)
        else:
            self.original_pixmap = QPixmap("history/images/mock_car.jpg")
            
        if self.original_pixmap and not self.original_pixmap.isNull():
            self.image_label.setPixmap(self.original_pixmap)
            self.scroll_area.setWidget(self.image_label)
        else:
            self.image_label.setText("No Image Available")
            self.scroll_area.setWidget(self.image_label)
            
        left_layout.addWidget(self.scroll_area, stretch=9)

        # Zoom Controls
        zoom_layout = QHBoxLayout()
        zoom_layout.setSpacing(8)
        
        zoom_lbl = QLabel("Zoom Factor:")
        zoom_layout.addWidget(zoom_lbl)
        
        self.zoom_slider = QSlider(Qt.Orientation.Horizontal)
        self.zoom_slider.setRange(50, 400)  # 50% to 400%
        self.zoom_slider.setValue(100)
        self.zoom_slider.setSingleStep(10)
        self.zoom_slider.valueChanged.connect(self.on_zoom_changed)
        zoom_layout.addWidget(self.zoom_slider)
        
        self.btn_zoom_out = QPushButton("-")
        self.btn_zoom_out.setFixedWidth(30)
        self.btn_zoom_out.clicked.connect(self.zoom_out)
        zoom_layout.addWidget(self.btn_zoom_out)

        self.btn_zoom_in = QPushButton("+")
        self.btn_zoom_in.setFixedWidth(30)
        self.btn_zoom_in.clicked.connect(self.zoom_in)
        zoom_layout.addWidget(self.btn_zoom_in)
        
        self.lbl_zoom_percent = QLabel("100%")
        self.lbl_zoom_percent.setFixedWidth(40)
        zoom_layout.addWidget(self.lbl_zoom_percent)
        
        left_layout.addLayout(zoom_layout, stretch=1)
        main_layout.addLayout(left_layout, stretch=6)

        # Right Column: Data fields panel
        right_panel = QFrame()
        right_panel.setObjectName("detailsFrame")
        right_panel.setFixedWidth(280)
        
        form_layout = QFormLayout(right_panel)
        form_layout.setContentsMargins(20, 20, 20, 20)
        form_layout.setSpacing(15)
        
        title_lbl = QLabel("Record Details")
        title_lbl.setStyleSheet("font-size: 15px; font-weight: bold; color: #00adb5; margin-bottom: 5px;")
        form_layout.addRow(title_lbl)

        # Info elements
        lbl_db_id = QLabel(str(self.record_data.get("id", "N/A")))
        lbl_veh_id = QLabel(str(self.record_data.get("vehicle_id", "N/A")))
        
        speed_val = self.record_data.get("speed", 0.0)
        lbl_speed = QLabel(f"{speed_val:.1f} km/h")
        if speed_val > 80.0:
            lbl_speed.setStyleSheet("color: #ef4444; font-weight: bold;")
        else:
            lbl_speed.setStyleSheet("color: #10b981; font-weight: bold;")
            
        lbl_datetime = QLabel(str(self.record_data.get("datetime") or self.record_data.get("timestamp", "N/A")))
        lbl_video = QLabel(str(self.record_data.get("video_name", "N/A")))
        
        # Style details
        for lbl in [lbl_db_id, lbl_veh_id, lbl_datetime, lbl_video]:
            lbl.setStyleSheet("color: #ffffff; font-weight: 500;")
            
        form_layout.addRow("Database ID:", lbl_db_id)
        form_layout.addRow("Vehicle ID:", lbl_veh_id)
        form_layout.addRow("Estimated Speed:", lbl_speed)
        form_layout.addRow("DateTime:", lbl_datetime)
        form_layout.addRow("Video Name:", lbl_video)

        # Spacer and Close Button
        spacer = QLabel("")
        spacer.setFixedHeight(20)
        form_layout.addRow(spacer)
        
        btn_close = QPushButton("Close Details")
        btn_close.clicked.connect(self.close)
        form_layout.addRow(btn_close)

        main_layout.addWidget(right_panel, stretch=4)

    def on_zoom_changed(self, value):
        self.zoom_factor = value / 100.0
        self.lbl_zoom_percent.setText(f"{value}%")
        self.update_image_zoom()

    def zoom_in(self):
        val = min(400, self.zoom_slider.value() + 20)
        self.zoom_slider.setValue(val)

    def zoom_out(self):
        val = max(50, self.zoom_slider.value() - 20)
        self.zoom_slider.setValue(val)

    def update_image_zoom(self):
        if self.original_pixmap and not self.original_pixmap.isNull():
            new_w = int(self.original_pixmap.width() * self.zoom_factor)
            new_h = int(self.original_pixmap.height() * self.zoom_factor)
            scaled_pixmap = self.original_pixmap.scaled(
                new_w, new_h, 
                Qt.AspectRatioMode.KeepAspectRatio, 
                Qt.TransformationMode.SmoothTransformation
            )
            self.image_label.setPixmap(scaled_pixmap)

    def apply_theme(self):
        self.setStyleSheet("""
            QDialog {
                background-color: #121212;
                color: #e0e0e0;
            }
            QFrame#detailsFrame {
                background-color: #1e1e1e;
                border: 1px solid #2d2d2d;
                border-radius: 8px;
            }
            QLabel {
                color: #a0a0a0;
                font-size: 13px;
                font-weight: bold;
            }
            QPushButton {
                background-color: #3b82f6;
                color: white;
                border: none;
                border-radius: 6px;
                padding: 10px 18px;
                font-weight: bold;
                font-size: 12px;
            }
            QPushButton:hover {
                background-color: #2563eb;
            }
        """)
