"""CLI for ping-me."""

from __future__ import annotations
import warnings
from urllib3.exceptions import NotOpenSSLWarning
warnings.filterwarnings("ignore", category=NotOpenSSLWarning)
import os
import socket
import subprocess
import sys
import time
from typing import Iterable


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


def validate_required_credentials() -> str | None:
    """Return an error message when required notification credentials are missing."""
    token = os.getenv("PING_ME_PUSHOVER_TOKEN")
    user = os.getenv("PING_ME_PUSHOVER_USER")
    if token and user:
        return None
    return "missing PING_ME_PUSHOVER_TOKEN or PING_ME_PUSHOVER_USER. Please set those environment variables!!"


def send_notification(
    event: str,
    command: list[str],
    return_code: int,
    runtime: float,
    job_name: str | None = None,
) -> None:
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
    hostname = os.getenv("PING_ME_DEVICE_NAME") or socket.gethostname()
    command_text = " ".join(command)
    status_line = f"Job {job_name}: {status}" if job_name else status
    message = (
        f"{status_line}\n"
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


def parse_args(argv: Iterable[str]) -> tuple[str | None, list[str]]:
    """Parse optional CLI flags and command list from argv."""
    args = list(argv)
    if "--" not in args:
        raise ValueError("missing required '--' separator")
    separator = args.index("--")

    option_args = args[:separator]
    job_name = None
    idx = 0
    while idx < len(option_args):
        arg = option_args[idx]
        if arg in {"--name", "-n"}:
            idx += 1
            if idx >= len(option_args):
                raise ValueError(f"missing value for '{arg}'")
            job_name = option_args[idx]
        elif arg.startswith("--name="):
            job_name = arg.split("=", 1)[1]
        else:
            raise ValueError(f"unknown option '{arg}'")
        idx += 1

    command = args[separator + 1 :]
    if not command:
        raise ValueError("missing command after '--'")
    return job_name, command


def main(argv: Iterable[str] | None = None) -> int:
    """CLI entrypoint."""
    raw_argv = list(sys.argv[1:] if argv is None else argv)
    try:
        job_name, command = parse_args(raw_argv)
    except ValueError as exc:
        print(f"ping-me: {exc}", file=sys.stderr)
        print("usage: ping-me [--name NAME|-n NAME] -- <command> [args ...]", file=sys.stderr)
        return 2

    credential_error = validate_required_credentials()
    if credential_error:
        print(f"ping-me: {credential_error}", file=sys.stderr)
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
        send_notification(event, command, return_code, runtime, job_name=job_name)
    except requests.RequestException as exc:
        print(f"ping-me: failed to send notification: {exc}", file=sys.stderr)

    return return_code


if __name__ == "__main__":
    raise SystemExit(main())
