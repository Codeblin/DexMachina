"""Tests for fast doctor broken-install scanning."""

from unittest.mock import patch

from dexmachina.doctor import check_broken_installs
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
