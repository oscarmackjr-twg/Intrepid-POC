"""Behavioral cashflow model: CDR/CPR survival-fraction engine.

Ported from utils.py (loan_engine). Computes modeled cashflow schedules by
applying CDR (default) and CPR (prepayment) assumptions to contractual flows.

No file I/O at import — all parameters are passed as arguments.

Loan type dispatch:
    ninp / hybrid / wpdi / wpdi_bd  →  _model_ninp_wpdi()
    standard / epni / solar / standard_bd  →  _model_standard_epni()

Recovery is 3-tranche, lagged 16 / 28 / 40 months (1/3 each).

Public API:
    create_contractual_flow(...)       → contractual P&I schedule DataFrame
    price_loan_sfc_case(loan_row, df)  → (modeled_df, irr, wal)  SFC assumptions
    price_loan_our_case(loan_row, df)  → (modeled_df, irr, wal)  OUR assumptions
    xirr(values, dates)                → float
"""
from __future__ import annotations

from typing import Tuple

import numpy as np
import numpy_financial as npf
import pandas as pd
from pandas.tseries.offsets import DateOffset
from scipy.optimize import newton

# ---------------------------------------------------------------------------
# WPDI loan IDs where the promo period is capped at 12 months.
# These are legacy loans with truncated promo structures; identified manually.
# ---------------------------------------------------------------------------
WPDI_SHORT_PROMO_IDS: frozenset = frozenset({
    "SFC_5387026", "SFC_4762813", "SFC_4773432", "SFC_5086492", "SFC_5118100",
    "SFC_5211106", "SFC_5275587", "SFC_5361860", "SFC_5368751", "SFC_5431496",
    "SFC_5463542", "SFC_5491704", "SFC_5493276", "SFC_5496710", "SFC_5509444",
    "SFC_5533868", "SFC_5545063", "SFC_5568733", "SFC_5576392", "SFC_5612338",
    "SFC_5324404", "SFC_5517937", "SFC_5612811", "SFC_5635256", "SFC_5664371",
    "SFC_5728818", "SFC_5752586", "SFC_5791594", "SFC_5804963", "SFC_5831579",
    "SFC_5868362", "SFC_5865793", "SFC_5884928", "SFC_5867531", "SFC_5899605",
    "SFC_5938501", "SFC_5857664", "SFC_5992457", "SFC_6035636", "SFC_6015062",
    "SFC_6106710", "SFC_6137800", "SFC_6103974", "SFC_6116907", "SFC_6153806",
    "SFC_5929608", "SFC_6170323", "SFC_6190788", "SFC_6194378", "SFC_6232757",
    "SFC_6192857", "SFC_6253445", "SFC_6286111", "SFC_6289448", "SFC_6289486",
    "SFC_6340544", "SFC_6357984", "SFC_6221709", "SFC_6412846", "SFC_6423359",
    "SFC_6432202", "SFC_6459331", "SFC_6460832", "SFC_6473886", "SFC_6507769",
    "SFC_6482551", "SFC_6487703", "SFC_6601710", "SFC_6594697", "SFC_6614154",
    "SFC_6649460",
})

_OUTPUT_COLS = [
    "dates", "loan_dates", "modeled_interest", "modeled_principal",
    "pre_payment", "write_off", "late_fee", "recovery", "end_upb",
    "total_principal_collected", "wal", "opening_upb", "servicing_cost",
    "interest paid",
]

# Sentinel epoch used for contractual date series (absolute dates don't matter;
# the loan_dates column carries actual payment dates).
_EPOCH = pd.Timestamp("2022-01-01")


# ---------------------------------------------------------------------------
# Date helpers
# ---------------------------------------------------------------------------

def _date_range(start, n_extra: int) -> pd.DatetimeIndex:
    """Monthly date range: [start, start+1m, ..., start+n_extra months]."""
    return pd.date_range(
        start=pd.to_datetime(start),
        periods=n_extra + 1,
        freq=DateOffset(months=1),
    )


# ---------------------------------------------------------------------------
# XIRR
# ---------------------------------------------------------------------------

