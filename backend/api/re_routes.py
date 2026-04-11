"""FastAPI router for the RE Portfolio API (Phase 18).

Endpoints:
  GET /api/re/kpis                  — API-01 Executive KPIs
  GET /api/re/concentration         — API-02 Concentration analysis
  GET /api/re/distributions         — API-03 Credit quality distributions
  GET /api/re/maturity-profile      — API-04 Maturity profile
  GET /api/re/loans                 — API-05 Paginated loan list
  GET /api/re/loans/{loan_id}       — API-06 Loan detail
  GET /api/re/cashflow-performance  — API-07 Cashflow performance
  GET /api/re/origination-pipeline  — API-08 Origination pipeline
  GET /api/re/market-context        — API-09 Market context
  GET /api/re/sensitivity           — API-10 Interest rate sensitivity

Security: every endpoint requires Depends(require_sales_team_access()).
  - SALES_TEAM users with no sales_team_id receive HTTP 403 (per T-18-06).
  - ANALYST and ADMIN roles pass through without data scoping.
Sales-team scoping is applied server-side from JWT claims only — never from query params (T-18-01).
"""

from decimal import Decimal
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session

from api.re_schemas import (
    FilterParams,
    KPIResponse,
    ConcentrationResponse,
    DistributionsResponse,
    MaturityProfileResponse,
    LoanListResponse,
    LoanDetailResponse,
    CashflowPerformanceResponse,
    OriginationPipelineResponse,
    MarketContextResponse,
    SensitivityResponse,
    DelinquencyWaterfallResponse,
    RiskRatingMigrationResponse,
    get_filter_params,
)
from auth.audit import log_data_access
from auth.security import require_sales_team_access
from db.connection import get_db
from db.models import RELoan, RELoanCashflow, UserRole, User

router = APIRouter(prefix="/api/re", tags=["re"])


# ---------------------------------------------------------------------------
# Shared filter helper
# ---------------------------------------------------------------------------


def build_re_filters(db: Session, params: FilterParams, user: User) -> list:
    """Build list of SQLAlchemy filter clauses for RE loan queries.

    Applies in this order:
    1. Sales-team scope (server-side from JWT — T-18-01).
    2. as_of_date: defaults to MAX(as_of_date) when not supplied (prevents dual-snapshot double-counting).
    3. All remaining FilterParams fields.

    Args:
        db: Active SQLAlchemy session (needed for MAX() subquery).
        params: Validated FilterParams from get_filter_params().
        user: Authenticated User from require_sales_team_access().

    Returns:
        List of SQLAlchemy column expressions ready for .filter(*filters).
    """
    filters: list = []

    # 1. Sales-team scope — always prepended before any client filter (T-18-01)
    if user.role == UserRole.SALES_TEAM and user.sales_team_id:
        filters.append(RELoan.sales_team_id == user.sales_team_id)

    # 2. as_of_date default: MAX(as_of_date) when not supplied
    if params.as_of_date is None:
        # Scope the MAX() to already-applied sales-team filter to avoid pulling dates outside scope
        latest = db.query(func.max(RELoan.as_of_date)).filter(*filters).scalar()
        if latest is not None:
            filters.append(RELoan.as_of_date == latest)
    else:
        filters.append(RELoan.as_of_date == params.as_of_date)

    # 3. Client-supplied filter fields
    if params.property_type is not None:
        filters.append(RELoan.property_type == params.property_type)

    if params.state is not None:
        filters.append(RELoan.state == params.state)

    if params.msa is not None:
        filters.append(RELoan.msa == params.msa)

    if params.loan_size_min is not None:
        filters.append(RELoan.upb >= params.loan_size_min)

    if params.loan_size_max is not None:
        filters.append(RELoan.upb <= params.loan_size_max)

    if params.risk_rating is not None:
        filters.append(RELoan.risk_rating == params.risk_rating)

    if params.vintage_year is not None:
        filters.append(RELoan.vintage_year == params.vintage_year)

    if params.borrower is not None:
        # Parameterized ilike — no raw string interpolation (T-18-02)
        filters.append(RELoan.borrower_name.ilike(f"%{params.borrower}%"))

    if params.rate_type is not None:
        filters.append(RELoan.rate_type == params.rate_type)

    return filters


# ---------------------------------------------------------------------------
# API-01 — GET /api/re/kpis
# ---------------------------------------------------------------------------


