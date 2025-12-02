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

* Password-protected Wi-Fi hotspot using **NetworkManager** (Wi-Fi AP connection on `wlan0`)
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

* This repository cloned to:

  ```text
  /home/pi/pi_hotspot_wlan_setter
  ```

* App CLI entry point: `hotspot-ui` (installed by Poetry)

* You are OK with:

  * Installing **Python 3.13** from source under `/usr/local/bin/python3.13`
  * Using **NetworkManager** to manage the hotspot connection on `wlan0`
  * Adding a **dnsmasq** config for the hotspot network

All of this is handled automatically by `install.sh`.

---

## Repository Layout

This repo contains both the app and the infra:

```text
/pi_hotspot_wlan_setter/
├── README.md
├── install.sh
├── pyproject.toml
├── src/hotspot_connection_setter/      # Streamlit app package
│   ├── app.py                          # Streamlit app
│   ├── cli.py                          # CLI entrypoint (hotspot-ui)
│   └── tabs/                           # One .py file per app tab
├── configs/
│   └── dnsmasq-hotspot.conf
├── scripts/
│   └── captive-portal.sh
└── systemd/
    ├── hotspot-ui.service
    ├── captive-portal.service
    ├── pi-hotspot-nm.service
    ├── setup-hotspot.target
    ├── hotspot-shutdown.service
    └── hotspot-shutdown.timer
```

### Components

* `configs/dnsmasq-hotspot.conf`
  DHCP + DNS configuration for `192.168.50.0/24`, with all DNS names resolved to `192.168.50.1`.

* `scripts/captive-portal.sh`
  Sets and clears iptables NAT rules to redirect HTTP on `wlan0:80` → `localhost:9000`.

* `systemd/hotspot-ui.service`
  Runs your app via Poetry:

  ```ini
  ExecStart=/usr/bin/env poetry run hotspot-ui --port 9000 --address 127.0.0.1
  ```

* `systemd/captive-portal.service`
  `Type=oneshot` service that calls `captive-portal.sh start` on start and `captive-portal.sh stop` on stop, and keeps its “active” state with `RemainAfterExit=yes`.

* `systemd/pi-hotspot-nm.service`
  `Type=oneshot` service that uses **NetworkManager** to bring the hotspot connection up/down:

  * `nmcli connection up pi-setup-hotspot`
  * `nmcli connection down pi-setup-hotspot`

* `systemd/setup-hotspot.target`
  Systemd target that ties everything together:

  * `pi-hotspot-nm.service` (NetworkManager hotspot)
  * `dnsmasq.service`
  * `captive-portal.service`
  * `hotspot-ui.service`

* `systemd/hotspot-shutdown.service` + `systemd/hotspot-shutdown.timer`
  Timer fires after 15 minutes and stops `setup-hotspot.target` → hotspot + app + iptables rules are shut down.

---

## Installation

> ⚠️ Installation assumes you are OK with:
>
> * Installing Python 3.13 from source
> * Using NetworkManager + nmcli to create/manage a Wi-Fi AP connection
> * Having dnsmasq run for the hotspot subnet

### 1. Clone the repository

As user `pi`:

```bash
cd ~
git clone https://github.com/mnowott/pi_hotspot_wlan_setter.git
cd pi_hotspot_wlan_setter
```

### 2. Make the installer executable

```bash
chmod +x install.sh
```

### 3. Run the installer

```bash
sudo ./install.sh
```

`install.sh` will:

1. **Install APT packages**

   * `dnsmasq`, `iptables-persistent`, `network-manager`
   * Build tools and libraries needed for Python 3.13

2. **Ensure NetworkManager is active**

   * Enable and start `NetworkManager`:

     ```bash
     systemctl enable --now NetworkManager
     ```

   * Stop and disable the global `dnsmasq` service (we only start it as part of the hotspot):

     ```bash
     systemctl stop dnsmasq
     systemctl disable dnsmasq
     ```

3. **Install Python 3.13**

   * Check if `python3.13` exists
   * If not, download, build, and `make altinstall` to `/usr/local/bin/python3.13`

4. **Install Poetry**

   * Ensure pip for Python 3.13
   * Install Poetry for user `pi` using Python 3.13 (as a user-level tool: `~/.local/bin/poetry`)

5. **Install your app via Poetry**

   * Verify that `/home/pi/pi_hotspot_wlan_setter` exists
   * As user `pi`, run from the app root:

     ```bash
     poetry env use /usr/local/bin/python3.13
     poetry install --no-interaction
     ```

