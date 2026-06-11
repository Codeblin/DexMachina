"""Environment health checks."""

from __future__ import annotations

import sys
from dataclasses import dataclass
from typing import Callable

from rich.console import Console
from rich.panel import Panel

from droidforge.banner import doctor_table
from droidforge.config import get_pinned_version
from droidforge.progress import work_progress
from droidforge.device import check_frida_server_running, get_local_frida_version, list_devices
from droidforge.installer import get_tool_version
from droidforge.registry import FRIDA_PIN_GROUP, TOOLS, get_tool
from droidforge.utils import parse_version, run_cmd, versions_match, which

console = Console()


@dataclass
class CheckResult:
    name: str
    status: str  # ok, warn, fail, info
    message: str
    fix: str | None = None
    fix_tool: str | None = None  # registry tool name for reinstall actions
    automated: bool = True  # False = manual-only (Java, Node, Python upgrade)


def check_python() -> CheckResult:
    v = sys.version_info
    if v >= (3, 10):
        return CheckResult("Python", "ok", f"{v.major}.{v.minor}.{v.micro}")
    return CheckResult(
        "Python",
        "fail",
        f"{v.major}.{v.minor}.{v.micro} — requires 3.10+",
        "Upgrade Python to 3.10 or newer",
        automated=False,
    )


def check_java() -> CheckResult:
    if not which("java"):
        return CheckResult(
            "Java",
            "warn",
            "Not found — required for jadx, apktool, uber-apk-signer",
            "Install JDK 11+ and set java_path in droidforge.toml",
            automated=False,
        )
    result = run_cmd("java -version")
    combined = (result.stderr or "") + (result.stdout or "")
    ver = parse_version(combined)
    return CheckResult("Java", "ok", ver or combined.strip().split("\n")[0])


def check_adb(config: dict) -> CheckResult:
    adb = config.get("settings", {}).get("adb_path", "adb")
    if not which(adb) and not which("adb"):
        return CheckResult(
            "ADB",
            "fail",
            "Not found in PATH",
            "droidforge install adb",
        )
    try:
        devices = list_devices(config)
        if devices:
            return CheckResult("ADB", "ok", f"Available — {len(devices)} device(s) connected")
        return CheckResult(
            "ADB",
            "warn",
            "Available but no devices connected",
            "Connect a device with USB debugging enabled",
            automated=False,
        )
    except Exception as e:
        return CheckResult("ADB", "fail", str(e), "droidforge install adb")


def check_nodejs() -> CheckResult:
    if not which("node"):
        return CheckResult(
            "Node.js",
            "warn",
            "Not found — required for apk-mitm",
            "Install Node.js from https://nodejs.org/",
            automated=False,
        )
    result = run_cmd("node --version")
    ver = parse_version(result.stdout or "")
    return CheckResult("Node.js", "ok", ver or (result.stdout or "").strip())


def check_frida_pin_group(config: dict) -> CheckResult:
    from droidforge.registry import FRIDA_PIN_GROUP
    from droidforge.versions import FRIDA_COMPANIONS, FRIDA_EXACT

    frida_tool = get_tool("frida")
    frida_ver = get_tool_version(frida_tool)

    if not frida_ver:
        return CheckResult(
            "Frida pin group",
            "warn",
            "frida runtime not installed",
            "droidforge use latest   # or: droidforge install frida",
        )

    parts = [f"frida={frida_ver}"]
    missing: list[str] = []
    for name in FRIDA_PIN_GROUP:
        if name in FRIDA_EXACT or name not in FRIDA_COMPANIONS:
            if name == "frida":
                continue
            if name == "medusa":
                continue
            continue
        tool = get_tool(name)
        ver = get_tool_version(tool)
        if ver:
            parts.append(f"{name}={ver}")
        else:
            missing.append(name)

    pinned = get_pinned_version(config, "frida")
    active = config.get("active", {}).get("frida") if isinstance(config.get("active"), dict) else None

    if pinned and not versions_match(pinned, frida_ver):
        return CheckResult(
            "Frida pin group",
            "fail",
            f"Pinned frida {pinned} but runtime installed is {frida_ver} ({', '.join(parts)})",
            f"droidforge use {pinned}   # align runtime to pin",
        )

    if missing:
        return CheckResult(
            "Frida pin group",
            "warn",
            f"Runtime {frida_ver}; missing companions: {', '.join(missing)}",
            "droidforge sync frida   # or: droidforge use " + frida_ver,
        )

    msg = f"Runtime OK — {', '.join(parts)}"
    if active:
        msg += f" (active venv: {active})"
    if pinned:
        msg += f" (pinned: {pinned})"
    return CheckResult("Frida pin group", "ok", msg)


