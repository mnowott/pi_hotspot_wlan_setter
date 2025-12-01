import streamlit as st
from hotspot_connection_setter.tabs import tab_network, env_tab
import socket


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
    page_title=f"Wlan Hotspot Connector",
    layout="wide",
)

st.title(f"Wlan Hotspot Connector")
st.write(
    "Chose wlan network from available hotspots and connect to it."
    "Portal is active for 15 minutes."
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
    env_tab.render()
