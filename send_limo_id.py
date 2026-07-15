#!/usr/bin/env python3
"""
Watches for ESP32 boards appearing on /dev/ttyACM* (any index - ACM0,
ACM1, etc) and tells each one which Limo it's plugged into, once per
connection - not repeatedly.

Designed to run as a systemd service at boot. Logs go to stdout, which
systemd/journald captures automatically. View them with:
    journalctl -u limo-id-sender -f

Install first:
    uv pip install pyserial
"""

import glob
import logging
import signal
import socket
import time

import serial

BAUD = 115200
SCAN_INTERVAL_SEC = 2
LIMO_ID = socket.gethostname()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
log = logging.getLogger("limo_id_sender")

connections = {}   # port path -> serial.Serial
running = True


def handle_signal(signum, frame):
    global running
    log.info("Shutting down...")
    running = False


signal.signal(signal.SIGINT, handle_signal)
signal.signal(signal.SIGTERM, handle_signal)


def find_ports():
    return sorted(glob.glob("/dev/ttyACM*"))


def open_and_identify(port):
    try:
        ser = serial.Serial(port, BAUD, timeout=0.2)
        time.sleep(2)   # allow the board to finish resetting after USB open
        ser.reset_input_buffer()
        ser.write(f"LIMO_ID:{LIMO_ID}\n".encode())
        log.info("New device on %s -> sent LIMO_ID:%s", port, LIMO_ID)
        connections[port] = ser
    except Exception as e:
        log.error("Failed to open %s: %s", port, e)


def main():
    log.info("This robot's ID: %s", LIMO_ID)
    log.info("Watching for ESP32 boards on /dev/ttyACM*...")

    while running:
        current_ports = find_ports()

        # New devices: open + send ID once
        for port in current_ports:
            if port not in connections:
                open_and_identify(port)

        # Removed devices: clean up so a future reconnect triggers a resend
        for port in list(connections.keys()):
            if port not in current_ports:
                log.info("Device removed: %s", port)
                try:
                    connections[port].close()
                except Exception:
                    pass
                del connections[port]

        # Drain and log anything the ESP32 sends back (confirmation, debug output)
        for port, ser in list(connections.items()):
            try:
                if ser.in_waiting:
                    line = ser.readline().decode(errors="replace").strip()
                    if line:
                        log.info("[%s] %s", port, line)
            except Exception as e:
                log.error("Read error on %s: %s", port, e)
                try:
                    ser.close()
                except Exception:
                    pass
                del connections[port]

        time.sleep(SCAN_INTERVAL_SEC)

    for ser in connections.values():
        try:
            ser.close()
        except Exception:
            pass


if __name__ == "__main__":
    main()