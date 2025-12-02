#!/bin/bash
set -e

# ---------- CONFIG ----------
APP_USER=pi
APP_HOME="/home/$APP_USER"
APP_DIR="$APP_HOME/pi_hotspot_wlan_setter"
PY_VER="3.13.7"
PY_TGZ="Python-$PY_VER.tgz"
PY_DIR="Python-$PY_VER"
PY_URL="https://www.python.org/ftp/python/$PY_VER/$PY_TGZ"
# ----------------------------

if [[ $EUID -ne 0 ]]; then
  echo "Please run as root: sudo ./install.sh"
  exit 1
fi

echo "[*] Updating apt packages..."
apt update

echo "[*] Installing system packages (AP + build deps)..."
apt install -y \
  hostapd dnsmasq iptables-persistent \
  build-essential zlib1g-dev libncurses5-dev libgdbm-dev \
  libnss3-dev libssl-dev libreadline-dev libffi-dev \
  libsqlite3-dev wget git

echo "[*] Switching to dhcpcd instead of NetworkManager (Bookworm)..."
if systemctl list-unit-files | grep -q NetworkManager.service; then
  systemctl disable --now NetworkManager || true
fi
systemctl enable --now dhcpcd || true

echo "[*] Ensure hostapd/dnsmasq are stopped (we start them only via target)..."
systemctl stop hostapd || true
systemctl stop dnsmasq || true
systemctl disable hostapd || true
systemctl disable dnsmasq || true

echo "[*] Installing Python $PY_VER if needed..."
if ! command -v python3.13 >/dev/null 2>&1; then
  cd /tmp
  if [[ ! -f "$PY_TGZ" ]]; then
    wget "$PY_URL"
  fi
  if [[ ! -d "$PY_DIR" ]]; then
    tar -xf "$PY_TGZ"
  fi
  cd "$PY_DIR"
  ./configure --enable-optimizations
  make -j"$(nproc)"
  make altinstall  # installs python3.13 to /usr/local/bin
else
  echo "  - python3.13 already present, skipping build."
fi

echo "[*] Installing Poetry for user $APP_USER (using python3.13)..."
sudo -u "$APP_USER" -H /usr/local/bin/python3.13 -m pip install --upgrade pip
sudo -u "$APP_USER" -H /usr/local/bin/python3.13 -m pip install poetry

echo "[*] Checking app directory at $APP_DIR..."
if [[ ! -d "$APP_DIR" ]]; then
  echo "ERROR: App directory $APP_DIR not found."
  echo "Clone your repo there or adjust APP_DIR in install.sh."
  exit 1
fi

echo "[*] Running 'poetry install' for the app (Python 3.13)..."
sudo -u "$APP_USER" -H bash -lc "
  cd '$APP_DIR'
  poetry env use /usr/local/bin/python3.13
  poetry install --no-interaction
"

echo "[*] Installing hostapd config..."
install -m 644 configs/hostapd.conf /etc/hostapd/hostapd.conf
if grep -q '^DAEMON_CONF=' /etc/default/hostapd 2>/dev/null; then
  sed -i 's|^DAEMON_CONF=.*|DAEMON_CONF=\"/etc/hostapd/hostapd.conf\"|' /etc/default/hostapd
else
  echo 'DAEMON_CONF="/etc/hostapd/hostapd.conf"' >> /etc/default/hostapd
fi

echo "[*] Installing dnsmasq config..."
if [[ -s /etc/dnsmasq.conf ]]; then
  cp /etc/dnsmasq.conf /etc/dnsmasq.conf.bak.$(date +%s)
fi
install -m 644 configs/dnsmasq-hotspot.conf /etc/dnsmasq.d/hotspot.conf

echo "[*] Appending dhcpcd hotspot snippet (if not already present)..."
if ! grep -q '192.168.50.1/24' /etc/dhcpcd.conf 2>/dev/null; then
  cat configs/dhcpcd-wlan0-hotspot.conf.snippet >> /etc/dhcpcd.conf
else
  echo "  - dhcpcd.conf already has 192.168.50.1, skipping."
fi

echo "[*] Installing captive portal script..."
install -m 755 scripts/captive-portal.sh /usr/local/bin/captive-portal.sh

echo "[*] Installing systemd units..."
install -m 644 systemd/hotspot-ui.service /etc/systemd/system/hotspot-ui.service
install -m 644 systemd/captive-portal.service /etc/systemd/system/captive-portal.service
install -m 644 systemd/setup-hotspot.target /etc/systemd/system/setup-hotspot.target
install -m 644 systemd/hotspot-shutdown.service /etc/systemd/system/hotspot-shutdown.service
install -m 644 systemd/hotspot-shutdown.timer /etc/systemd/system/hotspot-shutdown.timer

echo "[*] Reloading systemd..."
systemctl daemon-reload

echo "[*] Enabling the 15-minute shutdown timer (but not starting hotspot on boot)..."
systemctl enable hotspot-shutdown.timer
systemctl enable setup-hotspot.target

echo
echo "=========================================================="
echo "Installation complete."
echo
echo "To start a 15-minute hotspot session:"
echo "  sudo systemctl start setup-hotspot.target"
echo "  sudo systemctl start hotspot-shutdown.timer"
echo
echo "To stop immediately:"
echo "  sudo systemctl stop setup-hotspot.target"
echo "  sudo systemctl stop hotspot-shutdown.timer"
echo
echo "Connect to Wi-Fi SSID 'Pi-Setup' (password in hostapd.conf),"
echo "then open any HTTP site – you should see your hotspot UI."
echo "=========================================================="
