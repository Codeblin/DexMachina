"""Install and update logic per tool type."""

from __future__ import annotations

import os
import platform
import shutil
import stat
import sys
import tarfile
import tempfile
import zipfile
from pathlib import Path
from typing import Callable

import requests
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn, TimeElapsedColumn

from droidforge.config import get_pinned_version, install_dir
from droidforge.registry import Tool, get_pin_group, get_tool, resolve_install_order
from droidforge.utils import (
    compare_versions,
    detect_platform,
    detect_system_package_manager,
    extract_release_version,
    find_git,
    get_github_default_branch,
    get_installed_version,
    get_latest_github_release,
    github_headers,
    is_binary_available,
    npm_show_version,
    parse_version,
    pip_show_version,
    run_cmd,
    versions_match,
    which,
)

console = Console()


class InstallError(Exception):
    """Installation failed with a user-facing message."""


def get_tool_version(tool: Tool) -> str | None:
    """Get currently installed version for a tool."""
    if tool.install_method == "manual":
        return None

    if tool.install_method == "pip" and tool.pip_package:
        ver = pip_show_version(tool.pip_package)
        if ver:
            return ver

    if tool.install_method == "npm" and tool.npm_package:
        ver = npm_show_version(tool.npm_package)
        if ver:
            return ver

    if tool.version_cmd or tool.binary_name:
        return get_installed_version(tool.version_cmd, tool.binary_name)

    return None


def get_latest_version(tool: Tool) -> str | None:
    """Fetch latest available version."""
    if tool.install_method == "manual":
        return None

    if tool.install_method == "pip" and tool.pip_package:
        result = run_cmd([sys.executable, "-m", "pip", "index", "versions", tool.pip_package])
        if result.returncode == 0 and result.stdout:
            # "Available versions: 1.0, 2.0, ..."
            import re

            match = re.search(r"Available versions:\s*([^\n]+)", result.stdout)
            if match:
                versions = [v.strip() for v in match.group(1).split(",")]
                if versions:
                    return versions[0]
        # Fallback: pip install dry-run
        result = run_cmd(
            [sys.executable, "-m", "pip", "install", f"{tool.pip_package}==invalid"],
        )
        # Try PyPI JSON API
        try:
            resp = requests.get(
                f"https://pypi.org/pypi/{tool.pip_package}/json",
                timeout=15,
            )
            resp.raise_for_status()
            return resp.json()["info"]["version"]
        except (requests.RequestException, KeyError):
            return None

    if tool.github_repo:
        try:
            release = get_latest_github_release(tool.github_repo)
            return extract_release_version(release)
        except requests.RequestException:
            return None

    if tool.install_method == "npm" and tool.npm_package:
        result = run_cmd(f"npm view {tool.npm_package} version")
        if result.returncode == 0:
            return (result.stdout or "").strip()

    if tool.install_method in ("apt", "brew"):
        return None  # system package manager doesn't expose easy latest

    return None


def _pip_install(package: str, version: str | None, force: bool) -> None:
    spec = f"{package}=={version}" if version else package
    cmd = [sys.executable, "-m", "pip", "install", spec]
    if force:
        cmd.append("--force-reinstall")
    else:
        cmd.append("--upgrade")
    result = run_cmd(cmd)
    if result.returncode != 0:
        err = (result.stderr or result.stdout or "Unknown pip error").strip()
        raise InstallError(f"pip install failed for {package}:\n{err}")


def _pip_install_companion(package: str, force: bool) -> None:
    """Install/upgrade a pip package without pinning to frida's version number."""
    cmd = [sys.executable, "-m", "pip", "install", package, "--upgrade"]
    if force:
        cmd.append("--force-reinstall")
    result = run_cmd(cmd)
    if result.returncode != 0:
        err = (result.stderr or result.stdout or "Unknown pip error").strip()
        raise InstallError(f"pip install failed for {package}:\n{err}")


def _npm_install(package: str, version: str | None) -> None:
    spec = f"{package}@{version}" if version else package
    result = run_cmd(f"npm install -g {spec}")
    if result.returncode != 0:
        err = (result.stderr or result.stdout or "Unknown npm error").strip()
        raise InstallError(f"npm install failed for {package}:\n{err}")


