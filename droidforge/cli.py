"""Click CLI entrypoint for DroidForge."""

from __future__ import annotations

import sys

import click
from rich.console import Console
from rich.panel import Panel

from droidforge import __version__
from droidforge.banner import info_panel, print_banner, status_table
from droidforge.bypass import BypassError, list_recipes, run_bypass
from droidforge.config import (
    default_config_path,
    ensure_config,
    format_config_toml,
    load_config,
    pin_tool,
    save_config,
    set_config_value,
    unpin_tool,
)
from droidforge.device import push_frida_server
from droidforge.doctor import print_doctor_report
from droidforge.help_fmt import DroidForgeGroup
from droidforge.installer import (
    InstallError,
    get_latest_version,
    get_tool_status,
    get_tool_version,
    install_tools,
    sync_pin_group,
    update_pin_group,
    update_tool,
)
from droidforge.registry import (
    FRIDA_PIN_GROUP,
    TOOLS,
    get_pin_group,
    get_tool,
    list_tools,
    resolve_install_order,
)
from droidforge.progress import work_progress, work_spinner
from droidforge.runtime import (
    RunError,
    format_arsenal_row,
    list_runnable_tools,
    lookup_invocation,
    run_invocation,
)
from droidforge.utils import human_category
from droidforge.versions import (
    PinGroupSyncError,
    env_shell_hint,
    print_sync_error,
    print_versions_report,
    resolve_frida_target,
    use_frida_version,
)

console = Console()


def _resolve_tool_name(name: str) -> str | None:
    """Exact or case-insensitive registry lookup."""
    if name in TOOLS:
        return name
    lower = name.lower()
    for key in TOOLS:
        if key.lower() == lower:
            return key
    return None


def _suggest_tools(name: str, limit: int = 5) -> list[str]:
    """Fuzzy suggestions for unknown tool names."""
    q = name.lower()
    scored: list[tuple[int, str]] = []
    for key, tool in TOOLS.items():
        hay = f"{key} {tool.display_name}".lower()
        if q in hay:
            scored.append((0 if key.startswith(q) else 1, key))
    scored.sort(key=lambda x: (x[0], x[1]))
    return [k for _, k in scored[:limit]]


def _print_info_catalog(category: str | None) -> None:
    """List all registry tools when no tool name is given."""
    from rich.table import Table

    tools = list_tools(category)
    if not tools:
        console.print(f"[yellow]No tools in category:[/] {category}")
        console.print(
            "[dim]Categories:[/] dynamic_analysis, static_analysis, "
            "traffic_interception, device_adb, …"
        )
        return

    table = Table(
        title="[bold cyan]DroidForge Tool Catalog[/]",
        show_header=True,
        header_style="bold #00ff41",
        border_style="#3a6652",
    )
    table.add_column("Name", style="bold #39ff14")
    table.add_column("Display name")
    table.add_column("Category")
    table.add_column("Install")

    for t in tools:
        table.add_row(t.name, t.display_name, human_category(t.category), t.install_method)

    console.print(table)
    console.print(
        f"\n[dim]{len(tools)} tools — details:[/] [cyan]droidforge info <name>[/]  "
        f"[dim]e.g.[/] [cyan]droidforge info frida[/]"
    )


def _load_cfg() -> dict:
    ensure_config()
    return load_config()


@click.group(cls=DroidForgeGroup, invoke_without_command=True)
@click.pass_context
@click.version_option(__version__, prog_name="droidforge")
@click.option(
    "--no-banner",
    is_flag=True,
    default=False,
    help="Suppress ASCII banner (also: DROIDFORGE_NO_BANNER=1)",
)
def main(ctx: click.Context, no_banner: bool) -> None:
    """DroidForge — Android pentesting tool manager."""
    if no_banner:
        import os

        os.environ["DROIDFORGE_NO_BANNER"] = "1"

    if ctx.invoked_subcommand is None:
        print_banner(console, compact=False)
        click.echo(ctx.get_help())


