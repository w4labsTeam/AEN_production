import yaml
import subprocess
import cv2
import numpy as np
from ultralytics import YOLO
from app.services.camera_manager import latest_frames
import threading

model_lock = threading.Lock()

CONFIG_FILE = "app/models/config.yaml"

with open(CONFIG_FILE, "r") as file:
    config = yaml.safe_load(file)

# Load YOLO models
    
boundary_model_path = config["models"]["boundary"]
number_model_path = config["models"]["number"]

boundary_model_v2_path = config["models"]["boundary_v2"]

boundary_model = YOLO(boundary_model_path)
number_model = YOLO(number_model_path)

boundary_model_v2 = YOLO(boundary_model_v2_path)

last_valid_predictions = {}

# List of RTSP camera URLs
# url_list = ["rtsp://AENadmin:AENcamera@192.168.1.62:554/11"]

# def calculate_Sludge_Level(tank_number, frame):
#     """Runs inference on the given tank's camera feed and returns predicted sludge level"""
#     # rtsp_url = url_list[tank_number - 1]

#     if tank_number > 4:

#     with model_lock:
#         if tank_number <= 4:
#             results_boundary = boundary_model_v2.predict(source=frame, conf=0.6, save=False, verbose=False)
#         else:
#             results_boundary = boundary_model.predict(source=frame, conf=0.6, save=False, verbose=False)
#             results_number = number_model.predict(source=frame, conf=0.25, save=False, verbose=False)

#     # if not ret:
#     #     print("Failed to capture frame")
#     #     return None, None
#     if frame is None:
#         # print("No frame available for the given tank number")
#         return None, None

#     boundary_y = None

#     if len(results_boundary[0].boxes) > 0:
#         for result in results_boundary[0].boxes:
#             bbox = result.xyxy[0].cpu().numpy()
#             y_min_b, y_max_b = int(bbox[1]), int(bbox[3])
#             boundary_y = (y_max_b + y_min_b) / 2

#             # cv2.rectangle(captured_frame, (int(bbox[0]), int(bbox[1])), (int(bbox[2]), int(bbox[3])), (0, 255, 0), 2)

#     # Run number detection
    
#     predicted_number = None
#     min_distance = float('inf')

#     if len(results_number[0].boxes) > 0 and boundary_y is not None:
#         for result in results_number[0].boxes:
#             bbox = result.xyxy[0].cpu().numpy()
#             y_min, y_max = int(bbox[1]), int(bbox[3])
#             class_index = int(result.cls.cpu().numpy())
#             boundary_value = results_number[0].names[class_index]

#             box_center = (y_min + y_max) / 2

#             distance = abs(box_center - boundary_y)

#             if distance < min_distance:
#                 min_distance = distance
#                 predicted_number = boundary_value

#             cv2.line(frame, (0, int(boundary_y)), (frame.shape[1], int(boundary_y)), (255, 0, 0), 2)

#         if min_distance > 50:  # Threshold for proximity to boundary line
#             predicted_number = None
#     # frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

#     if predicted_number is not None:
#         last_valid_predictions[tank_number] = predicted_number
#         print(last_valid_predictions)
#         return predicted_number, frame
    
#     # If no prediction but we had one before
#     if tank_number in last_valid_predictions:
#         print(last_valid_predictions, " - using last valid prediction")
#         return last_valid_predictions[tank_number], frame

#     # Startup case: no previous value
#     return None, frame


def calculate_Sludge_Level(tank_number, frame):
    # if frame is None:
    #     # print("No frame available for the given tank number")
    #     return None, None

    # if tank_number > 4:

    #     with model_lock:
    #         results_boundary = boundary_model.predict(source=frame, conf=0.6, save=False, verbose=False)
    #         results_number = number_model.predict(source=frame, conf=0.25, save=False, verbose=False)

    #     # if not ret:
    #     #     print("Failed to capture frame")
    #     #     return None, None

    #     boundary_y = None

    #     if len(results_boundary[0].boxes) > 0:
    #         for result in results_boundary[0].boxes:
    #             bbox = result.xyxy[0].cpu().numpy()
    #             y_min_b, y_max_b = int(bbox[1]), int(bbox[3])
    #             boundary_y = (y_max_b + y_min_b) / 2

    #             # cv2.rectangle(captured_frame, (int(bbox[0]), int(bbox[1])), (int(bbox[2]), int(bbox[3])), (0, 255, 0), 2)

    #     # Run number detection
        
    #     predicted_number = None
    #     min_distance = float('inf')

    #     if len(results_number[0].boxes) > 0 and boundary_y is not None:
    #         for result in results_number[0].boxes:
    #             bbox = result.xyxy[0].cpu().numpy()
    #             y_min, y_max = int(bbox[1]), int(bbox[3])
    #             class_index = int(result.cls.cpu().numpy())
    #             boundary_value = results_number[0].names[class_index]

    #             box_center = (y_min + y_max) / 2

    #             distance = abs(box_center - boundary_y)

    #             if distance < min_distance:
    #                 min_distance = distance
    #                 predicted_number = boundary_value

    #             # cv2.line(frame, (0, int(boundary_y)), (frame.shape[1], int(boundary_y)), (255, 0, 0), 2)

    #         if min_distance > 50:  # Threshold for proximity to boundary line
    #             predicted_number = None

    #     if predicted_number is not None:
    #         last_valid_predictions[tank_number] = predicted_number
    #         return predicted_number, frame

    #     if tank_number in last_valid_predictions:
    #         return last_valid_predictions[tank_number], frame

    #     return None, frame
    
    # else:
    print(tank_number)

    with model_lock:
        results = boundary_model_v2.predict(source=frame, conf=0.4, save=False, verbose=False)

    result = results[0]

    sludge_y = None 
    predicted_number = None 

    number_boxes = []

    SLUDGE_CLASS = 16

    for box in result.boxes:
        cls = int(box.cls[0])
        confidence = float(box.conf[0])

        x1, y1, x2, y2 = box.xyxy[0].cpu().numpy().astype(int)

        if cls == SLUDGE_CLASS:
            sludge_y = y1
        
        else:
            number_boxes.append({
                "value": int(result.names[cls]),
                "center_y": (y1 + y2) / 2
            })

    if sludge_y is not None and len(number_boxes)>0:

        min_distance = float('inf')

        for number in number_boxes:
            distance = abs(number["center_y"] - sludge_y)
            
            if distance < min_distance:
                min_distance = distance
                predicted_number = number["value"]

        if min_distance > 50:  # Threshold for proximity to boundary line
            predicted_number = None
    
    if predicted_number is not None:
        last_valid_predictions[tank_number] = predicted_number
        return predicted_number, frame

    if tank_number in last_valid_predictions:
        return last_valid_predictions[tank_number], frame

    return None, frame