def _apt_install(package: str) -> None:
    if not which("apt-get") and not which("apt"):
        raise InstallError("apt not found. Install manually or use a Debian/Ubuntu system.")
    try:
        is_root = os.geteuid() == 0  # type: ignore[attr-defined]
    except AttributeError:
        is_root = False
    sudo = "" if is_root else "sudo "
    result = run_cmd(f"{sudo}apt-get update && {sudo}apt-get install -y {package}")
    if result.returncode != 0:
        raise InstallError(f"apt install failed for {package}")


def _brew_install(package: str) -> None:
    if not which("brew"):
        raise InstallError("Homebrew not found.")
    result = run_cmd(f"brew install {package}")
    if result.returncode != 0:
        raise InstallError(f"brew install failed for {package}")


def _write_cli_wrapper(wrapper: Path, argv_prefix: list[str]) -> None:
    """Write a small launcher script into install_dir/.../bin/."""
    wrapper.parent.mkdir(parents=True, exist_ok=True)
    if detect_platform() == "windows":
        if not wrapper.suffix:
            wrapper = wrapper.with_suffix(".bat")
        parts = " ".join(f'"{p}"' if " " in p else p for p in argv_prefix)
        wrapper.write_text(f"@echo off\n{parts} %*\n", encoding="utf-8")
    else:
        parts = " ".join(f'"{p}"' if " " in p else p for p in argv_prefix)
        wrapper.write_text(f"#!/bin/sh\nexec {parts} \"$@\"\n", encoding="utf-8")
        wrapper.chmod(wrapper.stat().st_mode | stat.S_IEXEC)


def _write_medusa_launcher(inst: Path, bin_name: str) -> None:
    """Launcher that patches readline on Windows before starting medusa.py."""
    launcher = inst / "bin" / "medusa_launcher.py"
    launcher.parent.mkdir(parents=True, exist_ok=True)
    launcher.write_text(
        '''\
"""DroidForge Medusa launcher."""
from __future__ import annotations

import runpy
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

if sys.platform == "win32":
    from droidforge.shims.readline_win import install_readline_shim

    install_readline_shim()

sys.path.insert(0, str(ROOT))
runpy.run_path(str(ROOT / "medusa.py"), run_name="__main__")
''',
        encoding="utf-8",
    )
    wrapper = inst / "bin" / bin_name
    _write_cli_wrapper(wrapper, [sys.executable, str(launcher)])


def _finalize_python_repo_install(tool: Tool, inst: Path) -> None:
    """Install requirements and write bin/ wrapper for a cloned or zipped repo."""
    requirements = inst / "requirements.txt"
    if requirements.is_file():
        result = run_cmd([sys.executable, "-m", "pip", "install", "-r", str(requirements)])
        if result.returncode != 0:
            err = (result.stderr or result.stdout or "pip failed").strip()
            raise InstallError(f"Failed to install {tool.name} requirements:\n{err}")

    entry = inst / f"{tool.name}.py"
    if not entry.is_file():
        candidates = list(inst.glob("*.py"))
        entry = next((p for p in candidates if p.stem.lower() == tool.name), None)
        if not entry and candidates:
            entry = candidates[0]
    if not entry or not entry.is_file():
        raise InstallError(
            f"Could not find entry script in {inst}. "
            f"Source fetch ok — check repo layout manually."
        )

    bin_name = tool.binary_name or tool.name
    if tool.name == "medusa":
        _write_medusa_launcher(inst, bin_name)
    else:
        wrapper = inst / "bin" / bin_name
        _write_cli_wrapper(wrapper, [sys.executable, str(entry)])
    console.print(f"[green]✓[/] {tool.display_name} installed at {inst}")
    console.print(f"  Run: [cyan]droidforge {bin_name} --help[/]")
    if tool.name == "medusa" and detect_platform() == "windows":
        console.print(
            "[yellow]Note:[/] Medusa upstream lists limited functionality on Windows. "
            "Linux/macOS + rooted device is recommended."
        )


def _download_github_repo_zip(tool: Tool, inst: Path) -> None:
    """Fetch repo default branch as a zip (no git required)."""
    branch = get_github_default_branch(tool.github_repo or "")
    url = f"https://codeload.github.com/{tool.github_repo}/zip/refs/heads/{branch}"
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        zip_path = tmp_path / "source.zip"
        _download_file(url, zip_path)
        extract_root = tmp_path / "extract"
        extract_root.mkdir()
        with zipfile.ZipFile(zip_path) as zf:
            zf.extractall(extract_root)
        children = [p for p in extract_root.iterdir() if p.is_dir()]
        if len(children) != 1:
            raise InstallError(
                f"Unexpected GitHub zip layout for {tool.name} "
                f"({len(children)} top-level folders)."
            )
        if inst.exists():
            shutil.rmtree(inst)
        shutil.move(str(children[0]), str(inst))
    (inst / ".droidforge-source").write_text("zip\n", encoding="utf-8")


