"""
ui/dashboard.py — Analysis dashboard (OpenCV window).

Hiển thị video, thống kê tốc độ, log xe và cho phép vẽ ROI.
Phím: P=Pause  D=Vẽ ROI  C=Xóa ROI  R=Chọn lại video  E=Export  Q=Thoát
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
    fillr(canvas, 0, 0, WIN_W, HEADER_H, HDR)
    hline(canvas, 0, WIN_W, HEADER_H, AMBER, 2)
    put(canvas, "VEHICLE ANALYSIS SYSTEM", 20, 36, TXT, 0.65, 1, FONTD)

    dot_color   = YELLOW if is_paused else GREEN
    status_text = "PAUSED" if is_paused else "LIVE"
    put(canvas, "●",          520, 36, dot_color, 0.60)
    put(canvas, status_text,  550, 36, dot_color, 0.45)

    bname = os.path.basename(video_name)
    if len(bname) > 50:
        bname = bname[:48] + ".."
    put_right(canvas, bname, WIN_W - 20, 36, DIM, 0.45)


def _draw_video_panel(canvas: np.ndarray, frame, roi_mode: bool,
                      roi_mode_points: list) -> None:
    """Vẽ panel video bên trái và overlay hướng dẫn vẽ ROI."""
    fillr(canvas, 0, HEADER_H, VIDEO_W, HEADER_H + CONTENT_H, BG)

    if frame is None:
        put_center(canvas, "No frame", VIDEO_W // 2, HEADER_H + CONTENT_H // 2,
                   DIM, 0.55)
        return

    scale, ox, oy, nw, nh = _get_video_transform(frame)
    resized = cv2.resize(frame, (nw, nh), interpolation=cv2.INTER_LINEAR)
    canvas[oy:oy + nh, ox:ox + nw] = resized

    # Vẽ các điểm ROI đang chọn
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

    # Banner hướng dẫn ROI
    if roi_mode:
        n   = len(roi_mode_points) if roi_mode_points else 0
        msg = (f"  ROI MODE — Click điểm {n + 1}/4 (TL→TR→BR→BL)  "
               if n < 4 else "  ROI SET — Nhấn [C] để xóa  ")
        tw  = get_text_width(msg, 0.55, 1)
        bx  = VIDEO_W // 2
        fillr(canvas, bx - tw // 2 - 12, HEADER_H + 10,
                      bx + tw // 2 + 12, HEADER_H + 40, (0, 60, 120))
        put_center(canvas, msg, bx, HEADER_H + 32, CYAN, 0.55, 1)


def _draw_stat_panel(canvas: np.ndarray, stats: dict, vehicle_log: list) -> None:
    """Vẽ panel thống kê và log xe bên phải."""
    SX, SW = STAT_X, STAT_W
    PX     = SX + 18
    PW     = SW - 36

    fillr(canvas, SX, HEADER_H, WIN_W, HEADER_H + CONTENT_H, PANEL)
    vline(canvas, SX, HEADER_H, HEADER_H + CONTENT_H, DIV)

    py = HEADER_H + 16

    # ── Tổng xe ──────────────────────────────────────────────────────────────
    total = stats.get("total", 0)
    fillr(canvas, PX, py, PX + PW, py + 120, HDR)
    put(canvas, "Total Vehicles", PX + 16, py + 30, LBL, 0.50)
    put(canvas, str(total),       PX + 16, py + 110, AMBER, 1.40, 2, FONTD)
    py += 130

    # ── Lưới tốc độ 1×3 ──────────────────────────────────────────────────────
    third = (PW - 16) // 3
    cells = [
        ("Avg Speed", f"{stats.get('avg_speed', 0):.1f}", "km/h", TXT),
        ("Max Speed", f"{stats.get('max_speed', 0):.1f}", "km/h", RED),
        ("Min Speed", f"{stats.get('min_speed', 0):.1f}", "km/h", GREEN),
    ]
    for i, (label, value, unit, val_color) in enumerate(cells):
        gx = PX + i * (third + 8)
        fillr(canvas, gx, py, gx + third, py + 120, HDR)
        put(canvas, label, gx + 12, py + 30, LBL,       0.45)
        put(canvas, value, gx + 12, py + 85, val_color,  0.90, 2, FONTD)
        put(canvas, unit,  gx + 12, py + 115, DIM,        0.40)
    py += 130

    # ── Vehicle Log ───────────────────────────────────────────────────────────
    put(canvas, "VEHICLE LOG", PX, py + 35, LBL, 0.55)
    hline(canvas, PX, SX + SW - 20, py + 48, DIV)
    py += 58

    fillr(canvas, PX, py, PX + PW, py + 40, HDR)
    for col_label, x_off in [("ID", 10), ("TYPE", 80), ("ENTRY", 240),
                              ("EXIT", 420), ("SPD", 620)]:
        put(canvas, col_label, PX + x_off, py + 28, DIM, 0.45)
    hline(canvas, PX, PX + PW, py + 40, DIV)
    py += 44

    ROW_H        = 44
    panel_bottom = HEADER_H + CONTENT_H - 6
    max_rows     = max(0, (panel_bottom - py) // ROW_H)
    display_log  = list(reversed(vehicle_log[-max_rows:])) if vehicle_log else []

    for i, entry in enumerate(display_log):
        ry = py + i * ROW_H
        if ry + ROW_H > panel_bottom:
            break
        if i % 2 == 0:
            fillr(canvas, PX, ry, PX + PW, ry + ROW_H, ALT_ROW)
        spd       = entry.get("max_speed", 0.0)
        spd_color = RED if spd > 100 else YELLOW if spd > 60 else GREEN
        put(canvas, str(entry.get("id", "?")),          PX + 10,  ry + 30, TEAL,      0.48)
        put(canvas, str(entry.get("type", "?"))[:10],   PX + 80,  ry + 30, TXT,       0.48)
        put(canvas, str(entry.get("entry_time", "--")), PX + 240, ry + 30, DIM,       0.45)
        put(canvas, str(entry.get("exit_time",  "--")), PX + 420, ry + 30, DIM,       0.45)
        put(canvas, f"{spd:.1f}",                       PX + 620, ry + 30, spd_color, 0.48)

    hline(canvas, SX, WIN_W, HEADER_H + CONTENT_H, DIV)


def _draw_statusbar(canvas: np.ndarray, frame_num: int, total_frames: int,
                    fps_real: float, roi_active: bool, is_paused: bool) -> list:
    """Vẽ thanh trạng thái dưới cùng và các nút chức năng."""
    SY = WIN_H - STATUSBAR_H
    fillr(canvas, 0, SY, WIN_W, WIN_H, HDR)
    hline(canvas, 0, WIN_W, SY, DIV)

    pct = frame_num / total_frames * 100 if total_frames > 0 else 0.0
    put(canvas, f"Frame {frame_num:,} / {total_frames:,}   {pct:.1f}%",
        20, SY + 36, TXT, 0.45)

    # Progress bar
    BAR_X1, BAR_X2 = 380, 640
    BAR_Y = SY + 26
    fillr(canvas, BAR_X1, BAR_Y, BAR_X2, BAR_Y + 8, DIV)
    fill_w = int((BAR_X2 - BAR_X1) * min(pct / 100.0, 1.0))
    if fill_w > 0:
        fillr(canvas, BAR_X1, BAR_Y, BAR_X1 + fill_w, BAR_Y + 8, AMBER)

    put(canvas, f"FPS {fps_real:.1f}", 660, SY + 36, GREEN, 0.45)

    if roi_active:
        put(canvas, "ROI ✓", 760, SY + 36, CYAN, 0.45)

    # Nút bấm
    buttons = []
    actions = [
        ("pause", "Resume" if is_paused else "Pause"),
        ("draw_roi", "Vẽ ROI"),
        ("clear_roi", "Xóa ROI"),
        ("reselect", "Chọn lại"),
        ("export", "Export"),
        ("quit", "Thoát")
    ]
    
    bx = WIN_W - 20
    for act, label in reversed(actions):
        tw = get_text_width(label, 0.45, 1)
        bw = tw + 40
        bh = 46
        by = SY + 7
        bx -= bw
        
        fillr(canvas, bx, by, bx + bw, by + bh, PANEL)
        bordr(canvas, bx, by, bx + bw, by + bh, DIV)
        put_center(canvas, label, bx + bw // 2, by + 30, TXT, 0.45)
        buttons.append({"action": act, "rect": (bx, by, bx + bw, by + bh)})
        bx -= 12  # khoảng cách giữa các nút
        
    return buttons


# ─────────────────────────────────────────────────────────────────────────────
# MAIN BUILDER
# ─────────────────────────────────────────────────────────────────────────────

def build_dashboard(ann_frame, stats: dict, vehicle_log: list,
                    frame_num: int, total_frames: int, fps_real: float,
                    is_paused: bool, video_name: str,
                    roi_mode: bool = False, roi_mode_points: list = None,
                    roi_active: bool = False) -> tuple:
    """Tổng hợp toàn bộ dashboard vào 1 canvas và trả về (canvas, buttons)."""
    canvas = np.zeros((WIN_H, WIN_W, 3), dtype=np.uint8)
    _draw_header(canvas, video_name, is_paused)
    _draw_video_panel(canvas, ann_frame, roi_mode, roi_mode_points or [])
    _draw_stat_panel(canvas, stats, vehicle_log)
    buttons = _draw_statusbar(canvas, frame_num, total_frames, fps_real, roi_active, is_paused)
    return canvas, buttons


# ─────────────────────────────────────────────────────────────────────────────
# MOUSE STATE
# ─────────────────────────────────────────────────────────────────────────────

class _MouseState:
    def __init__(self):
        self.x = self.y = 0
        self.clicked = False


def _mouse_cb(event, x, y, flags, state: _MouseState):
    state.x, state.y = x, y
    if event == cv2.EVENT_LBUTTONDOWN:
        state.clicked = True


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
    t_prev     = time.time()
    last_frame = None
    last_raw   = None
    last_stats = {"total": 0, "min_speed": 0.0, "max_speed": 0.0, "avg_speed": 0.0}
    last_log   = []

    # ROI state
    roi_mode        = False
    roi_mode_points = []
    roi_confirmed   = False

    frame_delay = 1.0 / video_fps if video_fps > 0 else 1.0 / 30.0

    while True:
        # ── Đọc frame mới ────────────────────────────────────────────────────
        if not is_paused:
            ok, raw_frame = cap.read()

            if not ok:
                # ── Video kết thúc ────────────────────────────────────────────
                canvas, buttons = build_dashboard(
                    last_frame, last_stats, last_log,
                    frame_num, total_frames, fps_real,
                    False, video_path,
                    roi_mode=roi_mode, roi_mode_points=roi_mode_points,
                    roi_active=roi_confirmed,
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
                    k = cv2.waitKeyEx(100)
                    
                    action = None
                    if k in (ord("q"), ord("Q")): action = "quit"
                    elif k in (ord("e"), ord("E")): action = "export"
                    elif k in (ord("r"), ord("R")): action = "reselect"
                    
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
            last_raw    = raw_frame
            last_frame  = tracker.process_frame(raw_frame)

            now = time.time()
            dt  = now - t_prev
            if dt > 0:
                fps_real = 0.9 * fps_real + 0.1 / dt
            t_prev = now

            if frame_num % 5 == 0:
                last_stats = tracker.get_statistics()
                last_log   = tracker.get_vehicle_log()

        # ── Xử lý click vẽ ROI ───────────────────────────────────────────────
        if dmouse.clicked and roi_mode and len(roi_mode_points) < 4 and last_raw is not None:
            scale, ox, oy, nw, nh = _get_video_transform(last_raw)
            # Only consume if clicked inside video panel area
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
            roi_active=roi_confirmed,
        )
        cv2.imshow(WIN_NAME, canvas)

        # ── Frame timing ──────────────────────────────────────────────────────
        elapsed = time.time() - t_prev
        wait_ms = max(1, int((frame_delay - elapsed) * 1000))
        key     = cv2.waitKeyEx(wait_ms)
        
        # ── Xử lý click trên các nút ──────────────────────────────────────────
        action = None
        if dmouse.clicked:
            # We already handled ROI points click earlier, but it clears dmouse.clicked.
            # Wait, dmouse.clicked was set to False above in ROI handling! 
            # We should check button clicks first or don't clear it.
            # Actually, ROI click check is conditional. Let's just re-check here.
            # I will fix this in the next replacement block or here.
            for btn in buttons:
                x1, y1, x2, y2 = btn["rect"]
                if x1 <= dmouse.x <= x2 and y1 <= dmouse.y <= y2:
                    action = btn["action"]
                    dmouse.clicked = False
                    break

        # ── Key handling ──────────────────────────────────────────────────────
        if key in (ord("q"), ord("Q")) or action == "quit":
            break

        elif key in (ord("p"), ord("P")) or action == "pause":
            is_paused = not is_paused
            print(f"[INFO] {'PAUSED' if is_paused else 'RESUMED'}")

        elif key in (ord("d"), ord("D")) or action == "draw_roi":
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

        elif key in (ord("c"), ord("C")) or action == "clear_roi":
            roi_mode        = False
            roi_mode_points = []
            roi_confirmed   = False
            tracker.clear_roi()
            print("[ROI]  ROI đã xóa.")

        elif key in (ord("r"), ord("R")) or action == "reselect":
            cap.release(); cv2.destroyAllWindows()
            return "reselect"

        elif key in (ord("e"), ord("E")) or action == "export":
            _do_export(tracker)

        try:
            if cv2.getWindowProperty(WIN_NAME, cv2.WND_PROP_VISIBLE) < 1:
                break
        except cv2.error:
            break

    cap.release()
    cv2.destroyAllWindows()
    return "quit"
