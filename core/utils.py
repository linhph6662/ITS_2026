"""
core/utils.py — Tiện ích tính toán và xuất báo cáo.

Bao gồm: tính tốc độ, làm mượt tốc độ, format thời gian, xuất Excel.
"""

import io
import math
from datetime import timedelta

import pandas as pd


# ─────────────────────────────────────────────────────────────────────────────
# TỐC ĐỘ
# ─────────────────────────────────────────────────────────────────────────────

def calculate_speed(
    prev_centroid: tuple,
    curr_centroid: tuple,
    pixel_per_meter: float,
    fps: float,
) -> float:
    """
    Tính tốc độ xe (km/h) từ sự dịch chuyển centroid giữa 2 frame liên tiếp.

    Args:
        prev_centroid: Tọa độ (x, y) centroid ở frame trước (warped space).
        curr_centroid: Tọa độ (x, y) centroid ở frame hiện tại (warped space).
        pixel_per_meter: Số pixel tương ứng 1 mét thực tế.
        fps: Tốc độ khung hình (frames per second) của video.

    Returns:
        Tốc độ tính bằng km/h.
    """
    if fps <= 0 or pixel_per_meter <= 0:
        return 0.0

    dx = curr_centroid[0] - prev_centroid[0]
    dy = curr_centroid[1] - prev_centroid[1]
    pixel_distance = math.sqrt(dx * dx + dy * dy)

    meter_distance = pixel_distance / pixel_per_meter
    time_seconds   = 1.0 / fps
    speed_kmh      = (meter_distance / time_seconds) * 3.6

    return speed_kmh


def smooth_speed(speed_history: list, window: int = 15) -> float:
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


# ─────────────────────────────────────────────────────────────────────────────
# THỜI GIAN & TÊN CLASS
# ─────────────────────────────────────────────────────────────────────────────

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
    td = timedelta(seconds=frame_number / fps)
    total_s = int(td.total_seconds())
    h = total_s // 3600
    m = (total_s % 3600) // 60
    s = total_s % 60
    return f"{h:02d}:{m:02d}:{s:02d}"


def get_vehicle_class_name(class_id: int, class_names: dict) -> str:
    """
    Lấy tên loại xe từ class ID của YOLO.

    Chỉ nhận diện các phương tiện trên đường cao tốc:
    car (2), bus (5), truck (7). Xe máy và xe đạp đã bị loại ở tầng YOLO.

    Args:
        class_id: ID lớp từ YOLO detection.
        class_names: Dict mapping class_id → tên lớp.

    Returns:
        Tên loại xe (ví dụ: 'car', 'truck', 'bus').
    """
    highway_classes = {
        2: "car",
        5: "bus",
        7: "truck",
    }
    if class_names and class_id in class_names:
        return class_names[class_id]
    return highway_classes.get(class_id, f"vehicle_{class_id}")


# ─────────────────────────────────────────────────────────────────────────────
# XUẤT EXCEL
# ─────────────────────────────────────────────────────────────────────────────

def export_to_excel(vehicle_log: list, stats: dict) -> bytes:
    """
    Xuất báo cáo ra file Excel (2 sheets).

    Sheet 1 — "Log Chi Tiết": Bảng log từng xe.
    Sheet 2 — "Tổng Hợp":    Thống kê tổng quan.

    Args:
        vehicle_log: List[dict] — {id, type, entry_time, exit_time, max_speed}.
        stats: Dict — {total, min_speed, max_speed, avg_speed}.

    Returns:
        Bytes của file Excel.
    """
    output = io.BytesIO()

    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        # ── Sheet 1: Log Chi Tiết ────────────────────────────────────────────
        columns = ["ID", "Loại Xe", "Thời Gian Vào", "Thời Gian Ra", "Tốc Độ Max (km/h)"]

        if vehicle_log:
            df_log = pd.DataFrame(vehicle_log, columns=["id", "type", "entry_time", "exit_time", "max_speed"])
            df_log.columns = columns
        else:
            df_log = pd.DataFrame(columns=columns)

        df_log.to_excel(writer, sheet_name="Log Chi Tiết", index=False)

        ws = writer.sheets["Log Chi Tiết"]
        for col_idx, col_name in enumerate(df_log.columns, 1):
            max_len = len(str(col_name))
            if len(df_log) > 0:
                max_len = max(max_len, df_log[col_name].astype(str).str.len().max())
            ws.column_dimensions[chr(64 + col_idx)].width = max_len + 4

        # ── Sheet 2: Tổng Hợp ────────────────────────────────────────────────
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

        ws2 = writer.sheets["Tổng Hợp"]
        ws2.column_dimensions["A"].width = 30
        ws2.column_dimensions["B"].width = 20

    output.seek(0)
    return output.getvalue()
