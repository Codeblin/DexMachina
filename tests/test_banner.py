"""Tests for banner module."""

import os

from dexmachina.banner import banner_enabled, render_banner


def test_banner_enabled_default():
    os.environ.pop("DEXMACHINA_NO_BANNER", None)
    assert banner_enabled() is True


def test_banner_disabled_via_env():
    os.environ["DEXMACHINA_NO_BANNER"] = "1"
    try:
        assert banner_enabled() is False
    finally:
        os.environ.pop("DEXMACHINA_NO_BANNER", None)


def test_render_banner_compact():
    rendered = render_banner(compact=True)
    assert rendered is not None


def test_render_banner_full():
    rendered = render_banner(compact=False)
    assert rendered is not None
