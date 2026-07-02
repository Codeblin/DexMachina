"""Tests for device / frida-server helpers."""

from unittest.mock import patch

from droidforge.device import (
    FridaServerStatus,
    device_has_su,
    frida_server_user,
    restart_frida_server,
)


def test_device_has_su_true():
    with patch("droidforge.device.run_cmd") as mock_run:
        mock_run.return_value.returncode = 0
        mock_run.return_value.stdout = "uid=0(root) gid=0(root)"
        assert device_has_su({}) is True


def test_frida_server_user_reads_root_uid():
    cfg = {}
    with patch("droidforge.device.frida_server_pid", return_value="1234"):
        with patch("droidforge.device.run_cmd") as mock_run:
            mock_run.return_value.returncode = 0
            mock_run.return_value.stdout = "Uid:\t0\t0\t0\t0\n"
            assert frida_server_user(cfg) == "root"


def test_restart_frida_server_uses_su_when_rooted():
    cfg = {}
    with patch("droidforge.device.device_has_su", return_value=True):
        with patch("droidforge.device._kill_frida_server"):
            with patch("droidforge.device.run_cmd") as mock_run:
                with patch("droidforge.device.frida_server_status") as status:
                    status.side_effect = [
                        FridaServerStatus(running=True, user="shell", device_rooted=True),
                        FridaServerStatus(running=True, user="root", device_rooted=True),
                    ]
                    result = restart_frida_server(cfg)
    assert result.runs_as_root
    su_calls = [c for c in mock_run.call_args_list if "su" in c.args[0]]
    assert su_calls
