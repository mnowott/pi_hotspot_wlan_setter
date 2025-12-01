from pathlib import Path
from typing import List, Dict

import streamlit as st

ENV_FILE = Path.home() / ".hotspot_connection_setter.env"


def _load_env_file() -> List[Dict[str, str]]:
    """Read KEY=VALUE pairs from the .env file into a list of dicts."""
    rows: List[Dict[str, str]] = []

    if not ENV_FILE.exists():
        return rows

    for line in ENV_FILE.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            continue

        key, value = line.split("=", 1)
        key = key.strip()
        # keep value as-is (except newline already stripped)
        rows.append({"key": key, "value": value})

    return rows


def _save_env_file(rows: List[Dict[str, str]]) -> None:
    """Write the current rows back to the .env file."""
    # keep only rows with a non-empty key
    cleaned = [r for r in rows if r["key"].strip()]

    lines = [f'{r["key"].strip()}={r["value"]}' for r in cleaned]
    text = "\n".join(lines) + ("\n" if lines else "")
    ENV_FILE.write_text(text)


def _ensure_state_initialized() -> None:
    if "env_rows" not in st.session_state:
        existing = _load_env_file()
        st.session_state.env_rows = existing or [{"key": "", "value": ""}]


def render() -> None:
    """Render the 'View saved env' tab."""
    st.subheader("Environment configuration")
    st.caption(f"File: `{ENV_FILE}`")

    _ensure_state_initialized()

    rows: List[Dict[str, str]] = st.session_state.env_rows

    st.markdown("Edit key/value pairs stored in the `.env` file:")

    # Render rows
    to_delete_index = None
    for idx, row in enumerate(rows):
        cols = st.columns([3, 6, 1])
        with cols[0]:
            rows[idx]["key"] = st.text_input(
                "Key",
                value=row["key"],
                key=f"env_key_{idx}",
                placeholder="MY_VAR",
            )
        with cols[1]:
            rows[idx]["value"] = st.text_input(
                "Value",
                value=row["value"],
                key=f"env_value_{idx}",
                placeholder="my-value",
            )
        with cols[2]:
            if st.button("🗑", key=f"env_del_{idx}", help="Delete this row"):
                to_delete_index = idx

    # Handle deletion (after loop to avoid index issues)
    if to_delete_index is not None:
        rows.pop(to_delete_index)
        if not rows:
            rows.append({"key": "", "value": ""})
        st.session_state.env_rows = rows
        st.rerun()

    # Add / Save controls
    col_add, col_save = st.columns(2)
    with col_add:
        if st.button("➕ Add row"):
            rows.append({"key": "", "value": ""})
            st.session_state.env_rows = rows
            st.rerun()

    with col_save:
        if st.button("💾 Save to .env"):
            try:
                _save_env_file(rows)
                st.success(f"Saved {len([r for r in rows if r['key'].strip()])} entries to {ENV_FILE}")
            except Exception as e:
                st.error(f"Failed to save .env file: {e}")
