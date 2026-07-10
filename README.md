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
| 🚗 **Phát hiện xe** | YOlO26 nhận diện ô tô, xe buýt, xe tải trên đường cao tốc |
| 🔍 **Theo dõi xe** | ByteTrack duy trì ID ổn định cho từng xe qua nhiều frame |
| 📐 **Đo tốc độ** | Perspective Transform + khoảng cách thực 12m → km/h |
| 📊 **Thống kê** | Tổng xe, tốc độ tối đa/tối thiểu/trung bình theo thời gian thực |
| 📝 **Xuất báo cáo** | File Excel (.xlsx) chi tiết từng xe |

### Đặc điểm nổi bật

- **Chỉ xe cơ giới lớn**: Nhận diện đúng 3 lớp COCO — `car (2)`, `bus (5)`, `truck (7)` — phù hợp với đường cao tốc, không phát hiện xe máy/xe đạp
- **Không cần camera đặc biệt**: Hoạt động với camera thường, file `.mp4` / `.avi` / `.mov` / `.mkv`
- **Đo tốc độ chuẩn**: Dựa trên khoảng cách vạch sơn thực tế 12m — không cần calibration phức tạp
- **Giao diện OpenCV hoàn toàn**: Không phụ thuộc web framework — chạy thẳng bằng `python main.py`
- **Tự điều chỉnh theo màn hình**: Cửa sổ tự scale theo độ phân giải thực tế (Windows/Linux)
- **Thêm video trực tiếp**: Nút "Thêm Video" mở file dialog để import video mà không cần copy thủ công

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

### Bước 2 — Tạo môi trường ảo ( Giúp tách bạch hệ thống/ Có thể dùng chính môi trường của máy tính)

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
| `ultralytics` | ≥ 8.0.0 | YOlO26 detection + ByteTrack |
| `opencv-python` | ≥ 4.8.0 | Xử lý video + giao diện |
| `numpy` | ≥ 1.24.0 | Tính toán ma trận |
| `pandas` | ≥ 2.0.0 | Xuất báo cáo |
| `openpyxl` | ≥ 3.1.0 | Ghi file Excel |
| `lapx` | ≥ 0.5.0 | Linear Assignment (ByteTrack) |
| `pillow` | ≥ 10.0.0 | Anti-aliased text rendering |

> **Lưu ý `pillow`**: Bắt buộc phải có — hệ thống dùng PIL để render văn bản anti-aliased lên canvas OpenCV (thay thế `cv2.putText`), đảm bảo chữ sắc nét ở mọi độ phân giải.

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

> **Cách nhanh hơn**: Dùng nút **"Thêm Video"** trong giao diện để import video từ bất kỳ nơi nào trên máy (file dialog + tự động copy vào `video/`).

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
│   └── yolo26n.pt           # YOLO model weights (~5.3 MB)
│
├── core/                    # Logic nghiệp vụ (không phụ thuộc UI)
│   ├── __init__.py
│   ├── tracker.py           # VehicleTracker: detect + track + speed
│   └── utils.py             # Tính tốc độ, format, xuất Excel
│
├── ui/                      # Giao diện OpenCV
│   ├── __init__.py
│   ├── theme.py             # Màu sắc, layout, hàm vẽ dùng chung + PIL text
│   ├── picker.py            # Màn hình chọn video
│   └── dashboard.py         # Dashboard phân tích chính
│
├── video/                   # Thư mục chứa video đầu vào
│   └── .gitkeep
│
├── report/                  # Thư mục lưu báo cáo Excel (tự tạo)
│   └── .gitkeep
│
├── requirements.txt         # Danh sách thư viện
├── .gitignore
└── README.md
```

### Nguyên tắc phân tách module

```
main.py
  └── ui.picker        (chọn video → trả về path, fps, total_frames)
  └── ui.dashboard     (dashboard chính → trả về "quit" / "reselect")
        └── core.tracker   (VehicleTracker: detect + track + speed)
              └── core.utils   (calculate_speed, smooth_speed, export_to_excel)
        └── ui.theme       (màu sắc, layout, PIL text rendering)
