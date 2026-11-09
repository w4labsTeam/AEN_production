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

    writer_url = config["modbus"]["writer_url"]

    init_camera_state(camera_ids)
    start_all_cameras(url_list, camera_ids)
    start_ml_worker(camera_ids)
    start_modbus_worker(camera_ids, writer_url)