def _install_git_clone(tool: Tool, cfg: dict, *, force: bool = False) -> None:
    """Clone or download a GitHub repo into install_dir and create a bin wrapper."""
    if not tool.github_repo:
        raise InstallError(f"No git repo defined for {tool.name}")

    inst = install_dir(cfg) / tool.name
    git_exe = find_git()
    bin_name = tool.binary_name or tool.name
    wrapper_sh = inst / "bin" / bin_name
    wrapper_bat = wrapper_sh.with_suffix(".bat")
    already_installed = (
        wrapper_sh.is_file()
        or wrapper_bat.is_file()
        or (inst / ".git").is_dir()
        or (inst / ".droidforge-source").is_file()
    )

    if (inst / ".git").is_dir() and git_exe and not force:
        result = run_cmd([git_exe, "-C", str(inst), "pull", "--ff-only"])
        if result.returncode != 0:
            console.print("[yellow]git pull failed; continuing with existing clone[/]")
        _finalize_python_repo_install(tool, inst)
        return

    if already_installed and not force:
        if tool.name == "medusa":
            _write_medusa_launcher(inst, bin_name)
        console.print(f"[dim]{tool.display_name} already installed at {inst}[/]")
        return

    if inst.exists() and force:
        shutil.rmtree(inst)

    if git_exe:
        inst.parent.mkdir(parents=True, exist_ok=True)
        repo_url = f"https://github.com/{tool.github_repo}.git"
        result = run_cmd([git_exe, "clone", "--depth", "1", repo_url, str(inst)])
        if result.returncode != 0:
            err = (result.stderr or result.stdout or "git clone failed").strip()
            raise InstallError(f"git clone failed for {tool.name}:\n{err}")
        (inst / ".droidforge-source").write_text("git\n", encoding="utf-8")
    else:
        console.print(
            "[yellow]git not found — downloading GitHub source zip instead.[/]"
        )
        console.print(
            "[dim]For easier updates, install Git: "
            "https://git-scm.com/download/win[/]"
        )
        inst.parent.mkdir(parents=True, exist_ok=True)
        _download_github_repo_zip(tool, inst)

    _finalize_python_repo_install(tool, inst)


def _download_file(url: str, dest: Path, progress: Progress | None = None) -> None:
    resp = requests.get(url, headers=github_headers(), stream=True, timeout=120)
    resp.raise_for_status()
    total = int(resp.headers.get("content-length", 0))
    dest.parent.mkdir(parents=True, exist_ok=True)

    task = None
    if progress:
        task = progress.add_task(f"Downloading {dest.name}", total=total or None)

    with dest.open("wb") as f:
        for chunk in resp.iter_content(chunk_size=8192):
            if chunk:
                f.write(chunk)
                if progress and task is not None:
                    progress.update(task, advance=len(chunk))


def _find_asset(release: dict, pattern: str | None, version: str) -> dict | None:
    assets = release.get("assets", [])
    if pattern:
        name = pattern.replace("{version}", version.lstrip("v"))
        for asset in assets:
            if asset["name"] == name or name in asset["name"]:
                return asset
    # Heuristic: first zip/tar for platform
    plat = detect_platform()
    for asset in assets:
        n = asset["name"].lower()
        if plat == "windows" and n.endswith(".zip") and "win" in n:
            return asset
        if plat == "macos" and ("mac" in n or "darwin" in n) and (
            n.endswith(".zip") or n.endswith(".tar.gz")
        ):
            return asset
        if plat == "linux" and ("linux" in n or "ubuntu" in n) and (
            n.endswith(".zip") or n.endswith(".tar.gz")
        ):
            return asset
    for asset in assets:
        n = asset["name"].lower()
        if n.endswith(".zip") or n.endswith(".tar.gz") or n.endswith(".jar"):
            return asset
    return None


def _extract_archive(archive: Path, dest: Path) -> None:
    dest.mkdir(parents=True, exist_ok=True)
    name = archive.name.lower()
    if name.endswith(".zip"):
        with zipfile.ZipFile(archive, "r") as zf:
            zf.extractall(dest)
    elif name.endswith((".tar.gz", ".tgz")):
        with tarfile.open(archive, "r:gz") as tf:
            tf.extractall(dest)
    else:
        shutil.copy(archive, dest / archive.name)


