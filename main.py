"""
main.py — Vehicle Tracking & Speed Measurement System
Run:  python main.py
Keys: P=Pause/Resume  Q=Quit. Các chức năng khác dùng nút bấm trên màn hình.
"""

import os

from ui.picker import run_picker
from ui.dashboard import run_dashboard

VIDEO_DIR  = "video"
REPORT_DIR = "report"


def main() -> None:
    os.makedirs(VIDEO_DIR,  exist_ok=True)
    os.makedirs(REPORT_DIR, exist_ok=True)

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
        # "reselect" → quay lại chọn video


if __name__ == "__main__":
    main()