@main.command()
@click.option("--category", "-c", default=None, help="Filter by category")
def status(category: str | None) -> None:
    """Show installed vs latest versions for all tools."""
    print_banner(console, compact=True)
    cfg = _load_cfg()
    tools = list_tools(category)

    table = status_table("DroidForge Tool Status")

    status_icons = {
        "ok": "[bold green]▣ OK[/]",
        "outdated": "[bold yellow]▲ OUTDATED[/]",
        "missing": "[bold red]✗ MISSING[/]",
        "pinned": "[bold blue]◉ PINNED[/]",
        "manual": "[dim cyan]▤ MANUAL[/]",
    }

    rows: list[tuple] = []
    with work_progress(
        "[cyan]Scanning tool registry…[/]",
        total=len(tools),
        console=console,
    ) as (update, advance):
        for tool in tools:
            update(f"[cyan]Checking[/] [bold]{tool.display_name}[/]…")
            info = get_tool_status(tool, cfg)
            icon = status_icons.get(info["status"], info["status"])
            rows.append(
                (
                    tool.display_name,
                    human_category(tool.category),
                    info["installed"] or "—",
                    info["latest"] or "—",
                    icon,
                )
            )
            advance()

    for row in rows:
        table.add_row(*row)

    console.print(table)

    # Frida pin group summary
    from droidforge.config import get_pinned_version
    from droidforge.versions import FRIDA_COMPANIONS, get_active_frida_version

    frida_ver = get_tool_version(get_tool("frida"))
    active = get_active_frida_version(cfg)
    pinned = get_pinned_version(cfg, "frida")

    if frida_ver:
        parts = [f"frida={frida_ver}"]
        for name in FRIDA_COMPANIONS:
            v = get_tool_version(get_tool(name))
            if v:
                parts.append(f"{name}={v}")
        line = ", ".join(parts)
        extras = []
        if active:
            extras.append(f"active venv [bold]{active}[/]")
        if pinned:
            extras.append(f"pinned [bold]{pinned}[/]")
        suffix = f" ({', '.join(extras)})" if extras else ""
        console.print(f"\n[bold green]◈ Frida stack:[/] {line}{suffix}")
        console.print(
            "  [dim]Switch runtime:[/] [cyan]droidforge use 17.11.0[/]  "
            "[dim]·[/]  [cyan]droidforge sync frida[/]  "
            "[dim]·[/]  [cyan]droidforge versions frida[/]"
        )
    else:
        console.print("\n[yellow]Frida not installed.[/] Try: [cyan]droidforge use latest[/]")


@main.command("install")
@click.argument("tool", required=False, default=None)
@click.option("--all", "install_all", is_flag=True, help="Install all registry tools")
@click.option("--version", "ver", default=None, help="Pin version for this install")
@click.option("--force", is_flag=True, help="Override pin group conflicts")
def install_cmd(tool: str | None, install_all: bool, ver: str | None, force: bool) -> None:
    """Install a tool and its dependencies."""
    print_banner(console, compact=True)
    cfg = _load_cfg()

    if install_all:
        names = [
            t.name
            for t in TOOLS.values()
            if t.install_method != "manual"
        ]
        names = [n for n in names if n not in cfg.get("ignored", {}).get("tools", [])]
        console.print(f"Installing {len(names)} tools in dependency order...")
        try:
            install_tools(names, cfg, force=force)
        except InstallError as e:
            console.print(f"[red]Error:[/] {e}")
            sys.exit(1)
        return

    if not tool:
        console.print("[red]Specify a tool name or use --all[/]")
        sys.exit(1)

    try:
        get_tool(tool)
    except KeyError:
        console.print(f"[red]Unknown tool:[/] {tool}")
        sys.exit(1)

    group = get_pin_group(tool)
    if ver and len(group) > 1 and not force:
        from droidforge.installer import check_pin_group_conflict

        conflicts = check_pin_group_conflict(tool, ver, cfg)
        if conflicts:
            console.print("[yellow]Warning:[/] This version may break the pin group:")
            for c in conflicts:
                console.print(f"  • {c}")
            console.print("Use [cyan]--force[/] to proceed anyway.")

    order = resolve_install_order([tool])
    console.print(f"Install order: {' → '.join(order)}")
    try:
        install_tools([tool], cfg, version=ver, force=force)
    except InstallError as e:
        console.print(f"[red]Error:[/] {e}")
        sys.exit(1)


