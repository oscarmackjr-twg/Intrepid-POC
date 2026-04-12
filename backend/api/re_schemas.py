"""Pydantic response models for the RE Portfolio API (Phase 18).

All monetary and rate fields use Decimal (per D-10 / PROJECT.md constraint — never float).
"""

from datetime import date
from decimal import Decimal
from typing import Annotated, Optional

from fastapi import Query
from pydantic import BaseModel, ConfigDict, Field
from pydantic.functional_serializers import PlainSerializer

# Decimal serialized as float in JSON (Pydantic v2 default is str, which breaks chart rendering).
# Used for all monetary/rate response fields. Internal calculations still use Decimal.
JsonDecimal = Annotated[Decimal, PlainSerializer(float, when_used="json")]


# ---------------------------------------------------------------------------
# Filter params
# ---------------------------------------------------------------------------


class FilterParams(BaseModel):
    """Query filter parameters shared across all /api/re/* endpoints."""

    model_config = ConfigDict(from_attributes=True)

    as_of_date: Optional[date] = None
    property_type: Optional[str] = None
    state: Optional[str] = None
    msa: Optional[str] = None
    loan_size_min: Optional[JsonDecimal] = None
    loan_size_max: Optional[JsonDecimal] = None
    risk_rating: Optional[str] = None
    vintage_year: Optional[int] = None
    borrower: Optional[str] = None
    rate_type: Optional[str] = None


def get_filter_params(
    as_of_date: Optional[date] = Query(None, description="Snapshot date; defaults to MAX(as_of_date)"),
    property_type: Optional[str] = Query(None, description="Property type filter (exact match)"),
    state: Optional[str] = Query(None, description="State 2-letter code (exact match)"),
    msa: Optional[str] = Query(None, description="MSA name (exact match)"),
    loan_size_min: Optional[JsonDecimal] = Query(None, description="Minimum UPB"),
    loan_size_max: Optional[JsonDecimal] = Query(None, description="Maximum UPB"),
    risk_rating: Optional[str] = Query(None, description="Risk rating (exact match)"),
    vintage_year: Optional[int] = Query(None, description="Vintage year (exact match)"),
    borrower: Optional[str] = Query(None, description="Borrower name (partial match, case-insensitive)"),
    rate_type: Optional[str] = Query(None, description="Rate type (exact match)"),
) -> FilterParams:
    """FastAPI Depends wrapper for FilterParams.

    Required because FastAPI cannot inject a BaseModel directly from query params (Pitfall 1).
    """
    return FilterParams(
        as_of_date=as_of_date,
        property_type=property_type,
        state=state,
        msa=msa,
        loan_size_min=loan_size_min,
        loan_size_max=loan_size_max,
        risk_rating=risk_rating,
        vintage_year=vintage_year,
        borrower=borrower,
        rate_type=rate_type,
    )


# ---------------------------------------------------------------------------
# KPI endpoint — API-01
# ---------------------------------------------------------------------------


class KPIResponse(BaseModel):
    """Portfolio KPI summary for the Executive Summary panel."""

    model_config = ConfigDict(from_attributes=True)

    total_upb: JsonDecimal
    wac: Optional[JsonDecimal]
    wam: Optional[JsonDecimal]
    wa_ltv: Optional[JsonDecimal]
    wa_dscr: Optional[JsonDecimal]
    active_loan_count: int
    delinquent_30_upb: JsonDecimal
    delinquent_60_upb: JsonDecimal
    delinquent_90_upb: JsonDecimal
    portfolio_yield: Optional[JsonDecimal]


# ---------------------------------------------------------------------------
# Concentration endpoint — API-02
# ---------------------------------------------------------------------------


class ConcentrationItem(BaseModel):
    """Single breakdown item within a concentration group."""

    model_config = ConfigDict(from_attributes=True)

    category: str
    loan_count: int
    total_upb: JsonDecimal
    pct_of_total: JsonDecimal


class TopExposure(BaseModel):
    """Top single-loan exposure for concentration risk monitoring."""

    model_config = ConfigDict(from_attributes=True)

    loan_number: str
    borrower_name: str
    upb: JsonDecimal
    ltv: Optional[JsonDecimal]
    dscr: Optional[JsonDecimal]
    property_type: str
    state: str


class ConcentrationLimit(BaseModel):
    """Concentration limit vs current exposure.

    proximity = current_pct / limit_pct (values > 1.0 indicate breach).
    """

    model_config = ConfigDict(from_attributes=True)

    category: str
    current_pct: JsonDecimal
    limit_pct: JsonDecimal
    proximity: JsonDecimal


