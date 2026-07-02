"""Tests for the interactive DexMachina console (REPL)."""

import dexmachina.console as console_mod
from dexmachina.console import DexMachinaConsole


def _make(monkeypatch, devices=None, apps=None):
    """Build a console with device/app lookups stubbed out (no real ADB)."""
    monkeypatch.setattr(console_mod, "list_devices", lambda cfg: list(devices or []))
    monkeypatch.setattr(
        console_mod, "list_android_apps", lambda cfg, serial=None: list(apps or [])
    )
    return DexMachinaConsole(config={}, serial=None)


def test_prompt_reflects_state(monkeypatch):
    c = _make(monkeypatch)
    assert "no-device" in c.prompt
    assert "no-target" in c.prompt
    c.serial = "emulator-5554"
    c.package = "com.example.app"
    c._update_prompt()
    assert "emulator-5554" in c.prompt
    assert "com.example.app" in c.prompt


def test_empty_line_is_noop(monkeypatch):
    c = _make(monkeypatch)
    assert c.emptyline() is False


def test_exit_stops_loop(monkeypatch):
    c = _make(monkeypatch)
    assert c.do_exit("") is True
    assert c.do_quit("") is True
    assert c.do_EOF("") is True


def test_guards_do_not_stop_loop(monkeypatch):
    c = _make(monkeypatch)
    for line in ["hook", "bypass", "objection", "adb shell", "proxy 1.2.3.4:8080", "pull /x"]:
        assert not c.onecmd(line), f"{line!r} should not stop the loop"


def test_use_rejects_unconnected_device(monkeypatch):
    c = _make(monkeypatch, devices=["emulator-5554"])
    c.onecmd("use nonexistent")
    assert c.serial is None
    c.onecmd("use emulator-5554")
    assert c.serial == "emulator-5554"


def test_devices_auto_selects_single(monkeypatch):
    c = _make(monkeypatch, devices=["emulator-5554"])
    c.do_devices("")
    assert c.serial == "emulator-5554"


def test_target_exact_match(monkeypatch):
    class App:
        def __init__(self, ident, name, pid=None):
            self.identifier = ident
            self.name = name
            self.pid = pid

        @property
        def running(self):
            return self.pid is not None

    apps = [App("com.example.app", "Example"), App("com.other.app", "Other")]
    c = _make(monkeypatch, apps=apps)
    c.do_target("com.example.app")
    assert c.package == "com.example.app"


def test_target_falls_back_to_literal_when_no_apps(monkeypatch):
    c = _make(monkeypatch, apps=[])
    c.do_target("com.manual.pkg")
    assert c.package == "com.manual.pkg"
