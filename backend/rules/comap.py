"""CoMAP validation rules."""
import pandas as pd
from typing import List, Dict, Any, Tuple
import logging

logger = logging.getLogger(__name__)


# FICO band mappings
PRIME_COMAP_COLS_MIN_FICO = {
    '660-699': 660,
    '700-739': 700,
    '740-749': 740,
    '750-769': 750,
    '770+': 770
}

PRIME_COMAP_COLS_MIN_FICO2 = {
    '660-699': 660,
    '700-739': 700,
    '740-749': 740,
    '750+': 750
}

SFY_COMAP_COLS_MIN_FICO = {
    '660-719': 660,
    '720-779': 720,
    '780-799': 780,
    '800+': 800
}

SFY_COMAP_COLS_MIN_FICO2 = {
    '660-699': 660,
    '700-739': 700,
    '740-749': 740,
    '750-769': 750,
    '770+': 770
}

SFY_COMAP_COLS_MIN_FICO3 = {
    '660-719': 660,
    '720-779': 720,
    '780+': 780
}

NOTES_COMAP_COLS_MIN_FICO = {
    '680-749': 680,
    '750-769': 750,
    '770-789': 770,
    '790+': 790
}


def _found_in_grid(prog: str, fico: float, grid: pd.DataFrame, fico_col_mins: dict) -> bool:
    """Return True if prog/fico is valid in a CoMAP grid.

    Checks two ways:
    1. The program appears as a mapped value in the FICO-appropriate column
       (loan program = the co-mapped/purchased program).
    2. The program appears in the first column ("Applied for Program") of the grid
       AND the FICO-appropriate band column contains a non-null mapped value
       (loan program = the originally applied program before co-mapping).
    """
    avail = [c for c in fico_col_mins if c in grid.columns]
    if not avail:
        return False

    # Check 1: prog is a co-mapped value in the correct FICO band column
    for col in avail:
        if prog in grid[col].values and fico >= fico_col_mins[col]:
            return True

    # Check 2: prog is the applied-for program; verify a mapping exists for the FICO band
    applied_col = grid.columns[0]
    matching_rows = grid[grid[applied_col] == prog]
    if not matching_rows.empty:
        for col in avail:
            if fico >= fico_col_mins[col]:
                mapped = matching_rows[col].dropna().astype(str).str.strip()
                if mapped.ne('').any():
                    return True

    return False


def check_comap_prime(
    buy_df: pd.DataFrame,
    prime_comap: pd.DataFrame,
    prime_comap_oct25: pd.DataFrame,
    prime_comap_oct25_2: pd.DataFrame,
    prime_comap_new: pd.DataFrame,
) -> List[Tuple[str, str, str]]:
    """Check Prime loans against CoMAP. Uses each loan's Submit Date for date-based grid (mirrors February_Baseline)."""
    loan_not_in_comap = []
    oct25_cutoff = pd.to_datetime('2025-10-24')
    prime_new_cutoff = pd.to_datetime('2020-06-11')

    check_df = buy_df[
        (buy_df['Application Type'] != 'HD NOTE') &
        (buy_df['purchase_price_check'] == True) &
        (buy_df['platform'] == 'prime')
    ].copy()
    if 'Submit Date' in check_df.columns:
        check_df['Submit Date'] = pd.to_datetime(check_df['Submit Date'])
    else:
        check_df['Submit Date'] = pd.NaT

    for _, row in check_df.iterrows():
        fico = row['FICO Borrower']
        prog = row['loan program']
        prog = str(prog) if pd.notna(prog) else ''
        submit_dt = row['Submit Date']
        found = False

        if pd.notna(submit_dt) and submit_dt > oct25_cutoff:
            found = (
                _found_in_grid(prog, fico, prime_comap_oct25, PRIME_COMAP_COLS_MIN_FICO2)
                or _found_in_grid(prog, fico, prime_comap_oct25_2, PRIME_COMAP_COLS_MIN_FICO)
                or _found_in_grid(prog, fico, prime_comap_new, PRIME_COMAP_COLS_MIN_FICO)
            )
        elif pd.notna(submit_dt) and submit_dt > prime_new_cutoff:
            found = _found_in_grid(prog, fico, prime_comap_new, PRIME_COMAP_COLS_MIN_FICO)
        else:
            found = _found_in_grid(prog, fico, prime_comap, PRIME_COMAP_COLS_MIN_FICO)

        if not found:
            loan_not_in_comap.append((row['SELLER Loan #'], prog, 'PRIME'))

    return loan_not_in_comap


def check_comap_sfy(
    buy_df: pd.DataFrame,
    sfy_comap: pd.DataFrame,
    sfy_comap2: pd.DataFrame,
    sfy_comap_oct25: pd.DataFrame,
    sfy_comap_oct25_2: pd.DataFrame,
    sfy_comap_bl5: pd.DataFrame,
) -> List[Tuple[str, str, str]]:
    """Check SFY loans against CoMAP. Uses each loan's Submit Date for date-based grid (mirrors February_Baseline)."""
    loan_not_in_comap = []
    oct25_cutoff = pd.to_datetime('2025-10-24')

    check_df = buy_df[
        (buy_df['Application Type'] != 'HD NOTE') &
        (buy_df['purchase_price_check'] == True) &
        (buy_df['platform'] == 'sfy')
    ].copy()
    if 'Submit Date' in check_df.columns:
        check_df['Submit Date'] = pd.to_datetime(check_df['Submit Date'])
    else:
        check_df['Submit Date'] = pd.NaT

    for _, row in check_df.iterrows():
        fico = row['FICO Borrower']
        prog = row['loan program']
        prog = str(prog) if pd.notna(prog) else ''
        submit_dt = row['Submit Date']
        found = False

        if pd.notna(submit_dt) and submit_dt > oct25_cutoff:
            found = (
                _found_in_grid(prog, fico, sfy_comap_oct25, SFY_COMAP_COLS_MIN_FICO3)
                or _found_in_grid(prog, fico, sfy_comap_oct25_2, SFY_COMAP_COLS_MIN_FICO2)
                or _found_in_grid(prog, fico, sfy_comap_bl5, SFY_COMAP_COLS_MIN_FICO)
            )
        else:
            found = (
                _found_in_grid(prog, fico, sfy_comap, SFY_COMAP_COLS_MIN_FICO)
                or _found_in_grid(prog, fico, sfy_comap2, SFY_COMAP_COLS_MIN_FICO2)
                or _found_in_grid(prog, fico, sfy_comap_bl5, SFY_COMAP_COLS_MIN_FICO)
            )

        if not found:
            loan_not_in_comap.append((row['SELLER Loan #'], prog, 'SFY'))

    return loan_not_in_comap


def check_comap_notes(
    buy_df: pd.DataFrame,
    notes_comap: pd.DataFrame
) -> List[Tuple[str, str, str]]:
    """Check Notes loans against CoMAP."""
    loan_not_in_comap = []

    check_df = buy_df[
        (buy_df['Application Type'] == 'HD NOTE') &
        (buy_df['purchase_price_check'] == True)
    ].copy()

    for _, row in check_df.iterrows():
        fico = row['FICO Borrower']
        prog = row['loan program']
        prog = str(prog) if pd.notna(prog) else ''

        if not _found_in_grid(prog, fico, notes_comap, NOTES_COMAP_COLS_MIN_FICO):
            loan_not_in_comap.append((row['SELLER Loan #'], prog, 'NOTES'))

    return loan_not_in_comap
