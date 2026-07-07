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
import time

import Jetson.GPIO as GPIO
import paho.mqtt.client as mqtt
from paho.mqtt.enums import CallbackAPIVersion

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
RED_PIN = 40
GREEN_PIN = 38
BLUE_PIN = 36
INFRARED_STRIP_MOSFET_PIN = 32

PWM_FREQ_HZ = 100

GPIO.setmode(GPIO.BOARD)
GPIO.setup(RED_PIN, GPIO.OUT)
GPIO.setup(GREEN_PIN, GPIO.OUT)
GPIO.setup(BLUE_PIN, GPIO.OUT)
GPIO.setup(INFRARED_STRIP_MOSFET_PIN, GPIO.OUT)

red = GPIO.PWM(RED_PIN, PWM_FREQ_HZ)
green = GPIO.PWM(GREEN_PIN, PWM_FREQ_HZ)
blue = GPIO.PWM(BLUE_PIN, PWM_FREQ_HZ)
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
        set_color(100, 100, 0)    # YELLOW
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
def on_connect(client, userdata, flags, rc, properties=None):
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


def on_disconnect(client, userdata, disconnect_flags, rc, properties=None):
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
    client = mqtt.Client(callback_api_version=CallbackAPIVersion.VERSION2)
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