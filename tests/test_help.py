"""Tests for categorized help output."""

from click.testing import CliRunner

from droidforge.cli import main
from droidforge.help_fmt import DroidForgeGroup


def test_main_uses_categorized_group():
    assert isinstance(main, DroidForgeGroup)


def test_help_has_sections():
    runner = CliRunner()
    result = runner.invoke(main, ["--help"])
    assert result.exit_code == 0
    assert "Environment" in result.output
    assert "Presets" in result.output
    assert "hook" in result.output
    assert "Arsenal — Dynamic Analysis" in result.output
    assert "Arsenal — Static Analysis" in result.output
    assert "status" in result.output
    assert "frida" in result.output


def test_run_passes_flags_to_tool():
    """Flags after the tool name must reach the underlying CLI (not Click)."""
    runner = CliRunner()
    # Before fix, Click rejected unknown options like --version on `run`.
    result = runner.invoke(main, ["run", "frida", "--version"])
    assert result.exit_code == 0
