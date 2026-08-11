#!/usr/bin/env python3
"""
Debug version - uses pyserial and prints back whatever the ESP32 sends,
so we can confirm bytes are actually making it to the board.

Install first:
    uv pip install pyserial
"""

import time

import serial

SERIAL_PORT = "/dev/ttyACM0"   # check with: ls /dev/ttyACM* /dev/ttyUSB*
SERIAL_BAUD = 115200


def main():
    ser = serial.Serial(
        SERIAL_PORT,
        SERIAL_BAUD,
        timeout=1,
        dsrdtr=False,
        rtscts=False,
    )
    time.sleep(2)  # give the board a moment after opening the port
    ser.reset_input_buffer()

    print("Connected to ESP32. Type r/g/b/o (off), q to quit.")

    try:
        while True:
            choice = input("Color> ").strip().lower()
            if choice == "q":
                break
            elif choice in ("r", "g", "b", "o"):
                ser.write(choice.encode("ascii"))
                time.sleep(0.2)  # give the board time to respond
                response = ser.read(ser.in_waiting or 1)
                print("ESP32 said:", response)
            else:
                print("Unknown option. Use r/g/b/o/q")
    finally:
        ser.close()
        print("\nClosed.")


if __name__ == "__main__":
    main()