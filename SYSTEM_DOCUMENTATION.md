# 🚗 Vehicle Analysis System — Tài Liệu Hệ Thống Chi Tiết

> **Phiên bản**: 2.0  
> **Ngôn ngữ**: Python 3.10+  
> **Giao diện**: OpenCV (Desktop GUI)  
> **Mục tiêu**: Phát hiện, theo dõi, đếm và đo tốc độ phương tiện từ video camera giao thông

---

## Mục lục

1. [Tổng quan kiến trúc](#1-tổng-quan-kiến-trúc)
2. [Cấu trúc thư mục](#2-cấu-trúc-thư-mục)
3. [Cài đặt & Chạy](#3-cài-đặt--chạy)
4. [Luồng hoạt động của hệ thống](#4-luồng-hoạt-động-của-hệ-thống)
5. [Chi tiết từng module](#5-chi-tiết-từng-module)
   - [main.py — Giao diện & Điều phối](#51-mainpy--giao-diện--điều-phối)
   - [tracker.py — Nhân xử lý](#52-trackerpy--nhân-xử-lý)
   - [utils.py — Tiện ích](#53-utilspy--tiện-ích)
   - [bytetrack.yaml — Cấu hình Tracker](#54-bytетrackyaml--cấu-hình-tracker)
6. [Tính năng ROI & Perspective Transform](#6-tính-năng-roi--perspective-transform)
7. [Cơ chế đếm xe (Counting Line)](#7-cơ-chế-đếm-xe-counting-line)
8. [Thuật toán đo tốc độ](#8-thuật-toán-đo-tốc-độ)
9. [Pipeline xử lý mỗi frame](#9-pipeline-xử-lý-mỗi-frame)
10. [Giao diện Dashboard](#10-giao-diện-dashboard)
11. [Phím tắt & Điều khiển](#11-phím-tắt--điều-khiển)
12. [Xuất báo cáo Excel](#12-xuất-báo-cáo-excel)
13. [Các vấn đề đã giải quyết & Thiết kế quyết định](#13-các-vấn-đề-đã-giải-quyết--thiết-kế-quyết-định)
14. [Thông số kỹ thuật](#14-thông-số-kỹ-thuật)

---

## 1. Tổng quan kiến trúc

```
┌─────────────────────────────────────────────────────────┐
│                     main.py (UI Layer)                   │
│  ┌─────────────┐  ┌──────────────┐  ┌────────────────┐  │
│  │ Video Picker│  │  Dashboard   │  │  ROI Selector  │  │
│  │  (chọn file)│  │  (hiển thị)  │  │  (vẽ 4 điểm)  │  │
│  └──────┬──────┘  └──────┬───────┘  └───────┬────────┘  │
└─────────┼────────────────┼──────────────────┼───────────┘
          │                │                  │
          ▼                ▼                  ▼
┌─────────────────────────────────────────────────────────┐
│                  tracker.py (Core Logic)                 │
│                                                          │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌────────┐  │
│  │  YOLO    │  │ByteTrack │  │Perspective│  │Counting│  │
│  │Detection │→ │Tracking  │→ │Transform  │→ │  Line  │  │
│  └──────────┘  └──────────┘  └──────────┘  └────────┘  │
└─────────────────────────────────────────────────────────┘
          │
          ▼
┌─────────────────────────────────────────────────────────┐
│                    utils.py (Utilities)                  │
│         calculate_speed │ smooth_speed │ export_excel     │
└─────────────────────────────────────────────────────────┘
```

### Hai luồng giao diện

| Giao diện | File | Cách chạy | Mô tả |
|---|---|---|---|
| **Desktop GUI** | `main.py` | `python main.py` | OpenCV window, phím tắt, ROI |
| **Web App** | `app.py` | `streamlit run app.py` | Trình duyệt, slider, upload |

---

## 2. Cấu trúc thư mục

```
ITSS/
│
├── main.py              # Giao diện desktop (OpenCV)
├── app.py               # Giao diện web (Streamlit)
├── tracker.py           # Core: detect + track + speed + ROI
├── utils.py             # Tính tốc độ, format, xuất Excel
├── bytetrack.yaml       # Cấu hình ByteTrack tracker
├── requirements.txt     # Thư viện cần cài
│
├── yolo26n.pt           # Model YOLO đã train (nano)
│
├── video/               # Thư mục chứa video đầu vào
│   └── *.mp4 / *.avi
│
└── report/              # Báo cáo Excel xuất ra
    └── vehicle_report_YYYYMMDD_HHMMSS.xlsx
```

---

## 3. Cài đặt & Chạy

### Yêu cầu hệ thống
- Python 3.10+
- GPU (khuyến nghị, YOLO chạy nhanh hơn nhiều)
- RAM ≥ 8 GB

### Cài đặt thư viện

```bash
pip install -r requirements.txt
```

**Nội dung `requirements.txt`:**

```
ultralytics>=8.0.0    # YOLOv8 + ByteTrack
streamlit>=1.30.0     # Web interface
opencv-python>=4.8.0  # Xử lý ảnh/video, GUI
pandas>=2.0.0         # Xuất Excel
openpyxl>=3.1.0       # Engine Excel
numpy>=1.24.0         # Tính toán ma trận
lapx>=0.5.0           # Linear Assignment (ByteTrack cần)
```

### Chạy ứng dụng

```bash
# Giao diện Desktop (khuyến nghị)
python main.py

# Giao diện Web
streamlit run app.py
```

---

## 4. Luồng hoạt động của hệ thống

```
Khởi động
    │
    ▼
┌─────────────────────────────┐
│    Video Picker Screen       │
│  - Quét thư mục video/       │
│  - Hiển thị danh sách       │
│  - Chọn file + Enter/Click  │
└──────────────┬──────────────┘
               │ Chọn video
               ▼
┌─────────────────────────────┐
│    Dashboard Screen          │
│  - Video chạy bình thường   │
│  - CHƯA detect/track gì cả  │
│  - Chờ người dùng vẽ ROI    │
└──────────────┬──────────────┘
               │ Nhấn [D]
               ▼
┌─────────────────────────────┐
│    ROI Selection Mode        │
│  - Video PAUSE              │
│  - Click 4 điểm trên đường  │
│    Thứ tự: TL→TR→BR→BL      │
│  - Polygon nối tự động      │
└──────────────┬──────────────┘
               │ Đủ 4 điểm
               ▼
┌─────────────────────────────┐
│  Tính Perspective Matrix    │
│  cv2.getPerspectiveTransform│
│  Video tự RESUME            │
└──────────────┬──────────────┘
               │
               ▼
┌─────────────────────────────┐
│  Calibration Phase (~2s)    │
│  - Chạy YOLO + ByteTrack   │
│  - Thu thập vector dx/dy   │
│    trong warped space       │
│  - Hiện "calibrating..."   │
└──────────────┬──────────────┘
               │ ≥60 vector
               ▼
┌─────────────────────────────┐
│  Active Tracking Phase      │
│  - Xác định trục chuyển động│
│  - Đặt counting line vuông  │
│    góc với hướng xe         │
│  - Đếm khi xe cắt vạch     │
│  - Hiển thị tốc độ         │
└──────────────┬──────────────┘
               │ Video hết / [Q]
               ▼
┌─────────────────────────────┐
│  Completion / Export         │
│  - [E] Xuất Excel           │
│  - [R] Chọn video khác      │
│  - [Q] Thoát               │
└─────────────────────────────┘
```

---

## 5. Chi tiết từng module

### 5.1 `main.py` — Giao diện & Điều phối

#### Layout cửa sổ (1280×760 px)

```
┌──────────────────────────────────────────────────────────────┐
│  HEADER (38px) — Tên hệ thống, trạng thái, tên file         │
├──────────────────────────────────┬───────────────────────────┤
│                                  │                           │
│   VIDEO PANEL (768×690px)        │   STAT PANEL (512×690px)  │
│                                  │                           │
│   - Frame video                  │   - Total Vehicles        │
│   - ROI overlay (cam)            │   - Avg/Max/Min Speed     │
│   - Counting line (xanh)         │   - Scale px/m            │
│   - Bounding boxes               │                           │
│   - Trails                       │   - VEHICLE LOG TABLE     │
│   - ROI mode banner              │     ID│Type│Entry│Exit│Spd│
│                                  │                           │
├──────────────────────────────────┴───────────────────────────┤
│  STATUSBAR (32px) — Frame progress, FPS, phím tắt           │
└──────────────────────────────────────────────────────────────┘
```

#### Các class và hàm chính

| Thành phần | Mô tả |
|---|---|
| `_MouseState` | Lưu trạng thái chuột (x, y, clicked) cho Video Picker |
| `_DashboardMouse` | Lưu trạng thái chuột cho Dashboard (ROI selection) |
| `run_picker()` | Vòng lặp chọn video — hover, click, double-click, Enter |
| `run_dashboard()` | Vòng lặp chính: đọc frame, xử lý, render, xử lý phím |
| `build_dashboard()` | Ghép toàn bộ canvas từ các panel |
| `_draw_header()` | Vẽ thanh tiêu đề |
| `_draw_video_panel()` | Scale frame vào panel, vẽ ROI overlay đang chọn |
| `_draw_stat_panel()` | Vẽ thống kê và log bảng |
| `_draw_statusbar()` | Vẽ progress bar, FPS, phím tắt |
| `_get_video_transform()` | Tính scale/offset frame→canvas (dùng cho ROI click) |
| `_canvas_to_frame()` | Chuyển tọa độ click trên canvas → tọa độ frame gốc |
| `_frame_to_canvas()` | Ngược lại — dùng để vẽ điểm ROI |
| `do_export()` | Gọi export_to_excel và lưu file |

#### ROI State Machine trong `run_dashboard()`

```python
roi_mode        = False   # Đang ở chế độ vẽ ROI?
roi_mode_points = []      # Điểm đã click (tọa độ frame gốc)
roi_confirmed   = False   # Đã đủ 4 điểm và set xong?
```

**Trạng thái chuyển đổi:**

```
NORMAL ──[D]──→ ROI_DRAWING (video pause)
               │ Click điểm 1
               │ Click điểm 2  
               │ Click điểm 3
               │ Click điểm 4 ──→ tracker.set_roi() ──→ NORMAL (roi_confirmed=True)
               │
               └──[D] lại──→ NORMAL (hủy bỏ)

NORMAL ──[C]──→ tracker.clear_roi() ──→ NORMAL (roi_confirmed=False)
```

#### Frame Timing

```python
frame_delay = 1.0 / video_fps   # VD: 1/30 = 0.033s = 33ms

# Sau mỗi frame:
elapsed = time.time() - t_prev
wait_ms = max(1, int((frame_delay - elapsed) * 1000))
key = cv2.waitKeyEx(wait_ms)
```

Điều này đảm bảo video chạy đúng FPS gốc dù YOLO mất bao lâu để xử lý.

---

### 5.2 `tracker.py` — Nhân xử lý

#### Class `VehicleTracker`

Đây là **nhân trung tâm** của toàn bộ hệ thống. Quản lý:

1. Model YOLO detection
2. ByteTrack tracking state
3. ROI và perspective transform
4. Counting line
5. Lịch sử tốc độ

#### Thuộc tính quan trọng

```python
# --- Model ---
self.model              # YOLO model instance
self.pixel_per_meter    # Tỷ lệ px/m (điều chỉnh bằng +/-)
self.fps                # FPS video

# --- Tracking history ---
self.track_history      # {track_id: [(x,y), (x,y), ...]} — tọa độ frame gốc
self.speed_history      # {track_id: [speed1, speed2, ...]} — km/h
self.vehicle_info       # {track_id: {type, entry_frame, last_frame, max_speed, counted}}
self.current_frame      # Số frame đang xử lý

# --- ROI & Perspective ---
self.roi_points         # np.array shape (4,2) — 4 điểm src
self.perspective_matrix # Ma trận 3×3 — cv2.getPerspectiveTransform output
self.dst_width = 400    # Chiều rộng warped space (pixel)
self.dst_height = 600   # Chiều cao warped space (pixel)

# --- Counting Line ---
self.counting_line_pos  = 0.5   # Vị trí 50% trên trục chính
self.counting_line_axis = 'y'   # 'x' (xe chạy ngang) hoặc 'y' (xe chạy dọc)
self._axis_locked       = False # Đã xác định hướng chưa?
self._motion_vectors    = []    # [(|dx|, |dy|), ...] tích lũy để detect hướng
self.counted_ids        = set() # Track ID đã được đếm (qua vạch)
self.line_side          = {}    # {id: 'above'/'below'/'left'/'right'}
```

#### Phương thức

| Phương thức | Mô tả |
|---|---|
| `__init__()` | Load YOLO, khởi tạo tất cả state |
| `reset()` | Xóa tracking data, giữ nguyên ROI |
| `set_roi(points)` | Tính perspective matrix từ 4 điểm |
| `clear_roi()` | Xóa ROI và reset toàn bộ counting |
| `update_config()` | Cập nhật pixel_per_meter hoặc fps |
| `process_frame()` | **Hàm chính** — xử lý 1 frame đầy đủ |
| `get_vehicle_log()` | Trả list log xe (cho bảng UI) |
| `get_statistics()` | Trả dict thống kê (total, min/max/avg speed) |
| `_order_points()` | ~~Đã xóa~~ — dùng thứ tự click trực tiếp |
| `_update_motion_axis()` | Tích lũy dx/dy, chốt trục sau 60 vector |
| `_transform_point()` | Chuyển 1 điểm qua perspective matrix |
| `_is_inside_roi()` | `cv2.pointPolygonTest` — kiểm tra trong ROI |
| `_check_line_crossing()` | Phát hiện xe cắt ngang counting line |
| `_get_color()` | Sinh màu duy nhất cho mỗi track ID (HSV→BGR) |

---

### 5.3 `utils.py` — Tiện ích

#### `calculate_speed(prev_centroid, curr_centroid, pixel_per_meter, fps)`

```
Khoảng cách Euclid (pixel)
         ↓  ÷ pixel_per_meter
Khoảng cách thực (mét)
         ↓  ÷ (1/fps) = × fps
Tốc độ (m/s)
         ↓  × 3.6
Tốc độ (km/h)
```

**Công thức:**

```
speed_kmh = sqrt((dx² + dy²)) / pixel_per_meter × fps × 3.6
```

> **Lưu ý quan trọng**: Hàm này được gọi với `prev_centroid` và `curr_centroid` đã được transform sang warped space (tọa độ phẳng), không phải tọa độ gốc. Điều này loại bỏ méo phối cảnh.

#### `smooth_speed(speed_history, window=15)`

Moving average trên 15 frame gần nhất:

```python
speed_smoothed = mean(speed_history[-15:])
```

Tránh dao động mạnh khi detection không ổn định.

#### `format_time(frame_number, fps)`

```
frame_number / fps = total_seconds → "HH:MM:SS"
```

#### `export_to_excel(vehicle_log, stats)`

Tạo file Excel `.xlsx` với 2 sheet:
- **Sheet "Log Chi Tiết"**: ID, Loại Xe, Thời Gian Vào, Thời Gian Ra, Tốc Độ Max
- **Sheet "Tổng Hợp"**: Tổng số xe, Min/Max/Avg speed

---

### 5.4 `bytetrack.yaml` — Cấu hình Tracker

```yaml
tracker_type: bytetrack

track_high_thresh: 0.5   # Confidence ≥ 0.5 → tạo track mới ngay
track_low_thresh: 0.1    # Confidence 0.1–0.5 → thử ghép track cũ trước
new_track_thresh: 0.6    # Confidence ≥ 0.6 để tạo track brand-new

track_buffer: 90         # Giữ track tối đa 90 frame (3s @ 30fps)
                         # khi mất detection (xe bị che khuất, đèn đỏ...)

match_thresh: 0.7        # IoU ≥ 0.7 để ghép detection với track cũ
fuse_score: true         # Kết hợp confidence score × IoU khi matching
```

**Tại sao `track_buffer: 90`?**  
Nếu xe dừng đèn đỏ >1 giây (30 frame cũ), ByteTrack sẽ xóa track và gán ID mới → đếm 2 lần. Với 90 frame (3 giây), xe có thể dừng tạm và được ghép lại đúng ID.

**Tại sao `match_thresh: 0.7` (giảm từ 0.8)?**  
Xe di chuyển nhanh → bounding box dịch nhiều → IoU thấp. Nếu threshold quá cao, ByteTrack từ chối ghép → tạo ID mới → đếm 2 lần.

---

## 6. Tính năng ROI & Perspective Transform

### 6.1 Vấn đề cần giải quyết

Camera giao thông thường đặt góc nghiêng. Khi đo khoảng cách trên ảnh gốc:

```
Camera góc nghiêng:
┌─────────────────────────┐
│  ←──── 100px ────→     │   Thực tế: 10 mét (gần camera)
│                         │
│   ←── 50px ──→         │   Thực tế: 10 mét (xa camera)
│                         │
└─────────────────────────┘
→ Cùng khoảng cách thực nhưng pixel khác nhau!
```

Perspective Transform giải quyết bằng cách biến đổi góc nhìn sang **bird's eye view** (nhìn từ trên xuống):

```
Bird's Eye View (400×600px):
┌──────────────┐
│              │
│   ←100px→   │   = 10 mét (gần)
│              │
│   ←100px→   │   = 10 mét (xa)
│              │
└──────────────┘
→ Tỷ lệ pixel/mét đồng đều toàn vùng ROI!
```

### 6.2 Cách người dùng thiết lập ROI

1. Nhấn **[D]** → video pause, chuyển sang ROI mode
2. Click **4 điểm** trên mặt đường theo thứ tự:

```
Camera nhìn thẳng đường:        Camera nhìn ngang:
                                 
  P1 ─────── P2                 P1 ── P2
   \           \                 |      |
    P4 ─────── P3               P4 ── P3
    
(hình thang góc phối cảnh)      (hình chữ nhật)
```

> **Quan trọng**: 4 điểm phải là cùng một mặt phẳng thực tế (mặt đường). Không được click vào xe hay vật thể nhô lên.

3. Sau khi đủ 4 điểm → **tự động tính ma trận** và resume video

### 6.3 Tính toán ma trận Perspective Transform

```python
src_pts = np.array(user_clicks, dtype=np.float32)   # 4 điểm người dùng chọn

dst_pts = np.array([
    [0,   0  ],   # P1 → góc trên-trái của warped
    [399, 0  ],   # P2 → góc trên-phải
    [399, 599],   # P3 → góc dưới-phải
    [0,   599],   # P4 → góc dưới-trái
], dtype=np.float32)

M = cv2.getPerspectiveTransform(src_pts, dst_pts)
# M là ma trận 3×3 dùng để transform bất kỳ điểm nào
```

**Transform 1 điểm (centroid xe):**

```python
pt = np.array([[[cx, cy]]], dtype=np.float32)
pt_warped = cv2.perspectiveTransform(pt, M)
# → (x', y') trong warped space [0..399, 0..599]
```

**Inverse transform (để vẽ counting line lên frame gốc):**

```python
inv_M = np.linalg.inv(M)
pts_warped = np.array([[[0, ly]], [[399, ly]]], dtype=np.float32)
pts_original = cv2.perspectiveTransform(pts_warped, inv_M)
# → 2 điểm trên frame gốc tạo thành đường đếm hiển thị đúng
```

---

## 7. Cơ chế đếm xe (Counting Line)

### 7.1 Vấn đề double-count

Ngay cả với ByteTrack tốt, đôi khi xe bị đếm nhiều lần vì:
- ByteTrack mất track → gán ID mới khi xe xuất hiện lại
- ID switching giữa 2 xe gần nhau

### 7.2 Giải pháp: Counting Line

Chỉ đếm xe **một lần** khi centroid của nó **cắt ngang** qua một vạch ảo:

```
Warped Space (400×600):
┌──────────────────────────┐
│  Xe đang ở phía "above"  │
│                          │
│  ─ ─ ─ ─ ─ ─ ─ ─ ─ ─  │  ← Counting line tại y=300 (50%)
│                          │
│  Xe đã qua "below" ✓    │  ← Đếm +1 tại đây
└──────────────────────────┘
```

**Logic:**
```python
# Mỗi frame, với mỗi xe trong ROI:
curr_side = 'above' if cy_warped < 300 else 'below'

if prev_side != curr_side and track_id not in counted_ids:
    counted_ids.add(track_id)   # Đếm 1 lần
    # Sau đó kể cả ID đổi, xe này đã được đếm rồi
```

### 7.3 Tự động xác định hướng vạch

Hệ thống **không biết trước** xe chạy dọc hay ngang. Vì vậy trong ~2 giây đầu sau khi set ROI:

```
Thu thập 60 vector (dx, dy) trong warped space
              ↓
      Tính tổng |dx| và |dy|
              ↓
┌─────────────┴──────────────┐
│                            │
sum(|dx|) ≥ sum(|dy|)   sum(|dy|) > sum(|dx|)
     ↓                           ↓
Xe chạy NGANG             Xe chạy DỌC
(theo trục X)             (theo trục Y)
     ↓                           ↓
Counting line ĐỨNG        Counting line NGANG
(x = 50% dst_width)       (y = 50% dst_height)
```

**Ví dụ output terminal:**
```
[ROI]  Auto-detected: vehicles move VERTICALLY → horizontal counting line at y=50% (dx_total=1250, dy_total=4830)
```

### 7.4 Trực quan hóa

- **Vạch xanh đứt khúc**: Counting line hiển thị trên frame gốc
- **`COUNT: 5`**: Số xe đã qua vạch, hiện ngay cạnh vạch
- **`COUNT: 2 (calibrating...)`**: Đang thu thập dữ liệu xác định hướng
- **Bounding box dày hơn (3px)**: Xe đã được đếm
- **Chấm xanh góc box**: Đánh dấu xe đã được đếm

---

## 8. Thuật toán đo tốc độ

### 8.1 Pipeline tính tốc độ

```
Frame N:   centroid_N = (cx, cy) trong frame gốc
               ↓  perspective_matrix
           warped_N = (x', y') trong warped space (400×600)

Frame N-1: warped_N1 = (x'_prev, y'_prev)

Khoảng cách pixel (warped): d_px = sqrt((x'-x'_prev)² + (y'-y'_prev)²)

Khoảng cách thực (mét): d_m = d_px / pixel_per_meter

Thời gian giữa 2 frame: dt = 1 / fps

Tốc độ: v = d_m / dt × 3.6  (km/h)
```

### 8.2 Làm mượt tốc độ

Raw speed dao động nhiều vì detection không ổn định. Áp dụng **moving average 15 frame**:

```python
speed_display = mean(speed_history[-15:])
```

Tương đương với làm mượt trong 0.5 giây (ở 30fps).

### 8.3 Điều chỉnh pixel_per_meter

Tham số quan trọng nhất. Cách tính chính xác:

1. Đo một khoảng cách **biết trước** trên mặt đường (VD: vạch kẻ đường = 2m, rộng làn = 3.5m)
2. Đếm số pixel khoảng cách đó chiếm trên frame
3. `pixel_per_meter = số_pixel / số_mét`

> Mặc định `DEFAULT_PPM = 28.0`. Điều chỉnh bằng phím **[+]** / **[-]** trong khi xem video.

---

## 9. Pipeline xử lý mỗi frame

```
process_frame(raw_frame)
│
├── 1. TĂNG current_frame
│
├── 2. VẼ ROI OVERLAY (nếu đã set)
│   ├── fillPoly (cam, alpha=0.15)
│   ├── polylines (viền cam)
│   ├── Đánh số điểm góc
│   └── Vẽ counting line (inverse transform + dashed)
│
├── 3. GATE: Nếu roi_points là None → return frame ngay
│           (Không tốn tài nguyên YOLO khi chưa set ROI)
│
├── 4. YOLO DETECTION + BYTETRACK
│   model.track(frame, persist=True, tracker="bytetrack.yaml", conf=0.4)
│   → Trả về: boxes(xyxy), track_ids, class_ids, confidences
│
├── 5. VỚI MỖI XE DETECTED:
│   │
│   ├── a. Tính centroid: cx=(x1+x2)/2, cy=(y1+y2)/2
│   │
│   ├── b. ROI CHECK: cv2.pointPolygonTest(roi_points, centroid)
│   │   ├── Ngoài ROI → vẽ box xám (80,80,80), skip
│   │   └── Trong ROI → tiếp tục
│   │
│   ├── c. Lưu centroid vào track_history[id]
│   │
│   ├── d. PERSPECTIVE TRANSFORM centroid → warped_point
│   │
│   ├── e. TÍNH TỐC ĐỘ
│   │   ├── Nếu có prev_warped: calculate_speed(prev_t, curr_t, ppm, fps)
│   │   └── smooth_speed(speed_history, window=15)
│   │
│   ├── f. CẬP NHẬT MOTION AXIS (nếu chưa lock)
│   │   └── _update_motion_axis(dx_warped, dy_warped)
│   │
│   ├── g. CHECK COUNTING LINE
│   │   └── _check_line_crossing(id, warped_point)
│   │       → counted_ids.add(id) nếu vừa cắt vạch
│   │
│   ├── h. CẬP NHẬT vehicle_info[id]
│   │   └── max_speed, last_frame, counted flag
│   │
│   └── i. VẼ ANNOTATION
│       ├── Bounding box (màu theo ID, dày nếu đã đếm)
│       ├── Label "ID:5 car"
│       ├── Speed label "45.2 km/h"
│       ├── Trail (20 điểm gần nhất)
│       └── Chấm xanh nếu đã qua vạch
│
└── 6. GIỚI HẠN track_history ≤ 50 điểm/xe
    └── return annotated_frame
```

---

## 10. Giao diện Dashboard

### 10.1 Stat Panel

| Ô | Nội dung | Màu |
|---|---|---|
| Total Vehicles | Số xe đã qua counting line | Amber |
| Avg Speed | Trung bình tốc độ max các xe đã đếm | White |
| Max Speed | Tốc độ cao nhất | Đỏ |
| Min Speed | Tốc độ thấp nhất | Xanh |
| Scale px/m | pixel_per_meter hiện tại | Teal |

### 10.2 Vehicle Log Table

Hiển thị tối đa các dòng vừa panel. Mới nhất hiện trên đầu.

| Cột | Nguồn |
|---|---|
| ID | ByteTrack track_id |
| TYPE | YOLO class_name (car, truck, bus...) |
| ENTRY | format_time(entry_frame, fps) |
| EXIT | format_time(last_frame, fps) |
| SPD | max_speed (km/h) |

**Màu tốc độ:**
- 🟢 Xanh: ≤ 40 km/h
- 🟡 Vàng: 41–70 km/h  
- 🔴 Đỏ: > 70 km/h

### 10.3 Progress Bar

```
Frame 1,250 / 5,400   23.1%   [████████░░░░░░░░░░░░░░░░░░]   FPS 28.3
```

---

## 11. Phím tắt & Điều khiển

### Video Picker

| Phím | Tác dụng |
|---|---|
| `↑` / `K` | Di chuyển lên trong danh sách |
| `↓` / `J` | Di chuyển xuống |
| `Enter` | Bắt đầu phân tích video đã chọn |
| Double-click | Bắt đầu phân tích ngay |
| `Q` / `ESC` | Thoát |

### Dashboard

| Phím | Tác dụng |
|---|---|
| `P` | Pause / Resume video |
| `D` | Bật chế độ vẽ ROI (video tự pause) |
| `C` | Xóa ROI và reset toàn bộ đếm |
| `R` | Quay lại chọn video khác |
| `E` | Xuất báo cáo Excel ngay lập tức |
| `+` / `=` | Tăng pixel_per_meter (xe đo chậm hơn) |
| `-` | Giảm pixel_per_meter (xe đo nhanh hơn) |
| `Q` | Thoát |

### ROI Selection (khi đang vẽ)

| Thao tác | Tác dụng |
|---|---|
| Click trái | Thêm điểm ROI (tối đa 4) |
| Đủ 4 điểm | Tự động xác nhận, video resume |
| `D` | Hủy ROI mode (nếu chưa đủ 4 điểm) |
| `C` | Xóa ROI và thoát mode |

---

## 12. Xuất báo cáo Excel

File lưu tại: `report/vehicle_report_YYYYMMDD_HHMMSS.xlsx`

### Sheet 1: Log Chi Tiết

| ID | Loại Xe | Thời Gian Vào | Thời Gian Ra | Tốc Độ Max (km/h) |
|---|---|---|---|---|
| 3 | car | 00:00:05 | 00:00:08 | 52.4 |
| 7 | truck | 00:00:12 | 00:00:18 | 34.1 |
| ... | ... | ... | ... | ... |

> **Chú ý**: Chỉ xuất các xe đã qua counting line (đã được đếm chính xác).

### Sheet 2: Tổng Hợp

| Chỉ Số | Giá Trị |
|---|---|
| Tổng số xe | 45 |
| Tốc độ thấp nhất (km/h) | 18.3 |
| Tốc độ cao nhất (km/h) | 87.6 |
| Tốc độ trung bình (km/h) | 48.2 |

---

## 13. Các vấn đề đã giải quyết & Thiết kế quyết định

### ❌ Vấn đề: ROI hình thang bị mất điểm

**Nguyên nhân**: Thuật toán `_order_points()` dùng heuristic `sum(x+y)` và `diff(y-x)` chỉ đúng cho hình chữ nhật axis-aligned. Với hình thang (trapeziod), thuật toán sắp xếp sai thứ tự → polygon tự giao cắt → `getPerspectiveTransform` ra ma trận sai.

**Giải pháp**: Bỏ `_order_points()`, dùng trực tiếp thứ tự click của người dùng. Người dùng biết điểm nào là TL/TR/BR/BL của vùng mình muốn.

---

### ❌ Vấn đề: Counting line song song với chiều xe

**Nguyên nhân**: Cố định `counting_line_y = 0.6 * dst_height` giả định xe luôn di chuyển theo trục Y trong warped space. Thực tế tùy theo cách người dùng click 4 điểm, xe có thể di chuyển theo trục X.

**Giải pháp**: Tự động phát hiện trục di chuyển bằng cách tích lũy 60 vector `(dx, dy)` trong warped space. So sánh `sum(|dx|)` vs `sum(|dy|)` → chốt trục → đặt vạch vuông góc.

---

### ❌ Vấn đề: Xe bị đếm nhiều lần (double counting)

**Nguyên nhân 1**: ByteTrack mất track khi xe bị che khuất → ID mới → `vehicle_info` ghi thêm xe mới.

**Giải pháp 1**: Tăng `track_buffer: 90` (3s thay vì 1s). Giảm `match_thresh: 0.7` để dễ ghép track hơn.

**Nguyên nhân 2**: Dù ID ổn định, cơ chế đếm theo `len(vehicle_info)` sẽ đếm mọi xe xuất hiện trong ROI, kể cả xe dừng rồi đi.

**Giải pháp 2**: Counting line mechanism — xe chỉ được đếm 1 lần duy nhất khi cắt ngang vạch, bất kể ID có thay đổi hay không.

---

### ❌ Vấn đề: Video bị chạy nhanh/chậm thất thường

**Nguyên nhân**: `cv2.waitKeyEx(1)` chạy vòng lặp nhanh nhất có thể. YOLO xử lý ~50ms/frame nhưng không có giới hạn nào khi YOLO nhanh hơn.

**Giải pháp**: Tính `frame_delay = 1/fps`, sau mỗi frame tính thời gian còn lại và truyền vào `waitKeyEx(wait_ms)`.

---

### ✅ Thiết kế: Không tracking khi chưa có ROI

**Quyết định**: `process_frame()` return sớm ngay khi `roi_points is None`, không gọi YOLO.

**Lý do**:
1. Tiết kiệm GPU khi người dùng chưa sẵn sàng đo
2. Không tích lũy vehicle_info "rác" từ trước khi ROI
3. Số đếm bắt đầu từ 0 sau khi set ROI — đúng ngữ nghĩa

---

### ✅ Thiết kế: `counted_ids` thay vì `len(vehicle_info)`

**Quyết định**: `get_statistics()["total"]` = `len(counted_ids)`, không phải `len(vehicle_info)`.

**Lý do**: `vehicle_info` chứa mọi xe đã track trong ROI (kể cả xe chỉ đi vào rồi quay ra, xe đứng yên). `counted_ids` chỉ chứa xe đã thực sự đi qua vạch đếm — đúng với nghĩa "số phương tiện đã lưu thông qua".

---

## 14. Thông số kỹ thuật

| Thông số | Giá trị |
|---|---|
| Model YOLO | `yolo26n.pt` (nano, tốc độ cao) |
| Classes được detect | bicycle(1), car(2), motorcycle(3), bus(5), truck(7) |
| Confidence threshold | 0.4 |
| Track buffer | 90 frame (~3s @ 30fps) |
| IoU match threshold | 0.7 |
| Speed smoothing window | 15 frame (~0.5s) |
| Track history limit | 50 điểm/xe (giữ 30 điểm gần nhất) |
| Trail hiển thị | 20 điểm gần nhất |
| Warped space size | 400 × 600 px |
| Counting line position | 50% trên trục chính |
| Calibration frames | 60 vector chuyển động |
| Window size | 1280 × 760 px |
| Video panel | 768 × 690 px (60% chiều rộng) |
| Stat panel | 512 × 690 px (40% chiều rộng) |
| Default pixel_per_meter | 28.0 |
| Max pixel_per_meter | 150.0 |
| Min pixel_per_meter | 1.0 |

---

## Phụ lục: Sơ đồ dữ liệu

```
Video Frame (BGR numpy array)
         │
         ▼
  YOLO detection
         │
         ▼
  boxes: [[x1,y1,x2,y2], ...]  ── class_ids ── track_ids ── confidences
         │
         │ Với mỗi box:
         ▼
  centroid (cx, cy)
         │
         ├──→ _is_inside_roi(centroid) → bool
         │          cv2.pointPolygonTest
         │
         └──→ _transform_point(centroid)
                    cv2.perspectiveTransform(M)
                         │
                         ▼
                  warped_point (x', y')
                         │
                    ┌────┴────┐
                    │         │
                    ▼         ▼
            calculate_speed  _check_line_crossing
            (prev_t, curr_t) (track_id, warped_pt)
                    │         │
                    ▼         ▼
             raw_speed    counted_ids.add(id)
                    │
                    ▼
             smooth_speed (window=15)
                    │
                    ▼
              speed_display → annotated_frame label
```

---

*Tài liệu được tạo tự động từ mã nguồn hệ thống — Cập nhật: 2026-07-03*
