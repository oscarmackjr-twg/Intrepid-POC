"""Unit tests for orchestration.archive_run module.

Tests focus on:
- _is_s3_style_prefix: path classification (S3 key vs absolute path)
- _collect_input_paths: reference file discovery under files_required/

Per D-11: s3_input_sync.py is explicitly out of scope and not tested here.
"""

import pytest
from pathlib import Path

from orchestration.archive_run import _is_s3_style_prefix, _collect_input_paths


# ---------------------------------------------------------------------------
# _is_s3_style_prefix tests
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestIsS3StylePrefix:
    """Tests for _is_s3_style_prefix path classification."""

    def test_rejects_windows_absolute_path(self):
        """Windows drive-letter paths (C:/...) are not S3-style."""
        assert _is_s3_style_prefix("C:/Users/gdehankar/data") is False
        assert _is_s3_style_prefix("C:\\Users\\omack\\folder") is False
        assert _is_s3_style_prefix("D:/some/path") is False

    def test_rejects_unix_absolute_path(self):
        """Unix absolute paths starting with / are not S3-style."""
        assert _is_s3_style_prefix("/home/user/data") is False
        assert _is_s3_style_prefix("/tmp/output") is False
        assert _is_s3_style_prefix("/") is False

    def test_accepts_s3_style_key(self):
        """Relative S3-style key prefixes are accepted."""
        assert _is_s3_style_prefix("runs/run_abc/output") is True
        assert _is_s3_style_prefix("archive/2024-01-15/input") is True
        assert _is_s3_style_prefix("runs/run_001") is True

    def test_rejects_empty_string(self):
        """Empty string is not a valid S3-style prefix."""
        assert _is_s3_style_prefix("") is False

    def test_rejects_none(self):
        """None is not a valid S3-style prefix."""
        assert _is_s3_style_prefix(None) is False

    def test_rejects_whitespace_only(self):
        """Whitespace-only string is not a valid S3-style prefix."""
        assert _is_s3_style_prefix("   ") is False

    def test_accepts_single_segment_key(self):
        """Single-segment key with no slashes is accepted (relative path)."""
        assert _is_s3_style_prefix("myprefix") is True

    def test_rejects_backslash_windows_path(self):
        """Windows backslash paths with drive letter are rejected."""
        # After replace('\\', '/') → 'C:/foo/bar' which contains ':'
        assert _is_s3_style_prefix("C:\\foo\\bar") is False

    def test_accepts_runs_prefix_format(self):
        """Standard pipeline prefix format 'runs/run_<id>/output' is accepted."""
        assert _is_s3_style_prefix("runs/run_20240115_abc123/output") is True


# ---------------------------------------------------------------------------
# _collect_input_paths tests
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestCollectInputPaths:
    """Tests for _collect_input_paths — finds reference files under files_required/."""

    def test_finds_existing_reference_files_in_files_required(self, temp_dir):
        """Files placed in files_required/ that match REFERENCE_FILENAMES are returned."""
        from orchestration.archive_run import REFERENCE_FILENAMES

        files_required = temp_dir / "files_required"
        files_required.mkdir(parents=True, exist_ok=True)

        # Create all reference files as empty placeholders
        for name in REFERENCE_FILENAMES:
            (files_required / name).write_bytes(b"placeholder")

        paths = _collect_input_paths(str(temp_dir), pdate=None)

        found_names = {p.name for p in paths}
        for name in REFERENCE_FILENAMES:
            assert name in found_names, f"Expected {name} to be found in collected paths"

    def test_missing_reference_files_are_silently_skipped(self, temp_dir):
        """If files_required/ exists but reference files are absent, no error is raised."""
        files_required = temp_dir / "files_required"
        files_required.mkdir(parents=True, exist_ok=True)
        # Don't create any files — directory is empty

        # Should not raise, should return empty or minimal list
        paths = _collect_input_paths(str(temp_dir), pdate=None)
        # No reference files were created, so the result should be empty
        assert isinstance(paths, list)
        assert len(paths) == 0

    def test_nonexistent_folder_does_not_raise(self, temp_dir):
        """Calling with a non-existent folder should not raise an exception."""
        nonexistent = temp_dir / "does_not_exist"
        # Should not raise — returns empty list
        try:
            paths = _collect_input_paths(str(nonexistent), pdate=None)
            assert isinstance(paths, list)
        except Exception as exc:
            pytest.fail(f"_collect_input_paths raised unexpectedly: {exc}")

    def test_partial_reference_files_returned(self, temp_dir):
        """Only reference files that actually exist are included in result."""
        from orchestration.archive_run import REFERENCE_FILENAMES

        files_required = temp_dir / "files_required"
        files_required.mkdir(parents=True, exist_ok=True)

        # Create only the first reference file
        first_name = REFERENCE_FILENAMES[0]
        (files_required / first_name).write_bytes(b"placeholder")

        paths = _collect_input_paths(str(temp_dir), pdate=None)

        found_names = {p.name for p in paths}
        assert first_name in found_names
        # The rest should NOT be present (they don't exist on disk)
        for name in REFERENCE_FILENAMES[1:]:
            assert name not in found_names

    def test_returned_paths_are_path_objects(self, temp_dir):
        """_collect_input_paths returns a list of pathlib.Path objects."""
        from orchestration.archive_run import REFERENCE_FILENAMES

        files_required = temp_dir / "files_required"
        files_required.mkdir(parents=True, exist_ok=True)
        (files_required / REFERENCE_FILENAMES[0]).write_bytes(b"x")

        paths = _collect_input_paths(str(temp_dir), pdate=None)
        for p in paths:
            assert isinstance(p, Path), f"Expected Path, got {type(p)}"
