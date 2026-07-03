"""
ui/dashboard.py — Analysis dashboard (OpenCV window).

Hiển thị video, thống kê tốc độ, log xe và cho phép vẽ ROI.
Phím: P=Pause/Resume  Q=Thoát. Tất cả chức năng khác dùng nút bấm trên màn hình.
"""

import os
import time
from datetime import datetime

import cv2
import numpy as np

from core.tracker import VehicleTracker
from core.utils import export_to_excel
from ui.theme import (
    WIN_W, WIN_H, HEADER_H, STATUSBAR_H, VIDEO_W, STAT_X, STAT_W, CONTENT_H,
    _SX, _SY,
    BG, HDR, PANEL, DIV, TXT, DIM, LBL, AMBER, GREEN, YELLOW, RED, TEAL,
    CYAN, ROI_CLR, ALT_ROW,
    FONT, FONTD,
    fillr, bordr, hline, vline, put, put_right, put_center, get_text_width
)

MODEL_PATH = "config/yolo26n.pt"
REPORT_DIR = "report"
WIN_NAME   = "VEHICLE ANALYSIS SYSTEM"


# ─────────────────────────────────────────────────────────────────────────────
# UTILITIES
# ─────────────────────────────────────────────────────────────────────────────

def _ensure_dir(path: str) -> None:
    os.makedirs(path, exist_ok=True)


def _get_report_path() -> str:
    _ensure_dir(REPORT_DIR)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    return os.path.join(REPORT_DIR, f"vehicle_report_{ts}.xlsx")


def _do_export(tracker: VehicleTracker) -> None:
    log   = tracker.get_vehicle_log()
    stats = tracker.get_statistics()
    if not log:
        print("[WARN] No vehicle data to export yet. Hãy đợi xe đi qua hoặc thoát khỏi ROI.")
        return
    try:
        data = export_to_excel(log, stats)
        path = _get_report_path()
        with open(path, "wb") as f:
            f.write(data)
        print(f"[OK]   Report saved → {os.path.abspath(path)}")
    except Exception as exc:
        import traceback
        print(f"[ERR]  Export failed: {exc}")
        traceback.print_exc()


# ─────────────────────────────────────────────────────────────────────────────
# COORDINATE TRANSFORM (canvas ↔ frame)
# ─────────────────────────────────────────────────────────────────────────────

def _get_video_transform(frame: np.ndarray) -> tuple:
    """Tính scale và offset để hiển thị frame lên canvas video panel."""
    if frame is None:
        return 1.0, 0, HEADER_H, VIDEO_W, CONTENT_H
    fh, fw = frame.shape[:2]
    scale  = min(VIDEO_W / fw, CONTENT_H / fh)
    nw, nh = int(fw * scale), int(fh * scale)
    ox     = (VIDEO_W - nw) // 2
    oy     = HEADER_H + (CONTENT_H - nh) // 2
    return scale, ox, oy, nw, nh


def _canvas_to_frame(cx: int, cy: int, scale: float, ox: int, oy: int) -> tuple:
    """Chuyển tọa độ click trên canvas → tọa độ frame gốc."""
    return (cx - ox) / scale, (cy - oy) / scale


def _frame_to_canvas(fx: float, fy: float, scale: float, ox: int, oy: int) -> tuple:
    """Chuyển tọa độ frame gốc → tọa độ canvas."""
    return int(fx * scale + ox), int(fy * scale + oy)


# ─────────────────────────────────────────────────────────────────────────────
# PANEL RENDERERS
# ─────────────────────────────────────────────────────────────────────────────

def _draw_header(canvas: np.ndarray, video_name: str, is_paused: bool) -> None:
    # Tọa độ Y tâm chữ trong header
    ty = int(HEADER_H * 0.68)
    fillr(canvas, 0, 0, WIN_W, HEADER_H, HDR)
    hline(canvas, 0, WIN_W, HEADER_H, AMBER, 2)
    put(canvas, "VEHICLE ANALYSIS SYSTEM", 20, ty, TXT, 0.65, 1, FONTD)

    dot_color   = YELLOW if is_paused else GREEN
    status_text = "PAUSED" if is_paused else "LIVE"
    dot_x = int(520 * _SX)
    put(canvas, "●",         dot_x,       ty, dot_color, 0.60)
    put(canvas, status_text, dot_x + 28,  ty, dot_color, 0.45)

    bname = os.path.basename(video_name)
    if len(bname) > 50:
        bname = bname[:48] + ".."
    put_right(canvas, bname, WIN_W - 20, ty, DIM, 0.45)


