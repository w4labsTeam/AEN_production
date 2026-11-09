import cv2
import threading
import time
from app.services.camera_manager import frame_buffers, frame_locks, latest_jpeg, jpeg_locks
import threading

def jpeg_encoder_worker(tank_id, fps=10):
    interval = 1.0 / fps

    while True:
        with frame_locks[tank_id]:
            if not frame_buffers[tank_id]:
                frame = None
            else:
                frame = frame_buffers[tank_id][-1]

        if frame is None:
            time.sleep(0.05)
            continue

        success, jpeg = cv2.imencode(
            ".jpg", frame,
            [cv2.IMWRITE_JPEG_QUALITY, 75]
        )
        if success:
            with jpeg_locks[tank_id]:
                latest_jpeg[tank_id] = jpeg.tobytes()

        time.sleep(interval)

def start_jpeg_encoders(camera_ids):
    for tank_id in camera_ids:
        t = threading.Thread(
            target=jpeg_encoder_worker,
            args=(tank_id,),
            daemon=True
        )
        t.start()

def generate_frames(tank_id: int):
    while True:
        if tank_id not in latest_jpeg:
            # print(f"No JPEG entry for tank {tank_id}")
            time.sleep(0.05)
            continue

        with jpeg_locks[tank_id]:
            jpeg = latest_jpeg.get(tank_id)

        if jpeg is None:
            # print(f"No JPEG available for tank {tank_id}")
            time.sleep(0.05)
            continue

        yield (
            b"--frame\r\n"
            b"Content-Type: image/jpeg\r\n\r\n"
            + jpeg +
            b"\r\n"
        )

        time.sleep(0.03)  # UI pacing only