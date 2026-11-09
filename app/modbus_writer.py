import threading
import time
from queue import Queue, Empty, Full
from contextlib import asynccontextmanager
from pathlib import Path

import yaml
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from pymodbus.client import ModbusTcpClient


# ---------------------------------------------------------
# Configuration
# ---------------------------------------------------------

CONFIG_PATH = (
    Path(__file__).resolve().parent
    / "config"
    / "modbus_writer.yaml"
)

with open(CONFIG_PATH, "r") as f:
    CONFIG = yaml.safe_load(f)

PLC_IP = CONFIG["plc"]["ip"]
PLC_PORT = CONFIG["plc"]["port"]
QUEUE_SIZE = CONFIG["writer"]["queue_size"]


# One shared queue for all eight tanks
modbus_queue = Queue(maxsize=QUEUE_SIZE)

stop_event = threading.Event()

# ---------------------------------------------------------
# Request model
# ---------------------------------------------------------

class ModbusWriteRequest(BaseModel):
    tank_id: int = Field(ge=1, le=8)
    value: int = Field(ge=0, le=65535)


# ---------------------------------------------------------
# Single Modbus worker
# ---------------------------------------------------------

def modbus_worker():

    client = ModbusTcpClient(
        PLC_IP,
        port=PLC_PORT,
        timeout=3
    )

    print(f"[MODBUS] Writer started")
    print(f"[MODBUS] PLC: {PLC_IP}:{PLC_PORT}")

    try:
        while not stop_event.is_set():

            try:
                tank_id, value = modbus_queue.get(timeout=0.5)
            except Empty:
                continue

            # Tank 1 -> register 0
            # Tank 8 -> register 7
            register_address = tank_id - 1

            # Retry this write until it succeeds or shutdown begins
            while not stop_event.is_set():

                try:
                    # Connect only when the socket is not open
                    if not client.is_socket_open():
                        if not client.connect():
                            raise ConnectionError(
                                "Unable to connect to PLC"
                            )

                    response = client.write_register(
                        address=register_address,
                        value=value
                    )

                    if response is None or response.isError():
                        raise RuntimeError(
                            f"PLC write failed: {response}"
                        )

                    print(
                        f"[MODBUS] SUCCESS | "
                        f"Tank {tank_id} | "
                        f"Register {register_address} | "
                        f"Value {value}"
                    )

                    break

                except Exception as e:

                    print(
                        f"[MODBUS] ERROR | "
                        f"Tank {tank_id} | {e}"
                    )

                    client.close()

                    # Wait before retrying
                    stop_event.wait(1)

            modbus_queue.task_done()

    finally:
        client.close()
        print("[MODBUS] Writer stopped")


# ---------------------------------------------------------
# HTTP API
# ---------------------------------------------------------

@asynccontextmanager
async def lifespan(app: FastAPI):

    stop_event.clear()

    worker_thread = threading.Thread(
        target=modbus_worker,
        daemon=True
    )

    worker_thread.start()

    yield

    stop_event.set()
    worker_thread.join(timeout=5)


app = FastAPI(lifespan=lifespan)


@app.get("/health")
def health():

    return {
        "status": "running",
        "plc_ip": PLC_IP,
        "plc_port": PLC_PORT,
        "queue_size": modbus_queue.qsize()
    }


@app.post("/write", status_code=202)
def receive_write(request: ModbusWriteRequest):

    try:
        modbus_queue.put_nowait(
            (request.tank_id, request.value)
        )

    except Full:
        raise HTTPException(
            status_code=503,
            detail="Modbus queue is full"
        )

    print(
        f"[HTTP] RECEIVED | "
        f"Tank {request.tank_id} | "
        f"Value {request.value}"
    )

    return {
        "accepted": True,
        "tank_id": request.tank_id,
        "value": request.value
    }
