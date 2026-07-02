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

ROBOT = "\n".join(
    [
        r"                         ___________",
        r"                     .-'           '-.",
        r"                    /    .- .---. -.     \\",
        r"                   /   .'  _ _  '.    \\",
        r"                  /   /   (o o)   \    \\",
        r"                 ;   |      ^       |   ;",
        r"                 |    \     -     /    |",
        r"                 |     '.   ___  .'     |",
        r"                  \       '---'       /",
        r"                   \                 /",
        r"                    \   .-------.   /",
        r"                     '-.|       |.-'",
        r"                        |       |",
        r"                     ___|_______|___",
        r"                    /               \\",
    ]
)

LOGO = r"""
  ____   ____   ___  ____  _____ ____  ___  _____
 |  _ \ |  _ \ / _ \|  _ \|  ___/ ___|/ _ \| ____|
 | | | || |_) | | | | | | | |_ | |  _| | | |  _|
 | |_| ||  _ <| |_| | |_| |  _|| |_| | |_| | |___
 |____/ |_| \_\___/|____/|_|   \____|\___/|_____|
"""

FORGE_ANVIL = r"""
                              ╱╲
                             ╱  ╲
                            ╱ ▓▓ ╲
                           ╱ ▓▓▓▓ ╲
                          ╱________╲
                         │ ▓▓▓▓▓▓▓▓ │
                         │ ▓▓▓▓▓▓▓▓ │
                         └──────────┘
"""

CIRCUIT_FOOTER = (
    "  ◈ ─── ⟨ adb ⟩ ─── ⟨ frida ⟩ ─── ⟨ jadx ⟩ ─── "
    "⟨ objection ⟩ ─── ⟨ apktool ⟩ ─── ◈"
)

TAGLINE = "▸  Android Pentest Arsenal Manager  ◂"


def banner_enabled() -> bool:
    val = os.environ.get("DEXMACHINA_NO_BANNER", "").lower()
    return val not in ("1", "true", "yes")


def _blend_hex(a: str, b: str, t: float) -> str:
    """Linear interpolate between two #RRGGBB colors."""
    t = max(0.0, min(1.0, t))
    ar, ag, ab = int(a[1:3], 16), int(a[3:5], 16), int(a[5:7], 16)
    br, bg, bb = int(b[1:3], 16), int(b[3:5], 16), int(b[5:7], 16)
    r = int(ar + (br - ar) * t)
    g = int(ag + (bg - ag) * t)
    bl = int(ab + (bb - ab) * t)
    return f"#{r:02x}{g:02x}{bl:02x}"


def _colorize_robot(art: str) -> Text:
    lines = art.splitlines()
    result = Text()
    for i, line in enumerate(lines):
        if i > 0:
            result.append("\n")
        # Eyes pop magenta, body green gradient
        for j, ch in enumerate(line):
            if ch in "o":
                result.append(ch, style=Style(color=C_ACCENT, bold=True))
            elif ch in "()":
                result.append(ch, style=Style(color=C_SECONDARY))
            elif ch in "_-|/\\;'":
                result.append(ch, style=Style(color=C_DIM))
            elif ch in "^":
                result.append(ch, style=Style(color=C_WARN))
            elif ch.strip():
                result.append(ch, style=Style(color=C_PRIMARY))
            else:
                result.append(ch)
    return result


def _colorize_logo(art: str) -> Text:
    result = Text()
    lines = [ln for ln in art.splitlines() if ln.strip()]
    for i, line in enumerate(lines):
        if i > 0:
            result.append("\n")
        for j, ch in enumerate(line):
            if ch in "|\\/_":
                result.append(ch, style=Style(color=C_DIM))
            elif ch.isupper() or ch in "DRFGEOI":
                result.append(ch, style=Style(color=C_PRIMARY, bold=True))
            elif ch.islower():
                result.append(ch, style=Style(color=C_SECONDARY))
            else:
                result.append(ch, style=Style(color=_blend_hex(C_SECONDARY, C_PRIMARY, i / max(len(lines) - 1, 1))))
    return result


def _colorize_anvil(art: str) -> Text:
    result = Text()
    for i, line in enumerate(art.splitlines()):
        if i > 0:
            result.append("\n")
        for ch in line:
            if ch == "▓":
                result.append(ch, style=Style(color=C_WARN, bold=True))
            elif ch in "╱╲_│└┘─":
                result.append(ch, style=Style(color=C_DIM))
            else:
                result.append(ch, style=Style(color=C_SECONDARY))
    return result


def render_banner(*, compact: bool = False, version: str = __version__) -> RenderableType:
    if compact:
        line = Text()
        line.append("◆ ", style=Style(color=C_ACCENT, bold=True))
        line.append("DROID", style=Style(color=C_SECONDARY, bold=True))
        line.append("FORGE", style=Style(color=C_PRIMARY, bold=True))
        line.append(f"  v{version}  ", style=Style(color=C_DIM))
        line.append("│", style=Style(color=C_DIM))
        line.append(" android pentest arsenal ", style=Style(color=C_GLOW, italic=True))
        return Panel(
            line,
            border_style=Style(color=C_DIM),
            padding=(0, 1),
        )

    robot = Align(_colorize_robot(ROBOT), align="center")
    logo = Align(_colorize_logo(LOGO), align="center")
    anvil = Align(_colorize_anvil(FORGE_ANVIL), align="center")
    version_txt = Align(
        Text(f" v{version} ", style=Style(color=C_WARN, bold=True)),
        align="center",
    )
    footer = Align(Text(CIRCUIT_FOOTER, style=Style(color=C_DIM)), align="center")

    stack = Group(
        Panel(
            Group(robot, Text(""), logo),
            border_style=Style(color=C_PRIMARY),
            padding=(1, 2),
            title="[bold bright_green]⚡ DEXMACHINA ⚡[/]",
            title_align="center",
            subtitle=TAGLINE,
            subtitle_align="center",
        ),
        anvil,
        version_txt,
        Rule(style=Style(color=C_DIM)),
        footer,
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
