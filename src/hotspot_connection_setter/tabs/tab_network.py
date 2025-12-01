import platform
import subprocess
from dataclasses import dataclass
from typing import List, Optional, Tuple

import streamlit as st


@dataclass
class WifiNetwork:
    ssid: str
    signal: str
    security: str


# ---------- Windows helpers (netsh) ----------


def list_wifi_windows() -> Tuple[List[WifiNetwork], str]:
    """List Wi-Fi networks using 'netsh' on Windows. Returns (networks, raw_output)."""
    try:
        result = subprocess.check_output(
            ["netsh", "wlan", "show", "networks", "mode=Bssid"],
            encoding="utf-8",
            errors="ignore",
        )
    except Exception as e:
        msg = f"Failed to run 'netsh': {e}"
        st.error(msg)
        return [], msg

    networks_by_ssid: dict[str, WifiNetwork] = {}
    current_ssid: Optional[str] = None

    for line in result.splitlines():
        line = line.strip()
        if not line:
            continue

        # SSID line (works in English & German)
        if line.startswith("SSID ") and ":" in line:
            # Example: "SSID 1 : Doodloe-wifi"
            parts = line.split(":", 1)
            current_ssid = parts[1].strip()
            if current_ssid:
                # Ensure entry exists
                if current_ssid not in networks_by_ssid:
                    networks_by_ssid[current_ssid] = WifiNetwork(
                        ssid=current_ssid,
                        signal="?",
                        security="?",
                    )

        # Signal line (same label in German/English output)
        elif line.startswith("Signal") and ":" in line:
            # Example: "Signal             : 82%"
            if current_ssid:
                parts = line.split(":", 1)
                sig_value = parts[1].strip()
                networks_by_ssid[current_ssid].signal = sig_value or "?"

        # Authentication / Authentifizierung (English / German)
        elif (
            line.startswith("Authentication") or line.startswith("Authentifizierung")
        ) and ":" in line:
            if current_ssid:
                parts = line.split(":", 1)
                sec_value = parts[1].strip()
                networks_by_ssid[current_ssid].security = sec_value or "?"

    return list(networks_by_ssid.values()), result


def connect_wifi_windows(ssid: str, password: Optional[str]) -> str:
    """
    VERY SIMPLE / LIMITED demo of connection logic on Windows.

    - If a profile for SSID already exists, 'netsh wlan connect name=\"SSID\"' might work.
    - Creating a new profile with password properly would require generating a profile XML
      and calling 'netsh wlan add profile filename=\"...\"'.

    This function currently just tries 'netsh wlan connect' and returns stdout/stderr.
    """
    try:
        cmd = ["netsh", "wlan", "connect", f"name={ssid}"]
        completed = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            shell=False,
        )
        out = completed.stdout.strip()
        err = completed.stderr.strip()
        return f"Return code: {completed.returncode}\nSTDOUT:\n{out}\n\nSTDERR:\n{err}"
    except Exception as e:
        return f"Exception while trying to connect: {e}"


# ---------- Linux / Raspberry Pi helpers (nmcli) ----------


def list_wifi_linux() -> Tuple[List[WifiNetwork], str]:
    """
    List Wi-Fi networks using 'nmcli' (NetworkManager) on Linux / Raspberry Pi.

    Requires that:
    - NetworkManager and nmcli are installed
    - The Wi-Fi interface is managed by NetworkManager
    """
    try:
        # -t: terse, -f fields: SSID,SIGNAL,SECURITY
        result = subprocess.check_output(
            ["nmcli", "-t", "-f", "SSID,SIGNAL,SECURITY", "device", "wifi", "list"],
            encoding="utf-8",
            errors="ignore",
        )
    except Exception as e:
        msg = (
            "Failed to run 'nmcli'. Ensure NetworkManager/nmcli are installed and "
            "manage your Wi-Fi interface.\n\n"
            f"Error: {e}"
        )
        st.error(msg)
        return [], msg

    networks: List[WifiNetwork] = []
    for line in result.splitlines():
        line = line.strip()
        if not line:
            continue

        # Format: SSID:SIGNAL:SECURITY
        parts = line.split(":")
        if len(parts) < 3:
            continue

        ssid, signal, security = parts[0], parts[1], parts[2]
        if not ssid:
            continue  # skip hidden SSIDs for this UI

        networks.append(
            WifiNetwork(
                ssid=ssid.strip(),
                signal=(signal or "?").strip(),
                security=(security or "?").strip(),
            )
        )

    # Remove duplicates by SSID
    unique: dict[str, WifiNetwork] = {}
    for n in networks:
        unique.setdefault(n.ssid, n)

    return list(unique.values()), result