def xnpv(rate: float, values, dates) -> float:
    """Net present value for irregular cash flows."""
    values_arr = np.asarray(values, dtype=float)
    dates_arr = pd.to_datetime(dates).to_numpy(dtype="datetime64[ns]")
    n = min(len(values_arr), len(dates_arr))
    values_arr = values_arr[:n]
    dates_arr = dates_arr[:n]
    min_date = dates_arr.min()
    year_fracs = ((dates_arr - min_date) / np.timedelta64(1, "D")).astype(float) / 365.0
    with np.errstate(over="ignore", invalid="ignore"):
        return np.sum(values_arr / np.power(1.0 + rate, year_fracs))


def xirr(values, dates) -> float:
    """Internal rate of return for irregular cash flows (Newton's method)."""
    return newton(lambda r: xnpv(r, values, dates), 0)


# ---------------------------------------------------------------------------
# Contractual cashflow schedule
# ---------------------------------------------------------------------------

def create_contractual_flow(
    monthly_payment: float,
    loan_rate: float,
    loan_original_amount: float,
    loan_term: int,
    loan_type: str,
    promo_loan_term: int,
    loan_id: str,
    loan_date,
) -> pd.DataFrame:
    """Generate contractual P&I cashflow schedule for a single loan.

    Parameters
    ----------
    monthly_payment : float
        Scheduled monthly payment amount.
    loan_rate : float
        Annual interest rate as a decimal (e.g. 0.12 for 12%).
    loan_original_amount : float
        Original principal balance.
    loan_term : int
        Total number of payment periods (months).
    loan_type : str
        One of: 'epni', 'ninp', 'hybrid', 'wpdi', 'standard', 'solar', etc.
    promo_loan_term : int
        Number of promo (interest-free / no-payment) periods.
    loan_id : str
        Loan identifier, stored in loan_number column.
    loan_date : date-like
        First actual payment date (used as base for loan_dates series).

    Returns
    -------
    pd.DataFrame
        Columns: dates, loan_dates, principal paid, interest paid,
                 pricipal_paid_cumsum, closing balance, opening balance,
                 loan_number.
        Row 0 is a sentinel pre-period (all payments zero, opening balance = 0).
    """
    n_periods = loan_term + 1
    principals = np.zeros(n_periods, dtype=float)
    interests = np.zeros(n_periods, dtype=float)

    if loan_type == "epni":
        principals[1:] = monthly_payment
    elif loan_type in ("ninp", "hybrid"):
        amort_n = loan_term - promo_loan_term
        periods = np.arange(1, amort_n + 1)
        principals[promo_loan_term + 1:] = -1.0 * npf.ppmt(
            loan_rate / 12.0,
            periods,
            amort_n,
            loan_original_amount,
        )
        interests[promo_loan_term + 1:] = -1.0 * npf.ipmt(
            loan_rate / 12.0,
            periods,
            amort_n,
            loan_original_amount,
        )
    else:  # standard, wpdi, solar, wpdi_bd, standard_bd
        periods = np.arange(1, loan_term + 1)
        principals[1:] = -1.0 * npf.ppmt(
            loan_rate / 12.0,
            periods,
            loan_term,
            loan_original_amount,
        )
        interests[1:] = -1.0 * npf.ipmt(
            loan_rate / 12.0,
            periods,
            loan_term,
            loan_original_amount,
        )

    principal_cumsum = principals.cumsum()
    closing_balance = loan_original_amount - principal_cumsum
    opening_balance = np.empty(n_periods, dtype=float)
    opening_balance[0] = np.nan
    opening_balance[1:] = closing_balance[:-1]

    return pd.DataFrame({
        "dates": _date_range(_EPOCH, loan_term),
        "loan_dates": _date_range(loan_date, loan_term),
        "principal paid": principals,
        "interest paid": interests,
        "pricipal_paid_cumsum": principal_cumsum,
        "closing balance": closing_balance,
        "opening balance": opening_balance,
        "loan_number": loan_id,
    })


