# LIMO LED Status Indicator

A lightweight systemd service that lights up an ESP32C6 LED connected to your LIMO robot whenever it's connected to the rastic MQTT

## How It Works

`limo-id-sender.service` runs in the background on the LIMO's onboard computer. It monitors the Wi-Fi connection and sends a signal over serial (USB) to ESP32C6, which drives the LED, on when connected, off when not.

## Prerequisites

- A LIMO robot running Ubuntu with `systemd`
- An esp32C6 connected to ardiuno
- SSH access to the robot
- `git` installed on the robot

## Installation

### 1. Connect to the LIMO

```bash
ssh agilex@limoXXX
```

Replace `XXX` with LIMO number
### 2. Clone this repository

```bash
git clone https://github.com/Vaxoff/LIMO-LED-Status-Indicator.git
cd LIMO-LED-Status-Indicator
```

### 3. Install the systemd service

```bash
sudo cp limo-id-sender.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable limo-id-sender
sudo systemctl start limo-id-sender
```

This copies the service file into place, registers it with systemd, and enables it to start automatically on boot.

### 4. Grant serial port access

The service needs permission to write to the USB serial device, which requires your user to be in the `dialout` group.

```bash
sudo usermod -aG dialout $USER
sudo reboot
```

A reboot is required — group membership changes don't take effect in your current session.

## Verifying the Setup

After rebooting, confirm everything is configured correctly:

**1. Check that you're in the `dialout` group:**

```bash
groups
```

You should see `dialout` in the output. If it's missing, you're still in the old session — reboot again.

**2. Check the serial device permissions:**

```bash
ls -l /dev/ttyACM0
```

Expected output looks like:

```
crw-rw-rw- 1 root dialout 166, 0 ... /dev/ttyACM0
```

The `dialout` group should own the device, confirming your user has access.

**3. Check the service is running and view live logs:**

```bash
journalctl -u limo-id-sender -f
```

This tails the service's logs in real time — useful for confirming it detects Wi-Fi changes and sends data correctly. Press `Ctrl+C` to exit.

### 5. Setup ESP32

After connecting to the ESP32 click on tools and enable `USB CDC On Boot`

Copy code from `ESP32C6-code.ino` into the esp32 than upload the 
    
## LED Status Reference
 
| Color | State | Meaning |
|---|---|---|
| ⚪ White | Waiting for ID | Board has booted but hasn't received its `LIMO_ID` from the host yet. Normal for a few seconds after plugging in. |
| 🔴 Red | Error | Either connecting to WiFi, or connected but failed to reach the MQTT broker. |
| 🔵 Blue | Idle | Connected to WiFi + MQTT, has an ID, but hasn't seen any tracking messages yet. |
| 🟣 Magenta | Not Tracked | MQTT messages are coming through, but none referencing this robot's ID in the last 10 seconds. |
| 🟢 Green | Tracked | Messages referencing this robot's ID have been seen in the last 10 seconds — it's actively being tracked. |



## Troubleshooting

| Symptom | Likely Cause | Fix |
|---|---|---|
| LED never lights up | Service not running | `sudo systemctl status limo-id-sender` |
| `Permission denied` on `/dev/ttyACM0` | User not in `dialout` group yet | Re-run step 4, then reboot |
| No `/dev/ttyACM0` device | Microcontroller not connected or wrong port | Check USB cable/port; try `ls /dev/tty*` to find the correct device name |
| Service fails on boot | Errors in service file or missing dependencies | Check `journalctl -u limo-id-sender -b` |

## Useful Commands

```bash
sudo systemctl status limo-id-sender     # Check current service status
sudo systemctl restart limo-id-sender    # Restart the service
sudo systemctl stop limo-id-sender       # Stop the service
sudo systemctl disable limo-id-sender    # Disable auto-start on boot
```

## Uninstalling

```bash
sudo systemctl stop limo-id-sender
sudo systemctl disable limo-id-sender
sudo rm /etc/systemd/system/limo-id-sender.service
sudo systemctl daemon-reload
```


--------------------------------------------------------------------------------------------------------------
# not fancy shmancy readme

Turns LED on when connected to wifi
```bash
ssh agilex@limoXXX

git clone repo

cd LIMO-LED-Status-Indicator-

sudo cp limo-id-sender.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable limo-id-sender
sudo systemctl start limo-id-sender
```
this fixes ACM port issue
``` bash
sudo usermod -aG dialout $USER
sudo reboot
groups
```
^ You should see dialout listed. If it's not there, you're still in the old session reboot again
```bash
ls -l /dev/ttyACM0
```
when you run this ^ you should see something like:
```bash
crw-rw-rw- 1 root dialout 166, 0 ... /dev/ttyACM0
```
this command checks logs
```bash
journalctl -u limo-id-sender -f
```

enable USB CDC On Boot and then copy esp32 code onto esp, the file is called:
```bash
ESP32C6-code.ino
```

LED color refrence:
Yellow: Waiting for LIMO id
Red: Error
Blue: Idle
Magenta: Not tracked
Green: Tracked
