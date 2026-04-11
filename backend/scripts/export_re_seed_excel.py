"""
Export RE seed data to Excel.

Regenerates the same 500 T0 + 500 T1 loans and 6,000 cashflow records
that were seeded into the database (deterministic — Faker.seed(42),
rng seed=42) and writes them to an Excel workbook with four sheets:

  Sheet 1 — Summary          portfolio statistics and data dictionary
  Sheet 2 — RE Loans (T0)    500 loans as of 2025-09-30
  Sheet 3 — RE Loans (T1)    500 loans as of 2025-12-31
  Sheet 4 — Cashflows        6,000 monthly cashflow records

Run from backend/ directory:
    python scripts/export_re_seed_excel.py
    python scripts/export_re_seed_excel.py --out /path/to/output.xlsx
"""

import argparse
from pathlib import Path
from datetime import date, timedelta

import numpy as np
import pandas as pd
from faker import Faker

# ---------------------------------------------------------------------------
# Same constants as seed_re_loans.py (must stay in sync)
# ---------------------------------------------------------------------------

fake = Faker()
Faker.seed(42)
rng = np.random.default_rng(seed=42)

N_LOANS = 500
T0_DATE = date(2025, 9, 30)
T1_DATE = date(2025, 12, 31)

PROPERTY_TYPES = ["multifamily", "office", "retail", "industrial", "hospitality", "mixed-use"]
PROPERTY_WEIGHTS = [0.35, 0.20, 0.15, 0.15, 0.10, 0.05]

RISK_RATINGS = ["AAA", "AA", "A", "BBB", "BB", "B", "CCC"]
RISK_WEIGHTS = [0.03, 0.07, 0.15, 0.35, 0.22, 0.13, 0.05]

RATE_TYPES = ["fixed", "floating", "hybrid"]
RATE_WEIGHTS = [0.60, 0.30, 0.10]

DELINQ_STATUSES = ["current", "30", "60", "90+"]
DELINQ_WEIGHTS = [0.85, 0.08, 0.05, 0.02]
DELINQ_DPD_MAP = {"current": 0, "30": 30, "60": 60, "90+": 90}

PIPELINE_STAGES = ["funded", "closing", "approved", "underwriting"]
PIPELINE_WEIGHTS = [0.75, 0.10, 0.10, 0.05]

STATE_MSA_MAP = {
    "NY": ["New York-Newark-Jersey City", "Buffalo-Cheektowaga"],
    "CA": ["Los Angeles-Long Beach", "San Francisco-Oakland"],
    "TX": ["Dallas-Fort Worth", "Houston-Woodlands"],
    "FL": ["Miami-Fort Lauderdale", "Tampa-St. Petersburg"],
    "IL": ["Chicago-Naperville"],
    "PA": ["Philadelphia-Camden"],
    "OH": ["Columbus"],
    "GA": ["Atlanta-Sandy Springs"],
    "NC": ["Charlotte-Concord"],
    "NJ": ["New York-Newark-Jersey City"],
    "VA": ["Washington-Arlington"],
    "MA": ["Boston-Cambridge"],
    "WA": ["Seattle-Tacoma"],
    "AZ": ["Phoenix-Mesa"],
    "CO": ["Denver-Aurora"],
    "TN": ["Nashville-Davidson"],
    "MD": ["Baltimore-Columbia"],
    "MN": ["Minneapolis-St. Paul"],
    "MO": ["St. Louis"],
    "IN": ["Indianapolis-Carmel"],
    "WI": ["Milwaukee-Waukesha"],
}

STATES = list(STATE_MSA_MAP.keys())
STATE_WEIGHTS_RAW = [0.15, 0.14, 0.12, 0.10, 0.08] + [0.025] * 16
_total_sw = sum(STATE_WEIGHTS_RAW)
STATE_WEIGHTS = [w / _total_sw for w in STATE_WEIGHTS_RAW]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def to_f(val, places: int = 6) -> float:
    return round(float(val), places)


def weighted_choice(options, weights):
    return options[int(rng.choice(len(options), p=weights))]