# ---------------------------------------------------------------------------
# Low-level modeled curve engines
# ---------------------------------------------------------------------------

def _model_standard_epni(
    contractual_df: pd.DataFrame,
    const_cpr: float,
    cdr: float,
    late_fee_pct: float,
    recovery_rate: float,
    servicing_cost_pct: float,
) -> pd.DataFrame:
    """Survival-fraction model for standard, epni, solar loan types.

    const_cpr and cdr are annual rates; converted to SMM internally.
    """
    df = contractual_df.sort_values("dates").reset_index(drop=True)
    n = len(df)
    opening_balance = df["opening balance"].to_numpy(dtype=float, copy=False)
    closing_balance = df["closing balance"].to_numpy(dtype=float, copy=False)
    principal_paid = df["principal paid"].to_numpy(dtype=float, copy=False)
    interest_paid = df["interest paid"].to_numpy(dtype=float, copy=False)

    cpr = np.zeros(n, dtype=float)
    cdr_arr = np.zeros(n, dtype=float)
    cpr_cdr_cum_bal = np.zeros(n, dtype=float)
    modeled_interest = np.zeros(n, dtype=float)
    modeled_principal = np.zeros(n, dtype=float)
    pre_payment = np.zeros(n, dtype=float)
    write_off = np.zeros(n, dtype=float)
    late_fee = np.zeros(n, dtype=float)
    end_upb = np.zeros(n, dtype=float)

    smm_cpr = 1.0 - (1.0 - const_cpr) ** (1.0 / 12.0)
    smm_cdr = 1.0 - (1.0 - cdr) ** (1.0 / 12.0)

    # Period 1 — seed the model
    if n > 1:
        cpr[1] = smm_cpr
        cdr_arr[1] = smm_cdr
        cpr_cdr_cum_bal[1] = 1.0 - smm_cpr - smm_cdr
        modeled_interest[1] = interest_paid[1] * (1.0 - smm_cdr)
        modeled_principal[1] = principal_paid[1] * cpr_cdr_cum_bal[1]
        pre_payment[1] = smm_cpr * opening_balance[1]
        write_off[1] = smm_cdr * opening_balance[1]
        late_fee[1] = late_fee_pct * opening_balance[1]
        end_upb[1] = (
            opening_balance[1]
            - write_off[1]
            - pre_payment[1]
            - modeled_principal[1]
        )

    # Survival ratio: scales CPR/CDR in later periods
    ratio = end_upb[1] / closing_balance[1] if n > 1 else 0.0

    # Periods 2+ — scale CPR/CDR by survival ratio
    for i in range(2, n):
        cpr[i] = ratio * cpr[i - 1]
        cdr_arr[i] = ratio * cdr_arr[i - 1]
        cpr_cdr_cum_bal[i] = cpr_cdr_cum_bal[i - 1] - cpr[i] - cdr_arr[i]
        modeled_interest[i] = interest_paid[i] * (cpr_cdr_cum_bal[i] + cpr[i])
        modeled_principal[i] = cpr_cdr_cum_bal[i] * principal_paid[i]
        pre_payment[i] = cpr[i] * opening_balance[i]
        write_off[i] = cdr_arr[i] * opening_balance[i]
        end_upb[i] = end_upb[i - 1] - write_off[i] - pre_payment[i] - modeled_principal[i]
        late_fee[i] = late_fee_pct * end_upb[i - 1]

    return _finalize(
        dates=df["dates"],
        loan_dates=df["loan_dates"],
        modeled_interest=modeled_interest,
        modeled_principal=modeled_principal,
        pre_payment=pre_payment,
        write_off=write_off,
        late_fee=late_fee,
        end_upb=end_upb,
        interest_paid=interest_paid,
        original_opening_balance=float(np.nanmax(opening_balance)),
        recovery_rate=recovery_rate,
        servicing_cost_pct=servicing_cost_pct,
    )


