"""ADB wrapper and frida-server push logic."""

from __future__ import annotations

import os
import stat
import tempfile
from pathlib import Path

import requests
from rich.console import Console
from rich.progress import Progress

from droidforge.config import get_setting
from droidforge.progress import work_spinner
from droidforge.utils import github_headers, parse_version, run_cmd, which

console = Console()

# Map adb ABI names to frida-server arch suffixes
ABI_MAP = {
    "arm64-v8a": "arm64",
    "armeabi-v7a": "arm",
    "armeabi": "arm",
    "x86": "x86",
    "x86_64": "x86_64",
}


class DeviceError(Exception):
    """Device operation failed."""


def adb_path(config: dict) -> str:
    custom = get_setting(config, "adb_path", "adb")
    if which(custom):
        return custom
    if which("adb"):
        return "adb"
    raise DeviceError(
        "adb not found. Install platform-tools or set adb_path in droidforge.toml"
    )


def list_devices(config: dict) -> list[str]:
    adb = adb_path(config)
    result = run_cmd([adb, "devices"])
    if result.returncode != 0:
        raise DeviceError(f"adb devices failed: {result.stderr}")
    devices: list[str] = []
    for line in (result.stdout or "").splitlines()[1:]:
        line = line.strip()
        if not line:
            continue
        parts = line.split("\t")
        if len(parts) >= 2 and parts[1] == "device":
            devices.append(parts[0])
    return devices


def get_device_arch(config: dict, serial: str | None = None) -> str:
    adb = adb_path(config)
    cmd = [adb]
    if serial:
        cmd.extend(["-s", serial])
    cmd.extend(["shell", "getprop", "ro.product.cpu.abi"])
    result = run_cmd(cmd)
    if result.returncode != 0:
        raise DeviceError(f"Could not detect device architecture: {result.stderr}")
    abi = (result.stdout or "").strip()
    arch = ABI_MAP.get(abi)
    if not arch:
        raise DeviceError(
            f"Unsupported device ABI: {abi}. "
            f"Supported: {', '.join(ABI_MAP.keys())}"
        )
    return arch


def get_local_frida_version() -> str:
    result = run_cmd("frida --version")
    if result.returncode != 0:
        raise DeviceError(
            "frida not installed locally. Install with: droidforge install frida"
        )
    ver = parse_version(result.stdout or result.stderr)
    if not ver:
        raise DeviceError("Could not parse local frida version")
    return ver


def download_frida_server(version: str, arch: str, dest: Path) -> Path:
    """Download frida-server binary matching version and arch."""
    filename = f"frida-server-{version}-android-{arch}"
    urls = [
        f"https://github.com/frida/frida/releases/download/{version}/{filename}.xz",
        f"https://github.com/frida/frida/releases/download/{version}/{filename}",
    ]

    dest.parent.mkdir(parents=True, exist_ok=True)
    last_error: Exception | None = None

    for url in urls:
        try:
            resp = requests.get(url, headers=github_headers(), stream=True, timeout=120)
            if resp.status_code == 404:
                continue
            resp.raise_for_status()
            raw = dest.with_suffix(".download")
            with raw.open("wb") as f:
                for chunk in resp.iter_content(8192):
                    f.write(chunk)

            if url.endswith(".xz"):
                try:
                    import lzma

                    data = lzma.open(raw).read()
                    out = dest
                    out.write_bytes(data)
                    raw.unlink()
                except ImportError:
                    raise DeviceError(
                        "Downloaded .xz frida-server but lzma module unavailable"
                    )
            else:
                raw.rename(dest)
            return dest
        except requests.RequestException as e:
            last_error = e
            continue

    raise DeviceError(
        f"Could not download frida-server {version} for {arch}. "
        f"Check that version exists at https://github.com/frida/frida/releases. "
        f"{last_error or ''}"
    )


def push_frida_server(
    config: dict,
    *,
    serial: str | None = None,
    start: bool = True,
    remote_path: str = "/data/local/tmp/frida-server",
) -> None:
    """Push matching frida-server to device."""
    frida_ver = get_local_frida_version()
    devices = list_devices(config)

    if not devices:
        raise DeviceError("No ADB devices connected. Connect a device and enable USB debugging.")

    targets = [serial] if serial else devices
    if serial and serial not in devices:
        raise DeviceError(f"Device {serial} not found. Connected: {', '.join(devices)}")

    adb = adb_path(config)

    for dev in targets:
        with work_spinner("[cyan]Detecting device architecture…[/]", console=console) as update:
            arch = get_device_arch(config, dev)
            update(f"[cyan]Device[/] [bold]{dev}[/] — [green]{arch}[/], frida [yellow]{frida_ver}[/]")

        with tempfile.TemporaryDirectory() as tmp:
            local_bin = Path(tmp) / "frida-server"
            with work_spinner(
                f"[cyan]Downloading frida-server {frida_ver} ({arch})…[/]",
                console=console,
            ):
                download_frida_server(frida_ver, arch, local_bin)

            if os.name != "nt":
                local_bin.chmod(local_bin.stat().st_mode | stat.S_IEXEC)

            cmd_base = [adb]
            if dev:
                cmd_base.extend(["-s", dev])

            # Push
            push_cmd = cmd_base + ["push", str(local_bin), remote_path]
            with work_spinner(f"[cyan]Pushing to {remote_path}…[/]", console=console):
                result = run_cmd(push_cmd)
            if result.returncode != 0:
                raise DeviceError(f"adb push failed: {result.stderr}")

            # chmod
            chmod_cmd = cmd_base + ["shell", f"chmod 755 {remote_path}"]
            run_cmd(chmod_cmd)

            console.print(f"[green]✓[/] Pushed frida-server {frida_ver} ({arch}) to {remote_path}")

            if start:
                # Kill existing and start in background
                with work_spinner("[cyan]Starting frida-server on device…[/]", console=console):
                    run_cmd(cmd_base + ["shell", f"pkill -9 frida-server 2>/dev/null; true"])
                    start_cmd = cmd_base + [
                        "shell",
                        f"{remote_path} -D &",
                    ]
                    run_cmd(start_cmd)
                console.print("[green]✓[/] Started frida-server on device")


def get_remote_frida_server_version(config: dict, serial: str | None = None) -> str | None:
    """Try to detect frida-server version on device via frida-ps."""
    if not which("frida-ps"):
        return None
    cmd = "frida-ps -U"
    if serial:
        cmd = f"frida-ps -D {serial}"
    result = run_cmd(cmd)
    if result.returncode != 0:
        return None
    # frida-ps doesn't show server version directly; use frida CLI
    result = run_cmd("frida --version")
    return parse_version(result.stdout) if result.returncode == 0 else None


def check_frida_server_running(config: dict, serial: str | None = None) -> bool:
    adb = adb_path(config)
    cmd = [adb]
    if serial:
        cmd.extend(["-s", serial])
    cmd.extend(["shell", "pgrep frida-server"])
    result = run_cmd(cmd)
    return result.returncode == 0 and bool((result.stdout or "").strip())
