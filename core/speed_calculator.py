import time
from typing import Dict, Optional
from utils.logger import logger

class SpeedCalculator:
    """Estimates speed based on time of flight between two horizontal lines."""
    def __init__(self, line_a_y: int = 300, line_b_y: int = 500, distance_meters: float = 20.0, fps: float = 30.0) -> None:
        self.line_a_y = line_a_y
        self.line_b_y = line_b_y
        self.distance_meters = distance_meters
        self.fps = fps
        
        self.last_y: Dict[int, int] = {}              # object_id -> last Y coordinate
        self.timestamps_a: Dict[int, float] = {}      # object_id -> timestamp at Line A
        self.calculated_speeds: Dict[int, float] = {}  # object_id -> speed value (km/h)
        
        logger.info(
            "Initialized SpeedCalculator: Line A (Y: %s), Line B (Y: %s), Distance: %s meters", 
            line_a_y, line_b_y, distance_meters
        )

    def update_track(self, object_id: int, centroid_y: int) -> None:
        """
        Updates tracking position and evaluates if the vehicle has crossed Line A or Line B.
        
        Args:
            object_id: Track ID of the target vehicle
            centroid_y: Current Y-coordinate of the vehicle centroid reference point
        """
        current_time = time.time()
        prev_y = self.last_y.get(object_id)
        
        if prev_y is not None:
            # Check crossing Line A (supports both top-to-bottom and bottom-to-top directions)
            if (prev_y < self.line_a_y <= centroid_y) or (prev_y > self.line_a_y >= centroid_y):
                if object_id not in self.timestamps_a:
                    self.timestamps_a[object_id] = current_time
                    logger.info("Vehicle ID %s crossed Line A at Y=%s. Timestamp recorded.", object_id, self.line_a_y)
                    
            # Check crossing Line B
            if (prev_y < self.line_b_y <= centroid_y) or (prev_y > self.line_b_y >= centroid_y):
                if object_id in self.timestamps_a and object_id not in self.calculated_speeds:
                    t_a = self.timestamps_a[object_id]
                    dt = current_time - t_a
                    
                    if dt > 0.05:  # Avoid division-by-zero or extreme noise
                        speed_mps = self.distance_meters / dt
                        speed_kmh = speed_mps * 3.6
                        self.calculated_speeds[object_id] = round(speed_kmh, 1)
                        logger.info(
                            "Vehicle ID %s crossed Line B at Y=%s. Elapsed time: %.3f s. Estimated speed: %.1f km/h",
                            object_id, self.line_b_y, dt, speed_kmh
                        )
                    else:
                        logger.warning("Vehicle ID %s transition time dt too small (%.4f s). Ignored.", object_id, dt)

        self.last_y[object_id] = centroid_y

    def get_speed(self, object_id: int) -> float:
        """
        Retrieves the calculated speed in km/h for the vehicle.
        
        Args:
            object_id: Unique track ID of the vehicle
            
        Returns:
            The calculated speed in km/h, or 0.0 if not yet estimated.
        """
        return self.calculated_speeds.get(object_id, 0.0)

    def clear_track(self, object_id: int) -> None:
        """
        Purges historical logs for a given track ID when it exits the camera scene.
        
        Args:
            object_id: Track ID to remove
        """
        if object_id in self.last_y:
            del self.last_y[object_id]
        if object_id in self.timestamps_a:
            del self.timestamps_a[object_id]
        if object_id in self.calculated_speeds:
            del self.calculated_speeds[object_id]
        logger.info("Cleaned up SpeedCalculator cache for object ID %s", object_id)
