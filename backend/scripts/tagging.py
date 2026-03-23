"""Tagging script: splits loans between SG and CIBC lenders.

Logic mirrors: loan_engine/inputs/93rd_buy/bin/tagging.py

Reads raw exhibit files from FOLDER/files_required/, writes four split output files
(_sg.xlsx and _cibc.xlsx variants) back to FOLDER/files_required/ and also to
FOLDER/output/ for the file manager.

Environment variables:
    FOLDER      - working directory (required); must contain files_required/
    PDATE       - purchase date YYYY-MM-DD (optional; defaults to next Tuesday)
    IRR_TARGET  - IRR target float (optional; default 7.9)
"""

import os
import re
import warnings
from pathlib import Path

import pandas as pd

warnings.filterwarnings("ignore")
pd.options.display.max_columns = 200
pd.options.display.max_rows = 500


# ---------------------------------------------------------------------------
# Allocation function (importable for unit tests)
# ---------------------------------------------------------------------------

def allocate_sg(buy_df, grouped_sum, p=0.325, s=0.5):
    """Allocate loans between SG and CIBC lenders.

    Builds an SG budget dict dynamically from grouped_sum keys using prefix-based
    classification: SFY* -> s ratio, PRIME* -> p ratio, _bd suffix -> 0 (always CIBC).
    Iterates over buy_df in order, assigning each loan to "sg" until budget exhausted
    then "cibc".

    Args:
        buy_df: DataFrame with "tags" and "Orig. Balance" columns.
        grouped_sum: Series from buy_df.groupby("tags")["Orig. Balance"].sum().
        p: PRIME SG allocation ratio (default 0.325 — 32.5%).
        s: SFY SG allocation ratio (default 0.5 — 50%).

    Returns:
        buy_df with "final" column populated ("sg" or "cibc").
    """
    sg = {}
    for tag in grouped_sum.index:
        if tag.endswith("_bd"):
            sg[tag] = 0
        elif tag.startswith("SFY"):
            sg[tag] = grouped_sum[tag] * s
        elif tag.startswith("PRIME"):
            sg[tag] = grouped_sum[tag] * p
        else:
            sg[tag] = 0  # unknown prefix, default to CIBC

    buy_df["final"] = "cibc"
    for i in buy_df.iterrows():
        tag = i[1]["tags"]
        if sg.get(tag, 0) > 0:
            buy_df.loc[i[0], "final"] = "sg"
            sg[tag] = sg[tag] - i[1]["Orig. Balance"]
    return buy_df