def _install_github_release(
    tool: Tool,
    version: str | None,
    cfg: dict,
    progress: Progress | None = None,
) -> None:
    if not tool.github_repo:
        raise InstallError(f"No GitHub repo defined for {tool.name}")

    if version:
        url = f"https://api.github.com/repos/{tool.github_repo}/releases/tags/v{version.lstrip('v')}"
        try:
            release = requests.get(url, headers=github_headers(), timeout=30).json()
            if "message" in release:
                url = f"https://api.github.com/repos/{tool.github_repo}/releases/tags/{version}"
                release = requests.get(url, headers=github_headers(), timeout=30).json()
        except requests.RequestException as e:
            raise InstallError(f"Failed to fetch release {version} for {tool.name}: {e}") from e
        ver = version.lstrip("v")
    else:
        release = get_latest_github_release(tool.github_repo)
        ver = extract_release_version(release)

    asset = _find_asset(release, tool.github_asset_pattern, ver)
    inst = install_dir(cfg)
    tool_dir = inst / tool.name
    tool_dir.mkdir(parents=True, exist_ok=True)

    if asset:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            archive = tmp_path / asset["name"]
            _download_file(asset["browser_download_url"], archive, progress)
            extract_to = tool_dir / "extracted"
            if extract_to.exists():
                shutil.rmtree(extract_to)
            _extract_archive(archive, extract_to)
            _link_binaries(tool, extract_to, tool_dir)
    elif tool.name == "medusa":
        raise InstallError(
            "Medusa uses git install — run: droidforge install medusa"
        )
    else:
        raise InstallError(f"No suitable release asset found for {tool.name} v{ver}")


def _link_binaries(tool: Tool, extract_root: Path, tool_dir: Path) -> None:
    """Create wrapper scripts in tool_dir/bin for discovered binaries."""
    bin_dir = tool_dir / "bin"
    bin_dir.mkdir(exist_ok=True)

    if tool.binary_name:
        candidates = list(extract_root.rglob(tool.binary_name + "*"))
        candidates = [c for c in candidates if c.is_file()]
        if tool.binary_name.endswith(".jar") or any(c.suffix == ".jar" for c in candidates):
            jar = next((c for c in candidates if c.suffix == ".jar"), None)
            if not jar:
                jars = list(extract_root.rglob("*.jar"))
                jar = jars[0] if jars else None
            if jar:
                dest_jar = tool_dir / jar.name
                shutil.copy(jar, dest_jar)
                wrapper = bin_dir / tool.binary_name
                if detect_platform() == "windows":
                    wrapper = bin_dir / f"{tool.binary_name}.bat"
                    wrapper.write_text(
                        f'@echo off\njava -jar "{dest_jar}" %*\n',
                        encoding="utf-8",
                    )
                else:
                    wrapper.write_text(
                        f'#!/bin/sh\nexec java -jar "{dest_jar}" "$@"\n',
                        encoding="utf-8",
                    )
                    wrapper.chmod(wrapper.stat().st_mode | stat.S_IEXEC)
            return

        if candidates:
            src = candidates[0]
            dest = bin_dir / tool.binary_name
            if detect_platform() == "windows" and not src.suffix:
                dest = bin_dir / f"{tool.binary_name}.exe"
            shutil.copy(src, dest)
            if detect_platform() != "windows":
                dest.chmod(dest.stat().st_mode | stat.S_IEXEC)


def _install_system(tool: Tool) -> None:
    pm = detect_system_package_manager()
    pkg = tool.brew_package if pm == "brew" else tool.apt_package
    if not pkg:
        pkg = tool.apt_package or tool.brew_package
    if not pkg:
        raise InstallError(f"No system package defined for {tool.name}")
    if pm == "brew":
        _brew_install(pkg)
    elif pm == "apt":
        _apt_install(pkg)
    else:
        raise InstallError(
            f"No supported package manager for {tool.name}. "
            f"Install {pkg} manually."
        )


