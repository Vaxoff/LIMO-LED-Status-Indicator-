#!/usr/bin/env python3
"""
Standalone MQTT -> RGB/IR LED driver for Jetson (no ROS).

Subscribes to an MQTT topic that reports robot status
(CONNECTED / DISCONNECTED / UNEXPECTED_DISCONNECT / TRACKED / NOT_TRACKED)
and drives an RGB LED (+ optional IR strip MOSFET) directly via Jetson.GPIO.
"""

import logging
import signal
import sys
import threading
import time

import Jetson.GPIO as GPIO
import paho.mqtt.client as mqtt

# -----------------------
# Logging
# -----------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
log = logging.getLogger("mqtt_led_driver")

# -----------------------
# MQTT Config
# -----------------------
BROKER = "rasticvm.internal"
PORT = 1883
TOPIC = "limo/status"
KEEP_ALIVE_TIME_SEC = 60

# -----------------------
# GPIO Configuration
# -----------------------
RED_PIN = 37
GREEN_PIN = 35
BLUE_PIN = 33
INFRARED_STRIP_MOSFET_PIN = 31

PWM_FREQ_HZ = 100  # software PWM refresh rate

GPIO.setmode(GPIO.BOARD)
GPIO.setup(RED_PIN, GPIO.OUT)
GPIO.setup(GREEN_PIN, GPIO.OUT)
GPIO.setup(BLUE_PIN, GPIO.OUT)
GPIO.setup(INFRARED_STRIP_MOSFET_PIN, GPIO.OUT)


class SoftwarePWM:
    """
    Bit-banged PWM for boards/pins without real hardware PWM support.
    Runs a background thread toggling the pin at PWM_FREQ_HZ according
    to the current duty cycle (0-100).
    """

    def __init__(self, pin, freq_hz=PWM_FREQ_HZ):
        self.pin = pin
        self.period = 1.0 / freq_hz
        self.duty = 0.0
        self._lock = threading.Lock()
        self._stop_event = threading.Event()
        self._thread = threading.Thread(target=self._run, daemon=True)

    def start(self, duty=0):
        self.ChangeDutyCycle(duty)
        self._thread.start()

    def ChangeDutyCycle(self, duty):
        with self._lock:
            self.duty = max(0.0, min(100.0, duty))

    def _run(self):
        while not self._stop_event.is_set():
            with self._lock:
                duty = self.duty
            if duty <= 0:
                GPIO.output(self.pin, GPIO.LOW)
                time.sleep(self.period)
            elif duty >= 100:
                GPIO.output(self.pin, GPIO.HIGH)
                time.sleep(self.period)
            else:
                on_time = self.period * (duty / 100.0)
                off_time = self.period - on_time
                GPIO.output(self.pin, GPIO.HIGH)
                time.sleep(on_time)
                GPIO.output(self.pin, GPIO.LOW)
                time.sleep(off_time)

    def stop(self):
        self._stop_event.set()
        self._thread.join(timeout=1)
        GPIO.output(self.pin, GPIO.LOW)


red = SoftwarePWM(RED_PIN)
green = SoftwarePWM(GREEN_PIN)
blue = SoftwarePWM(BLUE_PIN)
red.start(0)
green.start(0)
blue.start(0)


# -----------------------
# LED Helper Functions
# -----------------------
def set_color(r, g, b):
    """r, g, b are duty cycles 0-100."""
    red.ChangeDutyCycle(r)
    green.ChangeDutyCycle(g)
    blue.ChangeDutyCycle(b)


def set_infrared(state: bool):
    GPIO.output(INFRARED_STRIP_MOSFET_PIN, GPIO.HIGH if state else GPIO.LOW)


def apply_status(status: str):
    log.info("Status: %s", status)
    if status == "TRACKED":
        set_color(0, 100, 0)      # GREEN
        set_infrared(True)
    elif status == "NOT_TRACKED":
        set_color(0, 0, 100)      # BLUE
        set_infrared(True)
    elif status == "CONNECTED":
        set_color(10, 50, 90)    # YELLOW
        set_infrared(True)
    elif status == "DISCONNECTED":
        set_color(100, 50, 0)     # ORANGE
        set_infrared(False)
    elif status == "UNEXPECTED_DISCONNECT":
        set_color(100, 0, 0)      # RED
        set_infrared(False)
    else:
        set_color(50, 0, 50)      # PURPLE (unknown status)
        set_infrared(False)


# -----------------------
# MQTT Callbacks
# -----------------------
def on_connect(client, userdata, flags, rc):
    if rc == 0:
        log.info("Connected to MQTT broker successfully.")
        client.subscribe(TOPIC)
        apply_status("CONNECTED")
    else:
        log.error("MQTT connection failed with code: %s", rc)


def on_message(client, userdata, msg):
    payload = msg.payload.decode().strip()
    log.info("MQTT Received: %s", payload)
    apply_status(payload)


def on_disconnect(client, userdata, rc):
    log.warning("Disconnected from MQTT broker.")
    apply_status("DISCONNECTED")


# -----------------------
# Main
# -----------------------
def cleanup(client):
    log.info("Shutting down...")
    try:
        client.loop_stop()
        client.disconnect()
    except Exception:
        pass
    red.stop()
    green.stop()
    blue.stop()
    GPIO.cleanup()


def main():
    client = mqtt.Client()
    client.on_connect = on_connect
    client.on_message = on_message
    client.on_disconnect = on_disconnect

    log.info("Attempting connection to MQTT broker at %s:%d...", BROKER, PORT)
    try:
        client.connect(BROKER, PORT, KEEP_ALIVE_TIME_SEC)
    except Exception as e:
        log.error("Could not connect to broker: %s", e)
        GPIO.cleanup()
        return

    client.loop_start()

    def handle_sigint(signum, frame):
        cleanup(client)
        sys.exit(0)

    signal.signal(signal.SIGINT, handle_sigint)
    signal.signal(signal.SIGTERM, handle_sigint)

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        pass
    finally:
        cleanup(client)


if __name__ == "__main__":
    main()