import sqlite3
import os
import time
from typing import List, Dict, Any, Optional
from utils.logger import logger

class DatabaseManager:
    """Manages connection, table schemas, and queries for the SQLite traffic database."""
    def __init__(self, db_path: str = "database/traffic.db") -> None:
        self.db_path = db_path
        logger.info("Initializing DatabaseManager targeting database path: %s", db_path)
        self.init_db()

    def get_connection(self) -> sqlite3.Connection:
        """
        Creates and returns a connection to the SQLite database.
        Ensures the parent directories exist before connecting.
        """
        db_dir = os.path.dirname(os.path.abspath(self.db_path))
        if db_dir and not os.path.exists(db_dir):
            os.makedirs(db_dir, exist_ok=True)
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def init_db(self) -> None:
        """Creates the vehicle_history table if it does not already exist in the database."""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS vehicle_history (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        vehicle_id INTEGER,
                        image_path TEXT,
                        speed REAL,
                        datetime TEXT,
                        video_name TEXT
                    )
                """)
                conn.commit()
            logger.info("SQLite Database initialized successfully.")
        except sqlite3.Error as e:
            logger.error("Failed to initialize database tables: %s", e)

    def insert(self, vehicle_id: int, image_path: str, speed: float, datetime_str: str, video_name: str) -> Optional[int]:
        """
        Inserts a new vehicle history record.
        
        Args:
            vehicle_id: Persistent ByteTrack ID
            image_path: Absolute or relative filepath of the crop image JPG
            speed: Calculated speed in km/h
            datetime_str: Timestamp string of the crossing event (YYYY-MM-DD HH:MM:SS)
            video_name: Source video filename
            
        Returns:
            The inserted row's auto-incremented primary ID key, or None if insertion failed.
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO vehicle_history (vehicle_id, image_path, speed, datetime, video_name)
                    VALUES (?, ?, ?, ?, ?)
                """, (vehicle_id, image_path, speed, datetime_str, video_name))
                conn.commit()
                last_id = cursor.lastrowid
                logger.info("Successfully inserted record ID: %s for vehicle ID: %s", last_id, vehicle_id)
                return last_id
        except sqlite3.Error as e:
            logger.error("Failed to insert vehicle record: %s", e)
            return None

    def delete(self, record_id: int) -> int:
        """
        Deletes a vehicle record from history matching the primary ID.
        
        Args:
            record_id: Database key id
            
        Returns:
            The number of affected rows (1 if successful, 0 if ID was not found).
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("DELETE FROM vehicle_history WHERE id = ?", (record_id,))
                conn.commit()
                rows_affected = cursor.rowcount
                logger.info("Successfully deleted record ID: %s (Rows affected: %s)", record_id, rows_affected)
                return rows_affected
        except sqlite3.Error as e:
            logger.error("Failed to delete record ID %s: %s", record_id, e)
            return 0

    def update(self, record_id: int, **kwargs: Any) -> int:
        """
        Dynamically updates columns in vehicle_history for a given ID.
        
        Usage: db.update(1, speed=92.5, image_path="new_path.jpg")
        
        Args:
            record_id: Database key id
            kwargs: Dict of column keys and values to update
            
        Returns:
            The number of affected rows.
        """
        if not kwargs:
            return 0
            
        columns = ", ".join([f"{k} = ?" for k in kwargs.keys()])
        values = list(kwargs.values())
        values.append(record_id)
        
        query = f"UPDATE vehicle_history SET {columns} WHERE id = ?"
        
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(query, values)
                conn.commit()
                rows_affected = cursor.rowcount
                logger.info("Successfully updated record ID: %s fields: %s (Rows affected: %s)", record_id, kwargs, rows_affected)
                return rows_affected
        except sqlite3.Error as e:
            logger.error("Failed to update record ID %s: %s", record_id, e)
            return 0

    def get_all(self) -> List[Dict[str, Any]]:
        """
        Retrieves all historical logs from vehicle_history, ordered by latest.
        
        Returns:
            List of dict records.
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM vehicle_history ORDER BY id DESC")
                return [dict(row) for row in cursor.fetchall()]
        except sqlite3.Error as e:
            logger.error("Failed to fetch all records: %s", e)
            return []

    def search_by_speed(self, min_speed: float, max_speed: float) -> List[Dict[str, Any]]:
        """
        Queries records with speed between min_speed and max_speed.
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT * FROM vehicle_history 
                    WHERE speed BETWEEN ? AND ? 
                    ORDER BY id DESC
                """, (min_speed, max_speed))
                return [dict(row) for row in cursor.fetchall()]
        except sqlite3.Error as e:
            logger.error("Failed to query speed filter (%s - %s): %s", min_speed, max_speed, e)
            return []

    def search_by_date(self, start_date: str, end_date: str) -> List[Dict[str, Any]]:
        """
        Queries records logged between start_date and end_date.
        Expects format 'YYYY-MM-DD HH:MM:SS' or 'YYYY-MM-DD'.
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT * FROM vehicle_history 
                    WHERE datetime BETWEEN ? AND ? 
                    ORDER BY id DESC
                """, (start_date, end_date))
                return [dict(row) for row in cursor.fetchall()]
        except sqlite3.Error as e:
            logger.error("Failed to query date filter (%s - %s): %s", start_date, end_date, e)
            return []

    def search_by_video(self, video_name: str) -> List[Dict[str, Any]]:
        """
        Queries records from a specific video name (case-insensitive substring match).
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT * FROM vehicle_history 
                    WHERE video_name LIKE ? 
                    ORDER BY id DESC
                """, (f"%{video_name}%",))
                return [dict(row) for row in cursor.fetchall()]
        except sqlite3.Error as e:
            logger.error("Failed to query video filter (%s): %s", video_name, e)
            return []

    # Backwards compatibility wrappers for UI modules
    def get_vehicles(self, limit: int = 100, offset: int = 0, filter_type: Optional[str] = None, min_speed: Optional[float] = None) -> List[Dict[str, Any]]:
        query = "SELECT * FROM vehicle_history WHERE 1=1"
        params = []
        if min_speed is not None:
            query += " AND speed >= ?"
            params.append(min_speed)
        query += " ORDER BY id DESC LIMIT ? OFFSET ?"
        params.extend([limit, offset])
        
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(query, params)
                return [dict(row) for row in cursor.fetchall()]
        except sqlite3.Error as e:
            logger.error("Failed to fetch compatibility vehicles: %s", e)
            return []

    def insert_vehicle(self, vehicle_id: int, vehicle_type: str, speed: float, image_path: str) -> Optional[int]:
        dt_str = time.strftime("%Y-%m-%d %H:%M:%S")
        return self.insert(vehicle_id, image_path, speed, dt_str, "Camera Feed")
