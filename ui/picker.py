"""
ui/picker.py — Video selection screen.

Hiển thị danh sách video trong thư mục VIDEO_DIR và cho phép người dùng chọn.
Click để chọn · Click nút START để bắt đầu phân tích · Click Thoát để thoát.
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
_LX1, _LX2  = 20, 1000
_COL_H       = 34
_COL_Y       = HEADER_H + 20 + _COL_H       # y của dòng tiêu đề cột
_ITEM_H      = 60
_LY2         = WIN_H - STATUSBAR_H - 20
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
        20, 36, TXT, 0.65, 1, FONTD)
    put_right(canvas, f"{len(videos)} file(s) in ./{VIDEO_DIR}/",
              W - 20, 36, DIM, 0.45)

    # ── Danh sách video ───────────────────────────────────────────────────────
    LX1, LX2 = _LX1, _LX2
    LY1, LY2 = HEADER_H + 20, _LY2
    COL_Y, ITEM_H = _COL_Y, _ITEM_H

    fillr(canvas, LX1, LY1, LX2, COL_Y, (48, 48, 48))
    for label, x_off in [("#", 10), ("FILENAME", 45), ("RES", 560),
                          ("DUR", 680), ("FPS", 800), ("SIZE", 860)]:
        put(canvas, label, LX1 + x_off, COL_Y - 10, LBL, 0.40)
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

            ty = row_y + ITEM_H // 2 + 10
            nm = v["name"] if len(v["name"]) <= 54 else v["name"][:52] + ".."
            name_color = AMBER if vi == sel else TXT
            put(canvas, str(vi + 1),                    LX1 + 10,  ty, DIM,        0.45)
            put(canvas, nm,                              LX1 + 45,  ty, name_color, 0.52)
            put(canvas, f"{v['width']}x{v['height']}",  LX1 + 560, ty, DIM,        0.48)
            put(canvas, fmt_duration(v["duration"]),     LX1 + 680, ty, DIM,        0.48)
            put(canvas, f"{v['fps']:.0f}",               LX1 + 800, ty, DIM,        0.48)
            put(canvas, fmt_size(v["size"]),             LX1 + 860, ty, DIM,        0.48)
            hline(canvas, LX1, LX2, row_y + ITEM_H, DIV)

    bordr(canvas, LX1, LY1, LX2, LY2, DIV)

    # ── Info panel (phải) ─────────────────────────────────────────────────────
    RX1, RX2 = LX2 + 24, W - 24
    fillr(canvas, RX1, LY1, RX2, LY2, PANEL)
    bordr(canvas, RX1, LY1, RX2, LY2, DIV)

    iy = LY1 + 20
    put(canvas, "VIDEO INFORMATION", RX1 + 16, iy, LBL, 0.45)
    hline(canvas, RX1 + 1, RX2 - 1, iy + 12, DIV)
    iy += 34

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
            put(canvas, label, RX1 + 16, iy, DIM, 0.45)
            disp = value if len(value) <= 26 else value[:24] + ".."
            put(canvas, disp, RX1 + 16, iy + 24, TXT, 0.52)
            iy += 56

    # Nút Start
    BY1 = LY2 - 90
    BY2 = LY2 - 20
    BX1 = RX1 + 20
    BX2 = RX2 - 20
    can_start  = 0 <= sel < len(videos)
    btn_color  = AMBER if can_start else DIV
    text_color = BG    if can_start else DIM
    fillr(canvas, BX1, BY1, BX2, BY2, btn_color)
    put_center(canvas, "START ANALYSIS", (BX1 + BX2) // 2, BY1 + 42,
               text_color, 0.70, 1, FONTD)

    # ── Status bar ────────────────────────────────────────────────────────────
    fillr(canvas, 0, H - STATUSBAR_H, W, H, HDR)
    hline(canvas, 0, W, H - STATUSBAR_H, DIV)
    put(canvas,
        "Click để chọn video     Nhấn nút START để bắt đầu phân tích",
        20, H - 14, DIM, 0.45)

    # Nút Thoát
    from ui.theme import get_text_width
    tw = get_text_width("Thoát", 0.50, 1)
    bw = tw + 40
    bh = 40
    qx1 = W - 20 - bw
    qy1 = H - STATUSBAR_H + 10
    qx2 = qx1 + bw
    qy2 = qy1 + bh
    fillr(canvas, qx1, qy1, qx2, qy2, PANEL)
    bordr(canvas, qx1, qy1, qx2, qy2, DIV)
    put_center(canvas, "Thoát", qx1 + bw // 2, qy1 + 28, TXT, 0.50)

    # Nút Import
    itw = get_text_width("Thêm Video", 0.50, 1)
    ibw = itw + 40
    ix1 = qx1 - 20 - ibw
    iy1 = qy1
    ix2 = ix1 + ibw
    iy2 = qy2
    fillr(canvas, ix1, iy1, ix2, iy2, PANEL)
    bordr(canvas, ix1, iy1, ix2, iy2, DIV)
    put_center(canvas, "Thêm Video", ix1 + ibw // 2, iy1 + 28, TXT, 0.50)

    return (BX1, BX2, BY1, BY2), (qx1, qx2, qy1, qy2), (ix1, ix2, iy1, iy2)


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
        btn_start, btn_quit, btn_import = _draw(canvas, videos, sel, hov, scroll)
        bx1, bx2, by1, by2 = btn_start
        qx1, qx2, qy1, qy2 = btn_quit
        ix1, ix2, iy1, iy2 = btn_import

        # Xử lý click
        if ms.clicked:
            ms.clicked = False
            
            # Click Quit
            if qx1 <= ms.x <= qx2 and qy1 <= ms.y <= qy2:
                cv2.destroyAllWindows()
                return None, 0, 0
                
            # Click Import
            if ix1 <= ms.x <= ix2 and iy1 <= ms.y <= iy2:
                import subprocess
                cmd = [
                    'python3', '-c',
                    'import tkinter as tk; from tkinter import filedialog; root = tk.Tk(); root.attributes("-topmost", True); root.withdraw(); path = filedialog.askopenfilename(title="Chọn Video"); print(path)'
                ]
                try:
                    out_path = subprocess.check_output(cmd, text=True).strip()
                    if out_path and os.path.exists(out_path):
                        import shutil
                        import time
                        from ui.theme import get_text_width
                        
                        basename = os.path.basename(out_path)
                        dest_path = os.path.join(VIDEO_DIR, basename)
                        if os.path.exists(dest_path):
                            name, ext = os.path.splitext(basename)
                            dest_path = os.path.join(VIDEO_DIR, f"{name}_{int(time.time())}{ext}")
                        
                        print(f"[INFO] Copying {out_path} to {dest_path}...")
                        
                        msg = "Đang sao chép video, vui lòng đợi..."
                        tw = get_text_width(msg, 0.60, 1)
                        fillr(canvas, WIN_W//2 - tw//2 - 30, WIN_H//2 - 40, WIN_W//2 + tw//2 + 30, WIN_H//2 + 40, (0, 80, 0))
                        put_center(canvas, msg, WIN_W//2, WIN_H//2 + 10, TXT, 0.60)
                        cv2.imshow(WIN_NAME, canvas)
                        cv2.waitKeyEx(10)
                        
                        shutil.copy2(out_path, dest_path)
                        print("[INFO] Sao chép hoàn tất.")
                        
                        videos = scan_videos(VIDEO_DIR)
                        for idx, v in enumerate(videos):
                            if v["path"] == dest_path:
                                sel = idx
                                scroll = max(0, sel - _MAX_VIS // 2)
                                break
                except Exception as e:
                    print(f"[ERR] Dialog failed: {e}")

            # Click vào danh sách video — chỉ chọn, không tự khởi động
            if hov >= 0:
                sel = hov

            # Click nút START
            if bx1 <= ms.x <= bx2 and by1 <= ms.y <= by2 and 0 <= sel < len(videos):
                v = videos[sel]
                cv2.destroyAllWindows()
                return v["path"], v["fps"], v["frames"]

        cv2.imshow(WIN_NAME, canvas)
        key = cv2.waitKeyEx(33)

        # Chỉ giữ phím Q / ESC để thoát
        if key in (ord("q"), ord("Q"), 27):
            cv2.destroyAllWindows()
            return None, 0, 0

        try:
            if cv2.getWindowProperty(WIN_NAME, cv2.WND_PROP_VISIBLE) < 1:
                cv2.destroyAllWindows()
                return None, 0, 0
        except cv2.error:
            return None, 0, 0