@main.command("update")
@click.argument("tool", required=False, default=None)
@click.option("--all", "update_all", is_flag=True, help="Update all tools")
@click.option("--force", is_flag=True, help="Force update even if pin group fails partially")
def update_cmd(tool: str | None, update_all: bool, force: bool) -> None:
    """Update tool(s) to latest versions."""
    print_banner(console, compact=True)
    cfg = _load_cfg()

    if update_all:
        names = [
            t.name
            for t in TOOLS.values()
            if t.install_method not in ("manual",)
        ]
        updated = []
        processed_pin_groups: set[frozenset[str]] = set()
        order = [
            name
            for name in resolve_install_order(names)
            if get_tool(name).install_method != "manual"
        ]
        with work_progress(
            "[cyan]Updating tools…[/]",
            total=len(order),
            console=console,
        ) as (update, advance):
            for name in order:
                t = get_tool(name)
                update(f"[cyan]Updating[/] [bold]{t.display_name}[/]…")
                if t.pin_with:
                    group_key = frozenset(get_pin_group(name))
                    if group_key in processed_pin_groups:
                        advance()
                        continue
                    processed_pin_groups.add(group_key)
                    try:
                        results = update_pin_group(name, cfg, force=force)
                        for n, old, new in results:
                            if old != new:
                                updated.append(f"{n} {old or '?'} → {new}")
                    except InstallError as e:
                        console.print(f"[yellow]Skipped pin group ({name}):[/] {e}")
                    advance()
                    continue
                try:
                    old, new = update_tool(name, cfg, force=force)
                    if old != new:
                        updated.append(f"{name} {old or '?'} → {new}")
                except InstallError as e:
                    console.print(f"[yellow]Skipped {name}:[/] {e}")
                advance()
        if updated:
            console.print("[green]Updated:[/]")
            for line in updated:
                console.print(f"  • {line}")
        else:
            console.print("[dim]All tools up to date.[/]")
        return

    if not tool:
        console.print("[red]Specify a tool or use --all[/]")
        sys.exit(1)

    try:
        t = get_tool(tool)
    except KeyError:
        console.print(f"[red]Unknown tool:[/] {tool}")
        sys.exit(1)

    if t.pin_with:
        members = [m for m in get_pin_group(tool) if get_tool(m).install_method != "manual"]
        with work_spinner(f"[cyan]Resolving target frida runtime…[/]", console=console):
            target = resolve_frida_target(cfg, None)
        console.print(
            Panel(
                f"[bold]Target frida runtime:[/] {target}\n\n"
                "• [bold]frida[/] → installed at exactly this version\n"
                "• [bold]frida-tools, objection, r2frida[/] → upgraded to pip-compatible releases "
                "(they use [italic]different[/] version numbers)\n"
                "• [bold]medusa[/] → optional, best-effort\n\n"
                f"[dim]Members:[/] {', '.join(members)}\n\n"
                "Prefer nvm-style venvs? Use [cyan]droidforge use {target}[/] instead.".format(
                    target=target
                ),
                title="Sync frida pin group",
                border_style="#3a6652",
            )
        )
        try:
            with work_spinner(f"[cyan]Syncing frida stack…[/]", console=console):
                results = sync_pin_group(tool, cfg, force=force)
            for n, old, new in results:
                if old == new:
                    console.print(f"[dim]–[/] {n}: already OK ({old or '—'})")
                else:
                    console.print(f"[green]✓[/] {n}: {old or '?'} → {new}")
        except PinGroupSyncError as e:
            print_sync_error(e)
            sys.exit(1)
        except InstallError as e:
            console.print(f"[red]Error:[/] {e}")
            sys.exit(1)
    else:
        try:
            with work_spinner(f"[cyan]Updating[/] [bold]{tool}[/]…", console=console):
                old, new = update_tool(tool, cfg, force=force)
            if old == new:
                console.print(f"[dim]{tool} already at latest ({old})[/]")
            else:
                console.print(f"[green]✓[/] {tool}: {old or '?'} → {new}")
        except InstallError as e:
            console.print(f"[red]Error:[/] {e}")
            sys.exit(1)