@router.get("/kpis", response_model=KPIResponse)
def get_kpis(
    params: FilterParams = Depends(get_filter_params),
    current_user: User = Depends(require_sales_team_access()),
    db: Session = Depends(get_db),
) -> KPIResponse:
    """Executive KPI summary: total UPB, WAC, WAM, WA-LTV, WA-DSCR, delinquency buckets.

    Aggregation uses a single SQL query with UPB-weighted formulas (D-07).
    Defaults to MAX(as_of_date) snapshot when as_of_date filter is not supplied.
    """
    log_data_access(current_user, "re_kpis")

    from sqlalchemy import case, cast, Numeric as SaNumeric

    filters = build_re_filters(db, params, current_user)

    result = (
        db.query(
            func.sum(RELoan.upb).label("total_upb"),
            func.count(RELoan.id).label("active_loan_count"),
            (func.sum(RELoan.interest_rate * RELoan.upb) / func.nullif(func.sum(RELoan.upb), 0)).label("wac"),
            (
                func.sum(cast(RELoan.wam_months, SaNumeric(10, 6)) * RELoan.upb) / func.nullif(func.sum(RELoan.upb), 0)
            ).label("wam"),
            (func.sum(RELoan.ltv * RELoan.upb) / func.nullif(func.sum(RELoan.upb), 0)).label("wa_ltv"),
            (func.sum(RELoan.dscr * RELoan.upb) / func.nullif(func.sum(RELoan.upb), 0)).label("wa_dscr"),
            func.sum(case((RELoan.days_past_due >= 30, RELoan.upb), else_=0)).label("delinquent_30_upb"),
            func.sum(case((RELoan.days_past_due >= 60, RELoan.upb), else_=0)).label("delinquent_60_upb"),
            func.sum(case((RELoan.days_past_due >= 90, RELoan.upb), else_=0)).label("delinquent_90_upb"),
        )
        .filter(*filters)
        .one()
    )

    if result.active_loan_count == 0 or result.total_upb is None:
        return KPIResponse(
            total_upb=Decimal("0"),
            wac=None,
            wam=None,
            wa_ltv=None,
            wa_dscr=None,
            active_loan_count=0,
            delinquent_30_upb=Decimal("0"),
            delinquent_60_upb=Decimal("0"),
            delinquent_90_upb=Decimal("0"),
            portfolio_yield=None,
        )

    total_upb = Decimal(str(result.total_upb)) if result.total_upb is not None else Decimal("0")
    wac = Decimal(str(result.wac)) if result.wac is not None else None
    wam = Decimal(str(result.wam)) if result.wam is not None else None
    wa_ltv = Decimal(str(result.wa_ltv)) if result.wa_ltv is not None else None
    wa_dscr = Decimal(str(result.wa_dscr)) if result.wa_dscr is not None else None
    d30 = Decimal(str(result.delinquent_30_upb)) if result.delinquent_30_upb is not None else Decimal("0")
    d60 = Decimal(str(result.delinquent_60_upb)) if result.delinquent_60_upb is not None else Decimal("0")
    d90 = Decimal(str(result.delinquent_90_upb)) if result.delinquent_90_upb is not None else Decimal("0")

    return KPIResponse(
        total_upb=total_upb,
        wac=wac,
        wam=wam,
        wa_ltv=wa_ltv,
        wa_dscr=wa_dscr,
        active_loan_count=result.active_loan_count,
        delinquent_30_upb=d30,
        delinquent_60_upb=d60,
        delinquent_90_upb=d90,
        portfolio_yield=wac,  # proxy metric for POC per RESEARCH.md A5
    )


# ---------------------------------------------------------------------------
# API-02 — GET /api/re/concentration
# ---------------------------------------------------------------------------


