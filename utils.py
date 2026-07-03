"""
utils.py - Tiện ích cho ứng dụng đếm xe và đo tốc độ.
Bao gồm: xuất Excel, tính toán tốc độ, format thời gian.
"""

import io
import math
from datetime import timedelta

import pandas as pd


def calculate_speed(
    prev_centroid: tuple,
    curr_centroid: tuple,
    pixel_per_meter: float,
    fps: float,
) -> float:
    """
    Tính tốc độ xe (km/h) từ sự dịch chuyển centroid giữa 2 frame liên tiếp.

    Args:
        prev_centroid: Tọa độ (x, y) centroid ở frame trước.
        curr_centroid: Tọa độ (x, y) centroid ở frame hiện tại.
        pixel_per_meter: Số pixel tương ứng 1 mét thực tế.
        fps: Tốc độ khung hình (frames per second) của video.

    Returns:
        Tốc độ tính bằng km/h.
    """
    if fps <= 0 or pixel_per_meter <= 0:
        return 0.0

    # Khoảng cách Euclid giữa 2 centroid (pixel)
    dx = curr_centroid[0] - prev_centroid[0]
    dy = curr_centroid[1] - prev_centroid[1]
    pixel_distance = math.sqrt(dx * dx + dy * dy)

    # Chuyển pixel → mét
    meter_distance = pixel_distance / pixel_per_meter

    # Thời gian giữa 2 frame (giây)
    time_seconds = 1.0 / fps

    # Tốc độ: m/s → km/h (nhân 3.6)
    speed_kmh = (meter_distance / time_seconds) * 3.6

    return speed_kmh


def smooth_speed(speed_history: list, window: int = 5) -> float:
    """
    Làm mượt tốc độ bằng trung bình trượt (moving average).

    Args:
        speed_history: Danh sách tốc độ gần nhất của xe.
        window: Số frame để tính trung bình.

    Returns:
        Tốc độ đã được làm mượt (km/h).
    """
    if not speed_history:
        return 0.0
    recent = speed_history[-window:]
    return sum(recent) / len(recent)


def format_time(frame_number: int, fps: float) -> str:
    """
    Chuyển số frame thành chuỗi thời gian HH:MM:SS.

    Args:
        frame_number: Số thứ tự frame trong video.
        fps: Tốc độ khung hình của video.

    Returns:
        Chuỗi thời gian dạng HH:MM:SS.
    """
    if fps <= 0:
        return "00:00:00"
    total_seconds = frame_number / fps
    td = timedelta(seconds=total_seconds)
    # Lấy giờ, phút, giây
    hours = int(td.total_seconds() // 3600)
    minutes = int((td.total_seconds() % 3600) // 60)
    seconds = int(td.total_seconds() % 60)
    return f"{hours:02d}:{minutes:02d}:{seconds:02d}"


def get_vehicle_class_name(class_id: int, class_names: dict) -> str:
    """
    Lấy tên loại xe từ class ID của YOLO.

    Args:
        class_id: ID lớp từ YOLO detection.
        class_names: Dict mapping class_id → tên lớp.

    Returns:
        Tên loại xe (ví dụ: 'car', 'truck', 'bus').
    """
    # Các loại phương tiện trong COCO dataset
    vehicle_classes = {
        1: "bicycle",      # xe đạp
        2: "car",           # ô tô
        3: "motorcycle",    # xe máy
        5: "bus",           # xe buýt
        7: "truck",         # xe tải
    }

    if class_names and class_id in class_names:
        return class_names[class_id]
    return vehicle_classes.get(class_id, f"class_{class_id}")


def export_to_excel(vehicle_log: list, stats: dict) -> bytes:
    """
    Xuất báo cáo ra file Excel (2 sheets).

    Sheet 1 - "Log Chi Tiết": Bảng log từng xe.
    Sheet 2 - "Tổng Hợp": Thống kê tổng quan.

    Args:
        vehicle_log: Danh sách dict chứa thông tin từng xe.
                     Keys: id, type, entry_time, exit_time, max_speed
        stats: Dict thống kê tổng hợp.
               Keys: total, min_speed, max_speed, avg_speed

    Returns:
        Bytes của file Excel để download.
    """
    output = io.BytesIO()

    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        # ===== Sheet 1: Log Chi Tiết =====
        if vehicle_log:
            df_log = pd.DataFrame(vehicle_log)
            df_log.columns = [
                "ID",
                "Loại Xe",
                "Thời Gian Vào",
                "Thời Gian Ra",
                "Tốc Độ Max (km/h)",
            ]
        else:
            df_log = pd.DataFrame(
                columns=[
                    "ID",
                    "Loại Xe",
                    "Thời Gian Vào",
                    "Thời Gian Ra",
                    "Tốc Độ Max (km/h)",
                ]
            )

        df_log.to_excel(writer, sheet_name="Log Chi Tiết", index=False)

        # Chỉnh độ rộng cột
        worksheet = writer.sheets["Log Chi Tiết"]
        for col_idx, col_name in enumerate(df_log.columns, 1):
            max_len = max(
                len(str(col_name)),
                df_log[col_name].astype(str).str.len().max()
                if len(df_log) > 0
                else 0,
            )
            worksheet.column_dimensions[
                chr(64 + col_idx)
            ].width = max_len + 4

        # ===== Sheet 2: Tổng Hợp =====
        summary_data = {
            "Chỉ Số": [
                "Tổng số xe",
                "Tốc độ thấp nhất (km/h)",
                "Tốc độ cao nhất (km/h)",
                "Tốc độ trung bình (km/h)",
            ],
            "Giá Trị": [
                stats.get("total", 0),
                f"{stats.get('min_speed', 0):.1f}",
                f"{stats.get('max_speed', 0):.1f}",
                f"{stats.get('avg_speed', 0):.1f}",
            ],
        }
        df_summary = pd.DataFrame(summary_data)
        df_summary.to_excel(writer, sheet_name="Tổng Hợp", index=False)

        # Chỉnh độ rộng cột
        worksheet2 = writer.sheets["Tổng Hợp"]
        worksheet2.column_dimensions["A"].width = 30
        worksheet2.column_dimensions["B"].width = 20

    output.seek(0)
    return output.getvalue()