@main.command("sync")
@click.argument("tool", default="frida")
@click.option("--version", "ver", default=None, help="Frida runtime version (default: pin or latest)")
@click.option("--force", is_flag=True, help="Reinstall even if frida runtime already matches")
def sync_cmd(tool: str, ver: str | None, force: bool) -> None:
    """Sync a pin group to a frida runtime version (+ compatible companions)."""
    print_banner(console, compact=True)
    try:
        t = get_tool(tool)
    except KeyError:
        console.print(f"[red]Unknown tool:[/] {tool}")
        sys.exit(1)
    if not t.pin_with:
        console.print(f"[red]{tool} is not part of a pin group. Use update instead.[/]")
        sys.exit(1)
    cfg = _load_cfg()
    target = resolve_frida_target(cfg, ver)
    console.print(f"[bold]Syncing[/] frida pin group to runtime [cyan]{target}[/]")
    try:
        with work_spinner("[cyan]Syncing…[/]", console=console):
            results = sync_pin_group(tool, cfg, target_frida=ver, force=force)
        for n, old, new in results:
            if old == new:
                console.print(f"[dim]–[/] {n}: {old or '—'}")
            else:
                console.print(f"[green]✓[/] {n}: {old or '?'} → {new}")
    except PinGroupSyncError as e:
        print_sync_error(e)
        sys.exit(1)


@main.command("use")
@click.argument("version")
@click.option("--force", is_flag=True, help="Recreate venv and reinstall")
@click.option("--no-pin", is_flag=True, help="Do not write version to [pins] in config")
def use_cmd(version: str, force: bool, no_pin: bool) -> None:
    """Select frida runtime version (like nvm use) — isolated venv per version."""
    print_banner(console, compact=True)
    cfg = _load_cfg()
    try:
        with work_spinner(f"[cyan]Setting up frida {version}…[/]", console=console):
            venv = use_frida_version(cfg, version, force=force, pin=not no_pin)
    except PinGroupSyncError as e:
        print_sync_error(e)
        sys.exit(1)
    cfg = _load_cfg()
    from droidforge.versions import get_active_frida_version

    active = get_active_frida_version(cfg)
    console.print(f"\n[green]✓[/] Now using frida runtime [bold]{active}[/]")
    console.print(f"  venv: [dim]{venv}[/]")
    console.print(
        Panel(
            env_shell_hint(cfg),
            title="Add to your shell (so frida/objection use this venv)",
            border_style="#00ff41",
        )
    )
    console.print(
        "\n[dim]Device:[/] [cyan]droidforge push-server[/] after switching runtime"
    )


@main.command("versions")
@click.argument("tool", default="frida", required=False)
def versions_cmd(tool: str) -> None:
    """Show installed, pinned, active, and available versions."""
    print_banner(console, compact=True)
    if tool != "frida":
        console.print("[yellow]Only 'frida' pin group supported for now.[/]")
    cfg = _load_cfg()
    print_versions_report(cfg)


@main.command("env")
def env_cmd() -> None:
    """Print shell commands to activate the current frida venv."""
    cfg = _load_cfg()
    console.print(Panel(env_shell_hint(cfg), title="DroidForge environment", border_style="#3a6652"))


@main.command(
    "run",
    context_settings={
        "ignore_unknown_options": True,
        "allow_extra_args": True,
    },
)
@click.argument("tool")
@click.pass_context
def run_cmd(ctx: click.Context, tool: str) -> None:
    """Run a pentest tool through DroidForge (explicit dispatch).

    Pass tool flags after the tool name:

      droidforge run objection -g com.example.app explore

    Same as: droidforge objection -g com.example.app explore
    """
    cfg = _load_cfg()
    try:
        code = run_invocation(tool, list(ctx.args), cfg)
    except RunError as e:
        console.print(f"[red]{e}[/]")
        console.print("[dim]List runners:[/] [cyan]droidforge arsenal[/]")
        sys.exit(1)
    sys.exit(code)


