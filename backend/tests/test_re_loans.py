"""Tests for RE loan data foundation (Phase 17: DATA-01 through DATA-04)."""

from decimal import Decimal
from datetime import date
from sqlalchemy import Numeric as SANumeric

from db.models import RELoan, RELoanCashflow


# ---------------------------------------------------------------------------
# DATA-01: re_loans schema tests
# ---------------------------------------------------------------------------


def test_re_loans_table_columns():
    """Verify RELoan model has all 24 expected columns (DATA-01)."""
    cols = {c.name for c in RELoan.__table__.columns}
    expected = {
        "id",
        "loan_number",
        "borrower_name",
        "sales_team_id",
        "as_of_date",
        "upb",
        "original_balance",
        "interest_rate",
        "wam_months",
        "ltv",
        "dscr",
        "property_type",
        "state",
        "msa",
        "risk_rating",
        "prior_risk_rating",
        "rate_type",
        "origination_date",
        "maturity_date",
        "days_past_due",
        "delinquency_status",
        "pipeline_stage",
        "vintage_year",
        "created_at",
    }
    assert cols == expected, f"Missing: {expected - cols}, Extra: {cols - expected}"


def test_re_loans_numeric_precision():
    """Verify monetary and rate columns use correct Numeric precision (DATA-01)."""
    table = RELoan.__table__

    # Monetary columns: NUMERIC(18,6)
    monetary_cols = ["upb", "original_balance"]
    for col_name in monetary_cols:
        col = table.c[col_name]
        assert isinstance(col.type, SANumeric), f"{col_name} is not Numeric"
        assert col.type.precision == 18, f"{col_name} precision is {col.type.precision}, expected 18"
        assert col.type.scale == 6, f"{col_name} scale is {col.type.scale}, expected 6"

    # Rate columns: NUMERIC(10,6)
    rate_cols = ["interest_rate", "ltv", "dscr"]
    for col_name in rate_cols:
        col = table.c[col_name]
        assert isinstance(col.type, SANumeric), f"{col_name} is not Numeric"
        assert col.type.precision == 10, f"{col_name} precision is {col.type.precision}, expected 10"
        assert col.type.scale == 6, f"{col_name} scale is {col.type.scale}, expected 6"


# ---------------------------------------------------------------------------
# DATA-02: re_loan_cashflows schema tests
# ---------------------------------------------------------------------------


def test_re_loan_cashflows_table_columns():
    """Verify RELoanCashflow model has all 9 expected columns (DATA-02)."""
    cols = {c.name for c in RELoanCashflow.__table__.columns}
    expected = {
        "id",
        "loan_id",
        "period_date",
        "scheduled_principal",
        "actual_principal",
        "scheduled_interest",
        "actual_interest",
        "noi",
        "created_at",
    }
    assert cols == expected, f"Missing: {expected - cols}, Extra: {cols - expected}"


def test_re_loan_cashflows_numeric_precision():
    """Verify all 5 cashflow amount columns use NUMERIC(18,6) (DATA-02)."""
    table = RELoanCashflow.__table__
    monetary_cols = [
        "scheduled_principal",
        "actual_principal",
        "scheduled_interest",
        "actual_interest",
        "noi",
    ]
    for col_name in monetary_cols:
        col = table.c[col_name]
        assert isinstance(col.type, SANumeric), f"{col_name} is not Numeric"
        assert col.type.precision == 18, f"{col_name} precision is {col.type.precision}, expected 18"
        assert col.type.scale == 6, f"{col_name} scale is {col.type.scale}, expected 6"


def test_re_loan_cashflows_fk():
    """Verify loan_id FK references re_loans.id (DATA-02)."""
    fks = list(RELoanCashflow.__table__.foreign_keys)
    assert len(fks) == 1, f"Expected 1 FK, found {len(fks)}"
    assert fks[0].column.table.name == "re_loans", (
        f"FK references table '{fks[0].column.table.name}', expected 're_loans'"
    )
    assert fks[0].column.name == "id", f"FK references column '{fks[0].column.name}', expected 'id'"


# ---------------------------------------------------------------------------
# DATA-01 / DATA-03: Functional insert-and-query tests (in-memory SQLite)
# ---------------------------------------------------------------------------


def test_re_loan_insert_and_query(test_db_session):
    """Insert a RELoan with Decimal values and query it back (DATA-01, DATA-03)."""
    loan = RELoan(
        loan_number="TEST-00001",
        as_of_date=date(2025, 9, 30),
        upb=Decimal("1500000.123456"),
        original_balance=Decimal("1600000.000000"),
        interest_rate=Decimal("5.500000"),
        ltv=Decimal("0.670000"),
        dscr=Decimal("1.350000"),
        property_type="multifamily",
        state="NY",
        msa="New York-Newark-Jersey City",
        risk_rating="BBB",
        prior_risk_rating="BBB",
        rate_type="fixed",
    )
    test_db_session.add(loan)
    test_db_session.flush()

    assert loan.id is not None, "loan.id should be set after flush"

    queried = test_db_session.query(RELoan).filter(RELoan.loan_number == "TEST-00001").first()
    assert queried is not None
    assert queried.property_type == "multifamily"
    assert queried.state == "NY"
    assert queried.risk_rating == "BBB"
    assert queried.as_of_date == date(2025, 9, 30)


# ---------------------------------------------------------------------------
# DATA-02 / DATA-04: Cashflow insert tests (in-memory SQLite)
# ---------------------------------------------------------------------------


def test_re_loan_cashflow_insert(test_db_session):
    """Insert a loan and linked cashflow; verify FK relationship works (DATA-02, DATA-04)."""
    loan = RELoan(
        loan_number="TEST-CF-001",
        as_of_date=date(2025, 9, 30),
        upb=Decimal("1000000.000000"),
        property_type="office",
        state="CA",
    )
    test_db_session.add(loan)
    test_db_session.flush()

    cf = RELoanCashflow(
        loan_id=loan.id,
        period_date=date(2024, 10, 1),
        scheduled_principal=Decimal("2777.777778"),
        actual_principal=Decimal("2700.000000"),
        scheduled_interest=Decimal("4583.333333"),
        actual_interest=Decimal("4583.333333"),
        noi=Decimal("15000.000000"),
    )
    test_db_session.add(cf)
    test_db_session.flush()

    assert cf.id is not None, "cf.id should be set after flush"
    assert cf.loan_id == loan.id, "cashflow.loan_id must match loan.id"


def test_re_loan_cashflow_relationship(test_db_session):
    """Verify ORM relationship: loan.cashflows returns linked cashflows (DATA-02, DATA-04)."""
    loan = RELoan(
        loan_number="TEST-CF-REL-001",
        as_of_date=date(2025, 9, 30),
        upb=Decimal("2000000.000000"),
        property_type="retail",
        state="TX",
    )
    test_db_session.add(loan)
    test_db_session.flush()

    # Add 12 monthly cashflows
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
    for pd_date in period_dates:
        test_db_session.add(
            RELoanCashflow(
                loan_id=loan.id,
                period_date=pd_date,
                scheduled_principal=Decimal("5555.555556"),
                actual_principal=Decimal("5500.000000"),
                scheduled_interest=Decimal("9166.666667"),
                actual_interest=Decimal("9166.666667"),
                noi=Decimal("30000.000000"),
            )
        )
    test_db_session.flush()

    # Verify relationship via ORM
    test_db_session.expire(loan)
    reloaded = test_db_session.query(RELoan).filter(RELoan.id == loan.id).first()
    assert len(reloaded.cashflows) == 12, f"Expected 12 cashflows, found {len(reloaded.cashflows)}"
