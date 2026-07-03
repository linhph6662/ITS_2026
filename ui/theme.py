"""
ui/theme.py — Shared layout constants, color palette và drawing primitives.

Tất cả màu sắc dùng định dạng BGR (OpenCV).
Layout tự động điều chỉnh theo độ phân giải màn hình thực tế.
"""

import os
import cv2
import numpy as np

# ─────────────────────────────────────────────────────────────────────────────
# AUTO-DETECT SCREEN RESOLUTION
# ─────────────────────────────────────────────────────────────────────────────

def _detect_screen_size(max_ratio: float = 0.92) -> tuple:
    """
    Tự phát hiện độ phân giải màn hình và trả về (width, height) cho cửa sổ.
    Dùng 92% chiều cao màn hình để tránh tràn taskbar.
    Trả về (1920, 1080) nếu không phát hiện được.
    """
    sw, sh = 1920, 1080
    try:
        import ctypes
        # Lấy DPI-aware resolution (Windows)
        ctypes.windll.shcore.SetProcessDpiAwareness(2)
        sw = ctypes.windll.user32.GetSystemMetrics(0)
        sh = ctypes.windll.user32.GetSystemMetrics(1)
    except Exception:
        try:
            import subprocess
            # Fallback: dùng xrandr trên Linux
            out = subprocess.check_output(
                ["xrandr", "--current"], stderr=subprocess.DEVNULL, text=True)
            for line in out.splitlines():
                if " connected" in line and "x" in line:
                    import re
                    m = re.search(r"(\d+)x(\d+)", line)
                    if m:
                        sw, sh = int(m.group(1)), int(m.group(2))
                        break
        except Exception:
            pass

    # Tỷ lệ 16:9 → đảm bảo WIN_W luôn theo tỉ lệ chuẩn
    target_h = int(sh * max_ratio)
    target_w = int(target_h * 16 / 9)

    # Không vượt quá màn hình vật lý
    if target_w > int(sw * max_ratio):
        target_w = int(sw * max_ratio)
        target_h = int(target_w * 9 / 16)

    # Làm tròn xuống bội số 4 để tránh lỗi rendering
    target_w = (target_w // 4) * 4
    target_h = (target_h // 4) * 4

    # Tối thiểu 960×540
    target_w = max(target_w, 960)
    target_h = max(target_h, 540)

    return target_w, target_h


# Tính kích thước cửa sổ một lần khi module load
WIN_W, WIN_H = _detect_screen_size()

# Hệ số scale so với thiết kế gốc 1920×1080
_SX = WIN_W / 1920.0
_SY = WIN_H / 1080.0

# ─────────────────────────────────────────────────────────────────────────────
# WINDOW LAYOUT  (tất cả tính theo tỉ lệ màn hình)
# ─────────────────────────────────────────────────────────────────────────────
HEADER_H    = max(40, int(56  * _SY))
STATUSBAR_H = max(44, int(60  * _SY))
VIDEO_W     = int(WIN_W * 0.60)          # 60% chiều rộng cho video
STAT_X      = VIDEO_W
STAT_W      = WIN_W - VIDEO_W
CONTENT_H   = WIN_H - HEADER_H - STATUSBAR_H

# ─────────────────────────────────────────────────────────────────────────────
# COLOR PALETTE (BGR)
# ─────────────────────────────────────────────────────────────────────────────
BG      = ( 22,  22,  22)   # Nền chính
PANEL   = ( 32,  32,  32)   # Nền panel thống kê
HDR     = ( 42,  42,  42)   # Thanh header / section header
DIV     = ( 58,  58,  58)   # Đường kẻ phân cách
TXT     = (210, 210, 210)   # Văn bản chính
DIM     = (105, 105, 105)   # Văn bản phụ / mờ
LBL     = (148, 148, 148)   # Nhãn cột / caption
AMBER   = (  0, 160, 255)   # Nhấn màu cam      RGB 255,160,0
GREEN   = ( 80, 175,  80)   # Tốc độ bình thường
YELLOW  = ( 40, 200, 210)   # Tốc độ cảnh báo   RGB 210,200,40
RED     = ( 55,  55, 210)   # Tốc độ cao         RGB 210,55,55
TEAL    = (150, 165,  55)   # Track ID           RGB 55,165,150
CYAN    = (255, 255,   0)   # Điểm ROI           RGB 0,255,255
ROI_CLR = (  0, 180, 255)   # Đa giác ROI        RGB 255,180,0
SEL_BG  = ( 50,  38,  18)   # Nền dòng được chọn
HOV_BG  = ( 40,  40,  40)   # Nền dòng hover
ALT_ROW = ( 36,  36,  36)   # Nền dòng xen kẽ

# ─────────────────────────────────────────────────────────────────────────────
# FONTS (legacy — không dùng trực tiếp nữa, giữ để tương thích)
# ─────────────────────────────────────────────────────────────────────────────
FONT  = cv2.FONT_HERSHEY_SIMPLEX
FONTD = cv2.FONT_HERSHEY_DUPLEX

# ─────────────────────────────────────────────────────────────────────────────
# DRAWING PRIMITIVES
# ─────────────────────────────────────────────────────────────────────────────

def fillr(img, x1, y1, x2, y2, color):
    """Vẽ hình chữ nhật đặc."""
    cv2.rectangle(img, (int(x1), int(y1)), (int(x2), int(y2)), color, -1)


def bordr(img, x1, y1, x2, y2, color, thickness=1):
    """Vẽ viền hình chữ nhật."""
    cv2.rectangle(img, (int(x1), int(y1)), (int(x2), int(y2)), color, thickness)


def hline(img, x1, x2, y, color=None, thickness=1):
    """Vẽ đường nằm ngang."""
    if color is None:
        color = DIV
    cv2.line(img, (int(x1), int(y)), (int(x2), int(y)), color, thickness)


def vline(img, x, y1, y2, color=None, thickness=1):
    """Vẽ đường thẳng đứng."""
    if color is None:
        color = DIV
    cv2.line(img, (int(x), int(y1)), (int(x), int(y2)), color, thickness)


# ─────────────────────────────────────────────────────────────────────────────
# PIL TEXT RENDERING (anti-aliased, scale-aware)
# ─────────────────────────────────────────────────────────────────────────────

from PIL import Image, ImageDraw, ImageFont

_pil_font_cache: dict = {}

# Danh sách font ưu tiên
_FONT_CANDIDATES = [
    "C:\\Windows\\Fonts\\segoeui.ttf",   # Windows — Segoe UI (sắc nét nhất)
    "C:\\Windows\\Fonts\\arial.ttf",     # Windows — Arial
    "C:\\Windows\\Fonts\\calibri.ttf",   # Windows — Calibri
    "/System/Library/Fonts/Supplemental/Arial Unicode.ttf",  # macOS
    "/Library/Fonts/Arial Unicode.ttf",
    "/System/Library/Fonts/Helvetica.ttc",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",       # Linux
    "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
]

_selected_font_path: str | None = None

def _find_font() -> str | None:
    global _selected_font_path
    if _selected_font_path is not None:
        return _selected_font_path
    for p in _FONT_CANDIDATES:
        if os.path.exists(p):
            _selected_font_path = p
            return p
    return None


def get_pil_font(scale: float, thickness: int = 1) -> ImageFont.FreeTypeFont:
    """
    Trả về PIL font với size đã scale theo màn hình.
    scale là đơn vị tương đối so với thiết kế 1920px.
    """
    # Nhân thêm _SX để font tự scale theo kích thước màn hình
    base_size = max(10, int(scale * 55 * _SX))
    # Làm tròn đến số lẻ gần nhất để tránh rounding artifacts
    key = base_size

    if key not in _pil_font_cache:
        font_path = _find_font()
        font = None
        if font_path:
            try:
                font = ImageFont.truetype(font_path, base_size)
            except Exception:
                font = None
        if font is None:
            # Fallback: PIL default (không đẹp nhưng luôn hoạt động)
            try:
                font = ImageFont.load_default(size=base_size)
            except TypeError:
                font = ImageFont.load_default()
        _pil_font_cache[key] = font

    return _pil_font_cache[key]


def put(img, s, x, y, color=None, scale=0.43, thickness=1, font=None):
    """
    Viết văn bản căn trái lên canvas OpenCV dùng PIL (anti-aliased).
    Anchor: baseline-left tại (x, y).
    """
    if color is None:
        color = TXT
    s = str(s)
    if not s:
        return

    pil_font = get_pil_font(scale, thickness)

    # Đo kích thước text
    try:
        bbox = pil_font.getbbox(s, anchor="ls")
        left, top, right, bottom = bbox
    except Exception:
        try:
            w_t, h_t = pil_font.getsize(s)
            left, top, right, bottom = 0, -h_t, w_t, 0
        except Exception:
            return

    w, h = right - left, bottom - top
    if w <= 0 or h <= 0:
        return

    # Vùng ảnh cần vẽ (có padding để tránh clip)
    pad = 4
    ix = int(x) + left - pad
    iy = int(y) + top  - pad
    iw = w + pad * 2
    ih = h + pad * 2

    # Clamp vào canvas
    img_h, img_w = img.shape[:2]
    x1 = max(0, ix)
    y1 = max(0, iy)
    x2 = min(img_w, ix + iw)
    y2 = min(img_h, iy + ih)
    if x2 <= x1 or y2 <= y1:
        return

    # Trích vùng canvas → PIL → vẽ text → đưa lại
    roi = img[y1:y2, x1:x2]
    pil_img = Image.fromarray(cv2.cvtColor(roi, cv2.COLOR_BGR2RGB))
    draw = ImageDraw.Draw(pil_img)
    color_rgb = (int(color[2]), int(color[1]), int(color[0]))

    # Tọa độ vẽ trong patch (bù offset)
    draw_x = int(x) - x1
    draw_y = int(y) - y1
    draw.text((draw_x, draw_y), s, font=pil_font, fill=color_rgb, anchor="ls")
    img[y1:y2, x1:x2] = cv2.cvtColor(np.array(pil_img), cv2.COLOR_RGB2BGR)


def get_text_width(s: str, scale: float, thickness: int = 1, font=None) -> int:
    """Trả về chiều rộng pixel của chuỗi s với font/scale cho trước."""
    s = str(s)
    if not s:
        return 0
    pil_font = get_pil_font(scale, thickness)
    try:
        if hasattr(pil_font, "getlength"):
            return int(pil_font.getlength(s))
        bbox = pil_font.getbbox(s)
        return int(bbox[2] - bbox[0])
    except Exception:
        return len(s) * int(scale * 30 * _SX)


def put_right(img, s, rx, y, color=None, scale=0.43, thickness=1):
    """Viết văn bản căn phải theo tọa độ rx."""
    if color is None:
        color = TXT
    s = str(s)
    w = get_text_width(s, scale, thickness)
    put(img, s, int(rx) - w, y, color, scale, thickness)


def put_center(img, s, cx, y, color=None, scale=0.43, thickness=1, font=None):
    """Viết văn bản căn giữa theo tọa độ cx."""
    if color is None:
        color = TXT
    s = str(s)
    w = get_text_width(s, scale, thickness, font)
    put(img, s, int(cx) - w // 2, y, color, scale, thickness, font)


# ─────────────────────────────────────────────────────────────────────────────
# FORMAT UTILITIES
# ─────────────────────────────────────────────────────────────────────────────

def fmt_size(b: int) -> str:
    """Định dạng kích thước file (B/KB/MB/GB)."""
    for unit in ("B", "KB", "MB", "GB"):
        if b < 1024:
            return f"{b:.0f} {unit}"
        b /= 1024
    return f"{b:.1f} GB"


def fmt_duration(secs: float) -> str:
    """Định dạng thời lượng (M:SS hoặc H:MM:SS)."""
    h = int(secs // 3600)
    m = int((secs % 3600) // 60)
    s = int(secs % 60)
    return f"{h}:{m:02d}:{s:02d}" if h else f"{m}:{s:02d}"
