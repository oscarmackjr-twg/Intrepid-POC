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
            risk_rating="1",
            prior_risk_rating="1",
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
            risk_rating="2",
            prior_risk_rating="2",
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
            risk_rating="3",
            prior_risk_rating="3",
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
            risk_rating="1",
            prior_risk_rating="1",
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
            risk_rating="2",
            prior_risk_rating="2",
            rate_type="Floating",
            origination_date=date(2023, 11, 5),
            maturity_date=date(2031, 11, 5),
            days_past_due=0,
            delinquency_status="current",
            pipeline_stage="active",
            vintage_year=2023,
        ),
        # Loan 6: 60-bucket delinquent loan for delinquency waterfall test (CREDIT-04)
        RELoan(
            loan_number="RE-006",
            borrower_name="Borrower Zeta",
            sales_team_id=None,
            as_of_date=as_of,
            upb=Decimal("1000000.00"),
            original_balance=Decimal("1100000.00"),
            interest_rate=Decimal("0.070"),
            wam_months=120,
            ltv=Decimal("0.80"),
            dscr=Decimal("1.0"),
            property_type="Office",
            state="NY",
            msa="New York-Newark",
            risk_rating="4",
            prior_risk_rating="3",
            rate_type="Fixed",
            origination_date=date(2022, 6, 1),
            maturity_date=date(2027, 6, 1),
            days_past_due=65,
            delinquency_status="60dpd",
            pipeline_stage="active",
            vintage_year=2022,
        ),
        # Loan 7: default-bucket loan for delinquency waterfall test (CREDIT-04)
        RELoan(
            loan_number="RE-007",
            borrower_name="Borrower Eta",
            sales_team_id=None,
            as_of_date=as_of,
            upb=Decimal("500000.00"),
            original_balance=Decimal("600000.00"),
            interest_rate=Decimal("0.080"),
            wam_months=60,
            ltv=Decimal("0.90"),
            dscr=Decimal("0.80"),
            property_type="Retail",
            state="TX",
            msa="Dallas",
            risk_rating="5",
            prior_risk_rating="4",
            rate_type="Fixed",
            origination_date=date(2021, 3, 1),
            maturity_date=date(2026, 3, 1),
            days_past_due=200,
            delinquency_status="default",
            pipeline_stage="active",
            vintage_year=2021,
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
    assert data["active_loan_count"] == 7
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
    # Admin sees all 7 loans
    admin_resp = client.get("/api/re/kpis", headers=auth_headers_admin)
    assert admin_resp.status_code == 200
    assert admin_resp.json()["active_loan_count"] == 7

    # Sales user sees only loans assigned to their team (loans 1, 2, 5 = 3 loans)
    sales_resp = client.get("/api/re/kpis", headers=auth_headers_sales)
    assert sales_resp.status_code == 200
    assert sales_resp.json()["active_loan_count"] == 3


# ---------------------------------------------------------------------------
# API-05 — Paginated loan list
# ---------------------------------------------------------------------------


def test_loans_list(client, re_loan_fixtures, auth_headers_admin):
    """API-05: Paginated loan list returns correct envelope shape."""
    response = client.get("/api/re/loans", headers=auth_headers_admin)
    assert response.status_code == 200
    data = response.json()
    assert "total" in data
    assert "page" in data
    assert "page_size" in data
    assert "items" in data
    assert data["total"] >= 1
    assert isinstance(data["items"], list)
    assert len(data["items"]) >= 1


def test_loans_filter(client, re_loan_fixtures, auth_headers_admin):
    """API-05: Filtered loan list returns only matching property type."""
    response = client.get("/api/re/loans?property_type=Multifamily", headers=auth_headers_admin)
    assert response.status_code == 200
    data = response.json()
    assert data["total"] >= 1
    for item in data["items"]:
        assert item["property_type"] == "Multifamily"


def test_loans_sort_invalid(client, re_loan_fixtures, auth_headers_admin):
    """API-05: Invalid sort_by returns 400 (T-18-03 whitelist enforcement)."""
    response = client.get("/api/re/loans?sort_by=borrower_name__injected", headers=auth_headers_admin)
    assert response.status_code == 400


def test_loans_sort_valid(client, re_loan_fixtures, auth_headers_admin):
    """API-05: Valid sort_by=upb with sort_dir=desc returns 200."""
    response = client.get("/api/re/loans?sort_by=upb&sort_dir=desc", headers=auth_headers_admin)
    assert response.status_code == 200
    data = response.json()
    upbs = [Decimal(str(item["upb"])) for item in data["items"] if item["upb"] is not None]
    # Verify descending order
    assert upbs == sorted(upbs, reverse=True)


# ---------------------------------------------------------------------------
# API-06 — Loan detail
# ---------------------------------------------------------------------------


def test_loan_detail(client, re_loan_fixtures, auth_headers_admin):
    """API-06: Loan detail returns full shape including payment_history."""
    # First get a valid loan ID from the list endpoint
    list_resp = client.get("/api/re/loans", headers=auth_headers_admin)
    assert list_resp.status_code == 200
    loan_id = list_resp.json()["items"][0]["id"]

    response = client.get(f"/api/re/loans/{loan_id}", headers=auth_headers_admin)
    assert response.status_code == 200
    data = response.json()
    assert "loan_number" in data
    assert "payment_history" in data
    ph = data["payment_history"]
    assert "periods" in ph
    assert ph["periods"] >= 0


def test_loan_detail_not_found(client, re_loan_fixtures, auth_headers_admin):
    """API-06: Non-existent loan ID returns 404."""
    response = client.get("/api/re/loans/999999", headers=auth_headers_admin)
    assert response.status_code == 404


def test_loan_detail_out_of_scope_returns_404(client, re_loan_fixtures, auth_headers_sales):
    """API-06 / T-18-02: Out-of-scope loan returns 404, not 403 — prevents enumeration."""
    # Loans 3 and 4 have sales_team_id=None — not in the sales user's scope
    # Find their IDs via admin
    # We know from fixture: RE-003 and RE-004 have sales_team_id=None
    # Get all loan IDs via admin to find one outside scope
    # Use the fixture list — loans index 2 (RE-003) has sales_team_id=None
    # Get the ID from the fixture directly
    loan_no_team = re_loan_fixtures[2]  # RE-003, sales_team_id=None
    response = client.get(f"/api/re/loans/{loan_no_team.id}", headers=auth_headers_sales)
    assert response.status_code == 404


# ---------------------------------------------------------------------------
# API-07 — Cashflow performance
# ---------------------------------------------------------------------------


def test_cashflow_performance(client, re_loan_fixtures, auth_headers_admin):
    """API-07: Cashflow performance returns non-empty periods list."""
    response = client.get("/api/re/cashflow-performance", headers=auth_headers_admin)
    assert response.status_code == 200
    data = response.json()
    assert "periods" in data
    assert isinstance(data["periods"], list)
    assert len(data["periods"]) > 0
    # Check period shape
    period = data["periods"][0]
    assert "period_date" in period
    assert "scheduled_principal" in period
    assert "actual_principal" in period
    assert "scheduled_interest" in period
    assert "actual_interest" in period


# ---------------------------------------------------------------------------
# API-08 — Origination pipeline
# ---------------------------------------------------------------------------


def test_origination_pipeline(client, re_loan_fixtures, auth_headers_admin):
    """API-08: Origination pipeline returns all three sub-structures."""
    response = client.get("/api/re/origination-pipeline", headers=auth_headers_admin)
    assert response.status_code == 200
    data = response.json()
    assert "origination_by_month" in data
    assert "pipeline_funnel" in data
    assert "vintage_breakdown" in data
    assert isinstance(data["origination_by_month"], list)
    assert isinstance(data["pipeline_funnel"], list)
    assert isinstance(data["vintage_breakdown"], list)


# ---------------------------------------------------------------------------
# API-09 — Market context
# ---------------------------------------------------------------------------


def test_market_context(client, re_loan_fixtures, auth_headers_admin):
    """API-09: Market context returns stubbed values with source='stub'."""
    response = client.get("/api/re/market-context", headers=auth_headers_admin)
    assert response.status_code == 200
    data = response.json()
    assert "ten_year_treasury" in data
    assert "sofr" in data
    assert "cap_rates" in data
    assert "vacancy_rates" in data
    assert data["ten_year_treasury"]["source"] == "stub"
    assert data["sofr"]["source"] == "stub"
    assert len(data["cap_rates"]) > 0
    for rate in data["cap_rates"]:
        assert rate["source"] == "stub"


# ---------------------------------------------------------------------------
# API-10 — Sensitivity
# ---------------------------------------------------------------------------


def test_sensitivity(client, re_loan_fixtures, auth_headers_admin):
    """API-10: Sensitivity returns exactly 6 scenarios spanning -300 to +300 bps."""
    response = client.get("/api/re/sensitivity", headers=auth_headers_admin)
    assert response.status_code == 200
    data = response.json()
    assert "scenarios" in data
    assert len(data["scenarios"]) == 6
    bps_values = [s["bps_change"] for s in data["scenarios"]]
    assert -300 in bps_values
    assert 300 in bps_values
    # Each scenario has required fields
    for s in data["scenarios"]:
        assert "bps_change" in s
        assert "new_wac" in s
        assert "annual_interest_impact" in s


# ---------------------------------------------------------------------------
# API-11 — Full sales team scoping tests
# ---------------------------------------------------------------------------


def test_sales_team_scope_loans_list(client, re_loan_fixtures, auth_headers_sales, auth_headers_admin):
    """API-11: sales_team user sees only their team's loans in the list."""
    admin_resp = client.get("/api/re/loans", headers=auth_headers_admin)
    sales_resp = client.get("/api/re/loans", headers=auth_headers_sales)
    assert admin_resp.status_code == 200
    assert sales_resp.status_code == 200
    # Admin sees all 7; sales user sees only 3 (loans 1, 2, 5)
    assert admin_resp.json()["total"] == 7
    assert sales_resp.json()["total"] == 3


def test_sales_team_scope_loan_detail_own(client, re_loan_fixtures, auth_headers_sales):
    """API-11: sales_team user can access their own team's loan detail."""
    # Loan 0 (RE-001) belongs to the sales team
    own_loan = re_loan_fixtures[0]
    response = client.get(f"/api/re/loans/{own_loan.id}", headers=auth_headers_sales)
    assert response.status_code == 200


def test_sales_team_scope_loan_detail_other(client, re_loan_fixtures, auth_headers_sales):
    """API-11: sales_team user gets 404 for loan outside their team (T-18-02)."""
    # Loan 2 (RE-003) has sales_team_id=None
    other_loan = re_loan_fixtures[2]
    response = client.get(f"/api/re/loans/{other_loan.id}", headers=auth_headers_sales)
    assert response.status_code == 404


def test_sales_team_scope_concentration(client, re_loan_fixtures, auth_headers_sales, auth_headers_admin):
    """API-11: sales_team user sees scoped concentration (fewer loans than admin)."""
    admin_resp = client.get("/api/re/concentration", headers=auth_headers_admin)
    sales_resp = client.get("/api/re/concentration", headers=auth_headers_sales)
    assert admin_resp.status_code == 200
    assert sales_resp.status_code == 200
    admin_total = sum(item["loan_count"] for item in admin_resp.json()["property_type"])
    sales_total = sum(item["loan_count"] for item in sales_resp.json()["property_type"])
    assert sales_total < admin_total


def test_unauthenticated_rejected(client, re_loan_fixtures):
    """API-11: Unauthenticated request to any /api/re/* endpoint returns 401."""
    response = client.get("/api/re/kpis")
    assert response.status_code == 401


# ---------------------------------------------------------------------------
# CREDIT-04 — Delinquency waterfall
# ---------------------------------------------------------------------------


def test_delinquency_waterfall(client, re_loan_fixtures, auth_headers_admin):
    """CREDIT-04: Delinquency waterfall returns ordered exclusive buckets."""
    response = client.get("/api/re/delinquency-waterfall", headers=auth_headers_admin)
    assert response.status_code == 200
    data = response.json()
    assert "buckets" in data
    buckets = data["buckets"]
    assert len(buckets) >= 1
    # Verify structure
    for b in buckets:
        assert "bucket" in b
        assert "loan_count" in b
        assert "total_upb" in b
    # Verify ordering
    bucket_names = [b["bucket"] for b in buckets]
    expected_order = ["current", "30", "60", "default"]
    assert bucket_names == [n for n in expected_order if n in bucket_names]
    # At least current bucket has loans
    current_bucket = next((b for b in buckets if b["bucket"] == "current"), None)
    assert current_bucket is not None
    assert current_bucket["loan_count"] > 0


# ---------------------------------------------------------------------------
# CREDIT-05 — Risk rating migration
# ---------------------------------------------------------------------------


def test_risk_rating_migration(client, re_loan_fixtures, auth_headers_admin):
    """CREDIT-05: Migration matrix returns cells with prior/current rating pairs."""
    response = client.get("/api/re/risk-rating-migration", headers=auth_headers_admin)
    assert response.status_code == 200
    data = response.json()
    assert "cells" in data
    assert "ratings" in data
    assert isinstance(data["ratings"], list)
    assert len(data["ratings"]) >= 1
    for cell in data["cells"]:
        assert "prior_rating" in cell
        assert "current_rating" in cell
        assert "loan_count" in cell
        assert "total_upb" in cell
    # Total loan_count across cells should match count of loans with prior_risk_rating set
    total_migrated = sum(c["loan_count"] for c in data["cells"])
    assert total_migrated >= 1


# ---------------------------------------------------------------------------
# CREDIT-03 — LoanSummary includes prior_risk_rating
# ---------------------------------------------------------------------------


def test_loans_list_has_prior_risk_rating(client, re_loan_fixtures, auth_headers_admin):
    """CREDIT-03: LoanSummary items include prior_risk_rating for watchlist trend arrows."""
    response = client.get("/api/re/loans", headers=auth_headers_admin)
    assert response.status_code == 200
    items = response.json()["items"]
    assert len(items) >= 1
    # Every item must have the key (even if null)
    for item in items:
        assert "prior_risk_rating" in item


# ---------------------------------------------------------------------------
# CREDIT-01 — LTV distribution color bands
# ---------------------------------------------------------------------------


def test_distributions_ltv_color_bands(client, re_loan_fixtures, auth_headers_admin):
    """CREDIT-01: LTV histogram buckets each have a color field with valid value."""
    response = client.get("/api/re/distributions", headers=auth_headers_admin)
    assert response.status_code == 200
    ltv_hist = response.json()["ltv_histogram"]
    assert len(ltv_hist) >= 1
    valid_colors = {"green", "yellow", "red", "grey"}
    for bucket in ltv_hist:
        assert "color" in bucket
        assert bucket["color"] in valid_colors


# ---------------------------------------------------------------------------
# CREDIT-02 — DSCR distribution color bands
# ---------------------------------------------------------------------------


def test_distributions_dscr_color_bands(client, re_loan_fixtures, auth_headers_admin):
    """CREDIT-02: DSCR histogram buckets each have a color field with valid value."""
    response = client.get("/api/re/distributions", headers=auth_headers_admin)
    assert response.status_code == 200
    dscr_hist = response.json()["dscr_histogram"]
    assert len(dscr_hist) >= 1
    valid_colors = {"green", "yellow", "red", "grey"}
    for bucket in dscr_hist:
        assert "color" in bucket
        assert bucket["color"] in valid_colors


# ---------------------------------------------------------------------------
# WR-02 — CPR is None on principal shortfall
# ---------------------------------------------------------------------------


def test_cashflow_cpr_none_on_shortfall(client, test_db_session, auth_headers_admin, sample_sales_team):
    """WR-02: Period where actual_principal < scheduled_principal returns cpr=null (not 0)."""
    as_of = date(2026, 3, 1)
    loan = RELoan(
        loan_number="WR-02-LOAN",
        borrower_name="Shortfall Borrower",
        sales_team_id=sample_sales_team.id,
        as_of_date=as_of,
        upb=Decimal("1000000.00"),
        original_balance=Decimal("1100000.00"),
        interest_rate=Decimal("0.060"),
        wam_months=120,
        ltv=Decimal("0.65"),
        dscr=Decimal("1.3"),
        property_type="Multifamily",
        state="NY",
        msa="New York-Newark",
        risk_rating="2",
        prior_risk_rating="2",
        rate_type="Fixed",
        origination_date=date(2022, 1, 1),
        maturity_date=date(2032, 1, 1),
        days_past_due=0,
        delinquency_status="current",
        pipeline_stage="active",
        vintage_year=2022,
    )
    test_db_session.add(loan)
    test_db_session.flush()

    # Cashflow period where actual_principal < scheduled_principal (shortfall)
    cf = RELoanCashflow(
        loan_id=loan.id,
        period_date=date(2026, 4, 1),
        scheduled_principal=Decimal("20000.00"),
        actual_principal=Decimal("5000.00"),   # shortfall: actual < scheduled
        scheduled_interest=Decimal("5000.00"),
        actual_interest=Decimal("5000.00"),
        noi=Decimal("12000.00"),
    )
    test_db_session.add(cf)
    test_db_session.commit()

    response = client.get("/api/re/cashflow-performance", headers=auth_headers_admin)
    assert response.status_code == 200
    data = response.json()
    # Find the shortfall period (scheduled_principal > actual_principal)
    shortfall_period = next(
        (p for p in data["periods"]
         if p["scheduled_principal"] is not None
         and p["actual_principal"] is not None
         and float(p["scheduled_principal"]) > float(p["actual_principal"])),
        None,
    )
    assert shortfall_period is not None, "Expected at least one shortfall period"
    assert shortfall_period["cpr"] is None, "CPR must be null for a principal shortfall period"


# ---------------------------------------------------------------------------
# WR-01 — net_loss_rate includes principal shortfalls
# ---------------------------------------------------------------------------


def test_cashflow_net_loss_rate_includes_principal(client, test_db_session, auth_headers_admin, sample_sales_team):
    """WR-01: net_loss_rate reflects principal shortfall (was zero under the bug)."""
    as_of = date(2026, 3, 1)
    loan = RELoan(
        loan_number="WR-01-LOAN",
        borrower_name="NetLoss Borrower",
        sales_team_id=sample_sales_team.id,
        as_of_date=as_of,
        upb=Decimal("500000.00"),
        original_balance=Decimal("550000.00"),
        interest_rate=Decimal("0.055"),
        wam_months=60,
        ltv=Decimal("0.70"),
        dscr=Decimal("1.1"),
        property_type="Office",
        state="CA",
        msa="Los Angeles",
        risk_rating="3",
        prior_risk_rating="3",
        rate_type="Floating",
        origination_date=date(2021, 6, 1),
        maturity_date=date(2031, 6, 1),
        days_past_due=0,
        delinquency_status="current",
        pipeline_stage="active",
        vintage_year=2021,
    )
    test_db_session.add(loan)
    test_db_session.flush()

    # Cashflow with principal shortfall, no interest shortfall
    cf = RELoanCashflow(
        loan_id=loan.id,
        period_date=date(2026, 4, 1),
        scheduled_principal=Decimal("10000.00"),
        actual_principal=Decimal("0.00"),      # full principal shortfall
        scheduled_interest=Decimal("2500.00"),
        actual_interest=Decimal("2500.00"),    # no interest shortfall
        noi=Decimal("8000.00"),
    )
    test_db_session.add(cf)
    test_db_session.commit()

    response = client.get("/api/re/cashflow-performance", headers=auth_headers_admin)
    assert response.status_code == 200
    data = response.json()
    assert data["net_loss_rate"] is not None
    assert float(data["net_loss_rate"]) > 0, "net_loss_rate must be > 0 when principal is not collected"


# ---------------------------------------------------------------------------
# WR-03 — 90 DPD loan lands in "default" bucket, no "90" bucket in response
# ---------------------------------------------------------------------------


def test_delinquency_waterfall_90dpd_is_default(client, test_db_session, auth_headers_admin, sample_sales_team):
    """WR-03: Loan with days_past_due=90 must land in 'default', not '90' bucket."""
    as_of = date(2026, 3, 1)
    loan = RELoan(
        loan_number="WR-03-LOAN",
        borrower_name="90DPD Borrower",
        sales_team_id=sample_sales_team.id,
        as_of_date=as_of,
        upb=Decimal("750000.00"),
        original_balance=Decimal("800000.00"),
        interest_rate=Decimal("0.065"),
        wam_months=120,
        ltv=Decimal("0.75"),
        dscr=Decimal("1.0"),
        property_type="Retail",
        state="TX",
        msa="Dallas",
        risk_rating="4",
        prior_risk_rating="3",
        rate_type="Fixed",
        origination_date=date(2021, 1, 1),
        maturity_date=date(2031, 1, 1),
        days_past_due=90,
        delinquency_status="90dpd",
        pipeline_stage="active",
        vintage_year=2021,
    )
    test_db_session.add(loan)
    test_db_session.commit()

    response = client.get("/api/re/delinquency-waterfall", headers=auth_headers_admin)
    assert response.status_code == 200
    data = response.json()
    buckets = data["buckets"]
    bucket_names = [b["bucket"] for b in buckets]

    # No "90" bucket should appear in the response
    assert "90" not in bucket_names, "WR-03: '90' bucket must not exist — 90+ DPD maps to default"

    # The loan must appear in "default"
    default_bucket = next((b for b in buckets if b["bucket"] == "default"), None)
    assert default_bucket is not None, "Expected 'default' bucket in response"
    assert default_bucket["loan_count"] >= 1, "90 DPD loan must be counted in 'default' bucket"


# ---------------------------------------------------------------------------
# WR-04 — page_size > 200 is clamped to 200
# ---------------------------------------------------------------------------


def test_loans_page_size_cap(client, re_loan_fixtures, auth_headers_admin):
    """WR-04: Requesting page_size=9999 returns 200 with page_size clamped to <= 200."""
    response = client.get("/api/re/loans?page_size=9999", headers=auth_headers_admin)
    assert response.status_code == 200
    data = response.json()
    assert data["page_size"] <= 200, "page_size must be clamped to MAX_PAGE_SIZE=200"
