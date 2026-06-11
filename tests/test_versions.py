"""Tests for frida version sync logic."""

from unittest.mock import patch

import pytest

from droidforge.versions import FRIDA_COMPANIONS, FRIDA_EXACT, resolve_frida_target


def test_frida_exact_vs_companions():
    assert "frida" in FRIDA_EXACT
    assert "frida-tools" in FRIDA_COMPANIONS
    assert "frida" not in FRIDA_COMPANIONS


def test_resolve_frida_target_pinned():
    cfg = {"pins": {"frida": "16.1.4"}, "settings": {}, "ignored": {"tools": []}, "active": {}}
    assert resolve_frida_target(cfg, None) == "16.1.4"


def test_resolve_frida_target_explicit():
    cfg = {"pins": {}, "settings": {}, "ignored": {"tools": []}, "active": {}}
    assert resolve_frida_target(cfg, "17.11.0") == "17.11.0"
