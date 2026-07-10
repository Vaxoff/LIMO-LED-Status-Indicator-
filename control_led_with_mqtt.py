#!/usr/bin/env python3
"""
MQTT-to-Serial Bridge for ESP32 RGB Control.
Listens for status strings via MQTT, translates them to full color words, 
and writes them to the serial port.
"""

import os
import signal
import paho.mqtt.client as mqtt

SERIAL_PORT = "/dev/ttyACM0" #limo port:/dev/ttyACM0 my computer port: COM7
BROKER_HOST = "rasticvm.internal"
BROKER_PORT = 1883
TOPIC = "led/status"

# Scalable dictionary: "STATUS": ("serial_word", "Color Name for Log")
# Sends the full word + a newline (\n) so the ESP32 can read it easily.
STATUS_MAP = {
    "TRACKING":      ("green\n",    "Green"),
    "NOT TRACKING":  ("magenta\n",  "Magenta"),
    "IDLE":          ("blue\n",     "Blue"),
    "ERROR":         ("red\n",      "Red"),
    "OFF":           ("off\n",      "Off")
}

# Global variables for easy access in callbacks
ser = None
client = None


def on_connect(client, userdata, flags, rc, properties=None):
    if rc == 0:
        print(f"Connected to MQTT broker. Subscribing to '{TOPIC}'...", flush=True)
        client.subscribe(TOPIC, qos=1)
    else:
        print(f"Failed to connect to MQTT broker. Return code: {rc}", flush=True)


def on_message(client, userdata, msg):
    global ser
    try:
        # Decode payload and clean it up (case-insensitive)
        payload_str = msg.payload.decode('utf-8').strip().upper()
        
        if payload_str in STATUS_MAP:
            serial_word, color_name = STATUS_MAP[payload_str]
            
            if ser:
                # Write the full word to the serial port
                ser.write(serial_word.encode('ascii'))
                print(f"Received '{payload_str}' -> Sending '{color_name}' to {SERIAL_PORT}", flush=True)
            else:
                print(f"[ERROR] Serial port not open. Cannot send '{color_name}'", flush=True)
        else:
            print(f"[WARN] Received unknown status '{payload_str}'. Ignored.", flush=True)
            
    except Exception as e:
        print(f"[ERROR] Failed to process MQTT message: {e}", flush=True)


def setup_serial():
    global ser
    print(f"Configuring serial port {SERIAL_PORT}...", flush=True)
    
    # Configure the port to prevent hangups (from your original script)
    os.system(f"stty -F {SERIAL_PORT} 115200 cs8 -cstopb -parenb raw -echo -crtscts -hupcl")
    
    try:
        # Open the port ONE time in binary write mode, no buffering
        ser = open(SERIAL_PORT, 'wb', buffering=0)
        print(f"Serial port {SERIAL_PORT} opened successfully.", flush=True)
    except Exception as e:
        print(f"Failed to open {SERIAL_PORT}. Error: {e}", flush=True)
        ser = None


def shutdown(signum, frame):
    """Graceful shutdown on SIGINT (Ctrl+C) or SIGTERM (systemd stop)."""
    global ser, client
    print("\nShutting down...", flush=True)
    
    if client:
        client.loop_stop()
        client.disconnect()
        
    if ser:
        ser.close()
        print(f"Closed {SERIAL_PORT}.", flush=True)
        
    exit(0)


def main():
    global client
    
    # Register signal handlers for graceful shutdown
    signal.signal(signal.SIGINT, shutdown)
    signal.signal(signal.SIGTERM, shutdown)

    # 1. Setup Serial Port
    setup_serial()
    if not ser:
        print("Cannot continue without serial port. Exiting.", flush=True)
        return

    # 2. Setup MQTT Client
    client = mqtt.Client(client_id="led_serial_bridge", protocol=mqtt.MQTTv311)
    client.on_connect = on_connect
    client.on_message = on_message

    print(f"Connecting to MQTT broker at {BROKER_HOST}:{BROKER_PORT} ...", flush=True)
    try:
        client.connect(BROKER_HOST, BROKER_PORT, keepalive=60)
    except Exception as e:
        print(f"Failed to connect to broker: {e}", flush=True)
        ser.close()
        return

    # 3. Run forever, listening for MQTT messages
    print("Bridge is running. Waiting for messages...", flush=True)
    client.loop_forever(retry_first_connection=True)


if __name__ == "__main__":
    main()