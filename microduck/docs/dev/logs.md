# Logging

To activate logging, run:
```
sudo sed -i 's/Storage=volatile/Storage=persistent/' /usr/lib/systemd/journald.conf.d/40-rpi-volatile-storage.conf && sudo systemctl restart systemd-journald
```

Then, you can view the logs with `journalctl`. To view the last boot logs, run:
```
journalctl -b -1 -k
```

Once you have identified your problem, you should deactivate logging to save the SD card from unnecessary writes: 
```
sudo sed -i 's/Storage=persistent/Storage=volatile/' /usr/lib/systemd/journald.conf.d/40-rpi-volatile-storage.conf && sudo systemctl restart systemd-journald
```