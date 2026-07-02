# Highway Vehicle Monitoring System

A Python 3.12 application designed for highway vehicle monitoring, featuring real-time detection, tracking, vehicle counting, and speed estimation.

## Project Structure

```
highway_vehicle_monitoring_system/
│
├── main.py
├── requirements.txt
├── README.md
│
├── ui/
│   ├── main_window.py
│   ├── history_window.py
│   └── settings_dialog.py
│
├── core/
│   ├── detector.py
│   ├── tracker.py
│   ├── counter.py
│   ├── speed_calculator.py
│   ├── video_processor.py
│   └── worker.py
│
├── database/
│   └── database.py
│
├── utils/
│   ├── config.py
│   ├── logger.py
│   └── helper.py
│
├── history/
│   └── images/
│
├── reports/
│
├── models/
│
└── assets/
```

## Setup and Installation

1. Make sure you have **Python 3.12** installed.
2. Install the required dependencies:
   ```bash
   pip install -r requirements.txt
   ```

## Running the Application

To launch the GUI window application:
```bash
python main.py
```
