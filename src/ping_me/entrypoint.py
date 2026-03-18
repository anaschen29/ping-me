"""Console entrypoint for ping-me."""

from __future__ import annotations

import warnings
from typing import Iterable

warnings.filterwarnings(
    "ignore",
    category=Warning,
    message=r".*urllib3 v2 only supports OpenSSL.*",
)


def main(argv: Iterable[str] | None = None) -> int:
    """Run the CLI after applying startup warning filters."""
    from ping_me.cli import main as cli_main

    return cli_main(argv)
