"""
Seed re_loans and re_loan_cashflows with realistic CRE portfolio data.

Generates:
  - 500 T0 loans (as_of_date=2025-09-30)
  - 500 T1 loans (as_of_date=2025-12-31) with ~8% downgrades and ~5% upgrades
  - 12 monthly cashflow records per T0 loan (Oct 2024 - Sep 2025)

Idempotent: truncates re_loan_cashflows then re_loans before seeding.

Run from backend/ directory:
    python scripts/seed_re_loans.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import numpy as np
from decimal import Decimal
from datetime import date, timedelta
from faker import Faker
from sqlalchemy.orm import Session
from db.connection import SessionLocal
from db.models import RELoan, RELoanCashflow

fake = Faker()
Faker.seed(42)
rng = np.random.default_rng(seed=42)  # reproducible

# ---------------------------------------------------------------------------
# Constants (per 17-CONTEXT.md locked decisions)
# ---------------------------------------------------------------------------

N_LOANS = 500
T0_DATE = date(2025, 9, 30)
T1_DATE = date(2025, 12, 31)

PROPERTY_TYPES = ["multifamily", "office", "retail", "industrial", "hospitality", "mixed-use"]
PROPERTY_WEIGHTS = [0.35, 0.20, 0.15, 0.15, 0.10, 0.05]

RISK_RATINGS = ["AAA", "AA", "A", "BBB", "BB", "B", "CCC"]
RISK_WEIGHTS = [0.03, 0.07, 0.15, 0.35, 0.22, 0.13, 0.05]  # bell-curved around BBB

RATE_TYPES = ["fixed", "floating", "hybrid"]
RATE_WEIGHTS = [0.60, 0.30, 0.10]

DELINQ_STATUSES = ["current", "30", "60", "90+"]
DELINQ_WEIGHTS = [0.85, 0.08, 0.05, 0.02]
DELINQ_DPD_MAP = {"current": 0, "30": 30, "60": 60, "90+": 90}

PIPELINE_STAGES = ["funded", "closing", "approved", "underwriting"]
PIPELINE_WEIGHTS = [0.75, 0.10, 0.10, 0.05]

# Top states with MSA mapping (>=20 states, >=8 MSAs)
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
# Concentrate in NY, CA, TX, FL, IL — remaining 16 states share equal weight
STATE_WEIGHTS_RAW = [0.15, 0.14, 0.12, 0.10, 0.08] + [0.025] * 16
# Normalize to sum to 1.0
_total_sw = sum(STATE_WEIGHTS_RAW)
STATE_WEIGHTS = [w / _total_sw for w in STATE_WEIGHTS_RAW]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def to_dec(val, places: int = 6) -> Decimal:
    """Convert numpy float to Decimal with specified decimal places."""
    return Decimal(str(round(float(val), places)))


def weighted_choice(options: list, weights: list) -> str:
    """Pick one item from options using the given probability weights."""
    return options[int(rng.choice(len(options), p=weights))]


def generate_delinquency():
    """Return (delinquency_status, days_past_due) pair."""
    status = weighted_choice(DELINQ_STATUSES, DELINQ_WEIGHTS)
    dpd = DELINQ_DPD_MAP[status]
    return status, dpd


# ---------------------------------------------------------------------------
# T0 loan generation
# ---------------------------------------------------------------------------


def generate_t0_loans() -> list[RELoan]:
    """Generate N_LOANS T0 snapshot loans."""
    loans = []
    for i in range(N_LOANS):
        # Core financials
        upb_val = rng.uniform(500_000, 50_000_000)
        original_balance_val = upb_val * rng.uniform(1.0, 1.15)
        interest_rate_val = float(np.clip(rng.normal(5.5, 1.2), 2.5, 9.0))
        ltv_val = float(np.clip(rng.normal(0.67, 0.08), 0.40, 0.95))
        # DSCR inversely correlated with LTV
        dscr_val = float(np.clip(1.35 - 0.8 * (ltv_val - 0.67) + rng.normal(0, 0.20), 0.70, 2.80))

        # Geography
        state = weighted_choice(STATES, STATE_WEIGHTS)
        msa_options = STATE_MSA_MAP[state]
        msa = msa_options[int(rng.integers(0, len(msa_options)))]

        # Risk rating
        risk_rating = weighted_choice(RISK_RATINGS, RISK_WEIGHTS)

        # Dates
        origination_ts = fake.date_between(start_date=date(2018, 1, 1), end_date=date(2025, 6, 30))
        maturity_ts = origination_ts + timedelta(days=int(rng.integers(365 * 3, 365 * 10)))

        # Delinquency
        delinq_status, dpd = generate_delinquency()

        loan = RELoan(
            loan_number=f"RE-{i + 1:05d}",
            borrower_name=fake.company(),
            sales_team_id=None,
            as_of_date=T0_DATE,
            upb=to_dec(upb_val),
            original_balance=to_dec(original_balance_val),
            interest_rate=to_dec(interest_rate_val),
            wam_months=int(rng.integers(12, 360)),
            ltv=to_dec(ltv_val),
            dscr=to_dec(dscr_val),
            property_type=weighted_choice(PROPERTY_TYPES, PROPERTY_WEIGHTS),
            state=state,
            msa=msa,
            risk_rating=risk_rating,
            prior_risk_rating=risk_rating,  # T0: prior == current (base snapshot)
            rate_type=weighted_choice(RATE_TYPES, RATE_WEIGHTS),
            origination_date=origination_ts,
            maturity_date=maturity_ts,
            days_past_due=dpd,
            delinquency_status=delinq_status,
            pipeline_stage=weighted_choice(PIPELINE_STAGES, PIPELINE_WEIGHTS),
            vintage_year=origination_ts.year,
        )
        loans.append(loan)
    return loans


# ---------------------------------------------------------------------------
# T1 loan generation
# ---------------------------------------------------------------------------


def generate_t1_loans(t0_loans: list[RELoan]) -> list[RELoan]:
    """Generate T1 snapshot — same loan population, slight adjustments."""
    t1_loans = []
    for t0 in t0_loans:
        # Risk rating migration: ~8% downgrade, ~5% upgrade, ~87% unchanged
        roll = float(rng.random())
        current_idx = RISK_RATINGS.index(t0.risk_rating)
        if roll < 0.08:
            # Downgrade one notch
            new_idx = min(current_idx + 1, len(RISK_RATINGS) - 1)
        elif roll < 0.13:
            # Upgrade one notch
            new_idx = max(current_idx - 1, 0)
        else:
            new_idx = current_idx
        new_risk_rating = RISK_RATINGS[new_idx]

        # Slight UPB change (amortization or draw)
        new_upb = float(t0.upb) * float(rng.uniform(0.95, 1.02))

        # Slight delinquency change
        delinq_status, dpd = generate_delinquency()

        loan = RELoan(
            loan_number=t0.loan_number,
            borrower_name=t0.borrower_name,
            sales_team_id=None,
            as_of_date=T1_DATE,
            upb=to_dec(new_upb),
            original_balance=t0.original_balance,
            interest_rate=t0.interest_rate,
            wam_months=t0.wam_months,
            ltv=t0.ltv,
            dscr=t0.dscr,
            property_type=t0.property_type,
            state=t0.state,
            msa=t0.msa,
            risk_rating=new_risk_rating,
            prior_risk_rating=t0.risk_rating,  # T1: prior = T0 rating
            rate_type=t0.rate_type,
            origination_date=t0.origination_date,
            maturity_date=t0.maturity_date,
            days_past_due=dpd,
            delinquency_status=delinq_status,
            pipeline_stage=t0.pipeline_stage,
            vintage_year=t0.vintage_year,
        )
        t1_loans.append(loan)
    return t1_loans


# ---------------------------------------------------------------------------
# Cashflow generation (T0 loans only)
# ---------------------------------------------------------------------------


def generate_cashflows(t0_loans: list[RELoan]) -> list[RELoanCashflow]:
    """Generate 12 monthly cashflow records (Oct 2024 - Sep 2025) per T0 loan."""
    cashflows = []
    # Monthly period dates: first of each month from Oct 2024 to Sep 2025
    period_dates = [
        date(2024, 10, 1),
        date(2024, 11, 1),
        date(2024, 12, 1),
        date(2025, 1, 1),
        date(2025, 2, 1),
        date(2025, 3, 1),
        date(2025, 4, 1),
        date(2025, 5, 1),
        date(2025, 6, 1),
        date(2025, 7, 1),
        date(2025, 8, 1),
        date(2025, 9, 1),
    ]

    for loan in t0_loans:
        upb_float = float(loan.upb)
        rate_float = float(loan.interest_rate)

        for period_date in period_dates:
            # Simplified monthly amortization
            sched_principal = upb_float / 360.0
            actual_principal = sched_principal * float(rng.uniform(0.90, 1.05))

            # Monthly interest
            sched_interest = upb_float * (rate_float / 100.0 / 12.0)
            actual_interest = sched_interest * float(rng.uniform(0.95, 1.02))

            # NOI: proportional to UPB (~4-8% annual yield / 12 months)
            noi = upb_float * float(rng.uniform(0.04, 0.08)) / 12.0

            cashflows.append(
                RELoanCashflow(
                    loan_id=loan.id,
                    period_date=period_date,
                    scheduled_principal=to_dec(sched_principal),
                    actual_principal=to_dec(actual_principal),
                    scheduled_interest=to_dec(sched_interest),
                    actual_interest=to_dec(actual_interest),
                    noi=to_dec(noi),
                )
            )
    return cashflows


# ---------------------------------------------------------------------------
# Main seed function
# ---------------------------------------------------------------------------


def seed_re_loans() -> None:
    """Seed re_loans and re_loan_cashflows. Idempotent — safe to re-run."""
    db: Session = SessionLocal()
    try:
        # Idempotent: truncate child before parent (FK constraint order)
        db.query(RELoanCashflow).delete()
        db.query(RELoan).delete()
        db.commit()

        # Generate and insert T0 loans
        t0_loans = generate_t0_loans()
        db.add_all(t0_loans)
        db.flush()  # get auto-generated IDs before generating cashflows

        # Generate and insert T1 loans
        t1_loans = generate_t1_loans(t0_loans)
        db.add_all(t1_loans)

        # Generate and insert cashflows (T0 only — T1 does not duplicate cashflows)
        cashflows = generate_cashflows(t0_loans)
        db.add_all(cashflows)

        db.commit()
        print(f"Seeded {len(t0_loans)} T0 loans, {len(t1_loans)} T1 loans, {len(cashflows)} cashflow records")
    finally:
        db.close()


if __name__ == "__main__":
    seed_re_loans()