@router.get("/concentration", response_model=ConcentrationResponse)
def get_concentration(
    params: FilterParams = Depends(get_filter_params),
    current_user: User = Depends(require_sales_team_access()),
    db: Session = Depends(get_db),
) -> ConcentrationResponse:
    """Portfolio concentration analysis: property type, state, MSA, top exposures, limits."""
    from api.re_schemas import ConcentrationItem, TopExposure, ConcentrationLimit

    log_data_access(current_user, "re_concentration")

    filters = build_re_filters(db, params, current_user)

    # Total UPB for pct_of_total calculation
    total_upb_val = db.query(func.sum(RELoan.upb)).filter(*filters).scalar() or Decimal("0")
    total_upb = Decimal(str(total_upb_val))

    def _breakdown(group_col, order_desc: bool = True) -> list[ConcentrationItem]:
        rows = (
            db.query(group_col, func.count(RELoan.id), func.sum(RELoan.upb))
            .filter(*filters)
            .group_by(group_col)
            .order_by(func.sum(RELoan.upb).desc() if order_desc else group_col)
            .all()
        )
        items = []
        for row in rows:
            cat, cnt, upb_sum = row
            if cat is None:
                cat = "Unknown"
            upb_sum_d = Decimal(str(upb_sum)) if upb_sum is not None else Decimal("0")
            pct = (upb_sum_d / total_upb * 100) if total_upb > 0 else Decimal("0")
            items.append(
                ConcentrationItem(
                    category=str(cat),
                    loan_count=cnt,
                    total_upb=upb_sum_d,
                    pct_of_total=pct,
                )
            )
        return items

    property_type_breakdown = _breakdown(RELoan.property_type)
    state_breakdown = _breakdown(RELoan.state)
    msa_breakdown = _breakdown(RELoan.msa)

    # Top-10 exposures
    top_loans = db.query(RELoan).filter(*filters).order_by(RELoan.upb.desc()).limit(10).all()
    top_exposures = [
        TopExposure(
            loan_number=loan.loan_number,
            borrower_name=loan.borrower_name or "",
            upb=Decimal(str(loan.upb)) if loan.upb is not None else Decimal("0"),
            ltv=Decimal(str(loan.ltv)) if loan.ltv is not None else None,
            dscr=Decimal(str(loan.dscr)) if loan.dscr is not None else None,
            property_type=loan.property_type or "Unknown",
            state=loan.state or "Unknown",
        )
        for loan in top_loans
    ]

    # Concentration limits — hardcoded POC policy
    # TODO: POLICY-CONFIG — move to DB settings in production
    _LIMITS = {
        "state": Decimal("25"),
        "property_type": Decimal("40"),
        "borrower": Decimal("10"),
    }

    concentration_limits: list[ConcentrationLimit] = []

    # Top state pct
    if state_breakdown:
        top_state_pct = state_breakdown[0].pct_of_total
        lim = _LIMITS["state"]
        concentration_limits.append(
            ConcentrationLimit(
                category=f"state:{state_breakdown[0].category}",
                current_pct=top_state_pct,
                limit_pct=lim,
                proximity=top_state_pct / lim if lim > 0 else Decimal("0"),
            )
        )

    # Top property type pct
    if property_type_breakdown:
        top_pt_pct = property_type_breakdown[0].pct_of_total
        lim = _LIMITS["property_type"]
        concentration_limits.append(
            ConcentrationLimit(
                category=f"property_type:{property_type_breakdown[0].category}",
                current_pct=top_pt_pct,
                limit_pct=lim,
                proximity=top_pt_pct / lim if lim > 0 else Decimal("0"),
            )
        )

    # Top borrower pct
    borrower_rows = (
        db.query(RELoan.borrower_name, func.sum(RELoan.upb))
        .filter(*filters)
        .group_by(RELoan.borrower_name)
        .order_by(func.sum(RELoan.upb).desc())
        .first()
    )
    if borrower_rows and borrower_rows[1] is not None:
        top_borrower_upb = Decimal(str(borrower_rows[1]))
        top_borrower_pct = (top_borrower_upb / total_upb * 100) if total_upb > 0 else Decimal("0")
        lim = _LIMITS["borrower"]
        concentration_limits.append(
            ConcentrationLimit(
                category=f"borrower:{borrower_rows[0] or 'Unknown'}",
                current_pct=top_borrower_pct,
                limit_pct=lim,
                proximity=top_borrower_pct / lim if lim > 0 else Decimal("0"),
            )
        )

    return ConcentrationResponse(
        property_type=property_type_breakdown,
        state=state_breakdown,
        msa=msa_breakdown,
        top_10_exposures=top_exposures,
        concentration_limits=concentration_limits,
    )


# ---------------------------------------------------------------------------
# API-03 — GET /api/re/distributions
# ---------------------------------------------------------------------------


@router.get("/distributions", response_model=DistributionsResponse)
def get_distributions(
    params: FilterParams = Depends(get_filter_params),
    current_user: User = Depends(require_sales_team_access()),
    db: Session = Depends(get_db),
) -> DistributionsResponse:
    """Credit quality distribution histograms with CREDIT-01/02 color bands."""
    from api.re_schemas import HistogramBucket
    from sqlalchemy import case

    log_data_access(current_user, "re_distributions")

    filters = build_re_filters(db, params, current_user)

    # LTV histogram — CREDIT-01 color bands
    ltv_bucket = case(
        (RELoan.ltv < Decimal("0.65"), "<65%"),
        (RELoan.ltv <= Decimal("0.75"), "65-75%"),
        else_=">75%",
    )
    ltv_color_map = {"<65%": "green", "65-75%": "yellow", ">75%": "red"}
    ltv_rows = (
        db.query(ltv_bucket.label("bucket"), func.count(RELoan.id), func.sum(RELoan.upb))
        .filter(*filters)
        .filter(RELoan.ltv.isnot(None))
        .group_by(ltv_bucket)
        .all()
    )
    ltv_histogram = [
        HistogramBucket(
            bucket=row[0],
            loan_count=row[1],
            total_upb=Decimal(str(row[2])) if row[2] is not None else Decimal("0"),
            color=ltv_color_map.get(row[0], "grey"),
        )
        for row in ltv_rows
    ]

    # DSCR histogram — CREDIT-02 color bands
    dscr_bucket = case(
        (RELoan.dscr > Decimal("1.4"), ">1.4x"),
        (RELoan.dscr >= Decimal("1.0"), "1.0-1.4x"),
        else_="<1.0x",
    )
    dscr_color_map = {">1.4x": "green", "1.0-1.4x": "yellow", "<1.0x": "red"}
    dscr_rows = (
        db.query(dscr_bucket.label("bucket"), func.count(RELoan.id), func.sum(RELoan.upb))
        .filter(*filters)
        .filter(RELoan.dscr.isnot(None))
        .group_by(dscr_bucket)
        .all()
    )
    dscr_histogram = [
        HistogramBucket(
            bucket=row[0],
            loan_count=row[1],
            total_upb=Decimal(str(row[2])) if row[2] is not None else Decimal("0"),
            color=dscr_color_map.get(row[0], "grey"),
        )
        for row in dscr_rows
    ]

    # Loan size distribution
    size_bucket = case(
        (RELoan.upb < Decimal("1000000"), "<1M"),
        (RELoan.upb < Decimal("5000000"), "1-5M"),
        (RELoan.upb < Decimal("10000000"), "5-10M"),
        (RELoan.upb < Decimal("25000000"), "10-25M"),
        else_=">25M",
    )
    size_rows = (
        db.query(size_bucket.label("bucket"), func.count(RELoan.id), func.sum(RELoan.upb))
        .filter(*filters)
        .filter(RELoan.upb.isnot(None))
        .group_by(size_bucket)
        .all()
    )
    loan_size_distribution = [
        HistogramBucket(
            bucket=row[0],
            loan_count=row[1],
            total_upb=Decimal(str(row[2])) if row[2] is not None else Decimal("0"),
            color="grey",
        )
        for row in size_rows
    ]

    return DistributionsResponse(
        ltv_histogram=ltv_histogram,
        dscr_histogram=dscr_histogram,
        loan_size_distribution=loan_size_distribution,
    )


