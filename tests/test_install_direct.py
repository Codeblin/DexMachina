"""Tests for direct-download installs and install resilience."""

from pathlib import Path

import pytest

from dexmachina import installer
from dexmachina.config import META_KEY
from dexmachina.installer import InstallError, install_tools
from dexmachina.registry import get_tool


def _cfg(root: Path) -> dict:
    return {
        "settings": {"install_dir": ".dexmachina/tools"},
        "pins": {},
        "ignored": {"tools": []},
        "active": {},
        META_KEY: {"root": str(root), "path": str(root / "dexmachina.toml")},
    }


def test_adb_uses_direct_method_not_github():
    adb = get_tool("adb")
    assert adb.install_method == "direct"
    assert adb.github_repo is None
    assert adb.download_url_template and "{platform}" in adb.download_url_template


def test_platform_download_key_maps_known_platforms(monkeypatch):
    monkeypatch.setattr(installer, "detect_platform", lambda: "macos")
    assert installer._platform_download_key() == "darwin"
    monkeypatch.setattr(installer, "detect_platform", lambda: "windows")
    assert installer._platform_download_key() == "windows"
    monkeypatch.setattr(installer, "detect_platform", lambda: "linux")
    assert installer._platform_download_key() == "linux"


def test_install_direct_downloads_and_links(tmp_path, monkeypatch):
    cfg = _cfg(tmp_path)
    captured = {}

    def fake_download(url, dest, progress=None):
        captured["url"] = url
        dest.write_bytes(b"fake-zip")

    def fake_extract(archive, dest):
        dest.mkdir(parents=True, exist_ok=True)
        (dest / "adb").write_text("#!/bin/sh\n", encoding="utf-8")

    monkeypatch.setattr(installer, "detect_platform", lambda: "linux")
    monkeypatch.setattr(installer, "_download_file", fake_download)
    monkeypatch.setattr(installer, "_extract_archive", fake_extract)

    installer._install_direct(get_tool("adb"), cfg)

    assert "platform-tools-latest-linux.zip" in captured["url"]
    bin_dir = tmp_path / ".dexmachina" / "tools" / "adb" / "bin"
    assert (bin_dir / "adb").is_file()


def test_find_executable_prefers_exact_stem(tmp_path):
    root = tmp_path / "platform-tools"
    root.mkdir()
    (root / "adb.exe").write_text("x", encoding="utf-8")
    (root / "AdbWinApi.dll").write_text("x", encoding="utf-8")

    found = installer._find_executable_in_tree(tmp_path, "adb")
    assert found is not None
    assert found.name == "adb.exe"  # not the DLL


def test_link_binaries_wraps_in_place_keeping_siblings(tmp_path, monkeypatch):
    monkeypatch.setattr(installer, "detect_platform", lambda: "windows")
    extract_root = tmp_path / "extracted"
    pt = extract_root / "platform-tools"
    pt.mkdir(parents=True)
    (pt / "adb.exe").write_text("x", encoding="utf-8")
    (pt / "AdbWinApi.dll").write_text("x", encoding="utf-8")
    (pt / "fastboot.exe").write_text("x", encoding="utf-8")

    tool_dir = tmp_path / "adb"
    installer._link_binaries(get_tool("adb"), extract_root, tool_dir)

    bin_dir = tool_dir / "bin"
    adb_wrapper = bin_dir / "adb.bat"
    assert adb_wrapper.is_file()
    assert (bin_dir / "fastboot.bat").is_file()
    # Wrapper points at the in-place exe so sibling DLLs remain usable.
    assert "adb.exe" in adb_wrapper.read_text(encoding="utf-8")
    # The real exe is NOT copied out of its folder.
    assert not (bin_dir / "adb.exe").exists()


def test_install_tools_continue_on_error_collects_failures(tmp_path, monkeypatch):
    cfg = _cfg(tmp_path)

    def boom(name, config, *, version=None, force=False, progress=None):
        if name == "adb":
            raise InstallError("network down")

    monkeypatch.setattr(installer, "install_tool", boom)

    failures = install_tools(["adb"], cfg, continue_on_error=True)
    assert failures == [("adb", "network down")]


def test_install_tools_wraps_unexpected_error(tmp_path, monkeypatch):
    cfg = _cfg(tmp_path)

    def boom(name, config, *, version=None, force=False, progress=None):
        raise RuntimeError("404 not found")

    monkeypatch.setattr(installer, "install_tool", boom)

    # Non-InstallError must be wrapped, not propagated raw.
    with pytest.raises(InstallError):
        install_tools(["jadx"], cfg)
