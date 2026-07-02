import json
import os

class Config:
    def __init__(self, config_path="config.json"):
        self.config_path = config_path
        self.settings = self.get_default_settings()
        self.load()

    def get_default_settings(self):
        """Returns the default configuration settings."""
        return {
            "video": {
                "source": "0",  # Camera index or path to video file
                "resolution": [1280, 720],
                "fps": 30
            },
            "detection": {
                "confidence_threshold": 0.5,
                "nms_threshold": 0.4,
                "model_path": "models/yolov8n.pt",
                "classes": [2, 3, 5, 7]  # car, motorbike, bus, truck (COCO)
            },
            "speed_estimation": {
                "line_a_y": 300,
                "line_b_y": 500,
                "line_distance_meters": 20.0
            },
            "database": {
                "db_path": "database/traffic.db"
            }
        }

    def load(self):
        """Loads configuration from JSON file."""
        if os.path.exists(self.config_path):
            try:
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    user_settings = json.load(f)
                    # Recursively update default settings with loaded settings
                    self._update_dict(self.settings, user_settings)
            except Exception as e:
                print(f"Error loading configuration: {e}")
        else:
            self.save()

    def save(self):
        """Saves current configuration to JSON file."""
        try:
            log_dir = os.path.dirname(os.path.abspath(self.config_path))
            if log_dir and not os.path.exists(log_dir):
                os.makedirs(log_dir, exist_ok=True)
            with open(self.config_path, 'w', encoding='utf-8') as f:
                json.dump(self.settings, f, indent=4)
        except Exception as e:
            print(f"Error saving configuration: {e}")

    def _update_dict(self, d, u):
        for k, v in u.items():
            if isinstance(v, dict):
                d[k] = self._update_dict(d.get(k, {}), v)
            else:
                d[k] = v
        return d

    def get(self, key, default=None):
        """Helper to get a setting using key."""
        return self.settings.get(key, default)