# ---------------------------------------------------------------------------
# API-04 — GET /api/re/maturity-profile
# ---------------------------------------------------------------------------


@router.get("/maturity-profile", response_model=MaturityProfileResponse)
def get_maturity_profile(
    params: FilterParams = Depends(get_filter_params),
    current_user: User = Depends(require_sales_team_access()),
    db: Session = Depends(get_db),
) -> MaturityProfileResponse:
    """Maturity profile: loan count and UPB grouped by maturity year and quarter."""
    from api.re_schemas import MaturityPeriod

    log_data_access(current_user, "re_maturity_profile")

    filters = build_re_filters(db, params, current_user)

    # Exclude loans with null maturity_date
    filters_with_date = filters + [RELoan.maturity_date.isnot(None)]

    year_col = func.extract("year", RELoan.maturity_date)
    quarter_col = func.extract("quarter", RELoan.maturity_date)

    rows = (
        db.query(year_col, quarter_col, func.count(RELoan.id), func.sum(RELoan.upb))
        .filter(*filters_with_date)
        .group_by(year_col, quarter_col)
        .order_by(year_col, quarter_col)
        .all()
    )

    periods = [
        MaturityPeriod(
            year=int(row[0]),
            quarter=int(row[1]),
            loan_count=row[2],
            total_upb=Decimal(str(row[3])) if row[3] is not None else Decimal("0"),
        )
        for row in rows
    ]

    return MaturityProfileResponse(periods=periods)


# ---------------------------------------------------------------------------
# API-05 — GET /api/re/loans
# ---------------------------------------------------------------------------

ALLOWED_SORT_FIELDS = {"upb", "ltv", "dscr", "interest_rate", "maturity_date", "origination_date", "risk_rating"}


@router.get("/loans", response_model=LoanListResponse)
def get_loans(
    params: FilterParams = Depends(get_filter_params),
    current_user: User = Depends(require_sales_team_access()),
    db: Session = Depends(get_db),
    page: int = 1,
    page_size: int = 50,
    sort_by: Optional[str] = None,
    sort_dir: str = "asc",
) -> LoanListResponse:
    """Paginated, filterable, sortable loan list (API-05 / D-05 / D-06).

    Security: sales_team scope applied via build_re_filters() (T-18-01).
    Sort whitelist prevents arbitrary column access (T-18-03).
    page_size bounded to prevent memory exhaustion (T-18-04).
    """
    log_data_access(current_user, "re_loans_list")

    # Validate sort_by against whitelist (T-18-03)
    if sort_by is not None and sort_by not in ALLOWED_SORT_FIELDS:
        raise HTTPException(status_code=400, detail="Invalid sort field")

    filters = build_re_filters(db, params, current_user)
    base_query = db.query(RELoan).filter(*filters)

    # Count before pagination (Pitfall 2 — count on full filtered set)
    total = base_query.with_entities(func.count(RELoan.id)).scalar() or 0

    # Apply sort
    if sort_by is not None:
        order_col = getattr(RELoan, sort_by, RELoan.id)
        base_query = base_query.order_by(order_col.desc() if sort_dir == "desc" else order_col.asc())
    else:
        base_query = base_query.order_by(RELoan.id.asc())

    # Apply pagination
    offset = (page - 1) * page_size
    loans = base_query.offset(offset).limit(page_size).all()

    from api.re_schemas import LoanSummary

    items = [LoanSummary.model_validate(loan) for loan in loans]
    return LoanListResponse(total=total, page=page, page_size=page_size, items=items)


