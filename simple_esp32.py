#!/usr/bin/env python3
import serial
import time

SERIAL_PORT = "/dev/ttyACM0"  
SERIAL_BAUD = 115200

def main():
    try:
        ser = serial.Serial(SERIAL_PORT, SERIAL_BAUD, timeout=1)
        ser.dtr = False
        ser.rts = False
        time.sleep(3)
        print("Connected to ESP32. Type r/g/b/o (off), q to quit.")
    except Exception as e:
        print(f"Failed to open {SERIAL_PORT}. Error: {e}")
        return

    try:
        while True:
            choice = input("Color> ").strip().lower()
            
            if choice == "q":
                break
            elif choice in ("r", "g", "b", "o"):
                # Send just the single letter, no \n needed anymore!
                ser.write(choice.encode("ascii"))
                ser.flush()
                print(f"Sent: {choice}")
            else:
                print("Unknown option. Use r/g/b/o/q")
    finally:
        ser.close()
        print("Serial closed.")

if __name__ == "__main__":
    main()