#!/usr/bin/env python3
import os
import time

SERIAL_PORT = "/dev/ttyACM0"

def main():
    try:
        # Open the port ONE time using low-level OS commands.
        # O_RDWR = Read/Write, O_NOCTTY = No controlling terminal, O_NDELAY = Don't wait
        fd = os.open(SERIAL_PORT, os.O_RDWR | os.O_NOCTTY | os.O_NDELAY)
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
                    # Write directly to the open file descriptor
                    os.write(fd, (choice + "\n").encode("ascii"))
                    print(f"Sent: {choice}")
                except Exception as e:
                    print(f"Error sending: {e}")
            else:
                print("Unknown option. Use r/g/b/o/q")
    except KeyboardInterrupt:
        pass
    finally:
        # Only close the port when the user quits
        os.close(fd)
        print("\nClosed.")

if __name__ == "__main__":
    main()