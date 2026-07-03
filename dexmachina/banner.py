"""ASCII art banner and terminal theme for DexMachina."""

from __future__ import annotations

import os
from functools import wraps
from typing import Callable, TypeVar

from rich.align import Align
from rich.console import Console, Group, RenderableType
from rich.panel import Panel
from rich.rule import Rule
from rich.style import Style
from rich.table import Table
from rich.text import Text

from dexmachina import __version__

F = TypeVar("F", bound=Callable)

# ── Theme palette (classic hacker / Android pentest) ─────────────────────────
C_PRIMARY = "#00ff41"      # matrix green
C_SECONDARY = "#00d4ff"    # cyber cyan
C_ACCENT = "#ff0055"       # hot magenta
C_WARN = "#ffb000"         # amber
C_DIM = "#3a6652"          # muted green
C_GLOW = "#39ff14"         # neon

MACHINE_EYE = r"""
      .---------.
  .--' .-----. '--.
 /    / _____ \    \
|[::]| /     \ |[::]|
|----|<   X   >|----|
|[::]| \_____/ |[::]|
 \    \       /    /
  '--. '-----' .--'
      '---+---'
          V
"""

LOGO = r"""
  ____  _____ __  __
 |  _ \| ____|\ \/ /
 | | | |  _|   \  /
 | |_| | |___  /  \
 |____/|_____|/_/\_\

  __  __    _    ____ _   _ ___ _   _    _
 |  \/  |  / \  / ___| | | |_ _| \ | |  / \
 | |\/| | / _ \| |   | |_| || ||  \| | / _ \
 | |  | |/ ___ \ |___|  _  || || |\  |/ ___ \
 |_|  |_/_/   \_\____|_| |_|___|_| \_/_/   \_\
"""

CIRCUIT_FOOTER = (
    "[ adb ]---[ frida ]---[ jadx ]---[ objection ]---[ apktool ]"
)

TAGLINE = "ANDROID PENTEST ENVIRONMENT"


def banner_enabled() -> bool:
    val = os.environ.get("DEXMACHINA_NO_BANNER", "").lower()
    return val not in ("1", "true", "yes")


def _colorize_machine(art: str) -> Text:
    result = Text()
    lines = art.strip("\n").splitlines()
    for i, line in enumerate(lines):
        if i > 0:
            result.append("\n")
        for ch in line:
            if ch == "X":
                result.append(ch, style=Style(color=C_ACCENT, bold=True))
            elif ch in "<>V":
                result.append(ch, style=Style(color=C_WARN, bold=True))
            elif ch in "/\\_":
                result.append(ch, style=Style(color=C_SECONDARY, bold=True))
            elif ch in "|.-'+:[]":
                result.append(ch, style=Style(color=C_PRIMARY, bold=True))
            else:
                result.append(ch)
    return result


def _colorize_logo(art: str) -> Text:
    result = Text()
    lines = art.strip("\n").splitlines()
    for i, line in enumerate(lines):
        if i > 0:
            result.append("\n")
        if not line:
            continue
        color = C_SECONDARY if i < 5 else C_PRIMARY
        result.append(line, style=Style(color=color, bold=True))
    return result


def render_banner(*, compact: bool = False, version: str = __version__) -> RenderableType:
    if compact:
        line = Text()
        line.append("[::] ", style=Style(color=C_ACCENT, bold=True))
        line.append("DEX", style=Style(color=C_SECONDARY, bold=True))
        line.append("MACHINA", style=Style(color=C_PRIMARY, bold=True))
        line.append(f"  v{version}  ", style=Style(color=C_DIM))
        line.append("│", style=Style(color=C_DIM))
        line.append(" android pentest environment ", style=Style(color=C_GLOW, italic=True))
        return Panel(
            line,
            border_style=Style(color=C_DIM),
            padding=(0, 1),
        )

    hero = Table.grid(padding=(0, 3))
    hero.add_column(no_wrap=True)
    hero.add_column(no_wrap=True)
    hero.add_row(_colorize_machine(MACHINE_EYE), _colorize_logo(LOGO))
    hero_lockup = Align(hero, align="center")
    identity = Text(justify="center")
    identity.append(":: ", style=Style(color=C_ACCENT, bold=True))
    identity.append(TAGLINE, style=Style(color=C_GLOW, bold=True))
    identity.append(" ::", style=Style(color=C_ACCENT, bold=True))
    metadata = Text(justify="center")
    metadata.append(f"v{version}", style=Style(color=C_WARN, bold=True))
    metadata.append("  //  ", style=Style(color=C_DIM))
    metadata.append("DEX BYTECODE", style=Style(color=C_SECONDARY))
    metadata.append("  //  ", style=Style(color=C_DIM))
    metadata.append("MOBILE SECURITY", style=Style(color=C_PRIMARY))
    footer = Text(CIRCUIT_FOOTER, style=Style(color=C_DIM), justify="center")

    stack = Group(
        Panel(
            Group(hero_lockup, Text(""), identity, metadata, Text(""), footer),
            border_style=Style(color=C_PRIMARY),
            padding=(1, 2),
            title="[bold bright_green][ DEXMACHINA ][/]",
            title_align="center",
        ),
        Rule("[dim]environment online[/]", style=Style(color=C_DIM)),
    )
    return stack


def print_banner(console: Console | None = None, *, compact: bool = False) -> None:
    if not banner_enabled():
        return
    con = console or Console()
    con.print(render_banner(compact=compact))
    con.print()


def with_banner(*, compact: bool = True) -> Callable[[F], F]:
    """Decorator to print banner before a CLI command."""

    def decorator(fn: F) -> F:
        @wraps(fn)
        def wrapper(*args, **kwargs):
            print_banner(compact=compact)
            return fn(*args, **kwargs)

        return wrapper  # type: ignore[return-value]

    return decorator


# ── Shared table themes ───────────────────────────────────────────────────────

def status_table(title: str = "Tool Status") -> Table:
    table = Table(
        title=f"[bold bright_cyan]⚙ {title}[/]",
        title_style=Style(color=C_SECONDARY, bold=True),
        show_header=True,
        header_style=f"bold {C_PRIMARY}",
        border_style=C_DIM,
        row_styles=[Style(color="white"), Style(color=C_DIM)],
        show_lines=False,
        pad_edge=True,
    )
    table.add_column("Tool", style=f"bold {C_GLOW}")
    table.add_column("Category", style=C_SECONDARY)
    table.add_column("Installed", style="white")
    table.add_column("Latest", style=C_WARN)
    table.add_column("Status", justify="center")
    return table


def doctor_table() -> Table:
    table = Table(
        title="[bold]🩺 DexMachina Doctor[/]",
        title_style=Style(color=C_ACCENT, bold=True),
        show_header=True,
        header_style=f"bold {C_PRIMARY}",
        border_style=C_DIM,
    )
    table.add_column("Check", style=f"bold {C_SECONDARY}")
    table.add_column("Status", justify="center")
    table.add_column("Details", style="white")
    return table


def info_panel(title: str, content: str) -> Panel:
    return Panel(
        content,
        title=f"[bold {C_PRIMARY}]◈ {title}[/]",
        border_style=Style(color=C_SECONDARY),
        padding=(1, 2),
    )
