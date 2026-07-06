#!/usr/bin/env python3

import rospy
from std_msgs.msg import String
import Jetson.GPIO as GPIO

# -----------------------
# GPIO Configuration
# -----------------------
RED_PIN = 40
GREEN_PIN = 38
BLUE_PIN = 36
INFRARED_STRIP_MOSFET_PIN = 32

GPIO.setmode(GPIO.BOARD)

GPIO.setup(RED_PIN, GPIO.OUT)
GPIO.setup(GREEN_PIN, GPIO.OUT)
GPIO.setup(BLUE_PIN, GPIO.OUT)
# GPIO.setup(INFRARED_STRIP_MOSFET_PIN, GPIO.OUT)

# PWM at 100 Hz
red = GPIO.PWM(RED_PIN, 100)
green = GPIO.PWM(GREEN_PIN, 100)
blue = GPIO.PWM(BLUE_PIN, 100)

red.start(0)
green.start(0)
blue.start(0)


# -----------------------
# Helper Functions
# -----------------------
def set_color(r, g, b):
    red.ChangeDutyCycle(r)
    green.ChangeDutyCycle(g)
    blue.ChangeDutyCycle(b)


def set_infrared(state):
    GPIO.output(
        INFRARED_STRIP_MOSFET_PIN,
        GPIO.HIGH if state else GPIO.LOW
    )


# -----------------------
# ROS Node
# -----------------------
class RgbLedDriver:

    def __init__(self):
        rospy.init_node("rgb_led_driver")

        rospy.Subscriber(
            "/robot_status",
            String,
            self.on_status,
            queue_size=10
        )

        rospy.loginfo("RGB + IR LED driver running...")

    def on_status(self, msg):
        status = msg.data
        rospy.loginfo("Status: %s", status)

        """
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
            set_color(50, 0, 50)      # PURPLE
            set_infrared(False)
        """

        set_color(30, 60, 90)


# -----------------------
# Main
# -----------------------
def main():
    driver = RgbLedDriver()

    try:
        rospy.spin()

    except KeyboardInterrupt:
        rospy.loginfo("Shutting down node...")

    finally:
        red.stop()
        green.stop()
        blue.stop()
        GPIO.cleanup()


if __name__ == "__main__":
    main()