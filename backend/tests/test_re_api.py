"""Integration tests for the RE Portfolio API (Phase 18).

Wave 0: fixture infrastructure + stub tests.
Task 3 fleshes out API-01 through API-04 and API-11 tests.
Plan 02 implements and activates API-05 through API-10 tests.
"""

from datetime import date
from decimal import Decimal

import pytest

from db.models import RELoan, RELoanCashflow


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def re_loan_fixtures(test_db_session, sample_sales_team):
    """Create 5 RELoan rows and 3 RELoanCashflow rows per loan.

    Layout:
      Loan 1: Multifamily, NY, sales_team_id=sample_sales_team.id
      Loan 2: Office,      CA, sales_team_id=sample_sales_team.id
      Loan 3: Retail,      TX, sales_team_id=None
      Loan 4: Multifamily, FL, sales_team_id=None
      Loan 5: Industrial,  NY, sales_team_id=sample_sales_team.id

    All loans share as_of_date=2026-03-01.
    """
    as_of = date(2026, 3, 1)

    loans = [
        RELoan(
            loan_number="RE-001",
            borrower_name="Borrower Alpha",
            sales_team_id=sample_sales_team.id,
            as_of_date=as_of,
            upb=Decimal("5000000.00"),
            original_balance=Decimal("5500000.00"),
            interest_rate=Decimal("0.065"),
            wam_months=240,
            ltv=Decimal("0.60"),
            dscr=Decimal("1.5"),
            property_type="Multifamily",
            state="NY",
            msa="New York-Newark",
            risk_rating="A",
            rate_type="Fixed",
            origination_date=date(2022, 1, 15),
            maturity_date=date(2032, 1, 15),
            days_past_due=0,
            delinquency_status="current",
            pipeline_stage="active",
            vintage_year=2022,
        ),
        RELoan(
            loan_number="RE-002",
            borrower_name="Borrower Beta",
            sales_team_id=sample_sales_team.id,
            as_of_date=as_of,
            upb=Decimal("8000000.00"),
            original_balance=Decimal("8500000.00"),
            interest_rate=Decimal("0.072"),
            wam_months=180,
            ltv=Decimal("0.70"),
            dscr=Decimal("1.2"),
            property_type="Office",
            state="CA",
            msa="Los Angeles",
            risk_rating="B",
            rate_type="Floating",
            origination_date=date(2021, 6, 1),
            maturity_date=date(2031, 6, 1),
            days_past_due=35,
            delinquency_status="30dpd",
            pipeline_stage="active",
            vintage_year=2021,
        ),
        RELoan(
            loan_number="RE-003",
            borrower_name="Borrower Gamma",
            sales_team_id=None,
            as_of_date=as_of,
            upb=Decimal("3000000.00"),
            original_balance=Decimal("3200000.00"),
            interest_rate=Decimal("0.068"),
            wam_months=120,
            ltv=Decimal("0.78"),
            dscr=Decimal("0.95"),
            property_type="Retail",
            state="TX",
            msa="Dallas",
            risk_rating="C",
            rate_type="Fixed",
            origination_date=date(2023, 3, 10),
            maturity_date=date(2028, 3, 10),
            days_past_due=0,
            delinquency_status="current",
            pipeline_stage="active",
            vintage_year=2023,
        ),
        RELoan(
            loan_number="RE-004",
            borrower_name="Borrower Delta",
            sales_team_id=None,
            as_of_date=as_of,
            upb=Decimal("12000000.00"),
            original_balance=Decimal("13000000.00"),
            interest_rate=Decimal("0.061"),
            wam_months=300,
            ltv=Decimal("0.55"),
            dscr=Decimal("1.8"),
            property_type="Multifamily",
            state="FL",
            msa="Miami",
            risk_rating="A",
            rate_type="Fixed",
            origination_date=date(2020, 9, 20),
            maturity_date=date(2030, 9, 20),
            days_past_due=0,
            delinquency_status="current",
            pipeline_stage="active",
            vintage_year=2020,
        ),
        RELoan(
            loan_number="RE-005",
            borrower_name="Borrower Epsilon",
            sales_team_id=sample_sales_team.id,
            as_of_date=as_of,
            upb=Decimal("2500000.00"),
            original_balance=Decimal("2700000.00"),
            interest_rate=Decimal("0.075"),
            wam_months=96,
            ltv=Decimal("0.68"),
            dscr=Decimal("1.35"),
            property_type="Industrial",
            state="NY",
            msa="New York-Newark",
            risk_rating="B",
            rate_type="Floating",
            origination_date=date(2023, 11, 5),
            maturity_date=date(2031, 11, 5),
            days_past_due=0,
            delinquency_status="current",
            pipeline_stage="active",
            vintage_year=2023,
        ),
    ]

    for loan in loans:
        test_db_session.add(loan)
    test_db_session.flush()  # get IDs before adding cashflows

    # 3 cashflow rows per loan
    for loan in loans:
        for i in range(3):
            cf = RELoanCashflow(
                loan_id=loan.id,
                period_date=date(2026, 1 + i, 1),
                scheduled_principal=Decimal("10000.00"),
                actual_principal=Decimal("9500.00"),
                scheduled_interest=Decimal("2500.00"),
                actual_interest=Decimal("2500.00"),
                noi=Decimal("15000.00"),
            )
            test_db_session.add(cf)

    test_db_session.commit()
    return loans


