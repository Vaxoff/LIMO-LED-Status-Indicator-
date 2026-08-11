#!/usr/bin/env python3
"""
Watches for ESP32 boards appearing on /dev/ttyACM* (any index - ACM0,
ACM1, etc) and tells each one which Limo it's plugged into.

Unlike a naive "send once when the port shows up" approach, this:
  1. Pulses DTR/RTS on open to force a real hardware reset of the board
     (the same trick esptool/Arduino Serial Monitor use). This works around
     a known issue on native-USB ESP32 boards (S2/S3/C3) where the USB-CDC
     peripheral can get stuck after a hot unplug/replug and never recovers
     without an actual EN-pin reset.
  2. Retries sending LIMO_ID until the board ACKs it, instead of a single
     fire-and-forget write. This covers the case where the board isn't
     finished booting/connecting to WiFi yet when we first write.
  3. Listens for "REQUEST_ID" from the board and resends immediately,
     so even if our first attempts get lost, the board's own nagging
     will trigger a resend.

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

# Handshake tuning
ID_SEND_RETRY_INTERVAL_SEC = 1.0     # how often to re-send LIMO_ID while waiting for ACK
ID_SEND_MAX_WAIT_SEC = 20.0          # give up logging retries loudly after this long (keeps trying anyway)
BOOT_SETTLE_SEC = 2.0                # time to let the board finish resetting before first write

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
log = logging.getLogger("limo_id_sender")

# port path -> dict with keys: ser, acked (bool), last_send_time, first_seen_time, warned
connections = {}
running = True


def handle_signal(signum, frame):
    global running
    log.info("Shutting down...")
    running = False


signal.signal(signal.SIGINT, handle_signal)
signal.signal(signal.SIGTERM, handle_signal)


def find_ports():
    return sorted(glob.glob("/dev/ttyACM*"))


def hardware_reset(ser):
    """
    Pulse DTR/RTS to force the board through a real EN-pin reset, the same
    way esptool and the Arduino Serial Monitor do. This is what actually
    reinitializes the ESP32's USB-CDC peripheral after a hot replug.

    This is best-effort: it depends on the board having an auto-reset
    circuit (most ESP32 dev boards do, whether via a USB-UART bridge chip
    or native USB CDC-on-boot). If the board doesn't support it, this is
    a harmless no-op.
    """
    try:
        ser.setDTR(False)
        ser.setRTS(True)
        time.sleep(0.1)
        ser.setRTS(False)
        time.sleep(0.1)
        ser.setDTR(True)
    except Exception as e:
        log.warning("Hardware reset pulse failed (continuing anyway): %s", e)


def open_and_track(port):
    try:
        ser = serial.Serial(port, BAUD, timeout=0.2)
        hardware_reset(ser)
        time.sleep(BOOT_SETTLE_SEC)  # let the board finish booting before we start writing
        ser.reset_input_buffer()

        now = time.time()
        connections[port] = {
            "ser": ser,
            "acked": False,
            "last_send_time": 0,
            "first_seen_time": now,
            "warned": False,
        }
        log.info("New device on %s -> resetting and starting ID handshake", port)
        send_id(port)
    except Exception as e:
        log.error("Failed to open %s: %s", port, e)


def send_id(port):
    entry = connections.get(port)
    if entry is None:
        return
    try:
        entry["ser"].write(f"LIMO_ID:{LIMO_ID}\n".encode())
        entry["last_send_time"] = time.time()
        log.info("Sent LIMO_ID:%s to %s", LIMO_ID, port)
    except Exception as e:
        log.error("Write error on %s: %s", port, e)


def main():
    log.info("This robot's ID: %s", LIMO_ID)
    log.info("Watching for ESP32 boards on /dev/ttyACM*...")

    while running:
        current_ports = find_ports()

        # New devices: open, reset, and start the ID handshake
        for port in current_ports:
            if port not in connections:
                open_and_track(port)

        # Removed devices: clean up so a future reconnect triggers a fresh handshake
        for port in list(connections.keys()):
            if port not in current_ports:
                log.info("Device removed: %s", port)
                try:
                    connections[port]["ser"].close()
                except Exception:
                    pass
                del connections[port]

        # Read from every connected device; handle ACKs and REQUEST_ID
        for port, entry in list(connections.items()):
            ser = entry["ser"]
            try:
                if ser.in_waiting:
                    line = ser.readline().decode(errors="replace").strip()
                    if not line:
                        continue

                    if line == f"ACK:{LIMO_ID}":
                        if not entry["acked"]:
                            log.info("[%s] Confirmed LIMO_ID received", port)
                        entry["acked"] = True
                    elif line == "REQUEST_ID":
                        # Board is asking (or asking again) — answer right away
                        send_id(port)
                    else:
                        log.info("[%s] %s", port, line)
            except Exception as e:
                log.error("Read error on %s: %s", port, e)
                try:
                    ser.close()
                except Exception:
                    pass
                del connections[port]
                continue

            # Retry sending the ID until we get an ACK
            if not entry["acked"]:
                now = time.time()
                if now - entry["last_send_time"] >= ID_SEND_RETRY_INTERVAL_SEC:
                    send_id(port)
                if not entry["warned"] and (now - entry["first_seen_time"]) > ID_SEND_MAX_WAIT_SEC:
                    log.warning(
                        "[%s] Still no ACK after %.0fs — board may not be running "
                        "the updated firmware, or isn't finishing WiFi/boot.",
                        port, ID_SEND_MAX_WAIT_SEC,
                    )
                    entry["warned"] = True

        time.sleep(SCAN_INTERVAL_SEC)

    for entry in connections.values():
        try:
            entry["ser"].close()
        except Exception:
            pass


if __name__ == "__main__":
    main()