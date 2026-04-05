"""Public Python API for ping-me."""

from __future__ import annotations

import sys

from ping_me import cli


def notify(
    message: str,
    *,
    status: str = "info",
    job_name: str | None = None,
    command: list[str] | None = None,
    return_code: int | None = None,
    runtime: float | None = None,
) -> None:
    """Send a ping-me notification from Python code."""
    resolved_job_name = cli.resolve_job_name(job_name)
    command_for_message = command if command is not None else [sys.executable, "-c", "..."]
    try:
        cli.send_notification(
            status,
            command_for_message,
            return_code,
            runtime,
            job_name=resolved_job_name,
            detail_message=message,
        )
    except cli.requests.RequestException as exc:
        print(f"ping-me: failed to send notification: {exc}", file=sys.stderr)
