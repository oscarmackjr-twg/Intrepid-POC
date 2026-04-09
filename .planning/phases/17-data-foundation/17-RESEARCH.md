# Phase 17: Data Foundation - Research

**Researched:** 2026-04-08
**Domain:** SQLAlchemy 2 / Alembic migrations, PostgreSQL NUMERIC types, Python seed data generation
**Confidence:** HIGH

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**Schema: API-Driven Minimum (~25–30 columns)**

`re_loans` columns:
- Identity/admin: `id`, `loan_number`, `borrower_name`, `sales_team_id` (FK → sales_teams), `as_of_date`
- Financials: `upb` NUMERIC(18,6), `original_balance` NUMERIC(18,6), `interest_rate` NUMERIC(10,6), `wam_months` Integer, `ltv` NUMERIC(10,6), `dscr` NUMERIC(10,6)
- Classification: `property_type` String, `state` String(2), `msa` String, `risk_rating` String, `prior_risk_rating` String, `rate_type` String
- Dates: `origination_date` Date, `maturity_date` Date
- Delinquency: `days_past_due` Integer default 0, `delinquency_status` String
- Pipeline: `pipeline_stage` String, `vintage_year` Integer
- Audit: `created_at` DateTime

`re_loan_cashflows` columns:
- `id`, `loan_id` FK → re_loans, `period_date` Date, `scheduled_principal` NUMERIC(18,6), `actual_principal` NUMERIC(18,6), `scheduled_interest` NUMERIC(18,6), `actual_interest` NUMERIC(18,6), `noi` NUMERIC(18,6), `created_at` DateTime

**Constraint:** All monetary columns NUMERIC(18,6). All rate columns NUMERIC(10,6). No Float for financial values (project-wide).

**Seed Data: Statistically Realistic Distributions**
- 500–600 loans total across both as_of_date snapshots
- LTV: N(0.67, 0.08) clipped [0.40, 0.95]
- DSCR: inversely correlated with LTV, base N(1.35, 0.25) clipped [0.70, 2.80]
- Property types: multifamily 35%, office 20%, retail 15%, industrial 15%, hospitality 10%, mixed-use 5%
- Geographic: ≥20 states, ≥8 MSAs (concentrate NY, CA, TX, FL, IL)
- Risk ratings: AAA/AA/A/BBB/BB/B/CCC bell-curved around BBB
- Rate type: ~60% fixed, 30% floating, 10% hybrid
- Delinquency: ~85% current, ~8% 30-day, ~5% 60-day, ~2% 90+

**Two as_of_date Snapshots**
- T0: 2025-09-30 base snapshot (~500 loans)
- T1: 2025-12-31 updated snapshot (same loans, ~8% downgraded one notch, ~5% upgraded)
- `prior_risk_rating` = T0 rating; `risk_rating` = T1 rating on each row
- Cashflow history: 12 monthly records per loan (Oct 2024 – Sep 2025) — linked to T0 loan records only

**Seed Script**
- File: `backend/scripts/seed_re_loans.py`
- Invocation: `python scripts/seed_re_loans.py` from `backend/` directory
- Idempotent: truncates `re_loan_cashflows` then `re_loans` before re-seeding
- Pattern: follows `backend/scripts/seed_staging_user.py` — direct SQLAlchemy session, bulk inserts

**Alembic Migration Chain**
- Two new migration files chaining from `efe3898fdf4b`:
  1. `add_re_loans_table` — creates `re_loans` with indexes on `as_of_date`, `property_type`, `state`, `sales_team_id`
  2. `add_re_loan_cashflows_table` — creates `re_loan_cashflows` with FK to `re_loans` and composite index on `(loan_id, period_date)`
- SQLAlchemy model classes added to `backend/db/models.py`

### Claude's Discretion

- Exact fake company/borrower name generation approach (faker vs hand-rolled lists)
- Loan number format
- Exact MSA names and state distribution weights
- Whether to use `faker` or `numpy` random generation for string fields

### Deferred Ideas (OUT OF SCOPE)