```

---

## 5. Kiến trúc hệ thống

### Luồng xử lý tổng thể

```
Video File (.mp4/.avi/.mov/.mkv)
    │
    ▼
[cv2.VideoCapture] ──── raw frame (BGR) ────►
    │
    ▼
[VehicleTracker.process_frame(frame)]
    │
    ├─► [YOLO.track()]
    │       ├── detect: classes=[2,5,7] (car/bus/truck)
    │       ├── tracker: ByteTrack (config/bytetrack.yaml)
    │       └── conf ≥ 0.35
    │         │
    │         ▼
    │   [ROI Filter] ──── pointPolygonTest → chỉ xử lý xe TRONG ROI
    │         │
    │         ▼
    │   [Perspective Transform] ──── frame coords → warped (400×600 px)
    │         │
    │         ▼
    │   [Speed Calculation]
    │       ├── calculate_speed(prev_wpt, curr_wpt, ppm=50.0, fps)
    │       └── smooth_speed(history, window=15)
    │         │
    │         ▼
    │   [Motion Axis Detection] ──── tích lũy 60 vector để xác định trục chính
    │         │
    │         ▼
    │   [Counting Line Check] ──── đếm xe khi centroid cắt vạch (1 lần/xe)
    │         │
    │         ▼
    │   [Annotation]
    │       ├── bounding box (màu theo track ID)
    │       ├── label: "ID:{id} {type}" + "{speed} km/h"
    │       ├── trail: 20 vị trí centroid gần nhất
    │       ├── ROI overlay (cam bán trong suốt, 12% opacity)
    │       └── counting line (đường đứt nét xanh)
    │
    ▼
[build_dashboard()] ──── ghép video + stats panel + statusbar
    │
    ▼
[cv2.imshow()] ──── hiển thị lên màn hình
```

### Pipeline đo tốc độ

```
4 điểm ROI (tọa độ frame gốc)
        │
        ▼
cv2.getPerspectiveTransform()  →  Ma trận M (3×3)
        │
        ▼
Centroid xe (cx, cy) frame  →  cv2.perspectiveTransform(M)  →  Warped (x', y')
        │
        ▼
pixel_distance = √[(x'ₙ - x'ₙ₋₁)² + (y'ₙ - y'ₙ₋₁)²]   (warped space)
        │
        ▼
meter_distance = pixel_distance / PPM
  PPM = DST_HEIGHT / ROAD_MARKING_DISTANCE_M = 600 / 12.0 = 50.0 px/m
        │
        ▼
speed_ms  = meter_distance / (1 / FPS)
speed_kmh = speed_ms × 3.6
        │
        ▼
smooth_speed(history[-15:])  →  trung bình trượt 15 frame
```

### Xác định trục counting line (tự động)

Hệ thống không hard-code hướng vạch đếm. Sau khi thu thập **60 vector chuyển động** (dx, dy) trong warped space:

```python
if total_dx >= total_dy:
    counting_line_axis = "x"   # Xe di chuyển NGANG → vạch đứng
else:
    counting_line_axis = "y"   # Xe di chuyển DỌC → vạch ngang
