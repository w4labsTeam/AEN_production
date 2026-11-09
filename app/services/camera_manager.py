import subprocess
import numpy as np
import threading
import time
from collections import deque
from app.services.modbus_service import modbus_queue
import cv2   

WIDTH = 640
HEIGHT = 480
FRAME_SIZE = WIDTH * HEIGHT * 3  # 3 bytes per pixel for BGR format

ERROR_CAMERA_DISCONNECTED = -1

latest_frames = {}     # tank_id -> np.ndarray

frame_buffers = {}
frame_locks = {}
latest_jpeg = {}        # tank_id -> bytes
jpeg_locks = {}         # tank_id -> Lock

camera_status = {}        # tank_id -> bool (True if camera is streaming)
camera_status_lock = {}

last_frame_time = {}
last_frame_time_lock = {}

def init_camera_state(camera_ids):
    for tank_id in camera_ids:
        frame_buffers[tank_id] = deque(maxlen=1)
        frame_locks[tank_id] = threading.Lock()

        latest_jpeg[tank_id] = None
        jpeg_locks[tank_id] = threading.Lock()

        camera_status[tank_id] = False
        camera_status_lock[tank_id] = threading.Lock()

        last_frame_time[tank_id] = 0
        last_frame_time_lock[tank_id] = threading.Lock()    

def _read_full_frame(process):
    raw = b""
    while len(raw) < FRAME_SIZE:
        chunk = process.stdout.read(FRAME_SIZE - len(raw))
        if not chunk:
            return None
        raw += chunk
    return raw


def frame_reader(cam_id, process):
    while True:
        # print(f"[Camera {cam_id}] Frame received")
        raw = _read_full_frame(process)

        if raw is None:
            break

        frame = np.frombuffer(raw, dtype=np.uint8).reshape((HEIGHT, WIDTH, 3))

        with frame_locks[cam_id]:
            frame_buffers[cam_id].append(frame)

        with camera_status_lock[cam_id]:
            camera_status[cam_id] = True

        with last_frame_time_lock[cam_id]:
            last_frame_time[cam_id] = time.time()

def camera_worker(cam_id, rtsp_url):

    while True:

        print(f"[Camera {cam_id}] Starting FFmpeg")

        cmd = [
            "ffmpeg",
            "-rtsp_transport", "tcp",
            "-fflags", "nobuffer",
            "-flags", "low_delay",
            "-an",
            "-i", rtsp_url,
            "-pix_fmt", "bgr24",
            "-s", f"{WIDTH}x{HEIGHT}",
            "-f", "rawvideo",
            "-"
        ]

        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            bufsize=10**8
        )

        with last_frame_time_lock[cam_id]:
            last_frame_time[cam_id] = time.time()

        with camera_status_lock[cam_id]:
            camera_status[cam_id] = False

        # start reader thread
        t = threading.Thread(
            target=frame_reader,
            args=(cam_id, process),
            daemon=True
        )
        t.start()

        # # watchdog loop
        while True:

            time.sleep(1)

            with last_frame_time_lock[cam_id]:
                dt = time.time() - last_frame_time[cam_id]

            # if (cam_id >= 4):
            if dt > 30:
                print(f"[Camera {cam_id}] timeout detected")

                with camera_status_lock[cam_id]:
                    camera_status[cam_id] = False

                # modbus_queue.put((cam_id, ERROR_CAMERA_DISCONNECTED))

                break

        # cleanup
        try:
            process.terminate()
        except:
            pass

        try:
            process.kill()
        except:
            pass

        try:
            process.stdout.close()
        except:
            pass

        print(f"[Camera {cam_id}] Reconnecting in 60 seconds")
        time.sleep(60)

def start_all_cameras(rtsp_urls, camera_ids):
    if len(rtsp_urls) != len(camera_ids):
        raise ValueError("Length of rtsp_urls and camera_ids must be the same.")

    for cam_id, url in zip(camera_ids, rtsp_urls):
        print(f"Starting camera {cam_id} with URL: {url}")
        t = threading.Thread(
            target=camera_worker,
            args=(cam_id, url),
            daemon=True
        )
        t.start()




