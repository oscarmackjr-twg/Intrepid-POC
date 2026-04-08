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
    get_filter_params,
)
from auth.audit import log_data_access
from auth.security import require_sales_team_access
from db.connection import get_db
from db.models import RELoan, UserRole, User

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

    result = db.query(
        func.sum(RELoan.upb).label("total_upb"),
        func.count(RELoan.id).label("active_loan_count"),
        (
            func.sum(RELoan.interest_rate * RELoan.upb)
            / func.nullif(func.sum(RELoan.upb), 0)
        ).label("wac"),
        (
            func.sum(cast(RELoan.wam_months, SaNumeric(10, 6)) * RELoan.upb)
            / func.nullif(func.sum(RELoan.upb), 0)
        ).label("wam"),
        (
            func.sum(RELoan.ltv * RELoan.upb)
            / func.nullif(func.sum(RELoan.upb), 0)
        ).label("wa_ltv"),
        (
            func.sum(RELoan.dscr * RELoan.upb)
            / func.nullif(func.sum(RELoan.upb), 0)
        ).label("wa_dscr"),
        func.sum(
            case((RELoan.days_past_due >= 30, RELoan.upb), else_=0)
        ).label("delinquent_30_upb"),
        func.sum(
            case((RELoan.days_past_due >= 60, RELoan.upb), else_=0)
        ).label("delinquent_60_upb"),
        func.sum(
            case((RELoan.days_past_due >= 90, RELoan.upb), else_=0)
        ).label("delinquent_90_upb"),
    ).filter(*filters).one()

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
    top_loans = (
        db.query(RELoan)
        .filter(*filters)
        .order_by(RELoan.upb.desc())
        .limit(10)
        .all()
    )
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
    from sqlalchemy import case, cast, String as SaString

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
# API-05 — GET /api/re/loans  (stub — Plan 02)
# ---------------------------------------------------------------------------


@router.get("/loans", response_model=LoanListResponse)
def get_loans(
    params: FilterParams = Depends(get_filter_params),
    current_user: User = Depends(require_sales_team_access()),
    db: Session = Depends(get_db),
) -> LoanListResponse:
    """Paginated loan list. (Implementation: Plan 02)"""
    raise HTTPException(status_code=501, detail="Not implemented")


# ---------------------------------------------------------------------------
# API-06 — GET /api/re/loans/{loan_id}  (stub — Plan 02)
# ---------------------------------------------------------------------------


@router.get("/loans/{loan_id}", response_model=LoanDetailResponse)
def get_loan_detail(
    loan_id: int,
    current_user: User = Depends(require_sales_team_access()),
    db: Session = Depends(get_db),
) -> LoanDetailResponse:
    """Loan detail with payment history. (Implementation: Plan 02)"""
    raise HTTPException(status_code=501, detail="Not implemented")


# ---------------------------------------------------------------------------
# API-07 — GET /api/re/cashflow-performance  (stub — Plan 02)
# ---------------------------------------------------------------------------


@router.get("/cashflow-performance", response_model=CashflowPerformanceResponse)
def get_cashflow_performance(
    params: FilterParams = Depends(get_filter_params),
    current_user: User = Depends(require_sales_team_access()),
    db: Session = Depends(get_db),
) -> CashflowPerformanceResponse:
    """Cashflow performance by period. (Implementation: Plan 02)"""
    raise HTTPException(status_code=501, detail="Not implemented")


# ---------------------------------------------------------------------------
# API-08 — GET /api/re/origination-pipeline  (stub — Plan 02)
# ---------------------------------------------------------------------------


@router.get("/origination-pipeline", response_model=OriginationPipelineResponse)
def get_origination_pipeline(
    params: FilterParams = Depends(get_filter_params),
    current_user: User = Depends(require_sales_team_access()),
    db: Session = Depends(get_db),
) -> OriginationPipelineResponse:
    """Origination pipeline and vintage analysis. (Implementation: Plan 02)"""
    raise HTTPException(status_code=501, detail="Not implemented")


# ---------------------------------------------------------------------------
# API-09 — GET /api/re/market-context  (stub — Plan 02)
# ---------------------------------------------------------------------------


@router.get("/market-context", response_model=MarketContextResponse)
def get_market_context(
    current_user: User = Depends(require_sales_team_access()),
    db: Session = Depends(get_db),
) -> MarketContextResponse:
    """Market context: benchmark rates, cap rates, vacancy rates. (Implementation: Plan 02)"""
    raise HTTPException(status_code=501, detail="Not implemented")


# ---------------------------------------------------------------------------
# API-10 — GET /api/re/sensitivity  (stub — Plan 02)
# ---------------------------------------------------------------------------


@router.get("/sensitivity", response_model=SensitivityResponse)
def get_sensitivity(
    params: FilterParams = Depends(get_filter_params),
    current_user: User = Depends(require_sales_team_access()),
    db: Session = Depends(get_db),
) -> SensitivityResponse:
    """Interest rate sensitivity analysis. (Implementation: Plan 02)"""
    raise HTTPException(status_code=501, detail="Not implemented")