```

Vạch đếm nằm ở **50%** (counting_line_pos = 0.5) trên trục chính đã xác định.

---

## 6. Hướng dẫn sử dụng

### 6.1 Màn hình chọn video

Khi khởi động, hệ thống hiển thị danh sách video trong thư mục `video/`:

```
┌─────────────────────────────────────────────────────────────┐
│ VEHICLE ANALYSIS SYSTEM  //  Select Input Video   3 file(s) │
├───┬──────────────────────────┬────────┬──────┬──────┬───────┤
│ # │ FILENAME                 │ RES    │ DUR  │ FPS  │ SIZE  │
├───┼──────────────────────────┼────────┼──────┼──────┼───────┤
│ 1 │ highway_cam1.mp4         │1920x1080│ 5:30 │  30  │ 375 MB│
│ 2 │ test-case-2.MOV          │1280x720 │12:45 │  60  │  89 MB│
└───┴──────────────────────────┴────────┴──────┴──────┴───────┘
```

**Thao tác:**

| Thao tác | Cách thực hiện |
|----------|----------------|
| Chọn video | Click vào dòng video trong danh sách |
| Bắt đầu phân tích | Click nút **START ANALYSIS** (góc phải) |
| Import video mới | Click nút **Thêm Video** → file dialog mở → tự copy vào `video/` |
| Thoát | Click nút **Thoát** hoặc nhấn `Q` / `Esc` |

> **Ghi chú**: Video được xếp theo tên file (`sorted(os.listdir())`). Metadata (FPS, duration, resolution, file size) được đọc trực tiếp từ `cv2.VideoCapture`.

### 6.2 Vẽ ROI — Bước quan trọng nhất

Sau khi dashboard mở, nhấn nút **"Vẽ ROI"** (hoặc phím `D` nếu được hỗ trợ) để vào chế độ vẽ. **Video tự động dừng** khi ROI mode bật.

**ROI (Region of Interest)** là vùng đo tốc độ — phải được căn chỉnh chính xác với vạch sơn trắng trên đường.

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

**Thứ tự click bắt buộc**: `P1 (TL) → P2 (TR) → P3 (BR) → P4 (BL)`

#### Sau khi vẽ xong 4 điểm:

- Hệ thống tự tính **Perspective Transform Matrix** (`cv2.getPerspectiveTransform`)
- Banner xanh lá **"ROI ✓"** xuất hiện — nhấn **"Resume"** để video tiếp tục
- Vùng ROI hiển thị màu cam bán trong suốt (opacity 12%)
- Vạch đếm xe (đường xanh đứt nét) xuất hiện ở giữa ROI sau khi hệ thống thu thập đủ 60 mẫu chuyển động

### 6.3 Nút bấm trong Dashboard

| Nút | Phím tắt | Chức năng |
|-----|----------|-----------|
| **Pause / Resume** | `P` | Dừng / tiếp tục phát video |
| **Vẽ ROI** | — | Bật chế độ vẽ ROI (video tự dừng, click 4 điểm theo thứ tự TL→TR→BR→BL) |
| **Xóa ROI** | — | Xóa ROI + reset toàn bộ tracking data |
| **Chọn lại** | — | Quay lại màn hình chọn video |
| **Export** | — | Xuất báo cáo Excel (lưu vào `report/`) |
| **Thoát** | `Q` | Đóng chương trình |

> **Lưu ý**: Hầu hết chức năng đều thao tác qua **nút bấm trên màn hình**. Phím tắt bàn phím chỉ có `P` (Pause/Resume) và `Q` (Thoát).

### 6.4 Cuộn Vehicle Log

Dùng **scroll wheel chuột** để cuộn lên/xuống trong bảng Vehicle Log (panel phải). Log hiển thị xe mới nhất ở trên cùng.

---

## 7. Cơ sở khoa học — Đo tốc độ

### 7.1 Vấn đề phối cảnh (Perspective Distortion)

Camera nhìn đường từ góc nghiêng làm cho:
- Vật ở xa trông **nhỏ hơn** vật ở gần
- Cùng 1m thực tế = **số pixel khác nhau** tùy vị trí trong frame
- → Không thể dùng pixel trực tiếp để tính tốc độ

### 7.2 Giải pháp: Perspective Transform (Bird's-Eye View)

```
Frame gốc (góc nghiêng)        Warped space (400×600 px)
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

### 7.3 Công thức tính tốc độ (từ `core/utils.py`)

```python
# calculate_speed(prev_centroid, curr_centroid, pixel_per_meter, fps)
dx = curr_centroid[0] - prev_centroid[0]
dy = curr_centroid[1] - prev_centroid[1]
pixel_distance = math.sqrt(dx * dx + dy * dy)   # warped space

meter_distance = pixel_distance / pixel_per_meter   # = pixel_dist / 50.0
time_seconds   = 1.0 / fps
speed_kmh      = (meter_distance / time_seconds) * 3.6
```

### 7.4 Làm mượt tốc độ (Moving Average)

Do phát hiện không hoàn hảo mỗi frame, tốc độ thô có thể dao động mạnh. Hệ thống dùng **trung bình trượt 15 frame**:

