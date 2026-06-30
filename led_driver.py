#!/usr/bin/env python3

import rospy
from std_msgs.msg import String
import Jetson.GPIO as GPIO

# Config
RED_PIN = 11
GREEN_PIN = 13
BLUE_PIN = 15
INFRARED_PIN = 16

GPIO.setmode(GPIO.BOARD)

GPIO.setup(RED_PIN, GPIO.OUT)
GPIO.setup(GREEN_PIN, GPIO.OUT)
GPIO.setup(BLUE_PIN, GPIO.OUT)
GPIO.setup(INFRARED_PIN, GPIO.OUT)

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
    GPIO.output(INFRARED_PIN, GPIO.HIGH if state else GPIO.LOW)


# Callback
def on_status(msg):
    status = msg.data
    print("Status:", status)

    if status == "TRACKED":
        set_color(0, 100, 0)        # GREEN
        set_infrared(True)         # ON

    elif status == "NOT_TRACKED":
        set_color(0, 0, 100)        # BLUE
        set_infrared(True)         # ON

    elif status == "CONNECTED":
        set_color(100, 100, 0)     # YELLOW
        set_infrared(True)         # ON

    elif status == "DISCONNECTED":
        set_color(100, 50, 0)      # ORANGE
        set_infrared(False)        # OFF

    elif status == "UNEXPECTED_DISCONNECT":
        set_color(100, 0, 0)       # RED
        set_infrared(False)        # OFF

    else:
        set_color(50, 0, 50)       # PURPLE
        set_infrared(False)


# Main
def main():
    rospy.init_node("rgb_led_driver")

    rospy.Subscriber("/robot_status", String, on_status)

    print("RGB + IR LED driver running...")
    rospy.spin()


if __name__ == "__main__":
    main()