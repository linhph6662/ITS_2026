import cv2
import os
from typing import List, Dict, Any, Optional
from utils.logger import logger

class VehicleDetector:
    """YOLOv11 vehicle detector module supporting class filtering and bounding box visualization."""
    def __init__(self, model_path: Optional[str] = None, confidence_threshold: float = 0.5) -> None:
        self.model_path = model_path
        self.confidence_threshold = confidence_threshold
        
        # Target classes mapping: 2 = car, 3 = motorcycle, 5 = bus, 7 = truck
        self.target_classes: Dict[int, str] = {
            2: "car",
            3: "motorcycle",
            5: "bus",
            7: "truck"
        }
        self.use_mock: bool = True
        self.model: Any = None
        self.load_model()

    def load_model(self) -> None:
        """Loads target YOLOv11 model weights; falls back to mock if loading fails."""
        try:
            from ultralytics import YOLO
            model_file = self.model_path if self.model_path else "models/yolo11n.pt"
            
            # Ensure model parent directories exist
            os.makedirs(os.path.dirname(os.path.abspath(model_file)), exist_ok=True)
            self.model = YOLO(model_file)
            self.use_mock = False
            logger.info("YOLOv11 detector model loaded successfully from path: %s", model_file)
        except Exception as e:
            logger.warning("YOLO loading failed (%s). App will continue in simulation/mock mode.", e)
            self.use_mock = True

    def detect(self, frame: Any) -> List[Dict[str, Any]]:
        """
        Runs object detection on the frame and returns bounding boxes with ByteTrack IDs.
        
        Args:
            frame: cv2 image frame (numpy array)
            
        Returns:
            List of dictionaries containing bbox, class, confidence, and track_id:
            [{'bbox': [x1, y1, x2, y2], 'class': 'car', 'confidence': 0.85, 'class_id': 2, 'track_id': 1}, ...]
        """
        if self.use_mock or self.model is None:
            return []

        try:
            # Native model.track() integrates ByteTrack natively
            results = self.model.track(
                frame, 
                persist=True, 
                conf=self.confidence_threshold, 
                verbose=False
            )
            
            detections: List[Dict[str, Any]] = []
            if not results:
                return detections
                
            boxes = results[0].boxes
            ids = boxes.id.cpu().numpy().astype(int).tolist() if boxes.id is not None else None
            
            for i, box in enumerate(boxes):
                class_id = int(box.cls[0].item())
                if class_id in self.target_classes:
                    conf = float(box.conf[0].item())
                    x1, y1, x2, y2 = map(float, box.xyxy[0].tolist())
                    
                    track_id = ids[i] if ids is not None else None
                    
                    detections.append({
                        "bbox": [x1, y1, x2, y2],
                        "class": self.target_classes[class_id],
                        "confidence": conf,
                        "class_id": class_id,
                        "track_id": track_id
                    })
            return detections
        except Exception as e:
            logger.error("YOLO object tracking pipeline failure: %s", e)
            return []

    def draw_detections(self, frame: Any, detections: List[Dict[str, Any]], tracker: Optional[Any] = None, line_a_y: Optional[int] = None, line_b_y: Optional[int] = None) -> Any:
        """
        Renders bounding boxes, tracking paths, speeds, and triggers line overlays on the frame.
        
        Args:
            frame: Raw cv2 frame (numpy array)
            detections: List of detection dictionaries
            tracker: Optional VehicleTracker history database
            line_a_y: Optional horizontal Line A Y value
            line_b_y: Optional horizontal Line B Y value
            
        Returns:
            Rendered annotated frame.
        """
        try:
            annotated_frame = frame.copy()
        except Exception as e:
            logger.error("Failed to copy image frame for drawings: %s", e)
            return frame
        
        # Cyberpunk/Neon BGR colors
        colors = {
            2: (181, 173, 0),    # car: Cyan-teal
            3: (246, 92, 139),   # motorcycle: Purple
            5: (16, 185, 129),   # bus: Emerald
            7: (68, 68, 239)     # truck: Red
        }

        # 1. Bounding Boxes, IDs, and Speeds
        for d in detections:
            try:
                x1, y1, x2, y2 = map(int, d["bbox"])
                class_id = d.get("class_id", 2)
                track_id = d.get("track_id")
                speed = d.get("speed", 0.0)
                color = colors.get(class_id, (0, 255, 255))
                
                # Draw bounding box
                cv2.rectangle(annotated_frame, (x1, y1), (x2, y2), color, 2)
                
                # Draw header label (ngay phía trên xe)
                label = f"{d['class']} {d['confidence']:.2f}"
                if track_id is not None:
                    if speed > 0:
                        label = f"ID: {track_id} | {d['class']} | {speed:.0f} km/h"
                    else:
                        label = f"ID: {track_id} | {d['class']}"
                
                (w, h), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.4, 1)
                
                banner_y1 = max(0, y1 - 18)
                banner_y2 = max(0, y1)
                cv2.rectangle(annotated_frame, (x1, banner_y1), (x1 + w + 4, banner_y2), color, -1)
                cv2.putText(annotated_frame, label, (x1 + 2, banner_y2 - 4),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 255, 255), 1, cv2.LINE_AA)
            except Exception as e:
                logger.error("Failed drawing box details for detection: %s", e)

        # 2. Movement trajectories (Track Lines)
        if tracker is not None:
            for d in detections:
                track_id = d.get("track_id")
                if track_id is None:
                    continue
                
                try:
                    points = tracker.get_trajectory(track_id)
                    for idx in range(1, len(points)):
                        cv2.line(annotated_frame, points[idx - 1], points[idx], (0, 165, 255), 2)
                    if points:
                        cv2.circle(annotated_frame, points[-1], 3, (0, 255, 0), -1)
                except Exception as e:
                    logger.error("Failed drawing trajectory line for track %s: %s", track_id, e)

        # 3. Reference trigger lines (Line A & Line B)
        try:
            fh, fw, _ = annotated_frame.shape
            if line_a_y is not None:
                cv2.line(annotated_frame, (0, line_a_y), (fw, line_a_y), (0, 255, 255), 2)
                cv2.putText(annotated_frame, f"LINE A (Y: {line_a_y})", (15, line_a_y - 8),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 255, 255), 1, cv2.LINE_AA)

            if line_b_y is not None:
                cv2.line(annotated_frame, (0, line_b_y), (fw, line_b_y), (255, 0, 255), 2)
                cv2.putText(annotated_frame, f"LINE B (Y: {line_b_y})", (15, line_b_y - 8),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.45, (255, 0, 255), 1, cv2.LINE_AA)
        except Exception as e:
            logger.error("Failed drawing speed trigger boundaries on frame: %s", e)

        return annotated_frame
