import time
import threading
import cv2
import os
import numpy as np

from datetime import datetime
from app.database import SessionLocal
from app import crud
from app.services.camera_manager import frame_buffers, frame_locks
from calculate_Sludge_Level import calculate_Sludge_Level
from app.services.modbus_service import modbus_queue

latest_results = {}  # {tank_id: {"sludge_level": value, "timestamp": timestamp}}
results_lock = threading.Lock()

ml_active_lock = threading.Lock()

last_saved = {}
SAVE_INTERVAL = 3600  # 1 hour

MIN_INTERVAL = 100.0  # Minimum interval in seconds between ML runs for the same tank

def update_latest_result(tank_id, sludge_level, snapshot, timestamp):
    with results_lock:
        previous = latest_results.get(tank_id)

        if sludge_level is None:
            if previous is not None:
                latest_results[tank_id] = {
                    "sludge_level": previous["sludge_level"],
                }
                return previous["sludge_level"]

            latest_results[tank_id] = {
                "sludge_level": None,
            }
            return None

        latest_results[tank_id] = {
            "sludge_level": sludge_level,
        }
        return sludge_level


def ml_worker(active_tanks):
    last_run = {}
    last_sent = {}

    while True:
        with ml_active_lock:
            # active_tanks = [1,2,3,4]  
            tanks = list(active_tanks)

        if not tanks:
            time.sleep(1)
            continue

        now = time.time()
        for tank_id in tanks:
            last = last_run.get(tank_id, 0.0)

            if now - last < MIN_INTERVAL:  # Run every MIN_INTERVAL seconds per tank
                continue

            with frame_locks[tank_id]:
                if not frame_buffers[tank_id]:
                    continue
                frame = frame_buffers[tank_id][-1]
                frame_copy = frame.copy()

            # if last_frame is None or not np.array_equal(frame, last_frame):
            #     print(f"New frame detected for tank {tank_id}, running ML processing.")
            #     last_frame = frame.copy()
            #     frame_copy = frame.copy()
            # else:
            #     print(f"No new frame for tank {tank_id}, skipping ML processing.")
            #     continue

            # last_save_time = last_saved.get(tank_id, 0)

            # if now - last_save_time >= SAVE_INTERVAL:

            #     tank_folder = os.path.join(
            #         "dataset",
            #         f"tank_{tank_id}"
            #     )

            #     os.makedirs(tank_folder, exist_ok=True)

            #     timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

            #     filename = os.path.join(
            #         tank_folder,
            #         f"{timestamp}.jpg"
            #     )

            #     cv2.imwrite(filename, frame_copy)

            #     print(f"Saved image: {filename}")

            #     last_saved[tank_id] = now

            print("running ml model for", tank_id)

            sludge_level, snapshot = calculate_Sludge_Level(tank_id, frame_copy)

            print(f"Tank {tank_id}: Sludge Level = {sludge_level}")

            sludge_level = update_latest_result(
                tank_id,
                sludge_level,
                snapshot,
                now,
            )

            if sludge_level is not None and sludge_level != last_sent.get(tank_id):
                modbus_queue.put((tank_id, sludge_level))
                last_sent[tank_id] = sludge_level
                print(latest_results)

            last_run[tank_id] = now
        
        time.sleep(1)

def start_ml_worker(active_tanks):
    t = threading.Thread(
        target=ml_worker, 
        args=(active_tanks,),
        daemon=True,
    )
    t.start()

