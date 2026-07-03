"""
tracker.py - Module theo dõi xe và đo tốc độ.
Sử dụng YOLOv8 để phát hiện và ByteTrack để theo dõi.
"""

from collections import defaultdict

import cv2
import numpy as np
from ultralytics import YOLO

from utils import calculate_speed, format_time, get_vehicle_class_name, smooth_speed


class VehicleTracker:
    """
    Quản lý phát hiện, theo dõi xe và đo tốc độ từ video.

    Attributes:
        model: Model YOLOv8 đã load.
        pixel_per_meter: Tỉ lệ pixel/mét để tính tốc độ thực.
        fps: FPS của video.
        track_history: Lịch sử centroid cho mỗi xe {track_id: [(x,y), ...]}.
        speed_history: Lịch sử tốc độ cho mỗi xe {track_id: [speed1, speed2, ...]}.
        vehicle_info: Thông tin tổng hợp cho mỗi xe
                      {track_id: {type, entry_frame, last_frame, max_speed}}.
        current_frame: Số frame hiện tại đang xử lý.
    """

    # Các class ID của phương tiện giao thông trong COCO dataset
    VEHICLE_CLASS_IDS = {1, 2, 3, 5, 7}  # bicycle, car, motorcycle, bus, truck

    def __init__(self, model_path: str, pixel_per_meter: float = 8.0, fps: float = 30.0):
        """
        Khởi tạo VehicleTracker.

        Args:
            model_path: Đường dẫn tới file model YOLO (.pt).
            pixel_per_meter: Số pixel = 1 mét (mặc định 8.0).
            fps: FPS của video (mặc định 30.0).
        """
        self.model = YOLO(model_path)
        self.pixel_per_meter = pixel_per_meter
        self.fps = fps

        # Lịch sử tracking
        self.track_history = defaultdict(list)      # {id: [(x,y), ...]}
        self.speed_history = defaultdict(list)       # {id: [speed, ...]}
        self.vehicle_info = {}                       # {id: {type, entry_frame, ...}}
        self.current_frame = 0

        # ROI / Perspective Transform
        self.roi_points = None            # 4 điểm gốc (tọa độ frame)
        self.perspective_matrix = None    # Ma trận biến đổi M
        self.dst_width = 400              # Chiều rộng vùng trải phẳng (px)
        self.dst_height = 600             # Chiều cao vùng trải phẳng (px)

        # Counting Line — đếm xe khi cắt ngang vạch
        self.counting_line_pos  = 0.5          # Vị trí vạch (0−1) trên trục chính
        self.counting_line_axis = 'y'          # 'x' hoặc 'y' — tự động xác định
        self._axis_locked       = False        # True sau khi đã xác định hướng
        self._motion_vectors    = []           # Tích luĩ (dx,dy) trong warped space
        self.counted_ids        = set()        # Track ID đã được đếm
        self.line_side          = {}           # {id: side} phía vạch frame trước

    def reset(self):
        """Xóa toàn bộ dữ liệu tracking, reset về trạng thái ban đầu."""
        self.track_history.clear()
        self.speed_history.clear()
        self.vehicle_info.clear()
        self.counted_ids.clear()
        self.line_side.clear()
        self._motion_vectors.clear()
        self._axis_locked = False
        self.counting_line_axis = 'y'
        self.current_frame = 0
        # Reset model tracker state
        self.model.predictor = None
        # Giữ nguyên ROI khi reset tracking (người dùng đã chọn vùng)

    # ─────────────────────────────────────────────────────────────────────
    # ROI / PERSPECTIVE TRANSFORM
    # ─────────────────────────────────────────────────────────────────────
    def set_roi(self, points):
        """
        Thiết lập vùng ROI 4 điểm và tính ma trận perspective transform.
        Dùng thứ tự click trực tiếp: P1→TL, P2→TR, P3→BR, P4→BL.

        Args:
            points: List 4 điểm theo thứ tự click của người dùng.
        """
        if len(points) != 4:
            return

        # Dùng thứ tự click trực tiếp (không sắp xếp lại)
        src_pts = np.array(points, dtype=np.float32)
        self.roi_points = src_pts

        # Hình chữ nhật đích (bird's eye view)
        dst_pts = np.array([
            [0, 0],
            [self.dst_width - 1, 0],
            [self.dst_width - 1, self.dst_height - 1],
            [0, self.dst_height - 1],
        ], dtype=np.float32)

        # Tính ma trận biến đổi phối cảnh
        self.perspective_matrix = cv2.getPerspectiveTransform(src_pts, dst_pts)
        print(f"[ROI]  Perspective matrix computed. src={src_pts.tolist()}")

    def clear_roi(self):
        """Xóa ROI và ma trận perspective."""
        self.roi_points = None
        self.perspective_matrix = None
        # Reset đếm khi xóa ROI
        self.counted_ids.clear()
        self.line_side.clear()
        self.track_history.clear()
        self.speed_history.clear()
        self.vehicle_info.clear()
        self._motion_vectors.clear()
        self._axis_locked = False
        self.counting_line_axis = 'y'
        print("[ROI]  ROI cleared.")

    def _update_motion_axis(self, dx, dy):
        """
        Tích lũy vector chuyển động và tự động xác định trục chính.
        Gọi sau khi có đủ 60 điểm dữ liệu.
        """
        if self._axis_locked:
            return
        threshold = 1.0  # Bỏ qua vector quá nhỏ
        if abs(dx) > threshold or abs(dy) > threshold:
            self._motion_vectors.append((abs(dx), abs(dy)))

        if len(self._motion_vectors) >= 60:
            total_dx = sum(v[0] for v in self._motion_vectors)
            total_dy = sum(v[1] for v in self._motion_vectors)
            # Trục có tổng chuyển động lớn hơn = hướng chạy chính
            # Vạch đếm vuông góc với hướng chạy
            if total_dx >= total_dy:
                # Xe chạy chủ yếu theo trục X → vạch đứng (trục X)
                self.counting_line_axis = 'x'
                print(f"[ROI]  Auto-detected: vehicles move HORIZONTALLY → "
                      f"vertical counting line at x=50% (dx_total={total_dx:.0f}, dy_total={total_dy:.0f})")
            else:
                # Xe chạy chủ yếu theo trục Y → vạch ngang (trục Y)
                self.counting_line_axis = 'y'
                print(f"[ROI]  Auto-detected: vehicles move VERTICALLY → "
                      f"horizontal counting line at y=50% (dx_total={total_dx:.0f}, dy_total={total_dy:.0f})")
            self._axis_locked = True

    def _transform_point(self, point):
        """
        Chuyển đổi 1 điểm qua perspective matrix.

        Args:
            point: Tuple (x, y).

        Returns:
            Tuple (x', y') trong tọa độ trải phẳng.
        """
        if self.perspective_matrix is None:
            return point
        pt = np.array([[[point[0], point[1]]]], dtype=np.float32)
        transformed = cv2.perspectiveTransform(pt, self.perspective_matrix)
        return (float(transformed[0][0][0]), float(transformed[0][0][1]))

    def _is_inside_roi(self, point):
        """
        Kiểm tra 1 điểm có nằm trong vùng ROI hay không.

        Args:
            point: Tuple (x, y) — centroid.

        Returns:
            True nếu nằm trong hoặc trên biên ROI.
        """
        if self.roi_points is None:
            return False
        contour = self.roi_points.astype(np.float32)
        result = cv2.pointPolygonTest(contour, (float(point[0]), float(point[1])), False)
        return result >= 0  # >= 0: bên trong hoặc trên biên

    def _check_line_crossing(self, track_id, transformed_point):
        """
        Kiểm tra xe có vượt qua counting line không.
        Hướng vạch phụ thuộc vào counting_line_axis ('x' hoặc 'y').
        """
        if track_id in self.counted_ids:
            return False

        if self.counting_line_axis == 'x':
            # Vạch đứng: so sánh theo trục X
            pos = transformed_point[0]
            line_pos = self.counting_line_pos * self.dst_width
            current_side = 'left' if pos < line_pos else 'right'
        else:
            # Vạch ngang: so sánh theo trục Y
            pos = transformed_point[1]
            line_pos = self.counting_line_pos * self.dst_height
            current_side = 'above' if pos < line_pos else 'below'

        if track_id not in self.line_side:
            self.line_side[track_id] = current_side
            return False

        prev_side = self.line_side[track_id]
        self.line_side[track_id] = current_side

        if prev_side != current_side:
            self.counted_ids.add(track_id)
            return True

        return False

    def update_config(self, pixel_per_meter: float = None, fps: float = None):
        """
        Cập nhật cấu hình tracker.

        Args:
            pixel_per_meter: Tỉ lệ pixel/mét mới (None = giữ nguyên).
            fps: FPS mới (None = giữ nguyên).
        """
        if pixel_per_meter is not None:
            self.pixel_per_meter = pixel_per_meter
        if fps is not None:
            self.fps = fps

    def process_frame(self, frame: np.ndarray) -> np.ndarray:
        """
        Xử lý 1 frame: detect → track → tính tốc độ → vẽ annotation.
        Chỉ đếm/tracking khi ROI đã được set, và chỉ xe trong ROI.

        Args:
            frame: Frame ảnh BGR từ OpenCV.

        Returns:
            Frame đã được vẽ bounding box, ID, tốc độ.
        """
        self.current_frame += 1
        annotated_frame = frame.copy()

        # Vẽ ROI polygon lên frame nếu đã set
        if self.roi_points is not None:
            roi_int = self.roi_points.astype(np.int32)
            overlay = annotated_frame.copy()
            cv2.fillPoly(overlay, [roi_int], (0, 180, 255))
            cv2.addWeighted(overlay, 0.15, annotated_frame, 0.85, 0, annotated_frame)
            cv2.polylines(annotated_frame, [roi_int], True, (0, 180, 255), 2, cv2.LINE_AA)
            for i, pt in enumerate(roi_int):
                cv2.circle(annotated_frame, tuple(pt), 6, (0, 255, 255), -1, cv2.LINE_AA)
                cv2.putText(annotated_frame, str(i + 1), (pt[0] + 8, pt[1] - 8),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 255), 1, cv2.LINE_AA)

            # Vẽ counting line trong không gian gốc (inverse transform)
            if self.perspective_matrix is not None:
                inv_M = np.linalg.inv(self.perspective_matrix)
                # Chuyển 2 điểm đầu/cuối của counting line về frame gốc
                p = self.counting_line_pos
                if self.counting_line_axis == 'x':
                    # Vạch đứng trong warped: x = p*dst_width
                    lx = p * (self.dst_width - 1)
                    pts_dst = np.array([[[lx, 0]],
                                        [[lx, self.dst_height - 1]]], dtype=np.float32)
                else:
                    # Vạch ngang trong warped: y = p*dst_height
                    ly = p * (self.dst_height - 1)
                    pts_dst = np.array([[[0, ly]],
                                        [[self.dst_width - 1, ly]]], dtype=np.float32)
                pts_src = cv2.perspectiveTransform(pts_dst, inv_M)
                lp0 = tuple(pts_src[0][0].astype(int))
                lp1 = tuple(pts_src[1][0].astype(int))
                # Vẽ đường đứt (dashed)
                total_len = int(np.linalg.norm(
                    np.array(lp1, dtype=float) - np.array(lp0, dtype=float)))
                num_dashes = max(1, total_len // 20)
                for seg in range(num_dashes):
                    t0 = seg / num_dashes
                    t1 = (seg + 0.5) / num_dashes
                    p0 = (int(lp0[0] + t0 * (lp1[0] - lp0[0])),
                          int(lp0[1] + t0 * (lp1[1] - lp0[1])))
                    p1 = (int(lp0[0] + t1 * (lp1[0] - lp0[0])),
                          int(lp0[1] + t1 * (lp1[1] - lp0[1])))
                    cv2.line(annotated_frame, p0, p1, (0, 255, 0), 2, cv2.LINE_AA)
                # Label
                mid = ((lp0[0] + lp1[0]) // 2, (lp0[1] + lp1[1]) // 2)
                status = "" if self._axis_locked else " (calibrating...)"
                cv2.putText(annotated_frame,
                            f"COUNT: {len(self.counted_ids)}{status}",
                            (mid[0] + 6, mid[1] - 6),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0, 255, 0), 2, cv2.LINE_AA)

        # --- Nếu chưa set ROI → không tracking, chỉ trả frame gốc + ROI overlay ---
        if self.roi_points is None:
            return annotated_frame

        # --- 1. Chạy YOLO tracking với ByteTrack ---
        results = self.model.track(
            frame,
            persist=True,
            tracker="bytetrack.yaml",
            verbose=False,
            conf=0.4,
        )

        # Kiểm tra có kết quả tracking không
        if results[0].boxes is None or results[0].boxes.id is None:
            return annotated_frame

        # Lấy dữ liệu detection
        boxes = results[0].boxes.xyxy.cpu().numpy()
        track_ids = results[0].boxes.id.int().cpu().tolist()
        class_ids = results[0].boxes.cls.int().cpu().tolist()
        confidences = results[0].boxes.conf.cpu().tolist()
        class_names = results[0].names

        # --- 2. Xử lý từng xe detected ---
        for box, track_id, class_id, conf in zip(boxes, track_ids, class_ids, confidences):
            x1, y1, x2, y2 = box.astype(int)

            # Tính centroid (tâm) của bounding box
            cx = (x1 + x2) / 2
            cy = (y1 + y2) / 2
            centroid = (cx, cy)

            # --- Kiểm tra centroid có nằm trong ROI không ---
            if not self._is_inside_roi(centroid):
                # Xe ngoài ROI: vẽ box mờ, không đếm/tracking
                cv2.rectangle(annotated_frame, (x1, y1), (x2, y2),
                              (80, 80, 80), 1)
                continue

            # Lưu centroid vào lịch sử
            self.track_history[track_id].append(centroid)

            # --- 3. Tính tốc độ và cập nhật hướng chuyển động ---
            speed = 0.0
            curr_t = self._transform_point(centroid)
            if len(self.track_history[track_id]) >= 2:
                prev_centroid = self.track_history[track_id][-2]
                prev_t = self._transform_point(prev_centroid)
                dx_t = curr_t[0] - prev_t[0]
                dy_t = curr_t[1] - prev_t[1]
                # Tích lũy vector để xác định trục
                self._update_motion_axis(dx_t, dy_t)
                raw_speed = calculate_speed(
                    prev_t, curr_t, self.pixel_per_meter, self.fps
                )
                self.speed_history[track_id].append(raw_speed)
                speed = smooth_speed(self.speed_history[track_id], window=15)
            else:
                self.speed_history[track_id].append(0.0)

            # --- 4. Kiểm tra counting line & cập nhật thông tin xe ---
            crossed = self._check_line_crossing(track_id, curr_t)
            vehicle_type = get_vehicle_class_name(class_id, class_names)

            if track_id not in self.vehicle_info:
                self.vehicle_info[track_id] = {
                    "type": vehicle_type,
                    "entry_frame": self.current_frame,
                    "last_frame": self.current_frame,
                    "max_speed": speed,
                    "class_id": class_id,
                    "counted": track_id in self.counted_ids,
                }
            else:
                self.vehicle_info[track_id]["last_frame"] = self.current_frame
                self.vehicle_info[track_id]["counted"] = track_id in self.counted_ids
                if speed > self.vehicle_info[track_id]["max_speed"]:
                    self.vehicle_info[track_id]["max_speed"] = speed

            # --- 5. Vẽ annotation lên frame ---
            color = self._get_color(track_id)
            # Vạch sáng hơn nếu xe đã được đếm
            box_thickness = 3 if track_id in self.counted_ids else 2
            cv2.rectangle(annotated_frame, (x1, y1), (x2, y2), color, box_thickness)
            if track_id in self.counted_ids:
                # Đấu tich nhỏ bên góc phải bên trên
                cv2.circle(annotated_frame, (x2 - 6, y1 + 6), 5, (0, 255, 0), -1)

            label = f"ID:{track_id} {vehicle_type}"
            speed_label = f"{speed:.1f} km/h"

            (tw, th), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.6, 1)
            cv2.rectangle(
                annotated_frame,
                (x1, y1 - th - 10),
                (x1 + tw + 4, y1),
                color, -1,
            )
            cv2.putText(
                annotated_frame, label,
                (x1 + 2, y1 - 5),
                cv2.FONT_HERSHEY_SIMPLEX, 0.6,
                (255, 255, 255), 1, cv2.LINE_AA,
            )

            (sw, sh), _ = cv2.getTextSize(speed_label, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 1)
            cv2.rectangle(
                annotated_frame,
                (x1, y2),
                (x1 + sw + 4, y2 + sh + 8),
                (0, 0, 0), -1,
            )
            cv2.putText(
                annotated_frame, speed_label,
                (x1 + 2, y2 + sh + 4),
                cv2.FONT_HERSHEY_SIMPLEX, 0.5,
                (0, 255, 255), 1, cv2.LINE_AA,
            )

            # Vẽ đường đi (trail) của xe
            track = self.track_history[track_id]
            if len(track) > 1:
                points = np.array(track[-20:], dtype=np.int32).reshape((-1, 1, 2))
                cv2.polylines(
                    annotated_frame, [points], False, color, 2, cv2.LINE_AA
                )

        # Giới hạn lịch sử centroid
        for tid in list(self.track_history.keys()):
            if len(self.track_history[tid]) > 50:
                self.track_history[tid] = self.track_history[tid][-30:]

        return annotated_frame

    def get_vehicle_log(self) -> list:
        """
        Tạo bảng log tất cả các xe đã theo dõi.

        Returns:
            List of dicts: [{id, type, entry_time, exit_time, max_speed}, ...]
        """
        log = []
        for track_id, info in sorted(self.vehicle_info.items()):
            log.append({
                "id": track_id,
                "type": info["type"],
                "entry_time": format_time(info["entry_frame"], self.fps),
                "exit_time": format_time(info["last_frame"], self.fps),
                "max_speed": round(info["max_speed"], 1),
            })
        return log

    def get_statistics(self) -> dict:
        """
        Tính thống kê tổng hợp.
        Tổng xe = số xe đã vượt qua counting line (counted_ids).
        """
        # Tổng xe dùng counted_ids (chính xác, không bị double count)
        total_counted = len(self.counted_ids)

        # Tốc độ lấy từ các xe đã được đếm
        counted_speeds = [
            self.vehicle_info[tid]["max_speed"]
            for tid in self.counted_ids
            if tid in self.vehicle_info and self.vehicle_info[tid]["max_speed"] > 0
        ]

        if not counted_speeds:
            return {
                "total": total_counted,
                "min_speed": 0.0,
                "max_speed": 0.0,
                "avg_speed": 0.0,
            }

        return {
            "total": total_counted,
            "min_speed": round(min(counted_speeds), 1),
            "max_speed": round(max(counted_speeds), 1),
            "avg_speed": round(sum(counted_speeds) / len(counted_speeds), 1),
        }

    @staticmethod
    def _get_color(track_id: int) -> tuple:
        """
        Tạo màu khác nhau cho mỗi track ID (dùng HSV → BGR).

        Args:
            track_id: ID của track.

        Returns:
            Tuple BGR color.
        """
        hue = (track_id * 47) % 180  # Phân bố đều trên vòng tròn HSV
        color_hsv = np.array([[[hue, 255, 220]]], dtype=np.uint8)
        color_bgr = cv2.cvtColor(color_hsv, cv2.COLOR_HSV2BGR)[0][0]
        return (int(color_bgr[0]), int(color_bgr[1]), int(color_bgr[2]))
