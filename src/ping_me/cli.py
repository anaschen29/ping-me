"""CLI for ping-me."""

from __future__ import annotations

import os
import socket
import subprocess
import sys
import time
import warnings
from typing import Iterable

warnings.filterwarnings(
    "ignore",
    category=Warning,
    module=r"urllib3(\..*)?",
    message=r".*urllib3 v2 only supports OpenSSL.*",
)

import requests

PUSHOVER_URL = "https://api.pushover.net/1/messages.json"


def format_runtime(seconds: float) -> str:
    """Format elapsed time in a compact human-readable form."""
    whole = int(round(seconds))
    minutes, secs = divmod(whole, 60)
    hours, minutes = divmod(minutes, 60)
    if hours:
        return f"{hours}h {minutes}m {secs}s"
    if minutes:
        return f"{minutes}m {secs}s"
    return f"{secs}s"


def should_notify(event: str, setting: str | None) -> bool:
    """Return True when this event should trigger a notification."""
    raw = (setting or "all").strip().lower()
    if raw in {"", "all"}:
        return True
    if raw == "none":
        return False
    selected = {item.strip() for item in raw.split(",") if item.strip()}
    return event in selected


def send_notification(event: str, command: list[str], return_code: int, runtime: float) -> None:
    """Send a pushover message if configuration and settings allow it."""
    if not should_notify(event, os.getenv("PING_ME_NOTIFY")):
        return

    token = os.getenv("PING_ME_PUSHOVER_TOKEN")
    user = os.getenv("PING_ME_PUSHOVER_USER")
    if not token or not user:
        print(
            "ping-me: missing PING_ME_PUSHOVER_TOKEN or PING_ME_PUSHOVER_USER; skipping notification",
            file=sys.stderr,
        )
        return

    status_labels = {
        "success": "✅ Success",
        "failure": "❌ Failure",
        "interrupt": "⚠️ Interrupted",
    }
    status = status_labels.get(event, event)
    title = os.getenv("PING_ME_TITLE") or "ping-me"
    hostname = socket.gethostname()
    command_text = " ".join(command)
    message = (
        f"{status}\n"
        f"Host: {hostname}\n"
        f"Runtime: {format_runtime(runtime)}\n"
        f"Exit code: {return_code}\n"
        f"Command: {command_text}"
    )

    payload = {
        "token": token,
        "user": user,
        "title": title,
        "message": message,
    }
    response = requests.post(PUSHOVER_URL, data=payload, timeout=10)
    response.raise_for_status()


def parse_command(argv: Iterable[str]) -> list[str]:
    """Parse command list from argv, requiring a -- separator."""
    args = list(argv)
    if "--" not in args:
        raise ValueError("missing required '--' separator")
    separator = args.index("--")
    command = args[separator + 1 :]
    if not command:
        raise ValueError("missing command after '--'")
    return command


def main(argv: Iterable[str] | None = None) -> int:
    """CLI entrypoint."""
    raw_argv = list(sys.argv[1:] if argv is None else argv)
    try:
        command = parse_command(raw_argv)
    except ValueError as exc:
        print(f"ping-me: {exc}", file=sys.stderr)
        print("usage: ping-me -- <command> [args ...]", file=sys.stderr)
        return 2

    start = time.monotonic()
    event = "failure"
    return_code = 1
    try:
        result = subprocess.run(command, shell=False)
        return_code = result.returncode
        event = "success" if return_code == 0 else "failure"
    except KeyboardInterrupt:
        return_code = 130
        event = "interrupt"

    runtime = time.monotonic() - start
    try:
        send_notification(event, command, return_code, runtime)
    except requests.RequestException as exc:
        print(f"ping-me: failed to send notification: {exc}", file=sys.stderr)

    return return_code


if __name__ == "__main__":
    raise SystemExit(main())