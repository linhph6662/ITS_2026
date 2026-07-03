"""
app.py - Ứng dụng Streamlit đếm xe và đo tốc độ từ video.
Sử dụng YOLOv8 + ByteTrack để phát hiện và theo dõi phương tiện.

Chạy: streamlit run app.py
"""

import os
import tempfile
import time

import cv2
import pandas as pd
import streamlit as st

from tracker import VehicleTracker
from utils import export_to_excel


# =============================================================================
# CẤU HÌNH TRANG STREAMLIT
# =============================================================================
st.set_page_config(
    page_title="🚗 Đếm Xe & Đo Tốc Độ",
    page_icon="🚗",
    layout="wide",
    initial_sidebar_state="expanded",
)

# =============================================================================
# CSS TÙY CHỈNH
# =============================================================================
st.markdown(
    """
    <style>
    /* ===== Ẩn thanh Streamlit mặc định ===== */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}

    /* ===== Font và nền chính ===== */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');

    .stApp {
        font-family: 'Inter', sans-serif;
    }

    /* ===== Header chính ===== */
    .main-header {
        background: linear-gradient(135deg, #0f0c29, #302b63, #24243e);
        padding: 1.5rem 2rem;
        border-radius: 16px;
        margin-bottom: 1.5rem;
        text-align: center;
        box-shadow: 0 8px 32px rgba(0,0,0,0.3);
    }
    .main-header h1 {
        color: #ffffff;
        font-size: 2rem;
        font-weight: 700;
        margin: 0;
        letter-spacing: -0.5px;
    }
    .main-header p {
        color: #a0aec0;
        font-size: 0.95rem;
        margin: 0.5rem 0 0;
    }

    /* ===== Card thống kê ===== */
    .stat-card {
        background: linear-gradient(145deg, #1a1a2e, #16213e);
        border: 1px solid rgba(255,255,255,0.08);
        border-radius: 12px;
        padding: 1.2rem;
        text-align: center;
        box-shadow: 0 4px 15px rgba(0,0,0,0.2);
        transition: transform 0.2s ease;
    }
    .stat-card:hover {
        transform: translateY(-2px);
    }
    .stat-value {
        font-size: 2rem;
        font-weight: 700;
        background: linear-gradient(135deg, #00d2ff, #3a7bd5);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin: 0;
    }
    .stat-label {
        color: #a0aec0;
        font-size: 0.8rem;
        text-transform: uppercase;
        letter-spacing: 1px;
        margin-top: 0.3rem;
    }

    /* ===== Bảng Log ===== */
    .log-section {
        background: linear-gradient(145deg, #1a1a2e, #16213e);
        border: 1px solid rgba(255,255,255,0.08);
        border-radius: 12px;
        padding: 1.2rem;
        margin-top: 1rem;
    }
    .log-section h3 {
        color: #e2e8f0;
        font-size: 1.1rem;
        margin-bottom: 0.8rem;
    }

    /* ===== Video container ===== */
    .video-container {
        background: #0a0a1a;
        border-radius: 12px;
        padding: 4px;
        border: 1px solid rgba(255,255,255,0.05);
        box-shadow: 0 8px 32px rgba(0,0,0,0.4);
    }

    /* ===== Sidebar ===== */
    section[data-testid="stSidebar"] {
        background: linear-gradient(180deg, #0f0c29, #1a1a2e);
    }
    section[data-testid="stSidebar"] .stMarkdown h2 {
        color: #e2e8f0;
    }

    /* ===== Status badges ===== */
    .status-running {
        background: linear-gradient(135deg, #00b09b, #96c93d);
        color: white;
        padding: 0.3rem 1rem;
        border-radius: 20px;
        font-size: 0.85rem;
        font-weight: 600;
        display: inline-block;
    }
    .status-paused {
        background: linear-gradient(135deg, #f093fb, #f5576c);
        color: white;
        padding: 0.3rem 1rem;
        border-radius: 20px;
        font-size: 0.85rem;
        font-weight: 600;
        display: inline-block;
    }
    .status-idle {
        background: linear-gradient(135deg, #667eea, #764ba2);
        color: white;
        padding: 0.3rem 1rem;
        border-radius: 20px;
        font-size: 0.85rem;
        font-weight: 600;
        display: inline-block;
    }

    /* ===== Nút bấm ===== */
    .stButton > button {
        border-radius: 8px;
        font-weight: 600;
        padding: 0.5rem 1.5rem;
        transition: all 0.2s ease;
    }
    .stButton > button:hover {
        transform: translateY(-1px);
        box-shadow: 0 4px 12px rgba(0,0,0,0.3);
    }

    /* ===== Progress info ===== */
    .progress-info {
        background: rgba(255,255,255,0.05);
        border-radius: 8px;
        padding: 0.6rem 1rem;
        color: #a0aec0;
        font-size: 0.85rem;
        margin-top: 0.5rem;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


# =============================================================================
# KHỞI TẠO SESSION STATE
# =============================================================================
def init_session_state():
    """Khởi tạo các biến session state mặc định."""
    defaults = {
        "tracker": None,           # VehicleTracker instance
        "video_path": None,        # Đường dẫn video đang xử lý
        "is_playing": False,       # Trạng thái đang phát
        "is_paused": False,        # Trạng thái tạm dừng
        "current_frame_num": 0,    # Frame hiện tại
        "total_frames": 0,         # Tổng số frame
        "fps": 30.0,               # FPS của video
        "processed_log": [],       # Log xe đã xử lý
        "processed_stats": {},     # Thống kê đã xử lý
        "video_completed": False,  # Video đã xử lý xong
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


init_session_state()


# =============================================================================
# HEADER
# =============================================================================
st.markdown(
    """
    <div class="main-header">
        <h1>🚗 Đếm Xe & Đo Tốc Độ Từ Video</h1>
        <p>Phát hiện bằng YOLOv8 · Theo dõi bằng ByteTrack · Đo tốc độ thời gian thực</p>
    </div>
    """,
    unsafe_allow_html=True,
)


# =============================================================================
# SIDEBAR - CẤU HÌNH
# =============================================================================
with st.sidebar:
    st.markdown("## ⚙️ Cấu Hình")

    # --- Upload video ---
    st.markdown("### 📹 Video Đầu Vào")
    uploaded_file = st.file_uploader(
        "Chọn file video",
        type=["mp4", "avi"],
        help="Hỗ trợ định dạng MP4 và AVI",
    )

    # Xử lý khi upload video
    if uploaded_file is not None:
        # Lưu video vào thư mục tạm
        temp_dir = tempfile.mkdtemp()
        temp_path = os.path.join(temp_dir, uploaded_file.name)
        with open(temp_path, "wb") as f:
            f.write(uploaded_file.getbuffer())

        # Cập nhật path nếu video mới
        if st.session_state.video_path != temp_path:
            st.session_state.video_path = temp_path
            st.session_state.is_playing = False
            st.session_state.is_paused = False
            st.session_state.video_completed = False

            # Lấy thông tin video
            cap = cv2.VideoCapture(temp_path)
            st.session_state.fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
            st.session_state.total_frames = int(
                cap.get(cv2.CAP_PROP_FRAME_COUNT)
            )
            cap.release()

            st.success(f"✅ Đã tải: **{uploaded_file.name}**")

    st.markdown("---")

    # --- Cấu hình đo tốc độ ---
    st.markdown("### 📏 Cấu Hình Tốc Độ")

    pixel_per_meter = st.slider(
        "Pixel / Mét",
        min_value=1.0,
        max_value=50.0,
        value=8.0,
        step=0.5,
        help="Số pixel tương ứng 1 mét thực tế. Điều chỉnh theo góc camera.",
    )

    # Hiển thị FPS video
    if st.session_state.video_path:
        st.info(f"🎬 FPS Video: **{st.session_state.fps:.1f}**")
        st.info(
            f"🎞️ Tổng frame: **{st.session_state.total_frames:,}**"
        )

    st.markdown("---")

    # --- Model YOLO ---
    st.markdown("### 🤖 Model")
    model_path = st.text_input(
        "Đường dẫn model YOLO",
        value="yolo26n.pt",
        help="File model YOLOv8 (.pt)",
    )

    # --- Confidence threshold ---
    conf_threshold = st.slider(
        "Ngưỡng Confidence",
        min_value=0.1,
        max_value=0.9,
        value=0.3,
        step=0.05,
        help="Ngưỡng tin cậy cho detection",
    )

    st.markdown("---")

    # --- Thông tin ---
    st.markdown("### ℹ️ Hướng Dẫn")
    st.markdown(
        """
        1. **Upload** video (MP4/AVI)
        2. Điều chỉnh **Pixel/Mét**
        3. Nhấn **▶ Play** để bắt đầu
        4. Xem **Log** và **Thống kê**
        5. **Xuất Excel** khi hoàn tất
        """
    )


# =============================================================================
# NỘI DUNG CHÍNH
# =============================================================================

# --- Nút điều khiển ---
col_btn1, col_btn2, col_btn3, col_btn4 = st.columns(4)

with col_btn1:
    play_btn = st.button(
        "▶ Play",
        use_container_width=True,
        disabled=(
            st.session_state.video_path is None
            or st.session_state.is_playing
        ),
    )

with col_btn2:
    pause_btn = st.button(
        "⏸ Pause" if not st.session_state.is_paused else "▶ Resume",
        use_container_width=True,
        disabled=not st.session_state.is_playing,
    )

with col_btn3:
    reset_btn = st.button(
        "🔄 Reset",
        use_container_width=True,
        disabled=st.session_state.video_path is None,
    )

with col_btn4:
    # Trạng thái hiện tại
    if st.session_state.is_playing and not st.session_state.is_paused:
        st.markdown(
            '<div class="status-running">● Đang chạy</div>',
            unsafe_allow_html=True,
        )
    elif st.session_state.is_paused:
        st.markdown(
            '<div class="status-paused">⏸ Tạm dừng</div>',
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            '<div class="status-idle">○ Chờ</div>',
            unsafe_allow_html=True,
        )

# --- Xử lý nút bấm ---
if play_btn and st.session_state.video_path:
    # Khởi tạo tracker nếu chưa có
    if st.session_state.tracker is None:
        st.session_state.tracker = VehicleTracker(
            model_path=model_path,
            pixel_per_meter=pixel_per_meter,
            fps=st.session_state.fps,
        )
    else:
        st.session_state.tracker.update_config(
            pixel_per_meter=pixel_per_meter,
            fps=st.session_state.fps,
        )
    st.session_state.is_playing = True
    st.session_state.is_paused = False
    st.session_state.video_completed = False
    st.rerun()

if pause_btn:
    st.session_state.is_paused = not st.session_state.is_paused
    st.rerun()

if reset_btn:
    # Reset toàn bộ
    if st.session_state.tracker is not None:
        st.session_state.tracker.reset()
    st.session_state.is_playing = False
    st.session_state.is_paused = False
    st.session_state.current_frame_num = 0
    st.session_state.processed_log = []
    st.session_state.processed_stats = {}
    st.session_state.video_completed = False
    st.rerun()


# =============================================================================
# LAYOUT CHÍNH: VIDEO + THỐNG KÊ
# =============================================================================
col_video, col_stats = st.columns([2, 1])

with col_video:
    st.markdown("### 🎥 Video")
    video_placeholder = st.empty()
    progress_placeholder = st.empty()

with col_stats:
    st.markdown("### 📊 Thống Kê")
    stats_placeholder = st.empty()

# --- Bảng Log phía dưới ---
st.markdown("### 📋 Bảng Log Phương Tiện")
log_placeholder = st.empty()

# --- Nút xuất Excel ---
export_placeholder = st.empty()


# =============================================================================
# HÀM HIỂN THỊ THỐNG KÊ
# =============================================================================
def display_stats(stats: dict):
    """Hiển thị 4 card thống kê."""
    with stats_placeholder.container():
        # Tổng xe
        st.markdown(
            f"""
            <div class="stat-card">
                <p class="stat-value">{stats.get('total', 0)}</p>
                <p class="stat-label">Tổng Số Xe</p>
            </div>
            """,
            unsafe_allow_html=True,
        )
        st.markdown("")  # Spacing

        c1, c2 = st.columns(2)
        with c1:
            st.markdown(
                f"""
                <div class="stat-card">
                    <p class="stat-value">{stats.get('min_speed', 0):.1f}</p>
                    <p class="stat-label">Min Speed (km/h)</p>
                </div>
                """,
                unsafe_allow_html=True,
            )
        with c2:
            st.markdown(
                f"""
                <div class="stat-card">
                    <p class="stat-value">{stats.get('max_speed', 0):.1f}</p>
                    <p class="stat-label">Max Speed (km/h)</p>
                </div>
                """,
                unsafe_allow_html=True,
            )

        st.markdown("")  # Spacing
        st.markdown(
            f"""
            <div class="stat-card">
                <p class="stat-value">{stats.get('avg_speed', 0):.1f}</p>
                <p class="stat-label">Tốc Độ TB (km/h)</p>
            </div>
            """,
            unsafe_allow_html=True,
        )


def display_log(log: list):
    """Hiển thị bảng log phương tiện."""
    with log_placeholder.container():
        if log:
            df = pd.DataFrame(log)
            df.columns = [
                "ID",
                "Loại Xe",
                "Thời Gian Vào",
                "Thời Gian Ra",
                "Tốc Độ Max (km/h)",
            ]
            st.dataframe(
                df,
                use_container_width=True,
                hide_index=True,
                height=min(400, 40 + len(df) * 35),
            )
        else:
            st.info("📭 Chưa có dữ liệu. Nhấn Play để bắt đầu phân tích.")


# =============================================================================
# VÒNG LẶP XỬ LÝ VIDEO
# =============================================================================
if (
    st.session_state.is_playing
    and not st.session_state.is_paused
    and st.session_state.video_path
    and not st.session_state.video_completed
):
    tracker = st.session_state.tracker
    cap = cv2.VideoCapture(st.session_state.video_path)

    # Nhảy đến frame hiện tại (cho trường hợp resume)
    if st.session_state.current_frame_num > 0:
        cap.set(cv2.CAP_PROP_POS_FRAMES, st.session_state.current_frame_num)

    total = st.session_state.total_frames
    frame_count = st.session_state.current_frame_num

    while cap.isOpened():
        # Kiểm tra tạm dừng (sẽ xử lý ở lần rerun tiếp)
        success, frame = cap.read()
        if not success:
            # Video đã hết
            st.session_state.video_completed = True
            st.session_state.is_playing = False
            break

        frame_count += 1

        # Xử lý frame: detect + track + tính tốc độ + vẽ annotation
        annotated_frame = tracker.process_frame(frame)

        # Chuyển BGR → RGB để hiển thị trên Streamlit
        rgb_frame = cv2.cvtColor(annotated_frame, cv2.COLOR_BGR2RGB)

        # Hiển thị video frame
        video_placeholder.image(rgb_frame, channels="RGB", use_container_width=True)

        # Cập nhật progress
        progress = frame_count / total if total > 0 else 0
        progress_placeholder.markdown(
            f"""
            <div class="progress-info">
                📍 Frame: <b>{frame_count:,}</b> / {total:,}
                ({progress * 100:.1f}%)
                &nbsp;|&nbsp;
                ⏱ {frame_count / st.session_state.fps:.1f}s
            </div>
            """,
            unsafe_allow_html=True,
        )

        # Cập nhật thống kê và log mỗi 10 frame (tránh lag)
        if frame_count % 10 == 0 or frame_count == total:
            current_stats = tracker.get_statistics()
            current_log = tracker.get_vehicle_log()
            display_stats(current_stats)
            display_log(current_log)

            # Lưu vào session state
            st.session_state.processed_stats = current_stats
            st.session_state.processed_log = current_log

        # Lưu vị trí frame
        st.session_state.current_frame_num = frame_count

        # Delay nhỏ để Streamlit render kịp (không quá chậm)
        time.sleep(0.01)

    cap.release()

    # Cập nhật lần cuối
    if tracker:
        st.session_state.processed_stats = tracker.get_statistics()
        st.session_state.processed_log = tracker.get_vehicle_log()

    st.rerun()

else:
    # Không đang chạy → hiển thị dữ liệu đã có
    if st.session_state.processed_stats:
        display_stats(st.session_state.processed_stats)
    else:
        display_stats({"total": 0, "min_speed": 0, "max_speed": 0, "avg_speed": 0})

    display_log(st.session_state.processed_log)

    # Hiển thị thông báo khi video xong
    if st.session_state.video_completed:
        st.success("✅ **Phân tích hoàn tất!** Có thể xuất báo cáo Excel.")

    # Hiển thị video placeholder nếu chưa có video
    if not st.session_state.video_path:
        video_placeholder.markdown(
            """
            <div class="video-container" style="
                height: 400px;
                display: flex;
                align-items: center;
                justify-content: center;
                color: #4a5568;
                font-size: 1.1rem;
            ">
                📹 Upload video ở sidebar để bắt đầu
            </div>
            """,
            unsafe_allow_html=True,
        )


# =============================================================================
# XUẤT EXCEL
# =============================================================================
if st.session_state.processed_log:
    with export_placeholder.container():
        st.markdown("---")
        col_export1, col_export2 = st.columns([1, 3])
        with col_export1:
            excel_bytes = export_to_excel(
                st.session_state.processed_log,
                st.session_state.processed_stats,
            )
            st.download_button(
                label="📥 Xuất Báo Cáo Excel",
                data=excel_bytes,
                file_name="bao_cao_dem_xe.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True,
            )
        with col_export2:
            st.markdown(
                f"""
                <div class="progress-info">
                    📊 Báo cáo gồm 2 sheets: <b>Log Chi Tiết</b>
                    ({len(st.session_state.processed_log)} xe)
                    và <b>Tổng Hợp</b>
                </div>
                """,
                unsafe_allow_html=True,
            )
