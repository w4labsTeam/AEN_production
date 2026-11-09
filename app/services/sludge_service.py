import base64
import cv2
from app.services.ml_worker import latest_results, results_lock

def get_sludge_level(tank_id: int):
    with results_lock:
        result = latest_results.get(tank_id)

    if result is None:
        # print(f"No ML results available for tank {tank_id}")
        return None, None

    return result["sludge_level"], result["snapshot"]
