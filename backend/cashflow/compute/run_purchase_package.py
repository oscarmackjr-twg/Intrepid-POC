"""Purchase-package cashflow generator for lender-specific sale notices.

Implements the legacy purchase-package flow used by the CIBC and SG scripts.
It builds the buy population from PRIME and SFY Exhibit A workbooks plus the
master-sheet assumptions, then writes:

- TWG_cashflows_<buy_num>_<buyer>.csv
- SFC_cashflows_<buy_num>_<buyer>.csv
- loans_data_<buy_num>_<buyer>.csv
- cashflows_<buy_num>_<target>_<buyer>.xlsx
"""
from __future__ import annotations

import argparse
from pathlib import Path
from typing import Callable

import numpy as np
import numpy_financial as npf
import pandas as pd

from cashflow.compute.behavioral_model import (
    create_contractual_flow,
    price_loan_our_case,
    price_loan_sfc_case,
)

BD_PROGRAMS = frozenset({"6 Mth BD WPDI", "Unsec Std - 1490 - 120", "6 Mth BD WPDI 12S"})
RAW_CASHFLOW_COLS = [
    "dates", "loan_dates", "modeled_interest", "modeled_principal", "pre_payment",
    "write_off", "late_fee", "recovery", "end_upb", "total_principal_collected", "wal",
    "opening_upb", "servicing_cost", "interest paid", "loan_number", "loan_program",
    "platform", "cash_adjustment", "wal_adjustment", "purchase_price", "irr_support",
    "servicing_percent", "opening_mv_upb",
]
LOANS_DATA_COLS = [
    "loan_program", "loan_id", "platform", "Original Loan Amount", "type", "promo_term",
    "loan_term", "SFC_loan_term", "SFC_coupon", "coupon", "STATED_APR", "STATED_pmt",
    "OUR_pmt", "servicing_percent", "irr_support", "modeled_purchase_price", "IRR", "WAL",
    "SFC_IRR", "SFC_WAL", "SFC_gross_dlq", "SFC_gross_dlq_with_recoveries",
    "OUR_gross_dlq", "OUR_gross_dlq_with_recoveries",
]


def _resolve_loan_term(row: dict) -> int:
    t = str(row["type"])
    if "ninp" in t:
        return int(row["Term"]) + int(row["promo_term"])
    if t == "epni":
        return int(row["promo_term"])
    return int(row["Term"])


def _resolve_coupon(row: dict) -> float:
    t = str(row["type"])
    if t in ("hybrid", "ninp"):
        coupon = float(row["APR"]) / 100.0 if t == "ninp" else float(row["coupon"]) / 10_000.0
    elif t == "epni":
        coupon = float(row["coupon"]) / 10_000.0
    else:
        coupon = float(row["APR"]) / 100.0
    if str(row.get("Property State", "")) == "CT" and float(row.get("coupon", 0)) > 1200:
        coupon = 0.1199
    return coupon


def _resolve_stated_payment(row: dict, loan_term: int) -> float:
    if str(row["type"]) == "epni":
        return float(row["Orig. Balance"]) / loan_term
    return float(row["Monthly Payment"])


def _resolve_modeled_payment(loan_type: str, coupon: float, loan_amt: float, loan_term: int, promo_term: int) -> float:
    if loan_type in ("hybrid", "ninp"):
        return float(-1.0 * npf.pmt(coupon / 12.0, loan_term - promo_term, loan_amt))
    return float(-1.0 * npf.pmt(coupon / 12.0, loan_term, loan_amt))


def _resolve_loan_date(row: dict) -> pd.Timestamp:
    pay_date = pd.to_datetime(row["Monthly Payment Date"])
    if str(row["type"]) in ("hybrid", "ninp"):
        return pay_date - pd.DateOffset(months=int(row["promo_term"]))
    return pay_date


def _read_sale_notice(path: Path, platform: str) -> pd.DataFrame:
    df = pd.read_excel(path)
    drop_cols = [col for col in ["Unnamed: 0", "tags", "final"] if col in df.columns]
    if drop_cols:
        df = df.drop(columns=drop_cols)
    if "Application Type" in df.columns:
        df = df.loc[:, :"Application Type"]
    df["Platform"] = platform.upper()
    return df


