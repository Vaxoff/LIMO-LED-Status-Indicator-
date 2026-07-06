#!/usr/bin/env python3

import rospy
import paho.mqtt.client as mqtt
from paho.mqtt.enums import CallbackAPIVersion
from std_msgs.msg import String

# -----------------------
# Config
# -----------------------
BROKER = "rasticvm.internal"
PORT = 1883
TOPIC = "limo/status"
KEEP_ALIVE_TIME_SEC = 60

connected_pub = None
tracked_pub = None
debug_pub = None


# -----------------------
# Helper
# -----------------------
def publish_ros_string(pub, text):
    if pub is not None:
        msg = String()
        msg.data = text
        pub.publish(msg)


# -----------------------
# MQTT Callbacks
# -----------------------
def on_connect(client, userdata, flags, rc, properties=None):
    if rc == 0:
        rospy.loginfo("Connected to MQTT broker successfully.")
        client.subscribe(TOPIC)
        publish_ros_string(connected_pub, "CONNECTED")
    else:
        rospy.logerr("MQTT connection failed with code: %s", rc)


def on_message(client, userdata, msg):
    payload = msg.payload.decode().strip()

    rospy.loginfo("MQTT Received: %s", payload)

    if payload == "CONNECTED":
        publish_ros_string(connected_pub, "CONNECTED")

    elif payload == "DISCONNECTED":
        publish_ros_string(connected_pub, "DISCONNECTED")

    elif payload == "UNEXPECTED_DISCONNECT":
        publish_ros_string(debug_pub, "UNEXPECTED_DISCONNECT")

    elif payload == "TRACKED":
        publish_ros_string(tracked_pub, "TRACKED")

    elif payload == "NOT_TRACKED":
        publish_ros_string(tracked_pub, "NOT_TRACKED")


def on_disconnect(client, userdata, disconnect_flags, rc, properties=None):
    rospy.logwarn("Disconnected from MQTT broker.")
    publish_ros_string(connected_pub, "DISCONNECTED")


# -----------------------
# Main
# -----------------------
def main():

    global connected_pub, tracked_pub, debug_pub

    rospy.init_node("mqtt_listener")

    connected_pub = rospy.Publisher(
        "/robot_connected",
        String,
        queue_size=1
    )

    tracked_pub = rospy.Publisher(
        "/robot_tracked",
        String,
        queue_size=1
    )

    debug_pub = rospy.Publisher(
        "/robot_debug",
        String,
        queue_size=1
    )

    client = mqtt.Client(callback_api_version=CallbackAPIVersion.VERSION2)

    client.on_connect = on_connect
    client.on_message = on_message
    client.on_disconnect = on_disconnect

    rospy.loginfo(
        "Attempting connection to MQTT broker at %s:%d...",
        BROKER,
        PORT,
    )

    try:
        client.connect(BROKER, PORT, KEEP_ALIVE_TIME_SEC)

    except Exception as e:
        rospy.logerr("Could not connect to broker: %s", e)
        return

    client.loop_start()

    try:
        rospy.spin()

    except KeyboardInterrupt:
        rospy.loginfo("Shutting down...")

    finally:
        client.loop_stop()
        client.disconnect()


if __name__ == "__main__":
    main()