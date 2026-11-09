from unittest import result

from pymodbus.client import ModbusTcpClient
import threading
import time
from queue import Empty, Queue

# Queue for outgoing values
modbus_queue = Queue(maxsize=100)  # Adjust maxsize as needed


def modbus_worker(active_tanks, plc_ip, plc_port):
    client = ModbusTcpClient(plc_ip, port=plc_port)

    # last_tank_id = 1
    # last_value = 0  

    # while True:
    #     try:
    #         tank_id, value = modbus_queue.get(timeout=0.5)
    #         last_tank_id = tank_id
    #         last_value = value
    
    #     except Empty:
    #         # No new value, but we can still attempt to write the last known value
    #         tank_id = last_tank_id
    #         value = last_value

    #     try:
    #         if client.connect():
    #             # print("Connected to PLC")
    #             # Map tank_id to register address
    #             register_address = tank_id - 1  # Assuming tank_id starts at 1 and maps to register 0, 1, 2, ...

    #             # Convert to int (important)
    #             value_int = int(value)

    #             client.write_register(
    #                 address=register_address,
    #                 value=value_int,
    #             )
    #             # print(f"Wrote to PLC: Tank {tank_id} -> {value_int}")   

    #     except Exception as e:
    #         print(f"Modbus error: {e}")
    #         pass

    #     time.sleep(0.1)  # slight pacing

    while True:
        try:
            tank_id, value = modbus_queue.get(timeout=0.5)

            if tank_id not in active_tanks:
                # print(f"Tank {tank_id} is not active. Skipping write.")
                continue

            register_address = tank_id - 1
            value_int = int(value)

            if not client.connect():
                print("Failed to connect to PLC")
                time.sleep(1)
                continue

            print(f"Tank {tank_id} written to PLC")

            client.write_register(
                address=register_address,
                value=value_int,
            )

        except Empty:
            # No new value, but we can still attempt to write the last known value
            continue

        except Exception as e:
            print(f"Modbus error: {e}")
            time.sleep(1)


# def modbus_read_worker():
#     client = ModbusTcpClient(PLC_IP, port=PLC_PORT)

#     while True:
#         try:
#             if not client.connect():
#                 # print("Read worker: Failed to connect to PLC")
#                 time.sleep(1)
#                 continue

#             # Example: read 5 holding registers starting at address 0
#             result = client.read_holding_registers(
#                 address=0,
#                 count=5,
#             )

#             if result.isError():
#                 # print("Read error:", result)
#                 pass
#             else:
#                 registers = result.registers
#                 # print("Read Registers:", registers)

#                 # 👉 Here you can update your GUI safely using signals

#         except Exception as e:
#             print("Read worker exception:", e)
#             pass

#         time.sleep(1)  # read every 1 second

# def start_modbus_read_worker():
#     t = threading.Thread(
#         target=modbus_read_worker,
#         daemon=True
#     )
#     t.start()

# def start_modbus_worker():
#     t = threading.Thread(
#         target=modbus_worker,
#         daemon=True
#     )
#     t.start()

def start_modbus_worker(active_tanks, plc_ip, plc_port):
    t = threading.Thread(
        target=modbus_worker,
        args=(active_tanks, plc_ip, plc_port),
        daemon=True
    )
    t.start()