def _load_master_sheets(master_sheet: Path, notes_sheet: Path) -> pd.DataFrame:
    master = pd.read_excel(master_sheet)
    master["Platform"] = master["platform"].str.upper()
    notes = pd.read_excel(notes_sheet)
    notes["loan program"] = notes["loan program"].astype(str) + "notes"
    notes["Platform"] = notes["platform"].str.upper()
    return pd.concat([master, notes], ignore_index=True)


def _build_purchase_population(
    prime_file: Path,
    sfy_file: Path,
    master_sheet: Path,
    notes_sheet: Path,
    purchase_date: str,
    irr_target: float,
) -> pd.DataFrame:
    assumptions = _load_master_sheets(master_sheet, notes_sheet)
    prime_df = _read_sale_notice(prime_file, "PRIME")
    sfy_df = _read_sale_notice(sfy_file, "SFY")

    buy_df = pd.concat([prime_df, sfy_df], ignore_index=True)
    buy_df.rename(columns={"Loan Program": "loan program"}, inplace=True)
    buy_df["Repurchase"] = False
    buy_df["Repurchase_Date"] = None
    buy_df["Purchase_Date"] = pd.to_datetime(purchase_date)
    buy_df["Excess_Asset"] = False
    buy_df["Borrowing_Base_eligible"] = True
    buy_df["IRR Support Target"] = irr_target
    buy_df["Submit Date"] = pd.to_datetime(buy_df["Submit Date"])
    buy_df["Purchase_Date"] = pd.to_datetime(buy_df["Purchase_Date"])
    buy_df["Monthly Payment Date"] = pd.to_datetime(buy_df["Monthly Payment Date"])
    buy_df = buy_df.merge(assumptions, on=["loan program", "Platform"], how="left")
    buy_df["platform"] = buy_df["platform"].str.lower()

    wpdi_mask = (
        (buy_df["type"] == "wpdi")
        & (buy_df["new_programs"] == False)
        & (buy_df["Submit Date"] < pd.Timestamp("2025-01-07"))
    )
    override_pairs = [
        ("cdr", "cdr_old"),
        ("proposed_cdr", "proposed_cdr_old"),
        ("cdr_promo", "cdr_promo_old"),
        ("proposed_cdr_promo", "proposed_cdr_promo_old"),
    ]
    for target_col, source_col in override_pairs:
        if source_col in buy_df.columns:
            buy_df.loc[wpdi_mask, target_col] = buy_df.loc[wpdi_mask, source_col]

    if buy_df["SELLER Loan #"].duplicated().any():
        raise ValueError("Duplicate SELLER Loan # values found in purchase population.")
    return buy_df


