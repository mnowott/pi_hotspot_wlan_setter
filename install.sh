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
PY_BIN="/usr/local/bin/python3.13"

NM_HOTSPOT_NAME="pi-setup-hotspot"
HOTSPOT_SSID="Pi-Setup"
HOTSPOT_PSK="ChangeMe123"   # CHANGE THIS
HOTSPOT_IP="192.168.50.1/24"
# ----------------------------

if [[ $EUID -ne 0 ]]; then
  echo "Please run as root: sudo ./install.sh"
  exit 1
fi

echo "[*] Updating apt packages..."
apt update

echo "[*] Installing system packages (dnsmasq + iptables + build deps + NetworkManager)..."
apt install -y \
  dnsmasq iptables-persistent network-manager \
  build-essential zlib1g-dev libncurses5-dev libgdbm-dev \
  libnss3-dev libssl-dev libreadline-dev libffi-dev \
  libsqlite3-dev wget git

echo "[*] Ensuring NetworkManager is enabled and running..."
systemctl enable --now NetworkManager

echo "[*] Ensuring dnsmasq service is not auto-starting on boot (we start it via target only)..."
systemctl stop dnsmasq || true
systemctl disable dnsmasq || true

echo "[*] Ensuring local Python $PY_VER at $PY_BIN..."
if [[ -x "$PY_BIN" ]]; then
  echo "  - Found existing $PY_BIN, not rebuilding."
else
  echo "  - $PY_BIN not found, building Python $PY_VER from source..."
  cd /tmp
  if [[ ! -f "$PY_TGZ" ]]; then
    wget "$PY_URL"
  fi
  if [[ ! -d "$PY_DIR" ]]; then
    tar -xf "$PY_TGZ"
  fi
  cd "$PY_DIR"
  ./configure
  make -j"$(nproc)"
  make altinstall   # installs /usr/local/bin/python3.13
  echo "  - Built and installed python3.13 at $PY_BIN"
fi

echo "[*] Ensuring pip for python3.13 at $PY_BIN..."
"$PY_BIN" -m ensurepip --upgrade || true
"$PY_BIN" -m pip install --upgrade pip

echo "[*] Installing Poetry for user $APP_USER (using python3.13)..."
sudo -u "$APP_USER" -H "$PY_BIN" -m pip install --user poetry

echo "[*] Checking app directory at $APP_DIR..."
if [[ ! -d "$APP_DIR" ]]; then
  echo "ERROR: App directory $APP_DIR not found."
  echo "Clone your repo there or adjust APP_DIR in install.sh."
  exit 1
fi

echo "[*] Running 'poetry install' for the app (from repo root, Python 3.13)..."
sudo -u "$APP_USER" -H bash -lc "
  cd '$APP_DIR'
  export PATH=\$HOME/.local/bin:\$PATH
  poetry env use '$PY_BIN'
  poetry install --no-interaction
"

echo "[*] Installing dnsmasq hotspot config..."
# Backup original dnsmasq.conf if it exists and is non-empty
if [[ -s /etc/dnsmasq.conf ]]; then
  cp /etc/dnsmasq.conf /etc/dnsmasq.conf.bak.$(date +%s)
fi
# Make sure dnsmasq uses the /etc/dnsmasq.d/ directory
echo 'conf-dir=/etc/dnsmasq.d' > /etc/dnsmasq.conf
install -m 644 "$APP_DIR/configs/dnsmasq-hotspot.conf" /etc/dnsmasq.d/hotspot.conf

echo "[*] Creating/Updating NetworkManager hotspot connection '$NM_HOTSPOT_NAME'..."
# Check if the connection already exists
if nmcli connection show "$NM_HOTSPOT_NAME" >/dev/null 2>&1; then
  echo "  - Connection '$NM_HOTSPOT_NAME' already exists, updating settings..."
else
  echo "  - Adding new hotspot connection '$NM_HOTSPOT_NAME'..."
  nmcli connection add type wifi ifname wlan0 mode ap con-name "$NM_HOTSPOT_NAME" ssid "$HOTSPOT_SSID"
fi

nmcli connection modify "$NM_HOTSPOT_NAME" \
  802-11-wireless.band bg \
  802-11-wireless.channel 6 \
  802-11-wireless-security.key-mgmt wpa-psk \
  802-11-wireless-security.psk "$HOTSPOT_PSK" \
  ipv4.method manual \
  ipv4.addresses "$HOTSPOT_IP" \
  ipv6.method ignore

echo "[*] Installing captive portal script..."
install -m 755 "$APP_DIR/scripts/captive-portal.sh" /usr/local/bin/captive-portal.sh

echo "[*] Installing systemd units..."
install -m 644 "$APP_DIR/systemd/hotspot-ui.service" /etc/systemd/system/hotspot-ui.service
install -m 644 "$APP_DIR/systemd/captive-portal.service" /etc/systemd/system/captive-portal.service
install -m 644 "$APP_DIR/systemd/pi-hotspot-nm.service" /etc/systemd/system/pi-hotspot-nm.service
install -m 644 "$APP_DIR/systemd/setup-hotspot.target" /etc/systemd/system/setup-hotspot.target
install -m 644 "$APP_DIR/systemd/hotspot-shutdown.service" /etc/systemd/system/hotspot-shutdown.service
install -m 644 "$APP_DIR/systemd/hotspot-shutdown.timer" /etc/systemd/system/hotspot-shutdown.timer

echo "[*] Reloading systemd..."
systemctl daemon-reload

echo "[*] Enabling hotspot-on-boot and 15-minute shutdown timer..."
systemctl enable setup-hotspot.target
systemctl enable hotspot-shutdown.timer

echo
echo "=========================================================="
echo "Installation complete."
echo
echo "Python 3.13 used at: $PY_BIN"
echo
echo "On reboot:"
echo "  - NetworkManager brings up the system normally"
echo "  - setup-hotspot.target starts the NM hotspot + dnsmasq + captive portal + UI"
echo "  - hotspot-shutdown.timer stops them all after 15 minutes"
echo
echo "Manual control:"
echo "  Start hotspot  : sudo systemctl start setup-hotspot.target"
echo "  Stop hotspot   : sudo systemctl stop setup-hotspot.target"
echo "=========================================================="
