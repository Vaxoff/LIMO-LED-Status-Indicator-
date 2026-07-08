#!/usr/bin/env python3
import os
import time

SERIAL_PORT = "/dev/ttyACM0"

def main():
    # Configure the port to prevent hangups
    os.system(f"stty -F {SERIAL_PORT} 115200 cs8 -cstopb -parenb raw -echo -crtscts -hupcl")
    
    print("Opening port...")
    try:
        # Open the port ONE time in binary write mode, no buffering
        ser = open(SERIAL_PORT, 'wb', buffering=0)
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
                    # Write the byte directly to the open file
                    ser.write(choice.encode('ascii'))
                    print(f"Sent: {choice}")
                except Exception as e:
                    print(f"Error sending: {e}")
            else:
                print("Unknown option. Use r/g/b/o/q")
    except KeyboardInterrupt:
        pass
    finally:
        ser.close()
        print("\nClosed.")

if __name__ == "__main__":
    main()