@main.command("arsenal")
def arsenal_cmd() -> None:
    """List all tool CLIs available through droidforge (direct or via run)."""
    from rich.table import Table

    print_banner(console, compact=True)
    cfg = _load_cfg()
    invocations = list_runnable_tools()

    table = Table(
        title="[bold red]⚔ DroidForge Arsenal[/] — runnable CLIs",
        header_style="bold #00ff41",
        border_style="#3a6652",
    )
    table.add_column("Command", style="bold #39ff14")
    table.add_column("Registry tool")
    table.add_column("Status")
    table.add_column("Example")

    for inv in invocations:
        _, _, status = format_arsenal_row(inv, cfg)
        example = inv.usage_hint or f"droidforge {inv.name} --help"
        table.add_row(
            inv.name,
            inv.tool.name,
            status,
            example,
        )

    console.print(table)
    console.print(
        f"\n[dim]{len(invocations)} dispatchers · "
        "invoke directly: [cyan]droidforge frida --version[/]  "
        "or: [cyan]droidforge run objection explore[/]"
    )


def _bypass_options(func):
    """Shared options for bypass subcommands."""
    func = click.option(
        "-n",
        "--name",
        "package",
        required=False,
        default=None,
        help="Package identifier from frida-ps -Uai (Identifier column)",
    )(func)
    func = click.option(
        "-F",
        "--foremost",
        is_flag=True,
        help="Attach to the app currently open on screen (no package needed)",
    )(func)
    func = click.option(
        "-s",
        "--spawn",
        is_flag=True,
        help="Spawn the app (cold start). Auto-used if the app is not running.",
    )(func)
    func = click.option("-S", "--serial", default=None, help="ADB device serial")(func)
    func = click.option(
        "-N",
        "--network",
        is_flag=True,
        help="Connect to Frida over the network instead of USB",
    )(func)
    func = click.option(
        "--objection",
        "force_objection",
        is_flag=True,
        help="Force Objection (default when installed)",
    )(func)
    func = click.option(
        "--frida",
        "force_frida",
        is_flag=True,
        help="Force bundled Frida scripts instead of Objection",
    )(func)
    return func


def _resolve_bypass_engine(force_objection: bool, force_frida: bool) -> str:
    if force_objection and force_frida:
        raise click.ClickException("Use only one of --objection or --frida.")
    if force_objection:
        return "objection"
    if force_frida:
        return "frida"
    return "auto"


def _run_bypass_cmd(recipe_id: str, package: str | None, **kwargs) -> None:
    foremost = kwargs.get("foremost", False)
    if foremost and not package:
        package = ""
    elif not package:
        raise click.ClickException(
            "Missing -n / --name. List targets with: droidforge frida-ps -Uai\n"
            "Or use --foremost to hook the app on screen."
        )
    cfg = _load_cfg()
    engine = _resolve_bypass_engine(kwargs.pop("force_objection"), kwargs.pop("force_frida"))
    print_banner(console, compact=True)
    try:
        code = run_bypass(
            cfg,
            recipe_id,  # type: ignore[arg-type]
            package,
            engine=engine,  # type: ignore[arg-type]
            **kwargs,
        )
    except BypassError as e:
        console.print(f"[red]{e}[/]")
        sys.exit(1)
    sys.exit(code)