```python
# smooth_speed(speed_history, window=15)
recent = speed_history[-15:]
return sum(recent) / len(recent)
```

### 7.5 Vì sao khoảng cách vạch sơn = 12m?

Theo **TCVN 4054:2005** và **QCVN 41:2019** (Việt Nam):
- Vạch sơn phân cách làn đường cao tốc: đoạn sơn 3m + khoảng trống 9m → chu kỳ 12m
- Hoặc đoạn sơn 6m + khoảng trống 6m → cũng chu kỳ 12m

> 📐 **Kiểm tra lại với địa điểm cụ thể**: Nếu khoảng cách vạch tại vị trí camera khác 12m, hãy chỉnh `ROAD_MARKING_DISTANCE_M` trong `core/tracker.py`.

### 7.6 Đếm xe — Counting Line

Hệ thống đếm xe khi centroid **cắt qua counting line** ở giữa ROI:

- Vạch đếm ở **50%** trên trục chính (được xác định tự động qua motion analysis)
- Xe chỉ được đếm **1 lần** (track ID được lưu vào `counted_ids: set`)
- Hiển thị `COUNT: {n}` trên vạch đếm; `(calibrating...)` khi chưa đủ 60 mẫu

### 7.7 Màu sắc theo tốc độ

| Màu | Ngưỡng | Ý nghĩa |
|-----|--------|---------|
| 🟢 **Xanh lá** (GREEN) | < 60 km/h | Bình thường / chậm |
| 🟡 **Vàng** (YELLOW) | 60 – 100 km/h | Tốc độ cho phép |
| 🔴 **Đỏ** (RED) | > 100 km/h | Vượt tốc độ |

---

## 8. Cấu hình ByteTrack

File: `config/bytetrack.yaml`

```yaml
tracker_type: bytetrack

# Ngưỡng phát hiện
track_high_thresh: 0.35    # Confidence tối thiểu để tạo track mới (mặc định YOLO: 0.50)
track_low_thresh: 0.10     # Confidence thấp nhất cho secondary association
new_track_thresh: 0.40     # Confidence để tạo object hoàn toàn mới (mặc định YOLO: 0.60)

# Bộ nhớ track
track_buffer: 120          # Giữ track trong 120 frame dù không detect được
                           # = ~4 giây tại 30 FPS (xử lý khi xe bị khuất/mờ)

# Matching
match_thresh: 0.80         # IoU threshold để ghép detection với track cũ (mặc định: 0.70)
fuse_score: true           # Kết hợp confidence score + IoU

# Lọc nhiễu
min_box_area: 400          # Bỏ qua detection < 20×20 px (nhiễu nền, bóng đổ)
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
│           VIDEO PANEL (60%)               │  Avg Speed  Max Speed  Min Sp │
│                                            │  ┌────────┐ ┌────────┐ ┌────┐│
│    ROI polygon (cam bán trong suốt)       │  │  87.3  │ │ 124.6  │ │68.2││
│    Bounding boxes (màu theo track ID)     │  │  km/h  │ │  km/h  │ │km/h││
│    Speed labels (km/h)                    │  └────────┘ └────────┘ └────┘│
│    Trail đường đi (20 điểm gần nhất)     │                               │
│    Counting line (đứt nét xanh)           │  VEHICLE LOG                  │
│    COUNT: {n} label                       │  ID  TYPE  ENTRY   EXIT    SPD│
│                                            │   1  car  00:00:03 00:00:08  89│
│                                            │   2  truck 00:00:07 00:00:15 76│
│                                            │   3  bus  00:00:11 00:00:22 65│
│                                            │          ↕ scroll wheel        │
├────────────────────────────────────────────┴───────────────────────────────┤
│ Frame 1,234 / 9,876   12.5%  ████░░░░  FPS 28.3  ROI ✓                   │
│     [Pause] [Vẽ ROI] [Xóa ROI] [Chọn lại] [Export] [Thoát]               │  ← Statusbar
└────────────────────────────────────────────────────────────────────────────┘
```

### Layout chi tiết

