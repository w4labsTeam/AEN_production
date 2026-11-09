import yaml
import subprocess
import cv2

# Load config file
CONFIG_FILE = "app/models/config.yaml"

with open(CONFIG_FILE, "r") as file:
    config = yaml.safe_load(file)

# Load camera URLs (extend list for multiple tanks if needed)
url_list = ["rtsp://AENadmin:AENcamera@192.168.1.62:554/11"]

def is_camera_accessible(rtsp_url, timeout=1):
    try:
        subprocess.check_output(
            [
                "ffprobe", "-v", "error",
                "-rtsp_transport", "tcp",
                "-timeout", str(timeout * 1000000),
                "-i", rtsp_url
            ],
            stderr=subprocess.STDOUT
        )
        return True
    except subprocess.CalledProcessError as e:
        print("ffprobe error:", e.output.decode())
        return False
    except FileNotFoundError:
        print("ffprobe not found. Make sure FFmpeg is installed and in PATH.")
        return False
    except subprocess.TimeoutExpired:
        print("ffprobe timed out.")
        return False
    except Exception as e:
        print(f"Unexpected error: {e}")
        return False

def capture_frames(rtsp_url):
    """Capture a single frame from the given RTSP URL"""
    if not is_camera_accessible(rtsp_url):
        print(f"Camera at {rtsp_url} is not accessible.")
        return None

    cap = cv2.VideoCapture(rtsp_url)
    if not cap.isOpened():
        print(f"Error: Unable to open video stream from {rtsp_url}")
        return None

    ret, frame = cap.read()
    cap.release()

    if not ret:
        print(f"Error: Unable to read frame from {rtsp_url}")
        return None

    return frame