def _model_ninp_wpdi(
    contractual_df: pd.DataFrame,
    promo_term: int,
    cpr_schedule: np.ndarray,
    const_cpr: float,
    cdr: float,
    cdr_promo: float,
    late_fee_pct: float,
    recovery_rate: float,
    servicing_cost_pct: float,
) -> pd.DataFrame:
    """Survival-fraction model for ninp, wpdi, hybrid, wpdi_bd loan types.

    cpr_schedule  — per-period SMM values for the promo window (already in SMM).
    const_cpr, cdr, cdr_promo — annual rates; converted to SMM internally.
    """
    df = contractual_df.sort_values("dates").reset_index(drop=True)
    n = len(df)
    opening_balance = df["opening balance"].to_numpy(dtype=float, copy=False)
    closing_balance = df["closing balance"].to_numpy(dtype=float, copy=False)
    principal_paid = df["principal paid"].to_numpy(dtype=float, copy=False)
    interest_paid = df["interest paid"].to_numpy(dtype=float, copy=False)

    cpr = np.zeros(n, dtype=float)
    cdr_arr = np.zeros(n, dtype=float)
    cpr_cdr_cum_bal = np.zeros(n, dtype=float)
    modeled_interest = np.zeros(n, dtype=float)
    modeled_principal = np.zeros(n, dtype=float)
    pre_payment = np.zeros(n, dtype=float)
    write_off = np.zeros(n, dtype=float)
    late_fee = np.zeros(n, dtype=float)
    end_upb = np.zeros(n, dtype=float)

    smm_cdr = 1.0 - (1.0 - cdr) ** (1.0 / 12.0)
    smm_cdr_promo = 1.0 - (1.0 - cdr_promo) ** (1.0 / 12.0)
    smm_const_cpr = 1.0 - (1.0 - const_cpr) ** (1.0 / 12.0)

    # Period 1 — seed the model
    if n > 1:
        cpr[1] = cpr_schedule[0]
        cdr_arr[1] = smm_cdr_promo
        cpr_cdr_cum_bal[1] = 1.0 - cpr_schedule[0] - smm_cdr_promo
        modeled_interest[1] = interest_paid[1] * (1.0 - smm_cdr_promo)
        modeled_principal[1] = principal_paid[1] * cpr_cdr_cum_bal[1]
        pre_payment[1] = cpr_schedule[0] * opening_balance[1]
        write_off[1] = smm_cdr_promo * opening_balance[1]
        late_fee[1] = late_fee_pct * opening_balance[1]
        end_upb[1] = (
            opening_balance[1]
            - write_off[1]
            - pre_payment[1]
            - modeled_principal[1]
        )

    for i in range(2, n):
        if i <= promo_term:
            # Promo window: use per-period CPR schedule; scale CDR by survival
            cpr[i] = cpr_schedule[i - 1]
            cdr_arr[i] = (
                smm_cdr_promo
                * end_upb[i - 1]
                / closing_balance[i - 1]
            )
        else:
            # Post-promo: both CPR and CDR scale with cumulative survival
            cpr[i] = smm_const_cpr * cpr_cdr_cum_bal[i - 1]
            cdr_arr[i] = smm_cdr * cpr_cdr_cum_bal[i - 1]

        cpr_cdr_cum_bal[i] = cpr_cdr_cum_bal[i - 1] - cpr[i] - cdr_arr[i]
        modeled_interest[i] = interest_paid[i] * (cpr_cdr_cum_bal[i] + cpr[i])
        modeled_principal[i] = cpr_cdr_cum_bal[i] * principal_paid[i]
        write_off[i] = cdr_arr[i] * opening_balance[i]
        pre_payment[i] = cpr[i] * opening_balance[i]
        end_upb[i] = end_upb[i - 1] - write_off[i] - pre_payment[i] - modeled_principal[i]
        late_fee[i] = late_fee_pct * end_upb[i - 1]

        if end_upb[i] <= 1.0:
            break

    return _finalize(
        dates=df["dates"],
        loan_dates=df["loan_dates"],
        modeled_interest=modeled_interest,
        modeled_principal=modeled_principal,
        pre_payment=pre_payment,
        write_off=write_off,
        late_fee=late_fee,
        end_upb=end_upb,
        interest_paid=interest_paid,
        original_opening_balance=float(np.nanmax(opening_balance)),
        recovery_rate=recovery_rate,
        servicing_cost_pct=servicing_cost_pct,
    )


