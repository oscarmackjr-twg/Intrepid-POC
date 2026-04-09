/**
 * TypeScript interfaces mirroring backend/api/re_schemas.py Pydantic models.
 *
 * Design notes (D-11, D-12, D-13):
 * - Types are hand-written; no OpenAPI codegen.
 * - Monetary and rate fields typed as `number` (FastAPI serializes Decimal to JSON number).
 * - Date fields typed as `string` (JSON serializes Python date as ISO string).
 * - Optional fields typed as `T | null`.
 * - ReLoanFilters: all fields are `string | null` except loan_size_min/loan_size_max
 *   which are `number | null` (URL numeric input returns a number).
 */

// ---------------------------------------------------------------------------
// Filter params — used by useReLoanFilters hook
// ---------------------------------------------------------------------------

export interface ReLoanFilters {
  as_of_date: string | null
  property_type: string | null
  state: string | null
  msa: string | null
  loan_size_min: number | null
  loan_size_max: number | null
  risk_rating: string | null
  vintage_year: string | null
  borrower: string | null
  rate_type: string | null
}

// ---------------------------------------------------------------------------
// KPI endpoint — API-01
// ---------------------------------------------------------------------------

export interface KPIResponse {
  total_upb: number
  wac: number | null
  wam: number | null
  wa_ltv: number | null
  wa_dscr: number | null
  active_loan_count: number
  delinquent_30_upb: number
  delinquent_60_upb: number
  delinquent_90_upb: number
  portfolio_yield: number | null
}

// ---------------------------------------------------------------------------
// Concentration endpoint — API-02
// ---------------------------------------------------------------------------

export interface ConcentrationItem {
  category: string
  loan_count: number
  total_upb: number
  pct_of_total: number
}

export interface TopExposure {
  loan_number: string
  borrower_name: string
  upb: number
  ltv: number | null
  dscr: number | null
  property_type: string
  state: string
}

export interface ConcentrationLimit {
  category: string
  current_pct: number
  limit_pct: number
  proximity: number
}

export interface ConcentrationResponse {
  property_type: ConcentrationItem[]
  state: ConcentrationItem[]
  msa: ConcentrationItem[]
  top_10_exposures: TopExposure[]
  concentration_limits: ConcentrationLimit[]
}

// ---------------------------------------------------------------------------
// Distributions endpoint — API-03
// ---------------------------------------------------------------------------

export interface HistogramBucket {
  bucket: string
  loan_count: number
  total_upb: number
  color: string
}

export interface DistributionsResponse {
  ltv_histogram: HistogramBucket[]
  dscr_histogram: HistogramBucket[]
  loan_size_distribution: HistogramBucket[]
}

// ---------------------------------------------------------------------------
// Maturity profile endpoint — API-04
// ---------------------------------------------------------------------------

export interface MaturityPeriod {
  year: number
  quarter: number
  loan_count: number
  total_upb: number
}

export interface MaturityProfileResponse {
  periods: MaturityPeriod[]
}

// ---------------------------------------------------------------------------
// Loan list / detail endpoints — API-05, API-06
// ---------------------------------------------------------------------------

export interface LoanSummary {
  id: number
  loan_number: string
  borrower_name: string | null
  upb: number | null
  interest_rate: number | null
  ltv: number | null
  dscr: number | null
  property_type: string | null
  state: string | null
  risk_rating: string | null
  maturity_date: string | null
  origination_date: string | null
  days_past_due: number | null
  delinquency_status: string | null
  prior_risk_rating: string | null
}

export interface LoanListResponse {
  total: number
  page: number
  page_size: number
  items: LoanSummary[]
}

export interface PaymentHistorySummary {
  total_scheduled_principal: number | null
  total_actual_principal: number | null
  total_scheduled_interest: number | null
  total_actual_interest: number | null
  periods: number
}

export interface LoanDetailResponse {
  id: number
  loan_number: string
  borrower_name: string | null
  upb: number | null
  interest_rate: number | null
  ltv: number | null
  dscr: number | null
  property_type: string | null
  state: string | null
  risk_rating: string | null
  maturity_date: string | null
  origination_date: string | null
  days_past_due: number | null
  delinquency_status: string | null
  msa: string | null
  original_balance: number | null
  wam_months: number | null
  rate_type: string | null
  prior_risk_rating: string | null
  pipeline_stage: string | null
  vintage_year: number | null
  as_of_date: string | null
  payment_history: PaymentHistorySummary | null
  appraisal_history: unknown[]
}

// ---------------------------------------------------------------------------
// Cashflow performance endpoint — API-07
// ---------------------------------------------------------------------------

export interface CashflowPeriod {
  period_date: string
  scheduled_principal: number
  actual_principal: number
  scheduled_interest: number
  actual_interest: number
  total_noi: number
  gross_yield: number | null
  cpr: number | null
}

export interface CashflowPerformanceResponse {
  periods: CashflowPeriod[]
  net_loss_rate: number | null
}

// ---------------------------------------------------------------------------
// Origination pipeline endpoint — API-08
// ---------------------------------------------------------------------------

export interface OriginationMonth {
  year: number
  month: number
  loan_count: number
  total_upb: number
}

export interface PipelineFunnelStage {
  stage: string
  loan_count: number
  total_upb: number
}

export interface VintageGroup {
  vintage_year: number
  loan_count: number
  total_upb: number
  avg_ltv: number | null
  avg_dscr: number | null
}

export interface OriginationPipelineResponse {
  origination_by_month: OriginationMonth[]
  pipeline_funnel: PipelineFunnelStage[]
  vintage_breakdown: VintageGroup[]
}

// ---------------------------------------------------------------------------
// Market context endpoint — API-09
// ---------------------------------------------------------------------------

export interface MarketRate {
  value: number
  trend: string
  source: string
}

export interface CapRate {
  property_type: string
  value: number
  source: string
}

export interface MarketContextResponse {
  ten_year_treasury: MarketRate
  sofr: MarketRate
  cap_rates: CapRate[]
  vacancy_rates: CapRate[]
}

// ---------------------------------------------------------------------------
// Sensitivity analysis endpoint — API-10
// ---------------------------------------------------------------------------

export interface SensitivityScenario {
  bps_change: number
  new_wac: number
  annual_interest_impact: number
  impact_pct: number
}

export interface SensitivityResponse {
  base_wac: number
  total_upb: number
  scenarios: SensitivityScenario[]
}

// ---------------------------------------------------------------------------
// Delinquency waterfall endpoint — CREDIT-04
// ---------------------------------------------------------------------------

export interface DelinquencyBucket {
  bucket: string
  loan_count: number
  total_upb: number
}

export interface DelinquencyWaterfallResponse {
  buckets: DelinquencyBucket[]
}

// ---------------------------------------------------------------------------
// Risk rating migration endpoint — CREDIT-05
// ---------------------------------------------------------------------------

export interface MigrationCell {
  prior_rating: string
  current_rating: string
  loan_count: number
  total_upb: number
}

export interface RiskRatingMigrationResponse {
  cells: MigrationCell[]
  ratings: string[]
}
