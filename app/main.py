import ctypes
import os

from networkx import config
import psutil
ctypes.windll.winmm.timeBeginPeriod(1)

import logging
logging.getLogger("pymodbus").setLevel(logging.CRITICAL)

from fastapi import FastAPI
from app.services.camera_manager import start_all_cameras, init_camera_state
from app.services.live_service import start_jpeg_encoders
from app.services.ml_worker import start_ml_worker
# from app.services.modbus_service import start_modbus_worker, start_modbus_read_worker
from app.services.modbus_service import start_modbus_worker
from .routes import tank
from .database import Base, engine
from fastapi.middleware.cors import CORSMiddleware

from app.config.config_loader import load_config

# Create DB tables
Base.metadata.create_all(bind=engine)

app = FastAPI(title="Oil Tank Monitoring API")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(tank.router)

@app.on_event("startup")
def startup():
    import psutil
    import os

    p = psutil.Process(os.getpid())
    p.nice(psutil.HIGH_PRIORITY_CLASS)

    config = load_config()
    url_list = config["cameras"]["urls"]
    camera_ids = config["tanks"]["ids"]

    plc_ip = config["modbus"]["plc_ip"]
    plc_port = config["modbus"]["plc_port"]

    # Your RTSP URLs (4 cameras)
    # url_list = [
    #     # "",
    #     # "",
    #     # "",
    #     # "",
    #     "rtsp://AENadmin:AENcamera123@192.168.0.61:554/12",
    #     "rtsp://AENadmin:AENcamera123@192.168.0.62:554/11",
    #     "rtsp://AENadmin:AENcamera123@192.168.0.63:554/12",
    #     "rtsp://AENadmin:AENcamera123@192.168.0.64:554/12"
    #     # "rtsp://AENadmin:AENcamera@192.168.0.65:554/12",
    #     # "rtsp://AENadmin:AENcamera@192.168.0.66:554/12",
    #     # "rtsp://admin:Kavi0728@192.168.0.67:554/12",
    #     # "rtsp://AENadmin:AENcamera@192.168.0.68:554/12",
    #     # "rtsp://AENadmin:AENcamera@192.168.0.65:554/11",
    #     # "rtsp://AENadmin:AENcamera@192.168.0.66:554/11",
    #     # "rtsp://AENadmin:AENcamera@192.168.0.67:554/11",
    #     # "rtsp://AENadmin:AENcamera@192.168.0.68:554/11",
    # ]

    # url_list = ["rtsp://admin:Kavi0728@192.168.1.64:554/11"]

    # camera_ids = list(range(1, len(url_list) + 1))

    init_camera_state(camera_ids)
    start_all_cameras(url_list, camera_ids)
    # start_jpeg_encoders(camera_ids=camera_ids)
    start_ml_worker(camera_ids)
    start_modbus_worker(camera_ids, plc_ip, plc_port)
    # start_modbus_read_worker()
