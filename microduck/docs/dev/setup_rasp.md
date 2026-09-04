## Raspberry Pi setup

- Download the Raspberry Pi imager: https://www.raspberrypi.com/software/
- Plug your sd card in your computer
- Run it as sudo:

```
sudo Downloads/imager_[...].AppImage
```

- Select Raspberry Pi Zero 2 W
- Select Raspberry Pi OS (other)
- Select Raspberry Pi OS Lite (64-bit)
- Select your SD card
- Name it "microduck"
- Select your timezone
- Set a username and a password
- Set the SSID and password of your local network (2.4 GHz)
- Activate SSH with password authentification
- Write

Once it's done, eject the SD card and plug it in your robot. It should boot and connect to your wifi. The first time it boots, it will take a while to expand the filesystem and install updates, so be patient and don't switch it off.

## Connecting to the Pi from your computer

To connect to your Raspberry Pi from your computer, it needs to be on the same network. 
Once on the same network, you can find the IP address of your Raspberry Pi by running:
```
ping microduck.local
```

You should see a response looking like this:
```
64 bytes from 192.168.XXX.XXX: icmp_seq=1 ttl=64 time=100 ms
```

Then define a hostname for the Pi in your SSH config. To do this, add this entry to your `~/.ssh/config` file, with <USERNAME> being the username you set during the imager setup:
```
Host microduck
    HostName 192.168.XXX.XXX
    User <USERNAME>
```

Finally, you can connect to the Pi with
```
ssh microduck
```

In order not to have to enter the password everytime you connect to the Pi, you can copy your SSH key to the Pi. If you don't have an SSH key, you can generate one by running:
```
ssh-keygen -t ed25519
```

Then, copy your SSH key to the Pi with:
```
ssh-copy-id microduck
```

Now you can connect to the Pi without entering a password!

## Raspberry Pi configuration

Copy the configuration file to the Pi. From your computer, run:
```
scp docs/dev/config.txt microduck:config.txt
```

Then, on the Pi, move the configuration file to the correct location:
```
sudo mv config.txt /boot/firmware/config.txt
```

Reboot the Pi with `sudo reboot` for the changes to take effect.

After rebooting, connect to the Pi with `ssh microduck` and setup the raspi-config:
- run `sudo raspi-config`
    - go to Interface Options
        - go to I2C
            - enable I2C    
        - go to Serial Port
            - disable Serial Console
            - enable Serial Port

Then, to prevent ssh hangs when the Pi is idle, run:
```
sudo nmcli con mod <tab_to_find_your_wifi_connection> wifi.powersave disable
```

Finally desactivate automatic updates by running 
```
sudo touch /etc/apt/apt.conf.d/99disable-auto-upgrades
cat << 'EOF' | sudo tee /etc/apt/apt.conf.d/99disable-auto-upgrades > /dev/null
APT::Periodic::Update-Package-Lists "0";
APT::Periodic::Download-Upgradeable-Packages "0";
APT::Periodic::AutocleanInterval "0";
APT::Periodic::Unattended-Upgrade "0";
EOF
```

Reboot the Pi with `sudo reboot`.

Install uv, the Python package manager, on the Pi. First, set the date:
```
sudo date -s "2026-06-27 12:21:00"
```

Then, run:
```
curl -LsSf https://astral.sh/uv/install.sh | sh
```


## SSH host-key regeneration

A distributed image must not ship with fixed SSH host keys — otherwise every robot
flashed from it shares the same keys (a security risk, and SSH host-key conflicts when
two robots run on the same network). We remove the keys before imaging (see below) and
let each robot regenerate its own on first boot.

Raspberry Pi OS already ships `sshd-keygen.service`, but it only runs when
`ConditionFirstBoot=yes` (i.e. `/etc/machine-id` is empty). Add a more robust service,
triggered by the **absence of host keys**, so they always regenerate when missing.

