#!/usr/bin/env python3
import rclpy
from rclpy.node import Node
import paho.mqtt.client as mqtt
from paho.mqtt.enums import CallbackAPIVersion
from std_msgs.msg import String

# Config
BROKER = "rasticvm.internal"  # Ensure your robot's IP matches this!
PORT = 1883
TOPIC = "limo/status"
KEEP_ALIVE_TIME_SEC = 60

# ROS publishers (global so callbacks can access)
connected_pub = None
tracked_pub = None
debug_pub = None
node = None  # Global node reference for logging


# Helper function to easily publish ROS 2 strings
def publish_ros_string(publisher, text_data):
    if publisher is not None:
        msg = String()
        msg.data = text_data
        publisher.publish(msg)


# Callbacks updated for Paho MQTT v2 API
def on_connect(client, userdata, flags, rc, properties=None):
    # In Paho v2, rc is an integer or a ReasonCode object. Checking if it equals 0 or Success works.
    if rc == 0:
        if node:
            node.get_logger().info("Connected to MQTT broker successfully.")
        else:
            print("Connected to MQTT broker successfully.")
        client.subscribe(TOPIC)
        publish_ros_string(connected_pub, "CONNECTED")
    else:
        if node:
            node.get_logger().error(f"MQTT Connection failed with code: {rc}")
        else:
            print(f"MQTT Connection failed with code: {rc}")


def on_message(client, userdata, msg):
    payload = msg.payload.decode().strip()
    if node:
        node.get_logger().info(f"MQTT Received: {payload}")
    else:
        print("MQTT Received:", payload)

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
    if node:
        node.get_logger().warn("Disconnected from MQTT broker.")
    else:
        print("Disconnected from MQTT broker.")
    publish_ros_string(connected_pub, "DISCONNECTED")


# Main Execution Loop
def main():
    global connected_pub, tracked_pub, debug_pub, node
    rclpy.init()
    node = rclpy.create_node("mqtt_listener")

    # Correct ROS 2 publisher initialization
    connected_pub = node.create_publisher(String, "/robot_connected", 1)
    tracked_pub = node.create_publisher(String, "/robot_tracked", 1)
    debug_pub = node.create_publisher(String, "/robot_debug", 1)

    # Initialize client explicitly using the modern API version required by modern pip packages
    client = mqtt.Client(callback_api_version=CallbackAPIVersion.VERSION2)
    client.on_connect = on_connect
    client.on_message = on_message
    client.on_disconnect = on_disconnect

    node.get_logger().info(f"Attempting connection to MQTT broker at {BROKER}:{PORT}...")

    try:
        client.connect(BROKER, PORT, KEEP_ALIVE_TIME_SEC)
    except Exception as e:
        node.get_logger().error(f"Could not connect to broker: {e}. Check if the broker is active and reachable.")
        node.destroy_node()
        rclpy.shutdown()
        return

    # Start the background MQTT thread loop
    client.loop_start()

    # Spin the ROS 2 node inside a try/except block to handle clean shutdowns
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        node.get_logger().info("Shutting down node via keyboard interrupt...")
    finally:
        # Cleanup threads and resources
        client.loop_stop()
        client.disconnect()
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()