def _finalize(
    dates,
    loan_dates,
    modeled_interest: np.ndarray,
    modeled_principal: np.ndarray,
    pre_payment: np.ndarray,
    write_off: np.ndarray,
    late_fee: np.ndarray,
    end_upb: np.ndarray,
    interest_paid: np.ndarray,
    original_opening_balance: float,
    recovery_rate: float,
    servicing_cost_pct: float,
) -> pd.DataFrame:
    """Add 3-tranche recovery, WAL, servicing cost, and select output columns."""
    n = len(modeled_interest)
    out_len = n + 40

    dates_idx = pd.DatetimeIndex(pd.to_datetime(dates))
    loan_dates_idx = pd.DatetimeIndex(pd.to_datetime(loan_dates))
    dates_arr = np.empty(out_len, dtype="datetime64[ns]")
    loan_dates_arr = np.empty(out_len, dtype="datetime64[ns]")
    dates_arr[:n] = dates_idx.to_numpy()
    loan_dates_arr[:n] = loan_dates_idx.to_numpy()
    dates_arr[n:] = _date_range(dates_idx[-1] + DateOffset(months=1), 39).to_numpy()
    loan_dates_arr[n:] = _date_range(loan_dates_idx[-1] + DateOffset(months=1), 39).to_numpy()

    modeled_interest_out = np.zeros(out_len, dtype=float)
    modeled_principal_out = np.zeros(out_len, dtype=float)
    pre_payment_out = np.zeros(out_len, dtype=float)
    write_off_out = np.zeros(out_len, dtype=float)
    late_fee_out = np.zeros(out_len, dtype=float)
    end_upb_out = np.zeros(out_len, dtype=float)
    interest_paid_out = np.zeros(out_len, dtype=float)

    modeled_interest_out[:n] = modeled_interest
    modeled_principal_out[:n] = modeled_principal
    pre_payment_out[:n] = pre_payment
    write_off_out[:n] = write_off
    late_fee_out[:n] = late_fee
    end_upb_out[:n] = end_upb
    interest_paid_out[:n] = interest_paid

    recovery = np.zeros(out_len, dtype=float)
    for lag in (16, 28, 40):
        recovery[lag:] += write_off_out[:-lag] * recovery_rate / 3.0

    total_principal_collected = modeled_principal_out + pre_payment_out + recovery
    total_pc = total_principal_collected.sum()
    wal = (
        (total_principal_collected / total_pc) * np.arange(out_len, dtype=float)
        if total_pc > 0 else np.zeros(out_len, dtype=float)
    )

    opening_upb = np.zeros(out_len, dtype=float)
    if out_len > 1:
        opening_upb[1:] = end_upb_out[:-1]
        opening_upb[1] = original_opening_balance
    servicing_cost = opening_upb * (1.0 / 12.0) * servicing_cost_pct

    return pd.DataFrame({
        "dates": dates_arr,
        "loan_dates": loan_dates_arr,
        "modeled_interest": modeled_interest_out,
        "modeled_principal": modeled_principal_out,
        "pre_payment": pre_payment_out,
        "write_off": write_off_out,
        "late_fee": late_fee_out,
        "recovery": recovery,
        "end_upb": end_upb_out,
        "total_principal_collected": total_principal_collected,
        "wal": wal,
        "opening_upb": opening_upb,
        "servicing_cost": servicing_cost,
        "interest paid": interest_paid_out,
    })[_OUTPUT_COLS]


# ---------------------------------------------------------------------------
# CPR array helpers
# ---------------------------------------------------------------------------

def _parse_cpr(cpr_str: str) -> np.ndarray:
    """Parse semicolon-delimited CPR string to numpy array (already in SMM)."""
    return np.fromstring(str(cpr_str), sep=";", dtype=float)


