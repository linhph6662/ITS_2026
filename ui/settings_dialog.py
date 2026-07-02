from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
                             QLineEdit, QDoubleSpinBox, QSpinBox, 
                             QPushButton, QFileDialog, QFormLayout)

class SettingsDialog(QDialog):
    def __init__(self, config, parent=None):
        super().__init__(parent)
        self.config = config
        self.setWindowTitle("System Settings")
        self.setMinimumSize(400, 360)
        self.init_ui()
        self.apply_theme()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        form_layout = QFormLayout()
        form_layout.setSpacing(12)

        # Video Source
        self.source_input = QLineEdit()
        self.source_input.setText(str(self.config.settings["video"]["source"]))
        source_layout = QHBoxLayout()
        source_layout.addWidget(self.source_input)
        
        file_btn = QPushButton("Browse")
        file_btn.clicked.connect(self.browse_file)
        source_layout.addWidget(file_btn)
        form_layout.addRow("Video Source:", source_layout)

        # Confidence Threshold
        self.conf_spin = QDoubleSpinBox()
        self.conf_spin.setRange(0.1, 1.0)
        self.conf_spin.setSingleStep(0.05)
        self.conf_spin.setValue(self.config.settings["detection"]["confidence_threshold"])
        form_layout.addRow("Detection Confidence:", self.conf_spin)

        # Calibration Line A (Y)
        self.line_a_spin = QSpinBox()
        self.line_a_spin.setRange(50, 2000)
        self.line_a_spin.setValue(self.config.settings["speed_estimation"]["line_a_y"])
        form_layout.addRow("Line A Y-Coord (px):", self.line_a_spin)

        # Calibration Line B (Y)
        self.line_b_spin = QSpinBox()
        self.line_b_spin.setRange(50, 2000)
        self.line_b_spin.setValue(self.config.settings["speed_estimation"]["line_b_y"])
        form_layout.addRow("Line B Y-Coord (px):", self.line_b_spin)

        # Distance between lines
        self.dist_spin = QDoubleSpinBox()
        self.dist_spin.setRange(1.0, 1000.0)
        self.dist_spin.setValue(self.config.settings["speed_estimation"]["line_distance_meters"])
        form_layout.addRow("Line Distance (meters):", self.dist_spin)

        layout.addLayout(form_layout)

        # Buttons
        btn_layout = QHBoxLayout()
        save_btn = QPushButton("Save")
        save_btn.setObjectName("saveBtn")
        save_btn.clicked.connect(self.save_settings)
        
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)

        btn_layout.addStretch()
        btn_layout.addWidget(cancel_btn)
        btn_layout.addWidget(save_btn)
        layout.addLayout(btn_layout)

    def browse_file(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Open Video File", "", "Videos (*.mp4 *.avi *.mkv)")
        if file_path:
            self.source_input.setText(file_path)

    def save_settings(self):
        # Update config settings
        self.config.settings["video"]["source"] = self.source_input.text()
        self.config.settings["detection"]["confidence_threshold"] = self.conf_spin.value()
        self.config.settings["speed_estimation"]["line_a_y"] = self.line_a_spin.value()
        self.config.settings["speed_estimation"]["line_b_y"] = self.line_b_spin.value()
        self.config.settings["speed_estimation"]["line_distance_meters"] = self.dist_spin.value()
        
        # Save to file
        self.config.save()
        self.accept()

    def apply_theme(self):
        self.setStyleSheet("""
            QDialog {
                background-color: #121212;
                color: #e0e0e0;
            }
            QLabel {
                color: #b0b0b0;
                font-size: 13px;
                font-weight: 500;
            }
            QLineEdit, QDoubleSpinBox, QSpinBox {
                background-color: #1e1e1e;
                color: #ffffff;
                border: 1px solid #333333;
                border-radius: 6px;
                padding: 8px;
                font-size: 13px;
            }
            QLineEdit:focus, QDoubleSpinBox:focus, QSpinBox:focus {
                border: 1px solid #00adb5;
            }
            QPushButton {
                background-color: #1e1e1e;
                color: #ffffff;
                border: 1px solid #333333;
                border-radius: 6px;
                padding: 8px 16px;
                font-size: 13px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #2a2a2a;
                border: 1px solid #444444;
            }
            QPushButton#saveBtn {
                background-color: #00adb5;
                color: #121212;
                border: none;
            }
            QPushButton#saveBtn:hover {
                background-color: #008f95;
            }
        """)
