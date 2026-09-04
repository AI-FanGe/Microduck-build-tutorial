# Software Installation & Deployment

This guide takes you from the pre-built Microduck SD-card image to a robot you can drive
from your computer. The image already contains the operating system and the Microduck
code; you will flash it, connect to the robot over the network, and run it. For
day-to-day operation and development afterwards, see the [Usage Guide](usage.md).

## Step 1: Download and Flash the Image

Download `microduck.img.xz` from the
[latest image release](https://github.com/MarcDcls/microduck/releases/tag/image.v2)
([direct link](https://github.com/MarcDcls/microduck/releases/download/image.v2/microduck.img.xz)).
There is no need to decompress it; Raspberry Pi Imager reads the compressed `.xz`
directly.

Then use [Raspberry Pi Imager](https://www.raspberrypi.com/software/) to write
`microduck.img.xz` onto a micro-SD card. The card should be 16 GB or larger, and I
advise using a new card, as corrupted cards can cause issues.

1. Insert the micro-SD card into your computer.
2. Open Raspberry Pi Imager. It is distributed as an AppImage, so make it executable
   and run it as root to let it write to the SD card:
   ```bash
   chmod +x Downloads/imager_*.AppImage
   sudo Downloads/imager_*.AppImage
   ```
3. **Choose Device** → *Raspberry Pi Zero 2 W*.
4. **Choose OS** → scroll to the bottom and select *Use custom*, then pick the
   `microduck.img.xz` file.
5. **Choose Storage** → select your micro-SD card.
6. Click **Next**. When asked *"Would you like to apply OS customisation settings?"*,
   choose **No** — the image is already configured (the Wi-Fi is set up in Step 2).
7. Click **Write** and wait for the flashing and verification to complete.

> Alternatively, on Linux you can flash from the command line. **Double-check the
> device name** (`lsblk`) — writing to the wrong disk will erase it:
> ```bash
> xzcat microduck.img.xz | sudo dd of=/dev/sdX bs=4M status=progress conv=fsync
> ```

## Step 2: Headless Wi-Fi Configuration

Once the flashing process is complete, unplug and plug back the micro-SD card into your Ubuntu PC.

Open your terminal and open the network configuration file using nano:

```bash
sudo nano /media/$USER/bootfs/network-config
```

You should see a YAML file with the following content:

```yaml
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
```

⚠️ CRITICAL: DO NOT modify the YAML format. It is strictly space-sensitive and should not be changed. 

📶 CRITICAL: the network **must be 2.4 GHz**. The Raspberry Pi Zero 2 W has a 2.4 GHz-only
Wi-Fi chip and **cannot see or join a 5 GHz network** — it will silently never connect. If
you use a phone hotspot, force it to 2.4 GHz.

🛜 Replace <YOUR_WIFI_NAME> and <YOUR_WIFI_PASSWORD> with your local network credentials. In addition, you can set other networks, such as your phone hotspot to use your robot everywhere. To do so, add an entry to the access-points section:

```yaml
      access-points:
        "<YOUR_WIFI_NAME>":
          password: "<YOUR_WIFI_PASSWORD>"
        "<YOUR_SECOND_WIFI_NAME>":
          password: "<YOUR_SECOND_WIFI_PASSWORD>"
```

🌍 Don't forget to replace <YOUR_COUNTRY_CODE> with your local two-letter country code (ISO 3166-1 alpha-2). For example, use "US" for the United States, "GB" for the United Kingdom, "FR" for France, "DE" for Germany, etc. This ensures the Raspberry Pi uses the correct Wi-Fi channels allowed in your country.

Save and exit (Ctrl + O, then Enter, then Ctrl + X).

Safely eject the card from your Ubuntu PC, insert it into the Raspberry Pi Zero 2W, and power it up.

> **Changing the Wi-Fi networks later:** just edit `network-config` again — on the Pi,
> or offline with the SD card in your PC — and reboot. The robot detects the change at
> boot and re-applies it automatically (it resets cloud-init and reboots once). 

## Step 3: First SSH Connection

Give the Raspberry Pi about 1 to 2 minutes on its very first boot. It will automatically resize the file system to use the full capacity of your SD card and then connect to your Wi-Fi network. Do not power it off during this process, as it may take a while and interrupting it could cause issues.

When the Pi is ready, you should be able to ping it from your computer using the command:

```bash
ping microduck.local
```

You should see a response looking like this:
```
PING microduck.local (192.168.XXX.XX) 56(84) bytes of data.
64 bytes from 192.168.XXX.XXX: icmp_seq=1 ttl=64 time=100 ms
...
```

The default credentials of this image are:
- Username: `user`
- Password: `password`

Open your terminal and connect over SSH:

```bash
ssh user@microduck.local
```

> If `microduck.local` cannot be found after 5 minutes, look up your local router's DHCP client list
> to find the IP address assigned to the Pi, and connect with `ssh user@<IP>`.

## Step 4: Personalize and Secure Your Robot

Once you are successfully connected via SSH, change the default password and,
optionally, customize the hostname.

### Change the password

Run the password tool and follow the prompts:
```bash
passwd
```

Apply the changes:
```bash
sudo reboot
```

### OPTIONAL - Change the username

The image ships with the user `user`. A logged-in account cannot be renamed, so create
a temporary admin account, rename from there, then remove it. Replace `NEW_USER` with
your choice.

From the default `user` session, create a temporary admin and set its password:
```bash
sudo useradd -m -s /bin/bash -G sudo tmpadmin
sudo passwd tmpadmin
```
Log out, reconnect as `tmpadmin`, then rename the original account:
```bash
ssh tmpadmin@<ROBOT_IP>
sudo usermod -l NEW_USER -d /home/NEW_USER -m user
sudo groupmod -n NEW_USER user      # rename its primary group too
```
Log out, reconnect as `NEW_USER`, and delete the temporary account:
```bash
ssh NEW_USER@<ROBOT_IP>
sudo userdel -r tmpadmin
```
The shutdown-without-password rule still works (it targets the `sudo` group, not a
name). Remember to update the `User` field in your `~/.ssh/config` (Step 5).

Apply the changes:
```bash
sudo reboot
```

### OPTIONAL - Change the hostname

Rename your robot so it no longer answers to `microduck` on the network:
```bash
sudo hostnamectl set-hostname NEW_ROBOT_NAME
```
Then update the hosts file to match:
```bash
sudo nano /etc/hosts
```
Find the line containing `microduck` (usually the second line) and replace it with your
`NEW_ROBOT_NAME`. Save and exit (Ctrl+O, Enter, Ctrl+X).

Apply the changes:
```bash
sudo reboot
```

## Step 5: Deploy the Software from Your Computer

The code already ships on the robot, but you drive and update it from your computer
using the provided `Makefile`, which syncs your local copy to the Pi over SSH and
installs the dependencies there.

1. **Install [uv](https://docs.astral.sh/uv/)** (the Python package manager) on your
   computer:
   ```bash
   curl -LsSf https://astral.sh/uv/install.sh | sh
   ```

2. **Clone the repository** on your computer:
   ```bash
   git clone https://github.com/MarcDcls/microduck.git
   cd microduck
   ```

3. **Add SSH aliases** so the Makefile can reach the Pi. Add the following to your
   `~/.ssh/config`, replacing `user` if you changed it and `<IP_ADDRESS>` with the
   robot's IP on each network:
   ```
   # Main network
   Host microduck
       HostName <IP_ADDRESS>
       User user

   # Secondary network / phone hotspot
   Host microduck-ext
       HostName <IP_ADDRESS>
       User user
   ```
   To find the robot's IP on a given network ping it from your computer while connected to that network:
   ```bash
   ping microduck.local
   ```

   > The Makefile targets default to `HOST=microduck`. To operate the robot over the
   > secondary network, pass `HOST=microduck-ext` (e.g. `make run HOST=microduck-ext`),
   > or export it for the whole session: `export HOST=microduck-ext`.

4. **Copy your SSH key** (recommended) so you are not prompted for a password on every
   command:
   ```bash
   ssh-keygen -t ed25519     # skip if you already have a key
   ssh-copy-id microduck
   ```

5. **Push the code and install dependencies** on the Pi:
   ```bash
   make setup
   ```
   This rsyncs your local copy to the robot and runs `uv sync --frozen` there.

## Step 6: Run the Robot

Your Microduck is ready! Place it on a stable surface (or hold it securely), then start
the control loop from your computer:

```bash
make run
```

On start the robot enables torque and ramps to its neutral pose, then runs the control
loop at 50 Hz attached to your terminal. Press `q` or run `make stop` to stop.

🎉 For the full set of controls — Makefile commands, keyboard and gamepad driving,
the available moves, and how to add your own — see the **[Usage Guide](usage.md)**.
