import sys
import os

# Add current directory to python path to resolve core/ui/database modules
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.append(current_dir)

from PySide6.QtWidgets import QApplication
from utils.config import Config
from utils.logger import setup_logger, logger
from database.database import DatabaseManager
from ui.main_window import MainWindow

def main():
    # 1. Setup config
    config_file = os.path.join(current_dir, "config.json")
    config = Config(config_path=config_file)

    # 2. Setup logger
    log_file = os.path.join(current_dir, "app.log")
    setup_logger(name="highway_monitoring", log_file=log_file)
    logger.info("Initializing Highway Vehicle Monitoring System...")

    # 3. Setup database
    db_relative_path = config.settings["database"]["db_path"]
    db_path = os.path.join(current_dir, db_relative_path)
    db_manager = DatabaseManager(db_path=db_path)
    logger.info("Database initialized successfully.")

    # 4. Initialize PyQt Application
    app = QApplication(sys.argv)
    
    # 5. Launch Main Window
    window = MainWindow(config=config, db_manager=db_manager)
    window.show()
    
    logger.info("Main window displayed. Starting application event loop.")
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