# ---------------------------------------------------------------------------
# API-06 — GET /api/re/loans/{loan_id}
# ---------------------------------------------------------------------------


@router.get("/loans/{loan_id}", response_model=LoanDetailResponse)
def get_loan_detail(
    loan_id: int,
    params: FilterParams = Depends(get_filter_params),
    current_user: User = Depends(require_sales_team_access()),
    db: Session = Depends(get_db),
) -> LoanDetailResponse:
    """Single loan detail with aggregated payment history (API-06).

    Security: out-of-scope loan IDs return 404 identical to non-existent IDs
    — prevents enumeration of loan existence (T-18-01 / T-18-02).
    """
    from api.re_schemas import PaymentHistorySummary

    log_data_access(current_user, "re_loan_detail")

    filters = build_re_filters(db, params, current_user)
    loan = db.query(RELoan).filter(RELoan.id == loan_id, *filters).first()

    # Return 404 for both "not found" and "out of scope" — prevents enumeration (T-18-02)
    if loan is None:
        raise HTTPException(status_code=404, detail="Loan not found")

    # Aggregate payment history from linked cashflows
    cf_row = (
        db.query(
            func.sum(RELoanCashflow.scheduled_principal),
            func.sum(RELoanCashflow.actual_principal),
            func.sum(RELoanCashflow.scheduled_interest),
            func.sum(RELoanCashflow.actual_interest),
            func.count(RELoanCashflow.id),
        )
        .filter(RELoanCashflow.loan_id == loan_id)
        .one()
    )

    def _d(val) -> Optional[Decimal]:
        return Decimal(str(val)) if val is not None else None

    payment_history = PaymentHistorySummary(
        total_scheduled_principal=_d(cf_row[0]),
        total_actual_principal=_d(cf_row[1]),
        total_scheduled_interest=_d(cf_row[2]),
        total_actual_interest=_d(cf_row[3]),
        periods=cf_row[4] or 0,
    )

    return LoanDetailResponse(
        id=loan.id,
        loan_number=loan.loan_number,
        borrower_name=loan.borrower_name,
        upb=_d(loan.upb),
        interest_rate=_d(loan.interest_rate),
        ltv=_d(loan.ltv),
        dscr=_d(loan.dscr),
        property_type=loan.property_type,
        state=loan.state,
        risk_rating=loan.risk_rating,
        maturity_date=loan.maturity_date,
        origination_date=loan.origination_date,
        days_past_due=loan.days_past_due,
        delinquency_status=loan.delinquency_status,
        msa=loan.msa,
        original_balance=_d(loan.original_balance),
        wam_months=loan.wam_months,
        rate_type=loan.rate_type,
        prior_risk_rating=loan.prior_risk_rating,
        pipeline_stage=loan.pipeline_stage,
        vintage_year=loan.vintage_year,
        as_of_date=loan.as_of_date,
        payment_history=payment_history,
    )


# ---------------------------------------------------------------------------
# API-07 — GET /api/re/cashflow-performance
# ---------------------------------------------------------------------------