On the Pi (`ssh microduck`):
```bash
sudo tee /etc/systemd/system/regen-ssh-host-keys.service >/dev/null <<'EOF'
[Unit]
Description=Regenerate SSH host keys if missing
Before=ssh.service ssh.socket sshd.service
ConditionPathExists=!/etc/ssh/ssh_host_ed25519_key

[Service]
Type=oneshot
RemainAfterExit=yes
ExecStart=/usr/bin/ssh-keygen -A

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl enable regen-ssh-host-keys.service
```

## Wi-Fi re-application on change

`network-config` is read by cloud-init **only on the first boot**. So once a robot has
booted, editing `network-config` to switch Wi-Fi networks has no effect unless cloud-init
is reset. This service detects a changed `network-config` at boot and re-applies it
automatically, so a user can switch networks fully offline — edit `network-config` on the
SD card, boot, done — with no SSH or prior network access.

On the Pi (`ssh microduck`):
```bash
sudo tee /usr/local/bin/microduck-netcfg-reapply >/dev/null <<'EOF'
#!/bin/bash
# Re-apply /boot/firmware/network-config when it changes, by resetting cloud-init.
set -u

CFG=/boot/firmware/network-config
STAMP=/var/lib/microduck/netcfg.sha256

[ -f "$CFG" ] || exit 0
mkdir -p "$(dirname "$STAMP")"

new=$(sha256sum "$CFG" | awk '{print $1}')
old=$(cat "$STAMP" 2>/dev/null || true)

if [ -z "$old" ]; then
    # First run: cloud-init already applied this config this boot. Just record it.
    echo "$new" > "$STAMP"
    exit 0
fi

if [ "$new" != "$old" ]; then
    # Config changed: record it, reset cloud-init, and reboot so cloud-init
    # re-applies the new network-config on the next boot.
    echo "$new" > "$STAMP"
    /usr/bin/cloud-init clean --logs
    /usr/sbin/reboot
fi
EOF
sudo chmod 755 /usr/local/bin/microduck-netcfg-reapply

sudo tee /etc/systemd/system/microduck-netcfg-reapply.service >/dev/null <<'EOF'
[Unit]
Description=Re-apply network-config (reset cloud-init) when it changes
After=cloud-final.service
ConditionPathExists=/boot/firmware/network-config

[Service]
Type=oneshot
ExecStart=/usr/local/bin/microduck-netcfg-reapply

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl enable microduck-netcfg-reapply.service
```

## Serial console off, motor UART on fix

The Dynamixel motors are driven over the UART (`/dev/ttyAMA0`, 1 Mbps). The serial
**login console** must be **disabled** on that UART, otherwise the kernel and a getty
spew bytes onto the bus and the motors return checksum errors / stop responding. The
UART **hardware** must stay **enabled**.

⚠️ Setting this with `raspi-config` is **not enough on its own**: this image is driven
by cloud-init, whose `user-data` contains `rpi.interfaces.serial`. If it is set to
`true`, cloud-init **re-enables the serial console** every time it runs as a new
instance — which happens on every `cloud-init clean`, including the one the
`microduck-netcfg-reapply` service triggers on a Wi-Fi change. So a raspi-config tweak
gets silently reverted and the motors break again.

Fix it at the source. Edit `/boot/firmware/user-data` and set the granular form
(console off, hardware on):
```yaml
rpi:
  interfaces:
    serial:
      console: false
      hardware: true
```
Validate the file, then apply it cleanly:
```bash
sudo cloud-init schema -c /boot/firmware/user-data   # must report "Valid schema"
sudo cloud-init clean && sudo reboot
```
After reboot, confirm `/proc/cmdline` no longer contains `console=ttyAMA0` and that the
motors answer (`rustypot_wizard` at 1 Mbps sees all 19 IDs). This config survives every
cloud-init re-run, so the motors stay reachable.

> If cloud-init rejects the granular form on your version, the fallback is to remove the
> `rpi.interfaces.serial` line entirely (cloud-init then leaves the serial alone) — the
> UART stays on via `enable_uart=1` in `config.txt`, and you disable the console once
> with `raspi-config` (Interface Options → Serial Port → login shell: No, hardware: Yes).

### Device permissions

Reading `/dev/input/js*` requires membership in the `input` group (otherwise you'd
need root):

```
sudo usermod -aG input $USER
```
