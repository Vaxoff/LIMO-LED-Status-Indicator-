#!/usr/bin/env python3
"""
Tells the ESP32 which Limo it's plugged into, so if the board gets
swapped between robots it always learns the correct ID.

Reads this Jetson's own hostname (e.g. "limo780") and sends it over
USB serial as "LIMO_ID:limo780\n". Resends periodically so the ESP32
re-learns its ID automatically if it gets unplugged/replugged or
reset while this script keeps running.

Install first:
    uv pip install pyserial
"""

import logging
import signal
import socket
import sys
import time

import serial

SERIAL_PORT = "/dev/ttyACM1"   # check with: ls /dev/ttyACM* /dev/ttyUSB*
SERIAL_BAUD = 115200
RESEND_INTERVAL_SEC = 10

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
log = logging.getLogger("limo_id_sender")


def get_limo_id() -> str:
    """Returns this machine's hostname, e.g. 'limo780'."""
    return socket.gethostname()


def main():
    limo_id = get_limo_id()
    log.info("This robot's ID: %s", limo_id)

    try:
        ser = serial.Serial(SERIAL_PORT, SERIAL_BAUD, timeout=1)
    except Exception as e:
        log.error("Could not open serial port %s: %s", SERIAL_PORT, e)
        return

    time.sleep(2)  # give the ESP32 a moment after opening the port
    ser.reset_input_buffer()

    def handle_sigint(signum, frame):
        log.info("Shutting down...")
        ser.close()
        sys.exit(0)

    signal.signal(signal.SIGINT, handle_sigint)
    signal.signal(signal.SIGTERM, handle_sigint)

    def send_id():
        try:
            ser.write(f"LIMO_ID:{limo_id}\n".encode())
            log.info("Sent LIMO_ID:%s", limo_id)
        except Exception as e:
            log.error("Serial write failed: %s", e)

    send_id()

    last_sent = time.time()
    try:
        while True:
            # Print anything the ESP32 sends back (confirmation, debug logs)
            if ser.in_waiting:
                line = ser.readline().decode(errors="replace").strip()
                if line:
                    log.info("ESP32: %s", line)

            if time.time() - last_sent > RESEND_INTERVAL_SEC:
                send_id()
                last_sent = time.time()

            time.sleep(0.1)
    except KeyboardInterrupt:
        pass
    finally:
        ser.close()
        log.info("Closed.")


if __name__ == "__main__":
    main()