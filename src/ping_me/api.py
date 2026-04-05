"""Public Python API for ping-me."""

from __future__ import annotations

import sys
import os

from ping_me import cli


def notify(
    message: str,
    *,
    status: str = cli.PROGRESS_EVENT,
    job_name: str | None = None,
    command: list[str] | None = None,
    return_code: int | None = None,
    runtime: float | None = None,
) -> None:
    """Send a ping-me notification from Python code."""
    resolved_job_name = cli.resolve_job_name(job_name)
    inherited_parent_command = os.environ.get(cli.PING_ME_PARENT_COMMAND)
    if command is not None:
        command_for_message = command
    elif inherited_parent_command:
        command_for_message = [inherited_parent_command]
    else:
        command_for_message = [sys.executable, "-c", "..."]
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