# ---------------------------------------------------------------------------
# API-01 — KPIs
# ---------------------------------------------------------------------------


def test_kpis(client, re_loan_fixtures, auth_headers_admin):
    """API-01: KPI aggregations return non-zero values from seeded fixture data."""
    response = client.get("/api/re/kpis", headers=auth_headers_admin)
    assert response.status_code == 200
    data = response.json()
    assert Decimal(str(data["total_upb"])) > 0
    assert data["wac"] is not None
    assert data["active_loan_count"] == 5
    assert data["portfolio_yield"] is not None


# ---------------------------------------------------------------------------
# API-02 — Concentration
# ---------------------------------------------------------------------------


def test_concentration(client, re_loan_fixtures, auth_headers_admin):
    """API-02: Concentration breakdown returns property_type, state, MSA lists."""
    response = client.get("/api/re/concentration", headers=auth_headers_admin)
    assert response.status_code == 200
    data = response.json()
    assert len(data["property_type"]) > 0
    for item in data["property_type"]:
        assert "category" in item
        assert "total_upb" in item
        assert "pct_of_total" in item
    assert len(data["state"]) > 0
    assert len(data["top_10_exposures"]) > 0


# ---------------------------------------------------------------------------
# API-03 — Distributions
# ---------------------------------------------------------------------------


def test_distributions(client, re_loan_fixtures, auth_headers_admin):
    """API-03: Distribution histograms return at least one bucket with loan_count > 0."""
    response = client.get("/api/re/distributions", headers=auth_headers_admin)
    assert response.status_code == 200
    data = response.json()
    assert len(data["ltv_histogram"]) >= 1
    assert any(b["loan_count"] > 0 for b in data["ltv_histogram"])


# ---------------------------------------------------------------------------
# API-04 — Maturity profile
# ---------------------------------------------------------------------------


def test_maturity_profile(client, re_loan_fixtures, auth_headers_admin):
    """API-04: Maturity profile returns 200 with periods list (shape only — SQLite extract compat)."""
    response = client.get("/api/re/maturity-profile", headers=auth_headers_admin)
    assert response.status_code == 200
    data = response.json()
    assert "periods" in data
    assert isinstance(data["periods"], list)


# ---------------------------------------------------------------------------
# API-11 — Sales team scoping on KPIs
# ---------------------------------------------------------------------------


def test_sales_team_scoping_kpis(client, re_loan_fixtures, auth_headers_sales, auth_headers_admin):
    """API-11 (partial): sales_team JWT scopes KPI active_loan_count to team's loans only."""
    # Admin sees all 5 loans
    admin_resp = client.get("/api/re/kpis", headers=auth_headers_admin)
    assert admin_resp.status_code == 200
    assert admin_resp.json()["active_loan_count"] == 5

    # Sales user sees only loans assigned to their team (loans 1, 2, 5 = 3 loans)
    sales_resp = client.get("/api/re/kpis", headers=auth_headers_sales)
    assert sales_resp.status_code == 200
    assert sales_resp.json()["active_loan_count"] == 3


# ---------------------------------------------------------------------------
# Plan 02 stubs — API-05 through API-10 + full scoping test
# ---------------------------------------------------------------------------


@pytest.mark.skip(reason="Plan 02")
def test_loans_list(client, re_loan_fixtures, auth_headers_admin):
    """API-05: Paginated loan list."""
    ...


@pytest.mark.skip(reason="Plan 02")
def test_loans_filter(client, re_loan_fixtures, auth_headers_admin):
    """API-05: Filtered loan list."""
    ...


@pytest.mark.skip(reason="Plan 02")
def test_loan_detail(client, re_loan_fixtures, auth_headers_admin):
    """API-06: Loan detail with payment history."""
    ...


@pytest.mark.skip(reason="Plan 02")
def test_cashflow_performance(client, re_loan_fixtures, auth_headers_admin):
    """API-07: Cashflow performance by period."""
    ...


@pytest.mark.skip(reason="Plan 02")
def test_origination_pipeline(client, re_loan_fixtures, auth_headers_admin):
    """API-08: Origination pipeline and vintage analysis."""
    ...


@pytest.mark.skip(reason="Plan 02")
def test_market_context(client, re_loan_fixtures, auth_headers_admin):
    """API-09: Market context benchmark rates."""
    ...


@pytest.mark.skip(reason="Plan 02")
def test_sensitivity(client, re_loan_fixtures, auth_headers_admin):
    """API-10: Interest rate sensitivity scenarios."""
    ...


@pytest.mark.skip(reason="Plan 02")
def test_sales_team_scoping(client, re_loan_fixtures, auth_headers_sales, auth_headers_admin):
    """API-11 (full): sales_team scoping across all endpoints."""
    ...