def install_tool(
    tool_name: str,
    cfg: dict,
    *,
    version: str | None = None,
    force: bool = False,
    progress: Progress | None = None,
) -> None:
    tool = get_tool(tool_name)

    if tool.install_method == "manual":
        url = tool.manual_url or "project website"
        raise InstallError(
            f"{tool.display_name} is manual-only. Download from: {url}\n"
            f"{tool.notes or ''}"
        )

    pinned = get_pinned_version(cfg, tool_name)
    target_version = version or pinned

    if tool.install_method == "pip" and tool.pip_package:
        if version and tool.name in {"frida-tools", "objection", "r2frida"}:
            # These packages do not share frida's version number on PyPI.
            _pip_install_companion(tool.pip_package, force)
        else:
            _pip_install(tool.pip_package, target_version, force)
        return

    if tool.install_method == "npm" and tool.npm_package:
        if not which("npm"):
            raise InstallError("Node.js/npm not found. Install Node.js first.")
        _npm_install(tool.npm_package, target_version)
        return

    if tool.install_method == "github_release":
        _install_github_release(tool, target_version, cfg, progress)
        return

    if tool.install_method == "git":
        _install_git_clone(tool, cfg, force=force)
        return

    if tool.install_method in ("apt", "brew"):
        _install_system(tool)
        return

    raise InstallError(f"Unsupported install method '{tool.install_method}' for {tool.name}")


def check_pin_group_conflict(
    tool_name: str,
    target_version: str,
    cfg: dict,
) -> list[str]:
    """Return warning messages if target_version breaks pin group sync."""
    warnings: list[str] = []
    group = get_pin_group(tool_name)
    if len(group) <= 1:
        return warnings

    for member in group:
        if member == tool_name:
            continue
        member_tool = get_tool(member)
        installed = get_tool_version(member_tool)
        pinned = get_pinned_version(cfg, member)
        expected = pinned or installed
        if expected and not force_version_match(target_version, expected):
            warnings.append(
                f"{member} is at {expected}, would conflict with {tool_name}@{target_version}"
            )
    return warnings


def force_version_match(a: str, b: str) -> bool:
    from droidforge.utils import versions_match

    return versions_match(a, b)


def install_tools(
    tool_names: list[str],
    cfg: dict,
    *,
    version: str | None = None,
    force: bool = False,
    on_progress: Callable[[str], None] | None = None,
) -> None:
    order = resolve_install_order(tool_names)

    with Progress(
        SpinnerColumn(style="bright_green"),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(bar_width=28, style="#3a6652", complete_style="#00ff41"),
        TaskProgressColumn(),
        TimeElapsedColumn(),
        console=console,
        transient=True,
    ) as progress:
        task = progress.add_task("[cyan]Preparing install…[/]", total=len(order))
        for name in order:
            tool = get_tool(name)
            if tool.install_method == "manual":
                console.print(f"[dim]Skipping manual tool: {tool.display_name}[/]")
                progress.advance(task)
                continue

            pinned = get_pinned_version(cfg, name)
            from droidforge.versions import FRIDA_EXACT

            in_group = name in get_pin_group(tool_names[0])
            if name in FRIDA_EXACT and in_group:
                ver = version if version else pinned
            elif name in FRIDA_EXACT:
                ver = version or pinned
            else:
                ver = version if not in_group else None

            if not force and ver:
                conflicts = check_pin_group_conflict(name, ver, cfg)
                if conflicts:
                    raise InstallError(
                        "Pin group version conflict detected:\n"
                        + "\n".join(f"  • {w}" for w in conflicts)
                        + "\n\nUse --force to override or pin the group with: "
                        f"droidforge pin {name} {ver}"
                    )

            desc = f"[cyan]Installing[/] [bold]{tool.display_name}[/]" + (f" [yellow]@{ver}[/]" if ver else "")
            progress.update(task, description=desc)
            if on_progress:
                on_progress(name)

            try:
                install_tool(name, cfg, version=ver, force=force, progress=progress)
                console.print(f"[green]✓[/] Installed {tool.display_name}")
            except InstallError as e:
                console.print(f"[red]✗[/] {tool.display_name}: {e}")
                if not force:
                    raise
            progress.advance(task)


def update_tool(
    tool_name: str,
    cfg: dict,
    *,
    force: bool = False,
) -> tuple[str | None, str | None]:
    """Update tool; returns (old_version, new_version)."""
    tool = get_tool(tool_name)
    old = get_tool_version(tool)
    latest = get_latest_version(tool)
    if not latest:
        raise InstallError(f"Could not determine latest version for {tool.name}")
    if old and compare_versions(old, latest) == 0:
        return old, old
    install_tool(tool_name, cfg, version=latest, force=force)
    new = get_tool_version(tool) or latest
    return old, new