class ConcentrationResponse(BaseModel):
    """Portfolio concentration response — API-02."""

    model_config = ConfigDict(from_attributes=True)

    property_type: list[ConcentrationItem]
    state: list[ConcentrationItem]
    msa: list[ConcentrationItem]
    top_10_exposures: list[TopExposure]
    concentration_limits: list[ConcentrationLimit]


# ---------------------------------------------------------------------------
# Distributions endpoint — API-03
# ---------------------------------------------------------------------------


class HistogramBucket(BaseModel):
    """Single histogram bucket with CREDIT-01/02 color bands."""

    model_config = ConfigDict(from_attributes=True)

    bucket: str
    loan_count: int
    total_upb: JsonDecimal
    color: str


class DistributionsResponse(BaseModel):
    """Credit quality distribution histograms — API-03."""

    model_config = ConfigDict(from_attributes=True)

    ltv_histogram: list[HistogramBucket]
    dscr_histogram: list[HistogramBucket]
    loan_size_distribution: list[HistogramBucket]


# ---------------------------------------------------------------------------
# Maturity profile endpoint — API-04
# ---------------------------------------------------------------------------


class MaturityPeriod(BaseModel):
    """Single maturity period (year + quarter bucket)."""

    model_config = ConfigDict(from_attributes=True)

    year: int
    quarter: int
    loan_count: int
    total_upb: JsonDecimal


class MaturityProfileResponse(BaseModel):
    """Maturity profile response — API-04."""

    model_config = ConfigDict(from_attributes=True)

    periods: list[MaturityPeriod]


# ---------------------------------------------------------------------------
# Loan list / detail endpoints — API-05, API-06
# ---------------------------------------------------------------------------