@main.group("bypass", invoke_without_command=True)
@_bypass_options
@click.pass_context
def bypass_group(
    ctx: click.Context,
    package: str | None,
    foremost: bool,
    spawn: bool,
    serial: str | None,
    network: bool,
    force_objection: bool,
    force_frida: bool,
) -> None:
    """Bypass presets — SSL pinning, root detection, or both.

    Uses Objection when available, otherwise bundled Frida scripts.
    Session stays open until you press Ctrl+C.

    \b
    Quick start (both bypasses — recommended):
      droidforge bypass -n com.example.app --spawn
      droidforge hook -n com.example.app --spawn
      droidforge bypass all -n com.example.app --spawn

    \b
    Individual bypasses:
      droidforge bypass ssl -n com.example.app
      droidforge bypass root -n com.example.app
    """
    if ctx.invoked_subcommand is not None:
        return

    if package is not None or foremost:
        _run_bypass_cmd(
            "all",
            package,
            spawn=spawn,
            serial=serial,
            network=network,
            force_objection=force_objection,
            force_frida=force_frida,
            foremost=foremost,
        )
        return

    from rich.table import Table

    print_banner(console, compact=True)
    table = Table(
        title="[bold cyan]DroidForge Bypass Presets[/]",
        header_style="bold #00ff41",
        border_style="#3a6652",
    )
    table.add_column("Command", style="bold #39ff14")
    table.add_column("What it does")
    for recipe in list_recipes():
        label = recipe.id
        if recipe.id == "all":
            label = "all / both  (default)"
        table.add_row(f"bypass {label}", recipe.summary)
    console.print(table)
    console.print(
        "\n[bold]Quick start (SSL + root):[/]\n"
        "  [cyan]droidforge bypass -n com.example.app --spawn[/]\n"
        "  [cyan]droidforge hook -n com.example.app --spawn[/]\n\n"
        "[dim]Requires frida-server:[/] [cyan]droidforge push-server[/]"
    )


@bypass_group.command("all")
@_bypass_options
def bypass_all(
    package: str | None,
    foremost: bool,
    spawn: bool,
    serial: str | None,
    network: bool,
    force_objection: bool,
    force_frida: bool,
) -> None:
    """SSL pinning + root detection bypass together (default test setup)."""
    _run_bypass_cmd(
        "all",
        package,
        spawn=spawn,
        serial=serial,
        network=network,
        force_objection=force_objection,
        force_frida=force_frida,
        foremost=foremost,
    )


@bypass_group.command("both")
@_bypass_options
def bypass_both(
    package: str | None,
    foremost: bool,
    spawn: bool,
    serial: str | None,
    network: bool,
    force_objection: bool,
    force_frida: bool,
) -> None:
    """Alias for bypass all — SSL + root detection bypass."""
    _run_bypass_cmd(
        "all",
        package,
        spawn=spawn,
        serial=serial,
        network=network,
        force_objection=force_objection,
        force_frida=force_frida,
        foremost=foremost,
    )


@main.command("hook")
@_bypass_options
def hook_cmd(
    package: str | None,
    foremost: bool,
    spawn: bool,
    serial: str | None,
    network: bool,
    force_objection: bool,
    force_frida: bool,
) -> None:
    """Start a test hook: SSL pinning + root detection bypass (shorthand).

    Same as: droidforge bypass -n <package> --spawn

    \b
    Examples:
      droidforge hook -n com.example.app --spawn
      droidforge hook --foremost
    """
    _run_bypass_cmd(
        "all",
        package,
        spawn=spawn,
        serial=serial,
        network=network,
        force_objection=force_objection,
        force_frida=force_frida,
        foremost=foremost,
    )


@bypass_group.command("ssl")
@_bypass_options
def bypass_ssl(
    package: str | None,
    foremost: bool,
    spawn: bool,
    serial: str | None,
    network: bool,
    force_objection: bool,
    force_frida: bool,
) -> None:
    """Universal SSL / certificate pinning bypass."""
    _run_bypass_cmd(
        "ssl",
        package,
        spawn=spawn,
        serial=serial,
        network=network,
        force_objection=force_objection,
        force_frida=force_frida,
        foremost=foremost,
    )


@bypass_group.command("root")
@_bypass_options
def bypass_root(
    package: str | None,
    foremost: bool,
    spawn: bool,
    serial: str | None,
    network: bool,
    force_objection: bool,
    force_frida: bool,
) -> None:
    """Universal root-detection bypass (hide su / root checks from the app)."""
    _run_bypass_cmd(
        "root",
        package,
        spawn=spawn,
        serial=serial,
        network=network,
        force_objection=force_objection,
        force_frida=force_frida,
        foremost=foremost,
    )


