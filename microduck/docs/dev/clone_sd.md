# Cloning the SD card

This produces the distributable `microduck.img.xz`. Do the **depersonalization** and **imaging** steps every time you cut a new image.

## Depersonalize before each clone

Right before imaging, remove everything personal/unique so each user gets a clean,
private robot. Power off the Pi, insert the SD into your PC, then (adjust the mount
paths if needed):

```bash
R=/media/$USER/rootfs

# SSH host keys — regenerated on first boot by regen-ssh-host-keys.service
sudo rm -f "$R"/etc/ssh/ssh_host_*

# machine-id — regenerated on first boot; ensures unique DHCP identity / IP per robot
sudo truncate -s 0 "$R/etc/machine-id"

# cloud-init instance state — clears the "already configured" flag so the user's
# network-config (Wi-Fi) is actually applied on their first boot. Without this,
# cloud-init treats the image as already set up and IGNORES network-config edits, so
# the robot never joins the user's network. (Equivalent to `cloud-init clean` on the Pi.)
sudo rm -rf "$R"/var/lib/cloud/instances/* "$R"/var/lib/cloud/instance \
            "$R"/var/lib/cloud/sem/* "$R"/var/lib/cloud/data/*

# netcfg watcher stamp — records the sha256 of the last-applied network-config
# (see setup_rasp.md, microduck-netcfg-reapply.service). If left behind, it still
# holds YOUR network's hash, so the first user's identical-looking config can be seen
# as "unchanged" and the Wi-Fi never gets re-applied. Always clear it here.
sudo rm -f "$R"/var/lib/microduck/netcfg.sha256

# Your Wi-Fi credentials (any NetworkManager connection you created).
sudo rm -f "$R"/etc/NetworkManager/system-connections/*.nmconnection

# Your SSH public key, shell history, caches and logs
sudo rm -f "$R/home/user/.ssh/authorized_keys"
sudo rm -f "$R/home/user/.bash_history"
sudo rm -f "$R"/var/cache/apt/archives/*.deb
sudo rm -rf "$R"/var/log/journal/* "$R"/var/log/*.log "$R"/var/log/*.gz
```

Reset the Wi-Fi config to placeholders so it does not ship with your network
credentials:
```bash
sudo tee /media/$USER/bootfs/network-config >/dev/null <<'EOF'
network:
  version: 2
  ethernets:
    eth0:
      dhcp4: true
      dhcp6: true
      optional: true
  wifis:
    wlan0:
      dhcp4: true
      regulatory-domain: "<YOUR_COUNTRY_CODE>"
      access-points:
        "<YOUR_WIFI_NAME>":
          password: "<YOUR_WIFI_PASSWORD>"
      optional: true
EOF
```

Also confirm the password is the documented default (`user` / `password`) and the
hostname is `microduck`, so the image matches [the deployment guide](../deployment.md).

## Create and shrink the image

Go to gnome disks and create an image of the SD card.

Then shrink and compress it. The `-Z` flag compresses the shrunk image with `xz`
(turning a ~4 GB raw image into a few hundred MB), and `-a` runs the compression in
parallel across all CPU cores — much faster than the default single-threaded `xz`:
```
wget https://raw.githubusercontent.com/Drewsif/PiShrink/master/pishrink.sh
chmod +x pishrink.sh
sudo ./pishrink.sh -aZ ~/Documents/microduck.img
```

This produces `~/Documents/microduck.img.xz`. Check the final size with:
```
ls -lh ~/Documents/microduck.img.xz
```
