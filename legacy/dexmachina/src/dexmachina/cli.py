"""Deprecated DexMachina CLI wrapper for PinDroid."""

from __future__ import annotations

import sys
from collections.abc import Sequence
from typing import Any

NOTICE = (
    "DexMachina has been renamed to PinDroid. "
    "Install and use the maintained package with: pip install pindroid"
)


def print_deprecation_notice() -> None:
    print(f"WARNING: {NOTICE}", file=sys.stderr)


def main(
    args: Sequence[str] | None = None,
    prog_name: str = "dexmachina",
    **extra: Any,
) -> Any:
    print_deprecation_notice()
    from pindroid.cli import main as pindroid_main

    return pindroid_main(args=args, prog_name=prog_name, **extra)
