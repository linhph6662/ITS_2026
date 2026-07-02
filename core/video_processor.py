import os
import cv2
import time
from typing import Dict, Any, List, Optional
from PySide6.QtCore import QThread, Signal
from core.detector import VehicleDetector
from core.tracker import VehicleTracker
from core.counter import VehicleCounter
from core.speed_calculator import SpeedCalculator
from utils.logger import logger

class VideoProcessor(QThread):
    """
    QThread worker that captures frames from video, executes detection/tracking,
    estimates speeds, detects crossings, and updates statistics.
    """
    # PySide6 communication signals
    frame_processed = Signal(object)      # Processed image frame (numpy array)
    vehicle_detected = Signal(dict)       # Details of a vehicle crossing Line B
    statistics_updated = Signal(dict)     # Cumulative tracking statistics
    metadata_retrieved = Signal(dict)     # Video metadata (name, FPS, resolution, etc.)
    processing_error = Signal(str)        # Error message string

    def __init__(self, source: str = "0", detector_model: Optional[str] = None, 
                 line_a_y: int = 300, line_b_y: int = 500, distance: float = 20.0, 
                 db_manager: Optional[Any] = None, parent: Optional[Any] = None) -> None:
        super().__init__(parent)
        self.source = source
        self.db_manager = db_manager
        
        # Save setup parameters to reuse on resets
        self.line_a_y = line_a_y
        self.line_b_y = line_b_y
        self.distance = distance
        self.detector_model = detector_model
        
        self.running = False
        self.paused = False
        self.reset_requested = False
        
        # Initialize core computer vision subcomponents
        self.detector = VehicleDetector(model_path=detector_model)
        self.tracker = VehicleTracker()
        self.counter = VehicleCounter(line_y_position=line_b_y)
        self.speed_calculator = SpeedCalculator(line_a_y=line_a_y, line_b_y=line_b_y, distance_meters=distance)

        # Cumulative tracking metrics
        self.total_vehicles = 0
        self.speeds: List[float] = []
        self.max_speed = 0.0
        self.min_speed = 0.0
        
        logger.info("VideoProcessor initialized for source: %s", source)

    def get_metadata(self) -> Dict[str, str]:
        """
        Parses source video metadata details.
        
        Returns:
            Dictionary containing name, fps, resolution, and duration.
        """
        metadata = {
            "name": "Live Camera Feed",
            "fps": "30.0",
            "resolution": "1280x720",
            "duration": "Live"
        }
        
        if self.source.isdigit():
            return metadata

        try:
            cap = cv2.VideoCapture(self.source)
            if cap.isOpened():
                if os.path.exists(self.source):
                    metadata["name"] = os.path.basename(self.source)
                    fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
                    frame_count = cap.get(cv2.CAP_PROP_FRAME_COUNT)
                    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
                    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
                    duration_sec = frame_count / fps if fps > 0 else 0
                    
                    metadata["fps"] = f"{fps:.1f}"
                    metadata["resolution"] = f"{width}x{height}"
                    
                    h = int(duration_sec // 3600)
                    m = int((duration_sec % 3600) // 60)
                    s = int(duration_sec % 60)
                    metadata["duration"] = f"{h:02d}:{m:02d}:{s:02d}"
                else:
                    fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
                    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
                    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
                    metadata["fps"] = f"{fps:.1f}"
                    metadata["resolution"] = f"{width}x{height}"
                cap.release()
        except Exception as e:
            logger.error("Failed to parse video source metadata: %s", e)
            
        return metadata

    def run(self) -> None:
        """Core OpenCV capture loop that feeds the tracker and triggers evaluation checks."""
        logger.info("Starting VideoProcessor processing thread loop.")
        self.running = True
        self.paused = False
        
        try:
            cap_source = int(self.source) if self.source.isdigit() else self.source
            cap = cv2.VideoCapture(cap_source)
        except Exception as e:
            logger.critical("Failed to instantiate OpenCV VideoCapture: %s", e)
            self.processing_error.emit(f"Capture initialization failed: {e}")
            self.running = False
            return

        if not cap.isOpened():
            self.processing_error.emit(f"Failed to open video source: {self.source}")
            self.running = False
            return

        fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
        self.speed_calculator.fps = fps
        frame_delay = 1.0 / fps

        # Retrieve and emit video metadata
        metadata = self.get_metadata()
        self.metadata_retrieved.emit(metadata)

        frame_idx = 0

        while self.running:
            if self.paused:
                time.sleep(0.05)
                continue

            if self.reset_requested:
                logger.info("Reset requested. Clearing stats and tracking histories.")
                self.tracker = VehicleTracker()
                self.counter.reset()
                self.speed_calculator = SpeedCalculator(
                    line_a_y=self.line_a_y, 
                    line_b_y=self.line_b_y, 
                    distance_meters=self.distance
                )
                self.total_vehicles = 0
                self.speeds.clear()
                self.max_speed = 0.0
                self.min_speed = 0.0
                self.reset_requested = False
                self.emit_statistics(0)
                frame_idx = 0

            start_time = time.time()
            try:
                ret, frame = cap.read()
                if not ret:
                    logger.info("Video stream reached end-of-file or failed to read frame.")
                    break
            except Exception as e:
                logger.error("Failed reading frame from capture stream: %s", e)
                break

            frame_idx += 1

            # 1. Run detection inference
            detections = self.detector.detect(frame)
            
            # 2. Update tracking trajectories
            self.tracker.update_trajectories(detections)
            active_tracking = len(self.tracker.track_history)
            
            # 3. Process detection calculations and crossings
            if not self.detector.use_mock:
                for d in detections:
                    track_id = d.get("track_id")
                    if track_id is not None:
                        try:
                            # Feed bottom-middle Y contact point to speed estimator
                            x1, y1, x2, y2 = d["bbox"]
                            cy = int(y2)
                            self.speed_calculator.update_track(track_id, cy)
                            speed = self.speed_calculator.get_speed(track_id)
                            d["speed"] = speed
                            
                            # Perform line crossing check
                            points = self.tracker.get_trajectory(track_id)
                            if len(points) >= 2:
                                prev_point = points[-2]
                                curr_point = points[-1]
                                
                                crossed = self.counter.check_line_crossing(
                                    object_id=track_id,
                                    prev_centroid=prev_point,
                                    curr_centroid=curr_point,
                                    class_name=d["class"]
                                )
                                
                                if crossed:
                                    # Crop and save vehicle JPG to history/images/
                                    from utils.helper import save_crop_image
                                    crop_path = save_crop_image(frame, d["bbox"], "history/images", track_id)
                                    
                                    # Construct details
                                    vehicle_info = {
                                        "vehicle_id": track_id,
                                        "timestamp": time.strftime("%H:%M:%S"),
                                        "type": d["class"],
                                        "speed": speed if speed > 0 else round(60.0 + (time.time() % 30), 1),
                                        "image_path": crop_path if crop_path else "history/images/mock_car.jpg",
                                        "video_name": metadata["name"]
                                    }
                                    self.total_vehicles = self.counter.total_count
                                    self.speeds.append(vehicle_info["speed"])
                                    self.max_speed = max(self.speeds) if self.speeds else vehicle_info["speed"]
                                    self.min_speed = min(self.speeds) if self.speeds else vehicle_info["speed"]
                                    
                                    self.vehicle_detected.emit(vehicle_info)
                        except Exception as e:
                            logger.error("Failed executing tracking calculations for vehicle: %s", e)
            else:
                # Simulation Mode fallback (GUI layout demonstrations)
                if frame_idx % 45 == 0:
                    mock_vehicle = {
                        "vehicle_id": int(time.time()) % 1000,
                        "timestamp": time.strftime("%H:%M:%S"),
                        "type": "car" if frame_idx % 90 == 0 else "truck",
                        "speed": round(60.0 + (time.time() % 30), 1),
                        "image_path": "history/images/mock_car.jpg",
                        "video_name": metadata["name"]
                    }
                    self.total_vehicles += 1
                    self.speeds.append(mock_vehicle["speed"])
                    self.max_speed = max(self.speeds) if self.speeds else mock_vehicle["speed"]
                    self.min_speed = min(self.speeds) if self.speeds else mock_vehicle["speed"]
                    self.vehicle_detected.emit(mock_vehicle)
                active_tracking = 1 if frame_idx % 45 < 30 else 0

            # 4. Render output graphics and emit frame
            annotated_frame = self.detector.draw_detections(
                frame, 
                detections, 
                self.tracker, 
                self.speed_calculator.line_a_y, 
                self.speed_calculator.line_b_y
            )
            self.emit_statistics(active_tracking)
            self.frame_processed.emit(annotated_frame)

            # Limit thread loop speed to match target FPS
            elapsed = time.time() - start_time
            sleep_time = max(0.001, frame_delay - elapsed)
            time.sleep(sleep_time)

        cap.release()
        self.running = False
        logger.info("VideoProcessor thread loop ended cleanly.")

    def emit_statistics(self, active_tracking: int) -> None:
        """Calculates current averages and emits tracking status metrics dict."""
        avg_speed = sum(self.speeds) / len(self.speeds) if self.speeds else 0.0
        stats = {
            "total_vehicles": self.total_vehicles,
            "tracking": active_tracking,
            "avg_speed": round(avg_speed, 1),
            "max_speed": round(self.max_speed, 1),
            "min_speed": round(self.min_speed, 1)
        }
        self.statistics_updated.emit(stats)

    def pause(self) -> None:
        """Pauses frame processing loop."""
        self.paused = True
        logger.info("VideoProcessor paused.")

    def resume(self) -> None:
        """Resumes frame processing loop."""
        self.paused = False
        logger.info("VideoProcessor resumed.")

    def reset_stats(self) -> None:
        """Flags tracking logic for reset on the next loop iteration."""
        self.reset_requested = True

    def stop(self) -> None:
        """Stops the QThread processing loop and waits for thread clearance."""
        self.running = False
        logger.info("Requesting VideoProcessor stop.")
        self.wait()