6. **Install dnsmasq config**

   * Backup `/etc/dnsmasq.conf` if non-empty

   * Replace `/etc/dnsmasq.conf` with:

     ```ini
     conf-dir=/etc/dnsmasq.d
     ```

   * Install `configs/dnsmasq-hotspot.conf` as `/etc/dnsmasq.d/hotspot.conf`

7. **Create/Update NetworkManager hotspot connection**

   * Use `nmcli` to create/modify a Wi-Fi AP connection called `pi-setup-hotspot` with:

     * Interface: `wlan0`
     * Mode: `ap`
     * SSID: `Pi-Setup` (default, configurable)
     * Password: `ChangeMe123` (default, configurable)
     * Static IPv4: `192.168.50.1/24` on `wlan0`
     * IPv6 disabled

8. **Install captive portal script**

   * Copy `scripts/captive-portal.sh` to `/usr/local/bin/captive-portal.sh` and make it executable

9. **Install systemd units**

   * Copy units from `systemd/` to `/etc/systemd/system/`
   * Run `systemctl daemon-reload`
   * Enable on boot:

     * `setup-hotspot.target`
     * `hotspot-shutdown.timer`

After installation, a summary is printed describing boot behavior and manual control.

---

## Behavior After Installation

### On reboot

* `setup-hotspot.target` starts automatically, which starts:

  * `pi-hotspot-nm.service`
    → `nmcli connection up pi-setup-hotspot` (NetworkManager hotspot on `wlan0` with IP `192.168.50.1`)
  * `dnsmasq` (DHCP + DNS on `192.168.50.0/24`)
  * `captive-portal.service` (iptables redirect 80 → 9000)
  * `hotspot-ui.service` (your app via Poetry on `127.0.0.1:9000`)

* `hotspot-shutdown.timer` also starts automatically.

  * After 15 minutes it triggers `hotspot-shutdown.service`, which runs:

    ```bash
    systemctl stop setup-hotspot.target
    ```

  * This stops:

    * The NetworkManager hotspot connection (`nmcli connection down pi-setup-hotspot`)
    * `dnsmasq`
    * `captive-portal.service` (which flushes iptables NAT rules)
    * `hotspot-ui.service`

Result:
On boot, the Pi exposes a hotspot for 15 minutes, and then shuts it down automatically.
NetworkManager remains in control of networking before and after the hotspot session.

---

## Usage

### Connecting to the hotspot

1. On your client device (phone/laptop), connect to:

   * **SSID**: `Pi-Setup` (or whatever you set in `install.sh`)
   * **Password**: the one configured as `HOTSPOT_PSK` in `install.sh`
     (default: `ChangeMe123` – **change it!**)

2. Open any **HTTP** URL (e.g. `http://example.com`):

   * All DNS resolves to `192.168.50.1` (the Pi)
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
# See recent logs for hotspot-related services
journalctl -u NetworkManager -u dnsmasq -u hotspot-ui -u captive-portal --since "10 min ago"

# Follow the app logs in real time
journalctl -u hotspot-ui.service -f
```

---

## Customization

### Change SSID / password

**Option 1: Edit `install.sh` before running it**

* Change these variables near the top:

  ```bash
  NM_HOTSPOT_NAME="pi-setup-hotspot"
  HOTSPOT_SSID="Pi-Setup"
  HOTSPOT_PSK="ChangeMe123"
  HOTSPOT_IP="192.168.50.1/24"
  ```

Re-run `install.sh` (or just re-run the `nmcli connection modify` commands manually) to update the hotspot connection.

**Option 2: Use nmcli / NetworkManager after install**

```bash
nmcli connection modify pi-setup-hotspot 802-11-wireless.ssid "MyNewSSID"
nmcli connection modify pi-setup-hotspot 802-11-wireless-security.psk "MyNewSecret123"
```

Then either:

```bash
sudo systemctl restart setup-hotspot.target
```

or just reboot.

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

If you change the app port in `hotspot-ui.service`, also update `APP_PORT` in `scripts/captive-portal.sh` so iptables redirects to the right port.

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

   * `/etc/dnsmasq.d/hotspot.conf`
   * (Optionally) restore `/etc/dnsmasq.conf` from backup

3. Optionally remove the NetworkManager hotspot connection:

   ```bash
   nmcli connection delete pi-setup-hotspot
   ```

4. You can keep NetworkManager as-is; no need to change system-wide networking.

A scripted `uninstall.sh` can be added to automate this.

---

## Security Notes

* **Change the default Wi-Fi password** from `ChangeMe123` before using this anywhere non-trivial.
* The hotspot network is local-only by default (no internet), but still treat connected clients as untrusted.
* The app runs as user `pi`. For stronger isolation, consider creating a dedicated system user for the app and updating `hotspot-ui.service` accordingly.

```
::contentReference[oaicite:0]{index=0}
```