| Vùng | Tỉ lệ | Nội dung |
|------|-------|---------|
| **Header** | Toàn chiều rộng | Logo, trạng thái LIVE/PAUSED, tên file video |
| **Video Panel** | 60% chiều rộng | Frame annotated + ROI overlay + counting line |
| **Stat Panel** | 40% chiều rộng | Tổng xe, tốc độ avg/max/min, Vehicle Log có scroll |
| **Status Bar** | Toàn chiều rộng | Progress bar, FPS, ROI indicator, các nút bấm |

### Trạng thái xe trong Video Panel

| Biểu tượng | Ý nghĩa |
|------------|---------|
| Box **dày** (3px) + dấu ● xanh góc | Xe đã đếm (đã qua vạch counting line) |
| Box **mỏng** (2px) | Xe trong ROI, chưa qua vạch đếm |
| Box **xám nhạt** (1px) | Xe ngoài ROI (chỉ để debug, không tracking) |
| Trail đường đi | 20 vị trí centroid gần nhất |

### Màu track ID

Mỗi track ID được tô màu khác nhau bằng công thức HSV:

```python
hue = (track_id * 47) % 180   # Phân bố đều 180 mức màu
hsv = np.array([[[hue, 255, 220]]])
bgr = cv2.cvtColor(hsv, cv2.COLOR_HSV2BGR)
```

### Tự động scale theo màn hình

`ui/theme.py` tự phát hiện độ phân giải màn hình thực tế khi load:

```python
WIN_W, WIN_H = _detect_screen_size(max_ratio=0.92)
# Windows: ctypes.windll.user32.GetSystemMetrics()
# Linux:   xrandr --current (fallback)
# Default: 1920×1080
```

Tất cả font size, padding, button size đều scale theo `_SX = WIN_W / 1920.0` và `_SY = WIN_H / 1080.0`.

---

## 10. Xuất báo cáo Excel

Nhấn nút **"Export"** trong dashboard để xuất báo cáo. File lưu tại:

```
report/vehicle_report_YYYYMMDD_HHMMSS.xlsx
```

> Thư mục `report/` được tạo tự động bởi `main.py` nếu chưa tồn tại.

### Sheet 1: Log Chi Tiết

| ID | Loại Xe | Thời Gian Vào | Thời Gian Ra | Tốc Độ Max (km/h) |
|----|---------|--------------|-------------|-------------------|
| 1  | car     | 00:00:03     | 00:00:08    | 89.4 |
| 2  | truck   | 00:00:07     | 00:00:15    | 76.1 |
| 3  | bus     | 00:00:11     | 00:00:22    | 65.8 |

- **Loại xe**: `car`, `bus`, hoặc `truck` (từ YOLO class names)
- **Thời gian**: Tính theo số frame và FPS (`format_time(frame_number, fps)`)
- **Tốc độ Max**: Tốc độ cao nhất trong tất cả frame khi xe hiện diện trong ROI

### Sheet 2: Tổng Hợp

| Chỉ Số | Giá Trị |
|--------|---------| 
| Tổng số xe | 42 |
| Tốc độ thấp nhất (km/h) | 58.3 |
| Tốc độ cao nhất (km/h) | 134.7 |
| Tốc độ trung bình (km/h) | 87.2 |

> **Lưu ý**: Thống kê chỉ tính trên xe đã **qua counting line** (`counted_ids`), không tính xe chỉ đi vào ROI rồi quay ra.

---

## 11. Giải thích từng module

### `main.py`

Entry point duy nhất. Tạo thư mục `video/` và `report/` nếu chưa có, sau đó điều phối vòng lặp chính:

```python
while True:
    vpath, vfps, vtotal = run_picker()   # Chờ người dùng chọn video
    if vpath is None: break              # Người dùng thoát

    result = run_dashboard(vpath, vfps, vtotal)
    if result == "quit": break           # Thoát
    # result == "reselect" → quay lại chọn video
```

---

### `core/tracker.py` — `VehicleTracker`

**Class chính của hệ thống.** Quản lý toàn bộ logic detect + track + speed.

**Hằng số quan trọng:**

