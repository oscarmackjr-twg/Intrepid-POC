"""Unit tests for rules.comap module — grid lookup and skip logic.

IMPORTANT: Grid DataFrames are built inline in each test using the FICO band column
names imported from the module constants. Mismatched column names would cause `avail`
to be empty and all lookups to silently return False, so we always import and use the
constant dict keys directly.
"""

import pytest
import pandas as pd

from rules.comap import (
    _prog_in_grid,
    _found_in_grid,
    SFY_COMAP_COLS_MIN_FICO,
    PRIME_COMAP_COLS_MIN_FICO,
    PRIME_COMAP_COLS_MIN_FICO2,
    NOTES_COMAP_COLS_MIN_FICO,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_grid(fico_col_mins: dict, rows: list[dict]) -> pd.DataFrame:
    """Build a minimal grid DataFrame with columns matching fico_col_mins keys."""
    cols = list(fico_col_mins.keys())
    df = pd.DataFrame(rows, columns=cols)
    return df


# ---------------------------------------------------------------------------
# _prog_in_grid tests
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestProgInGrid:
    """Tests for the _prog_in_grid helper — FICO-agnostic presence check."""

    def test_returns_true_when_program_present_in_any_column(self):
        """Program found in at least one FICO band column returns True."""
        grid = _make_grid(
            SFY_COMAP_COLS_MIN_FICO,
            [{"660-719": "Prog-A", "720-779": None, "780-799": None, "800+": None}],
        )
        assert _prog_in_grid("Prog-A", grid, SFY_COMAP_COLS_MIN_FICO) is True

    def test_returns_false_when_program_absent_from_all_columns(self):
        """Program absent from every FICO band column (skip, not flag) returns False."""
        grid = _make_grid(
            PRIME_COMAP_COLS_MIN_FICO2,
            [
                {"660-699": "Prog-X", "700-739": "Prog-Y", "740-749": None, "750+": None},
                {"660-699": None, "700-739": "Prog-Z", "740-749": None, "750+": None},
            ],
        )
        # "Prog-ABSENT" is not in the grid at all
        assert _prog_in_grid("Prog-ABSENT", grid, PRIME_COMAP_COLS_MIN_FICO2) is False

    def test_program_present_in_only_one_column_returns_true(self):
        """Program present in exactly one column (the 660-699 band) returns True."""
        grid = _make_grid(
            PRIME_COMAP_COLS_MIN_FICO2,
            [
                {"660-699": "Only-Here", "700-739": None, "740-749": None, "750+": None},
            ],
        )
        assert _prog_in_grid("Only-Here", grid, PRIME_COMAP_COLS_MIN_FICO2) is True

    def test_returns_false_for_empty_grid(self):
        """Empty grid produces False (no columns have data)."""
        grid = _make_grid(
            SFY_COMAP_COLS_MIN_FICO,
            [{"660-719": None, "720-779": None, "780-799": None, "800+": None}],
        )
        assert _prog_in_grid("Any-Prog", grid, SFY_COMAP_COLS_MIN_FICO) is False

    def test_column_mismatch_returns_false(self):
        """If grid columns don't match fico_col_mins keys, avail is empty and result is False."""
        # Grid with wrong column names — won't match SFY_COMAP_COLS_MIN_FICO
        grid = pd.DataFrame([{"wrong-col-name": "Prog-A"}])
        assert _prog_in_grid("Prog-A", grid, SFY_COMAP_COLS_MIN_FICO) is False

    def test_sfy_grid_uses_sfy_columns(self):
        """SFY grid correctly uses SFY FICO band columns (not Prime columns)."""
        # SFY_COMAP_COLS_MIN_FICO has: 660-719, 720-779, 780-799, 800+
        sfy_grid = _make_grid(
            SFY_COMAP_COLS_MIN_FICO,
            [{"660-719": "SFY-Prog", "720-779": None, "780-799": None, "800+": None}],
        )
        assert _prog_in_grid("SFY-Prog", sfy_grid, SFY_COMAP_COLS_MIN_FICO) is True
        # The same program is NOT found when searching with Prime column keys
        assert _prog_in_grid("SFY-Prog", sfy_grid, PRIME_COMAP_COLS_MIN_FICO2) is False

    def test_notes_grid_columns_work(self):
        """Notes grid uses NOTES_COMAP_COLS_MIN_FICO column keys."""
        notes_grid = _make_grid(
            NOTES_COMAP_COLS_MIN_FICO,
            [{"680-749": "Notes-Prog", "750-769": None, "770-789": None, "790+": None}],
        )
        assert _prog_in_grid("Notes-Prog", notes_grid, NOTES_COMAP_COLS_MIN_FICO) is True
        assert _prog_in_grid("Missing", notes_grid, NOTES_COMAP_COLS_MIN_FICO) is False


# ---------------------------------------------------------------------------
# _found_in_grid tests
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestFoundInGrid:
    """Tests for _found_in_grid — FICO-sensitive eligibility check."""

    def test_returns_true_when_prog_in_correct_fico_band(self):
        """Program in the 660-699 column is found for FICO=680 (within band)."""
        grid = _make_grid(
            PRIME_COMAP_COLS_MIN_FICO2,
            [{"660-699": "Match-Prog", "700-739": None, "740-749": None, "750+": None}],
        )
        # FICO 680 >= 660, so the 660-699 band is eligible
        assert _found_in_grid("Match-Prog", 680, grid, PRIME_COMAP_COLS_MIN_FICO2) is True

    def test_returns_false_when_fico_below_minimum_for_column(self):
        """Program in 700-739 column is NOT found for FICO=680 (below band minimum 700)."""
        grid = _make_grid(
            PRIME_COMAP_COLS_MIN_FICO2,
            [{"660-699": None, "700-739": "High-Prog", "740-749": None, "750+": None}],
        )
        # FICO 680 < 700 → band 700-739 is excluded
        assert _found_in_grid("High-Prog", 680, grid, PRIME_COMAP_COLS_MIN_FICO2) is False

    def test_returns_false_when_prog_absent_from_all_columns(self):
        """Program not in any column returns False regardless of FICO."""
        grid = _make_grid(
            SFY_COMAP_COLS_MIN_FICO,
            [{"660-719": "Other-Prog", "720-779": None, "780-799": None, "800+": None}],
        )
        assert _found_in_grid("Absent-Prog", 750, grid, SFY_COMAP_COLS_MIN_FICO) is False

    def test_returns_false_for_empty_avail_columns(self):
        """Returns False immediately when grid columns don't match fico_col_mins."""
        grid = pd.DataFrame([{"bad-col": "Prog"}])
        assert _found_in_grid("Prog", 700, grid, PRIME_COMAP_COLS_MIN_FICO) is False

    def test_high_fico_qualifies_for_higher_band_column(self):
        """FICO 760 qualifies for the 750+ column in PRIME_COMAP_COLS_MIN_FICO2."""
        grid = _make_grid(
            PRIME_COMAP_COLS_MIN_FICO2,
            [{"660-699": None, "700-739": None, "740-749": None, "750+": "Premium-Prog"}],
        )
        assert _found_in_grid("Premium-Prog", 760, grid, PRIME_COMAP_COLS_MIN_FICO2) is True

    def test_oct25_cutoff_note(self):
        """All loans use oct25 grids because cutoff is 1900-10-24 (all Submit Dates are after).

        This test verifies the grid lookup works correctly with PRIME_COMAP_COLS_MIN_FICO2
        columns (the oct25 grid variant used for all Prime loans).
        """
        # oct25 grid uses PRIME_COMAP_COLS_MIN_FICO2: 660-699, 700-739, 740-749, 750+
        oct25_grid = _make_grid(
            PRIME_COMAP_COLS_MIN_FICO2,
            [
                {"660-699": "Oct25-Prog-A", "700-739": "Oct25-Prog-B", "740-749": None, "750+": None},
            ],
        )
        # Loan with FICO 710 should find Oct25-Prog-B in the 700-739 band
        assert _found_in_grid("Oct25-Prog-B", 710, oct25_grid, PRIME_COMAP_COLS_MIN_FICO2) is True
        # Loan with FICO 660 cannot use 700-739 band (below minimum)
        assert _found_in_grid("Oct25-Prog-B", 660, oct25_grid, PRIME_COMAP_COLS_MIN_FICO2) is False
