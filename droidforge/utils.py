"""GitHub releases API, version comparison, and subprocess helpers."""

from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

import requests
from packaging import version as pkg_version

CACHE_TTL_SECONDS = 3600
GITHUB_API = "https://api.github.com"


def run_cmd(
    cmd: str | list[str],
    *,
    capture: bool = True,
    check: bool = False,
    env: dict[str, str] | None = None,
    cwd: Path | None = None,
) -> subprocess.CompletedProcess[str]:
    if isinstance(cmd, str):
        shell = True
        args: str | list[str] = cmd
    else:
        shell = False
        args = cmd
    return subprocess.run(
        args,
        shell=shell,
        capture_output=capture,
        text=True,
        check=check,
        env=env,
        cwd=str(cwd) if cwd else None,
    )


def which(binary: str) -> str | None:
    return shutil.which(binary)


def find_git() -> str | None:
    """Locate git on PATH or common Windows install locations."""
    found = which("git")
    if found:
        return found
    if sys.platform != "win32":
        return None
    for base in (
        os.environ.get("ProgramFiles"),
        os.environ.get("ProgramFiles(x86)"),
    ):
        if not base:
            continue
        for sub in ("Git/cmd/git.exe", "Git/bin/git.exe"):
            candidate = Path(base) / sub
            if candidate.is_file():
                return str(candidate)
    return None


def get_github_default_branch(repo: str) -> str:
    """Return the repo's default branch (main/master)."""
    data = github_get(f"{GITHUB_API}/repos/{repo}")
    if isinstance(data, dict):
        branch = data.get("default_branch")
        if branch:
            return str(branch)
    return "main"


def parse_version(text: str | None) -> str | None:
    """Extract semver-like version from command output."""
    if not text:
        return None
    text = text.strip()
    # Common patterns: "16.1.4", "v16.1.4", "Version 2.9.0"
    match = re.search(r"v?(\d+\.\d+(?:\.\d+)?(?:[a-zA-Z0-9.-]*)?)", text)
    if match:
        ver = match.group(1)
        # Strip trailing non-version suffixes
        ver = re.sub(r"[-_][a-zA-Z]+$", "", ver) if ver.count(".") >= 2 else ver
        return ver.lstrip("v")
    return None


def normalize_version(ver: str | None) -> str | None:
    if not ver:
        return None
    ver = ver.strip().lstrip("v")
    try:
        return str(pkg_version.parse(ver))
    except pkg_version.InvalidVersion:
        return ver


def compare_versions(a: str | None, b: str | None) -> int | None:
    """Return -1 if a<b, 0 if equal, 1 if a>b, None if incomparable."""
    if not a or not b:
        return None
    try:
        va = pkg_version.parse(a)
        vb = pkg_version.parse(b)
        if va < vb:
            return -1
        if va > vb:
            return 1
        return 0
    except pkg_version.InvalidVersion:
        if a == b:
            return 0
        return None


def versions_match(a: str | None, b: str | None) -> bool:
    if not a or not b:
        return False
    na = normalize_version(a)
    nb = normalize_version(b)
    if na and nb:
        return compare_versions(na, nb) == 0
    return a.strip().lstrip("v") == b.strip().lstrip("v")


def cache_dir() -> Path:
    d = Path.home() / ".droidforge" / "cache"
    d.mkdir(parents=True, exist_ok=True)
    return d


def _cache_key(url: str) -> Path:
    h = hashlib.sha256(url.encode()).hexdigest()[:16]
    return cache_dir() / f"{h}.json"


def _read_cache(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        if time.time() - data.get("_cached_at", 0) > CACHE_TTL_SECONDS:
            return None
        return data
    except (json.JSONDecodeError, OSError):
        return None


def _write_cache(path: Path, payload: dict[str, Any]) -> None:
    payload = {**payload, "_cached_at": time.time()}
    path.write_text(json.dumps(payload), encoding="utf-8")


def github_headers() -> dict[str, str]:
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": "droidforge/0.1.0",
    }
    token = os.environ.get("GITHUB_TOKEN")
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return headers


def github_get(url: str, *, use_cache: bool = True) -> dict[str, Any] | list[Any]:
    cache_path = _cache_key(url)
    if use_cache:
        cached = _read_cache(cache_path)
        if cached and "body" in cached:
            return cached["body"]

    resp = requests.get(url, headers=github_headers(), timeout=30)
    resp.raise_for_status()
    body = resp.json()
    if use_cache:
        _write_cache(cache_path, {"body": body, "url": url})
    return body


def get_latest_github_release(repo: str) -> dict[str, Any]:
    url = f"{GITHUB_API}/repos/{repo}/releases/latest"
    try:
        return github_get(url)  # type: ignore[return-value]
    except requests.HTTPError as e:
        if e.response is not None and e.response.status_code == 404:
            # Some repos use tags only
            tags_url = f"{GITHUB_API}/repos/{repo}/tags"
            tags = github_get(tags_url)
            if tags:
                tag_name = tags[0]["name"]  # type: ignore[index]
                return {"tag_name": tag_name, "assets": []}
        raise


def extract_release_version(release: dict[str, Any]) -> str:
    tag = release.get("tag_name", "")
    return tag.lstrip("v")


def get_installed_version(version_cmd: str | None, binary_name: str | None = None) -> str | None:
    if version_cmd:
        try:
            result = run_cmd(version_cmd)
            if result.returncode == 0 and result.stdout:
                return parse_version(result.stdout) or parse_version(result.stderr)
            if result.stderr:
                return parse_version(result.stderr)
        except (OSError, subprocess.SubprocessError):
            pass

    if binary_name and which(binary_name):
        try:
            result = run_cmd(f"{binary_name} --version")
            if result.returncode == 0:
                combined = (result.stdout or "") + (result.stderr or "")
                return parse_version(combined)
        except (OSError, subprocess.SubprocessError):
            pass
    return None


def is_binary_available(binary_name: str | None) -> bool:
    if not binary_name:
        return False
    return which(binary_name) is not None


def pip_show_version(package: str) -> str | None:
    result = run_cmd([sys.executable, "-m", "pip", "show", package])
    if result.returncode != 0:
        return None
    for line in (result.stdout or "").splitlines():
        if line.startswith("Version:"):
            return line.split(":", 1)[1].strip()
    return None


def npm_show_version(package: str) -> str | None:
    result = run_cmd(f"npm list -g {package} --depth=0")
    if result.returncode != 0:
        return None
    match = re.search(rf"{re.escape(package)}@(\S+)", result.stdout or "")
    return match.group(1) if match else None


def detect_platform() -> str:
    if sys.platform == "win32":
        return "windows"
    if sys.platform == "darwin":
        return "macos"
    return "linux"


def detect_system_package_manager() -> str | None:
    if shutil.which("brew"):
        return "brew"
    if shutil.which("apt-get") or shutil.which("apt"):
        return "apt"
    return None


def human_category(category: str) -> str:
    return category.replace("_", " ").title()