```python
ROAD_MARKING_DISTANCE_M = 12.0    # Khoảng cách thực giữa 2 vạch (m)
DST_WIDTH               = 400     # Chiều rộng warped space (px)
DST_HEIGHT              = 600     # Chiều cao warped space (px) — tương ứng 12m
DEFAULT_PPM             = 50.0    # = DST_HEIGHT / ROAD_MARKING_DISTANCE_M
HIGHWAY_CLASS_IDS       = [2, 5, 7]   # car, bus, truck
BYTETRACK_CFG           = "config/bytetrack.yaml"
```

**Các method public:**

| Method | Mô tả |
|--------|-------|
| `__init__(model_path, fps)` | Load YOLO model, khởi tạo state |
| `set_roi(points)` | Nhận 4 điểm TL→TR→BR→BL, tính Perspective Matrix |
| `clear_roi()` | Xóa ROI + toàn bộ tracking data (track history, speed, counts) |
| `reset()` | Xóa tracking data, **giữ nguyên ROI** |
| `process_frame(frame)` | Xử lý 1 frame BGR, trả về frame đã annotate |
| `get_vehicle_log()` | Trả về `list[dict]` — log từng xe |
| `get_statistics()` | Trả về `dict` — tổng hợp thống kê |

**Lịch sử tracking** (tất cả là `defaultdict`):

```python
self.track_history  = defaultdict(list)   # {id: [(cx, cy), ...]} — tối đa 50 → trim về 30
self.speed_history  = defaultdict(list)   # {id: [speed_kmh, ...]}
self.vehicle_info   = {}                  # {id: {type, entry_frame, last_frame, max_speed, counted}}
self.counted_ids    = set()               # Track ID đã qua vạch đếm
```

---

### `core/utils.py`

Tập hợp các hàm tính toán thuần túy, không có side effect.

| Function | Signature | Mô tả |
|----------|-----------|-------|
| `calculate_speed` | `(prev, curr, ppm, fps) → float` | Tính km/h từ 2 centroid warped |
| `smooth_speed` | `(history, window=15) → float` | Moving average tốc độ |
| `format_time` | `(frame_number, fps) → str` | `"HH:MM:SS"` từ số frame |
| `get_vehicle_class_name` | `(class_id, class_names) → str` | Tên loại xe từ YOLO class ID |
| `export_to_excel` | `(vehicle_log, stats) → bytes` | Tạo file Excel 2 sheets, trả về bytes |

---

### `ui/theme.py`

Định nghĩa toàn bộ hệ thống thiết kế. **Không có logic nghiệp vụ.**

**Layout (tự scale theo màn hình):**

```python
WIN_W, WIN_H  # Kích thước cửa sổ (tự phát hiện, mặc định 1920×1080)
HEADER_H      # Chiều cao thanh header (~56px)
STATUSBAR_H   # Chiều cao status bar (~60px)
VIDEO_W       # Chiều rộng video panel (= WIN_W × 60%)
STAT_W        # Chiều rộng stat panel (= WIN_W × 40%)
CONTENT_H     # Chiều cao nội dung (= WIN_H - HEADER_H - STATUSBAR_H)
```

**Bảng màu (BGR format):**

| Hằng số | Màu BGR | Dùng cho |
|---------|---------|---------|
| `BG` | (22, 22, 22) | Nền chính |
| `PANEL` | (32, 32, 32) | Nền panel stat |
| `HDR` | (42, 42, 42) | Header / section header |
| `AMBER` | (0, 160, 255) | Nhấn cam — accent chính |
| `GREEN` | (80, 175, 80) | Tốc độ bình thường |
| `YELLOW` | (40, 200, 210) | Tốc độ cảnh báo |
| `RED` | (55, 55, 210) | Tốc độ quá nhanh |
| `ROI_CLR` | (0, 180, 255) | Viền ROI polygon |

**Text rendering:** Dùng **PIL (Pillow)** thay vì `cv2.putText` để có anti-aliased text. Font ưu tiên: `Segoe UI (Windows)` → `Arial` → `Calibri` → DejaVu Sans (Linux) → PIL default.

**Drawing primitives:**