- Phase 25 side-panel fields (appraisal history, collateral description, covenant notes)
- Live data ingestion or real loan data
- Seed wired into CI or Alembic
</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| DATA-01 | `re_loans` table with all required financial fields using NUMERIC(18,6) for monetary/rate columns, `as_of_date` index, `prior_risk_rating`, and `sales_team_id` FK | Alembic migration pattern from `efe3898fdf4b`; SQLAlchemy `Numeric` type for NUMERIC(18,6) |
| DATA-02 | `re_loan_cashflows` table with monthly records linked to `re_loans` | Composite index on `(loan_id, period_date)`; FK cascade pattern from existing migrations |
| DATA-03 | Seed script populates 500–2,000 loans across ≥5 property types, ≥20 states, ≥8 MSAs, two `as_of_date` snapshots, 12 months of cashflow per loan | `numpy` already installed; `faker` not installed (needs install); bulk insert via `db.bulk_save_objects` |
| DATA-04 | Alembic migrations chain off current head (`efe3898fdf4b`) without conflicts; `alembic upgrade head` succeeds in CI | Current head confirmed `efe3898fdf4b`; `down_revision` must point to this; `env.py` uses `from db.models import *` so new model classes must be added to `models.py` |
</phase_requirements>

---

## Summary

Phase 17 establishes the PostgreSQL database foundation for the v2.0 RE Loan Dashboard. The work consists of three concrete deliverables: two Alembic migrations (creating `re_loans` and `re_loan_cashflows`), corresponding SQLAlchemy model classes in `models.py`, and a seed script that populates realistic CRE portfolio data.

The project's Alembic/SQLAlchemy stack is already well-established and working. The current migration head is `efe3898fdf4b` (audit_log table, 2026-03-10). Both new migrations must chain off this revision. The `env.py` imports `from db.models import *`, which means new model classes added to `models.py` will be automatically detected by Alembic's autogenerate — but for this phase, migrations are hand-written following the existing pattern (not autogenerated) to maintain tight control over NUMERIC precision types.

The critical constraint throughout is `NUMERIC(18,6)` for all monetary columns and `NUMERIC(10,6)` for all rate columns — never `Float`. SQLAlchemy's `Numeric(precision=18, scale=6)` maps directly to this PostgreSQL type. `faker>=33.0.0` is not currently installed (only `numpy` and `scipy` are available); it needs to be added to `requirements-dev.txt` before running the seed script.

**Primary recommendation:** Write migrations manually (not via autogenerate) to precisely control NUMERIC precision. Use `numpy.random` for statistical distributions (LTV, DSCR, interest rates) and `faker` for human-readable string fields (borrower names, loan numbers). The seed script inserts T0 and T1 loan rows separately, then bulk-inserts all cashflow records in a single pass linked to T0 loan IDs.

---

## Standard Stack

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| SQLAlchemy | 2.0.36 [VERIFIED: installed] | ORM / column type definitions | Project standard — already in requirements.txt |
| Alembic | 1.14.0 [VERIFIED: installed] | Database migration management | Project standard — already in requirements.txt |
| psycopg2-binary | 2.9.10 [VERIFIED: requirements.txt] | PostgreSQL driver | Project standard |
| numpy | 2.3.1 [VERIFIED: installed] | Statistical distribution generation | Already installed; N(mu, sigma) sampling, clipping |
| scipy | >=1.11.0 [VERIFIED: requirements.txt] | Truncated normal distributions (optional) | Already installed; `scipy.stats.truncnorm` if needed |

### Supporting (for Seed Script)

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| faker | >=33.0.0 [VERIFIED: STATE.md decision] | Generate borrower names, loan numbers | Seed script only — add to requirements-dev.txt |
| random (stdlib) | stdlib | Categorical sampling (property type, state, etc.) | Use `random.choices(population, weights)` for weighted categorical draws |
| decimal (stdlib) | stdlib | Precise decimal construction from float | Wrap numpy floats as `Decimal(str(value))` before DB insert |

**Installation (seed script dependency only):**
```bash
# From backend/ directory
pip install "faker>=33.0.0"
# And add to requirements-dev.txt:
faker>=33.0.0
```

**Version note:** `faker` is not currently installed [VERIFIED: pip show faker returned no output]. STATE.md locked `faker>=33.0.0` to requirements-dev.txt (not requirements.txt). PostgreSQL 18.1 is running locally [VERIFIED: psql --version].

---

## Architecture Patterns

### Recommended Project Structure (new files only)

