"""Failing test stubs for FF-01, FF-02, FF-07, FF-08.

These tests cover:
- FF-01: SG final funding script executes end-to-end
- FF-02: CIBC final funding script executes end-to-end
- FF-07: Cashflow bridge copies current_assets.csv to files_required/
- FF-08: Cashflow bridge is a no-op when current_assets.csv is absent

FF-01 and FF-02 are marked @pytest.mark.integration — they require real bundled scripts
(backend/scripts/final_funding_sg.py and final_funding_cibc.py) that do not exist until
Plan 02. They are skipped in CI by default.

FF-07 and FF-08 test _bridge_cashflow_outputs_to_inputs which is added in Plan 03.
They skip when that function is absent.
"""
import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch

from orchestration.final_funding_runner import (
    execute_final_funding_sg,
    execute_final_funding_cibc,
)

# Resilient import: _bridge_cashflow_outputs_to_inputs is added in Plan 03.
try:
    from orchestration.final_funding_runner import _bridge_cashflow_outputs_to_inputs
    _BRIDGE_AVAILABLE = True
except ImportError:
    _BRIDGE_AVAILABLE = False


# ---------------------------------------------------------------------------
# FF-01: SG script executes end-to-end
# ---------------------------------------------------------------------------

@pytest.mark.integration
def test_sg_script_executes(temp_ff_input_dir, monkeypatch):
    """execute_final_funding_sg runs the bundled SG script and returns the output prefix.

    RED: bundled script (backend/scripts/final_funding_sg.py) does not exist until Plan 02.
    GREEN: function resolves the script, sets up temp dir, and returns 'final_funding_sg'.

    _upload_local_output_to_storage is mocked to keep the test self-contained
    (no real storage write needed).
    """
    monkeypatch.setattr(
        "orchestration.final_funding_runner.settings",
        MagicMock(
            STORAGE_TYPE="local",
            INPUT_DIR=str(temp_ff_input_dir),
            FINAL_FUNDING_SG_SCRIPT_PATH=None,
            FINAL_FUNDING_CIBC_SCRIPT_PATH=None,
        ),
    )

    with patch(
        "orchestration.final_funding_runner._upload_local_output_to_storage"
    ):
        result = execute_final_funding_sg(folder=str(temp_ff_input_dir))

    assert result == "final_funding_sg", (
        f"Expected 'final_funding_sg', got {result!r}"
    )


# ---------------------------------------------------------------------------
# FF-02: CIBC script executes end-to-end
# ---------------------------------------------------------------------------

@pytest.mark.integration
def test_cibc_script_executes(temp_ff_input_dir, monkeypatch):
    """execute_final_funding_cibc runs the bundled CIBC script and returns the output prefix.

    RED: bundled script (backend/scripts/final_funding_cibc.py) does not exist until Plan 02.
    GREEN: function resolves the script, sets up temp dir, and returns 'final_funding_cibc'.
    """
    monkeypatch.setattr(
        "orchestration.final_funding_runner.settings",
        MagicMock(
            STORAGE_TYPE="local",
            INPUT_DIR=str(temp_ff_input_dir),
            FINAL_FUNDING_SG_SCRIPT_PATH=None,
            FINAL_FUNDING_CIBC_SCRIPT_PATH=None,
        ),
    )

    with patch(
        "orchestration.final_funding_runner._upload_local_output_to_storage"
    ):
        result = execute_final_funding_cibc(folder=str(temp_ff_input_dir))

    assert result == "final_funding_cibc", (
        f"Expected 'final_funding_cibc', got {result!r}"
    )


# ---------------------------------------------------------------------------
# FF-07: cashflow bridge copies current_assets.csv to files_required/
# ---------------------------------------------------------------------------

@pytest.mark.skipif(
    not _BRIDGE_AVAILABLE,
    reason="_bridge_cashflow_outputs_to_inputs not yet implemented (Plan 03)"
)
def test_cashflow_bridge_copies_file(temp_dir):
    """_bridge_cashflow_outputs_to_inputs copies current_assets.csv from outputs to files_required/.

    RED: function not yet added to final_funding_runner.
    GREEN: after call, (temp_dir / files_required / current_assets.csv) exists with content.
    """
    files_required = temp_dir / "files_required"
    files_required.mkdir(parents=True, exist_ok=True)

    # Build a mock storage backend that has current_assets.csv
    mock_file_info = MagicMock()
    mock_file_info.name = "current_assets.csv"
    mock_file_info.last_modified = "2026-01-01T00:00:00"

    mock_storage = MagicMock()
    mock_storage.list_files.return_value = [mock_file_info]
    mock_storage.read_file.return_value = b"col1,col2\n1,2\n"

    with patch(
        "orchestration.final_funding_runner.get_storage_backend",
        return_value=mock_storage,
    ):
        _bridge_cashflow_outputs_to_inputs(str(temp_dir), "local")

    target = temp_dir / "files_required" / "current_assets.csv"
    assert target.exists(), (
        f"Expected current_assets.csv to be copied to {target} but it was not found"
    )
    assert target.read_bytes() == b"col1,col2\n1,2\n", "File content does not match"


# ---------------------------------------------------------------------------
# FF-08: cashflow bridge is a no-op when current_assets.csv is absent
# ---------------------------------------------------------------------------

@pytest.mark.skipif(
    not _BRIDGE_AVAILABLE,
    reason="_bridge_cashflow_outputs_to_inputs not yet implemented (Plan 03)"
)
def test_cashflow_bridge_absent_is_noop(temp_dir):
    """_bridge_cashflow_outputs_to_inputs does nothing when outputs storage has no matching files.

    RED: function not yet added to final_funding_runner.
    GREEN: empty list_files → no exception raised, files_required/ unchanged (only placeholder).
    """
    files_required = temp_dir / "files_required"
    files_required.mkdir(parents=True, exist_ok=True)
    placeholder = files_required / "placeholder.txt"
    placeholder.write_text("existing")

    mock_storage = MagicMock()
    mock_storage.list_files.return_value = []  # nothing in outputs

    with patch(
        "orchestration.final_funding_runner.get_storage_backend",
        return_value=mock_storage,
    ):
        # Must complete without raising
        _bridge_cashflow_outputs_to_inputs(str(temp_dir), "local")

    # files_required/ should be unchanged
    assert placeholder.exists(), "Placeholder file should remain untouched"
    csv_target = files_required / "current_assets.csv"
    assert not csv_target.exists(), "current_assets.csv should NOT have been created"