```python
fillr(img, x1, y1, x2, y2, color)          # Hình chữ nhật đặc
bordr(img, x1, y1, x2, y2, color, thick)   # Viền hình chữ nhật
hline(img, x1, x2, y, color, thick)        # Đường ngang
vline(img, x, y1, y2, color, thick)        # Đường đứng
put(img, s, x, y, color, scale, thick)     # Text căn trái (PIL)
put_right(img, s, rx, y, ...)              # Text căn phải
put_center(img, s, cx, y, ...)             # Text căn giữa
get_text_width(s, scale, ...) → int        # Đo chiều rộng text
```

---

### `ui/picker.py`

Màn hình chọn video. Quét thư mục `video/`, hiển thị metadata.

**Tính năng:**
- **Scan video**: `scan_videos(video_dir)` — quét `.mp4/.avi/.mov/.mkv`, đọc metadata qua `cv2.VideoCapture`
- **Hover highlight**: Dòng chuột đang ở được tô nền `HOV_BG`
- **Selection**: Dòng được chọn tô nền `SEL_BG` + dải cam bên trái + tên file màu AMBER
- **Info panel**: Panel bên phải hiển thị chi tiết video được chọn (Name, Resolution, Duration, Frames, FPS, Size)
- **Import video**: Nút "Thêm Video" → `subprocess` + `tkinter.filedialog` → `shutil.copy2` vào `video/`
- **Thoát**: Nút "Thoát" hoặc `Q`/`Esc`

**API:**

```python
run_picker() -> (video_path: str | None, fps: float, total_frames: int)
# Trả về (None, 0, 0) nếu người dùng chọn thoát
```

---

### `ui/dashboard.py`

Dashboard chính. Tích hợp `VehicleTracker` với giao diện OpenCV.

**Các hàm render:**

| Hàm | Mô tả |
|-----|-------|
| `_draw_header(canvas, video_name, is_paused)` | Thanh header + trạng thái LIVE/PAUSED |
| `_draw_video_panel(canvas, frame, roi_mode, ...)` | Panel video + ROI overlay (2 chế độ: đang vẽ / đã xác nhận) |
| `_draw_stat_panel(canvas, stats, vehicle_log, log_scroll)` | Panel thống kê + Vehicle Log có scroll |
| `_draw_statusbar(canvas, frame_num, total_frames, fps, ...)` | Progress bar + nút bấm → trả về `list[{action, rect}]` |
| `build_dashboard(...)` | Tổng hợp tất cả panel → `(canvas, buttons)` |

**Frame timing:**

```python
frame_delay = 1.0 / video_fps         # Thời gian mỗi frame (giây)
next_frame_time = time.perf_counter()  # Timestamp phải đọc frame tiếp theo
# Sau mỗi frame: next_frame_time += frame_delay
# Nếu bị trễ quá 1 frame: reset để tránh catch-up burst
```

**Tọa độ canvas ↔ frame:**

```python
_get_video_transform(frame)        # → (scale, ox, oy, nw, nh)
_canvas_to_frame(cx, cy, scale, ox, oy)  # Canvas → frame (khi click ROI)
_frame_to_canvas(fx, fy, scale, ox, oy)  # Frame → canvas (khi vẽ overlay)
```

**API:**

