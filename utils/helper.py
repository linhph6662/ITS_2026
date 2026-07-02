import datetime
import os
import cv2
from typing import List, Tuple, Optional
from utils.logger import logger

def format_datetime(dt: Optional[datetime.datetime] = None) -> str:
    """Formats datetime to string YYYY-MM-DD HH:MM:SS."""
    if dt is None:
        dt = datetime.datetime.now()
    return dt.strftime("%Y-%m-%d %H:%M:%S")

def save_crop_image(image: Optional[cv2.Mat], bbox: List[float], output_dir: str, vehicle_id: int) -> Optional[str]:
    """
    Crops a vehicle image and saves it to output_dir.
    
    Args:
        image: Original raw frame image (numpy array)
        bbox: Bounding box coordinates list [x1, y1, x2, y2]
        output_dir: Destination folder path
        vehicle_id: Track ID of the vehicle
        
    Returns:
        The saved crop JPG path on disk, or None if cropping failed.
    """
    if image is None or len(bbox) != 4:
        logger.error("Failed image cropping check: frame is null or bbox length is not 4.")
        return None
    
    try:
        os.makedirs(output_dir, exist_ok=True)
        x1, y1, x2, y2 = map(int, bbox)
        h, w, _ = image.shape
        
        # Clip coordinates within frame boundary
        x1, y1 = max(0, x1), max(0, y1)
        x2, y2 = min(w, x2), min(h, y2)
        
        crop = image[y1:y2, x1:x2]
        if crop.size == 0:
            logger.warning("Cropped image segment has size 0. Bounding box coordinates are invalid.")
            return None
            
        filename = f"vehicle_{vehicle_id}_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.jpg"
        filepath = os.path.join(output_dir, filename)
        
        cv2.imwrite(filepath, crop)
        logger.info("Successfully cropped and saved vehicle ID %s image to: %s", vehicle_id, filepath)
        return filepath
    except Exception as e:
        logger.error("Failed to crop and save vehicle ID %s image: %s", vehicle_id, e)
        return None

def calculate_centroid(bbox: List[float]) -> Tuple[int, int]:
    """Calculates centroid coordinate (cx, cy) of a bounding box."""
    try:
        x1, y1, x2, y2 = bbox
        cx = int((x1 + x2) / 2)
        cy = int((y1 + y2) / 2)
        return cx, cy
    except Exception as e:
        logger.error("Failed calculating centroid coordinates for bbox %s: %s", bbox, e)
        return 0, 0
