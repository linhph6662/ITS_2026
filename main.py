"""
main.py — Vehicle Tracking & Speed Measurement Dashboard
Run:  python main.py
Keys: P=Pause  R=Reselect  E=Export  +/-=Scale  Q=Quit
"""

import os
import sys
import time
from datetime import datetime

import cv2
import numpy as np

from tracker import VehicleTracker
from utils import export_to_excel


# ─────────────────────────────────────────────────────────────────────────────
# LAYOUT CONSTANTS
# ─────────────────────────────────────────────────────────────────────────────
WIN_W, WIN_H   = 1280, 760
HEADER_H       = 38
STATUSBAR_H    = 32
VIDEO_W        = int(WIN_W * 0.60)          # 768
STAT_X         = VIDEO_W
STAT_W         = WIN_W - VIDEO_W            # 512
CONTENT_H      = WIN_H - HEADER_H - STATUSBAR_H   # 690

VIDEO_DIR      = "video"
REPORT_DIR     = "report"
MODEL_PATH     = "yolo26n.pt"

# Default pixels-per-metre.
# Rule of thumb: measure a known distance in the frame (e.g. lane width ≈ 3.5 m)
# and count how many pixels it spans, then set PPM = pixels / metres.
DEFAULT_PPM    = 28.0

# ─────────────────────────────────────────────────────────────────────────────
# COLOR PALETTE  (BGR throughout)
# ─────────────────────────────────────────────────────────────────────────────
BG      = ( 22,  22,  22)   # main background
PANEL   = ( 32,  32,  32)   # stat panel background
HDR     = ( 42,  42,  42)   # header / section header bars
DIV     = ( 58,  58,  58)   # divider lines
TXT     = (210, 210, 210)   # primary text
DIM     = (105, 105, 105)   # secondary / dim text
LBL     = (148, 148, 148)   # column labels / captions
AMBER   = (  0, 160, 255)   # accent orange   RGB 255,160,0
GREEN   = ( 80, 175,  80)   # OK / normal speed
YELLOW  = ( 40, 200, 210)   # caution speed   RGB 210,200,40
RED     = ( 55,  55, 210)   # high speed      RGB 210,55,55
TEAL    = (150, 165,  55)   # track IDs       RGB 55,165,150
CYAN    = (255, 255,   0)   # ROI points      RGB 0,255,255
ROI_CLR = (  0, 180, 255)   # ROI polygon     RGB 255,180,0
SEL_BG  = ( 50,  38,  18)   # selected row background
HOV_BG  = ( 40,  40,  40)   # hovered row background
ALT_ROW = ( 36,  36,  36)   # alternating log row

FONT  = cv2.FONT_HERSHEY_SIMPLEX
FONTD = cv2.FONT_HERSHEY_DUPLEX
WIN_NAME = "VEHICLE ANALYSIS SYSTEM"


# ─────────────────────────────────────────────────────────────────────────────
# DRAWING PRIMITIVES
# ─────────────────────────────────────────────────────────────────────────────
def fillr(img, x1, y1, x2, y2, color):
    cv2.rectangle(img, (int(x1), int(y1)), (int(x2), int(y2)), color, -1)

def bordr(img, x1, y1, x2, y2, color, thickness=1):
    cv2.rectangle(img, (int(x1), int(y1)), (int(x2), int(y2)), color, thickness)

def hline(img, x1, x2, y, color=DIV, thickness=1):
    cv2.line(img, (int(x1), int(y)), (int(x2), int(y)), color, thickness)

def vline(img, x, y1, y2, color=DIV, thickness=1):
    cv2.line(img, (int(x), int(y1)), (int(x), int(y2)), color, thickness)

def put(img, s, x, y, color=TXT, scale=0.43, thickness=1, font=FONT):
    cv2.putText(img, str(s), (int(x), int(y)), font, scale,
                color, thickness, cv2.LINE_AA)

def put_right(img, s, rx, y, color=TXT, scale=0.43, thickness=1):
    s = str(s)
    w = cv2.getTextSize(s, FONT, scale, thickness)[0][0]
    cv2.putText(img, s, (int(rx) - w, int(y)), FONT, scale,
                color, thickness, cv2.LINE_AA)

