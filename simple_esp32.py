#!/usr/bin/env python3
"""
Simple LED color tester - talks to the ESP32 over USB serial.
Type r/g/b/o in the terminal and the NeoPixel changes color.

Install first:
    uv pip install pyserial
"""

import serial

SERIAL_PORT = "/dev/ttyACM0"   # check with: ls /dev/ttyACM* /dev/ttyUSB*
SERIAL_BAUD = 115200


def main():
    ser = serial.Serial(SERIAL_PORT, SERIAL_BAUD, timeout=1)
    print("Connected to ESP32. Type r/g/b/o (off), q to quit.")

    try:
        while True:
            choice = input("Color> ").strip().lower()
            if choice == "q":
                break
            elif choice in ("r", "g", "b", "o"):
                ser.write(choice.encode())
            else:
                print("Unknown option. Use r/g/b/o/q")
    finally:
        ser.close()
        print("Serial closed.")


if __name__ == "__main__":
    main()