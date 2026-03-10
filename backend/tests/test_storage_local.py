"""Tests for local storage backend URL behavior (HARD-04).

RED phase: these tests verify behaviors that do not yet exist.
- get_file_url must return an API path, never a file:// URI
"""
import pytest
from pathlib import Path

from storage.local import LocalStorageBackend


class TestLocalStorageGetFileUrl:
    """Test that LocalStorageBackend returns safe API paths, not file:// URIs."""

    def test_get_file_url_returns_api_path_not_file_uri(self, tmp_path):
        """get_file_url must return a path starting with /api/files/download/, not file://."""
        backend = LocalStorageBackend(base_path=str(tmp_path))
        # Create a real file so the method doesn't raise FileNotFoundError
        test_file = tmp_path / "report.xlsx"
        test_file.write_bytes(b"dummy")

        url = backend.get_file_url("report.xlsx")

        assert not url.startswith("file://"), (
            f"get_file_url returned a file:// URI which leaks internal filesystem path: {url!r}"
        )

    def test_get_file_url_starts_with_api_download_prefix(self, tmp_path):
        """get_file_url must return a relative API download URL."""
        backend = LocalStorageBackend(base_path=str(tmp_path))
        test_file = tmp_path / "output.csv"
        test_file.write_bytes(b"col1,col2\n1,2")

        url = backend.get_file_url("output.csv")

        assert url.startswith("/api/files/download/"), (
            f"Expected URL starting with /api/files/download/, got: {url!r}"
        )

    def test_get_file_url_contains_filename(self, tmp_path):
        """get_file_url result must contain the requested filename."""
        backend = LocalStorageBackend(base_path=str(tmp_path))
        test_file = tmp_path / "my_report.xlsx"
        test_file.write_bytes(b"dummy")

        url = backend.get_file_url("my_report.xlsx")

        assert "my_report.xlsx" in url, (
            f"Expected filename in URL, got: {url!r}"
        )

    def test_get_file_url_raises_for_missing_file(self, tmp_path):
        """get_file_url must raise FileNotFoundError when file does not exist."""
        backend = LocalStorageBackend(base_path=str(tmp_path))

        with pytest.raises(FileNotFoundError):
            backend.get_file_url("nonexistent.xlsx")
