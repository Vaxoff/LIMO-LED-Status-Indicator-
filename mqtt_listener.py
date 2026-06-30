#!/usr/bin/env python3

import rospy
import paho.mqtt.client as mqtt
from std_msgs.msg import String

# Config
BROKER = "192.168.1.100"
PORT = 1883
TOPIC = "limo/status"
KEEP_ALIVE_TIME_SEC = 60


# ROS publishers (global so callbacks can access)
connected_pub = None
tracked_pub = None
debug_pub = None


# Callbacks
def on_connect(client, userdata, flags, rc):
    if rc == 0:
        print("Connected to MQTT broker")
        client.subscribe(TOPIC)

        connected_pub.publish("CONNECTED")
    else:
        print(f"Connection failed: {rc}")


def on_message(client, userdata, msg):
    payload = msg.payload.decode().strip()
    print("MQTT:", payload)

    if payload == "CONNECTED":
        connected_pub.publish("CONNECTED")

    elif payload == "DISCONNECTED":
        connected_pub.publish("DISCONNECTED")

    elif payload == "UNEXPECTED_DISCONNECT":
        debug_pub.publish("UNEXPECTED_DISCONNECT")

    elif payload == "TRACKED":
        tracked_pub.publish("TRACKED")

    elif payload == "NOT_TRACKED":
        tracked_pub.publish("NOT_TRACKED")


def on_disconnect(client, userdata, rc):
    print("Disconnected from broker")
    connected_pub.publish("DISCONNECTED")


# Main
def main():
    global connected_pub, tracked_pub, debug_pub

    rospy.init_node("mqtt_listener")

    connected_pub = rospy.Publisher("/robot_connected", String, queue_size=1)
    tracked_pub   = rospy.Publisher("/robot_tracked", String, queue_size=1)
    debug_pub     = rospy.Publisher("/robot_debug", String, queue_size=1)

    client = mqtt.Client()

    client.on_connect = on_connect
    client.on_message = on_message
    client.on_disconnect = on_disconnect

    client.connect(BROKER, PORT, KEEP_ALIVE_TIME_SEC)

    # IMPORTANT: non-blocking loop
    client.loop_start()

    rospy.spin()


if __name__ == "__main__":
    main()