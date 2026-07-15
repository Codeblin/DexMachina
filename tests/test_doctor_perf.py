"""Tests for fast doctor broken-install scanning."""

from unittest.mock import patch

from dexmachina.doctor import check_broken_installs, check_frida_server_match
from dexmachina.registry import get_tool


def test_check_broken_installs_skips_version_cmd_probes():
    config = {"settings": {"install_dir": "~/.dexmachina/tools"}, "pins": {}, "ignored": {"tools": []}}
    tool = get_tool("jadx")

    def installed_side_effect(tool_arg, _config, _pip_versions):
        if tool_arg.name == "jadx":
            return True, "1.5.0"
        return False, None

    with patch("dexmachina.installer._merged_pip_versions", return_value={}):
        with patch("dexmachina.doctor.collect_tool_bin_paths", return_value=[]):
            with patch("dexmachina.doctor._tool_installed_fast", side_effect=installed_side_effect):
                with patch("dexmachina.doctor._binary_resolvable", return_value=False):
                    with patch("dexmachina.installer.get_installed_version") as mock_version:
                        results = check_broken_installs(config)

    assert len(results) == 1
    assert results[0].name == tool.display_name
    mock_version.assert_not_called()


def test_check_broken_installs_no_issue_when_binary_resolvable():
    config = {"settings": {"install_dir": "~/.dexmachina/tools"}, "pins": {}, "ignored": {"tools": []}}

    with patch("dexmachina.installer._merged_pip_versions", return_value={"frida": "17.0.0"}):
        with patch("dexmachina.doctor.collect_tool_bin_paths", return_value=[]):
            with patch("dexmachina.doctor._binary_resolvable", return_value=True):
                results = check_broken_installs(config)

    assert results == []


def test_frida_server_check_uses_managed_run_env():
    config = {"settings": {"install_dir": "~/.dexmachina/tools"}, "active": {"frida": "17.0.0"}}
    captured = {}

    def fake_run(cmd, *, env=None, timeout=None, **kwargs):
        captured["cmd"] = cmd
        captured["env"] = env

        class Result:
            returncode = 0
            stdout = "ok"
            stderr = ""

        return Result()

    with patch("dexmachina.doctor.list_devices", return_value=["emulator-5554"]):
        with patch("dexmachina.doctor.get_local_frida_version", return_value="17.0.0") as local:
            with patch("dexmachina.doctor.check_frida_server_running", return_value=True):
                with patch(
                    "dexmachina.doctor.frida_server_status",
                    return_value=type("Status", (), {"device_rooted": True, "runs_as_root": True})(),
                ):
                    with patch("dexmachina.doctor.build_run_env", return_value={"PATH": "/tmp/frida"}):
                        with patch("dexmachina.doctor.run_cmd", side_effect=fake_run):
                            result = check_frida_server_match(config)

    assert result.status == "ok"
    local.assert_called_once_with(config)
    assert captured["cmd"] == "frida-ps -U"
    assert captured["env"] == {"PATH": "/tmp/frida"}