@router.get("/cashflow-performance", response_model=CashflowPerformanceResponse)
def get_cashflow_performance(
    params: FilterParams = Depends(get_filter_params),
    current_user: User = Depends(require_sales_team_access()),
    db: Session = Depends(get_db),
) -> CashflowPerformanceResponse:
    """Monthly P&I actual vs projected, NOI trend, gross yield, CPR (API-07).

    Security: cashflow join applies sales-team scope from build_re_filters() — sales_team
    users cannot see other teams' cashflow data (T-18-05).
    as_of_date is intentionally excluded: cashflows are historical time-series data tied to
    loan IDs from the T0 snapshot; filtering by MAX(as_of_date) would match only the T1
    snapshot (which has no linked cashflows) and return zero rows.
    Group-by period_date prevents Cartesian product explosion (Pitfall 6).
    """
    from api.re_schemas import CashflowPeriod

    log_data_access(current_user, "re_cashflow_performance")

    # Cashflow scope: sales-team filter only — no as_of_date (see docstring).
    # Use the latest snapshot UPB for yield/rate calculations.
    snapshot_filters = build_re_filters(db, params, current_user)

    # Sales-team scope only (first element when role == SALES_TEAM, else empty)
    cashflow_filters: list = []
    if current_user.role == UserRole.SALES_TEAM and current_user.sales_team_id:
        cashflow_filters.append(RELoan.sales_team_id == current_user.sales_team_id)
    if params.property_type is not None:
        cashflow_filters.append(RELoan.property_type == params.property_type)
    if params.state is not None:
        cashflow_filters.append(RELoan.state == params.state)
    if params.msa is not None:
        cashflow_filters.append(RELoan.msa == params.msa)
    if params.loan_size_min is not None:
        cashflow_filters.append(RELoan.upb >= params.loan_size_min)
    if params.loan_size_max is not None:
        cashflow_filters.append(RELoan.upb <= params.loan_size_max)
    if params.risk_rating is not None:
        cashflow_filters.append(RELoan.risk_rating == params.risk_rating)

    # Total UPB from the latest snapshot for yield/CPR denominators
    total_upb_val = db.query(func.sum(RELoan.upb)).filter(*snapshot_filters).scalar()
    total_upb = Decimal(str(total_upb_val)) if total_upb_val is not None else Decimal("0")

    # Join cashflows to loans to apply scoping filters (T-18-05)
    # Group by period_date — prevents row explosion (Pitfall 6)
    rows = (
        db.query(
            RELoanCashflow.period_date,
            func.sum(RELoanCashflow.scheduled_principal),
            func.sum(RELoanCashflow.actual_principal),
            func.sum(RELoanCashflow.scheduled_interest),
            func.sum(RELoanCashflow.actual_interest),
            func.sum(RELoanCashflow.noi),
        )
        .join(RELoan, RELoanCashflow.loan_id == RELoan.id)
        .filter(*cashflow_filters)
        .group_by(RELoanCashflow.period_date)
        .order_by(RELoanCashflow.period_date)
        .all()
    )

    def _d(val) -> Decimal:
        return Decimal(str(val)) if val is not None else Decimal("0")

    periods = []
    total_scheduled_sum = Decimal("0")
    total_actual_sum = Decimal("0")

    for row in rows:
        period_date, sched_p, act_p, sched_i, act_i, noi = row
        sched_p_d = _d(sched_p)
        act_p_d = _d(act_p)
        sched_i_d = _d(sched_i)
        act_i_d = _d(act_i)
        noi_d = _d(noi)

        # Gross yield: annualized actual interest / total UPB
        gross_yield = None
        if total_upb > 0:
            gross_yield = act_i_d / total_upb * Decimal("12")

        # CPR: SMM = (actual_principal - scheduled_principal) / total_upb
        cpr = None
        if total_upb > 0:
            smm = (act_p_d - sched_p_d) / total_upb
            if smm > Decimal("0"):
                # CPR = 1 - (1 - SMM)^12
                cpr = Decimal("1") - (Decimal("1") - smm) ** Decimal("12")
            else:
                cpr = Decimal("0")

        total_scheduled_sum += sched_i_d
        total_actual_sum += act_i_d

        periods.append(
            CashflowPeriod(
                period_date=period_date,
                scheduled_principal=sched_p_d,
                actual_principal=act_p_d,
                scheduled_interest=sched_i_d,
                actual_interest=act_i_d,
                total_noi=noi_d,
                gross_yield=gross_yield,
                cpr=cpr,
            )
        )

    # Net loss rate: (total_scheduled - total_actual) / total_upb — clamp to 0
    net_loss_rate = None
    if total_upb > 0:
        raw = (total_scheduled_sum - total_actual_sum) / total_upb
        net_loss_rate = max(raw, Decimal("0"))

    return CashflowPerformanceResponse(periods=periods, net_loss_rate=net_loss_rate)


# ---------------------------------------------------------------------------
# API-08 — GET /api/re/origination-pipeline
# ---------------------------------------------------------------------------

PIPELINE_STAGE_ORDER = {"underwriting": 1, "approved": 2, "closing": 3, "funded": 4}


