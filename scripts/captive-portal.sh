#!/bin/bash
set -e

APP_PORT=9000
WLAN_IF=wlan0

case "$1" in
  start)
    echo "[captive-portal] Setting up iptables rules"
    # Flush NAT table
    iptables -t nat -F

    # Redirect HTTP on wlan0 to our app port
    iptables -t nat -A PREROUTING -i "$WLAN_IF" -p tcp --dport 80 \
      -j REDIRECT --to-port "$APP_PORT"

    # optional: also redirect 8080 → 9000 if needed
    # iptables -t nat -A PREROUTING -i "$WLAN_IF" -p tcp --dport 8080 \
    #   -j REDIRECT --to-port "$APP_PORT"

    ;;

  stop)
    echo "[captive-portal] Clearing iptables NAT rules"
    iptables -t nat -F
    ;;

  *)
    echo "Usage: $0 {start|stop}"
    exit 1
    ;;
esac
