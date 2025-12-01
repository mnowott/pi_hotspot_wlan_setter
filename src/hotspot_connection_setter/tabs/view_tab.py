from pathlib import Path

import streamlit as st
from PIL import Image


def list_saved_images(folder: Path):
    """Return a sorted list of image paths in the given folder."""
    if not folder.exists():
        return []
    exts = {".png", ".jpg", ".jpeg"}
    return sorted(
        [p for p in folder.iterdir() if p.is_file() and p.suffix.lower() in exts],
        key=lambda p: p.name,
    )


def render_saved_images_view(folder: Path):
    """
    Render the saved images list + preview (view-only).
    No delete here.
    """
    st.subheader("Saved images")

    saved_images = list_saved_images(folder)

    if not saved_images:
        st.info("No saved images found in the output folder yet.")
        return

    col_list, col_preview = st.columns([1, 2])

    saved_names = [p.name for p in saved_images]

    with col_list:
        selected_saved_name = st.selectbox(
            "Saved images",
            saved_names,
            key="view_saved_image_select",
        )

        selected_saved_path = saved_images[saved_names.index(selected_saved_name)]

    # Preview in the right column
    with col_preview:
        try:
            img = Image.open(selected_saved_path)
            st.image(img, caption=selected_saved_name, use_container_width=True)
        except Exception as e:
            st.error(f"Could not open {selected_saved_name}: {e}")


def render(output_folder: Path):
    """Render the 'View' tab."""
    st.subheader("View saved images")
    render_saved_images_view(output_folder)
