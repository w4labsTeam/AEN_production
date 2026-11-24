
import subprocess
import numpy as np
import threading
import time
from collections import deque

WIDTH = 640
HEIGHT = 480
FRAME_SIZE = WIDTH * HEIGHT * 3

# Camera acquisition settings
CAPTURE_INTERVAL = 60       
RETRY_INTERVAL = 10          
FFMPEG_TIMEOUT = 20          
CAMERA_START_OFFSET = 2     

ERROR_CAMERA_DISCONNECTED = -1

latest_frames = {}

frame_buffers = {}
frame_locks = {}

latest_jpeg = {}
jpeg_locks = {}

camera_status = {}
camera_status_lock = {}

last_frame_time = {}
last_frame_time_lock = {}


# ---------------------------------------------------------
# Initialize camera states
# ---------------------------------------------------------

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


# ---------------------------------------------------------
# Capture exactly one frame from RTSP
# ---------------------------------------------------------

def capture_one_frame(rtsp_url):

    cmd = [
        "ffmpeg",
        "-hide_banner",
        "-loglevel", "error",
        "-rtsp_transport", "tcp",
         "-fflags", "nobuffer",       # <-- Reduces buffering/latency
        "-flags", "low_delay",       # <-- Forces low delay decoding
        "-analyzeduration", "100000",# <-- Stops probing stream format too long
        "-probesize", "100000",      # <-- Limits initial data probe size
        "-i", rtsp_url,
        "-an",
        "-sn",
        "-dn",
        "-frames:v", "1",
        "-vf", f"scale={WIDTH}:{HEIGHT}",
        "-pix_fmt", "bgr24",
        "-f", "rawvideo",
        "pipe:1"
    ]

    result = subprocess.run(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=FFMPEG_TIMEOUT,
        check=True
    )

    raw = result.stdout

    if len(raw) != FRAME_SIZE:
        raise RuntimeError(
            f"Invalid frame size: {len(raw)} bytes"
        )

    frame = np.frombuffer(
        raw,
        dtype=np.uint8
    ).reshape((HEIGHT, WIDTH, 3))

    return frame.copy()


# ---------------------------------------------------------
# Camera worker
# ---------------------------------------------------------

def camera_worker(cam_id, rtsp_url, initial_delay=0):

    print(
        f"[Camera {cam_id}] Worker started. "
        f"Initial delay: {initial_delay}s"
    )

    if initial_delay > 0:
        time.sleep(initial_delay)

    while True:

        try:

            print(f"[Camera {cam_id}] Capturing image...")

            frame = capture_one_frame(rtsp_url)

            # Store only the latest frame
            with frame_locks[cam_id]:
                frame_buffers[cam_id].append(frame)

            # Update camera status
            with camera_status_lock[cam_id]:
                camera_status[cam_id] = True

            with last_frame_time_lock[cam_id]:
                last_frame_time[cam_id] = time.time()

            print(
                f"[Camera {cam_id}] "
                f"Capture successful"
            )

            # Wait until the next scheduled capture
            time.sleep(CAPTURE_INTERVAL)

        except subprocess.TimeoutExpired:

            print(
                f"[Camera {cam_id}] "
                f"FFmpeg capture timeout"
            )

            with camera_status_lock[cam_id]:
                camera_status[cam_id] = False

            time.sleep(RETRY_INTERVAL)

        except subprocess.CalledProcessError as e:

            print(
                f"[Camera {cam_id}] "
                f"FFmpeg error: {e.stderr.decode(errors='replace')}"
            )

            with camera_status_lock[cam_id]:
                camera_status[cam_id] = False

            time.sleep(RETRY_INTERVAL)

        except Exception as e:

            print(
                f"[Camera {cam_id}] "
                f"Capture error: {e}"
            )

            with camera_status_lock[cam_id]:
                camera_status[cam_id] = False

            time.sleep(RETRY_INTERVAL)


# ---------------------------------------------------------
# Start all cameras
# ---------------------------------------------------------

def start_all_cameras(rtsp_urls, camera_ids):

    if len(rtsp_urls) != len(camera_ids):
        raise ValueError(
            "Length of rtsp_urls and camera_ids must be the same."
        )

    for index, (cam_id, url) in enumerate(
        zip(camera_ids, rtsp_urls)
    ):

        initial_delay = index * CAMERA_START_OFFSET
        print(
            f"Starting camera {cam_id} "
            f"with initial delay {initial_delay}s"
        )
        t = threading.Thread(
            target=camera_worker,
            args=(cam_id, url, initial_delay),
            daemon=True
        )
        t.start()