@router.get("/origination-pipeline", response_model=OriginationPipelineResponse)
def get_origination_pipeline(
    params: FilterParams = Depends(get_filter_params),
    current_user: User = Depends(require_sales_team_access()),
    db: Session = Depends(get_db),
) -> OriginationPipelineResponse:
    """Origination by month, pipeline funnel, and vintage breakdown (API-08)."""
    from api.re_schemas import OriginationMonth, PipelineFunnelStage, VintageGroup

    log_data_access(current_user, "re_origination_pipeline")

    filters = build_re_filters(db, params, current_user)

    # 1. Origination by month — exclude NULL origination_date
    year_col = func.extract("year", RELoan.origination_date)
    month_col = func.extract("month", RELoan.origination_date)
    orig_rows = (
        db.query(year_col, month_col, func.count(RELoan.id), func.sum(RELoan.upb))
        .filter(*filters)
        .filter(RELoan.origination_date.isnot(None))
        .group_by(year_col, month_col)
        .order_by(year_col, month_col)
        .all()
    )
    origination_by_month = [
        OriginationMonth(
            year=int(row[0]),
            month=int(row[1]),
            loan_count=row[2],
            total_upb=Decimal(str(row[3])) if row[3] is not None else Decimal("0"),
        )
        for row in orig_rows
    ]

    # 2. Pipeline funnel — group by pipeline_stage, sort by stage order
    funnel_rows = (
        db.query(RELoan.pipeline_stage, func.count(RELoan.id), func.sum(RELoan.upb))
        .filter(*filters)
        .group_by(RELoan.pipeline_stage)
        .all()
    )
    pipeline_funnel = sorted(
        [
            PipelineFunnelStage(
                stage=row[0] or "unknown",
                loan_count=row[1],
                total_upb=Decimal(str(row[2])) if row[2] is not None else Decimal("0"),
            )
            for row in funnel_rows
        ],
        key=lambda s: PIPELINE_STAGE_ORDER.get(s.stage, 99),
    )

    # 3. Vintage breakdown — group by vintage_year
    vintage_rows = (
        db.query(
            RELoan.vintage_year,
            func.count(RELoan.id),
            func.sum(RELoan.upb),
            func.avg(RELoan.ltv),
            func.avg(RELoan.dscr),
        )
        .filter(*filters)
        .filter(RELoan.vintage_year.isnot(None))
        .group_by(RELoan.vintage_year)
        .order_by(RELoan.vintage_year)
        .all()
    )
    vintage_breakdown = [
        VintageGroup(
            vintage_year=row[0],
            loan_count=row[1],
            total_upb=Decimal(str(row[2])) if row[2] is not None else Decimal("0"),
            avg_ltv=Decimal(str(row[3])) if row[3] is not None else None,
            avg_dscr=Decimal(str(row[4])) if row[4] is not None else None,
        )
        for row in vintage_rows
    ]

    return OriginationPipelineResponse(
        origination_by_month=origination_by_month,
        pipeline_funnel=pipeline_funnel,
        vintage_breakdown=vintage_breakdown,
    )


# ---------------------------------------------------------------------------
# API-09 — GET /api/re/market-context
# ---------------------------------------------------------------------------


@router.get("/market-context", response_model=MarketContextResponse)
def get_market_context(
    current_user: User = Depends(require_sales_team_access()),
    db: Session = Depends(get_db),
) -> MarketContextResponse:
    """Market context: benchmark rates, cap rates, vacancy rates (API-09).

    Returns hardcoded stubs — no DB queries. Auth still required to prevent
    unauthenticated enumeration (T-18-07).
    """
    from api.re_schemas import MarketRate, CapRate

    log_data_access(current_user, "re_market_context")

    # TODO: LIVE-FEED-HOOK -- replace with FRED API call for 10Y Treasury rate
    ten_year_treasury = MarketRate(value=Decimal("4.25"), trend="flat", source="stub")

    # TODO: LIVE-FEED-HOOK -- replace with FRED API call for SOFR rate
    sofr = MarketRate(value=Decimal("5.33"), trend="declining", source="stub")

    # TODO: LIVE-FEED-HOOK -- replace with CRE index provider API for cap rates
    cap_rates = [
        CapRate(property_type="multifamily", value=Decimal("5.0"), source="stub"),
        CapRate(property_type="office", value=Decimal("7.5"), source="stub"),
        CapRate(property_type="industrial", value=Decimal("6.0"), source="stub"),
        CapRate(property_type="retail", value=Decimal("6.5"), source="stub"),
        CapRate(property_type="hotel", value=Decimal("8.0"), source="stub"),
    ]

    # TODO: LIVE-FEED-HOOK -- replace with CRE index provider API for vacancy rates
    vacancy_rates = [
        CapRate(property_type="multifamily", value=Decimal("5.5"), source="stub"),
        CapRate(property_type="office", value=Decimal("18.0"), source="stub"),
        CapRate(property_type="industrial", value=Decimal("4.0"), source="stub"),
        CapRate(property_type="retail", value=Decimal("8.0"), source="stub"),
        CapRate(property_type="hotel", value=Decimal("12.0"), source="stub"),
    ]

    return MarketContextResponse(
        ten_year_treasury=ten_year_treasury,
        sofr=sofr,
        cap_rates=cap_rates,
        vacancy_rates=vacancy_rates,
    )


# ---------------------------------------------------------------------------
# API-10 — GET /api/re/sensitivity
# ---------------------------------------------------------------------------