def _process_purchase_loan(row: dict, cprshock: float, cdrshock: float):
    loan_amt = float(row["Orig. Balance"])
    loan_type = str(row["type"])
    promo_term = int(row["promo_term"])
    loan_term = _resolve_loan_term(row)
    coupon = _resolve_coupon(row)
    stated_payment = _resolve_stated_payment(row, loan_term)
    modeled_payment = _resolve_modeled_payment(loan_type, coupon, loan_amt, loan_term, promo_term)
    loan_date = _resolve_loan_date(row)

    contractual = create_contractual_flow(
        monthly_payment=stated_payment,
        loan_rate=coupon,
        loan_original_amount=loan_amt,
        loan_term=loan_term,
        loan_type=loan_type,
        promo_loan_term=promo_term,
        loan_id=row["SELLER Loan #"],
        loan_date=loan_date,
    )

    sfc_df, sfc_irr, sfc_wal = price_loan_sfc_case(row, contractual, cpr_shock=cprshock, cdr_shock=cdrshock)
    our_df, our_irr, our_wal = price_loan_our_case(row, contractual, cpr_shock=cprshock, cdr_shock=cdrshock)

    irr_support = float(row["irr_support"])
    servicing_percent = float(row["servicing_cost"])
    pp = float(row["modeled_purchase_price"])
    for frame in (sfc_df, our_df):
        frame["irr_support"] = irr_support
        frame["servicing_percent"] = servicing_percent
        frame["opening_mv_upb"] = frame["opening_upb"] * pp

    loan_summary = {
        "loan_program": row["loan program"],
        "loan_id": row["SELLER Loan #"],
        "platform": row["platform"],
        "Original Loan Amount": loan_amt,
        "type": loan_type,
        "promo_term": promo_term,
        "loan_term": loan_term,
        "SFC_loan_term": row.get("loan_term", loan_term),
        "SFC_coupon": row.get("coupon"),
        "coupon": coupon,
        "STATED_APR": row.get("APR"),
        "STATED_pmt": stated_payment,
        "OUR_pmt": modeled_payment,
        "servicing_percent": servicing_percent,
        "irr_support": irr_support,
        "modeled_purchase_price": pp,
        "IRR": our_irr,
        "WAL": our_wal,
        "SFC_IRR": sfc_irr,
        "SFC_WAL": sfc_wal,
        "SFC_gross_dlq": sfc_df["write_off"].sum() / loan_amt,
        "SFC_gross_dlq_with_recoveries": (sfc_df["write_off"] - sfc_df["recovery"]).sum() / loan_amt,
        "OUR_gross_dlq": our_df["write_off"].sum() / loan_amt,
        "OUR_gross_dlq_with_recoveries": (our_df["write_off"] - our_df["recovery"]).sum() / loan_amt,
    }

    return (
        sfc_df[RAW_CASHFLOW_COLS].copy(),
        our_df[RAW_CASHFLOW_COLS].copy(),
        loan_summary,
    )


def _portfolio_irr_support(
    sfc_cashflows: pd.DataFrame,
    our_cashflows: pd.DataFrame,
    purchase_price_sum: float,
    target_pct: float,
) -> pd.DataFrame:
    if sfc_cashflows.empty or our_cashflows.empty:
        return pd.DataFrame()

    sfc = sfc_cashflows.copy()
    our = our_cashflows.copy()
    sfc["reserve_cost"] = sfc["servicing_cost"] * (sfc["irr_support"] / sfc["servicing_percent"])
    our["reserve_cost"] = our["servicing_cost"] * (our["irr_support"] / our["servicing_percent"])

    base_data = sfc.groupby("dates").agg({
        "modeled_interest": np.sum,
        "modeled_principal": np.sum,
        "opening_upb": np.sum,
        "pre_payment": np.sum,
        "write_off": np.sum,
        "late_fee": np.sum,
        "recovery": np.sum,
        "servicing_cost": np.sum,
        "total_principal_collected": np.sum,
        "reserve_cost": np.sum,
        "cash_adjustment": np.sum,
        "interest paid": np.sum,
        "wal_adjustment": np.sum,
    }).reset_index()
    x2_data = our.groupby("dates").agg({
        "modeled_interest": np.sum,
        "modeled_principal": np.sum,
        "pre_payment": np.sum,
        "write_off": np.sum,
        "late_fee": np.sum,
        "recovery": np.sum,
        "servicing_cost": np.sum,
        "reserve_cost": np.sum,
        "total_principal_collected": np.sum,
        "cash_adjustment": np.sum,
        "interest paid": np.sum,
        "wal_adjustment": np.sum,
        "irr_support": "unique",
        "servicing_percent": "unique",
        "opening_upb": np.sum,
        "opening_mv_upb": np.sum,
    }).reset_index()

    x2_data["total_inflow"] = (
        x2_data["modeled_interest"] + x2_data["modeled_principal"] + x2_data["pre_payment"]
        + x2_data["recovery"] - x2_data["cash_adjustment"] - x2_data["servicing_cost"]
    )
    base_data["total_base_inflow"] = (
        base_data["modeled_interest"] + base_data["modeled_principal"] + base_data["pre_payment"]
        + base_data["recovery"] - base_data["cash_adjustment"] - base_data["servicing_cost"]
    )
    x2_data = x2_data.merge(base_data[["dates", "total_base_inflow"]], on="dates", how="left")
    x2_data["reserve_cost_cumsum"] = x2_data["reserve_cost"].cumsum()
    x2_data["Reverse_Servicing_cost_addition"] = 0.0
    x2_data.reset_index(drop=True, inplace=True)

    irr_arr = np.array([-1.0 * purchase_price_sum], dtype=float)
    target_yield = target_pct / 100.0
    year_vals: dict[int, float] = {}

    for year in range(1, 11):
        cutoff_idx = year * 12
        if cutoff_idx >= len(x2_data):
            year_vals[year] = 0.0
            continue
        new_yr_col = np.concatenate((
            irr_arr,
            x2_data["total_inflow"].iloc[1: cutoff_idx + 1].to_numpy(dtype=float),
            x2_data["total_base_inflow"].iloc[cutoff_idx + 1:].to_numpy(dtype=float),
        ))
        curr_yr_val = new_yr_col[cutoff_idx]
        if year > 1:
            for prior_year in range(1, year):
                prior_idx = prior_year * 12
                if prior_idx < len(new_yr_col):
                    new_yr_col[prior_idx] += year_vals[prior_year]
        start, end = 0.0, 100_000_000.0
        curr_irr = npf.irr(new_yr_col) * 12
        if curr_irr > target_yield:
            year_vals[year] = 0.0
        else:
            while start < end:
                bump = (start + end) / 2.0
                new_yr_col[cutoff_idx] = curr_yr_val + bump
                curr_irr = npf.irr(new_yr_col) * 12
                if abs(target_yield * 100 - curr_irr * 100) < 0.001:
                    year_vals[year] = bump
                    break
                if curr_irr < target_yield:
                    start = bump + 1.0
                else:
                    end = bump - 1.0
            else:
                year_vals[year] = max(start - 1.0, 0.0)

        subtract_val = min(float(x2_data["reserve_cost_cumsum"].iloc[cutoff_idx]), year_vals[year])
        x2_data.loc[cutoff_idx:, "reserve_cost_cumsum"] = (
            x2_data.loc[cutoff_idx:, "reserve_cost_cumsum"] - subtract_val
        )
        year_vals[year] = subtract_val
        new_yr_col[cutoff_idx] = curr_yr_val + subtract_val
        x2_data[f"year_{year}"] = new_yr_col
        x2_data.loc[cutoff_idx, "Reverse_Servicing_cost_addition"] = subtract_val

    return x2_data


