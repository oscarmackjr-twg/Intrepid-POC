import { useQuery } from '@tanstack/react-query'
import axios from 'axios'
import {
  BarChart,
  Bar,
  Cell,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from 'recharts'
import { useReLoanFilters } from '../hooks/useReLoanFilters'
import { ChartCard } from '../components/re/ChartCard'
import type {
  DistributionsResponse,
  LoanListResponse,
  DelinquencyWaterfallResponse,
  RiskRatingMigrationResponse,
  SensitivityResponse,
  MigrationCell,
} from '../types/re'

const COLOR_MAP: Record<string, string> = {
  green:  '#059669',
  yellow: '#d97706',
  red:    '#dc2626',
  grey:   '#94a3b8',
}

const DELINQUENCY_COLORS: Record<string, string> = {
  current: '#059669',
  '30':    '#d97706',
  '60':    '#f97316',
  '90':    '#dc2626',
  default: '#7f1d1d',
}

const BUCKET_LABELS: Record<string, string> = {
  current: 'Current',
  '30':    '30 DPD',
  '60':    '60 DPD',
  '90':    '90 DPD',
  default: 'Default',
}

function getTrendArrow(current: string | null, prior: string | null): { symbol: string; color: string } {
  if (!current || !prior) return { symbol: '\u2014', color: 'text-[#94a3b8]' }
  const c = Number(current)
  const p = Number(prior)
  if (isNaN(c) || isNaN(p)) return { symbol: '\u2014', color: 'text-[#94a3b8]' }
  if (c > p) return { symbol: '\u2191', color: 'text-red-600' }    // deterioration
  if (c < p) return { symbol: '\u2193', color: 'text-green-600' }  // improvement
  return { symbol: '\u2014', color: 'text-[#94a3b8]' }             // unchanged
}

function getCellColor(prior: string, current: string): string {
  if (prior === current) return 'bg-gray-100'
  return Number(current) > Number(prior) ? 'bg-red-100' : 'bg-green-100'
}

function formatUPB(value: number | string): string {
  const v = Number(value)
  if (v >= 1_000_000) return `$${(v / 1_000_000).toFixed(1)}M`
  if (v >= 1_000) return `$${(v / 1_000).toFixed(0)}K`
  return `$${v.toFixed(0)}`
}

function formatPct(value: number | string): string {
  const v = Number(value)
  return `${v >= 0 ? '+' : ''}${v.toFixed(2)}%`
}

function formatRate(value: number | string): string {
  const v = Number(value)
  return `${(v * 100).toFixed(3)}%`
}

export default function ReCreditQualityPage() {
  const { filters } = useReLoanFilters()

  // 1. Distributions (LTV + DSCR histograms) — existing endpoint
  const distributions = useQuery({
    queryKey: ['re-distributions', filters],
    queryFn: async () => {
      const params = Object.fromEntries(
        Object.entries(filters).filter(([, v]) => v !== null && v !== '')
      )
      const { data } = await axios.get<DistributionsResponse>('/api/re/distributions', { params })
      return data
    },
  })

  // 2. Watchlist loans — fetch all loans WITHOUT global risk_rating filter, then client-side filter for 4/5
  // This ensures the watchlist always shows criticized loans even if the user has a different risk_rating in sidebar
  const watchlistLoans = useQuery({
    queryKey: ['re-loans-watchlist', filters],
    queryFn: async () => {
      const params = Object.fromEntries(
        Object.entries(filters).filter(([k, v]) => v !== null && v !== '' && k !== 'risk_rating')
      )
      const { data } = await axios.get<LoanListResponse>('/api/re/loans', {
        params: { ...params, page_size: 500 },
      })
      return data
    },
  })

  // 3. Delinquency waterfall — new endpoint from Plan 01
  const waterfall = useQuery({
    queryKey: ['re-delinquency-waterfall', filters],
    queryFn: async () => {
      const params = Object.fromEntries(
        Object.entries(filters).filter(([, v]) => v !== null && v !== '')
      )
      const { data } = await axios.get<DelinquencyWaterfallResponse>('/api/re/delinquency-waterfall', { params })
      return data
    },
  })

  // 4. Risk rating migration — new endpoint from Plan 01
  const migration = useQuery({
    queryKey: ['re-risk-rating-migration', filters],
    queryFn: async () => {
      const params = Object.fromEntries(
        Object.entries(filters).filter(([, v]) => v !== null && v !== '')
      )
      const { data } = await axios.get<RiskRatingMigrationResponse>('/api/re/risk-rating-migration', { params })
      return data
    },
  })

  // 5. Sensitivity — existing endpoint
  const sensitivity = useQuery({
    queryKey: ['re-sensitivity', filters],
    queryFn: async () => {
      const params = Object.fromEntries(
        Object.entries(filters).filter(([, v]) => v !== null && v !== '')
      )
      const { data } = await axios.get<SensitivityResponse>('/api/re/sensitivity', { params })
      return data
    },
  })

  // Derive watchlist from loans — risk_rating 4 or 5 (criticized)
  const criticizedLoans = (watchlistLoans.data?.items ?? []).filter(
    (l) => ['4', '5'].includes(l.risk_rating ?? '')
  )

  // Build migration matrix lookup
  const cellMap = new Map(
    (migration.data?.cells ?? []).map((c: MigrationCell) => [`${c.prior_rating}:${c.current_rating}`, c])
  )
  const ratings = migration.data?.ratings ?? []

  // Waterfall data with display labels
  const waterfallData = (waterfall.data?.buckets ?? []).map((b) => ({
    ...b,
    label: BUCKET_LABELS[b.bucket] ?? b.bucket,
  }))

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 gap-6">

      {/* Panel 1: LTV Histogram — CREDIT-01 */}
      <ChartCard
        title="LTV Distribution"
        isLoading={distributions.isLoading}
        isEmpty={!distributions.data?.ltv_histogram?.length}
      >
        <ResponsiveContainer width="100%" height={280}>
          <BarChart data={distributions.data?.ltv_histogram ?? []}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis dataKey="bucket" tick={{ fontSize: 11 }} />
            <YAxis />
            <Tooltip />
            <Bar dataKey="loan_count">
              {(distributions.data?.ltv_histogram ?? []).map((entry, index) => (
                <Cell key={`ltv-${index}`} fill={COLOR_MAP[entry.color] ?? '#94a3b8'} />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
        {/* TODO: UX-01 click-to-filter for LTV buckets — bucket labels don't map cleanly to filter params */}
      </ChartCard>

      {/* Panel 2: DSCR Histogram — CREDIT-02 */}
      <ChartCard
        title="DSCR Distribution"
        isLoading={distributions.isLoading}
        isEmpty={!distributions.data?.dscr_histogram?.length}
      >
        <ResponsiveContainer width="100%" height={280}>
          <BarChart data={distributions.data?.dscr_histogram ?? []}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis dataKey="bucket" tick={{ fontSize: 11 }} />
            <YAxis />
            <Tooltip />
            <Bar dataKey="loan_count">
              {(distributions.data?.dscr_histogram ?? []).map((entry, index) => (
                <Cell key={`dscr-${index}`} fill={COLOR_MAP[entry.color] ?? '#94a3b8'} />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
        {/* TODO: UX-01 click-to-filter for DSCR buckets — bucket labels don't map cleanly to filter params */}
      </ChartCard>

      {/* Panel 3: Watchlist Table — CREDIT-03 (full width) */}
      <ChartCard
        title="Watchlist — Criticized Loans"
        isLoading={watchlistLoans.isLoading}
        isEmpty={!criticizedLoans.length}
        colSpan="full"
      >
        <div className="overflow-x-auto">
          <table className="text-xs w-full border-collapse">
            <thead>
              <tr className="border-b border-gray-200">
                <th className="p-2 text-left text-[#475569]">Loan #</th>
                <th className="p-2 text-left text-[#475569]">Borrower</th>
                <th className="p-2 text-right text-[#475569]">UPB</th>
                <th className="p-2 text-right text-[#475569]">LTV</th>
                <th className="p-2 text-right text-[#475569]">DSCR</th>
                <th className="p-2 text-center text-[#475569]">Rating</th>
                <th className="p-2 text-center text-[#475569]">Trend</th>
                <th className="p-2 text-right text-[#475569]">DPD</th>
              </tr>
            </thead>
            <tbody>
              {criticizedLoans.map((loan) => {
                const trend = getTrendArrow(loan.risk_rating, loan.prior_risk_rating)
                return (
                  <tr key={loan.id} className="border-b border-gray-100 hover:bg-gray-50">
                    <td className="p-2 text-[#1a3868] font-medium">{loan.loan_number}</td>
                    <td className="p-2">{loan.borrower_name ?? '\u2014'}</td>
                    <td className="p-2 text-right">{loan.upb != null ? formatUPB(loan.upb) : '\u2014'}</td>
                    <td className="p-2 text-right">{loan.ltv != null ? `${(loan.ltv * 100).toFixed(1)}%` : '\u2014'}</td>
                    <td className="p-2 text-right">{loan.dscr != null ? `${loan.dscr.toFixed(2)}x` : '\u2014'}</td>
                    <td className="p-2 text-center font-medium">{loan.risk_rating ?? '\u2014'}</td>
                    <td className={`p-2 text-center text-lg ${trend.color}`}>{trend.symbol}</td>
                    <td className="p-2 text-right">{loan.days_past_due ?? 0}</td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        </div>
      </ChartCard>

      {/* Panel 4: Delinquency Waterfall — CREDIT-04 */}
      <ChartCard
        title="Delinquency Waterfall"
        isLoading={waterfall.isLoading}
        isEmpty={!waterfallData.length}
      >
        <ResponsiveContainer width="100%" height={280}>
          <BarChart data={waterfallData}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis dataKey="label" tick={{ fontSize: 11 }} />
            <YAxis />
            <Tooltip />
            <Bar dataKey="loan_count">
              {waterfallData.map((entry, i) => (
                <Cell key={`wf-${i}`} fill={DELINQUENCY_COLORS[entry.bucket] ?? '#94a3b8'} />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </ChartCard>

      {/* Panel 5: Risk Rating Migration Matrix — CREDIT-05 */}
      <ChartCard
        title="Risk Rating Migration"
        isLoading={migration.isLoading}
        isEmpty={!ratings.length}
      >
        <div className="overflow-x-auto">
          <table className="text-xs w-full border-collapse">
            <thead>
              <tr>
                <th className="p-1 text-left text-[#475569]">Prior \ Current</th>
                {ratings.map((r) => (
                  <th key={r} className="p-1 text-center text-[#475569]">{r}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {ratings.map((prior) => (
                <tr key={prior}>
                  <td className="p-1 font-medium text-[#1a3868]">{prior}</td>
                  {ratings.map((current) => {
                    const cell = cellMap.get(`${prior}:${current}`)
                    return (
                      <td
                        key={current}
                        className={`p-1 text-center ${getCellColor(prior, current)}`}
                        title={cell ? `${cell.loan_count} loans, ${formatUPB(cell.total_upb)}` : 'No loans'}
                      >
                        {cell?.loan_count ?? '\u2014'}
                      </td>
                    )
                  })}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </ChartCard>

      {/* Panel 6: Interest Rate Sensitivity Table — CREDIT-06 (full width) */}
      <ChartCard
        title="Interest Rate Sensitivity"
        isLoading={sensitivity.isLoading}
        isEmpty={!sensitivity.data?.scenarios?.length}
        colSpan="full"
      >
        <div className="overflow-x-auto">
          <table className="text-xs w-full border-collapse">
            <thead>
              <tr className="border-b border-gray-200">
                <th className="p-2 text-left text-[#475569]">Scenario</th>
                <th className="p-2 text-right text-[#475569]">New WAC</th>
                <th className="p-2 text-right text-[#475569]">Annual Interest Impact</th>
                <th className="p-2 text-right text-[#475569]">Impact %</th>
              </tr>
            </thead>
            <tbody>
              {(sensitivity.data?.scenarios ?? []).map((s) => {
                const isNegative = s.bps_change < 0
                return (
                  <tr key={s.bps_change} className="border-b border-gray-100">
                    <td className="p-2 font-medium text-[#1a3868]">
                      {s.bps_change > 0 ? '+' : ''}{s.bps_change} bps
                    </td>
                    <td className="p-2 text-right">{formatRate(s.new_wac)}</td>
                    <td className={`p-2 text-right ${isNegative ? 'text-red-600' : 'text-green-600'}`}>
                      {formatUPB(s.annual_interest_impact)}
                    </td>
                    <td className={`p-2 text-right ${isNegative ? 'text-red-600' : 'text-green-600'}`}>
                      {formatPct(s.impact_pct)}
                    </td>
                  </tr>
                )
              })}
            </tbody>
          </table>
          {sensitivity.data && (
            <p className="text-[10px] text-[#94a3b8] mt-2">
              Base WAC: {formatRate(sensitivity.data.base_wac)} | Total UPB: {formatUPB(sensitivity.data.total_upb)}
            </p>
          )}
        </div>
      </ChartCard>

    </div>
  )
}
