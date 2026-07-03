# ITS_2026 — Intelligent Traffic System

> **Hệ thống Phân tích Giao thông Thông minh**  
> Phát hiện, theo dõi và đo tốc độ phương tiện trên đường cao tốc theo thời gian thực.

---

## Mục lục

1. [Tổng quan hệ thống](#1-tổng-quan-hệ-thống)
2. [Yêu cầu hệ thống](#2-yêu-cầu-hệ-thống)
3. [Cài đặt](#3-cài-đặt)
4. [Cấu trúc thư mục](#4-cấu-trúc-thư-mục)
5. [Kiến trúc hệ thống](#5-kiến-trúc-hệ-thống)
6. [Hướng dẫn sử dụng](#6-hướng-dẫn-sử-dụng)
7. [Cơ sở khoa học — Đo tốc độ](#7-cơ-sở-khoa-học--đo-tốc-độ)
8. [Cấu hình ByteTrack](#8-cấu-hình-bytetrack)
9. [Dashboard — Giao diện](#9-dashboard--giao-diện)
10. [Xuất báo cáo Excel](#10-xuất-báo-cáo-excel)
11. [Giải thích từng module](#11-giải-thích-từng-module)
12. [Tham số quan trọng](#12-tham-số-quan-trọng)
13. [Câu hỏi thường gặp](#13-câu-hỏi-thường-gặp)

---

## 1. Tổng quan hệ thống

ITS_2026 là hệ thống phân tích giao thông sử dụng thị giác máy tính để:

| Chức năng | Mô tả |
|-----------|-------|
| 🚗 **Phát hiện xe** | YOLOv8 nhận diện ô tô, xe buýt, xe tải trên đường cao tốc |
| 🔍 **Theo dõi xe** | ByteTrack duy trì ID ổn định cho từng xe qua nhiều frame |
| 📐 **Đo tốc độ** | Perspective Transform + khoảng cách thực 12m → km/h |
| 📊 **Thống kê** | Tổng xe, tốc độ tối đa/tối thiểu/trung bình theo thời gian thực |
| 📝 **Xuất báo cáo** | File Excel (.xlsx) chi tiết từng xe |

### Đặc điểm nổi bật

- **Không có xe máy**: Hệ thống chỉ nhận diện car/bus/truck, phù hợp 100% với đường cao tốc Việt Nam
- **Không cần camera đặc biệt**: Hoạt động với camera thường, file MP4/AVI/MOV/MKV
- **Đo tốc độ chuẩn**: Dựa trên khoảng cách vạch sơn thực tế 12m — không cần calibration phức tạp
- **Giao diện OpenCV**: Không phụ thuộc web framework — chạy thẳng bằng `python main.py`

---

## 2. Yêu cầu hệ thống

### Phần cứng tối thiểu

| Thành phần | Tối thiểu | Khuyến nghị |
|------------|-----------|-------------|
| CPU | 4 nhân, 2.5 GHz | 8 nhân, 3.5 GHz |
| RAM | 8 GB | 16 GB |
| GPU | Không bắt buộc | NVIDIA GPU (CUDA) |
| Ổ cứng | 5 GB trống | SSD |
| OS | Windows 10 / Ubuntu 20.04 | Windows 11 / Ubuntu 22.04 |

> **Ghi chú GPU**: Nếu có GPU NVIDIA với CUDA, hệ thống sẽ tự động sử dụng, tăng tốc xử lý lên 5–10×.

### Phần mềm

- Python **3.10+** (khuyến nghị 3.11)
- pip hoặc conda

---

## 3. Cài đặt

### Bước 1 — Clone hoặc tải dự án

```bash
git clone <repo-url>
cd ITS_2026
```

### Bước 2 — Tạo môi trường ảo

```bash
# Windows
python -m venv .venv
.venv\Scripts\activate

# Linux / macOS
python3 -m venv .venv
source .venv/bin/activate
```

### Bước 3 — Cài đặt thư viện

```bash
pip install -r requirements.txt
```

Danh sách thư viện (`requirements.txt`):

| Thư viện | Phiên bản | Mục đích |
|----------|-----------|---------|
| `ultralytics` | ≥ 8.0.0 | YOLOv8 detection + ByteTrack |
| `opencv-python` | ≥ 4.8.0 | Xử lý video + giao diện |
| `numpy` | ≥ 1.24.0 | Tính toán ma trận |
| `pandas` | ≥ 2.0.0 | Xuất báo cáo |
| `openpyxl` | ≥ 3.1.0 | Ghi file Excel |
| `lapx` | ≥ 0.5.0 | Linear Assignment (ByteTrack) |

### Bước 4 — Đặt model YOLO

Đặt file model `yolo26n.pt` vào thư mục `config/`:

```
ITS_2026/
└── config/
    ├── yolo26n.pt        ← file model ở đây
    └── bytetrack.yaml
```

### Bước 5 — Thêm video vào thư mục `video/`

```
ITS_2026/
└── video/
    ├── highway_cam1.mp4
    └── highway_cam2.mov
```

Các định dạng được hỗ trợ: `.mp4`, `.avi`, `.mov`, `.mkv`

### Bước 6 — Chạy hệ thống

```bash
python main.py
```

---

## 4. Cấu trúc thư mục

```
ITS_2026/
│
├── main.py                  # Entry point — khởi động ứng dụng
│
├── config/                  # Tất cả file cấu hình
│   ├── bytetrack.yaml       # Thông số ByteTrack tracker
│   └── yolo26n.pt           # YOLO model weights
│
├── core/                    # Logic nghiệp vụ (không phụ thuộc UI)
│   ├── __init__.py
│   ├── tracker.py           # VehicleTracker: detect + track + speed
│   └── utils.py             # Tính tốc độ, format, xuất Excel
│
├── ui/                      # Giao diện OpenCV
│   ├── __init__.py
│   ├── theme.py             # Màu sắc, layout, hàm vẽ dùng chung
│   ├── picker.py            # Màn hình chọn video
│   └── dashboard.py         # Dashboard phân tích chính
│
├── video/                   # Thư mục chứa video đầu vào
│   └── .gitkeep
│
├── report/                  # Thư mục lưu báo cáo Excel
│   └── .gitkeep
│
├── requirements.txt         # Danh sách thư viện
└── .gitignore
```

### Nguyên tắc phân tách module

```
main.py
  └── ui.picker        (chọn video)
  └── ui.dashboard     (dashboard chính)
        └── core.tracker   (detect + track + speed)
              └── core.utils   (tính toán + Excel)
        └── ui.theme       (màu sắc + drawing primitives)
```

---

## 5. Kiến trúc hệ thống

### Luồng xử lý tổng thể

```
Video File
    │
    ▼
[cv2.VideoCapture] ──── raw frame (BGR) ────►
    │
    ▼
[VehicleTracker.process_frame()]
    │
    ├─► [YOLO.track()] ──── detect: car/bus/truck
    │         │              tracker: ByteTrack
    │         │              conf ≥ 0.35
    │         │
    │         ▼
    │   [ROI Filter] ──── chỉ xử lý xe TRONG ROI
    │         │
    │         ▼
    │   [Perspective Transform] ──── frame coords → warped coords
    │         │
    │         ▼
    │   [Speed Calculation] ──── pixel distance / PPM / FPS × 3.6
    │         │
    │         ▼
    │   [Counting Line Check] ──── đếm xe khi cắt vạch
    │         │
    │         ▼
    │   [Annotation] ──── vẽ box, ID, km/h, trail
    │
    ▼
[build_dashboard()] ──── ghép video + stats + log
    │
    ▼
[cv2.imshow()] ──── hiển thị lên màn hình
```

### Pipeline đo tốc độ

```
4 điểm ROI (tọa độ frame)
        │
        ▼
getPerspectiveTransform()  →  Ma trận M (4×4)
        │
        ▼
Centroid xe (x,y) trong frame  →  perspectiveTransform(M)  →  Warped (x',y')
        │
        ▼
Khoảng cách pixel = √[(x'₂-x'₁)² + (y'₂-y'₁)²]
        │
        ▼
Khoảng cách thực = pixel_distance / PPM
  (PPM = 600px / 12m = 50.0 px/m)
        │
        ▼
Tốc độ = (khoảng_cách_thực / thời_gian) × 3.6  →  km/h
  (thời_gian = 1/FPS giây)
        │
        ▼
smooth_speed(window=15)  →  trung bình trượt 15 frame
```

---

## 6. Hướng dẫn sử dụng

### 6.1 Màn hình chọn video

Khi khởi động, hệ thống hiển thị danh sách video trong thư mục `video/`:

```
┌─────────────────────────────────────────────────────────────┐
│ VEHICLE ANALYSIS SYSTEM  //  Select Input Video             │
├───┬──────────────────────────┬────────┬──────┬──────┬───────┤
│ # │ FILENAME                 │ RES    │ DUR  │ FPS  │ SIZE  │
├───┼──────────────────────────┼────────┼──────┼──────┼───────┤
│ 1 │ highway_cam1.mp4         │1920x1080│ 5:30 │  30  │ 375 MB│
│ 2 │ test-case-2.MOV          │1280x720 │12:45 │  60  │  89 MB│
└───┴──────────────────────────┴────────┴──────┴──────┴───────┘
```

**Điều hướng:**

| Thao tác | Phím |
|----------|------|
| Di chuyển lên/xuống | `J` / `K` hoặc `↑` / `↓` |
| Chọn video | Click chuột |
| Bắt đầu phân tích | Double-click hoặc `Enter` |
| Thoát | `Q` hoặc `Esc` |

### 6.2 Vẽ ROI — Bước quan trọng nhất

Sau khi video bắt đầu, nhấn **`D`** để vào chế độ vẽ ROI.

**ROI (Region of Interest)** là vùng đo tốc độ, phải được căn chỉnh chính xác với vạch sơn trắng trên đường.

#### Cách đặt 4 điểm ROI đúng:

```
                    CHIỀU XA (phía trên ảnh)
    ┌──────────────────────────────────────────────┐
    │                                              │
    │    ════════════════════════ ← vạch sơn TRÊN │
    │   P1(TL)─────────────────P2(TR)             │
    │    │   vùng ROI 12m        │                │
    │   P4(BL)─────────────────P3(BR)             │
    │    ════════════════════════ ← vạch sơn DƯỚI │
    │                                              │
    └──────────────────────────────────────────────┘
                    CHIỀU GẦN (phía dưới ảnh)
```

**Quy tắc đặt điểm:**

| Điểm | Vị trí | Hướng dẫn click |
|------|--------|-----------------|
| **P1 (TL)** | Trên-Trái | Mép **ngoài** (phía xa) vạch sơn trên, bên trái làn |
| **P2 (TR)** | Trên-Phải | Mép **ngoài** (phía xa) vạch sơn trên, bên phải làn |
| **P3 (BR)** | Dưới-Phải | Mép **trong** (phía gần) vạch sơn dưới, bên phải làn |
| **P4 (BL)** | Dưới-Trái | Mép **trong** (phía gần) vạch sơn dưới, bên trái làn |

> ⚠️ **Lưu ý**: Cạnh trên ROI phải **bao trùm toàn bộ** vạch sơn trên. Cạnh dưới ROI phải **vừa chạm** đường sơn trắng dưới. Khoảng cách giữa 2 vạch = **12m thực tế**.

**Thứ tự click bắt buộc**: `P1 → P2 → P3 → P4` (ngược chiều kim đồng hồ từ trên-trái)

#### Sau khi vẽ xong:

- Hệ thống tự tính **Perspective Transform Matrix**
- Video **tự tiếp tục** chạy (không cần nhấn gì thêm)
- Vùng ROI hiển thị màu cam bán trong suốt
- Vạch đếm xe (đường xanh đứt nét) xuất hiện ở giữa ROI

### 6.3 Phím tắt trong Dashboard

| Phím | Chức năng |
|------|-----------|
| `P` | Pause / Resume video |
| `D` | Bật chế độ vẽ ROI (video tự dừng) |
| `C` | Xóa ROI hiện tại và reset tracking |
| `R` | Quay lại màn hình chọn video |
| `E` | Xuất báo cáo Excel (lưu vào `report/`) |
| `Q` | Thoát chương trình |

---

## 7. Cơ sở khoa học — Đo tốc độ

### 7.1 Vấn đề phối cảnh (Perspective Distortion)

Camera nhìn đường từ góc nghiêng làm cho:
- Vật ở xa trông **nhỏ hơn** vật ở gần
- Cùng 1m thực tế = **số pixel khác nhau** tùy vị trí trong frame
- → Không thể dùng pixel trực tiếp để tính tốc độ

### 7.2 Giải pháp: Perspective Transform (Bird's-Eye View)

```
Frame gốc (góc nghiêng)        Warped space (nhìn từ trên)
┌──────────────────────┐        ┌──────────────────┐
│     /‾‾‾‾‾‾‾‾‾‾\    │        │                  │
│    /    ROI      \   │  →→→   │   ROI phẳng      │
│   /_______________\  │  M     │   (tỉ lệ đều)    │
└──────────────────────┘        └──────────────────┘
```

Sau khi transform:
- Mỗi pixel trong warped space = khoảng cách thực **đều nhau**
- **PPM (pixel per meter)** = `600px / 12m = 50.0`
- Tốc độ tính chính xác bất kể xe ở đầu hay cuối ROI

### 7.3 Công thức tính tốc độ

```
distance_px  = √[(x'ₙ - x'ₙ₋₁)² + (y'ₙ - y'ₙ₋₁)²]   (warped space)

distance_m   = distance_px / PPM
             = distance_px / 50.0

time_s       = 1 / FPS

speed_ms     = distance_m / time_s

speed_kmh    = speed_ms × 3.6
```

### 7.4 Làm mượt tốc độ (Moving Average)

Do phát hiện không hoàn hảo mỗi frame, tốc độ thô có thể dao động mạnh.
Hệ thống dùng **trung bình trượt 15 frame**:

```python
speed_smooth = mean(speed_history[-15:])
```

### 7.5 Vì sao khoảng cách vạch sơn = 12m?

Theo **TCVN 4054:2005** và **QCVN 41:2019** (Việt Nam):
- Vạch sơn phân cách làn đường cao tốc: đoạn sơn 3m + khoảng trống 9m → chu kỳ 12m
- Hoặc đoạn sơn 6m + khoảng trống 6m → cũng chu kỳ 12m

> 📐 **Kiểm tra lại với địa điểm cụ thể**: Nếu khoảng cách vạch tại vị trí camera khác 12m, hãy chỉnh `ROAD_MARKING_DISTANCE_M` trong `core/tracker.py`.

### 7.6 Đếm xe — Counting Line

Hệ thống đếm xe khi centroid (điểm giữa bounding box) **cắt qua vạch đếm** ở giữa ROI:

- Vạch đếm nằm ở **50% chiều cao** của warped space
- Xe chỉ được đếm **1 lần** (tránh đếm trùng)
- Hướng vạch (ngang/đứng) tự động xác định sau 60 mẫu dữ liệu chuyển động

---

## 8. Cấu hình ByteTrack

File: `config/bytetrack.yaml`

```yaml
tracker_type: bytetrack

# Ngưỡng phát hiện
track_high_thresh: 0.35    # Confidence tối thiểu để tạo track mới
track_low_thresh: 0.10     # Confidence thấp nhất cho secondary association
new_track_thresh: 0.40     # Confidence để tạo object hoàn toàn mới

# Bộ nhớ track
track_buffer: 120          # Giữ track trong 120 frame dù không detect được
                           # = ~4 giây tại 30 FPS (xử lý khi xe bị khuất/mờ)

# Matching
match_thresh: 0.80         # IoU threshold để ghép detection với track cũ
fuse_score: true           # Kết hợp confidence score + IoU

# Lọc nhiễu
min_box_area: 400          # Bỏ qua detection < 20×20 px (nhiễu nền)
```

### Tại sao cần điều chỉnh cho đường cao tốc?

| Tham số | Mặc định YOLO | ITS_2026 | Lý do |
|---------|--------------|----------|-------|
| `track_high_thresh` | 0.50 | **0.35** | Xe từ xa trông nhỏ, confidence thấp hơn |
| `new_track_thresh` | 0.60 | **0.40** | Dễ tạo track khi xe mới xuất hiện |
| `track_buffer` | 30 | **120** | Xe cao tốc bị khuất 1–2s vẫn giữ ID |
| `match_thresh` | 0.70 | **0.80** | Xe tốc độ cao → di chuyển nhiều → cần IoU cao hơn |
| `min_box_area` | 0 | **400** | Loại bỏ detection giả (bóng, phản chiếu) |

---

## 9. Dashboard — Giao diện

```
┌────────────────────────────────────────────────────────────────────────────┐
│ VEHICLE ANALYSIS SYSTEM               ● LIVE          highway_cam1.mp4    │  ← Header
├────────────────────────────────────────────┬───────────────────────────────┤
│                                            │  Total Vehicles               │
│                                            │  ┌──────────────────────────┐│
│                                            │  │         42               ││
│                                            │  └──────────────────────────┘│
│                                            │                               │
│           VIDEO PANEL                     │  Avg Speed  Max Speed  Min Sp │
│         (768 × 690 px)                    │  ┌────────┐ ┌────────┐ ┌────┐│
│                                            │  │  87.3  │ │ 124.6  │ │68.2││
│    ROI polygon (cam)                      │  │  km/h  │ │  km/h  │ │km/h││
│    Bounding boxes (màu theo ID)           │  └────────┘ └────────┘ └────┘│
│    Speed labels (km/h)                    │                               │
│    Trail đường đi                         │  VEHICLE LOG                  │
│    Vạch đếm (đứt nét xanh)               │  ID  TYPE  ENTRY   EXIT    SPD│
│                                            │   1  car  00:00:03 00:00:08  89│
│                                            │   2  truck 00:00:07 00:00:15 76│
│                                            │   3  bus  00:00:11 00:00:22 65│
├────────────────────────────────────────────┴───────────────────────────────┤
│ Frame 1,234 / 9,876   12.5%  ████░░░░  FPS 28.3  ROI ✓                   │  ← Statusbar
│                              [P] Pause [D] Vẽ ROI [C] Xóa [R] Chọn [Q]  │
└────────────────────────────────────────────────────────────────────────────┘
```

### Ý nghĩa màu sắc tốc độ

| Màu | Tốc độ | Ý nghĩa |
|-----|--------|---------|
| 🟢 Xanh lá | < 60 km/h | Bình thường / chậm |
| 🟡 Vàng | 60 – 100 km/h | Tốc độ cho phép |
| 🔴 Đỏ | > 100 km/h | Vượt tốc độ |

### Ý nghĩa các trạng thái xe

| Biểu tượng | Ý nghĩa |
|------------|---------|
| Box **dày** (3px) + dấu ● xanh góc | Xe đã được đếm (đã qua vạch) |
| Box **mỏng** (2px) | Xe trong ROI, chưa qua vạch đếm |
| Box **xám nhạt** (1px) | Xe ngoài ROI, không tracking |
| Trail đường đi | 20 vị trí gần nhất của xe |

---

## 10. Xuất báo cáo Excel

Nhấn **`E`** trong dashboard để xuất báo cáo. File lưu tại:
```
report/vehicle_report_YYYYMMDD_HHMMSS.xlsx
```

### Sheet 1: Log Chi Tiết

| ID | Loại Xe | Thời Gian Vào | Thời Gian Ra | Tốc Độ Max (km/h) |
|----|---------|--------------|-------------|-------------------|
| 1  | car     | 00:00:03     | 00:00:08    | 89.4 |
| 2  | truck   | 00:00:07     | 00:00:15    | 76.1 |
| 3  | bus     | 00:00:11     | 00:00:22    | 65.8 |

### Sheet 2: Tổng Hợp

| Chỉ Số | Giá Trị |
|--------|---------|
| Tổng số xe | 42 |
| Tốc độ thấp nhất (km/h) | 58.3 |
| Tốc độ cao nhất (km/h) | 134.7 |
| Tốc độ trung bình (km/h) | 87.2 |

---

## 11. Giải thích từng module

### `main.py`
Entry point duy nhất. Khởi tạo thư mục cần thiết và điều phối vòng lặp:
```
run_picker() → run_dashboard() → [reselect / quit]
```

---

### `core/tracker.py` — VehicleTracker

**Class chính của hệ thống.** Bao gồm:

| Method | Mô tả |
|--------|-------|
| `__init__(model_path, fps)` | Load YOLO model, khởi tạo state |
| `set_roi(points)` | Nhận 4 điểm, tính Perspective Matrix |
| `clear_roi()` | Reset toàn bộ ROI + tracking data |
| `process_frame(frame)` | Xử lý 1 frame, trả về frame đã annotate |
| `get_vehicle_log()` | Trả về list log từng xe |
| `get_statistics()` | Trả về dict tổng hợp thống kê |
| `reset()` | Xóa tracking data, giữ ROI |

**Hằng số quan trọng:**

```python
ROAD_MARKING_DISTANCE_M = 12.0    # Khoảng cách thực giữa 2 vạch (m)
DST_HEIGHT              = 600     # Chiều cao warped space (px)
DEFAULT_PPM             = 50.0    # = 600 / 12
HIGHWAY_CLASS_IDS       = [2, 5, 7]  # car, bus, truck
BYTETRACK_CFG           = "config/bytetrack.yaml"
```

---

### `core/utils.py`

| Function | Mô tả |
|----------|-------|
| `calculate_speed(prev, curr, ppm, fps)` | Tính tốc độ km/h từ 2 centroid |
| `smooth_speed(history, window=15)` | Trung bình trượt tốc độ |
| `format_time(frame, fps)` | Chuyển số frame → "HH:MM:SS" |
| `get_vehicle_class_name(class_id, names)` | Trả về tên loại xe |
| `export_to_excel(log, stats)` | Tạo file Excel, trả về bytes |

---

### `ui/theme.py`

Định nghĩa toàn bộ hệ thống màu sắc và các hàm vẽ dùng chung.
Không có logic nghiệp vụ — chỉ là constants + drawing primitives.

---

### `ui/picker.py`

Màn hình chọn video. Quét thư mục `video/`, hiển thị metadata (FPS, duration, resolution).

- Hỗ trợ điều hướng bàn phím (J/K/↑/↓)
- Click chuột chọn; double-click bắt đầu
- Hiển thị thông tin chi tiết video được chọn ở panel phải

---

### `ui/dashboard.py`

Dashboard chính. Render 3 panel:

1. **Video Panel** (trái, 60%): Hiển thị frame đã annotate + overlay ROI
2. **Stat Panel** (phải, 40%): Thống kê + Vehicle Log
3. **Status Bar** (dưới): Progress + FPS + phím tắt

---

## 12. Tham số quan trọng

### Thay đổi khoảng cách vạch sơn

Nếu khoảng cách thực tế tại camera **không phải 12m**, chỉnh trong `core/tracker.py`:

```python
# core/tracker.py
ROAD_MARKING_DISTANCE_M = 12.0    # ← Đổi thành khoảng cách thực tế (m)
DST_HEIGHT              = 600     # Giữ nguyên
DEFAULT_PPM             = DST_HEIGHT / ROAD_MARKING_DISTANCE_M   # Tự tính lại
```

### Thay đổi ngưỡng phát hiện YOLO

Trong `core/tracker.py`, method `process_frame()`:

```python
results = self.model.track(
    frame,
    conf    = 0.35,    # ← Tăng nếu nhiều false positive, giảm nếu bỏ sót xe
    classes = HIGHWAY_CLASS_IDS,
    ...
)
```

### Thay đổi độ làm mượt tốc độ

Trong `core/tracker.py`:
```python
speed = smooth_speed(self.speed_history[track_id], window=15)
#                                                   ^^^^^^^^
#                       Tăng để ổn định hơn, giảm để phản ứng nhanh hơn
```

### Thay đổi màu ngưỡng cảnh báo tốc độ

Trong `ui/dashboard.py`:
```python
spd_color = RED if spd > 100 else YELLOW if spd > 60 else GREEN
#                       ^^^                      ^^
#               Ngưỡng đỏ (km/h)          Ngưỡng vàng (km/h)
```

### Thay đổi kích thước cửa sổ

Trong `ui/theme.py`:
```python
WIN_W = 1280    # Chiều rộng cửa sổ
WIN_H = 760     # Chiều cao cửa sổ
```

---

## 13. Câu hỏi thường gặp

**Q: Tốc độ hiển thị sai, quá nhanh hoặc quá chậm?**

A: Kiểm tra ROI có được vẽ đúng không. Cạnh dưới phải chạm vạch sơn dưới, cạnh trên phải bao trùm vạch sơn trên. Nếu khoảng cách vạch không phải 12m, chỉnh `ROAD_MARKING_DISTANCE_M`.

---

**Q: Xe bị mất ID (ID thay đổi liên tục)?**

A: Tăng `track_buffer` trong `config/bytetrack.yaml` (ví dụ: 150 hoặc 180). Kiểm tra ROI có đủ rộng để xe luôn nằm trong vùng tracking.

---

**Q: Hệ thống detect nhầm xe máy / người đi bộ?**

A: Bình thường — hệ thống chỉ nhận diện class 2/5/7 (car/bus/truck). Các đối tượng khác bị lọc ở tầng YOLO bằng `classes=[2, 5, 7]`.

---

**Q: Nhiều false positive (detect nhầm cây cối, bảng hiệu)?**

A: Tăng `conf` trong `process_frame()` từ 0.35 lên 0.45–0.50. Hoặc tăng `track_high_thresh` trong `bytetrack.yaml`.

---

**Q: Chạy chậm, FPS thấp?**

A: 
- Dùng GPU NVIDIA (cài CUDA + torch GPU version)
- Giảm độ phân giải video đầu vào
- Dùng model nhỏ hơn (nano thay vì large)

---

**Q: Cửa sổ không hiển thị / bị đen?**

A: Kiểm tra `opencv-python` đã cài đúng phiên bản. Trên Linux có thể cần `opencv-python-headless` thay thế.

---

**Q: Export Excel bị lỗi?**

A: Đảm bảo thư mục `report/` tồn tại và có quyền ghi. Kiểm tra `openpyxl` đã cài (`pip install openpyxl`).

---

## Thông tin kỹ thuật

| Thông tin | Chi tiết |
|-----------|---------|
| Ngôn ngữ | Python 3.10+ |
| Detection | YOLOv8 (Ultralytics) |
| Tracking | ByteTrack |
| Giao diện | OpenCV (không dùng web framework) |
| Phép đo tốc độ | Perspective Transform + PPM |
| Đơn vị tốc độ | km/h |
| Warped space | 400 × 600 px |
| PPM mặc định | 50.0 px/m (12m → 600px) |
| Classes nhận diện | car (2), bus (5), truck (7) |
| Smoothing window | 15 frame |
| Track buffer | 120 frame (~4s @ 30fps) |

---

*ITS_2026 — Developed for intelligent highway traffic monitoring.*
