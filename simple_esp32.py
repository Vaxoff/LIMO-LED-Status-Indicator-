#!/usr/bin/env python3
import serial
import time

SERIAL_PORT = "/dev/ttyACM0"  
SERIAL_BAUD = 115200

def main():
    try:
        # Added rtscts=False and dsrdtr=False to prevent flow control hangs
        # Added write_timeout=2 so it never freezes forever
        ser = serial.Serial(
            SERIAL_PORT, 
            SERIAL_BAUD, 
            timeout=1,
            rtscts=False,
            dsrdtr=False,
            write_timeout=2
        )
        # Give the ESP32 3 seconds to finish booting up after the reset
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
                try:
                    ser.write((choice + "\n").encode("ascii"))
                    print(f"Sent: {choice}")
                except serial.SerialTimeoutException:
                    print("ESP32 didn't respond in time. Try again.")
            else:
                print("Unknown option. Use r/g/b/o/q")
    finally:
        ser.close()
        print("Serial closed.")

if __name__ == "__main__":
    main()