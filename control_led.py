#!/usr/bin/env python3
import Jetson.GPIO as GPIO
import time

RED_PIN = 37
GREEN_PIN = 35
BLUE_PIN = 33

duty_cycle_repeat = False

GPIO.setmode(GPIO.BOARD)
GPIO.setup(RED_PIN, GPIO.OUT)
GPIO.setup(GREEN_PIN, GPIO.OUT)
GPIO.setup(BLUE_PIN, GPIO.OUT)

COLORS = {
    "r": (1, 0, 0),
    "g": (0, 1, 0),
    "b": (0, 0, 1),
    "a": (1, 1, 1),
    "n": (0, 0, 0)
}


def set_color(r, g, b):
    GPIO.output(RED_PIN, GPIO.HIGH if r else GPIO.LOW)
    GPIO.output(GREEN_PIN, GPIO.HIGH if g else GPIO.LOW)
    GPIO.output(BLUE_PIN, GPIO.HIGH if b else GPIO.LOW)

def run_duty_cycle(pin, duty, cycles=500, freq=100):
    period = 1.0 / freq
    on_time = period * (duty / 100.0)
    off_time = period - on_time

    for _ in range(cycles):
        GPIO.output(pin, GPIO.HIGH)
        time.sleep(on_time)
        GPIO.output(pin, GPIO.LOW)
        time.sleep(off_time)


def main():
    print(__doc__)
    try:
        while True:
            choice = input("Color> ").strip().lower()
            if choice == "q":
                break
            elif choice == "d":
                pin_letter = input("  Pin (r/g/b)> ").strip().lower()
                pin_map = {"r": RED_PIN, "g": GREEN_PIN, "b": BLUE_PIN}
                if pin_letter not in pin_map:
                    print("  Unknown pin. Use r/g/b")
                    continue
                duty = float(input("  Duty cycle (0-100)> ").strip())
                run_duty_cycle(pin_map[pin_letter], duty)
            elif choice in COLORS:
                set_color(*COLORS[choice])
            else:
                print("Unknown option")

    except KeyboardInterrupt:
        pass
    finally:
        set_color(0, 0, 0)
        GPIO.cleanup()
        print("LED off.")


if __name__ == "__main__":
    main()