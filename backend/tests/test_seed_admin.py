"""Tests for one-time password generation in seed_admin (HARD-02).

These tests are RED (failing) until seed_admin.py is refactored to generate
a random URL-safe password instead of using hardcoded values.
"""
import pytest
import secrets
import string


HARDCODED_PASSWORDS = {"admin123", "twg123"}


def _call_generate_password():
    """
    Helper that calls the password generation logic from seed_admin.
    RED: seed_admin currently has no generate_password() function — this import
    will fail until one is added.
    """
    from scripts.seed_admin import generate_password
    return generate_password()


class TestSeedAdminPasswordGeneration:
    """Tests that seed_admin generates non-hardcoded passwords."""

    def test_generates_non_hardcoded_password(self):
        """generate_password() must return a value that is NOT 'admin123' or 'twg123'.

        RED: seed_admin has no generate_password() function yet — import will fail.
        """
        password = _call_generate_password()
        assert password not in HARDCODED_PASSWORDS, (
            f"generate_password() returned a hardcoded password: {password!r}. "
            "The function must generate a random password."
        )

    def test_password_is_url_safe_string(self):
        """generate_password() must return a string of at least 16 chars with no spaces.

        RED: seed_admin has no generate_password() function yet — import will fail.
        """
        password = _call_generate_password()
        assert isinstance(password, str), "Password must be a string"
        assert len(password) >= 16, (
            f"Password too short: {len(password)} chars. Must be at least 16."
        )
        assert " " not in password, "Password must not contain spaces"
