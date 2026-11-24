import threading
import time
import struct
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

PLCS = CONFIG.get("plcs", [])
QUEUE_SIZE = CONFIG["writer"]["queue_size"]

# One shared queue for all tanks
modbus_queue = Queue(maxsize=QUEUE_SIZE)
stop_event = threading.Event()

# ---------------------------------------------------------
# Tank to PLC & Register Mapping
# ---------------------------------------------------------
# Note: Corrected Tank 4 to 14-15 to avoid overlap with Tank 3 (12-13)
TANK_MAPPING = {
    # PLC 1: 192.168.0.101:502 (32-bit Float, LE Swapped)
    1: {"plc_ip": "192.168.0.101", "plc_port": 502, "registers": [8, 9], "type": "float32"},
    2: {"plc_ip": "192.168.0.101", "plc_port": 502, "registers": [10, 11], "type": "float32"},
    3: {"plc_ip": "192.168.0.101", "plc_port": 502, "registers": [12, 13], "type": "float32"},
    4: {"plc_ip": "192.168.0.101", "plc_port": 502, "registers": [14, 15], "type": "float32"},
    
    # PLC 2: 192.168.0.3:502 (16-bit Integer)
    5: {"plc_ip": "192.168.0.3", "plc_port": 502, "registers": [8], "type": "int16"},
    6: {"plc_ip": "192.168.0.3", "plc_port": 502, "registers": [9], "type": "int16"},
    7: {"plc_ip": "192.168.0.3", "plc_port": 502, "registers": [10], "type": "int16"},
    8: {"plc_ip": "192.168.0.3", "plc_port": 502, "registers": [11], "type": "int16"},
}

# ---------------------------------------------------------
# Request model
# ---------------------------------------------------------

class ModbusWriteRequest(BaseModel):
    tank_id: int = Field(ge=1, le=8)
    # Changed to float to accommodate 32-bit float requirements for tanks 1-4
    value: float = Field(ge=0.0) 


# ---------------------------------------------------------
# Helper for Float Conversion (LE Swapped / CDAB)
# ---------------------------------------------------------

def float_to_registers(value: float) -> list[int]:
    """
    Converts a 32-bit float into two 16-bit Modbus registers.
    LE Swapped (Word Swapped / CDAB): 
    The 32-bit float is packed in Little Endian byte order, 
    but the two 16-bit words are swapped.
    """
    # Pack as Big Endian to get standard bytes A, B, C, D
    packed = struct.pack('>f', float(value))
    # Unpack as Big Endian 16-bit words: reg1=AB, reg2=CD
    reg1, reg2 = struct.unpack('>HH', packed)
    # Swap the words to get CDAB (LE Swapped / Word Swapped)
    return [reg2, reg1]


# ---------------------------------------------------------
# Single Modbus worker (Handles multiple PLCs)
# ---------------------------------------------------------

def modbus_worker():
    # Dictionary to hold connections for each unique PLC
    clients = {}
    
    def get_client(ip: str, port: int) -> ModbusTcpClient:
        key = (ip, port)
        if key not in clients:
            clients[key] = ModbusTcpClient(ip, port=port, timeout=3)
        return clients[key]

    print(f"[MODBUS] Writer started")
    
    try:
        while not stop_event.is_set():
            try:
                tank_id, value = modbus_queue.get(timeout=0.5)
            except Empty:
                continue

            mapping = TANK_MAPPING.get(tank_id)
            if not mapping:
                print(f"[MODBUS] ERROR | Unknown tank_id {tank_id}")
                modbus_queue.task_done()
                continue

            ip = mapping["plc_ip"]
            port = mapping["plc_port"]
            registers = mapping["registers"]
            data_type = mapping["type"]
            
            client = get_client(ip, port)

            # Retry this write until it succeeds or shutdown begins
            while not stop_event.is_set():
                try:
                    if not client.is_socket_open():
                        if not client.connect():
                            raise ConnectionError(f"Unable to connect to PLC {ip}:{port}")

                    if data_type == "float32":
                        regs_to_write = float_to_registers(value)
                        response = client.write_registers(
                            address=registers[0],
                            values=regs_to_write
                        )
                    else:
                        response = client.write_register(
                            address=registers[0],
                            value=int(value)
                        )

                    if response is None or response.isError():
                        raise RuntimeError(f"PLC write failed: {response}")

                    print(
                        f"[MODBUS] SUCCESS | "
                        f"Tank {tank_id} | "
                        f"PLC {ip}:{port} | "
                        f"Registers {registers} | "
                        f"Value {value}"
                    )
                    break

                except Exception as e:
                    print(f"[MODBUS] ERROR | Tank {tank_id} | {e}")
                    client.close()
                    stop_event.wait(1)

            modbus_queue.task_done()

    finally:
        for client in clients.values():
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
        "plcs": [{"ip": p["ip"], "port": p["port"]} for p in PLCS],
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