from typing import Tuple, Dict, Set
from utils.logger import logger

class VehicleCounter:
    """Monitors track centroids to count vehicles crossing a reference horizontal line."""
    def __init__(self, line_y_position: int = 400) -> None:
        self.line_y_position = line_y_position
        self.total_count = 0
        self.counts_by_type: Dict[str, int] = {}
        self.counted_ids: Set[int] = set()
        logger.info("Initialized VehicleCounter at horizontal line Y=%s", line_y_position)

    def set_line_position(self, y_position: int) -> None:
        """Sets the line Y-coordinate threshold for counting."""
        self.line_y_position = y_position
        logger.info("Updated VehicleCounter counting line Y position to: %s", y_position)

    def check_line_crossing(self, object_id: int, prev_centroid: Tuple[int, int], curr_centroid: Tuple[int, int], class_name: str) -> bool:
        """
        Determines if a tracked vehicle crossed the counting line in the current step.
        Increments the counter exacty once per unique object_id.
        
        Args:
            object_id: Persistent track ID
            prev_centroid: Previous coordinate tuple (x, y)
            curr_centroid: Current coordinate tuple (x, y)
            class_name: Target classification class label (e.g. 'car')
            
        Returns:
            True if the vehicle crossed the counting line threshold, False otherwise.
        """
        if object_id in self.counted_ids:
            return False

        # Crossing evaluation (handles both top-to-bottom and bottom-to-top movements)
        prev_y = prev_centroid[1]
        curr_y = curr_centroid[1]

        if (prev_y < self.line_y_position <= curr_y) or (prev_y > self.line_y_position >= curr_y):
            self.total_count += 1
            self.counts_by_type[class_name] = self.counts_by_type.get(class_name, 0) + 1
            self.counted_ids.add(object_id)
            
            logger.info(
                "Counted Vehicle ID %s [%s] crossing line Y=%s. Total counts: %s", 
                object_id, class_name, self.line_y_position, self.total_count
            )
            return True
            
        return False

    def reset(self) -> None:
        """Resets all metrics and memory tables."""
        self.total_count = 0
        self.counts_by_type.clear()
        self.counted_ids.clear()
        logger.info("VehicleCounter metrics reset successfully.")