```
backend/
├── db/
│   └── models.py                    # Add RELoan + RELoanCashflow classes here
├── migrations/
│   └── versions/
│       ├── efe3898fdf4b_add_audit_log_table.py   # current head (DO NOT TOUCH)
│       ├── XXXX_add_re_loans_table.py             # new migration 1
│       └── YYYY_add_re_loan_cashflows_table.py    # new migration 2
└── scripts/
    └── seed_re_loans.py             # new seed script
```

### Pattern 1: Alembic Migration (hand-written, following project convention)

**What:** Create table with NUMERIC columns, indexes, and FK constraints. `op.f()` naming convention used throughout the project for all indexes.

**When to use:** Any new table addition — never autogenerate when NUMERIC precision matters.

**Example (from `efe3898fdf4b`, adapted for re_loans):**
```python
# Source: backend/migrations/versions/efe3898fdf4b_add_audit_log_table.py [VERIFIED]
from alembic import op
import sqlalchemy as sa

revision = "XXXX"
down_revision = "efe3898fdf4b"   # chain from current head
branch_labels = None
depends_on = None

def upgrade() -> None:
    op.create_table(
        "re_loans",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("loan_number", sa.String(length=50), nullable=False),
        sa.Column("borrower_name", sa.String(length=255), nullable=True),
        sa.Column("sales_team_id", sa.Integer(), nullable=True),
        sa.Column("as_of_date", sa.Date(), nullable=False),
        sa.Column("upb", sa.Numeric(precision=18, scale=6), nullable=True),
        sa.Column("original_balance", sa.Numeric(precision=18, scale=6), nullable=True),
        sa.Column("interest_rate", sa.Numeric(precision=10, scale=6), nullable=True),
        sa.Column("wam_months", sa.Integer(), nullable=True),
        sa.Column("ltv", sa.Numeric(precision=10, scale=6), nullable=True),
        sa.Column("dscr", sa.Numeric(precision=10, scale=6), nullable=True),
        sa.Column("property_type", sa.String(length=50), nullable=True),
        sa.Column("state", sa.String(length=2), nullable=True),
        sa.Column("msa", sa.String(length=100), nullable=True),
        sa.Column("risk_rating", sa.String(length=10), nullable=True),
        sa.Column("prior_risk_rating", sa.String(length=10), nullable=True),
        sa.Column("rate_type", sa.String(length=20), nullable=True),
        sa.Column("origination_date", sa.Date(), nullable=True),
        sa.Column("maturity_date", sa.Date(), nullable=True),
        sa.Column("days_past_due", sa.Integer(), nullable=True),
        sa.Column("delinquency_status", sa.String(length=20), nullable=True),
        sa.Column("pipeline_stage", sa.String(length=30), nullable=True),
        sa.Column("vintage_year", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["sales_team_id"], ["sales_teams.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_re_loans_id"), "re_loans", ["id"], unique=False)
    op.create_index(op.f("ix_re_loans_loan_number"), "re_loans", ["loan_number"], unique=False)
    op.create_index(op.f("ix_re_loans_as_of_date"), "re_loans", ["as_of_date"], unique=False)
    op.create_index(op.f("ix_re_loans_property_type"), "re_loans", ["property_type"], unique=False)
    op.create_index(op.f("ix_re_loans_state"), "re_loans", ["state"], unique=False)
    op.create_index(op.f("ix_re_loans_sales_team_id"), "re_loans", ["sales_team_id"], unique=False)

def downgrade() -> None:
    op.drop_index(op.f("ix_re_loans_sales_team_id"), table_name="re_loans")
    op.drop_index(op.f("ix_re_loans_state"), table_name="re_loans")
    op.drop_index(op.f("ix_re_loans_property_type"), table_name="re_loans")
    op.drop_index(op.f("ix_re_loans_as_of_date"), table_name="re_loans")
    op.drop_index(op.f("ix_re_loans_loan_number"), table_name="re_loans")
    op.drop_index(op.f("ix_re_loans_id"), table_name="re_loans")
    op.drop_table("re_loans")
```

### Pattern 2: SQLAlchemy Model with Numeric Columns

**What:** Add model class to `models.py` using `sa.Numeric` not `Float`.

**When to use:** All financial value columns — project-wide constraint.

