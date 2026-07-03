"""
core/tracker.py — Vehicle tracking & speed measurement.

Sử dụng YOLO để phát hiện và ByteTrack để theo dõi xe.
Tối ưu cho đường cao tốc: chỉ nhận diện car/bus/truck, không có xe máy.

Thông số tốc độ:
    - Khoảng cách thực tế giữa 2 vạch sơn = 12m
    - Warped space height = 600px
    - PPM mặc định = 600 / 12 = 50.0 px/m
"""

import os
from collections import defaultdict
from pathlib import Path

import cv2
import numpy as np
from ultralytics import YOLO

from core.utils import calculate_speed, format_time, get_vehicle_class_name, smooth_speed

# Đường dẫn tới file config ByteTrack (tương đối từ thư mục gốc dự án)
_CONFIG_DIR  = Path(__file__).parent.parent / "config"
BYTETRACK_CFG = str(_CONFIG_DIR / "bytetrack.yaml")

# Khoảng cách thực tế giữa 2 vạch sơn trắng (mét)
ROAD_MARKING_DISTANCE_M = 12.0

# Kích thước warped space (bird's-eye view)
DST_WIDTH  = 400   # px — chiều rộng (không ảnh hưởng tốc độ)
DST_HEIGHT = 600   # px — chiều cao tương ứng với 12m thực

# PPM mặc định: DST_HEIGHT / ROAD_MARKING_DISTANCE_M = 50.0 px/m
DEFAULT_PPM = DST_HEIGHT / ROAD_MARKING_DISTANCE_M   # 50.0

# Chỉ nhận diện phương tiện trên đường cao tốc (không có xe máy/xe đạp)
HIGHWAY_CLASS_IDS = [2, 5, 7]   # car, bus, truck