@main.command("pin")
@click.argument("tool")
@click.argument("version")
def pin_cmd(tool: str, version: str) -> None:
    """Lock a tool (and its pin group) to a specific version."""
    try:
        get_tool(tool)
    except KeyError:
        console.print(f"[red]Unknown tool:[/] {tool}")
        sys.exit(1)

    cfg = _load_cfg()
    group = get_pin_group(tool)
    new_cfg = pin_tool(cfg, tool, version)
    path = save_config(new_cfg)
    console.print(f"[green]✓[/] Pinned frida [bold]runtime[/] to [bold]{version}[/]")
    console.print(
        "  [dim]Pin saves the version; install it with:[/] "
        f"[cyan]droidforge use {version}[/] or [cyan]droidforge sync frida[/]"
    )
    if len(group) > 1:
        console.print(f"  Companions (frida-tools, objection, …) follow automatically")
    console.print(f"  Config saved to {path}")


@main.command("unpin")
@click.argument("tool")
def unpin_cmd(tool: str) -> None:
    """Remove version lock for a tool."""
    try:
        get_tool(tool)
    except KeyError:
        console.print(f"[red]Unknown tool:[/] {tool}")
        sys.exit(1)

    cfg = _load_cfg()
    new_cfg = unpin_tool(cfg, tool)
    path = save_config(new_cfg)
    console.print(f"[green]✓[/] Unpinned {tool} (config: {path})")


@main.command("push-server")
@click.option("--device", "-d", default=None, help="ADB device serial")
@click.option("--no-start", is_flag=True, help="Do not start frida-server after push")
def push_server_cmd(device: str | None, no_start: bool) -> None:
    """Push matching frida-server binary to connected device(s)."""
    print_banner(console, compact=True)
    cfg = _load_cfg()
    try:
        push_frida_server(cfg, serial=device, start=not no_start)
    except Exception as e:
        console.print(f"[red]Error:[/] {e}")
        sys.exit(1)


@main.command("doctor")
def doctor_cmd() -> None:
    """Run environment health checks."""
    print_banner(console, compact=True)
    cfg = _load_cfg()
    code = print_doctor_report(cfg)
    sys.exit(code)


@main.command("fix")
@click.option("--dry-run", is_flag=True, help="Show fix plan without applying")
@click.option("--yes", "-y", is_flag=True, help="Apply fixes without confirmation")
@click.option(
    "--aggressive",
    is_flag=True,
    help="Also update all outdated tools (medium impact; slow, network-heavy)",
)
@click.option(
    "--bootstrap",
    is_flag=True,
    help="Install missing core pentest tools (adb, frida, jadx, apktool, …)",
)
@click.option(
    "--only",
    default=None,
    help="Comma-separated categories: frida,server,adb,reinstall,bootstrap,updates",
)
@click.option(
    "--no-legend",
    is_flag=True,
    help="Hide the impact-level explanation panel",
)
def fix_cmd(
    dry_run: bool,
    yes: bool,
    aggressive: bool,
    bootstrap: bool,
    only: str | None,
    no_legend: bool,
) -> None:
    """Diagnose and automatically repair common environment issues.

    Each planned fix shows an \bIMPACT level (low / medium / high) describing
    how disruptive the change is — not a security score. See the legend in the
    fix plan output, or run: droidforge fix --dry-run
    """
    print_banner(console, compact=True)
    cfg = _load_cfg()
    only_set = None
    if only:
        only_set = {c.strip() for c in only.split(",") if c.strip()}
        unknown = only_set - {"frida", "server", "adb", "reinstall", "bootstrap", "updates", "missing"}
        if unknown:
            console.print(f"[red]Unknown fix categories:[/] {', '.join(sorted(unknown))}")
            sys.exit(1)
    code = run_fix(
        cfg,
        dry_run=dry_run,
        yes=yes,
        aggressive=aggressive,
        bootstrap=bootstrap,
        only=only_set,
        show_legend=not no_legend,
    )
    sys.exit(code)