@router.get("/sensitivity", response_model=SensitivityResponse)
def get_sensitivity(
    params: FilterParams = Depends(get_filter_params),
    current_user: User = Depends(require_sales_team_access()),
    db: Session = Depends(get_db),
) -> SensitivityResponse:
    """Interest rate sensitivity analysis: 6 BPS scenarios -300 to +300 (API-10)."""
    from api.re_schemas import SensitivityScenario

    log_data_access(current_user, "re_sensitivity")

    filters = build_re_filters(db, params, current_user)

    result = (
        db.query(
            (func.sum(RELoan.interest_rate * RELoan.upb) / func.nullif(func.sum(RELoan.upb), 0)).label("base_wac"),
            func.sum(RELoan.upb).label("total_upb"),
        )
        .filter(*filters)
        .one()
    )

    base_wac_raw = result.base_wac
    total_upb_raw = result.total_upb

    # Handle empty portfolio
    if base_wac_raw is None or total_upb_raw is None:
        return SensitivityResponse(
            base_wac=Decimal("0"),
            total_upb=Decimal("0"),
            scenarios=[],
        )

    base_wac = Decimal(str(base_wac_raw))
    total_upb = Decimal(str(total_upb_raw))

    bps_changes = [-300, -200, -100, 100, 200, 300]
    scenarios = []
    for bps in bps_changes:
        bps_decimal = Decimal(str(bps)) / Decimal("10000")
        new_wac = base_wac + bps_decimal
        annual_interest_impact = total_upb * bps_decimal
        impact_pct = bps_decimal / base_wac * Decimal("100") if base_wac > 0 else Decimal("0")
        scenarios.append(
            SensitivityScenario(
                bps_change=bps,
                new_wac=new_wac,
                annual_interest_impact=annual_interest_impact,
                impact_pct=impact_pct,
            )
        )

    return SensitivityResponse(base_wac=base_wac, total_upb=total_upb, scenarios=scenarios)


# ---------------------------------------------------------------------------
# CREDIT-04 — GET /api/re/delinquency-waterfall
# ---------------------------------------------------------------------------


@router.get("/delinquency-waterfall", response_model=DelinquencyWaterfallResponse)
def get_delinquency_waterfall(
    params: FilterParams = Depends(get_filter_params),
    current_user: User = Depends(require_sales_team_access()),
    db: Session = Depends(get_db),
) -> DelinquencyWaterfallResponse:
    """Delinquency waterfall: exclusive DPD buckets ordered current->30->60->90->default (CREDIT-04)."""
    from sqlalchemy import case
    from api.re_schemas import DelinquencyBucket

    log_data_access(current_user, "re_delinquency_waterfall")

    filters = build_re_filters(db, params, current_user)

    bucket_expr = case(
        (RELoan.days_past_due == 0, "current"),
        (RELoan.days_past_due < 60, "30"),
        (RELoan.days_past_due < 90, "60"),
        (RELoan.days_past_due < 180, "90"),
        else_="default",
    )
    rows = (
        db.query(
            bucket_expr.label("bucket"),
            func.count(RELoan.id).label("loan_count"),
            func.sum(RELoan.upb).label("total_upb"),
        )
        .filter(*filters)
        .group_by(bucket_expr)
        .all()
    )

    ORDER = {"current": 0, "30": 1, "60": 2, "90": 3, "default": 4}
    buckets = sorted(
        [
            DelinquencyBucket(
                bucket=r.bucket,
                loan_count=r.loan_count,
                total_upb=Decimal(str(r.total_upb)) if r.total_upb else Decimal("0"),
            )
            for r in rows
        ],
        key=lambda b: ORDER.get(b.bucket, 99),
    )
    return DelinquencyWaterfallResponse(buckets=buckets)


# ---------------------------------------------------------------------------
# CREDIT-05 — GET /api/re/risk-rating-migration
# ---------------------------------------------------------------------------


@router.get("/risk-rating-migration", response_model=RiskRatingMigrationResponse)
def get_risk_rating_migration(
    params: FilterParams = Depends(get_filter_params),
    current_user: User = Depends(require_sales_team_access()),
    db: Session = Depends(get_db),
) -> RiskRatingMigrationResponse:
    """Risk rating migration matrix: prior vs current rating grouped counts (CREDIT-05)."""
    from api.re_schemas import MigrationCell

    log_data_access(current_user, "re_risk_rating_migration")

    filters = build_re_filters(db, params, current_user)

    rows = (
        db.query(
            RELoan.prior_risk_rating,
            RELoan.risk_rating,
            func.count(RELoan.id).label("loan_count"),
            func.sum(RELoan.upb).label("total_upb"),
        )
        .filter(*filters)
        .filter(RELoan.prior_risk_rating.isnot(None))
        .filter(RELoan.risk_rating.isnot(None))
        .group_by(RELoan.prior_risk_rating, RELoan.risk_rating)
        .all()
    )

    cells = [
        MigrationCell(
            prior_rating=r[0],
            current_rating=r[1],
            loan_count=r[2],
            total_upb=Decimal(str(r[3])) if r[3] else Decimal("0"),
        )
        for r in rows
    ]

    # Derive ordered distinct ratings from actual data (not hardcoded 1-5)
    all_ratings: set[str] = set()
    for c in cells:
        all_ratings.add(c.prior_rating)
        all_ratings.add(c.current_rating)
    try:
        ratings = sorted(all_ratings, key=lambda x: int(x))
    except ValueError:
        ratings = sorted(all_ratings)

    return RiskRatingMigrationResponse(cells=cells, ratings=ratings)
