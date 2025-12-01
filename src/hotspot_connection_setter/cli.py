# src/hotspot_connection_setter/cli.py

import argparse
import pathlib
import subprocess
import sys


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run the Hotspot Connection Streamlit UI."
    )
    parser.add_argument(
        "-p",
        "--port",
        type=int,
        default=8050,
        help="Port for the Streamlit server (default: 8050)",
    )
    parser.add_argument(
        "-a",
        "--address",
        default="0.0.0.0",
        help='Address for the Streamlit server (default: "0.0.0.0")',
    )

    # Anything after `--` will be forwarded to streamlit directly
    args, extra = parser.parse_known_args()

    # Path to app.py next to this file
    app_path = pathlib.Path(__file__).with_name("app.py")

    cmd = [
        sys.executable,
        "-m",
        "streamlit",
        "run",
        str(app_path),
        "--server.port",
        str(args.port),
        "--server.address",
        args.address,
    ]

    # Forward extra args to Streamlit if user wants
    cmd.extend(extra)

    # Replace current process with streamlit (or use subprocess.run if you prefer)
    raise SystemExit(subprocess.call(cmd))