@main.command("info")
@click.argument("tool", required=False, default=None)
@click.option("--category", "-c", default=None, help="Filter catalog by category")
def info_cmd(tool: str | None, category: str | None) -> None:
    """Show detailed information about a tool (or list all tools)."""
    print_banner(console, compact=True)

    if not tool:
        _print_info_catalog(category)
        return

    # Allow partial match: "jadx" matches, or suggest close names
    resolved = _resolve_tool_name(tool)
    if resolved is None:
        console.print(f"[red]Unknown tool:[/] {tool}")
        suggestions = _suggest_tools(tool)
        if suggestions:
            console.print("[dim]Did you mean:[/] " + ", ".join(f"[cyan]{s}[/]" for s in suggestions))
        console.print("\n[dim]List all tools:[/] [cyan]droidforge info[/]")
        sys.exit(1)

    t = get_tool(resolved)
    cfg = _load_cfg()
    installed = get_tool_version(t)
    with work_spinner(f"[cyan]Fetching release info for[/] [bold]{resolved}[/]…", console=console):
        latest = get_latest_version(t)
    pinned = cfg.get("pins", {}).get("frida") if t.pin_with else cfg.get("pins", {}).get(t.name)

    lines = [
        f"[bold]{t.display_name}[/] ({t.name})",
        f"Category: {human_category(t.category)}",
        f"Install method: {t.install_method}",
    ]
    if t.description:
        lines.append(f"Description: {t.description}")
    if t.pip_package:
        lines.append(f"pip package: {t.pip_package}")
    if t.github_repo:
        lines.append(f"GitHub: https://github.com/{t.github_repo}")
    if t.manual_url:
        lines.append(f"URL: {t.manual_url}")
    if t.depends_on:
        lines.append(f"Depends on: {', '.join(t.depends_on)}")
    if t.pin_with:
        lines.append(f"Pin group: {', '.join(t.pin_with)}")
    lines.append(f"Installed: {installed or '—'}")
    lines.append(f"Latest: {latest or '—'}")
    if pinned:
        lines.append(f"Pinned: {pinned}")
    if t.notes:
        lines.append(f"\n[bold yellow]Notes:[/] {t.notes}")

    console.print(info_panel(t.display_name, "\n".join(lines)))


@main.group("config", invoke_without_command=True)
@click.pass_context
def config_group(ctx: click.Context) -> None:
    """View or modify droidforge.toml."""
    if ctx.invoked_subcommand is None:
        path = ensure_config()
        cfg = load_config(path)
        console.print(Panel(format_config_toml(cfg), title=str(path)))


@config_group.command("show")
def config_show() -> None:
    """Print current configuration."""
    path = ensure_config()
    cfg = load_config(path)
    console.print(Panel(format_config_toml(cfg), title=str(path)))


@config_group.command("set")
@click.argument("key")
@click.argument("value")
def config_set(key: str, value: str) -> None:
    """Set a settings value."""
    cfg = _load_cfg()
    new_cfg = set_config_value(cfg, key, value)
    path = save_config(new_cfg)
    console.print(f"[green]✓[/] Set {key} = {value} ({path})")


@config_group.command("path")
def config_path_cmd() -> None:
    """Print config file path."""
    console.print(str(default_config_path()))


def _register_tool_runners() -> None:
    """Register each runnable tool as a top-level droidforge subcommand."""
    seen: set[str] = set()
    for inv in list_runnable_tools():
        if inv.name in seen:
            continue
        seen.add(inv.name)

        def make_tool_command(invocation_name: str, display: str):
            @click.command(
                name=invocation_name,
                add_help_option=False,
                context_settings={
                    "ignore_unknown_options": True,
                    "allow_extra_args": True,
                },
                help=inv.tool.description or f"Run {inv.tool.display_name}",
            )
            @click.pass_context
            def _tool_runner(ctx: click.Context) -> None:
                cfg = ensure_config()
                cfg_data = load_config(cfg)
                try:
                    code = run_invocation(
                        invocation_name,
                        list(ctx.args),
                        cfg_data,
                    )
                except RunError as e:
                    console.print(f"[red]{e}[/]")
                    sys.exit(1)
                sys.exit(code)

            return _tool_runner

        cmd = make_tool_command(inv.name, inv.tool.display_name)
        main.add_command(cmd)


_register_tool_runners()


if __name__ == "__main__":
    main()