def _build_shift_stack(df: pd.DataFrame, left_col: str, right_col: str, left_label: str, right_label: str) -> pd.DataFrame:
    stack = df[["dates", left_col]].merge(df[["dates", right_col]], on="dates", how="outer")
    stack["Total_UPB"] = stack[left_col] + stack[right_col]
    for i in range(1, 18):
        stack[f"{i+1}_{left_col}"] = stack[left_col].shift(i)
        stack[f"{i+1}_{right_col}"] = stack[right_col].shift(i)
        stack[f"{i+1}_Total_UPB"] = stack["Total_UPB"].shift(i)
    left_cols = [col for col in stack.columns if left_col in col]
    right_cols = [col for col in stack.columns if right_col in col]
    total_cols = [col for col in stack.columns if "Total_UPB" in col]
    stack[left_label] = stack[left_cols].sum(axis=1)
    stack[right_label] = stack[right_cols].sum(axis=1)
    stack["Pool Total UPB"] = stack[total_cols].sum(axis=1)
    return stack


def _write_cibc_workbook(
    output_path: Path,
    loans_df: pd.DataFrame,
    sfc_cashflows: pd.DataFrame,
    our_cashflows: pd.DataFrame,
    target: float,
) -> None:
    prime_data = loans_df[loans_df["platform"] == "prime"].copy()
    sfy_data = loans_df[loans_df["platform"] == "sfy"].copy()

    prime_sfc = sfc_cashflows[sfc_cashflows["platform"] == "prime"].copy()
    prime_our = our_cashflows[our_cashflows["platform"] == "prime"].copy()
    sfy_sfc = sfc_cashflows[sfc_cashflows["platform"] == "sfy"].copy()
    sfy_our = our_cashflows[our_cashflows["platform"] == "sfy"].copy()

    portfolio_level_prime = _portfolio_irr_support(prime_sfc, prime_our, prime_data["Original Loan Amount"].mul(prime_data["modeled_purchase_price"]).sum(), target)
    portfolio_level_sfy = _portfolio_irr_support(sfy_sfc, sfy_our, sfy_data["Original Loan Amount"].mul(sfy_data["modeled_purchase_price"]).sum(), target)

    bd_sfc = sfc_cashflows[sfc_cashflows["loan_program"].isin(BD_PROGRAMS)].copy()
    bd_our = our_cashflows[our_cashflows["loan_program"].isin(BD_PROGRAMS)].copy()
    non_bd_sfc = sfc_cashflows[~sfc_cashflows["loan_program"].isin(BD_PROGRAMS)].copy()
    non_bd_our = our_cashflows[~our_cashflows["loan_program"].isin(BD_PROGRAMS)].copy()

    def _portfolio_level(df: pd.DataFrame) -> pd.DataFrame:
        out = df.copy()
        out["reserve_cost"] = out["servicing_cost"] * (out["irr_support"] / out["servicing_percent"])
        return out.groupby("dates").agg({
            "modeled_interest": np.sum,
            "modeled_principal": np.sum,
            "pre_payment": np.sum,
            "write_off": np.sum,
            "late_fee": np.sum,
            "recovery": np.sum,
            "servicing_cost": np.sum,
            "total_principal_collected": np.sum,
            "cash_adjustment": np.sum,
            "interest paid": np.sum,
            "wal_adjustment": np.sum,
            "reserve_cost": np.sum,
            "irr_support": "unique",
            "servicing_percent": "unique",
            "opening_upb": np.sum,
            "opening_mv_upb": np.sum,
        }).reset_index()

    portfolio_level_bd = _portfolio_level(bd_our)
    portfolio_level_non_bd = _portfolio_level(non_bd_our)

    bd_columns = ["dates"] + [f"BD_{col}" for col in portfolio_level_bd.columns if col != "dates"]
    non_bd_columns = ["dates"] + [f"Non_BD_{col}" for col in portfolio_level_non_bd.columns if col != "dates"]
    portfolio_level_bd.columns = bd_columns
    portfolio_level_non_bd.columns = non_bd_columns

    portfolio_level_bd["int-CA"] = portfolio_level_bd["BD_modeled_interest"] - portfolio_level_bd["BD_cash_adjustment"]
    portfolio_level_non_bd["int-CA"] = portfolio_level_non_bd["Non_BD_modeled_interest"] - portfolio_level_non_bd["Non_BD_cash_adjustment"]

    bd_df = portfolio_level_bd[["dates", "BD_opening_upb", "BD_opening_mv_upb"]].reset_index(drop=False).iloc[1:].copy()
    non_bd_df = portfolio_level_non_bd[["dates", "Non_BD_opening_upb", "Non_BD_opening_mv_upb"]].reset_index(drop=False).iloc[1:].copy()
    upb_df = bd_df[["dates", "BD_opening_upb"]].merge(non_bd_df[["dates", "Non_BD_opening_upb"]], on="dates", how="outer")
    upbmv_df = bd_df[["dates", "BD_opening_mv_upb"]].merge(non_bd_df[["dates", "Non_BD_opening_mv_upb"]], on="dates", how="outer")
    upb_df = _build_shift_stack(upb_df, "BD_opening_upb", "Non_BD_opening_upb", "Pool BD UPB", "Pool Non BD UPB")
    upbmv_df = _build_shift_stack(upbmv_df, "BD_opening_mv_upb", "Non_BD_opening_mv_upb", "Pool BD UPB", "Pool Non BD UPB")

    prime_cols = ["dates"] + [f"prime_{col}" for col in portfolio_level_prime.columns if col != "dates"]
    sfy_cols = ["dates"] + [f"sfy_{col}" for col in portfolio_level_sfy.columns if col != "dates"]
    portfolio_level_prime.columns = prime_cols
    portfolio_level_sfy.columns = sfy_cols
    combined_data = portfolio_level_prime.merge(portfolio_level_sfy, on="dates", how="outer")
    common_cols = [
        "modeled_interest", "modeled_principal", "pre_payment", "write_off", "late_fee", "recovery",
        "servicing_cost", "total_principal_collected", "cash_adjustment", "interest paid",
        "wal_adjustment", "reserve_cost_cumsum", "Reverse_Servicing_cost_addition",
    ]
    for col in common_cols:
        combined_data[col] = combined_data.get(f"prime_{col}", 0).fillna(0) + combined_data.get(f"sfy_{col}", 0).fillna(0)

    sfy_mv = portfolio_level_sfy[["dates", "sfy_opening_mv_upb"]].reset_index(drop=False).iloc[1:].copy()
    prime_mv = portfolio_level_prime[["dates", "prime_opening_mv_upb"]].reset_index(drop=False).iloc[1:].copy()
    mv_prime_sfy_df = sfy_mv[["dates", "sfy_opening_mv_upb"]].merge(
        prime_mv[["dates", "prime_opening_mv_upb"]], on="dates", how="outer"
    )
    mv_prime_sfy_df = _build_shift_stack(
        mv_prime_sfy_df,
        "sfy_opening_mv_upb",
        "prime_opening_mv_upb",
        "Pool SFY UPB",
        "Pool PRIME UPB",
    )

    with pd.ExcelWriter(output_path, engine="openpyxl") as writer:
        combined_data.loc[:, ["reserve_cost_cumsum", "Reverse_Servicing_cost_addition"]].to_excel(
            writer, sheet_name="IRR support"
        )
        portfolio_level_bd[[
            "dates", "BD_modeled_principal", "BD_pre_payment", "BD_recovery", "BD_write_off",
            "int-CA", "BD_late_fee", "BD_servicing_cost", "BD_modeled_interest",
            "BD_total_principal_collected", "BD_cash_adjustment", "BD_wal_adjustment",
        ]].to_excel(writer, sheet_name="BD Cashflows")
        portfolio_level_non_bd[[
            "dates", "Non_BD_modeled_principal", "Non_BD_pre_payment", "Non_BD_recovery",
            "Non_BD_write_off", "int-CA", "Non_BD_late_fee", "Non_BD_servicing_cost",
            "Non_BD_modeled_interest", "Non_BD_total_principal_collected",
            "Non_BD_cash_adjustment", "Non_BD_wal_adjustment",
        ]].to_excel(writer, sheet_name="Non BD cashflows")
        upb_df[["dates", "Pool BD UPB", "Pool Non BD UPB"]].to_excel(writer, sheet_name="18 mth Stack")
        upbmv_df[["dates", "Pool BD UPB", "Pool Non BD UPB"]].to_excel(writer, sheet_name="Market Value UPB 18 mth Stack")
        mv_prime_sfy_df[["dates", "Pool SFY UPB", "Pool PRIME UPB"]].to_excel(writer, sheet_name="PRIME & SFY Market Value UPB 18")
        prime_data.to_excel(writer, sheet_name="PRIME Data")
        sfy_data.to_excel(writer, sheet_name="SFY Data")