def sync_pin_group(
    tool_name: str,
    cfg: dict,
    *,
    target_frida: str | None = None,
    force: bool = False,
) -> list[tuple[str, str | None, str | None]]:
    """Align the frida pin group to a frida *runtime* version.

    Only ``frida`` is installed at the exact target version. Companion pip tools
    (frida-tools, objection, r2frida) are upgraded so pip resolves versions
    compatible with that runtime — they do NOT use the same version number.
    """
    from droidforge.versions import (
        FRIDA_COMPANIONS,
        FRIDA_COMPANIONS_OPTIONAL,
        FRIDA_EXACT,
        FRIDA_OPTIONAL,
        PinGroupSyncError,
        SyncStep,
        resolve_frida_target,
    )

    group = get_pin_group(tool_name)
    target = resolve_frida_target(cfg, target_frida)
    steps: list[SyncStep] = []
    results: list[tuple[str, str | None, str | None]] = []

    def record(name: str, old: str | None, new: str | None, action: str, detail: str) -> None:
        steps.append(SyncStep(name, action, detail, old, new))
        results.append((name, old, new))

    order = resolve_install_order(list(group))

    for name in order:
        tool = get_tool(name)
        if tool.install_method == "manual":
            continue

        old = get_tool_version(tool)

        if name in FRIDA_EXACT:
            if not force and old and versions_match(old, target):
                record(name, old, old, "skip", f"already at frida runtime {target}")
                continue
            try:
                _pip_install(tool.pip_package or "frida", target, force)
                new = get_tool_version(tool) or target
                record(name, old, new, "install", f"frida runtime → {new}")
            except InstallError as e:
                steps.append(SyncStep(name, "failed", str(e), old, None))
                raise PinGroupSyncError(
                    f"Could not install frida runtime {target}.",
                    target_frida=target,
                    steps=steps,
                    cause=str(e),
                ) from e
            continue

        if name in FRIDA_COMPANIONS or name in FRIDA_COMPANIONS_OPTIONAL:
            try:
                _pip_install_companion(tool.pip_package or name, force)
                new = get_tool_version(tool)
                record(
                    name,
                    old,
                    new,
                    "install",
                    f"upgraded compatible release → {new or '?'} (frida runtime {target})",
                )
            except InstallError as e:
                if name in FRIDA_COMPANIONS_OPTIONAL:
                    record(name, old, old, "skip", f"optional, skipped: {e}")
                    continue
                steps.append(SyncStep(name, "failed", str(e), old, None))
                raise PinGroupSyncError(
                    f"Frida runtime is {target}, but {name} failed to install.",
                    target_frida=target,
                    steps=steps,
                    cause=str(e),
                ) from e
            continue

        if name in FRIDA_OPTIONAL:
            try:
                install_tool(name, cfg, version=None, force=force)
                new = get_tool_version(tool)
                record(name, old, new, "install", f"optional tool → {new or 'installed'}")
            except InstallError as e:
                record(name, old, old, "skip", f"optional, skipped: {e}")

    return results


def update_pin_group(
    tool_name: str,
    cfg: dict,
    *,
    force: bool = False,
) -> list[tuple[str, str | None, str | None]]:
    """Update all members of a pin group atomically."""
    from droidforge.versions import PinGroupSyncError, print_sync_error

    try:
        return sync_pin_group(tool_name, cfg, force=force)
    except PinGroupSyncError as e:
        print_sync_error(e)
        raise InstallError(str(e)) from e


def get_tool_status(tool: Tool, cfg: dict) -> dict:
    """Return status dict for a tool."""
    installed = get_tool_version(tool)
    latest = get_latest_version(tool)
    pinned = get_pinned_version(cfg, tool.name)
    ignored = tool.name in cfg.get("ignored", {}).get("tools", [])

    if tool.install_method == "manual":
        status = "manual"
    elif installed is None and not is_binary_available(tool.binary_name):
        status = "missing"
    elif pinned:
        status = "pinned"
    elif latest and installed and compare_versions(installed, latest) < 0:
        status = "outdated"
    elif installed or is_binary_available(tool.binary_name):
        status = "ok"
    else:
        status = "missing"

    return {
        "tool": tool,
        "installed": installed,
        "latest": latest,
        "pinned": pinned,
        "status": status,
        "ignored": ignored,
    }
