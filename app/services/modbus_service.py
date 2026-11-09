import threading
import time
import requests
from queue import Empty, Queue

# Queue for outgoing values
modbus_queue = Queue(maxsize=1000)  # Adjust maxsize as needed

def modbus_worker(active_tanks, writer_url):
    active_tanks = set(active_tanks)  # Convert to set for faster lookup
    session = requests.Session()  # Use a session for connection pooling

    print("[MODBUS] Writer started")
    print(f"[MODBUS CLIENT] writer: {writer_url}")
    print(f"[MODBUS CLIENT] active tanks: {active_tanks}")

    while True:
        try:
            tank_id, value = modbus_queue.get(timeout=0.5)

        except Empty:
            continue  # No new value, but we can still attempt to write the last known value

        try:
            if tank_id not in active_tanks:
                # print(f"Tank {tank_id} is not active. Skipping write.")
                continue
            payload = {
                "tank_id": tank_id,
                "value": value
            }

            while True:
                try:
                    response = session.post(
                        writer_url,
                        json=payload,
                        timeout=3  # Set a timeout for the request
                    )
                    response.raise_for_status()  # Raise an error for bad responses
                    print(
                        f"[MODBUS CLIENT] |"
                        f"Tank={tank_id} | Value={value}"
                    )

                    break
                except requests.RequestException as e:
                    print(
                        f"[MODBUS CLIENT] Error writing to tank {tank_id}: {e}. Retrying..."
                    )
                    time.sleep(1)  # Wait before retrying

        finally:
            modbus_queue.task_done()  # Mark the task as done
                      

def start_modbus_worker(active_tanks, writer_url):
    t = threading.Thread(
        target=modbus_worker,
        args=(active_tanks, writer_url),
        daemon=True
    )
    t.start()