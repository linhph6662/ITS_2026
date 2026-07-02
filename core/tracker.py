from typing import List, Dict, Tuple, Any
from utils.logger import logger

class VehicleTracker:
    """Manages centroid trajectory histories for active tracks (ByteTrack target lines)."""
    def __init__(self) -> None:
        # Maps track_id -> list of centroids [(x, y), ...] representing the trajectory path
        self.track_history: Dict[int, List[Tuple[int, int]]] = {}
        logger.info("Initialized VehicleTracker.")

    def update_trajectories(self, detections: List[Dict[str, Any]]) -> None:
        """
        Updates centroid history for actively tracked vehicles and removes stale IDs.
        
        Args:
            detections: List of detection dicts containing 'bbox' and 'track_id' keys
        """
        active_ids = set()
        
        for d in detections:
            track_id = d.get("track_id")
            if track_id is None:
                continue
                
            active_ids.add(track_id)
            try:
                x1, y1, x2, y2 = d["bbox"]
                
                # Bottom-middle coordinate of bounding box matches vehicle contact point
                cx = int((x1 + x2) / 2)
                cy = int(y2)
                
                if track_id not in self.track_history:
                    self.track_history[track_id] = []
                    logger.debug("Starting tracking trace for vehicle ID: %s", track_id)
                    
                self.track_history[track_id].append((cx, cy))
                
                # Limit history lengths to 30 trace coordinates to save memory
                if len(self.track_history[track_id]) > 30:
                    self.track_history[track_id].pop(0)
            except (ValueError, KeyError, TypeError) as e:
                logger.error("Failed to parse bbox coordinates for vehicle ID %s: %s", track_id, e)

        # Purge trace lines for vehicles that have left the camera viewport
        stale_ids = [tid for tid in list(self.track_history.keys()) if tid not in active_ids]
        for tid in stale_ids:
            if tid in self.track_history:
                del self.track_history[tid]
                logger.debug("Removed stale track ID %s from memory", tid)

    def get_trajectory(self, track_id: int) -> List[Tuple[int, int]]:
        """
        Returns the history list of tuples (x, y) for a specific track ID.
        """
        return self.track_history.get(track_id, [])

    def reset(self) -> None:
        """Clears all tracking histories."""
        self.track_history.clear()
        logger.info("VehicleTracker trajectories reset successfully.")