def run_purchase_package(
    prime_file: str,
    sfy_file: str,
    master_sheet: str,
    notes_sheet: str,
    purchase_date: str,
    output_dir: str,
    buy_num: str,
    buyer: str = "cibc",
    irr_target: float = 7.9,
    cprshock: float = 1.0,
    cdrshock: float = 1.0,
    progress_callback: Callable[[int, str], None] | None = None,
    should_cancel: Callable[[], bool] | None = None,
) -> dict[str, str]:
    buyer_norm = buyer.lower()
    if progress_callback:
        progress_callback(2, f"Loading {buyer_norm.upper()} purchase population")

    population = _build_purchase_population(
        Path(prime_file),
        Path(sfy_file),
        Path(master_sheet),
        Path(notes_sheet),
        purchase_date,
        irr_target,
    )

    sfc_frames: list[pd.DataFrame] = []
    our_frames: list[pd.DataFrame] = []
    loan_rows: list[dict] = []
    total = len(population)
    if progress_callback:
        progress_callback(8, f"Prepared {total:,} loans")

    for idx, (_, row) in enumerate(population.iterrows(), 1):
        if should_cancel and should_cancel():
            raise InterruptedError("Cashflow job cancelled.")
        if idx % 100 == 0 or idx == total:
            print(f"  {idx}/{total} ({idx/total*100:.0f}%) …")
        if progress_callback and (idx == total or idx % max(25, total // 20 or 1) == 0):
            progress = min(82, 8 + int((idx / max(total, 1)) * 70))
            progress_callback(progress, f"Processed {idx:,} of {total:,} {buyer_norm.upper()} loans")
        sfc_df, our_df, summary = _process_purchase_loan(row.to_dict(), cprshock, cdrshock)
        sfc_frames.append(sfc_df)
        our_frames.append(our_df)
        loan_rows.append(summary)

    sfc_cashflows = pd.concat(sfc_frames, ignore_index=True)
    our_cashflows = pd.concat(our_frames, ignore_index=True)
    loans_df = pd.DataFrame(loan_rows)[LOANS_DATA_COLS]

    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    if progress_callback:
        progress_callback(88, "Writing raw cashflow files")
    raw_suffix = f"{buy_num}_{buyer_norm}"
    workbook_name = f"cashflows_{buy_num}_{irr_target}_{buyer_norm}.xlsx"

    sfc_csv = output_path / f"SFC_cashflows_{raw_suffix}.csv"
    our_csv = output_path / f"TWG_cashflows_{raw_suffix}.csv"
    loans_csv = output_path / f"loans_data_{raw_suffix}.csv"
    workbook = output_path / workbook_name

    sfc_cashflows[RAW_CASHFLOW_COLS].to_csv(sfc_csv, index=False)
    our_cashflows[RAW_CASHFLOW_COLS].to_csv(our_csv, index=False)
    loans_df.to_csv(loans_csv, index=False)
    if progress_callback:
        progress_callback(94, f"Writing {workbook_name}")
    _write_cibc_workbook(workbook, loans_df, sfc_cashflows, our_cashflows, irr_target)
    if progress_callback:
        progress_callback(100, f"Finished {workbook_name}")

    return {
        "sfc_csv": str(sfc_csv),
        "our_csv": str(our_csv),
        "loans_csv": str(loans_csv),
        "workbook": str(workbook),
    }


def run_cibc_package(**kwargs) -> dict[str, str]:
    """Compatibility wrapper for the CIBC purchase-package flow."""
    kwargs.setdefault("buyer", "cibc")
    return run_purchase_package(**kwargs)


def run_sg_package(**kwargs) -> dict[str, str]:
    """Compatibility wrapper for the SG purchase-package flow."""
    kwargs.setdefault("buyer", "sg")
    return run_purchase_package(**kwargs)


def _parse_args(argv=None):
    parser = argparse.ArgumentParser(description="Generate lender-specific purchase cashflow package.")
    parser.add_argument("--prime-file", required=True, help="Path to PRIME Exhibit A workbook")
    parser.add_argument("--sfy-file", required=True, help="Path to SFY Exhibit A workbook")
    parser.add_argument("--master-sheet", required=True, help="Path to MASTER_SHEET.xlsx")
    parser.add_argument("--notes-sheet", required=True, help="Path to MASTER_SHEET - Notes.xlsx")
    parser.add_argument("--purchase-date", required=True, help="Purchase date in YYYY-MM-DD format")
    parser.add_argument("--output-dir", required=True, help="Output directory for generated files")
    parser.add_argument("--buy-num", required=True, help="Buy identifier used in output file names")
    parser.add_argument("--buyer", default="cibc", help="Buyer/lender suffix for output file names")
    parser.add_argument("--target", type=float, default=7.9, help="IRR target in percent")
    parser.add_argument("--cprshock", type=float, default=1.0, help="CPR shock multiplier")
    parser.add_argument("--cdrshock", type=float, default=1.0, help="CDR shock multiplier")
    return parser.parse_args(argv)


if __name__ == "__main__":
    args = _parse_args()
    outputs = run_purchase_package(
        prime_file=args.prime_file,
        sfy_file=args.sfy_file,
        master_sheet=args.master_sheet,
        notes_sheet=args.notes_sheet,
        purchase_date=args.purchase_date,
        output_dir=args.output_dir,
        buy_num=args.buy_num,
        buyer=args.buyer,
        irr_target=args.target,
        cprshock=args.cprshock,
        cdrshock=args.cdrshock,
    )
    for name, path in outputs.items():
        print(f"{name}: {path}")
