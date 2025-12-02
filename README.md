````markdown
# pi_hotspot_infra

Infrastructure to turn a **Raspberry Pi Zero 2 W** (Pi OS 64-bit) into a **captive-portal Wi-Fi hotspot** that serves your WLAN setup UI from:

> `https://github.com/mnowott/pi_hotspot_wlan_setter.git`

The app is started via:

```bash
poetry run hotspot-ui --port 9000 --address 127.0.0.1
````

All HTTP traffic from hotspot clients is transparently redirected to this app for **15 minutes**, after which the hotspot automatically shuts down and the Pi returns to normal networking.

---

## Features

* Password-protected Wi-Fi hotspot using **hostapd**
* **DHCP + DNS** using **dnsmasq**, with all DNS names resolved to the Pi → captive-portal behavior
* **iptables** redirects client HTTP (port 80) → `hotspot-ui` on port **9000**
* The app is managed by **systemd**, started via **Poetry** using **Python 3.13**
* Hotspot + app **auto-start on boot**
* **Auto-shutdown after 15 minutes** via a systemd timer
* Can still be **started / stopped manually** via `systemctl`

---

## Requirements / Assumptions

* Device: Raspberry Pi Zero 2 W (or similar Pi with Wi-Fi)

* OS: Raspberry Pi OS 64-bit (Bookworm)

* User: `pi`

* Your app repo cloned to:

  ```text
  /home/pi/pi_hotspot_wlan_setter
  ```

* App CLI entry point: `hotspot-ui` (installed by Poetry)

* You are OK with:

  * Switching networking from **NetworkManager → dhcpcd**
  * Installing **Python 3.13** from source under `/usr/local/bin/python3.13`

All of this is handled automatically by `install.sh`.

---

## Repository Layout

This infra repo is intended to live next to your app repo:

```text
/pi_hotspot_wlan_setter/ # this repo  # your app (Streamlit/Poetry)
└── /         
    ├── README.md
    ├── install.sh
    ├── src/ # streamlit app
    │   ├── hotspot_connection_setter/
    │   │   ├── app.py # streamlit app
    │   │   ├── cli.py # entrypoint for systemd to take on command line arguments
    │   │   ├── tabs/  # .py file per app tab
    ├── configs/
    │   ├── hostapd.conf
    │   ├── dnsmasq-hotspot.conf
    │   └── dhcpcd-wlan0-hotspot.conf.snippet
    ├── scripts/
    │   └── captive-portal.sh
    └── systemd/
        ├── hotspot-ui.service
        ├── captive-portal.service
        ├── setup-hotspot.target
        ├── hotspot-shutdown.service
        └── hotspot-shutdown.timer
```

### Components

* `configs/hostapd.conf`
  Wi-Fi hotspot configuration (SSID, password, channel, etc.).

* `configs/dnsmasq-hotspot.conf`
  DHCP + DNS configuration for `192.168.50.0/24`, with all DNS names resolved to `192.168.50.1`.

* `configs/dhcpcd-wlan0-hotspot.conf.snippet`
  Snippet appended to `/etc/dhcpcd.conf` to give `wlan0` a static IP and disable `wpa_supplicant`.

* `scripts/captive-portal.sh`
  Sets and clears iptables NAT rules to redirect HTTP on `wlan0:80` → `localhost:9000`.

* `systemd/hotspot-ui.service`
  Runs your app via Poetry:

  ```ini
  ExecStart=/usr/bin/env poetry run hotspot-ui --port 9000 --address 127.0.0.1
  ```

* `systemd/captive-portal.service`
  `Type=oneshot` service that calls `captive-portal.sh start` on start and `captive-portal.sh stop` on stop.

* `systemd/setup-hotspot.target`
  Systemd target that ties everything together:

  * `hostapd.service`
  * `dnsmasq.service`
  * `captive-portal.service`
  * `hotspot-ui.service`

* `systemd/hotspot-shutdown.service` + `systemd/hotspot-shutdown.timer`
  Timer fires after 15 minutes and stops `setup-hotspot.target` → hotspot + app + iptables rules are shut down.

---

## Installation

> ⚠️ Installation assumes you are OK with:
>
> * Disabling NetworkManager
> * Enabling dhcpcd
> * Installing Python 3.13 from source

### 1. Clone repositories

As user `pi`:

```bash
cd ~
git clone https://github.com/mnowott/pi_hotspot_wlan_setter.git
git clone https://github.com/<your-account>/pi_hotspot_infra.git
```

Adjust the second URL to wherever you host this infra repo.

### 2. Make the installer executable

```bash
cd ~/pi_hotspot_infra
chmod +x install.sh
```

### 3. Run the installer

```bash
sudo ./install.sh
```

`install.sh` will:

1. **Install APT packages**

   * `hostapd`, `dnsmasq`, `iptables-persistent`
   * Build tools and libraries needed for Python 3.13

2. **Configure networking**

   * Disable and stop `NetworkManager` (if present)
   * Enable and start `dhcpcd`
   * Stop and disable global autostart of `hostapd` and `dnsmasq`
     (they’re started only via `setup-hotspot.target`)

3. **Install Python 3.13**

   * Check if `python3.13` exists
   * If not, download, build, and `make altinstall` to `/usr/local/bin/python3.13`

4. **Install Poetry**

   * Ensure pip for Python 3.13
   * Install Poetry for user `pi` with Python 3.13

5. **Install your app via Poetry**

   * Verify that `/home/pi/pi_hotspot_wlan_setter` exists
   * As user `pi`, run from the app root:

     ```bash
     poetry env use /usr/local/bin/python3.13
     poetry install --no-interaction
     ```

6. **Install configs**

   * Copy `configs/hostapd.conf` to `/etc/hostapd/hostapd.conf` and set `DAEMON_CONF` in `/etc/default/hostapd`
   * Backup `/etc/dnsmasq.conf` if non-empty and copy `configs/dnsmasq-hotspot.conf` to `/etc/dnsmasq.d/hotspot.conf`
   * Append `configs/dhcpcd-wlan0-hotspot.conf.snippet` to `/etc/dhcpcd.conf` if not already present

7. **Install captive portal script**

   * Copy `scripts/captive-portal.sh` to `/usr/local/bin/captive-portal.sh` and make it executable

8. **Install systemd units**

   * Copy units from `systemd/` to `/etc/systemd/system/`
   * Run `systemctl daemon-reload`
   * Enable on boot:

     * `setup-hotspot.target`
     * `hotspot-shutdown.timer`

After installation, a summary is printed showing how to control the hotspot.

---

## Behavior After Installation

### On reboot

* `setup-hotspot.target` starts automatically, which starts:

  * `hostapd` (Wi-Fi hotspot, default SSID: `Pi-Setup`)
  * `dnsmasq` (DHCP + DNS)
  * `captive-portal.service` (iptables redirect)
  * `hotspot-ui.service` (your app via Poetry on `127.0.0.1:9000`)

* `hotspot-shutdown.timer` also starts automatically.

  * After 15 minutes it triggers `hotspot-shutdown.service`, which runs:

    ```bash
    systemctl stop setup-hotspot.target
    ```

  * This stops all hotspot-related services and clears the NAT rules.

Result:
On boot, the Pi exposes a hotspot for 15 minutes, and then shuts it down automatically.

---

## Usage

### Connecting to the hotspot

1. On your client device (phone/laptop), connect to:

   * **SSID**: `Pi-Setup`
   * **Password**: the one set in `configs/hostapd.conf` (default: `ChangeMe123` – change it!)

2. Open any **HTTP** URL (e.g. `http://example.com`):

   * All DNS resolves to `192.168.50.1` (Pi)
   * iptables redirects port 80 on `wlan0` to `localhost:9000`
   * You see the `hotspot-ui` app

