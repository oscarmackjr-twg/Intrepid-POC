"""Tests for SECRET_KEY startup guard (HARD-02).

These tests are RED (failing) until the startup guard is implemented in
config/settings.py. The guard must raise ValueError/ValidationError when
Settings is instantiated with the sentinel key outside LOCAL_DEV_MODE.
"""
import pytest
from pydantic import ValidationError


SENTINEL = "your-secret-key-change-in-production"


class TestSecretKeyGuard:
    """Tests for startup guard that rejects sentinel SECRET_KEY in production."""

    def test_startup_fails_with_fallback_secret_key(self):
        """Settings must raise an error when SECRET_KEY is the sentinel and LOCAL_DEV_MODE=False.

        RED: This will fail until a @model_validator guard is added to Settings that
        raises ValueError when SECRET_KEY == SENTINEL and LOCAL_DEV_MODE is False.
        """
        from config.settings import Settings

        with pytest.raises((ValueError, ValidationError)):
            Settings(SECRET_KEY=SENTINEL, LOCAL_DEV_MODE=False)

    def test_startup_succeeds_with_local_dev_mode(self):
        """Settings must NOT raise when LOCAL_DEV_MODE=True, even with sentinel key.

        This test will pass only after LOCAL_DEV_MODE field is added to Settings.
        RED until LOCAL_DEV_MODE field exists.
        """
        from config.settings import Settings

        # Should not raise — dev mode bypasses the guard
        s = Settings(SECRET_KEY=SENTINEL, LOCAL_DEV_MODE=True)
        assert s.LOCAL_DEV_MODE is True
