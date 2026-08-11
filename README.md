# LIMO-LED-Status-Indicator-
Turns LED on when connected to wifi
ssh agilex@limoXXX

git clone repo

cd LIMO-LED-Status-Indicator-

sudo cp limo-id-sender.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable limo-id-sender
sudo systemctl start limo-id-sender

journalctl -u limo-id-sender -f
^ checks logs