def generate_delinquency():
    status = weighted_choice(DELINQ_STATUSES, DELINQ_WEIGHTS)
    return status, DELINQ_DPD_MAP[status]


# ---------------------------------------------------------------------------
# Data generation → dicts (no SQLAlchemy models needed)
# ---------------------------------------------------------------------------


def generate_t0_rows():
    rows = []
    for i in range(N_LOANS):
        upb = rng.uniform(500_000, 50_000_000)
        orig_bal = upb * rng.uniform(1.0, 1.15)
        rate = float(np.clip(rng.normal(5.5, 1.2), 2.5, 9.0))
        ltv = float(np.clip(rng.normal(0.67, 0.08), 0.40, 0.95))
        dscr = float(np.clip(1.35 - 0.8 * (ltv - 0.67) + rng.normal(0, 0.20), 0.70, 2.80))

        state = weighted_choice(STATES, STATE_WEIGHTS)
        msa = STATE_MSA_MAP[state][int(rng.integers(0, len(STATE_MSA_MAP[state])))]
        risk_rating = weighted_choice(RISK_RATINGS, RISK_WEIGHTS)
        orig_date = fake.date_between(start_date=date(2018, 1, 1), end_date=date(2025, 6, 30))
        mat_date = orig_date + timedelta(days=int(rng.integers(365 * 3, 365 * 10)))
        delinq_status, dpd = generate_delinquency()

        rows.append(
            {
                "loan_number": f"RE-{i + 1:05d}",
                "borrower_name": fake.company(),
                "as_of_date": T0_DATE,
                "upb": to_f(upb, 2),
                "original_balance": to_f(orig_bal, 2),
                "interest_rate_pct": to_f(rate, 4),
                "wam_months": int(rng.integers(12, 360)),
                "ltv": to_f(ltv, 4),
                "dscr": to_f(dscr, 4),
                "property_type": weighted_choice(PROPERTY_TYPES, PROPERTY_WEIGHTS),
                "state": state,
                "msa": msa,
                "risk_rating": risk_rating,
                "prior_risk_rating": risk_rating,
                "rate_type": weighted_choice(RATE_TYPES, RATE_WEIGHTS),
                "origination_date": orig_date,
                "maturity_date": mat_date,
                "days_past_due": dpd,
                "delinquency_status": delinq_status,
                "pipeline_stage": weighted_choice(PIPELINE_STAGES, PIPELINE_WEIGHTS),
                "vintage_year": orig_date.year,
            }
        )
    return rows


def generate_t1_rows(t0_rows):
    t1 = []
    for t0 in t0_rows:
        roll = float(rng.random())
        idx = RISK_RATINGS.index(t0["risk_rating"])
        if roll < 0.08:
            idx = min(idx + 1, len(RISK_RATINGS) - 1)
        elif roll < 0.13:
            idx = max(idx - 1, 0)
        new_rating = RISK_RATINGS[idx]
        new_upb = t0["upb"] * float(rng.uniform(0.95, 1.02))
        delinq_status, dpd = generate_delinquency()

        t1.append(
            {
                **t0,
                "as_of_date": T1_DATE,
                "upb": to_f(new_upb, 2),
                "risk_rating": new_rating,
                "prior_risk_rating": t0["risk_rating"],
                "days_past_due": dpd,
                "delinquency_status": delinq_status,
            }
        )
    return t1


def generate_cashflow_rows(t0_rows):
    period_dates = [
        date(2024, 10, 1), date(2024, 11, 1), date(2024, 12, 1),
        date(2025, 1, 1),  date(2025, 2, 1),  date(2025, 3, 1),
        date(2025, 4, 1),  date(2025, 5, 1),  date(2025, 6, 1),
        date(2025, 7, 1),  date(2025, 8, 1),  date(2025, 9, 1),
    ]
    rows = []
    for t0 in t0_rows:
        upb = t0["upb"]
        rate = t0["interest_rate_pct"]
        for pd_date in period_dates:
            sched_p = upb / 360.0
            actual_p = sched_p * float(rng.uniform(0.90, 1.05))
            sched_i = upb * (rate / 100.0 / 12.0)
            actual_i = sched_i * float(rng.uniform(0.95, 1.02))
            noi = upb * float(rng.uniform(0.04, 0.08)) / 12.0
            rows.append(
                {
                    "loan_number": t0["loan_number"],
                    "borrower_name": t0["borrower_name"],
                    "period_date": pd_date,
                    "scheduled_principal": to_f(sched_p, 2),
                    "actual_principal": to_f(actual_p, 2),
                    "scheduled_interest": to_f(sched_i, 2),
                    "actual_interest": to_f(actual_i, 2),
                    "noi": to_f(noi, 2),
                }
            )
    return rows


