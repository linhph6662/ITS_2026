"""
ui/theme.py — Shared layout constants, color palette và drawing primitives.

Tất cả màu sắc dùng định dạng BGR (OpenCV).
"""

import cv2
import numpy as np

# ─────────────────────────────────────────────────────────────────────────────
# WINDOW LAYOUT
# ─────────────────────────────────────────────────────────────────────────────
WIN_W       = 1920
WIN_H       = 1080
HEADER_H    = 56
STATUSBAR_H = 60
VIDEO_W     = int(WIN_W * 0.60)              # 1152 px
STAT_X      = VIDEO_W
STAT_W      = WIN_W - VIDEO_W               # 768 px
CONTENT_H   = WIN_H - HEADER_H - STATUSBAR_H   # 964 px

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
# FONTS
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


from PIL import Image, ImageDraw, ImageFont
import os

_pil_font_cache = {}

def get_pil_font(scale, thickness):
    size = max(18, int(scale * 55))
    if size not in _pil_font_cache:
        font = None
        font_paths = [
            "/System/Library/Fonts/Supplemental/Arial Unicode.ttf",
            "/Library/Fonts/Arial Unicode.ttf",
            "/System/Library/Fonts/Helvetica.ttc",
            "C:\\Windows\\Fonts\\arial.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
        ]
        for p in font_paths:
            if os.path.exists(p):
                try:
                    font = ImageFont.truetype(p, size)
                    break
                except:
                    pass
        if font is None:
            font = ImageFont.load_default()
        _pil_font_cache[size] = font
    return _pil_font_cache[size]

def put(img, s, x, y, color=None, scale=0.43, thickness=1, font=None):
    """Viết văn bản căn trái."""
    if color is None:
        color = TXT
    s = str(s)
        
    pil_font = get_pil_font(scale, thickness)
    if hasattr(pil_font, 'getbbox'):
        left, top, right, bottom = pil_font.getbbox(s, anchor="ls")
    else:
        left, top, right, bottom = pil_font.getbbox(s)
        
    w, h = right - left, bottom - top
    if w <= 0 or h <= 0: return
    
    pad = 10
    y1 = max(0, int(y) + top - pad)
    y2 = min(img.shape[0], int(y) + bottom + pad)
    x1 = max(0, int(x) + left - pad)
    x2 = min(img.shape[1], int(x) + right + pad)
    if y2 <= y1 or x2 <= x1: return
    
    roi = img[y1:y2, x1:x2]
    pil_img = Image.fromarray(cv2.cvtColor(roi, cv2.COLOR_BGR2RGB))
    draw = ImageDraw.Draw(pil_img)
    color_rgb = (color[2], color[1], color[0])
    
    draw_x = int(x) - x1
    draw_y = int(y) - y1
    draw.text((draw_x, draw_y), s, font=pil_font, fill=color_rgb, anchor="ls")
    img[y1:y2, x1:x2] = cv2.cvtColor(np.array(pil_img), cv2.COLOR_RGB2BGR)

def get_text_width(s, scale, thickness, font=None):
    s = str(s)
    pil_font = get_pil_font(scale, thickness)
    if hasattr(pil_font, 'getlength'):
        return int(pil_font.getlength(s))
    elif hasattr(pil_font, 'getbbox'):
        return pil_font.getbbox(s)[2] - pil_font.getbbox(s)[0]
    else:
        return pil_font.getsize(s)[0]

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