**Example:**
```python
# Source: backend/db/models.py patterns [VERIFIED] + project NUMERIC constraint [VERIFIED: CONTEXT.md, PROJECT.md]
from sqlalchemy import Numeric

class RELoan(Base):
    __tablename__ = "re_loans"

    id = Column(Integer, primary_key=True, index=True)
    loan_number = Column(String(50), index=True, nullable=False)
    borrower_name = Column(String(255))
    sales_team_id = Column(Integer, ForeignKey("sales_teams.id"), nullable=True)
    as_of_date = Column(Date, nullable=False, index=True)

    # Financials — NUMERIC, never Float
    upb = Column(Numeric(18, 6))
    original_balance = Column(Numeric(18, 6))
    interest_rate = Column(Numeric(10, 6))
    wam_months = Column(Integer)
    ltv = Column(Numeric(10, 6))
    dscr = Column(Numeric(10, 6))

    # Classification
    property_type = Column(String(50), index=True)
    state = Column(String(2), index=True)
    msa = Column(String(100))
    risk_rating = Column(String(10))
    prior_risk_rating = Column(String(10))
    rate_type = Column(String(20))

    # Dates
    origination_date = Column(Date)
    maturity_date = Column(Date)

    # Delinquency
    days_past_due = Column(Integer, default=0)
    delinquency_status = Column(String(20))

    # Pipeline
    pipeline_stage = Column(String(30))
    vintage_year = Column(Integer)

    # Audit
    created_at = Column(DateTime, default=datetime.utcnow)

    sales_team = relationship("SalesTeam")
    cashflows = relationship("RELoanCashflow", back_populates="loan")
```

### Pattern 3: Seed Script Structure

**What:** Idempotent seed that truncates child table first, then parent, then re-inserts.

**When to use:** Any seed script that can be re-run safely.

**Example:**
```python
# Source: backend/scripts/seed_staging_user.py pattern [VERIFIED] + CONTEXT.md decisions [VERIFIED]
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import numpy as np
from decimal import Decimal
from datetime import date, datetime
from faker import Faker
from sqlalchemy.orm import Session
from db.connection import SessionLocal
from db.models import RELoan, RELoanCashflow

fake = Faker()
rng = np.random.default_rng(seed=42)   # reproducible seed

def seed_re_loans() -> None:
    db: Session = SessionLocal()
    try:
        # Idempotent: truncate child before parent (FK constraint order)
        db.query(RELoanCashflow).delete()
        db.query(RELoan).delete()
        db.commit()

        # Generate T0 loans ...
        # Generate T1 loans (same loan_number, updated risk ratings) ...
        # Bulk insert loans ...
        # Generate 12 cashflow records per T0 loan ...
        # Bulk insert cashflows ...
        db.commit()
        print(f"Seeded {len(t0_loans)} T0 loans, {len(t1_loans)} T1 loans, {len(cashflows)} cashflow records")
    finally:
        db.close()

if __name__ == "__main__":
    seed_re_loans()
```

### Pattern 4: Statistical Distribution for LTV/DSCR

**What:** Generate correlated LTV/DSCR values using numpy with clipping.

**Example:**
```python
# Source: CONTEXT.md locked distributions [VERIFIED] + numpy docs [ASSUMED standard usage]
n_loans = 500
rng = np.random.default_rng(seed=42)

ltv_raw = rng.normal(loc=0.67, scale=0.08, size=n_loans)
ltv = np.clip(ltv_raw, 0.40, 0.95)

# DSCR inversely correlated: higher LTV → lower DSCR
dscr_noise = rng.normal(loc=0, scale=0.20, size=n_loans)
dscr_base = 1.35 - 0.8 * (ltv - 0.67)    # inverse correlation factor
dscr = np.clip(dscr_base + dscr_noise, 0.70, 2.80)

# Convert to Decimal for DB insert (never insert numpy float64 directly)
ltv_decimal = Decimal(str(round(float(ltv[i]), 6)))
```

### Pattern 5: Two-Snapshot Design

**What:** T0 and T1 are separate rows in `re_loans` with the SAME `loan_number` but different `as_of_date`, `risk_rating`, and `prior_risk_rating`.

**Key constraint:** Cashflows belong only to T0 rows (by `loan_id`). T1 rows have no cashflow records.

**Implication for seed script:** Insert T0 rows first, capture their auto-generated `id` values, then insert T1 rows. Cashflows reference T0 `id` values only.

```python
# After inserting T0 loans and flushing to get IDs:
db.flush()   # forces Postgres to assign IDs without commit
t0_ids = [loan.id for loan in t0_loans]
# Insert cashflows referencing t0_ids
# Then insert T1 loans
```