# ---------------------------------------------------------------------------
# Excel formatting helpers
# ---------------------------------------------------------------------------

NAVY = "1A3868"
LIGHT_BLUE = "D6E4F7"
WHITE = "FFFFFF"
YELLOW = "FFF2CC"


def style_header_row(ws, row_idx, col_count, bg=NAVY, fg=WHITE, bold=True):
    from openpyxl.styles import PatternFill, Font, Alignment

    fill = PatternFill(fill_type="solid", fgColor=bg)
    font = Font(bold=bold, color=fg)
    for col in range(1, col_count + 1):
        cell = ws.cell(row=row_idx, column=col)
        cell.fill = fill
        cell.font = font
        cell.alignment = Alignment(horizontal="center", vertical="center")


def auto_width(ws, min_w=10, max_w=40):
    for col in ws.columns:
        length = max(
            (len(str(cell.value)) if cell.value is not None else 0) for cell in col
        )
        ws.column_dimensions[col[0].column_letter].width = min(max(length + 2, min_w), max_w)


def write_df_to_sheet(ws, df, header_bg=NAVY):

    # Write header
    for col_idx, col_name in enumerate(df.columns, 1):
        ws.cell(row=1, column=col_idx, value=col_name)
    style_header_row(ws, 1, len(df.columns), bg=header_bg)

    # Write data rows
    for row_idx, row in enumerate(df.itertuples(index=False), 2):
        for col_idx, val in enumerate(row, 1):
            ws.cell(row=row_idx, column=col_idx, value=val)

    auto_width(ws)

    # Freeze header
    ws.freeze_panes = "A2"


# ---------------------------------------------------------------------------
# Summary sheet
# ---------------------------------------------------------------------------