# ---------------------------------------------------------------------------
# Main script execution (runs when called directly or via subprocess)
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    # ---------------------------------------------------------------------------
    # Configuration from environment
    # ---------------------------------------------------------------------------
    folder = Path(os.environ.get("FOLDER", ".")).resolve()
    irr_target = float(os.environ.get("IRR_TARGET", "7.9"))
    pdate = os.environ.get("PDATE", "")

    files_required = folder / "files_required"
    output_dir = folder / "output"
    output_dir.mkdir(exist_ok=True)

    # ---------------------------------------------------------------------------
    # Auto-detect curr_date from available raw exhibit file
    # Pattern: FX3_{curr_date}_ExhibitAtoFormofSaleNotice.xlsx (no _sg/_cibc suffix)
    # ---------------------------------------------------------------------------
    sfy_candidates = [
        p
        for p in files_required.glob("FX3_*_ExhibitAtoFormofSaleNotice.xlsx")
        if "_sg" not in p.name and "_cibc" not in p.name
    ]
    if not sfy_candidates:
        raise FileNotFoundError(
            f"No raw SFY exhibit file (FX3_*_ExhibitAtoFormofSaleNotice.xlsx) found in {files_required}. "
            "Run pre-funding first to generate exhibit files."
        )
    sfy_raw = sfy_candidates[0]
    m = re.search(r"FX3_(.+?)_ExhibitAtoFormofSaleNotice\.xlsx", sfy_raw.name)
    curr_date = m.group(1) if m else None
    if not curr_date:
        raise ValueError(f"Could not parse curr_date from filename: {sfy_raw.name}")

    prime_raw = files_required / f"{curr_date} Exhibit A To Form Of Sale Notice.xlsx"
    if not prime_raw.exists():
        raise FileNotFoundError(f"Expected PRIME exhibit file not found: {prime_raw}")

    # ---------------------------------------------------------------------------
    # Load MASTER_SHEET and Notes
    # ---------------------------------------------------------------------------
    df_loans_types = pd.read_excel(files_required / "MASTER_SHEET.xlsx")
    notes = pd.read_excel(files_required / "MASTER_SHEET - Notes.xlsx")

    df_loans_types["Platform"] = df_loans_types.platform.str.upper()
    notes["loan program"] = notes["loan program"].apply(lambda x: x + "notes")
    notes["Platform"] = notes.platform.str.upper()
    df_loans_types = pd.concat([df_loans_types, notes])

    # ---------------------------------------------------------------------------
    # Read raw exhibit files (4 header rows + 1 footer row to strip)
    # ---------------------------------------------------------------------------
    sfy_df = pd.read_excel(sfy_raw)
    sfy_df = sfy_df.iloc[4:].reset_index(drop=True)
    sfy_df.columns = sfy_df.iloc[0]
    sfy_df = sfy_df[1:].reset_index(drop=True)
    sfy_df = sfy_df.iloc[:-1].reset_index(drop=True)

    prime_df = pd.read_excel(prime_raw)
    prime_df = prime_df.iloc[4:].reset_index(drop=True)
    prime_df.columns = prime_df.iloc[0]
    prime_df = prime_df[1:].reset_index(drop=True)
    prime_df = prime_df.iloc[:-1].reset_index(drop=True)

    # ---------------------------------------------------------------------------
    # Build combined buy_df
    # ---------------------------------------------------------------------------
    sfy_df["Platform"] = "SFY"
    prime_df["Platform"] = "PRIME"
    buy_df = pd.concat([prime_df, sfy_df])
    buy_df.rename(columns={"Loan Program": "loan program"}, inplace=True)
    buy_df["loan program"] = buy_df.apply(
        lambda x: x["loan program"] + "notes" if x["Application Type"] == "HD NOTE" else x["loan program"], axis=1
    )
    buy_df["Repurchase"] = False
    buy_df["Repurchase_Date"] = None
    if pdate:
        buy_df["Purchase_Date"] = pd.to_datetime(pdate)
    buy_df["Excess_Asset"] = False
    buy_df["Borrowing_Base_eligible"] = True
    buy_df["IRR Support Target"] = irr_target
    buy_df["Submit Date"] = pd.to_datetime(buy_df["Submit Date"])
    buy_df["Monthly Payment Date"] = pd.to_datetime(buy_df["Monthly Payment Date"])
    buy_df = buy_df.merge(df_loans_types, on=["loan program", "Platform"], how="left")

    # ---------------------------------------------------------------------------
    # Tagging: create tags column and allocate loans to SG / CIBC
    # ---------------------------------------------------------------------------
    buy_df["tags"] = buy_df["Platform"] + buy_df["type"]

    grouped_sum = buy_df.groupby("tags")["Orig. Balance"].sum()
    print("Balance by tag group:")
    print(grouped_sum)

    # Random shuffle (same as reference)
    buy_df = buy_df.sample(frac=1, random_state=42)

    # SG allocation targets: 50% of SFY, 32.5% of PRIME (per D-11)
    p = 0.325
    s = 0.5
    buy_df = allocate_sg(buy_df, grouped_sum, p=p, s=s)

    print("SG count:", (buy_df["final"] == "sg").sum(), "  CIBC count:", (buy_df["final"] == "cibc").sum())

    # ---------------------------------------------------------------------------
    # Write split output files to files_required/ (for downstream pipeline steps)
    # ---------------------------------------------------------------------------
    cibc_sfy_path = files_required / f"FX3_{curr_date}_ExhibitAtoFormofSaleNotice_cibc.xlsx"
    cibc_prime_path = files_required / f"{curr_date} Exhibit A To Form Of Sale Notice_cibc.xlsx"
    sg_sfy_path = files_required / f"FX3_{curr_date}_ExhibitAtoFormofSaleNotice_sg.xlsx"
    sg_prime_path = files_required / f"{curr_date} Exhibit A To Form Of Sale Notice_sg.xlsx"

    buy_df[(buy_df["final"] == "cibc") & (buy_df["Platform"] == "SFY")].to_excel(cibc_sfy_path)
    buy_df[(buy_df["final"] == "cibc") & (buy_df["Platform"] == "PRIME")].to_excel(cibc_prime_path)
    buy_df[(buy_df["final"] == "sg") & (buy_df["Platform"] == "SFY")].to_excel(sg_sfy_path)
    buy_df[(buy_df["final"] == "sg") & (buy_df["Platform"] == "PRIME")].to_excel(sg_prime_path)

    print(f"Wrote: {sg_sfy_path.name}")
    print(f"Wrote: {sg_prime_path.name}")
    print(f"Wrote: {cibc_sfy_path.name}")
    print(f"Wrote: {cibc_prime_path.name}")

    # Also write summary to output/ for the file manager
    # Recompute sg_target per tag from grouped_sum using the same prefix logic as allocate_sg
    summary_rows = []
    for tag in grouped_sum.index:
        if tag.endswith("_bd"):
            target = 0.0
        elif tag.startswith("SFY"):
            target = grouped_sum.get(tag, 0) * s
        elif tag.startswith("PRIME"):
            target = grouped_sum.get(tag, 0) * p
        else:
            target = 0.0
        allocated = buy_df[(buy_df["tags"] == tag) & (buy_df["final"] == "sg")]["Orig. Balance"].sum()
        summary_rows.append({"tag": tag, "sg_target": round(target, 2), "sg_allocated": round(float(allocated), 2)})
    pd.DataFrame(summary_rows).to_excel(output_dir / "tagging_summary.xlsx", index=False)
    buy_df[["SELLER Loan #", "Platform", "tags", "final", "Orig. Balance"]].to_excel(
        output_dir / "tagging_allocation.xlsx", index=False
    )
    print("Done.")
