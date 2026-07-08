#!/usr/bin/env python3
import time

SERIAL_PORT = "/dev/ttyACM0"

def main():
    print("Connected to ESP32. Type r/g/b/o (off), q to quit.")

    try:
        while True:
            choice = input("Color> ").strip().lower()
            
            if choice == "q":
                break
            elif choice in ("r", "g", "b", "o"):
                # Open the port as a standard file and write to it, 
                # exactly like the 'echo' command does!
                try:
                    with open(SERIAL_PORT, 'w') as f:
                        f.write(choice + "\n")
                        f.flush()
                    print(f"Sent: {choice}")
                except Exception as e:
                    print(f"Error sending: {e}")
            else:
                print("Unknown option. Use r/g/b/o/q")
    except KeyboardInterrupt:
        pass
    finally:
        print("\nClosed.")

if __name__ == "__main__":
    main()