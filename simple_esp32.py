#!/usr/bin/env python3
"""
Simple LED color tester - runs on the Jetson Nano.
Talks to the ESP32 over USB serial.
Type r/g/b/o in the terminal and the NeoPixel changes color.

Install first:
    pip install pyserial
"""

import serial

# On the Jetson Nano, the ESP32 will likely show up here.
# If it doesn't work, run: ls /dev/ttyACM* /dev/ttyUSB*
# and change this to match what you see.
SERIAL_PORT = "/dev/ttyACM0"  
SERIAL_BAUD = 115200

def main():
    try:
        ser = serial.Serial(SERIAL_PORT, SERIAL_BAUD, timeout=1)
        print("Connected to ESP32. Type r/g/b/o (off), q to quit.")
    except Exception as e:
        print(f"Failed to open {SERIAL_PORT}. Error: {e}")
        print("Did you check the port path? (ls /dev/ttyUSB*)")
        return

    try:
        while True:
            choice = input("Color> ").strip().lower()
            
            if choice == "q":
                break
            elif choice in ("r", "g", "b", "o"):
                # We add '\n' because the ESP32 C++ code uses readStringUntil('\n')
                ser.write((choice + "\n").encode("ascii"))
            else:
                print("Unknown option. Use r/g/b/o/q")
    finally:
        ser.close()
        print("Serial closed.")

if __name__ == "__main__":
    main()