def _cap_cpr(cpr: np.ndarray) -> np.ndarray:
    """Ensure cumulative CPR does not exceed 1.0."""
    cpr = cpr.copy()
    cumsum = np.cumsum(cpr)
    over_idx = np.flatnonzero(cumsum > 1.0)
    if over_idx.size:
        i = int(over_idx[0])
        cpr[i] -= cumsum[i] - 1.0
        cpr[i + 1:] = 0.0
    return cpr


# ---------------------------------------------------------------------------
# WPDI cash/WAL adjustment + IRR builder
# ---------------------------------------------------------------------------

def _build_result(
    curr_df: pd.DataFrame,
    contractual_df: pd.DataFrame,
    loan_row,
    loan_type: str,
    promo_loan_term: int,
    resolved_cpr: np.ndarray,
) -> Tuple[pd.DataFrame, float, float]:
    """Attach loan metadata, compute XIRR and WAL, handle WPDI adjustment."""
    purchase_price = float(loan_row["modeled_purchase_price"]) * float(loan_row["Orig. Balance"])

    curr_df = curr_df.reset_index(drop=True).copy()
    curr_df["cash_adjustment"] = 0.0
    curr_df["wal_adjustment"] = 0.0
    curr_df["purchase_price"] = purchase_price
    curr_df["loan_number"] = loan_row["SELLER Loan #"]
    curr_df["loan_program"] = loan_row["loan program"]
    curr_df["platform"] = loan_row["platform"]

    arr = [-purchase_price]

    if loan_type in ("wpdi", "wpdi_bd"):
        # WPDI: accrued interest recapture adjustment during promo window
        interest_promo = contractual_df["interest paid"].values[1: promo_loan_term + 1]
        cash_adj = np.cumsum(interest_promo) * resolved_cpr
        adj_cpr = np.insert(np.sum(resolved_cpr) - np.cumsum(resolved_cpr), 0, np.sum(resolved_cpr))[:promo_loan_term]
        total_cf = interest_promo * adj_cpr - cash_adj

        pad_len = curr_df.shape[0] - 1 - promo_loan_term
        padded_cash_adj = np.pad(cash_adj, (0, pad_len), "constant")
        padded_total_cf = np.pad(total_cf, (0, pad_len), "constant")

        pool = curr_df["total_principal_collected"].values[1:] + padded_total_cf
        pool_sum = pool.sum()
        wal = (
            sum((pool / pool_sum) * curr_df.index.values[1:]) / 12.0
            if pool_sum > 0 else 0.0
        )

        cashflow_arr = (
            (curr_df["modeled_interest"] + curr_df["modeled_principal"]
             + curr_df["pre_payment"] + curr_df["recovery"]
             - curr_df["servicing_cost"]).iloc[1:]
            - padded_cash_adj
        )
        arr.extend(cashflow_arr.values)
        irr = xirr(arr, contractual_df["loan_dates"])

        curr_df.loc[1:, "cash_adjustment"] = padded_cash_adj
        curr_df.loc[1:, "wal_adjustment"] = padded_total_cf

    else:
        wal = curr_df["wal"].sum() / 12.0
        arr.extend(
            (curr_df["modeled_principal"] + curr_df["pre_payment"]
             + curr_df["recovery"] + curr_df["modeled_interest"]
             - curr_df["servicing_cost"])[1:-1].values
        )
        irr = xirr(arr, contractual_df["loan_dates"])

    return curr_df, irr, wal


# ---------------------------------------------------------------------------
# Public high-level entry points
# ---------------------------------------------------------------------------