class LoanSummary(BaseModel):
    """Loan list item — mirrors key RELoan fields for paginated list view."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    loan_number: str
    borrower_name: Optional[str]
    upb: Optional[JsonDecimal]
    interest_rate: Optional[JsonDecimal]
    ltv: Optional[JsonDecimal]
    dscr: Optional[JsonDecimal]
    property_type: Optional[str]
    state: Optional[str]
    risk_rating: Optional[str]
    prior_risk_rating: Optional[str] = None
    maturity_date: Optional[date]
    origination_date: Optional[date]
    days_past_due: Optional[int]
    delinquency_status: Optional[str]


class LoanListResponse(BaseModel):
    """Paginated loan list response — API-05 (D-05/D-06)."""

    model_config = ConfigDict(from_attributes=True)

    total: int
    page: int
    page_size: int
    items: list[LoanSummary]


class PaymentHistorySummary(BaseModel):
    """Aggregated payment history summary for loan detail."""

    model_config = ConfigDict(from_attributes=True)

    total_scheduled_principal: Optional[JsonDecimal]
    total_actual_principal: Optional[JsonDecimal]
    total_scheduled_interest: Optional[JsonDecimal]
    total_actual_interest: Optional[JsonDecimal]
    periods: int


class LoanDetailResponse(BaseModel):
    """Full loan detail response — API-06.

    Extends LoanSummary with additional fields and payment history.
    """

    model_config = ConfigDict(from_attributes=True)

    # LoanSummary fields
    id: int
    loan_number: str
    borrower_name: Optional[str]
    upb: Optional[JsonDecimal]
    interest_rate: Optional[JsonDecimal]
    ltv: Optional[JsonDecimal]
    dscr: Optional[JsonDecimal]
    property_type: Optional[str]
    state: Optional[str]
    risk_rating: Optional[str]
    maturity_date: Optional[date]
    origination_date: Optional[date]
    days_past_due: Optional[int]
    delinquency_status: Optional[str]

    # Extended fields
    msa: Optional[str]
    original_balance: Optional[JsonDecimal]
    wam_months: Optional[int]
    rate_type: Optional[str]
    prior_risk_rating: Optional[str]
    pipeline_stage: Optional[str]
    vintage_year: Optional[int]
    as_of_date: Optional[date]

    # Related data
    payment_history: Optional[PaymentHistorySummary]
    # TODO: APPRAISAL-HOOK — RELoan model has no appraisal columns;
    #       stub as empty list for Phase 18 POC.
    appraisal_history: list = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Cashflow performance endpoint — API-07
# ---------------------------------------------------------------------------


class CashflowPeriod(BaseModel):
    """Monthly cashflow performance period."""

    model_config = ConfigDict(from_attributes=True)

    period_date: date
    scheduled_principal: JsonDecimal
    actual_principal: JsonDecimal
    scheduled_interest: JsonDecimal
    actual_interest: JsonDecimal
    total_noi: JsonDecimal
    gross_yield: Optional[JsonDecimal]
    cpr: Optional[JsonDecimal]


class CashflowPerformanceResponse(BaseModel):
    """Cashflow performance response — API-07."""

    model_config = ConfigDict(from_attributes=True)

    periods: list[CashflowPeriod]
    net_loss_rate: Optional[JsonDecimal]


# ---------------------------------------------------------------------------
# Origination pipeline endpoint — API-08
# ---------------------------------------------------------------------------


class OriginationMonth(BaseModel):
    """Monthly origination volume."""

    model_config = ConfigDict(from_attributes=True)

    year: int
    month: int
    property_type: str
    loan_count: int
    total_upb: JsonDecimal


class PipelineFunnelStage(BaseModel):
    """Pipeline funnel stage volume."""

    model_config = ConfigDict(from_attributes=True)

    stage: str
    loan_count: int
    total_upb: JsonDecimal


class VintageGroup(BaseModel):
    """Vintage year group with average credit metrics."""

    model_config = ConfigDict(from_attributes=True)

    vintage_year: int
    loan_count: int
    total_upb: JsonDecimal
    avg_ltv: Optional[JsonDecimal]
    avg_dscr: Optional[JsonDecimal]
    avg_rate: Optional[JsonDecimal]


class OriginationPipelineResponse(BaseModel):
    """Origination pipeline response — API-08."""

    model_config = ConfigDict(from_attributes=True)

    origination_by_month: list[OriginationMonth]
    pipeline_funnel: list[PipelineFunnelStage]
    vintage_breakdown: list[VintageGroup]


# ---------------------------------------------------------------------------
# Market context endpoint — API-09
# ---------------------------------------------------------------------------


class MarketRate(BaseModel):
    """Single market rate indicator."""

    model_config = ConfigDict(from_attributes=True)

    value: JsonDecimal
    trend: str
    source: str


class CapRate(BaseModel):
    """Cap rate or vacancy rate by property type."""

    model_config = ConfigDict(from_attributes=True)

    property_type: str
    value: JsonDecimal
    source: str


class MarketContextResponse(BaseModel):
    """Market context response — API-09."""

    model_config = ConfigDict(from_attributes=True)

    ten_year_treasury: MarketRate
    sofr: MarketRate
    cap_rates: list[CapRate]
    vacancy_rates: list[CapRate]


# ---------------------------------------------------------------------------
# Sensitivity analysis endpoint — API-10
# ---------------------------------------------------------------------------


class SensitivityScenario(BaseModel):
    """Single rate sensitivity scenario."""

    model_config = ConfigDict(from_attributes=True)

    bps_change: int
    new_wac: JsonDecimal
    annual_interest_impact: JsonDecimal
    impact_pct: JsonDecimal


class SensitivityResponse(BaseModel):
    """Interest rate sensitivity analysis response — API-10."""

    model_config = ConfigDict(from_attributes=True)

    base_wac: JsonDecimal
    total_upb: JsonDecimal
    scenarios: list[SensitivityScenario]


# ---------------------------------------------------------------------------
# Delinquency waterfall endpoint — CREDIT-04
# ---------------------------------------------------------------------------


class DelinquencyBucket(BaseModel):
    """Single delinquency bucket for waterfall display."""

    model_config = ConfigDict(from_attributes=True)

    bucket: str
    loan_count: int
    total_upb: JsonDecimal


class DelinquencyWaterfallResponse(BaseModel):
    """Delinquency waterfall response — CREDIT-04."""

    model_config = ConfigDict(from_attributes=True)

    buckets: list[DelinquencyBucket]


# ---------------------------------------------------------------------------
# Risk rating migration endpoint — CREDIT-05
# ---------------------------------------------------------------------------


class MigrationCell(BaseModel):
    """Single cell in the risk rating migration matrix."""

    model_config = ConfigDict(from_attributes=True)

    prior_rating: str
    current_rating: str
    loan_count: int
    total_upb: JsonDecimal


class RiskRatingMigrationResponse(BaseModel):
    """Risk rating migration matrix response — CREDIT-05."""

    model_config = ConfigDict(from_attributes=True)

    cells: list[MigrationCell]
    ratings: list[str]