> Note: Captive portal behaviour depends on the client OS; some may automatically open a “login” page.

### Manual control

Even with auto-start enabled, you can control the hotspot manually:

* **Start hotspot + timer** (e.g. if it already timed out):

  ```bash
  sudo systemctl start setup-hotspot.target
  sudo systemctl start hotspot-shutdown.timer
  ```

* **Stop hotspot immediately**:

  ```bash
  sudo systemctl stop setup-hotspot.target
  sudo systemctl stop hotspot-shutdown.timer
  ```

* **Disable auto-start on boot** (if you only want manual control):

  ```bash
  sudo systemctl disable setup-hotspot.target
  sudo systemctl disable hotspot-shutdown.timer
  ```

### Logs

Useful commands:

```bash
# See recent logs for hotspot services
journalctl -u hostapd -u dnsmasq -u hotspot-ui -u captive-portal --since "10 min ago"

# Follow the app logs in real time
journalctl -u hotspot-ui.service -f
```

---

## Customization

### Change SSID / password

Edit `configs/hostapd.conf` before installation, or after installation edit:

```bash
sudo nano /etc/hostapd/hostapd.conf
sudo systemctl restart hostapd
```

### Change timeout duration

Edit:

```ini
# /etc/systemd/system/hotspot-shutdown.timer
OnActiveSec=15min
```

For example, `30min` or `5min`. Then:

```bash
sudo systemctl daemon-reload
sudo systemctl restart hotspot-shutdown.timer
```

### Change app port

If you change the app port in `hotspot-ui.service`, also update `APP_PORT` in `scripts/captive-portal.sh` so iptables redirects to the correct port.

### Change user / paths

If your user is not `pi` or the app path differs, update:

* `APP_USER`, `APP_HOME`, `APP_DIR` in `install.sh`
* `User` and `WorkingDirectory` in `systemd/hotspot-ui.service`

---

## Uninstall (Manual)

To undo the basic setup:

1. Disable units:

   ```bash
   sudo systemctl disable setup-hotspot.target
   sudo systemctl disable hotspot-shutdown.timer
   ```

2. Optionally clean up config files:

   * `/etc/hostapd/hostapd.conf`
   * `/etc/dnsmasq.d/hotspot.conf`
   * The hotspot snippet in `/etc/dhcpcd.conf`

3. Optionally re-enable NetworkManager and disable dhcpcd:

   ```bash
   sudo systemctl enable --now NetworkManager
   sudo systemctl disable --now dhcpcd
   ```

A scripted `uninstall.sh` can be added to automate this.

---

## Security Notes

* **Change the default Wi-Fi password** from `ChangeMe123` before using this anywhere non-trivial.
* The hotspot network is local-only by default (no internet), but still treat connected clients as untrusted.
* The app runs as user `pi`. For stronger isolation, consider creating a dedicated system user for the app and updating `hotspot-ui.service` accordingly.

```
::contentReference[oaicite:0]{index=0}
```
