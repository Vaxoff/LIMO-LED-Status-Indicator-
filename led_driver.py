#!/usr/bin/env python3
import rclpy
from rclpy.node import Node
from std_msgs.msg import String
import Jetson.GPIO as GPIO

# Config
RED_PIN = 40
GREEN_PIN = 38
BLUE_PIN = 36
INFRARED_STRIP_MOSFET_PIN = 32

GPIO.setmode(GPIO.BOARD)
GPIO.setup(RED_PIN, GPIO.OUT)
GPIO.setup(GREEN_PIN, GPIO.OUT)
GPIO.setup(BLUE_PIN, GPIO.OUT)
#GPIO.setup(INFRARED_STRIP_MOSFET_PIN, GPIO.OUT)

# PWM (correct frequency ~100Hz)
red = GPIO.PWM(RED_PIN, 100)
green = GPIO.PWM(GREEN_PIN, 100)
blue = GPIO.PWM(BLUE_PIN, 100)
red.start(0)
green.start(0)
blue.start(0)


# Helper functions
def set_color(r, g, b):
    red.ChangeDutyCycle(r)
    green.ChangeDutyCycle(g)
    blue.ChangeDutyCycle(b)


def set_infrared(state: bool):
    GPIO.output(INFRARED_STRIP_MOSFET_PIN, GPIO.HIGH if state else GPIO.LOW)


class RgbLedDriver(Node):
    def __init__(self):
        super().__init__("rgb_led_driver")
        self.subscription = self.create_subscription(
            String, "/robot_status", self.on_status, 10
        )
        self.get_logger().info("RGB + IR LED driver running...")

    def on_status(self, msg: String):
        status = msg.data
        self.get_logger().info(f"Status: {status}")

        """
        if status == "TRACKED":
            set_color(0, 100, 0)     # GREEN
            set_infrared(True)       # ON
        elif status == "NOT_TRACKED":
            set_color(0, 0, 100)     # BLUE
            set_infrared(True)       # ON
        elif status == "CONNECTED":
            set_color(100, 100, 0)   # YELLOW
            set_infrared(True)       # ON
        elif status == "DISCONNECTED":
            set_color(100, 50, 0)    # ORANGE
            set_infrared(False)      # OFF
        elif status == "UNEXPECTED_DISCONNECT":
            set_color(100, 0, 0)     # RED
            set_infrared(False)      # OFF
        else:
            set_color(50, 0, 50)     # PURPLE
            set_infrared(False)
        """
        set_color(30,60,90)

def main():
    rclpy.init()
    node = RgbLedDriver()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        node.get_logger().info("Shutting down node via keyboard interrupt...")
    finally:
        red.stop()
        green.stop()
        blue.stop()
        GPIO.cleanup()
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()