class VehicleTracker:
    """
    Quản lý phát hiện, theo dõi xe và đo tốc độ từ video.

    Attributes:
        model:            YOLO model đã load.
        pixel_per_meter:  Tỉ lệ pixel/mét trong warped space.
        fps:              FPS của video nguồn.
        track_history:    Lịch sử centroid {track_id: [(x,y), ...]}.
        speed_history:    Lịch sử tốc độ {track_id: [spd, ...]}.
        vehicle_info:     Thông tin tổng hợp {track_id: {...}}.
        current_frame:    Số frame hiện tại đang xử lý.
    """

    def __init__(self, model_path: str, fps: float = 30.0):
        """
        Khởi tạo VehicleTracker.

        Args:
            model_path: Đường dẫn tới file YOLO model (.pt).
            fps:        FPS của video (mặc định 30.0).
        """
        self.model           = YOLO(model_path)
        self.pixel_per_meter = DEFAULT_PPM
        self.fps             = fps

        # Lịch sử tracking
        self.track_history  = defaultdict(list)   # {id: [(x,y), ...]}
        self.speed_history  = defaultdict(list)    # {id: [speed, ...]}
        self.vehicle_info   = {}                   # {id: {type, entry_frame, ...}}
        self.current_frame  = 0

        # ROI & Perspective Transform
        self.roi_points          = None   # 4 điểm gốc (tọa độ frame)
        self.perspective_matrix  = None   # Ma trận M (frame → warped)

        # Counting line — phát hiện xe cắt ngang vạch
        self.counting_line_pos  = 0.5    # Vị trí vạch (0–1) trên trục chính
        self.counting_line_axis = "y"    # "x" hoặc "y" — tự động xác định
        self._axis_locked       = False  # True sau khi đã xác định hướng
        self._motion_vectors    = []     # Tích luỹ (dx, dy) trong warped space
        self.counted_ids        = set()  # Track ID đã qua vạch đếm
        self.line_side          = {}     # {id: side} phía vạch ở frame trước

    # ─────────────────────────────────────────────────────────────────────────
    # RESET
    # ─────────────────────────────────────────────────────────────────────────

    def reset(self):
        """Xóa toàn bộ dữ liệu tracking, giữ nguyên ROI."""
        self.track_history.clear()
        self.speed_history.clear()
        self.vehicle_info.clear()
        self.counted_ids.clear()
        self.line_side.clear()
        self._motion_vectors.clear()
        self._axis_locked       = False
        self.counting_line_axis = "y"
        self.current_frame      = 0
        self.model.predictor    = None

    # ─────────────────────────────────────────────────────────────────────────
    # ROI & PERSPECTIVE TRANSFORM
    # ─────────────────────────────────────────────────────────────────────────

    def set_roi(self, points) -> None:
        """
        Thiết lập ROI 4 điểm và tính ma trận perspective transform.

        Thứ tự click: P1=TL → P2=TR → P3=BR → P4=BL.
        Cạnh dưới (P3-P4) phải chạm mép trong vạch sơn dưới.
        Cạnh trên (P1-P2) phải bao trùm mép ngoài vạch sơn trên.
        Khoảng cách thực giữa 2 vạch = 12m → PPM = 50.0 px/m.

        Args:
            points: List/tuple 4 điểm theo thứ tự click của người dùng.
        """
        if len(points) != 4:
            return

        src_pts = np.array(points, dtype=np.float32)
        self.roi_points = src_pts

        dst_pts = np.array([
            [0,              0             ],
            [DST_WIDTH - 1,  0             ],
            [DST_WIDTH - 1,  DST_HEIGHT - 1],
            [0,              DST_HEIGHT - 1],
        ], dtype=np.float32)

        self.perspective_matrix = cv2.getPerspectiveTransform(src_pts, dst_pts)
        print(f"[ROI]  Perspective matrix computed. PPM={self.pixel_per_meter:.1f} px/m "
              f"({ROAD_MARKING_DISTANCE_M}m → {DST_HEIGHT}px)")

    def clear_roi(self) -> None:
        """Xóa ROI, ma trận perspective và reset toàn bộ tracking data."""
        self.roi_points         = None
        self.perspective_matrix = None
        self.counted_ids.clear()
        self.line_side.clear()
        self.track_history.clear()
        self.speed_history.clear()
        self.vehicle_info.clear()
        self._motion_vectors.clear()
        self._axis_locked       = False
        self.counting_line_axis = "y"
        print("[ROI]  ROI cleared.")

    # ─────────────────────────────────────────────────────────────────────────
    # PRIVATE HELPERS
    # ─────────────────────────────────────────────────────────────────────────

    def _transform_point(self, point: tuple) -> tuple:
        """
        Chuyển 1 điểm từ tọa độ frame gốc sang warped space.

        Args:
            point: (x, y) trong tọa độ frame.

        Returns:
            (x', y') trong warped space.
        """
        if self.perspective_matrix is None:
            return point
        pt = np.array([[[point[0], point[1]]]], dtype=np.float32)
        warped = cv2.perspectiveTransform(pt, self.perspective_matrix)
        return (float(warped[0][0][0]), float(warped[0][0][1]))

    def _is_inside_roi(self, point: tuple) -> bool:
        """
        Kiểm tra điểm có nằm trong vùng ROI không.

        Args:
            point: (x, y) centroid trong tọa độ frame.

        Returns:
            True nếu nằm trong hoặc trên biên ROI.
        """
        if self.roi_points is None:
            return False
        result = cv2.pointPolygonTest(
            self.roi_points.astype(np.float32),
            (float(point[0]), float(point[1])),
            False,
        )
        return result >= 0

    def _update_motion_axis(self, dx: float, dy: float) -> None:
        """
        Tích lũy vector chuyển động để tự động xác định trục chính.
        Gọi sau mỗi frame cho đến khi có đủ 60 mẫu.

        Args:
            dx: Chênh lệch x trong warped space.
            dy: Chênh lệch y trong warped space.
        """
        if self._axis_locked:
            return
        if abs(dx) > 1.0 or abs(dy) > 1.0:
            self._motion_vectors.append((abs(dx), abs(dy)))

        if len(self._motion_vectors) >= 60:
            total_dx = sum(v[0] for v in self._motion_vectors)
            total_dy = sum(v[1] for v in self._motion_vectors)
            if total_dx >= total_dy:
                self.counting_line_axis = "x"
                print(f"[ROI]  Xe di chuyển NGANG → vạch đứng "
                      f"(dx={total_dx:.0f}, dy={total_dy:.0f})")
            else:
                self.counting_line_axis = "y"
                print(f"[ROI]  Xe di chuyển DỌC → vạch ngang "
                      f"(dx={total_dx:.0f}, dy={total_dy:.0f})")
            self._axis_locked = True

    def _check_line_crossing(self, track_id: int, warped_pt: tuple) -> bool:
        """
        Kiểm tra xe có vượt qua counting line không.

        Args:
            track_id:  Track ID của xe.
            warped_pt: Tọa độ (x, y) trong warped space.

        Returns:
            True nếu xe vừa vượt qua vạch (lần đầu).
        """
        if track_id in self.counted_ids:
            return False

        if self.counting_line_axis == "x":
            pos         = warped_pt[0]
            line_pos    = self.counting_line_pos * DST_WIDTH
            current_side = "left" if pos < line_pos else "right"
        else:
            pos         = warped_pt[1]
            line_pos    = self.counting_line_pos * DST_HEIGHT
            current_side = "above" if pos < line_pos else "below"

        if track_id not in self.line_side:
            self.line_side[track_id] = current_side
            return False

        prev_side = self.line_side[track_id]
        self.line_side[track_id] = current_side

        if prev_side != current_side:
            self.counted_ids.add(track_id)
            return True

        return False

    @staticmethod
    def _get_track_color(track_id: int) -> tuple:
        """
        Tạo màu BGR độc lập cho mỗi track ID.

        Args:
            track_id: ID của track.

        Returns:
            Tuple màu BGR.
        """
        hue = (track_id * 47) % 180
        hsv = np.array([[[hue, 255, 220]]], dtype=np.uint8)
        bgr = cv2.cvtColor(hsv, cv2.COLOR_HSV2BGR)[0][0]
        return (int(bgr[0]), int(bgr[1]), int(bgr[2]))

    # ─────────────────────────────────────────────────────────────────────────
    # ANNOTATION HELPERS
    # ─────────────────────────────────────────────────────────────────────────

    def _draw_roi_overlay(self, frame: np.ndarray) -> None:
        """Vẽ ROI polygon và counting line lên frame."""
        roi_int = self.roi_points.astype(np.int32)
        overlay = frame.copy()
        cv2.fillPoly(overlay, [roi_int], (0, 180, 255))
        cv2.addWeighted(overlay, 0.12, frame, 0.88, 0, frame)
        cv2.polylines(frame, [roi_int], True, (0, 180, 255), 2, cv2.LINE_AA)
        for i, pt in enumerate(roi_int):
            cv2.circle(frame, tuple(pt), 6, (0, 255, 255), -1, cv2.LINE_AA)
            cv2.putText(frame, str(i + 1), (pt[0] + 8, pt[1] - 8),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 255), 1, cv2.LINE_AA)

        if self.perspective_matrix is None:
            return

        # Vẽ counting line (inverse transform từ warped → frame gốc)
        inv_M = np.linalg.inv(self.perspective_matrix)
        p = self.counting_line_pos
        if self.counting_line_axis == "x":
            lx = p * (DST_WIDTH - 1)
            pts_dst = np.array([[[lx, 0]], [[lx, DST_HEIGHT - 1]]], dtype=np.float32)
        else:
            ly = p * (DST_HEIGHT - 1)
            pts_dst = np.array([[[0, ly]], [[DST_WIDTH - 1, ly]]], dtype=np.float32)

        pts_src = cv2.perspectiveTransform(pts_dst, inv_M)
        lp0 = tuple(pts_src[0][0].astype(int))
        lp1 = tuple(pts_src[1][0].astype(int))

        # Vẽ đường đứt nét (dashed line)
        total_len = int(np.linalg.norm(
            np.array(lp1, dtype=float) - np.array(lp0, dtype=float)
        ))
        n_dashes = max(1, total_len // 20)
        for seg in range(n_dashes):
            t0 = seg / n_dashes
            t1 = (seg + 0.5) / n_dashes
            p0 = (int(lp0[0] + t0 * (lp1[0] - lp0[0])),
                  int(lp0[1] + t0 * (lp1[1] - lp0[1])))
            p1 = (int(lp0[0] + t1 * (lp1[0] - lp0[0])),
                  int(lp0[1] + t1 * (lp1[1] - lp0[1])))
            cv2.line(frame, p0, p1, (0, 255, 0), 2, cv2.LINE_AA)

        # Label đếm xe
        mid = ((lp0[0] + lp1[0]) // 2, (lp0[1] + lp1[1]) // 2)
        status = "" if self._axis_locked else " (calibrating...)"
        cv2.putText(frame,
                    f"COUNT: {len(self.counted_ids)}{status}",
                    (mid[0] + 6, mid[1] - 6),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0, 255, 0), 2, cv2.LINE_AA)

    def _draw_vehicle(self, frame: np.ndarray, box: np.ndarray,
                      track_id: int, vehicle_type: str, speed: float) -> None:
        """Vẽ bounding box, label và trail của một xe."""
        x1, y1, x2, y2 = box.astype(int)
        color         = self._get_track_color(track_id)
        is_counted    = track_id in self.counted_ids
        box_thickness = 3 if is_counted else 2

        cv2.rectangle(frame, (x1, y1), (x2, y2), color, box_thickness)

        if is_counted:
            cv2.circle(frame, (x2 - 6, y1 + 6), 5, (0, 255, 0), -1)

        # Label trên: ID + loại xe
        label = f"ID:{track_id} {vehicle_type}"
        (tw, th), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.6, 1)
        cv2.rectangle(frame, (x1, y1 - th - 10), (x1 + tw + 4, y1), color, -1)
        cv2.putText(frame, label, (x1 + 2, y1 - 5),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 1, cv2.LINE_AA)

        # Label dưới: tốc độ
        speed_label = f"{speed:.1f} km/h"
        (sw, sh), _ = cv2.getTextSize(speed_label, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 1)
        cv2.rectangle(frame, (x1, y2), (x1 + sw + 4, y2 + sh + 8), (0, 0, 0), -1)
        cv2.putText(frame, speed_label, (x1 + 2, y2 + sh + 4),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 255), 1, cv2.LINE_AA)

        # Trail (đường đi)
        trail = self.track_history[track_id]
        if len(trail) > 1:
            pts = np.array(trail[-20:], dtype=np.int32).reshape((-1, 1, 2))
            cv2.polylines(frame, [pts], False, color, 2, cv2.LINE_AA)

    # ─────────────────────────────────────────────────────────────────────────
    # MAIN PROCESSING
    # ─────────────────────────────────────────────────────────────────────────

    def process_frame(self, frame: np.ndarray) -> np.ndarray:
        """
        Xử lý 1 frame: detect → track → tính tốc độ → vẽ annotation.

        Chỉ tracking khi ROI đã được set.
        Chỉ nhận diện xe trong ROI (car, bus, truck).

        Args:
            frame: Frame ảnh BGR từ OpenCV.

        Returns:
            Frame đã được vẽ bounding box, ID, tốc độ.
        """
        self.current_frame += 1
        annotated = frame.copy()

        # Vẽ ROI overlay nếu đã set
        if self.roi_points is not None:
            self._draw_roi_overlay(annotated)

        # Chưa set ROI → không tracking
        if self.roi_points is None:
            return annotated

        # ── YOLO tracking với ByteTrack ──────────────────────────────────────
        results = self.model.track(
            frame,
            persist  = True,
            tracker  = BYTETRACK_CFG,
            classes  = HIGHWAY_CLASS_IDS,   # Chỉ car, bus, truck
            conf     = 0.35,                # Hạ thấp để bắt xe từ xa
            verbose  = False,
        )

        if results[0].boxes is None or results[0].boxes.id is None:
            return annotated

        boxes       = results[0].boxes.xyxy.cpu().numpy()
        track_ids   = results[0].boxes.id.int().cpu().tolist()
        class_ids   = results[0].boxes.cls.int().cpu().tolist()
        class_names = results[0].names

        # ── Xử lý từng xe được phát hiện ────────────────────────────────────
        for box, track_id, class_id in zip(boxes, track_ids, class_ids):
            cx = (box[0] + box[2]) / 2
            cy = (box[1] + box[3]) / 2
            centroid = (cx, cy)

            # Bỏ qua xe ngoài ROI (vẽ box mờ để dễ debug)
            if not self._is_inside_roi(centroid):
                x1, y1, x2, y2 = box.astype(int)
                cv2.rectangle(annotated, (x1, y1), (x2, y2), (80, 80, 80), 1)
                continue

            # Cập nhật lịch sử centroid
            self.track_history[track_id].append(centroid)

            # ── Tính tốc độ ──────────────────────────────────────────────────
            speed    = 0.0
            curr_wpt = self._transform_point(centroid)
            history  = self.track_history[track_id]

            if len(history) >= 2:
                prev_wpt = self._transform_point(history[-2])
                dx = curr_wpt[0] - prev_wpt[0]
                dy = curr_wpt[1] - prev_wpt[1]
                self._update_motion_axis(dx, dy)
                raw_speed = calculate_speed(prev_wpt, curr_wpt,
                                            self.pixel_per_meter, self.fps)
                self.speed_history[track_id].append(raw_speed)
                speed = smooth_speed(self.speed_history[track_id], window=15)
            else:
                self.speed_history[track_id].append(0.0)

            # ── Kiểm tra counting line ────────────────────────────────────────
            self._check_line_crossing(track_id, curr_wpt)
            vehicle_type = get_vehicle_class_name(class_id, class_names)

            # ── Cập nhật thông tin xe ─────────────────────────────────────────
            if track_id not in self.vehicle_info:
                self.vehicle_info[track_id] = {
                    "type":        vehicle_type,
                    "entry_frame": self.current_frame,
                    "last_frame":  self.current_frame,
                    "max_speed":   speed,
                    "counted":     track_id in self.counted_ids,
                }
            else:
                info = self.vehicle_info[track_id]
                info["last_frame"] = self.current_frame
                info["counted"]    = track_id in self.counted_ids
                if speed > info["max_speed"]:
                    info["max_speed"] = speed

            # ── Vẽ annotation ─────────────────────────────────────────────────
            self._draw_vehicle(annotated, box, track_id, vehicle_type, speed)

        # Giới hạn độ dài lịch sử centroid
        for tid in list(self.track_history):
            if len(self.track_history[tid]) > 50:
                self.track_history[tid] = self.track_history[tid][-30:]

        return annotated

    # ─────────────────────────────────────────────────────────────────────────
    # DATA ACCESSORS
    # ─────────────────────────────────────────────────────────────────────────

    def get_vehicle_log(self) -> list:
        """
        Trả về bảng log tất cả xe đã theo dõi.

        Returns:
            List[dict]: [{id, type, entry_time, exit_time, max_speed}, ...]
        """
        return [
            {
                "id":         track_id,
                "type":       info["type"],
                "entry_time": format_time(info["entry_frame"], self.fps),
                "exit_time":  format_time(info["last_frame"],  self.fps),
                "max_speed":  round(info["max_speed"], 1),
            }
            for track_id, info in sorted(self.vehicle_info.items())
        ]

    def get_statistics(self) -> dict:
        """
        Tính thống kê tổng hợp dựa trên xe đã qua counting line.

        Returns:
            Dict: {total, min_speed, max_speed, avg_speed}
        """
        total = len(self.counted_ids)
        speeds = [
            self.vehicle_info[tid]["max_speed"]
            for tid in self.counted_ids
            if tid in self.vehicle_info and self.vehicle_info[tid]["max_speed"] > 0
        ]

        if not speeds:
            return {"total": total, "min_speed": 0.0, "max_speed": 0.0, "avg_speed": 0.0}

        return {
            "total":     total,
            "min_speed": round(min(speeds), 1),
            "max_speed": round(max(speeds), 1),
            "avg_speed": round(sum(speeds) / len(speeds), 1),
        }
