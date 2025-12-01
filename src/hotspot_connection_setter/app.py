from pathlib import Path

import streamlit as st
from tabs import file_tab, view_tab, tab_network
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

# ---------- Sidebar: uploads, movement settings, output folder ----------

st.sidebar.header("Upload Images")
uploaded_files = st.sidebar.file_uploader(
    "Choose PNG/JPG images from your computer",
    type=["png", "jpg", "jpeg"],
    accept_multiple_files=True,
)

if uploaded_files:
    names = [f.name for f in uploaded_files]
    selected_name = st.sidebar.selectbox(
        "Select image to edit",
        names,
        key="uploaded_image_select",
    )
    selected_file = uploaded_files[names.index(selected_name)]
else:
    selected_name = None
    selected_file = None

st.sidebar.header("Move Selection")
step = st.sidebar.number_input(
    "Step size (pixels)",
    min_value=1,
    max_value=500,
    value=20,
)

st.sidebar.header("Output folder")
output_root_default = str(Path.cwd() / "output")
output_folder_str = st.sidebar.text_input(
    "Output folder on disk",
    value=output_root_default,
    key="output_folder",
)
output_folder = Path(output_folder_str)

# ---------- Tabs ----------

tab_manage, tab_view, tab_net = st.tabs(["Image management", "View", "Network"])


with tab_net:
    # Network tab is still available even if we're offline,
    # since it might be used to *establish* connectivity.
    tab_network.render()

with tab_manage:
    if not online:
        st.info(
            "🚫 No internet connection detected.\n\n"
            "Image management is temporarily disabled. "
            "Please connect to the internet and rerun."
        )
    else:
        file_tab.render(
            uploaded_files=uploaded_files,
            selected_name=selected_name,
            selected_file=selected_file,
            step=step,
            output_folder=output_folder,
            crop_width=CROP_WIDTH,
            crop_height=CROP_HEIGHT,
        )

with tab_view:
    if not online:
        st.info(
            "🚫 No internet connection detected.\n\n"
            "Viewing saved images is temporarily disabled. "
            "Please connect to the internet and rerun."
        )
    else:
        view_tab.render(
            output_folder=output_folder,
        )
