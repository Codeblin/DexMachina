"""Tests for the environment lockfile."""

from pathlib import Path

from dexmachina import lockfile
from dexmachina.config import META_KEY


def _cfg(root: Path) -> dict:
    return {
        "settings": {"install_dir": ".dexmachina/tools", "profile": "minimal"},
        "pins": {},
        "ignored": {"tools": []},
        "active": {},
        META_KEY: {"root": str(root), "path": str(root / "dexmachina.toml")},
    }


def test_build_and_roundtrip_lock(tmp_path, monkeypatch):
    def fake_version(tool, config=None):
        return {"adb": "1.0.41", "frida": "17.9.6"}.get(tool.name)

    monkeypatch.setattr("dexmachina.installer.get_tool_version", fake_version)
    monkeypatch.setattr("dexmachina.versions.get_active_frida_version", lambda _c: "17.9.6")

    cfg = _cfg(tmp_path)
    path = lockfile.write_lock(cfg)
    assert path == tmp_path / lockfile.LOCK_NAME
    assert path.exists()

    lock = lockfile.read_lock(cfg)
    assert lock is not None
    assert lock["tools"]["adb"]["version"] == "1.0.41"
    assert lock["tools"]["frida"]["version"] == "17.9.6"
    assert lock["frida"]["active"] == "17.9.6"
    assert lock["meta"]["profile"] == "minimal"


def test_read_lock_missing_returns_none(tmp_path):
    assert lockfile.read_lock(_cfg(tmp_path)) is None


def test_lock_path_next_to_config(tmp_path):
    assert lockfile.lock_path(_cfg(tmp_path)) == tmp_path / lockfile.LOCK_NAME


def test_restore_skips_frida_pip_members(tmp_path, monkeypatch):
    cfg = _cfg(tmp_path)
    lock = {
        "tools": {
            "frida": {"version": "17.9.6", "method": "pip"},
            "objection": {"version": "1.11.0", "method": "pip"},
            "jadx": {"version": "1.5.0", "method": "github_release"},
        },
        "frida": {"active": "17.9.6"},
    }

    used = {}

    def fake_use(config, version, pin=True):
        used["frida"] = version

    installed: list[tuple[str, str | None]] = []

    def fake_install(name, config, *, version=None, force=False, progress=None):
        installed.append((name, version))

    monkeypatch.setattr("dexmachina.versions.use_frida_version", fake_use)
    monkeypatch.setattr("dexmachina.installer.install_tool", fake_install)

    restored, failures = lockfile.restore_from_lock(cfg, lock)

    assert used["frida"] == "17.9.6"
    # frida/objection are pip members of the frida group → provided by venv, skipped.
    installed_names = [n for n, _ in installed]
    assert "frida" not in installed_names
    assert "objection" not in installed_names
    assert ("jadx", "1.5.0") in installed
    assert failures == []
    assert any("jadx" in r for r in restored)