def price_loan_sfc_case(
    loan_row,
    contractual_df: pd.DataFrame,
    promo_cpr_shock: float = 1.0,
    cpr_shock: float = 1.0,
    cdr_shock: float = 1.0,
    promo_cdr_shock: float = 1.0,
) -> Tuple[pd.DataFrame, float, float]:
    """Price a loan using SFC (seller) CDR/CPR base assumptions.

    Parameters
    ----------
    loan_row : dict or pd.Series
        Row from current_assets.csv with MASTER_SHEET columns pre-merged.
        Required fields: type, promo_term, cpr, constant_cpr, cdr, cdr_promo,
        late_percent, recovery_percent, servicing_cost, modeled_purchase_price,
        Orig. Balance, SELLER Loan #, loan program, platform.
    contractual_df : pd.DataFrame
        Output of create_contractual_flow().
    *_shock : float
        Multiplier shocks applied to CPR/CDR (1.0 = no shock).

    Returns
    -------
    (modeled_df, irr, wal)
    """
    loan_id = loan_row["SELLER Loan #"]
    loan_type = str(loan_row["type"])
    promo_loan_term = int(loan_row["promo_term"])

    cpr = _parse_cpr(loan_row["cpr"]) * promo_cpr_shock
    const_cpr = float(loan_row["constant_cpr"]) * cpr_shock
    cdr = float(loan_row["cdr"]) * cdr_shock
    cdr_promo = float(loan_row["cdr_promo"]) * promo_cdr_shock
    late_fee_pct = float(loan_row["late_percent"])
    recovery_rate = float(loan_row["recovery_percent"])
    servicing_cost_pct = float(loan_row["servicing_cost"])

    if loan_id in WPDI_SHORT_PROMO_IDS:
        cpr = cpr[:12]
        promo_loan_term = 12

    cpr = _cap_cpr(cpr)

    if loan_type in ("ninp", "wpdi", "hybrid", "wpdi_bd"):
        curr_df = _model_ninp_wpdi(
            contractual_df, promo_loan_term, cpr, const_cpr,
            cdr, cdr_promo, late_fee_pct, recovery_rate, servicing_cost_pct,
        )
    else:  # standard, epni, solar, standard_bd
        curr_df = _model_standard_epni(
            contractual_df, const_cpr, cdr,
            late_fee_pct, recovery_rate, servicing_cost_pct,
        )

    return _build_result(curr_df, contractual_df, loan_row, loan_type, promo_loan_term, cpr)


def price_loan_our_case(
    loan_row,
    contractual_df: pd.DataFrame,
    promo_cpr_shock: float = 1.0,
    cpr_shock: float = 1.0,
    cdr_shock: float = 1.0,
    promo_cdr_shock: float = 1.0,
) -> Tuple[pd.DataFrame, float, float]:
    """Price a loan using OUR (stressed) CDR/CPR assumptions.

    Uses proposed_cdr / proposed_cpr / proposed_promo_cpr_percent columns
    instead of the SFC base values.

    Parameters and return value identical to price_loan_sfc_case().
    """
    loan_id = loan_row["SELLER Loan #"]
    loan_type = str(loan_row["type"])
    promo_loan_term = int(loan_row["promo_term"])

    cpr = _parse_cpr(loan_row["cpr"]) * float(loan_row["proposed_promo_cpr_percent"]) * promo_cpr_shock
    const_cpr = float(loan_row["proposed_cpr"]) * cpr_shock
    cdr = float(loan_row["proposed_cdr"]) * cdr_shock
    cdr_promo = float(loan_row["proposed_cdr_promo"]) * promo_cdr_shock
    late_fee_pct = float(loan_row["late_percent"])
    recovery_rate = float(loan_row["recovery_percent"])
    servicing_cost_pct = float(loan_row["servicing_cost"])

    if loan_id in WPDI_SHORT_PROMO_IDS:
        cpr = cpr[:12]
        promo_loan_term = 12

    cpr = _cap_cpr(cpr)

    if loan_type in ("ninp", "wpdi", "hybrid", "wpdi_bd"):
        curr_df = _model_ninp_wpdi(
            contractual_df, promo_loan_term, cpr, const_cpr,
            cdr, cdr_promo, late_fee_pct, recovery_rate, servicing_cost_pct,
        )
    else:  # standard, epni, solar, standard_bd
        curr_df = _model_standard_epni(
            contractual_df, const_cpr, cdr,
            late_fee_pct, recovery_rate, servicing_cost_pct,
        )

    return _build_result(curr_df, contractual_df, loan_row, loan_type, promo_loan_term, cpr)
