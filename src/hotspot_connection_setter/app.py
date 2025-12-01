from pathlib import Path

import streamlit as st
from src.hotspot_connection_setter.tabs import tab_network, view_tab
import socket

# === CONFIG ===
CROP_WIDTH = 200
CROP_HEIGHT = 200


def has_internet(timeout: float = 3.0) -> bool:
    """
    Check if we have (likely) internet access by trying to open a TCP
    connection to Google's public DNS server (8.8.8.8) on port 53.

    This avoids DNS lookup and is a common, lightweight connectivity check.
    """
    try:
        socket.create_connection(("8.8.8.8", 53), timeout=timeout)
        return True
    except OSError:
        return False


st.set_page_config(
    page_title=f"Image Cropper {CROP_WIDTH}x{CROP_HEIGHT}",
    layout="wide",
)

st.title(f"Local Image Cropper ({CROP_WIDTH} x {CROP_HEIGHT})")
st.write(
    "Upload an image, move the fixed-size selection with buttons, "
    "save crops, and manage/view saved images."
)

# ---------- Connectivity status ----------

online = has_internet()

status_col1, status_col2 = st.columns([1, 4])
with status_col1:
    if online:
        st.success("Internet: online")
    else:
        st.error("Internet: offline")
with status_col2:
    if not online:
        st.write(
            "Tabs **Image management** and **View** are disabled until an "
            "internet connection is available."
        )

# ---------- Tabs ----------

tab_net, tab_view = st.tabs(["Network", "placeholder View"])


with tab_net:
    # Network tab is still available even if we're offline,
    # since it might be used to *establish* connectivity.
    tab_network.render()

with tab_view:
    if not online:
        st.info(
            "🚫 No internet connection detected.\n\n"
            "Viewing saved images is temporarily disabled. "
            "Please connect to the internet and rerun."
        )
    else:
        view_tab.render(
        )
