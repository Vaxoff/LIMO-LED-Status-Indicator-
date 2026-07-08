#!/usr/bin/env python3
import subprocess

SERIAL_PORT = "/dev/ttyACM0"

def main():
    print("Connected to ESP32. Type r/g/b/o (off), q to quit.")

    try:
        while True:
            choice = input("Color> ").strip().lower()
            
            if choice == "q":
                break
            elif choice in ("r", "g", "b", "o"):
                # This runs the exact same 'echo' command you typed in the terminal
                command = f'echo "{choice}" > {SERIAL_PORT}'
                try:
                    subprocess.run(command, shell=True, check=True)
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