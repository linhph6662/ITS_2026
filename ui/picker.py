"""
ui/picker.py — Video selection screen.

Hiển thị danh sách video trong thư mục VIDEO_DIR và cho phép người dùng chọn.
Phím: J/K hoặc ↑/↓ điều hướng · Enter/Double-click xác nhận · Q thoát.
"""

import os

import cv2
import numpy as np

from ui.theme import (
    WIN_W, WIN_H, HEADER_H, STATUSBAR_H,
    BG, HDR, PANEL, DIV, TXT, DIM, LBL, AMBER,
    SEL_BG, HOV_BG,
    FONT, FONTD,
    fillr, bordr, hline, put, put_right, put_center,
    fmt_size, fmt_duration,
)

VIDEO_DIR = "video"

# ── Layout constants ──────────────────────────────────────────────────────────
_LX1, _LX2  = 18, 760
_COL_H       = 26
_COL_Y       = HEADER_H + 14 + _COL_H       # y của dòng tiêu đề cột
_ITEM_H      = 46
_LY2         = WIN_H - STATUSBAR_H - 14
_MAX_VIS     = max(1, (_LY2 - _COL_Y) // _ITEM_H)

WIN_NAME = "VEHICLE ANALYSIS SYSTEM"


# ─────────────────────────────────────────────────────────────────────────────
# MOUSE STATE
# ─────────────────────────────────────────────────────────────────────────────

class _MouseState:
    def __init__(self):
        self.x = self.y = 0
        self.clicked = False


def _mouse_cb(event, x, y, flags, ms: _MouseState):
    ms.x, ms.y = x, y
    if event == cv2.EVENT_LBUTTONDOWN:
        ms.clicked = True


# ─────────────────────────────────────────────────────────────────────────────
# VIDEO SCANNING
# ─────────────────────────────────────────────────────────────────────────────

def scan_videos(video_dir: str) -> list:
    """
    Quét thư mục và trả về metadata của tất cả video hợp lệ.

    Args:
        video_dir: Đường dẫn thư mục chứa video.

    Returns:
        List[dict]: [{name, path, size, fps, frames, width, height, duration}]
    """
    items = []
    if not os.path.isdir(video_dir):
        return items

    for filename in sorted(os.listdir(video_dir)):
        if not filename.lower().endswith((".mp4", ".avi", ".mov", ".mkv")):
            continue
        path = os.path.join(video_dir, filename)
        size = os.path.getsize(path)
        cap  = cv2.VideoCapture(path)
        fps    = cap.get(cv2.CAP_PROP_FPS) or 30.0
        frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        width  = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        cap.release()
        items.append({
            "name":     filename,
            "path":     path,
            "size":     size,
            "fps":      fps,
            "frames":   frames,
            "width":    width,
            "height":   height,
            "duration": frames / fps if fps > 0 else 0,
        })
    return items


# ─────────────────────────────────────────────────────────────────────────────
# DRAWING
# ─────────────────────────────────────────────────────────────────────────────

def _draw(canvas: np.ndarray, videos: list, sel: int, hov: int, scroll: int):
    """Render toàn bộ màn hình chọn video."""
    W, H = WIN_W, WIN_H
    canvas[:] = BG

    # ── Header ───────────────────────────────────────────────────────────────
    fillr(canvas, 0, 0, W, HEADER_H, HDR)
    hline(canvas, 0, W, HEADER_H, AMBER, 2)
    put(canvas, "VEHICLE ANALYSIS SYSTEM  //  Select Input Video",
        14, 25, TXT, 0.52, 1, FONTD)
    put_right(canvas, f"{len(videos)} file(s) in ./{VIDEO_DIR}/",
              W - 14, 25, DIM, 0.37)

    # ── Danh sách video ───────────────────────────────────────────────────────
    LX1, LX2 = _LX1, _LX2
    LY1, LY2 = HEADER_H + 14, _LY2
    COL_Y, ITEM_H = _COL_Y, _ITEM_H

    fillr(canvas, LX1, LY1, LX2, COL_Y, (48, 48, 48))
    for label, x_off in [("#", 8), ("FILENAME", 34), ("RES", 430),
                          ("DUR", 518), ("FPS", 608), ("SIZE", 650)]:
        put(canvas, label, LX1 + x_off, COL_Y - 7, LBL, 0.33)
    hline(canvas, LX1, LX2, COL_Y, DIV)

    if not videos:
        put(canvas, f"No video files found in  ./{VIDEO_DIR}/",
            LX1 + 16, COL_Y + 40, DIM, 0.44)
    else:
        for idx, v in enumerate(videos[scroll: scroll + _MAX_VIS]):
            vi    = idx + scroll
            row_y = COL_Y + idx * ITEM_H

            if vi == sel:
                fillr(canvas, LX1, row_y, LX2, row_y + ITEM_H, SEL_BG)
                fillr(canvas, LX1, row_y, LX1 + 3, row_y + ITEM_H, AMBER)
            elif vi == hov:
                fillr(canvas, LX1, row_y, LX2, row_y + ITEM_H, HOV_BG)

            ty = row_y + ITEM_H // 2 + 7
            nm = v["name"] if len(v["name"]) <= 54 else v["name"][:52] + ".."
            name_color = AMBER if vi == sel else TXT
            put(canvas, str(vi + 1),                    LX1 + 8,   ty, DIM,        0.35)
            put(canvas, nm,                              LX1 + 34,  ty, name_color, 0.42)
            put(canvas, f"{v['width']}x{v['height']}",  LX1 + 430, ty, DIM,        0.37)
            put(canvas, fmt_duration(v["duration"]),     LX1 + 518, ty, DIM,        0.37)
            put(canvas, f"{v['fps']:.0f}",               LX1 + 608, ty, DIM,        0.37)
            put(canvas, fmt_size(v["size"]),             LX1 + 650, ty, DIM,        0.37)
            hline(canvas, LX1, LX2, row_y + ITEM_H, DIV)

    bordr(canvas, LX1, LY1, LX2, LY2, DIV)

    # ── Info panel (phải) ─────────────────────────────────────────────────────
    RX1, RX2 = LX2 + 18, W - 18
    fillr(canvas, RX1, LY1, RX2, LY2, PANEL)
    bordr(canvas, RX1, LY1, RX2, LY2, DIV)

    iy = LY1 + 14
    put(canvas, "VIDEO INFORMATION", RX1 + 12, iy, LBL, 0.36)
    hline(canvas, RX1 + 1, RX2 - 1, iy + 8, DIV)
    iy += 26

    if 0 <= sel < len(videos):
        v = videos[sel]
        for label, value in [
            ("Name",       v["name"]),
            ("Resolution", f"{v['width']} x {v['height']}"),
            ("Duration",   fmt_duration(v["duration"])),
            ("Frames",     f"{v['frames']:,}"),
            ("FPS",        f"{v['fps']:.1f}"),
            ("File size",  fmt_size(v["size"])),
        ]:
            put(canvas, label, RX1 + 12, iy, DIM, 0.36)
            disp = value if len(value) <= 26 else value[:24] + ".."
            put(canvas, disp, RX1 + 12, iy + 18, TXT, 0.41)
            iy += 42

    # Nút Start
    BY1 = LY2 - 58
    BY2 = LY2 - 12
    BX1 = RX1 + 12
    BX2 = RX2 - 12
    can_start  = 0 <= sel < len(videos)
    btn_color  = AMBER if can_start else DIV
    text_color = BG    if can_start else DIM
    fillr(canvas, BX1, BY1, BX2, BY2, btn_color)
    put_center(canvas, "START ANALYSIS", (BX1 + BX2) // 2, BY1 + 28,
               text_color, 0.50, 1, FONTD)

    # ── Status bar ────────────────────────────────────────────────────────────
    fillr(canvas, 0, H - STATUSBAR_H, W, H, HDR)
    hline(canvas, 0, W, H - STATUSBAR_H, DIV)
    put(canvas,
        "Click to select     Double-click / Enter to start"
        "     J/K or ↑/↓ to navigate     Q to quit",
        14, H - 10, DIM, 0.36)

    return BX1, BX2, BY1, BY2


# ─────────────────────────────────────────────────────────────────────────────
# PUBLIC API
# ─────────────────────────────────────────────────────────────────────────────

def run_picker() -> tuple:
    """
    Hiển thị màn hình chọn video.

    Returns:
        (video_path, fps, total_frames) hoặc (None, 0, 0) nếu thoát.
    """
    videos = scan_videos(VIDEO_DIR)
    ms     = _MouseState()
    sel    = 0 if videos else -1
    hov    = -1
    scroll = 0

    cv2.namedWindow(WIN_NAME, cv2.WINDOW_NORMAL)
    cv2.resizeWindow(WIN_NAME, WIN_W, WIN_H)
    cv2.setMouseCallback(WIN_NAME, _mouse_cb, ms)

    while True:
        # Tính hover từ vị trí chuột hiện tại
        hov = -1
        if _LX1 <= ms.x <= _LX2 and _COL_Y <= ms.y:
            ri = (ms.y - _COL_Y) // _ITEM_H + scroll
            if 0 <= ri < len(videos):
                hov = ri

        canvas = np.zeros((WIN_H, WIN_W, 3), dtype=np.uint8)
        bx1, bx2, by1, by2 = _draw(canvas, videos, sel, hov, scroll)

        # Xử lý click
        if ms.clicked:
            ms.clicked = False
            if hov >= 0:
                if hov == sel:   # Double-click
                    v = videos[sel]
                    cv2.destroyAllWindows()
                    return v["path"], v["fps"], v["frames"]
                sel = hov
            if bx1 <= ms.x <= bx2 and by1 <= ms.y <= by2 and 0 <= sel < len(videos):
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
                if sel >= scroll + _MAX_VIS:
                    scroll = sel - _MAX_VIS + 1

        try:
            if cv2.getWindowProperty(WIN_NAME, cv2.WND_PROP_VISIBLE) < 1:
                cv2.destroyAllWindows()
                return None, 0, 0
        except cv2.error:
            return None, 0, 0