```python
run_dashboard(video_path, video_fps, total_frames) -> "quit" | "reselect"
```

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
#               Tăng để ổn định hơn, giảm để phản ứng nhanh hơn
```

### Thay đổi ngưỡng cảnh báo màu tốc độ

Trong `ui/dashboard.py`:

```python
spd_color = RED if spd > 100 else YELLOW if spd > 60 else GREEN
#                       ^^^                      ^^
#               Ngưỡng đỏ (km/h)          Ngưỡng vàng (km/h)
```

### Thay đổi kích thước warped space

Trong `core/tracker.py` (ảnh hưởng PPM):

```python
DST_WIDTH  = 400   # px — không ảnh hưởng tốc độ
DST_HEIGHT = 600   # px — tương ứng ROAD_MARKING_DISTANCE_M
```

### Thêm định dạng video mới

Trong `ui/picker.py`, hàm `scan_videos()`:

```python
if not filename.lower().endswith((".mp4", ".avi", ".mov", ".mkv")):
#                                  ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
#                           Thêm định dạng ở đây, ví dụ: ".ts", ".flv"
```

---

## 13. Câu hỏi thường gặp

**Q: Tốc độ hiển thị sai, quá nhanh hoặc quá chậm?**

A: Kiểm tra ROI có được vẽ đúng không. Cạnh dưới phải chạm vạch sơn dưới, cạnh trên phải bao trùm vạch sơn trên. Nếu khoảng cách vạch không phải 12m, chỉnh `ROAD_MARKING_DISTANCE_M` trong `core/tracker.py`.

---

**Q: Xe bị mất ID (ID thay đổi liên tục)?**

A: Tăng `track_buffer` trong `config/bytetrack.yaml` (ví dụ: 150 hoặc 180). Kiểm tra ROI có đủ rộng để xe luôn nằm trong vùng tracking.

---

**Q: COUNT hiển thị "(calibrating...)"?**

A: Bình thường — hệ thống cần thu thập **60 vector chuyển động** để xác định hướng di chuyển chính. Chỉ cần đợi vài chục xe đi qua.

---

**Q: Hệ thống không phát hiện được xe máy?**

A: Đây là thiết kế cố ý — hệ thống chỉ nhận diện `car (2)`, `bus (5)`, `truck (7)` theo COCO classes. Các đối tượng khác bị lọc ở tầng YOLO bằng `classes=[2, 5, 7]`.

---

**Q: Nhiều false positive (detect nhầm cây cối, bảng hiệu)?**

A: Tăng `conf` trong `process_frame()` từ 0.35 lên 0.45–0.50. Hoặc tăng `track_high_thresh` và `min_box_area` trong `config/bytetrack.yaml`.

---

**Q: Chạy chậm, FPS thấp?**

A:
- Dùng GPU NVIDIA (cài CUDA + `torch` GPU version trước khi cài `ultralytics`)
- Giảm độ phân giải video đầu vào (dùng tool như HandBrake)
- Dùng model nhỏ hơn nếu có

---

**Q: Cửa sổ không hiển thị / bị đen?**

A: Kiểm tra `opencv-python` đã cài đúng phiên bản. Trên Linux có thể cần `opencv-python-headless` thay thế. Kiểm tra DISPLAY environment variable trên Linux.

---

**Q: Import video (nút "Thêm Video") không hoạt động?**

A: Nút này dùng `tkinter.filedialog` qua `subprocess`. Trên Windows cần Python được cài với Tk support (mặc định có). Trên Linux cần cài `python3-tk` (`sudo apt install python3-tk`).

---

**Q: Export Excel bị lỗi?**

A: Đảm bảo thư mục `report/` tồn tại và có quyền ghi. Kiểm tra `openpyxl` đã cài (`pip install openpyxl`). Thư mục `report/` được tạo tự động khi chạy `main.py`.

---

## Thông tin kỹ thuật

| Thông tin | Chi tiết |
|-----------|---------|
| Ngôn ngữ | Python 3.10+ |
| Detection | YOlO26 (Ultralytics ≥ 8.0.0) |
| Tracking | ByteTrack (tích hợp trong Ultralytics) |
| Giao diện | OpenCV `cv2.imshow` — không dùng web framework |
| Text rendering | PIL (Pillow) anti-aliased — không dùng `cv2.putText` |
| Phép đo tốc độ | Perspective Transform + PPM |
| Đơn vị tốc độ | km/h |
| Warped space | 400 × 600 px |
| PPM mặc định | 50.0 px/m (12m thực → 600px warped) |
| Classes nhận diện | car (2), bus (5), truck (7) — COCO |
| Smoothing window | 15 frame |
| Track buffer | 120 frame (~4s @ 30fps) |
| Motion calibration | 60 vector để xác định trục counting line |
| Trail history | 20 điểm centroid gần nhất |
| Stats refresh | Mỗi 5 frame (`frame_num % 5 == 0`) |
| Screen scale | Tự phát hiện (Windows: ctypes, Linux: xrandr) |

---

*ITS_2026 — Developed for intelligent highway traffic monitoring.*