def check_frida_server_match(config: dict) -> CheckResult:
    try:
        devices = list_devices(config)
    except Exception:
        return CheckResult(
            "Frida server",
            "info",
            "Skipped — ADB not available",
        )

    if not devices:
        return CheckResult(
            "Frida server",
            "info",
            "Skipped — no device connected",
        )

    try:
        local = get_local_frida_version()
    except Exception as e:
        return CheckResult("Frida server", "warn", f"Local frida not installed: {e}")

    running = any(check_frida_server_running(config, d) for d in devices)
    if not running:
        return CheckResult(
            "Frida server",
            "warn",
            f"Not running on device (local frida: {local})",
            "droidforge push-server",
        )

    # Best-effort: if frida-ps works, versions likely match
    result = run_cmd("frida-ps -U")
    if result.returncode == 0:
        return CheckResult(
            "Frida server",
            "ok",
            f"Running on device, local frida {local}",
        )
    return CheckResult(
        "Frida server",
        "warn",
        f"Running but frida-ps failed — version mismatch likely (local: {local})",
        "droidforge push-server",
    )


def check_broken_installs(config: dict) -> list[CheckResult]:
    results: list[CheckResult] = []
    for name, tool in TOOLS.items():
        if tool.install_method == "manual":
            continue
        installed = get_tool_version(tool)
        if not installed:
            continue
        if tool.binary_name and not which(tool.binary_name):
            results.append(
                CheckResult(
                    tool.display_name,
                    "warn",
                    f"Registered version {installed} but binary '{tool.binary_name}' not in PATH",
                    f"Add install_dir/bin to PATH or reinstall: droidforge install {name}",
                    fix_tool=name,
                    automated=True,
                )
            )
    return results


def run_doctor(config: dict) -> list[CheckResult]:
    steps: list[tuple[str, Callable[[], CheckResult]]] = [
        ("Python", check_python),
        ("Java", check_java),
        ("ADB", lambda: check_adb(config)),
        ("Node.js", check_nodejs),
        ("Frida pin group", lambda: check_frida_pin_group(config)),
        ("Frida server", lambda: check_frida_server_match(config)),
    ]

    checks: list[CheckResult] = []
    with work_progress(
        "[cyan]Running health checks…[/]",
        total=len(steps) + 1,
        console=console,
    ) as (update, advance):
        for label, fn in steps:
            update(f"[cyan]Checking[/] [bold]{label}[/]…")
            checks.append(fn())
            advance()

        update("[cyan]Scanning for broken installs…[/]")
        checks.extend(check_broken_installs(config))
        advance()

    return checks


def print_doctor_report(config: dict) -> int:
    checks = run_doctor(config)
    table = doctor_table()

    status_style = {
        "ok": "[bold green]▣ PASS[/]",
        "warn": "[bold yellow]▲ WARN[/]",
        "fail": "[bold red]✗ FAIL[/]",
        "info": "[bold cyan]◉ INFO[/]",
    }

    failures = 0
    for c in checks:
        style = status_style.get(c.status, c.status)
        table.add_row(c.name, style, c.message)
        if c.status == "fail":
            failures += 1

    console.print(table)

    fixes = [c for c in checks if c.fix and c.status in ("fail", "warn")]
    if fixes:
        console.print()
        fix_text = "\n".join(
            f"[cyan]▸[/] [bold]{c.name}:[/] {c.fix}" for c in fixes
        )
        console.print(
            Panel(
                fix_text,
                title="[bold yellow]⚡ Suggested Fixes[/]",
                border_style="#3a6652",
                padding=(1, 2),
            )
        )

    if failures:
        console.print(f"\n[bold red]⚠ {failures} check(s) failed.[/]")
        return 1
    console.print("\n[bold green]◈ Environment looks healthy.[/]")
    return 0