def connect_wifi_linux(ssid: str, password: Optional[str]) -> str:
    """
    Connect to Wi-Fi using 'nmcli device wifi connect'.

    This typically requires:
    - Permission to manage networking (often sudo or being in the appropriate group).
    """
    try:
        if password:
            cmd = ["nmcli", "device", "wifi", "connect", ssid, "password", password]
        else:
            cmd = ["nmcli", "device", "wifi", "connect", ssid]

        completed = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            shell=False,
        )
        out = completed.stdout.strip()
        err = completed.stderr.strip()
        return f"Return code: {completed.returncode}\nSTDOUT:\n{out}\n\nSTDERR:\n{err}"
    except Exception as e:
        return f"Exception while trying to connect: {e}"


# ---------- Unified render ----------


def render():
    st.subheader("Network / WLAN configuration (experimental)")

    os_name = platform.system()

    if os_name == "Windows":
        st.info("Detected OS: Windows (using 'netsh').")
        list_fn = list_wifi_windows
        connect_fn = connect_wifi_windows
    elif os_name == "Linux":
        st.info("Detected OS: Linux (using 'nmcli' / NetworkManager).")
        list_fn = list_wifi_linux
        connect_fn = connect_wifi_linux
    else:
        st.info(
            "This demo currently supports only Windows (netsh) and "
            "Linux/Raspberry Pi (nmcli/NetworkManager).\n\n"
            f"Your OS appears to be: {os_name}."
        )
        return

    st.markdown("### Available Wi-Fi networks")

    if st.button("Scan networks"):
        networks, raw = list_fn()
        st.session_state["wifi_scan_results"] = networks
        st.session_state["wifi_raw_output"] = raw

    networks = st.session_state.get("wifi_scan_results", [])
    raw_output = st.session_state.get("wifi_raw_output", "")

    if not networks:
        st.info(
            "No networks parsed.\n\n"
            "This might mean:\n"
            "- Wi-Fi is disabled, or\n"
            "- There's no wireless interface, or\n"
            "- The command output format is different than expected.\n\n"
            "See the raw command output below."
        )

        if raw_output:
            with st.expander("Show raw command output"):
                st.code(raw_output, language="text")
        else:
            st.info("Click 'Scan networks' to list available Wi-Fi networks.")
        return

    # Show the parsed list
    ssid_labels = [
        f"{n.ssid} (Signal: {n.signal}, Security: {n.security})" for n in networks
    ]
    selected_idx = st.selectbox(
        "Select network",
        options=list(range(len(networks))),
        format_func=lambda i: ssid_labels[i],
        key="wifi_select",
    )
    selected_network = networks[selected_idx]

    st.write(f"Selected SSID: **{selected_network.ssid}**")
    password = st.text_input(
        "Password (if required)",
        type="password",
        key="wifi_password",
    )

    if st.button("Connect to selected network"):
        st.info("Attempting to connect... (this may take a few seconds)")
        result = connect_fn(selected_network.ssid, password or None)

        # Show the result once in this run (useful for debugging)
        st.code(result, language="text")

        # Force a rerun so that app.py recomputes `online = has_internet()`
        st.success("Connection command executed. Re-checking connectivity...")
        st.rerun()

    # Always show the last raw output in an expander for debugging
    if raw_output:
        with st.expander("Show raw command output"):
            st.code(raw_output, language="text")
