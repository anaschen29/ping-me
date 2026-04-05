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
PING_ME_CONTEXT_ACTIVE = "PING_ME_CONTEXT_ACTIVE"
PING_ME_JOB_NAME = "PING_ME_JOB_NAME"
PING_ME_PARENT_COMMAND = "PING_ME_PARENT_COMMAND"
TERMINAL_EVENTS = {"success", "failure", "interrupt"}
PROGRESS_EVENT = "notify_progress"


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
    normalized_event = normalize_event(event)
    selected = {normalize_event(item.strip()) for item in raw.split(",") if item.strip()}
    if normalized_event in selected:
        return True
    if "terminal" in selected and event in TERMINAL_EVENTS:
        return True
    return False


def normalize_event(event: str) -> str:
    """Map legacy event aliases to canonical event names."""
    aliases = {"info": PROGRESS_EVENT, "progress": PROGRESS_EVENT}
    return aliases.get(event, event)


def validate_required_credentials() -> str | None:
    """Return an error message when required notification credentials are missing."""
    token = os.getenv("PING_ME_PUSHOVER_TOKEN")
    user = os.getenv("PING_ME_PUSHOVER_USER")
    if token and user:
        return None
    return "missing PING_ME_PUSHOVER_TOKEN or PING_ME_PUSHOVER_USER. Please set those environment variables!!"


def send_notification(
    event: str,
    command: list[str] | None,
    return_code: int | None,
    runtime: float | None,
    job_name: str | None = None,
    detail_message: str | None = None,
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

    normalized_event = normalize_event(event)
    status_labels = {
        "success": "✅ Succeeded",
        "failure": "❌ Failed",
        "interrupt": "⚠️ Interrupted",
        PROGRESS_EVENT: "🔄 In Progress",
        "warning": "⚠️ Warning",
    }
    status = status_labels.get(normalized_event, normalized_event)
    title = os.getenv("PING_ME_TITLE") or "ping-me"
    hostname = os.getenv("PING_ME_DEVICE_NAME") or socket.gethostname()
    command_text = " ".join(command) if command else "(none)"
    status_line = f"{job_name} {status}" if job_name else status
    message_lines = [status_line, f"Host: {hostname}"]
    if runtime is not None:
        message_lines.append(f"Runtime: {format_runtime(runtime)}")
    if return_code is not None:
        message_lines.append(f"Exit code: {return_code}")
    message_lines.append(f"Command: {command_text}")
    if detail_message:
        message_lines.append(f"Message: {detail_message}")
    message = "\n".join(message_lines)

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


def resolve_job_name(explicit_job_name: str | None = None) -> str | None:
    """Resolve job name from explicit argument first, then inherited env context."""
    if explicit_job_name:
        return explicit_job_name
    inherited = os.getenv(PING_ME_JOB_NAME)
    if inherited:
        return inherited
    return None


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
        child_env = os.environ.copy()
        child_env[PING_ME_CONTEXT_ACTIVE] = "1"
        child_env[PING_ME_PARENT_COMMAND] = " ".join(command)
        resolved_job_name = resolve_job_name(job_name)
        if resolved_job_name:
            child_env[PING_ME_JOB_NAME] = resolved_job_name
        result = subprocess.run(command, shell=False, env=child_env)
        return_code = result.returncode
        event = "success" if return_code == 0 else "failure"
    except KeyboardInterrupt:
        return_code = 130
        event = "interrupt"

    runtime = time.monotonic() - start
    try:
        send_notification(event, command, return_code, runtime, job_name=resolve_job_name(job_name))
    except requests.RequestException as exc:
        print(f"ping-me: failed to send notification: {exc}", file=sys.stderr)

    return return_code


if __name__ == "__main__":
    raise SystemExit(main())