def _draw_video_panel(canvas: np.ndarray, frame, roi_mode: bool,
                      roi_mode_points: list,
                      roi_confirmed: bool = False,
                      roi_points_confirmed: list = None) -> None:
    """
    Vẽ panel video bên trái và overlay ROI.
    - roi_mode=True: đang click chọn điểm → hiện điểm + banner hướng dẫn
    - roi_confirmed=True + roi_mode=False: ROI đã xác nhận → hiện polygon xanh
    """
    fillr(canvas, 0, HEADER_H, VIDEO_W, HEADER_H + CONTENT_H, BG)

    if frame is None:
        put_center(canvas, "No frame", VIDEO_W // 2, HEADER_H + CONTENT_H // 2,
                   DIM, 0.55)
        return

    scale, ox, oy, nw, nh = _get_video_transform(frame)
    resized = cv2.resize(frame, (nw, nh), interpolation=cv2.INTER_LINEAR)
    canvas[oy:oy + nh, ox:ox + nw] = resized

    # ── Đang vẽ ROI (roi_mode=True): hiện các điểm đang chọn ────────────────
    if roi_mode and roi_mode_points:
        pts_c = [_frame_to_canvas(p[0], p[1], scale, ox, oy)
                 for p in roi_mode_points]
        for i, pt in enumerate(pts_c):
            cv2.circle(canvas, pt, 7, CYAN, -1, cv2.LINE_AA)
            cv2.circle(canvas, pt, 9, ROI_CLR, 2, cv2.LINE_AA)
            put(canvas, str(i + 1), pt[0] + 12, pt[1] - 6, CYAN, 0.50, 1)
            if i > 0:
                cv2.line(canvas, pts_c[i - 1], pts_c[i], ROI_CLR, 2, cv2.LINE_AA)
        if len(pts_c) == 4:
            cv2.line(canvas, pts_c[3], pts_c[0], ROI_CLR, 2, cv2.LINE_AA)

    # ── ROI đã xác nhận: hiện polygon màu xanh lá bán trong suốt ─────────────
    if roi_confirmed and not roi_mode and roi_points_confirmed and len(roi_points_confirmed) == 4:
        pts_c = [_frame_to_canvas(p[0], p[1], scale, ox, oy)
                 for p in roi_points_confirmed]
        pts_arr = np.array(pts_c, dtype=np.int32)

        # Overlay bán trong suốt
        overlay = canvas.copy()
        cv2.fillPoly(overlay, [pts_arr], (0, 60, 0))
        cv2.addWeighted(overlay, 0.25, canvas, 0.75, 0, canvas)

        # Vẽ đường viền
        cv2.polylines(canvas, [pts_arr], isClosed=True, color=ROI_CLR,
                      thickness=2, lineType=cv2.LINE_AA)
        # Vẽ các góc
        labels = ["TL", "TR", "BR", "BL"]
        for i, pt in enumerate(pts_c):
            cv2.circle(canvas, pt, 5, CYAN, -1, cv2.LINE_AA)
            put(canvas, labels[i], pt[0] + 8, pt[1] - 4, CYAN, 0.40, 1)

        # Badge xác nhận
        badge = "  ROI ✓ — Nhấn Resume để tiếp tục  "
        tw = get_text_width(badge, 0.50, 1)
        bx = VIDEO_W // 2
        banner_y1 = HEADER_H + 8
        banner_y2 = banner_y1 + int(32 * _SY)
        fillr(canvas, bx - tw // 2 - 12, banner_y1,
                      bx + tw // 2 + 12, banner_y2, (0, 80, 0))
        put_center(canvas, badge, bx, banner_y1 + int(24 * _SY), ROI_CLR, 0.50, 1)

    # ── Banner hướng dẫn khi đang chọn điểm ─────────────────────────────────
    if roi_mode:
        n   = len(roi_mode_points) if roi_mode_points else 0
        msg = (f"  ROI MODE — Click điểm {n + 1}/4 (TL→TR→BR→BL)  "
               if n < 4 else "  ROI SET — Nhấn [C] để xóa  ")
        tw  = get_text_width(msg, 0.55, 1)
        bx  = VIDEO_W // 2
        banner_y1 = HEADER_H + 8
        banner_y2 = banner_y1 + int(32 * _SY)
        fillr(canvas, bx - tw // 2 - 12, banner_y1,
                      bx + tw // 2 + 12, banner_y2, (0, 60, 120))
        put_center(canvas, msg, bx, banner_y1 + int(24 * _SY), CYAN, 0.55, 1)


def _draw_stat_panel(canvas: np.ndarray, stats: dict, vehicle_log: list,
                     log_scroll: int = 0) -> None:
    """Vẽ panel thống kê và log xe bên phải (scale theo màn hình)."""
    SX, SW = STAT_X, STAT_W
    # Padding scale theo _SX
    PAD    = max(10, int(18 * _SX))
    PX     = SX + PAD
    PW     = SW - PAD * 2

    fillr(canvas, SX, HEADER_H, WIN_W, HEADER_H + CONTENT_H, PANEL)
    vline(canvas, SX, HEADER_H, HEADER_H + CONTENT_H, DIV)

    py = HEADER_H + max(8, int(16 * _SY))

    # Chiều cao các box scale theo _SY
    BOX_H  = max(60, int(120 * _SY))
    BOX_SP = max(8,  int(10  * _SY))   # khoảng cách giữa box và py tiếp theo
    ty1    = max(18, int(30  * _SY))   # offset dòng label trong box
    ty2    = max(BOX_H - 12, int((BOX_H - 10) * 1.0))  # offset dòng giá trị

    # ── Tổng xe ──────────────────────────────────────────────────────────────
    total = stats.get("total", 0)
    fillr(canvas, PX, py, PX + PW, py + BOX_H, HDR)
    put(canvas, "Total Vehicles", PX + 16, py + ty1, LBL, 0.50)
    put(canvas, str(total),       PX + 16, py + ty2, AMBER, 1.20, 2, FONTD)
    py += BOX_H + BOX_SP

    # ── Lưới tốc độ 1×3 ──────────────────────────────────────────────────────
    gap   = max(4, int(8 * _SX))
    third = (PW - gap * 2) // 3
    cells = [
        ("Avg Speed", f"{stats.get('avg_speed', 0):.1f}", "km/h", TXT),
        ("Max Speed", f"{stats.get('max_speed', 0):.1f}", "km/h", RED),
        ("Min Speed", f"{stats.get('min_speed', 0):.1f}", "km/h", GREEN),
    ]
    v_mid  = int(BOX_H * 0.70)   # y offset cho giá trị
    v_unit = int(BOX_H * 0.90)   # y offset cho unit
    for i, (label, value, unit, val_color) in enumerate(cells):
        gx = PX + i * (third + gap)
        fillr(canvas, gx, py, gx + third, py + BOX_H, HDR)
        put(canvas, label, gx + 8, py + ty1,   LBL,       0.43)
        put(canvas, value, gx + 8, py + v_mid,  val_color, 0.80, 2, FONTD)
        put(canvas, unit,  gx + 8, py + v_unit, DIM,       0.38)
    py += BOX_H + BOX_SP

    # ── Vehicle Log ───────────────────────────────────────────────────────────
    log_label_h = max(30, int(50 * _SY))
    put(canvas, "VEHICLE LOG", PX, py + int(log_label_h * 0.70), LBL, 0.55)
    hline(canvas, PX, SX + SW - 20, py + log_label_h, DIV)
    py += log_label_h + max(4, int(8 * _SY))

    # Header row
    HDR_ROW_H = max(28, int(40 * _SY))
    fillr(canvas, PX, py, PX + PW, py + HDR_ROW_H, HDR)
    # Cột scale theo _SX (thiết kế gốc cho STAT_W ≈ 768px)
    col_ratio = PW / 710.0   # 710 = tổng width gốc (cột cuối cùng tại x=700)
    col_x = [int(x * col_ratio) for x in [10, 80, 240, 420, 600]]
    col_labels = ["ID", "TYPE", "ENTRY", "EXIT", "SPD"]
    for col_label, cx in zip(col_labels, col_x):
        put(canvas, col_label, PX + cx, py + int(HDR_ROW_H * 0.72), DIM, 0.43)
    hline(canvas, PX, PX + PW, py + HDR_ROW_H, DIV)
    py += HDR_ROW_H

    ROW_H        = max(32, int(44 * _SY))
    panel_bottom = HEADER_H + CONTENT_H - 6
    max_rows     = max(0, (panel_bottom - py) // ROW_H)

    # Áp dụng scroll: log_scroll=0 → hiển thị mới nhất (reversed)
    total_log    = len(vehicle_log)
    reversed_log = list(reversed(vehicle_log)) if vehicle_log else []
    max_scroll   = max(0, total_log - max_rows)
    log_scroll   = max(0, min(log_scroll, max_scroll))
    display_log  = reversed_log[log_scroll: log_scroll + max_rows]

    row_ty = int(ROW_H * 0.70)   # y-offset chữ trong row
    for i, entry in enumerate(display_log):
        ry = py + i * ROW_H
        if ry + ROW_H > panel_bottom:
            break
        if i % 2 == 0:
            fillr(canvas, PX, ry, PX + PW, ry + ROW_H, ALT_ROW)
        spd       = entry.get("max_speed", 0.0)
        spd_color = RED if spd > 100 else YELLOW if spd > 60 else GREEN
        put(canvas, str(entry.get("id", "?")),          PX + col_x[0], ry + row_ty, TEAL,      0.46)
        put(canvas, str(entry.get("type", "?"))[:10],   PX + col_x[1], ry + row_ty, TXT,       0.46)
        put(canvas, str(entry.get("entry_time", "--")), PX + col_x[2], ry + row_ty, DIM,       0.43)
        put(canvas, str(entry.get("exit_time",  "--")), PX + col_x[3], ry + row_ty, DIM,       0.43)
        put(canvas, f"{spd:.1f}",                       PX + col_x[4], ry + row_ty, spd_color, 0.46)

    # Scrollbar indicator
    if total_log > max_rows and max_scroll > 0:
        sb_x  = SX + SW - max(6, int(6 * _SX))
        sb_y1 = py
        sb_y2 = panel_bottom
        sb_h  = sb_y2 - sb_y1
        thumb_h = max(16, int(sb_h * max_rows / total_log))
        thumb_y = sb_y1 + int((sb_h - thumb_h) * log_scroll / max_scroll)
        fillr(canvas, sb_x, sb_y1, sb_x + 4, sb_y2, (50, 50, 60))
        fillr(canvas, sb_x, thumb_y, sb_x + 4, thumb_y + thumb_h, AMBER)

    hline(canvas, SX, WIN_W, HEADER_H + CONTENT_H, DIV)


def _draw_statusbar(canvas: np.ndarray, frame_num: int, total_frames: int,
                    fps_real: float, roi_active: bool, is_paused: bool) -> list:
    """Vẽ thanh trạng thái dưới cùng và các nút chức năng (scale theo màn hình)."""
    SY = WIN_H - STATUSBAR_H
    fillr(canvas, 0, SY, WIN_W, WIN_H, HDR)
    hline(canvas, 0, WIN_W, SY, DIV)

    # Tọa độ Y tâm chữ trong statusbar
    ty = SY + int(STATUSBAR_H * 0.62)

    pct = frame_num / total_frames * 100 if total_frames > 0 else 0.0
    put(canvas, f"Frame {frame_num:,} / {total_frames:,}  {pct:.1f}%",
        20, ty, TXT, 0.43)

    # Progress bar (scale theo _SX)
    BAR_X1 = int(360 * _SX)
    BAR_X2 = int(580 * _SX)
    BAR_H  = max(5, int(8 * _SY))
    BAR_Y  = SY + (STATUSBAR_H - BAR_H) // 2
    fillr(canvas, BAR_X1, BAR_Y, BAR_X2, BAR_Y + BAR_H, DIV)
    fill_w = int((BAR_X2 - BAR_X1) * min(pct / 100.0, 1.0))
    if fill_w > 0:
        fillr(canvas, BAR_X1, BAR_Y, BAR_X1 + fill_w, BAR_Y + BAR_H, AMBER)

    fps_x = BAR_X2 + max(12, int(20 * _SX))
    put(canvas, f"FPS {fps_real:.1f}", fps_x, ty, GREEN, 0.43)

    if roi_active:
        roi_x = fps_x + max(70, int(90 * _SX))
        put(canvas, "ROI ✓", roi_x, ty, CYAN, 0.43)

    # Nút bấm — chiều cao scale theo _SY
    buttons = []
    actions = [
        ("pause",     "Resume" if is_paused else "Pause"),
        ("draw_roi",  "Vẽ ROI"),
        ("clear_roi", "Xóa ROI"),
        ("reselect",  "Chọn lại"),
        ("export",    "Export"),
        ("quit",      "Thoát")
    ]

    BTN_H   = max(28, int(44 * _SY))
    BTN_PAD = max(16, int(28 * _SX))   # padding ngang trong nút
    BTN_GAP = max(6,  int(10 * _SX))   # khoảng cách giữa các nút
    by      = SY + (STATUSBAR_H - BTN_H) // 2
    bx      = WIN_W - max(10, int(16 * _SX))

    for act, label in reversed(actions):
        tw = get_text_width(label, 0.43, 1)
        bw = tw + BTN_PAD
        bx -= bw

        fillr(canvas, bx, by, bx + bw, by + BTN_H, PANEL)
        bordr(canvas, bx, by, bx + bw, by + BTN_H, DIV)
        put_center(canvas, label, bx + bw // 2, by + int(BTN_H * 0.68), TXT, 0.43)
        buttons.append({"action": act, "rect": (bx, by, bx + bw, by + BTN_H)})
        bx -= BTN_GAP

    return buttons


# ─────────────────────────────────────────────────────────────────────────────
# MAIN BUILDER
# ─────────────────────────────────────────────────────────────────────────────

def build_dashboard(ann_frame, stats: dict, vehicle_log: list,
                    frame_num: int, total_frames: int, fps_real: float,
                    is_paused: bool, video_name: str,
                    roi_mode: bool = False, roi_mode_points: list = None,
                    roi_active: bool = False, log_scroll: int = 0,
                    roi_points_confirmed: list = None) -> tuple:
    """Tổng hợp toàn bộ dashboard vào 1 canvas và trả về (canvas, buttons)."""
    canvas = np.zeros((WIN_H, WIN_W, 3), dtype=np.uint8)
    _draw_header(canvas, video_name, is_paused)
    _draw_video_panel(
        canvas, ann_frame, roi_mode, roi_mode_points or [],
        roi_confirmed=roi_active,
        roi_points_confirmed=roi_points_confirmed,
    )
    _draw_stat_panel(canvas, stats, vehicle_log, log_scroll)
    buttons = _draw_statusbar(canvas, frame_num, total_frames, fps_real, roi_active, is_paused)
    return canvas, buttons


# ─────────────────────────────────────────────────────────────────────────────
# MOUSE STATE
# ─────────────────────────────────────────────────────────────────────────────

class _MouseState:
    def __init__(self):
        self.x = self.y = 0
        self.clicked = False
        self.scroll_delta = 0   # +1 = lăn lên, -1 = lăn xuống


def _mouse_cb(event, x, y, flags, state: _MouseState):
    state.x, state.y = x, y
    if event == cv2.EVENT_LBUTTONDOWN:
        state.clicked = True
    elif event == cv2.EVENT_MOUSEWHEEL:
        # flags > 0: lăn lên (cuộn log lên), < 0: lăn xuống
        state.scroll_delta += 1 if flags > 0 else -1


# ─────────────────────────────────────────────────────────────────────────────
# DASHBOARD RUNNER
# ─────────────────────────────────────────────────────────────────────────────

def run_dashboard(video_path: str, video_fps: float, total_frames: int) -> str:
    """
    Chạy dashboard phân tích video.

    Args:
        video_path:   Đường dẫn file video.
        video_fps:    FPS của video.
        total_frames: Tổng số frame.

    Returns:
        "quit" hoặc "reselect".
    """
    tracker = VehicleTracker(model_path=MODEL_PATH, fps=video_fps)
    cap     = cv2.VideoCapture(video_path)

    cv2.namedWindow(WIN_NAME, cv2.WINDOW_NORMAL)
    cv2.resizeWindow(WIN_NAME, WIN_W, WIN_H)

    dmouse = _MouseState()
    cv2.setMouseCallback(WIN_NAME, _mouse_cb, dmouse)

    is_paused  = False
    frame_num  = 0
    fps_real   = 0.0
    t_prev     = time.perf_counter()
    last_frame = None
    last_raw   = None
    last_stats = {"total": 0, "min_speed": 0.0, "max_speed": 0.0, "avg_speed": 0.0}
    last_log   = []
    log_scroll = 0   # Cuộn vehicle log

    # ROI state
    roi_mode        = False
    roi_mode_points = []
    roi_confirmed   = False

    # Thời gian mục tiêu mỗi frame (giây)
    frame_delay = 1.0 / video_fps if video_fps > 0 else 1.0 / 30.0
    # Thời điểm phải hiển thị frame kế tiếp
    next_frame_time = time.perf_counter()

    while True:
        now = time.perf_counter()

        # ── Đọc frame mới ────────────────────────────────────────────────────
        if not is_paused and now >= next_frame_time:
            ok, raw_frame = cap.read()

            if not ok:
                # ── Video kết thúc ────────────────────────────────────────────
                canvas, buttons = build_dashboard(
                    last_frame, last_stats, last_log,
                    frame_num, total_frames, fps_real,
                    False, video_path,
                    roi_mode=roi_mode, roi_mode_points=roi_mode_points,
                    roi_active=roi_confirmed, log_scroll=log_scroll,
                )
                msg = "  PHÂN TÍCH HOÀN TẤT — Vui lòng dùng các nút bên dưới  "
                tw  = get_text_width(msg, 0.48, 1)
                mx  = VIDEO_W // 2
                my  = HEADER_H + CONTENT_H // 2
                fillr(canvas, mx - tw // 2 - 10, my - 22,
                              mx + tw // 2 + 10, my + 10, (20, 80, 20))
                put_center(canvas, msg, mx, my, TXT, 0.48)
                cv2.imshow(WIN_NAME, canvas)

                while True:
                    k = cv2.waitKeyEx(50)

                    action = None
                    if k in (ord("q"), ord("Q")):
                        action = "quit"

                    # Xử lý scroll wheel trong màn hình kết thúc
                    if dmouse.scroll_delta != 0:
                        log_scroll = max(0, log_scroll + dmouse.scroll_delta)
                        dmouse.scroll_delta = 0

                    if dmouse.clicked:
                        dmouse.clicked = False
                        for btn in buttons:
                            x1, y1, x2, y2 = btn["rect"]
                            if x1 <= dmouse.x <= x2 and y1 <= dmouse.y <= y2:
                                action = btn["action"]
                                break

                    if action == "quit":
                        cap.release(); cv2.destroyAllWindows()
                        return "quit"
                    elif action == "export":
                        _do_export(tracker)
                    elif action == "reselect":
                        cap.release(); cv2.destroyAllWindows()
                        return "reselect"

                    try:
                        if cv2.getWindowProperty(WIN_NAME, cv2.WND_PROP_VISIBLE) < 1:
                            cap.release(); cv2.destroyAllWindows()
                            return "quit"
                    except cv2.error:
                        return "quit"

            frame_num += 1
            last_raw   = raw_frame
            last_frame = tracker.process_frame(raw_frame)

            # Đo FPS thực tế
            dt = now - t_prev
            if dt > 0:
                fps_real = 0.9 * fps_real + 0.1 / dt
            t_prev = now

            # Lên lịch frame tiếp theo
            next_frame_time += frame_delay
            # Nếu bị trễ quá 1 frame, reset để tránh catch-up loop
            if next_frame_time < now - frame_delay:
                next_frame_time = now + frame_delay

            if frame_num % 5 == 0:
                last_stats = tracker.get_statistics()
                last_log   = tracker.get_vehicle_log()

        # ── Xử lý scroll wheel cho vehicle log ──────────────────────────────
        if dmouse.scroll_delta != 0:
            log_scroll = max(0, log_scroll + dmouse.scroll_delta)
            dmouse.scroll_delta = 0

        # ── Xử lý click vẽ ROI ───────────────────────────────────────────────
        if dmouse.clicked and roi_mode and len(roi_mode_points) < 4 and last_raw is not None:
            scale, ox, oy, nw, nh = _get_video_transform(last_raw)
            if ox <= dmouse.x <= ox + nw and oy <= dmouse.y <= oy + nh:
                dmouse.clicked = False
                fx, fy = _canvas_to_frame(dmouse.x, dmouse.y, scale, ox, oy)
                fh, fw = last_raw.shape[:2]
                if 0 <= fx <= fw and 0 <= fy <= fh:
                    roi_mode_points.append((fx, fy))
                    print(f"[ROI]  Điểm {len(roi_mode_points)}: frame=({fx:.0f}, {fy:.0f})")
                    if len(roi_mode_points) == 4:
                        tracker.set_roi(roi_mode_points)
                        roi_confirmed = True
                        roi_mode      = False
                        print("[ROI]  4 điểm đã set — perspective transform kích hoạt.")

        # ── Render dashboard ─────────────────────────────────────────────────
        canvas, buttons = build_dashboard(
            last_frame, last_stats, last_log,
            frame_num, total_frames, fps_real,
            is_paused, video_path,
            roi_mode=roi_mode, roi_mode_points=roi_mode_points,
            roi_active=roi_confirmed, log_scroll=log_scroll,
            roi_points_confirmed=roi_mode_points if roi_confirmed else None,
        )
        cv2.imshow(WIN_NAME, canvas)

        # ── Frame timing — chờ đúng thời gian để đạt FPS mục tiêu ────────────
        time_to_next = next_frame_time - time.perf_counter()
        if is_paused:
            # Khi pause: poll 30ms để UI responsive
            wait_ms = 30
        else:
            # Chờ đến lúc phải đọc frame tiếp theo nhưng vẫn xử lý events
            wait_ms = max(1, int(time_to_next * 1000))
        key = cv2.waitKeyEx(wait_ms)

        # ── Xử lý click trên các nút ──────────────────────────────────────────
        action = None
        if dmouse.clicked:
            for btn in buttons:
                x1, y1, x2, y2 = btn["rect"]
                if x1 <= dmouse.x <= x2 and y1 <= dmouse.y <= y2:
                    action = btn["action"]
                    dmouse.clicked = False
                    break

        # ── Key handling — chỉ giữ P và Q ─────────────────────────────────────
        if key in (ord("q"), ord("Q")) or action == "quit":
            break

        elif key in (ord("p"), ord("P")) or action == "pause":
            is_paused = not is_paused
            if not is_paused:
                # Reset timer khi resume để tránh burst frames
                next_frame_time = time.perf_counter() + frame_delay
            print(f"[INFO] {'PAUSED' if is_paused else 'RESUMED'}")

        elif action == "draw_roi":
            if not roi_mode:
                roi_mode        = True
                roi_mode_points = []
                roi_confirmed   = False
                tracker.clear_roi()
                is_paused       = True
                print("[ROI]  Chế độ vẽ ROI BẬT — click 4 điểm theo thứ tự TL→TR→BR→BL. "
                      "Video tạm dừng.")
            else:
                roi_mode = False
                print("[ROI]  Chế độ vẽ ROI TẮT.")

        elif action == "clear_roi":
            roi_mode        = False
            roi_mode_points = []
            roi_confirmed   = False
            tracker.clear_roi()
            print("[ROI]  ROI đã xóa.")

        elif action == "reselect":
            cap.release(); cv2.destroyAllWindows()
            return "reselect"

        elif action == "export":
            _do_export(tracker)

        try:
            if cv2.getWindowProperty(WIN_NAME, cv2.WND_PROP_VISIBLE) < 1:
                break
        except cv2.error:
            break

    cap.release()
    cv2.destroyAllWindows()
    return "quit"
