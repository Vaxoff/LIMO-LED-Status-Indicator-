#!/usr/bin/env python3
import Jetson.GPIO as GPIO

RED_PIN = 37
GREEN_PIN = 35
BLUE_PIN = 33

GPIO.setmode(GPIO.BOARD)
GPIO.setup(RED_PIN, GPIO.OUT)
GPIO.setup(GREEN_PIN, GPIO.OUT)
GPIO.setup(BLUE_PIN, GPIO.OUT)

COLORS = {
    "r": (1, 0, 0),
    "g": (0, 1, 0),
    "b": (0, 0, 1),
    "a": (1, 1, 1)
}


def set_color(r, g, b):
    GPIO.output(RED_PIN, GPIO.HIGH if r else GPIO.LOW)
    GPIO.output(GREEN_PIN, GPIO.HIGH if g else GPIO.LOW)
    GPIO.output(BLUE_PIN, GPIO.HIGH if b else GPIO.LOW)


def main():
    print(__doc__)
    try:
        while True:
            choice = input("Color> ").strip().lower()
            if choice == "q":
                break
            elif choice in COLORS:
                set_color(*COLORS[choice])
            else:
                print("Pick a dif color")
    except KeyboardInterrupt:
        pass
    finally:
        set_color(0, 0, 0)
        GPIO.cleanup()
        print("\nLED off, GPIO cleaned up.")


if __name__ == "__main__":
    main()