### Anti-Patterns to Avoid

- **Using `Float` for financial columns:** Use `Numeric(18, 6)` in both SQLAlchemy model and Alembic migration. `Float` loses precision on aggregation across 500+ rows.
- **Using `db.add()` in a loop for bulk inserts:** Use `db.bulk_save_objects(list_of_objects)` or `db.add_all(list)` — single round-trip for 500+ loans + 6,000 cashflow records.
- **Inserting numpy float64 directly:** Always convert: `Decimal(str(round(float(val), 6)))` before DB insert. SQLAlchemy Numeric accepts Python `Decimal` and `float` but numpy types can cause dialect-level errors.
- **Autogenerating migration from model:** Never run `alembic revision --autogenerate` for these tables — autogenerate infers `Float` for Python `float` attributes. Hand-write the migration to guarantee `sa.Numeric(18, 6)`.
- **Deleting parent before child:** The FK from `re_loan_cashflows.loan_id → re_loans.id` means cashflows must be deleted before loans. Truncating in wrong order raises FK violation.
- **Using `db.flush()` without `autoflush=False`:** The `SessionLocal` uses `autoflush=False` [VERIFIED: db/connection.py], so `db.flush()` is explicit and safe to use before `commit()` to capture IDs.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Statistical distributions | Custom random generator | `numpy.random.default_rng().normal()` + `np.clip()` | Reproducible, vectorized, already installed |
| Fake borrower names | Static list of 50 names | `faker.company()` or `faker.name()` | >10,000 unique values, locale-aware |
| Weighted categorical sampling | Manual probability loop | `random.choices(population, weights=weights)` | Stdlib, clean, weights sum handled automatically |
| Migration revision IDs | Hand-typed hex strings | `alembic revision -m "add_re_loans_table"` | Alembic generates collision-free 12-char hex IDs |
| Decimal conversion | String format gymnastics | `Decimal(str(round(float(val), 6)))` | One-liner; avoids float repr artifacts |

**Key insight:** The seed script is the only place where `faker` is needed. All statistical generation can use `numpy` (already installed). The seed script should never be called from application code — it's a one-time ops tool.

---

## Common Pitfalls

### Pitfall 1: Migration Chain Break
**What goes wrong:** New migration sets `down_revision` to the wrong value, creating a branch or detached head. `alembic upgrade head` fails or applies only partial migrations.
**Why it happens:** Copy-pasting an old migration template without updating `down_revision`.
**How to avoid:** After generating with `alembic revision -m "add_re_loans_table"`, verify the generated file has `down_revision = "efe3898fdf4b"`. Run `alembic heads` — should show exactly one head.
**Warning signs:** `alembic upgrade head` says "Running upgrade efe3898fdf4b -> XXXX" but then stops before the cashflows migration.

### Pitfall 2: NUMERIC vs Numeric Casing in SQLAlchemy
**What goes wrong:** Using `sa.NUMERIC` (Postgres-dialect uppercase) in the migration instead of `sa.Numeric`. Both work against Postgres but `sa.NUMERIC` without precision args defaults to unconstrained numeric.
**Why it happens:** Copying from PostgreSQL docs where `NUMERIC(18,6)` is uppercase.
**How to avoid:** Always use `sa.Numeric(precision=18, scale=6)` in both the migration and the model.
**Warning signs:** `\d re_loans` in psql shows `numeric` without precision annotation.