def build_summary_sheet(ws, t0_df, t1_df, cf_df):
    from openpyxl.styles import PatternFill, Font, Alignment

    navy_fill = PatternFill(fill_type="solid", fgColor=NAVY)
    light_fill = PatternFill(fill_type="solid", fgColor=LIGHT_BLUE)
    navy_font = Font(bold=True, color=WHITE, size=12)
    bold = Font(bold=True)
    center = Alignment(horizontal="center")

    def write_header(row, text):
        c = ws.cell(row=row, column=1, value=text)
        c.fill = navy_fill
        c.font = navy_font
        c.alignment = center
        ws.merge_cells(start_row=row, start_column=1, end_row=row, end_column=4)

    def write_kv(row, label, value):
        lc = ws.cell(row=row, column=1, value=label)
        lc.font = bold
        lc.fill = light_fill
        vc = ws.cell(row=row, column=2, value=value)
        vc.alignment = center

    row = 1
    write_header(row, "RE Portfolio Seed Data — Summary")
    row += 2

    write_header(row, "Dataset Overview")
    row += 1
    write_kv(row, "T0 Snapshot Date", str(T0_DATE))
    row += 1
    write_kv(row, "T1 Snapshot Date", str(T1_DATE))
    row += 1
    write_kv(row, "T0 Loan Count", len(t0_df))
    row += 1
    write_kv(row, "T1 Loan Count", len(t1_df))
    row += 1
    write_kv(row, "Cashflow Records", len(cf_df))
    row += 1
    write_kv(row, "Cashflow Months", "Oct 2024 – Sep 2025 (12 months)")
    row += 2

    write_header(row, "T0 Portfolio Statistics")
    row += 1
    write_kv(row, "Total UPB ($)", f"${t0_df['upb'].sum():,.0f}")
    row += 1
    write_kv(row, "Average UPB ($)", f"${t0_df['upb'].mean():,.0f}")
    row += 1
    write_kv(row, "Weighted Avg Interest Rate", f"{t0_df['interest_rate_pct'].mean():.2f}%")
    row += 1
    write_kv(row, "Weighted Avg LTV", f"{t0_df['ltv'].mean():.1%}")
    row += 1
    write_kv(row, "Weighted Avg DSCR", f"{t0_df['dscr'].mean():.2f}x")
    row += 1
    write_kv(row, "Avg WAM (months)", f"{t0_df['wam_months'].mean():.0f}")
    row += 1
    delinq = t0_df[t0_df["delinquency_status"] != "current"]
    write_kv(row, "Delinquent Loans (30+)", f"{len(delinq)} ({len(delinq)/len(t0_df):.1%})")
    row += 2

    write_header(row, "T0 Property Type Distribution")
    row += 1
    for pt, cnt in t0_df["property_type"].value_counts().items():
        write_kv(row, pt.title(), f"{cnt} loans ({cnt/len(t0_df):.1%})")
        row += 1
    row += 1

    write_header(row, "T0 Risk Rating Distribution")
    row += 1
    for rr in RISK_RATINGS:
        cnt = (t0_df["risk_rating"] == rr).sum()
        write_kv(row, rr, f"{cnt} loans ({cnt/len(t0_df):.1%})")
        row += 1
    row += 1

    write_header(row, "Sheets Guide")
    row += 1
    guide = [
        ("RE Loans (T0)", "500 loans at 2025-09-30. Base snapshot. prior_risk_rating = risk_rating."),
        ("RE Loans (T1)", "500 loans at 2025-12-31. Same population — ~8% downgrade, ~5% upgrade."),
        ("Cashflows", "6,000 rows. 12 monthly records per T0 loan (Oct 2024–Sep 2025)."),
    ]
    for sheet, desc in guide:
        lc = ws.cell(row=row, column=1, value=sheet)
        lc.font = bold
        lc.fill = light_fill
        ws.cell(row=row, column=2, value=desc)
        row += 1

    ws.column_dimensions["A"].width = 32
    ws.column_dimensions["B"].width = 55


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main():
    parser = argparse.ArgumentParser(description="Export RE seed data to Excel")
    parser.add_argument(
        "--out",
        default=str(Path(__file__).parent.parent.parent / "RE_Seed_Data.xlsx"),
        help="Output file path (default: repo root RE_Seed_Data.xlsx)",
    )
    args = parser.parse_args()
    out_path = Path(args.out)

    print("Generating T0 loans...")
    t0_rows = generate_t0_rows()
    print("Generating T1 loans...")
    t1_rows = generate_t1_rows(t0_rows)
    print("Generating cashflows...")
    cf_rows = generate_cashflow_rows(t0_rows)

    t0_df = pd.DataFrame(t0_rows)
    t1_df = pd.DataFrame(t1_rows)
    cf_df = pd.DataFrame(cf_rows)

    print(f"Writing Excel workbook to {out_path} ...")

    from openpyxl import Workbook

    wb = Workbook()

    # Sheet 1: Summary
    ws_summary = wb.active
    ws_summary.title = "Summary"
    build_summary_sheet(ws_summary, t0_df, t1_df, cf_df)

    # Sheet 2: T0 Loans
    ws_t0 = wb.create_sheet("RE Loans (T0)")
    write_df_to_sheet(ws_t0, t0_df)

    # Sheet 3: T1 Loans
    ws_t1 = wb.create_sheet("RE Loans (T1)")
    write_df_to_sheet(ws_t1, t1_df)

    # Sheet 4: Cashflows
    ws_cf = wb.create_sheet("Cashflows")
    write_df_to_sheet(ws_cf, cf_df, header_bg=NAVY)

    wb.save(out_path)
    print("\nDone.")
    print(f"  T0 loans:   {len(t0_df):,}")
    print(f"  T1 loans:   {len(t1_df):,}")
    print(f"  Cashflows:  {len(cf_df):,}")
    print(f"  Output:     {out_path.resolve()}")


if __name__ == "__main__":
    main()