def put_center(img, s, cx, y, color=TXT, scale=0.43, thickness=1, font=FONT):
    s = str(s)
    w = cv2.getTextSize(s, font, scale, thickness)[0][0]
    cv2.putText(img, s, (int(cx) - w // 2, int(y)), font, scale,
                color, thickness, cv2.LINE_AA)


# ─────────────────────────────────────────────────────────────────────────────
# UTILITIES
# ─────────────────────────────────────────────────────────────────────────────
def fmt_size(b):
    for unit in ("B", "KB", "MB", "GB"):
        if b < 1024:
            return f"{b:.0f} {unit}"
        b /= 1024
    return f"{b:.1f} GB"


def fmt_duration(secs):
    h = int(secs // 3600)
    m = int((secs % 3600) // 60)
    s = int(secs % 60)
    return f"{h}:{m:02d}:{s:02d}" if h else f"{m}:{s:02d}"


def ensure_dir(path):
    os.makedirs(path, exist_ok=True)


def scan_videos(video_dir):
    """Return list of video metadata dicts from video_dir."""
    items = []
    if not os.path.isdir(video_dir):
        return items
    for filename in sorted(os.listdir(video_dir)):
        if not filename.lower().endswith((".mp4", ".avi", ".mov", ".mkv")):
            continue
        path = os.path.join(video_dir, filename)
        size = os.path.getsize(path)
        cap = cv2.VideoCapture(path)
        fps    = cap.get(cv2.CAP_PROP_FPS) or 30.0
        frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        width  = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        cap.release()
        items.append({
            "name":    filename,
            "path":    path,
            "size":    size,
            "fps":     fps,
            "frames":  frames,
            "width":   width,
            "height":  height,
            "duration": frames / fps if fps > 0 else 0,
        })
    return items


def get_report_path():
    ensure_dir(REPORT_DIR)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    return os.path.join(REPORT_DIR, f"vehicle_report_{ts}.xlsx")


def do_export(tracker):
    log   = tracker.get_vehicle_log()
    stats = tracker.get_statistics()
    if not log:
        print("[WARN] No vehicle data to export yet.")
        return
    try:
        data = export_to_excel(log, stats)
        path = get_report_path()
        with open(path, "wb") as f:
            f.write(data)
        print(f"[OK]   Report saved → {os.path.abspath(path)}")
    except Exception as exc:
        print(f"[ERR]  Export failed: {exc}")


# ─────────────────────────────────────────────────────────────────────────────
# VIDEO PICKER
# ─────────────────────────────────────────────────────────────────────────────
# Picker layout constants (fixed so hover can be computed before draw)
_PK_LX1, _PK_LX2 = 18, 760
_PK_COL_H  = 26
_PK_COL_Y  = HEADER_H + 14 + _PK_COL_H           # = 78
_PK_ITEM_H = 46
_PK_LY2    = WIN_H - STATUSBAR_H - 14
_PK_MAX_VIS = max(1, (_PK_LY2 - _PK_COL_Y) // _PK_ITEM_H)


class _MouseState:
    def __init__(self):
        self.x = self.y = 0
        self.clicked = False


def _picker_mouse_cb(event, x, y, flags, ms):
    ms.x, ms.y = x, y
    if event == cv2.EVENT_LBUTTONDOWN:
        ms.clicked = True


def _draw_picker(canvas, videos, sel, hov, scroll):
    """Render the video selection screen onto canvas."""
    W, H = WIN_W, WIN_H
    canvas[:] = BG

    # ── Header ───────────────────────────────────────────────────────────────
    fillr(canvas, 0, 0, W, HEADER_H, HDR)
    hline(canvas, 0, W, HEADER_H, AMBER, 2)
    put(canvas, "VEHICLE ANALYSIS SYSTEM  //  Select Input Video",
        14, 25, TXT, 0.52, 1, FONTD)
    put_right(canvas, f"{len(videos)} file(s) in ./{VIDEO_DIR}/",
              W - 14, 25, DIM, 0.37)

    # ── List panel ───────────────────────────────────────────────────────────
    LX1, LX2 = _PK_LX1, _PK_LX2
    LY1, LY2 = HEADER_H + 14, _PK_LY2
    COL_Y, ITEM_H = _PK_COL_Y, _PK_ITEM_H

    # Column header row
    fillr(canvas, LX1, LY1, LX2, COL_Y, (48, 48, 48))
    put(canvas, "#",        LX1 + 8,   COL_Y - 7, LBL, 0.33)
    put(canvas, "FILENAME", LX1 + 34,  COL_Y - 7, LBL, 0.33)
    put(canvas, "RES",      LX1 + 430, COL_Y - 7, LBL, 0.33)
    put(canvas, "DUR",      LX1 + 518, COL_Y - 7, LBL, 0.33)
    put(canvas, "FPS",      LX1 + 608, COL_Y - 7, LBL, 0.33)
    put(canvas, "SIZE",     LX1 + 650, COL_Y - 7, LBL, 0.33)
    hline(canvas, LX1, LX2, COL_Y, DIV)

    if not videos:
        put(canvas, f"No video files (.mp4 / .avi) found in  ./{VIDEO_DIR}/",
            LX1 + 16, COL_Y + 40, DIM, 0.44)
    else:
        visible = videos[scroll: scroll + _PK_MAX_VIS]
        for idx, v in enumerate(visible):
            vi = idx + scroll
            row_y = COL_Y + idx * ITEM_H

            if vi == sel:
                fillr(canvas, LX1, row_y, LX2, row_y + ITEM_H, SEL_BG)
                fillr(canvas, LX1, row_y, LX1 + 3, row_y + ITEM_H, AMBER)
            elif vi == hov:
                fillr(canvas, LX1, row_y, LX2, row_y + ITEM_H, HOV_BG)

            ty = row_y + ITEM_H // 2 + 7
            name_color = AMBER if vi == sel else TXT
            nm = v["name"] if len(v["name"]) <= 54 else v["name"][:52] + ".."
            put(canvas, str(vi + 1),             LX1 + 8,   ty, DIM,        0.35)
            put(canvas, nm,                       LX1 + 34,  ty, name_color, 0.42)
            put(canvas, f"{v['width']}x{v['height']}", LX1 + 430, ty, DIM,  0.37)
            put(canvas, fmt_duration(v["duration"]),   LX1 + 518, ty, DIM,  0.37)
            put(canvas, f"{v['fps']:.0f}",        LX1 + 608, ty, DIM,        0.37)
            put(canvas, fmt_size(v["size"]),      LX1 + 650, ty, DIM,        0.37)
            hline(canvas, LX1, LX2, row_y + ITEM_H, DIV)

    bordr(canvas, LX1, LY1, LX2, LY2, DIV)

    # ── Info + Start panel (right) ───────────────────────────────────────────
    RX1 = LX2 + 18
    RX2 = W - 18
    fillr(canvas, RX1, LY1, RX2, LY2, PANEL)
    bordr(canvas, RX1, LY1, RX2, LY2, DIV)

    iy = LY1 + 14
    put(canvas, "VIDEO INFORMATION", RX1 + 12, iy, LBL, 0.36)
    hline(canvas, RX1 + 1, RX2 - 1, iy + 8, DIV)
    iy += 26

    if 0 <= sel < len(videos):
        v = videos[sel]
        info = [
            ("Name",       v["name"]),
            ("Resolution", f"{v['width']} x {v['height']}"),
            ("Duration",   fmt_duration(v["duration"])),
            ("Frames",     f"{v['frames']:,}"),
            ("FPS",        f"{v['fps']:.1f}"),
            ("File size",  fmt_size(v["size"])),
        ]
        for label, value in info:
            put(canvas, label, RX1 + 12, iy, DIM, 0.36)
            disp = value if len(value) <= 26 else value[:24] + ".."
            put(canvas, disp,  RX1 + 12, iy + 18, TXT, 0.41)
            iy += 42

    # Start button
    BY1 = LY2 - 58
    BY2 = LY2 - 12
    BX1 = RX1 + 12
    BX2 = RX2 - 12
    can_start = 0 <= sel < len(videos)
    btn_color  = AMBER if can_start else DIV
    text_color = BG    if can_start else DIM
    fillr(canvas, BX1, BY1, BX2, BY2, btn_color)
    put_center(canvas, "START ANALYSIS", (BX1 + BX2) // 2, BY1 + 28,
               text_color, 0.50, 1, FONTD)

    # ── Status bar ───────────────────────────────────────────────────────────
    fillr(canvas, 0, H - STATUSBAR_H, W, H, HDR)
    hline(canvas, 0, W, H - STATUSBAR_H, DIV)
    put(canvas, "Click item to select     Double-click / Enter to start"
               "     J/K or ↑/↓ to navigate     Q to quit",
        14, H - 10, DIM, 0.36)

    return BX1, BX2, BY1, BY2


def run_picker():
    """Show the video picker. Returns (path, fps, frames) or (None, 0, 0)."""
    videos = scan_videos(VIDEO_DIR)
    ms = _MouseState()
    sel = 0 if videos else -1
    hov = -1
    scroll = 0

    cv2.namedWindow(WIN_NAME, cv2.WINDOW_NORMAL)
    cv2.resizeWindow(WIN_NAME, WIN_W, WIN_H)
    cv2.setMouseCallback(WIN_NAME, _picker_mouse_cb, ms)

    while True:
        # ── Compute hover from current mouse pos ──────────────────────────
        mx, my = ms.x, ms.y
        hov = -1
        if _PK_LX1 <= mx <= _PK_LX2 and _PK_COL_Y <= my:
            ri = (my - _PK_COL_Y) // _PK_ITEM_H + scroll
            if 0 <= ri < len(videos):
                hov = ri

        # ── Draw ─────────────────────────────────────────────────────────
        canvas = np.zeros((WIN_H, WIN_W, 3), dtype=np.uint8)
        bx1, bx2, by1, by2 = _draw_picker(canvas, videos, sel, hov, scroll)

        # ── Handle click ─────────────────────────────────────────────────
        if ms.clicked:
            ms.clicked = False
            if hov >= 0:
                if hov == sel:
                    # Double-click: confirm immediately
                    v = videos[sel]
                    cv2.destroyAllWindows()
                    return v["path"], v["fps"], v["frames"]
                sel = hov
            # Start button
            if bx1 <= mx <= bx2 and by1 <= my <= by2 and 0 <= sel < len(videos):
                v = videos[sel]
                cv2.destroyAllWindows()
                return v["path"], v["fps"], v["frames"]

        cv2.imshow(WIN_NAME, canvas)
        key = cv2.waitKeyEx(33)

        if key in (ord("q"), ord("Q"), 27):
            cv2.destroyAllWindows()
            return None, 0, 0

        elif key in (13, 10):   # Enter
            if 0 <= sel < len(videos):
                v = videos[sel]
                cv2.destroyAllWindows()
                return v["path"], v["fps"], v["frames"]

        elif key in (ord("k"), ord("K"), 2490368):   # K / Up arrow
            if sel > 0:
                sel -= 1
                if sel < scroll:
                    scroll = sel

        elif key in (ord("j"), ord("J"), 2621440):   # J / Down arrow
            if sel < len(videos) - 1:
                sel += 1
                if sel >= scroll + _PK_MAX_VIS:
                    scroll = sel - _PK_MAX_VIS + 1

        try:
            if cv2.getWindowProperty(WIN_NAME, cv2.WND_PROP_VISIBLE) < 1:
                cv2.destroyAllWindows()
                return None, 0, 0
        except cv2.error:
            return None, 0, 0


# ─────────────────────────────────────────────────────────────────────────────
# DASHBOARD DRAWING
# ─────────────────────────────────────────────────────────────────────────────
def _draw_header(canvas, video_name, is_paused):
    fillr(canvas, 0, 0, WIN_W, HEADER_H, HDR)
    hline(canvas, 0, WIN_W, HEADER_H, AMBER, 2)
    put(canvas, "VEHICLE ANALYSIS SYSTEM", 14, 25, TXT, 0.52, 1, FONTD)
    dot_color   = YELLOW if is_paused else GREEN
    status_text = "PAUSED" if is_paused else "LIVE"
    put(canvas, "●", 268, 25, dot_color, 0.50)
    put(canvas, status_text, 286, 25, dot_color, 0.38)
    bname = os.path.basename(video_name)
    if len(bname) > 50:
        bname = bname[:48] + ".."
    put_right(canvas, bname, WIN_W - 14, 25, DIM, 0.37)


def _get_video_transform(frame):
    """Compute scale, offset for frame→canvas mapping. Returns (scale, ox, oy, nw, nh)."""
    if frame is None:
        return 1.0, 0, HEADER_H, VIDEO_W, CONTENT_H
    AW, AH = VIDEO_W, CONTENT_H
    fh, fw = frame.shape[:2]
    scale = min(AW / fw, AH / fh)
    nw, nh = int(fw * scale), int(fh * scale)
    ox = (AW - nw) // 2
    oy = HEADER_H + (AH - nh) // 2
    return scale, ox, oy, nw, nh


def _canvas_to_frame(cx, cy, scale, ox, oy):
    """Convert canvas (click) coordinates to original frame coordinates."""
    fx = (cx - ox) / scale
    fy = (cy - oy) / scale
    return fx, fy


def _frame_to_canvas(fx, fy, scale, ox, oy):
    """Convert original frame coordinates to canvas coordinates."""
    cx = int(fx * scale + ox)
    cy = int(fy * scale + oy)
    return cx, cy


def _draw_video_panel(canvas, frame, roi_points=None, roi_mode=False,
                      roi_mode_points=None):
    """Draw the video panel, optionally with ROI overlay."""
    AW, AH = VIDEO_W, CONTENT_H
    AX, AY = 0, HEADER_H
    fillr(canvas, AX, AY, AX + AW, AY + AH, BG)
    if frame is None:
        put_center(canvas, "No frame", AX + AW // 2, AY + AH // 2, DIM, 0.55)
        return
    fh, fw = frame.shape[:2]
    scale, ox, oy, nw, nh = _get_video_transform(frame)
    resized = cv2.resize(frame, (nw, nh), interpolation=cv2.INTER_LINEAR)
    canvas[oy:oy + nh, ox:ox + nw] = resized

    # ── Draw ROI selection points (during selection mode) ─────────────
    if roi_mode and roi_mode_points:
        pts_canvas = [_frame_to_canvas(p[0], p[1], scale, ox, oy)
                      for p in roi_mode_points]
        # Draw lines between consecutive points
        for i in range(len(pts_canvas)):
            cv2.circle(canvas, pts_canvas[i], 7, CYAN, -1, cv2.LINE_AA)
            cv2.circle(canvas, pts_canvas[i], 9, ROI_CLR, 2, cv2.LINE_AA)
            put(canvas, str(i + 1),
                pts_canvas[i][0] + 12, pts_canvas[i][1] - 6, CYAN, 0.50, 1)
            if i > 0:
                cv2.line(canvas, pts_canvas[i - 1], pts_canvas[i],
                         ROI_CLR, 2, cv2.LINE_AA)
        # Close polygon if 4 points
        if len(pts_canvas) == 4:
            cv2.line(canvas, pts_canvas[3], pts_canvas[0],
                     ROI_CLR, 2, cv2.LINE_AA)

    # ── ROI mode banner ──────────────────────────────────────────────
    if roi_mode:
        n = len(roi_mode_points) if roi_mode_points else 0
        if n < 4:
            msg = f"  ROI MODE — Click point {n + 1}/4 (TL>TR>BR>BL)  "
        else:
            msg = "  ROI SET — Press [C] to clear  "
        tw = cv2.getTextSize(msg, FONT, 0.45, 1)[0][0]
        bx = AX + AW // 2
        fillr(canvas, bx - tw // 2 - 8, AY + 6,
                      bx + tw // 2 + 8, AY + 28, (0, 60, 120))
        put_center(canvas, msg, bx, AY + 23, CYAN, 0.45, 1)


def _draw_stat_panel(canvas, stats, vehicle_log, ppm):
    SX, SW = STAT_X, STAT_W
    PX = SX + 14
    PW = SW - 28

    fillr(canvas, SX, HEADER_H, WIN_W, HEADER_H + CONTENT_H, PANEL)
    vline(canvas, SX, HEADER_H, HEADER_H + CONTENT_H, DIV)

    py = HEADER_H + 12

    # ── Total Vehicles ────────────────────────────────────────────────────
    total = stats.get("total", 0)
    fillr(canvas, PX, py, PX + PW, py + 54, HDR)
    put(canvas, "Total Vehicles", PX + 10, py + 15, LBL, 0.36)
    put(canvas, str(total),       PX + 10, py + 47, AMBER, 0.92, 2, FONTD)
    py += 60

    # ── 2×2 Speed Grid ───────────────────────────────────────────────────
    half = (PW - 6) // 2
    avg_s = stats.get("avg_speed", 0.0)
    max_s = stats.get("max_speed", 0.0)
    min_s = stats.get("min_speed", 0.0)
    cells = [
        ("Avg Speed",  f"{avg_s:.1f}", "km/h",    TXT),
        ("Max Speed",  f"{max_s:.1f}", "km/h",    RED),
        ("Min Speed",  f"{min_s:.1f}", "km/h",    GREEN),
        ("Scale px/m", f"{ppm:.1f}",   "+/-",     TEAL),
    ]
    for i, (label, value, unit, val_color) in enumerate(cells):
        gx = PX + (i % 2) * (half + 6)
        gy = py + (i // 2) * 60
        fillr(canvas, gx, gy, gx + half, gy + 54, HDR)
        put(canvas, label, gx + 8, gy + 14, LBL,       0.31)
        put(canvas, value, gx + 8, gy + 38, val_color,  0.60, 1, FONTD)
        put(canvas, unit,  gx + 8, gy + 50, DIM,        0.29)
    py += 128   # 2 rows × 60 + 8 gap

    # ── Vehicle Log ───────────────────────────────────────────────────────
    put(canvas, "VEHICLE LOG", PX, py, LBL, 0.35)
    hline(canvas, PX, SX + SW - 14, py + 7, DIV)
    py += 18

    # Table header
    fillr(canvas, PX, py, PX + PW, py + 18, HDR)
    put(canvas, "ID",    PX + 2,   py + 13, DIM, 0.30)
    put(canvas, "TYPE",  PX + 28,  py + 13, DIM, 0.30)
    put(canvas, "ENTRY", PX + 108, py + 13, DIM, 0.30)
    put(canvas, "EXIT",  PX + 168, py + 13, DIM, 0.30)
    put(canvas, "SPD",   PX + 224, py + 13, DIM, 0.30)
    hline(canvas, PX, PX + PW, py + 18, DIV)
    py += 22

    # Rows
    ROW_H = 20
    panel_bottom = HEADER_H + CONTENT_H - 6
    max_rows = max(0, (panel_bottom - py) // ROW_H)
    display_log = list(reversed(vehicle_log[-max_rows:])) if vehicle_log else []

    for i, entry in enumerate(display_log):
        ry = py + i * ROW_H
        if ry + ROW_H > panel_bottom:
            break
        if i % 2 == 0:
            fillr(canvas, PX, ry, PX + PW, ry + ROW_H, ALT_ROW)
        spd = entry.get("max_speed", 0.0)
        spd_color = RED if spd > 70 else YELLOW if spd > 40 else GREEN
        put(canvas, str(entry.get("id", "?")),         PX + 2,   ry + 14, TEAL,      0.32)
        put(canvas, str(entry.get("type", "?"))[:10],  PX + 28,  ry + 14, TXT,       0.32)
        put(canvas, str(entry.get("entry_time", "--")),PX + 108, ry + 14, DIM,       0.30)
        put(canvas, str(entry.get("exit_time",  "--")),PX + 168, ry + 14, DIM,       0.30)
        put(canvas, f"{spd:.1f}",                      PX + 224, ry + 14, spd_color, 0.32)

    hline(canvas, SX, WIN_W, HEADER_H + CONTENT_H, DIV)


def _draw_statusbar(canvas, frame_num, total_frames, fps_real, roi_active=False):
    SY = WIN_H - STATUSBAR_H
    fillr(canvas, 0, SY, WIN_W, WIN_H, HDR)
    hline(canvas, 0, WIN_W, SY, DIV)

    pct = frame_num / total_frames * 100 if total_frames > 0 else 0.0
    put(canvas, f"Frame {frame_num:,} / {total_frames:,}   {pct:.1f}%",
        14, SY + 21, TXT, 0.37)

    # Progress bar
    BAR_X1, BAR_X2 = 270, 460
    BAR_Y = SY + 15
    fillr(canvas, BAR_X1, BAR_Y, BAR_X2, BAR_Y + 6, DIV)
    fill_w = int((BAR_X2 - BAR_X1) * min(pct / 100.0, 1.0))
    if fill_w > 0:
        fillr(canvas, BAR_X1, BAR_Y, BAR_X1 + fill_w, BAR_Y + 6, AMBER)

    put(canvas, f"FPS {fps_real:.1f}", 470, SY + 21, GREEN, 0.37)

    # ROI indicator
    if roi_active:
        put(canvas, "ROI", 530, SY + 21, CYAN, 0.37, 1)

    put_right(canvas,
              "[P] Pause  [D] ROI  [C] Clear ROI  [R] Reselect  [E] Export  [+/-] Scale  [Q] Quit",
              WIN_W - 14, SY + 21, DIM, 0.30)


def build_dashboard(ann_frame, stats, vehicle_log, ppm,
                    frame_num, total_frames, fps_real, is_paused, video_name,
                    roi_points=None, roi_mode=False, roi_mode_points=None,
                    roi_active=False):
    canvas = np.zeros((WIN_H, WIN_W, 3), dtype=np.uint8)
    _draw_header(canvas, video_name, is_paused)
    _draw_video_panel(canvas, ann_frame, roi_points, roi_mode, roi_mode_points)
    _draw_stat_panel(canvas, stats, vehicle_log, ppm)
    _draw_statusbar(canvas, frame_num, total_frames, fps_real, roi_active)
    return canvas


# ─────────────────────────────────────────────────────────────────────────────
# DASHBOARD RUNNER
# ─────────────────────────────────────────────────────────────────────────────
class _DashboardMouse:
    """Mouse state for the dashboard window (ROI selection)."""
    def __init__(self):
        self.x = self.y = 0
        self.clicked = False


def _dashboard_mouse_cb(event, x, y, flags, state):
    state.x, state.y = x, y
    if event == cv2.EVENT_LBUTTONDOWN:
        state.clicked = True


def run_dashboard(video_path, video_fps, total_frames):
    """Run the analysis dashboard. Returns 'quit' or 'reselect'."""
    ppm     = DEFAULT_PPM
    tracker = VehicleTracker(model_path=MODEL_PATH,
                             pixel_per_meter=ppm, fps=video_fps)
    cap = cv2.VideoCapture(video_path)

    cv2.namedWindow(WIN_NAME, cv2.WINDOW_NORMAL)
    cv2.resizeWindow(WIN_NAME, WIN_W, WIN_H)

    # Mouse callback for ROI selection
    dmouse = _DashboardMouse()
    cv2.setMouseCallback(WIN_NAME, _dashboard_mouse_cb, dmouse)

    is_paused  = False
    frame_num  = 0
    fps_real   = 0.0
    t_prev     = time.time()
    last_frame = None
    last_raw   = None          # keep raw frame for coordinate mapping
    last_stats = {"total": 0, "min_speed": 0.0, "max_speed": 0.0, "avg_speed": 0.0}
    last_log   = []

    # ── ROI state ────────────────────────────────────────────────────────
    roi_mode        = False    # True khi đang chọn điểm ROI
    roi_mode_points = []       # Các điểm đã chọn (tọa độ frame gốc)
    roi_confirmed   = False    # Đã xác nhận 4 điểm

    # ── Frame timing (giữ FPS ổn định) ───────────────────────────────
    frame_delay = 1.0 / video_fps if video_fps > 0 else 1.0 / 30.0

    while True:
        if not is_paused:
            ok, raw_frame = cap.read()

            if not ok:
                # ── Video finished ────────────────────────────────────────
                canvas = build_dashboard(
                    last_frame, last_stats, last_log, ppm,
                    frame_num, total_frames, fps_real,
                    False, video_path,
                    roi_mode=roi_mode, roi_mode_points=roi_mode_points,
                    roi_active=roi_confirmed)
                # Completion banner
                msg = "  ANALYSIS COMPLETE — E: Export    R: Reselect    Q: Quit  "
                tw = cv2.getTextSize(msg, FONT, 0.48, 1)[0][0]
                mx = VIDEO_W // 2
                my = HEADER_H + CONTENT_H // 2
                fillr(canvas, mx - tw // 2 - 10, my - 22,
                              mx + tw // 2 + 10, my + 10, (20, 80, 20))
                put_center(canvas, msg, mx, my, TXT, 0.48)
                cv2.imshow(WIN_NAME, canvas)

                while True:
                    k = cv2.waitKeyEx(100)
                    if k in (ord("q"), ord("Q")):
                        cap.release()
                        cv2.destroyAllWindows()
                        return "quit"
                    if k in (ord("e"), ord("E")):
                        do_export(tracker)
                    if k in (ord("r"), ord("R")):
                        cap.release()
                        cv2.destroyAllWindows()
                        return "reselect"
                    try:
                        if cv2.getWindowProperty(WIN_NAME, cv2.WND_PROP_VISIBLE) < 1:
                            cap.release()
                            cv2.destroyAllWindows()
                            return "quit"
                    except cv2.error:
                        return "quit"
                # end completion loop

            frame_num += 1
            last_raw = raw_frame
            last_frame = tracker.process_frame(raw_frame)

            now = time.time()
            dt  = now - t_prev
            if dt > 0:
                fps_real = 0.9 * fps_real + 0.1 / dt
            t_prev = now

            if frame_num % 5 == 0:
                last_stats = tracker.get_statistics()
                last_log   = tracker.get_vehicle_log()

        # ── Handle ROI click ─────────────────────────────────────────────
        if dmouse.clicked:
            dmouse.clicked = False
            if roi_mode and len(roi_mode_points) < 4 and last_raw is not None:
                # Convert canvas coords → frame coords
                scale, ox, oy, nw, nh = _get_video_transform(last_raw)
                fx, fy = _canvas_to_frame(dmouse.x, dmouse.y, scale, ox, oy)
                fh, fw = last_raw.shape[:2]
                # Only accept if click is within the video area
                if 0 <= fx <= fw and 0 <= fy <= fh:
                    roi_mode_points.append((fx, fy))
                    print(f"[ROI]  Point {len(roi_mode_points)}: "
                          f"frame=({fx:.0f}, {fy:.0f})")
                    if len(roi_mode_points) == 4:
                        tracker.set_roi(roi_mode_points)
                        roi_confirmed = True
                        roi_mode = False
                        print("[ROI]  4 points set — perspective transform active.")

        # ── Render ───────────────────────────────────────────────────────
        canvas = build_dashboard(
            last_frame, last_stats, last_log, ppm,
            frame_num, total_frames, fps_real,
            is_paused, video_path,
            roi_mode=roi_mode, roi_mode_points=roi_mode_points,
            roi_active=roi_confirmed)
        cv2.imshow(WIN_NAME, canvas)

        # ── Frame timing: giữ đúng FPS của video ───────────────────────
        elapsed = time.time() - t_prev
        wait_ms = max(1, int((frame_delay - elapsed) * 1000))
        key = cv2.waitKeyEx(wait_ms)

        if key in (ord("q"), ord("Q")):
            break
        elif key in (ord("p"), ord("P")):
            is_paused = not is_paused
            print(f"[INFO] {'PAUSED' if is_paused else 'RESUMED'}")

        elif key in (ord("d"), ord("D")):
            # Toggle ROI draw mode
            if not roi_mode:
                roi_mode = True
                roi_mode_points = []
                roi_confirmed = False
                tracker.clear_roi()
                is_paused = True
                print("[ROI]  Draw mode ON — click 4 points on the road. "
                      "Video paused.")
            else:
                roi_mode = False
                print("[ROI]  Draw mode OFF.")

        elif key in (ord("c"), ord("C")):
            # Clear ROI
            roi_mode = False
            roi_mode_points = []
            roi_confirmed = False
            tracker.clear_roi()
            print("[ROI]  ROI cleared.")

        elif key in (ord("r"), ord("R")):
            cap.release()
            cv2.destroyAllWindows()
            return "reselect"
        elif key in (ord("e"), ord("E")):
            do_export(tracker)
        elif key in (ord("+"), ord("=")):
            ppm = min(150.0, ppm + 1.0)
            tracker.update_config(pixel_per_meter=ppm)
            print(f"[INFO] Scale = {ppm:.1f} px/m")
        elif key == ord("-"):
            ppm = max(1.0, ppm - 1.0)
            tracker.update_config(pixel_per_meter=ppm)
            print(f"[INFO] Scale = {ppm:.1f} px/m")

        try:
            if cv2.getWindowProperty(WIN_NAME, cv2.WND_PROP_VISIBLE) < 1:
                break
        except cv2.error:
            break

    cap.release()
    cv2.destroyAllWindows()
    return "quit"


# ─────────────────────────────────────────────────────────────────────────────
# ENTRY POINT
# ─────────────────────────────────────────────────────────────────────────────
def main():
    ensure_dir(REPORT_DIR)
    ensure_dir(VIDEO_DIR)

    while True:
        vpath, vfps, vtotal = run_picker()

        if vpath is None:
            print("[INFO] Exiting.")
            break

        print(f"[INFO] Video  : {vpath}")
        print(f"[INFO] FPS={vfps:.1f}  Frames={vtotal:,}")

        result = run_dashboard(vpath, vfps, vtotal)

        if result == "quit":
            break
        # "reselect" → loop back to picker


if __name__ == "__main__":
    main()