### Pitfall 3: FK Constraint Ordering in Downgrade
**What goes wrong:** `downgrade()` tries to drop `re_loans` before `re_loan_cashflows`. Postgres raises: `ERROR: cannot drop table re_loans because other objects depend on it`.
**Why it happens:** Reverse order not respected in downgrade function.
**How to avoid:** Downgrade for `add_re_loan_cashflows_table` runs first (it's a later migration). Downgrade for `add_re_loans_table` then drops `re_loans`. This is correct by default if the two migrations are separate files — Alembic downgrades in reverse order automatically.
**Warning signs:** `alembic downgrade -1` fails with FK violation.

### Pitfall 4: Env.py Model Import for New Tables
**What goes wrong:** New model classes not imported in `env.py`, causing `alembic check` or autogenerate to miss the new tables.
**Why it happens:** Forgetting that `env.py` uses `from db.models import *` — new classes ARE auto-included, but only if they are added to `models.py`. If models are in a new file, they won't be picked up.
**How to avoid:** Add `RELoan` and `RELoanCashflow` to `backend/db/models.py` (the existing file), not a new module. [VERIFIED: env.py imports `from db.models import *`]
**Warning signs:** `alembic check` reports tables as missing from ORM even after adding models.

### Pitfall 5: T0/T1 Cashflow Linkage Error
**What goes wrong:** Cashflow records accidentally linked to T1 loan IDs instead of T0. Phase 23 cashflow queries return 0 records for loans.
**Why it happens:** Seed script uses the last-inserted loan IDs without distinguishing T0 from T1.
**How to avoid:** After inserting T0 loans, call `db.flush()` to get IDs, store them in a list, then insert T1 loans. Cashflows are created from the T0 ID list only. Never use `db.query(RELoan).all()` to get IDs at insert time — the list will contain both T0 and T1.
**Warning signs:** `SELECT COUNT(*) FROM re_loan_cashflows` returns 500*12=6,000 rows but joining to T1 loans returns all of them.

### Pitfall 6: Numpy Float64 to SQLAlchemy Numeric
**What goes wrong:** Passing `numpy.float64` directly to a `Numeric(18,6)` column raises `ProgrammingError: can't adapt type 'numpy.float64'` with psycopg2.
**Why it happens:** psycopg2 does not natively adapt numpy scalar types.
**How to avoid:** Convert: `float(numpy_val)` or `Decimal(str(round(float(numpy_val), 6)))` before constructing model objects.
**Warning signs:** Script runs fine for first few rows then crashes with adaptation error.

### Pitfall 7: Faker Not in requirements-dev.txt
**What goes wrong:** Seed script works locally but fails in CI or on a fresh clone because `faker` isn't in any requirements file.
**Why it happens:** Installing locally with `pip install faker` without updating `requirements-dev.txt`.
**How to avoid:** Add `faker>=33.0.0` to `requirements-dev.txt` (which doesn't yet exist — needs to be created or the line added). STATE.md decision is clear: dev dependency only, not production requirements.txt.
**Warning signs:** `ModuleNotFoundError: No module named 'faker'` in CI.

---

## Code Examples

### Bulk Insert Pattern (from SQLAlchemy 2 conventions)
```python
# Source: SQLAlchemy 2.0 docs — Session.bulk_save_objects [ASSUMED: standard 2.0 pattern]
# Preferred for large inserts (500 loans + 6000 cashflows)
loan_objects = [RELoan(...) for _ in range(n)]
db.bulk_save_objects(loan_objects)
db.flush()   # get IDs assigned without commit

# For cashflows after T0 IDs are known:
cashflow_objects = [RELoanCashflow(loan_id=lid, ...) for lid in t0_ids for month in range(12)]
db.bulk_save_objects(cashflow_objects)
db.commit()
```

### Weighted Categorical Sampling
```python
# Source: Python stdlib docs [ASSUMED: standard random.choices usage]
import random

PROPERTY_TYPES = ["multifamily", "office", "retail", "industrial", "hospitality", "mixed-use"]
PROPERTY_WEIGHTS = [35, 20, 15, 15, 10, 5]

property_type = random.choices(PROPERTY_TYPES, weights=PROPERTY_WEIGHTS, k=n_loans)
```

### Risk Rating Migration for T1 Snapshot
```python
# Source: CONTEXT.md decisions [VERIFIED]
RATING_LADDER = ["AAA", "AA", "A", "BBB", "BB", "B", "CCC"]

def apply_migration(rating: str, direction: int) -> str:
    """direction: -1 = downgrade, 0 = unchanged, +1 = upgrade"""
    idx = RATING_LADDER.index(rating)
    new_idx = max(0, min(len(RATING_LADDER) - 1, idx - direction))  # lower index = better rating
    return RATING_LADDER[new_idx]

# For each T0 loan: 8% downgrade, 5% upgrade, 87% unchanged
outcomes = random.choices([-1, 0, 1], weights=[8, 87, 5], k=len(t0_loans))
```

### Alembic Composite Index on (loan_id, period_date)
```python
# Source: CONTEXT.md decision + Alembic op.create_index docs [ASSUMED: standard pattern]
op.create_index(
    "ix_re_loan_cashflows_loan_period",
    "re_loan_cashflows",
    ["loan_id", "period_date"],
    unique=False,
)
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `alembic revision --autogenerate` | Hand-written migrations for NUMERIC tables | Project convention from Phase 7 | Prevents Float/Numeric type inference errors |
| `Session.add()` in loop | `Session.bulk_save_objects()` | SQLAlchemy 1.4+ | 10–50x faster for >100 rows |
| `declarative_base()` from `sqlalchemy.ext.declarative` | Same — project uses pre-2.0 compat import [VERIFIED: db/connection.py] | Not changed | The import works in SQLAlchemy 2.0 but shows deprecation warning; acceptable for now |

**Deprecated/outdated:**
- `Float` for financial columns: Project-wide constraint prohibits this. All existing `Float` columns in `models.py` are legacy (LoanFact, PipelineRun) — new tables use `Numeric`.

---

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | `db.bulk_save_objects()` is the correct bulk insert API for SQLAlchemy 2.0 | Architecture Patterns / Code Examples | Minor — `session.add_all(list)` is equivalent and also works; performance difference is negligible at 500 loans |
| A2 | `random.choices()` weights do not need to sum to 100 (relative weights accepted) | Code Examples | None — Python stdlib `random.choices` explicitly supports relative weights |
| A3 | `scipy.stats.truncnorm` is not needed — `np.clip` on normal samples is sufficient for the distributions specified | Standard Stack | Low — both approaches produce valid truncated distributions; `np.clip` is simpler and already available |
| A4 | Alembic revision IDs are generated by running `alembic revision -m "..."` from `backend/` directory with the virtualenv active | Common Pitfalls | Low — standard Alembic workflow |

---

## Open Questions

1. **`requirements-dev.txt` does not exist yet**
   - What we know: STATE.md says `faker>=33.0.0` goes in `requirements-dev.txt`. The file doesn't exist [VERIFIED: only `requirements.txt` found in `backend/`].
   - What's unclear: Should the planner create `requirements-dev.txt` as a new file, or add `faker` as a comment/section in `requirements.txt`?
   - Recommendation: Create `backend/requirements-dev.txt` as a new file with `faker>=33.0.0`. This is unambiguously correct per STATE.md.

2. **`sales_teams` table seeding for `sales_team_id` FK**
   - What we know: `re_loans.sales_team_id` is a FK to `sales_teams.id`. The `sales_teams` table may have no rows in a fresh local DB.
   - What's unclear: Should the seed script create a default sales team if none exists, or seed with `sales_team_id=NULL`?
   - Recommendation: Seed with `nullable=True` and leave `sales_team_id=NULL` for most loans (or a subset). The FK allows NULL. This avoids a dependency on the sales_teams table being pre-populated, which would make the seed script non-standalone.

3. **Whether to use `db.flush()` or add-then-commit for getting T0 IDs**
   - What we know: `SessionLocal` uses `autoflush=False` [VERIFIED: db/connection.py].
   - What's unclear: Whether `bulk_save_objects` populates `id` fields on the Python objects after flush.
   - Recommendation: Use `db.add_all(t0_loan_objects); db.flush()` instead of `bulk_save_objects` for T0 loans specifically, since `flush()` after `add_all` reliably populates autoincrement IDs on the objects. Use `bulk_save_objects` for T1 loans and cashflows where IDs aren't needed.

---

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python | All | ✓ | 3.12.9 | — |
| PostgreSQL | Migrations, seed | ✓ | 18.1 | — |
| SQLAlchemy | Models, migrations | ✓ | 2.0.36 | — |
| Alembic | Migrations | ✓ | 1.14.0 | — |
| numpy | Seed distributions | ✓ | 2.3.1 | — |
| scipy | Truncated normal (optional) | ✓ | >=1.11.0 in requirements.txt | np.clip on normal samples |
| faker | Seed string fields | ✗ | not installed | Use `uuid` / static lists (degraded quality) |
| psycopg2-binary | DB driver | ✓ | 2.9.10 | — |

**Missing dependencies with no fallback:**
- None — PostgreSQL and all required libs are present.

**Missing dependencies with fallback:**
- `faker`: not installed. Fallback is static lists for borrower names, but quality is degraded. Plan must include `pip install faker>=33.0.0` and creating `requirements-dev.txt`.

---

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest 8.3.3 |
| Config file | `backend/pytest.ini` |
| Quick run command | `cd backend && pytest tests/test_db_models.py -x -v` |
| Full suite command | `cd backend && pytest -v` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| DATA-01 | `re_loans` table has correct schema — NUMERIC(18,6) for monetary cols, NUMERIC(10,6) for rate cols | unit | `pytest tests/test_re_loans_schema.py -x` | ❌ Wave 0 |
| DATA-02 | `re_loan_cashflows` has FK to `re_loans`, composite index on (loan_id, period_date) | unit | `pytest tests/test_re_loans_schema.py::test_cashflow_schema -x` | ❌ Wave 0 |
| DATA-03 | Seed script is idempotent; produces ≥500 loans, 2 as_of_date values, ≥5 property types, 12 cashflows per T0 loan | integration | `pytest tests/test_re_loans_schema.py::test_seed_idempotent -x -m integration` | ❌ Wave 0 |
| DATA-04 | Alembic migrations apply cleanly from `efe3898fdf4b` head | smoke | Manual: `alembic upgrade head` with no errors | N/A — manual verification |

### Sampling Rate
- **Per task commit:** `cd backend && pytest tests/test_re_loans_schema.py -x -v`
- **Per wave merge:** `cd backend && pytest -v`
- **Phase gate:** Full suite green + manual `alembic upgrade head` verification before `/gsd-verify-work`

### Wave 0 Gaps
- [ ] `tests/test_re_loans_schema.py` — covers DATA-01, DATA-02, DATA-03 schema and seed assertions
- [ ] Framework install: `pip install faker>=33.0.0` — seed script dependency

**Note:** DATA-03 integration test should be marked `@pytest.mark.integration` and excluded from default `pytest` run per project convention (pytest.ini: `-m "not integration"`).

---

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | no | — |
| V3 Session Management | no | — |
| V4 Access Control | no | — |
| V5 Input Validation | no | Seed script only — no user input |
| V6 Cryptography | no | — |

**Security note:** The seed script runs locally / as a one-off ECS task. It contains no user-facing input and no secrets beyond `DATABASE_URL` from environment (the project-standard `settings.DATABASE_URL` via `db.connection.SessionLocal`). No additional security controls needed for this phase.

---

## Sources

### Primary (HIGH confidence)
- `backend/db/models.py` [VERIFIED: read] — existing model patterns, import structure, column type conventions
- `backend/migrations/versions/efe3898fdf4b_add_audit_log_table.py` [VERIFIED: read] — current Alembic head, migration file structure, `op.f()` naming convention
- `backend/migrations/versions/60a8a67090c8_initial_schema.py` [VERIFIED: read] — FK constraint patterns, full index naming convention
- `backend/migrations/env.py` [VERIFIED: read] — `from db.models import *` confirmed; model classes must be in `models.py`
- `backend/scripts/seed_staging_user.py` [VERIFIED: read] — seed script pattern: `SessionLocal()`, query-then-upsert, `if __name__ == "__main__"`
- `backend/db/connection.py` [VERIFIED: read] — `autoflush=False` confirmed on `SessionLocal`
- `backend/requirements.txt` [VERIFIED: read] — numpy 2.x, scipy, sqlalchemy 2.0.36, alembic 1.14.0 present; faker absent
- `backend/pytest.ini` [VERIFIED: read] — pytest config, `not integration` default marker
- `.planning/phases/17-data-foundation/17-CONTEXT.md` [VERIFIED: read] — all locked decisions
- `.planning/STATE.md` [VERIFIED: read] — `faker>=33.0.0` to requirements-dev.txt, NUMERIC constraint decision
- pip show output [VERIFIED: bash] — faker not installed, numpy 2.3.1 installed, alembic 1.14.0, sqlalchemy 2.0.36
- psql --version [VERIFIED: bash] — PostgreSQL 18.1 available; pg_isready returns accepting connections

### Secondary (MEDIUM confidence)
- numpy `random.default_rng().normal()` + `np.clip()` — standard vectorized sampling, well-established API

### Tertiary (LOW confidence)
- None

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all libraries verified via pip show and requirements.txt
- Architecture: HIGH — all patterns derived from verified existing codebase files
- Pitfalls: HIGH — most derived from reading actual code and FK/type constraints in the project
- Seed distributions: HIGH — directly from CONTEXT.md locked decisions; numpy math is standard

**Research date:** 2026-04-08
**Valid until:** 2026-05-08 (stable stack — Alembic/SQLAlchemy versions locked in requirements.txt)
