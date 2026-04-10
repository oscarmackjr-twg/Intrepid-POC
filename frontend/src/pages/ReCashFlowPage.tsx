import { useQuery } from '@tanstack/react-query'
import axios from 'axios'
import {
  LineChart,
  Line,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from 'recharts'
import { useReLoanFilters } from '../hooks/useReLoanFilters'
import { ChartCard } from '../components/re/ChartCard'
import type {
  CashflowPerformanceResponse,
  MarketContextResponse,
} from '../types/re'

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

// Silence unused-variable warnings for formatPct/formatRate used in future extension
void formatPct
void formatRate

export default function ReCashFlowPage() {
  const { filters } = useReLoanFilters()

  const cashflow = useQuery({
    queryKey: ['re-cashflow-performance', filters],
    queryFn: async () => {
      const params = Object.fromEntries(
        Object.entries(filters).filter(([, v]) => v !== null && v !== '')
      )
      const { data } = await axios.get<CashflowPerformanceResponse>(
        '/api/re/cashflow-performance', { params }
      )
      return data
    },
  })

  const market = useQuery({
    queryKey: ['re-market-context'],  // no filters — market rates are global
    queryFn: async () => {
      const { data } = await axios.get<MarketContextResponse>('/api/re/market-context')
      return data
    },
  })

  const periods = cashflow.data?.periods ?? []

  // P&I chart data: compute projected_pi and actual_pi per period
  const piData = periods.map((p) => ({
    period_date: p.period_date,
    projected_pi: Number(p.scheduled_principal) + Number(p.scheduled_interest),
    actual_pi: Number(p.actual_principal) + Number(p.actual_interest),
    variance:
      Number(p.actual_principal) +
      Number(p.actual_interest) -
      (Number(p.scheduled_principal) + Number(p.scheduled_interest)),
  }))

  // NOI bar chart data
  const noiData = periods.map((p) => ({
    period_date: p.period_date,
    total_noi: Number(p.total_noi),
  }))

  // CPR trend data
  const cprData = periods.map((p) => ({
    period_date: p.period_date,
    cpr_pct: p.cpr != null ? Number(p.cpr) * 100 : 0,
  }))

  // Yield analysis (from last period + market rates)
  const lastPeriod = periods[periods.length - 1]
  const grossYield = lastPeriod?.gross_yield != null ? Number(lastPeriod.gross_yield) : null
  const netLossRate =
    cashflow.data?.net_loss_rate != null ? Number(cashflow.data.net_loss_rate) : 0
  const netYield = grossYield != null ? grossYield - netLossRate : null
  const sofrValue =
    market.data?.sofr?.value != null ? Number(market.data.sofr.value) : null
  const treasuryValue =
    market.data?.ten_year_treasury?.value != null
      ? Number(market.data.ten_year_treasury.value)
      : null
  const sofrSpread =
    grossYield != null && sofrValue != null ? grossYield - sofrValue : null
  const treasurySpread =
    grossYield != null && treasuryValue != null ? grossYield - treasuryValue : null

  // Loss/recovery (CASHFLOW-04)
  const realizedLosses = periods.reduce((sum, p) => {
    const variance =
      Number(p.scheduled_principal) +
      Number(p.scheduled_interest) -
      (Number(p.actual_principal) + Number(p.actual_interest))
    return sum + Math.max(0, variance)
  }, 0)
  // recovery = 0 (no recovery column in RELoanCashflow — POC stub)

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 gap-6">

      {/* Panel 1: P&I Actual vs Projected (full width, CASHFLOW-01) */}
      <ChartCard
        title="P&I Actual vs Projected"
        isLoading={cashflow.isLoading}
        isEmpty={!piData.length}
        colSpan="full"
      >
        <ResponsiveContainer width="100%" height={280}>
          <LineChart data={piData}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis dataKey="period_date" tick={{ fontSize: 10 }} />
            <YAxis tickFormatter={(v) => formatUPB(v)} tick={{ fontSize: 11 }} />
            <Tooltip
              formatter={(value, name) => [formatUPB(Number(value ?? 0)), String(name)]}
              labelFormatter={(label) => `Period: ${label}`}
            />
            <Legend />
            <Line
              type="monotone"
              dataKey="actual_pi"
              stroke="#0f2e5a"
              name="Actual P&I"
              dot={false}
              strokeWidth={2}
            />
            <Line
              type="monotone"
              dataKey="projected_pi"
              stroke="#94a3b8"
              strokeDasharray="4 2"
              name="Projected P&I"
              dot={false}
              strokeWidth={2}
            />
          </LineChart>
        </ResponsiveContainer>
        {/* UX-01: P&I series don't map to filter dimensions — no click handler per Phase 22 precedent */}
      </ChartCard>

      {/* Panel 2: NOI Trend (half width, CASHFLOW-02) */}
      <ChartCard
        title="NOI Trend"
        isLoading={cashflow.isLoading}
        isEmpty={!noiData.length}
      >
        <ResponsiveContainer width="100%" height={280}>
          <BarChart data={noiData}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis dataKey="period_date" tick={{ fontSize: 10 }} />
            <YAxis tickFormatter={(v) => formatUPB(v)} tick={{ fontSize: 11 }} />
            <Tooltip formatter={(value) => [formatUPB(Number(value ?? 0)), 'NOI']} />
            <Bar dataKey="total_noi" fill="#0f2e5a" name="NOI" />
          </BarChart>
        </ResponsiveContainer>
      </ChartCard>

      {/* Panel 3: CPR Trend (half width, CASHFLOW-04) */}
      <ChartCard
        title="CPR Trend"
        isLoading={cashflow.isLoading}
        isEmpty={!cprData.length}
      >
        <ResponsiveContainer width="100%" height={280}>
          <LineChart data={cprData}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis dataKey="period_date" tick={{ fontSize: 10 }} />
            <YAxis tickFormatter={(v) => `${v.toFixed(1)}%`} tick={{ fontSize: 11 }} />
            <Tooltip formatter={(value) => [`${Number(value ?? 0).toFixed(2)}%`, 'CPR']} />
            <Line
              type="monotone"
              dataKey="cpr_pct"
              stroke="#059669"
              name="CPR"
              dot={false}
              strokeWidth={2}
            />
          </LineChart>
        </ResponsiveContainer>
      </ChartCard>

      {/* Panel 4: Yield Analysis (full width, CASHFLOW-03) */}
      <ChartCard
        title="Yield Analysis"
        isLoading={cashflow.isLoading || market.isLoading}
        isEmpty={grossYield == null}
        colSpan="full"
      >
        <dl className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <div className="bg-gray-50 rounded p-3">
            <dt className="text-xs text-[#475569] mb-1">Gross Yield</dt>
            <dd className="text-lg font-semibold text-[#0f2e5a]">
              {grossYield != null ? `${(grossYield * 100).toFixed(3)}%` : '\u2014'}
            </dd>
            <p className="text-[10px] text-[#94a3b8]">Annualized, last period</p>
          </div>
          <div className="bg-gray-50 rounded p-3">
            <dt className="text-xs text-[#475569] mb-1">Net Yield</dt>
            <dd className="text-lg font-semibold text-[#0f2e5a]">
              {netYield != null ? `${(netYield * 100).toFixed(3)}%` : '\u2014'}
            </dd>
            <p className="text-[10px] text-[#94a3b8]">After net loss rate</p>
          </div>
          <div className="bg-gray-50 rounded p-3">
            <dt className="text-xs text-[#475569] mb-1">SOFR Spread</dt>
            <dd
              className={`text-lg font-semibold ${
                sofrSpread != null && sofrSpread >= 0 ? 'text-green-700' : 'text-red-600'
              }`}
            >
              {sofrSpread != null
                ? `${sofrSpread >= 0 ? '+' : ''}${(sofrSpread * 100).toFixed(0)} bps`
                : '\u2014'}
            </dd>
            <p className="text-[10px] text-[#94a3b8]">
              vs SOFR {sofrValue != null ? `${sofrValue.toFixed(2)}%` : ''} (stub)
            </p>
          </div>
          <div className="bg-gray-50 rounded p-3">
            <dt className="text-xs text-[#475569] mb-1">Treasury Spread</dt>
            <dd
              className={`text-lg font-semibold ${
                treasurySpread != null && treasurySpread >= 0 ? 'text-green-700' : 'text-red-600'
              }`}
            >
              {treasurySpread != null
                ? `${treasurySpread >= 0 ? '+' : ''}${(treasurySpread * 100).toFixed(0)} bps`
                : '\u2014'}
            </dd>
            <p className="text-[10px] text-[#94a3b8]">
              vs 10Y Treasury {treasuryValue != null ? `${treasuryValue.toFixed(2)}%` : ''} (stub)
            </p>
          </div>
        </dl>
      </ChartCard>

      {/* Panel 5: Loss and Recovery (full width, CASHFLOW-04) */}
      <ChartCard
        title="Loss and Recovery"
        isLoading={cashflow.isLoading}
        isEmpty={false}
        colSpan="full"
      >
        <dl className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div className="bg-gray-50 rounded p-3">
            <dt className="text-xs text-[#475569] mb-1">Net Loss Rate</dt>
            <dd className="text-lg font-semibold text-[#0f2e5a]">
              {cashflow.data?.net_loss_rate != null
                ? `${(Number(cashflow.data.net_loss_rate) * 100).toFixed(3)}%`
                : '0.000%'}
            </dd>
            <p className="text-[10px] text-[#94a3b8]">(scheduled - actual) / total UPB</p>
          </div>
          <div className="bg-gray-50 rounded p-3">
            <dt className="text-xs text-[#475569] mb-1">Realized Losses (Proxy)</dt>
            <dd className="text-lg font-semibold text-red-700">{formatUPB(realizedLosses)}</dd>
            <p className="text-[10px] text-[#94a3b8]">Sum of P&amp;I shortfalls</p>
          </div>
          <div className="bg-gray-50 rounded p-3">
            <dt className="text-xs text-[#475569] mb-1">Recovery</dt>
            <dd className="text-lg font-semibold text-[#94a3b8]">$0</dd>
            <p className="text-[10px] text-[#94a3b8]">No recovery column in data (POC stub)</p>
          </div>
        </dl>
      </ChartCard>

    </div>
  )
}
