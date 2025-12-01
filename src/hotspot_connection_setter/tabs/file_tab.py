from io import BytesIO
from pathlib import Path

import streamlit as st
from PIL import Image, ImageDraw


# ---------- Helper functions ----------


def load_image_from_upload(uploaded_file):
    """Load and verify an uploaded image, return (PIL.Image, error_message_or_None)."""
    try:
        data = uploaded_file.getvalue()
        # First open for verification
        img = Image.open(BytesIO(data))
        img.verify()  # validate
        # Re-open for actual usage (verify() makes the object unusable)
        img = Image.open(BytesIO(data))
        img = img.convert("RGBA")
        return img, None
    except Exception as e:
        return None, str(e)


def create_overlay_preview(
    image: Image.Image, x: int, y: int, w: int, h: int
) -> Image.Image:
    """Return a copy of the image with a red rectangle drawn at (x, y, x+w, y+h)."""
    overlay = image.copy()
    draw = ImageDraw.Draw(overlay)
    box = (x, y, x + w, y + h)
    draw.rectangle(box, outline="red", width=3)
    return overlay


def list_saved_images(folder: Path):
    """Return a sorted list of image paths in the given folder."""
    if not folder.exists():
        return []
    exts = {".png", ".jpg", ".jpeg"}
    return sorted(
        [p for p in folder.iterdir() if p.is_file() and p.suffix.lower() in exts],
        key=lambda p: p.name,
    )


def render_saved_images_section(folder: Path):
    """
    Render the saved images list + preview + delete button.
    This is the 'management' view.
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
            key="manage_saved_image_select",
        )

        selected_saved_path = saved_images[saved_names.index(selected_saved_name)]

        delete_clicked = st.button(
            "🗑️ Delete selected", key="manage_delete_saved_button"
        )
        if delete_clicked:
            try:
                selected_saved_path.unlink()
                st.success(f"Deleted {selected_saved_name}")
                st.experimental_rerun()
            except Exception as e:
                st.error(f"Failed to delete {selected_saved_name}: {e}")

    # Preview in the right column
    with col_preview:
        try:
            img = Image.open(selected_saved_path)
            st.image(img, caption=selected_saved_name, use_container_width=True)
        except Exception as e:
            st.error(f"Could not open {selected_saved_name}: {e}")


# ---------- Main render function for tab 1 ----------


def render(
    uploaded_files,
    selected_name,
    selected_file,
    step: int,
    output_folder: Path,
    crop_width: int,
    crop_height: int,
):
    """
    Render the 'Image management' tab:
    - cropping UI for the selected uploaded image
    - saved-images list + delete + preview
    """
    st.subheader("Manage & crop images")

    # --- Cropping UI (only if we have an uploaded file) ---
    if selected_file is None:
        st.info("Upload images in the sidebar to crop new ones.")
    else:
        # Load image
        img, err = load_image_from_upload(selected_file)
        if err or img is None:
            st.error(f"Failed to open image (invalid or corrupted?): {err}")
        else:
            st.success(f"Loaded image: {img.width} x {img.height} pixels")

            # Effective crop size (never larger than the image)
            desired_w, desired_h = crop_width, crop_height
            crop_w = min(desired_w, img.width)
            crop_h = min(desired_h, img.height)

            if crop_w < desired_w or crop_h < desired_h:
                st.warning(
                    f"Image is smaller than {desired_w}x{desired_h}. "
                    f"Using crop size {crop_w}x{crop_h} instead."
                )

            max_x = img.width - crop_w
            max_y = img.height - crop_h

            # Session state for position per image
            state_key = f"crop_state_{selected_name}"

            if state_key not in st.session_state:
                # Initialize centered
                st.session_state[state_key] = {
                    "x": max_x // 2 if max_x > 0 else 0,
                    "y": max_y // 2 if max_y > 0 else 0,
                    "img_w": img.width,
                    "img_h": img.height,
                    "crop_w": crop_w,
                    "crop_h": crop_h,
                }
            else:
                s = st.session_state[state_key]
                # Reset if image size or crop size changed
                if (
                    s["img_w"] != img.width
                    or s["img_h"] != img.height
                    or s["crop_w"] != crop_w
                    or s["crop_h"] != crop_h
                ):
                    st.session_state[state_key] = {
                        "x": max_x // 2 if max_x > 0 else 0,
                        "y": max_y // 2 if max_y > 0 else 0,
                        "img_w": img.width,
                        "img_h": img.height,
                        "crop_w": crop_w,
                        "crop_h": crop_h,
                    }

            s = st.session_state[state_key]
            x, y = s["x"], s["y"]

            # Movement buttons (centered layout)
            st.markdown("### Move crop area")

            # Row 1: Up button centered
            row1 = st.columns([1, 2, 1])
            with row1[1]:
                btn_up = st.button("⬆️ Up")

            # Row 2: Left / Center / Right
            row2 = st.columns([1, 2, 1])
            with row2[0]:
                btn_left = st.button("⬅️ Left")
            with row2[1]:
                btn_center = st.button("⏺ Center")
            with row2[2]:
                btn_right = st.button("➡️ Right")

            # Row 3: Down button centered
            row3 = st.columns([1, 2, 1])
            with row3[1]:
                btn_down = st.button("⬇️ Down")

            # Update position based on button clicks
            if btn_up:
                y = max(0, y - step)
            if btn_down:
                y = min(max_y, y + step)
            if btn_left:
                x = max(0, x - step)
            if btn_right:
                x = min(max_x, x + step)
            if btn_center:
                x = max_x // 2 if max_x > 0 else 0
                y = max_y // 2 if max_y > 0 else 0

            # Save back to session_state
            s["x"], s["y"] = x, y

            # Create overlay and crop
            overlay_img = create_overlay_preview(img, x, y, crop_w, crop_h)

            crop_box = (x, y, x + crop_w, y + crop_h)
            cropped_img = img.crop(crop_box)

            # Show original + crop preview
            col1, col2 = st.columns(2)

            with col1:
                st.subheader("Original with selection rectangle")
                st.image(overlay_img, use_container_width=True)

            with col2:
                st.subheader(f"Cropped preview ({crop_w} x {crop_h})")
                st.image(cropped_img, use_container_width=False)

            # Save cropped image
            st.markdown("---")
            st.subheader("Save crop")

            save_clicked = st.button("Save cropped image")
            if save_clicked:
                output_folder.mkdir(parents=True, exist_ok=True)

                base_name = Path(selected_file.name).stem
                save_name = f"{base_name}_crop_{x}_{y}_{crop_w}x{crop_h}.png"
                save_path = output_folder / save_name

                cropped_img.save(save_path)
                st.success(f"Saved cropped image to: {save_path}")

    # Saved images list + preview + delete
    st.markdown("---")
    render_saved_images_section(output_folder)
