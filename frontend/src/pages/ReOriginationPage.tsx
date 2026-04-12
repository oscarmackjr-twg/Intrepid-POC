import { useQuery } from '@tanstack/react-query'
import axios from 'axios'
import {
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
import { formatUPB, formatRate, formatDSCR } from '../utils/formatKpi'
import type { OriginationPipelineResponse, MarketContextResponse } from '../types/re'

// TWG brand palette — matches RePortfolioPage PIE_COLORS (per D-02)
const PROPERTY_COLORS = ['#1a3868', '#2563eb', '#0ea5e9', '#7c3aed', '#db2777', '#d97706', '#059669', '#6366f1']

export default function ReOriginationPage() {
  const { filters, setFilter } = useReLoanFilters()

  // Origination pipeline query — re-fetches when filters change (per D-10)
  const origination = useQuery({
    queryKey: ['re-origination-pipeline', filters],
    queryFn: async () => {
      const params = Object.fromEntries(
        Object.entries(filters).filter(([, v]) => v !== null && v !== '')
      )
      const { data } = await axios.get<OriginationPipelineResponse>(
        '/api/re/origination-pipeline', { params }
      )
      return data
    },
  })

  // Market context query — static key (no filters — market rates are global, per D-10)
  const market = useQuery({
    queryKey: ['re-market-context'],
    queryFn: async () => {
      const { data } = await axios.get<MarketContextResponse>('/api/re/market-context')
      return data
    },
  })

  // Collect unique property types for stacked bar (D-03)
  const propertyTypes = [
    ...new Set(
      origination.data?.origination_by_month?.map((r) => r.property_type) ?? []
    ),
  ]

  // Pivot flat rows into Recharts stacked bar format: one data point per YYYY-MM (D-03)
  const volumeByMonth = new Map<string, Record<string, number>>()
  for (const row of origination.data?.origination_by_month ?? []) {
    const key = `${row.year}-${String(row.month).padStart(2, '0')}`
    if (!volumeByMonth.has(key)) volumeByMonth.set(key, { month: key } as unknown as Record<string, number>)
    volumeByMonth.get(key)![row.property_type] = Number(row.total_upb)
  }
  const volumeData = [...volumeByMonth.values()]

  // Net Origination Volume KPI (D-05, ORIGIN-02)
  const netOriginationVolume = (origination.data?.origination_by_month ?? []).reduce(
    (sum, r) => sum + Number(r.total_upb),
    0
  )

  return (
    <div className="space-y-6">

      {/* Origination panels: 2x2 grid (per D-02) */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">

        {/* Panel 1: Origination Volume stacked bar by property type (D-03, ORIGIN-01) */}
        <ChartCard
          title="Origination Volume by Month"
          isLoading={origination.isLoading}
          isEmpty={!volumeData.length}
        >
          <ResponsiveContainer width="100%" height={280}>
            <BarChart data={volumeData}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="month" tick={{ fontSize: 10 }} />
              <YAxis tickFormatter={(v) => formatUPB(v)} tick={{ fontSize: 11 }} />
              <Tooltip formatter={(value) => [formatUPB(Number(value ?? 0))]} />
              <Legend />
              {propertyTypes.map((pt, i) => (
                <Bar
                  key={pt}
                  dataKey={pt}
                  stackId="origination"
                  fill={PROPERTY_COLORS[i % PROPERTY_COLORS.length]}
                  onClick={() => setFilter('property_type', pt)}
                  style={{ cursor: 'pointer' }}
                />
              ))}
            </BarChart>
          </ResponsiveContainer>
        </ChartCard>

        {/* Panel 2: Net Origination Volume KPI (D-05, ORIGIN-02) */}
        <ChartCard
          title="Net Origination Volume"
          isLoading={origination.isLoading}
          isEmpty={netOriginationVolume === 0 && !origination.isLoading}
        >
          <div className="flex flex-col items-center justify-center py-8">
            <span className="text-3xl font-bold text-[#1a3868]">
              {formatUPB(netOriginationVolume)}
            </span>
            <span className="text-xs text-[#475569] mt-1">
              Total origination volume for filtered period
            </span>
          </div>
        </ChartCard>

        {/* Panel 3: Pipeline Funnel horizontal bar (D-06, ORIGIN-03) */}
        <ChartCard
          title="Pipeline Funnel"
          isLoading={origination.isLoading}
          isEmpty={!origination.data?.pipeline_funnel?.length}
        >
          <ResponsiveContainer width="100%" height={200}>
            <BarChart
              data={origination.data?.pipeline_funnel ?? []}
              layout="vertical"
              margin={{ left: 80 }}
            >
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis type="number" tickFormatter={(v) => formatUPB(v)} tick={{ fontSize: 11 }} />
              <YAxis type="category" dataKey="stage" tick={{ fontSize: 11 }} width={80} />
              <Tooltip
                formatter={(value, _name, props) => {
                  const stage = props.payload
                  return [
                    `${formatUPB(Number(value ?? 0))} (${stage.loan_count} loans)`,
                    'UPB',
                  ]
                }}
              />
              <Bar dataKey="total_upb" fill="#1a3868" />
            </BarChart>
          </ResponsiveContainer>
        </ChartCard>

        {/* Panel 4: Vintage Analysis table (D-07, ORIGIN-04) */}
        <ChartCard
          title="Vintage Analysis"
          isLoading={origination.isLoading}
          isEmpty={!origination.data?.vintage_breakdown?.length}
        >
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-gray-200 text-left text-[#475569]">
                  <th className="py-2 pr-4 font-medium">Vintage</th>
                  <th className="py-2 pr-4 font-medium text-right">Loans</th>
                  <th className="py-2 pr-4 font-medium text-right">UPB</th>
                  <th className="py-2 pr-4 font-medium text-right">Avg LTV</th>
                  <th className="py-2 pr-4 font-medium text-right">Avg DSCR</th>
                  <th className="py-2 font-medium text-right">Avg Rate</th>
                </tr>
              </thead>
              <tbody>
                {(origination.data?.vintage_breakdown ?? []).map((v) => (
                  <tr key={v.vintage_year} className="border-b border-gray-100 text-[#1a3868]">
                    <td className="py-2 pr-4">{v.vintage_year}</td>
                    <td className="py-2 pr-4 text-right">{v.loan_count}</td>
                    <td className="py-2 pr-4 text-right">{formatUPB(v.total_upb)}</td>
                    <td className="py-2 pr-4 text-right">{formatRate(v.avg_ltv)}</td>
                    <td className="py-2 pr-4 text-right">{formatDSCR(v.avg_dscr)}</td>
                    <td className="py-2 text-right">{formatRate(v.avg_rate)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </ChartCard>

      </div>

      {/* Market Context section: full width below the 2x2 grid (D-08, D-09, MARKET-01, MARKET-02) */}
      <div>
        <h2 className="text-lg font-semibold text-[#1a3868] mb-1">Market Context</h2>
        <p className="text-xs text-[#94a3b8] mb-4">Indicative values — not connected to live feeds</p>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">

          {/* Rate cards: 10Y Treasury + SOFR with trend arrows (MARKET-01, D-08) */}
          <div className="bg-white rounded-lg border border-gray-200 p-4">
            <div className="grid grid-cols-2 gap-4">
              <div>
                <dt className="text-xs text-[#475569] mb-1">10Y Treasury</dt>
                <dd className="text-2xl font-bold text-[#1a3868]">
                  {market.data?.ten_year_treasury
                    ? `${Number(market.data.ten_year_treasury.value).toFixed(2)}%`
                    : '\u2013'}
                  <span className="text-sm ml-1">
                    {market.data?.ten_year_treasury?.trend === 'up'
                      ? '\u2191'
                      : market.data?.ten_year_treasury?.trend === 'down'
                      ? '\u2193'
                      : '\u2192'}
                  </span>
                </dd>
              </div>
              <div>
                <dt className="text-xs text-[#475569] mb-1">SOFR</dt>
                <dd className="text-2xl font-bold text-[#1a3868]">
                  {market.data?.sofr
                    ? `${Number(market.data.sofr.value).toFixed(2)}%`
                    : '\u2013'}
                  <span className="text-sm ml-1">
                    {market.data?.sofr?.trend === 'up'
                      ? '\u2191'
                      : market.data?.sofr?.trend === 'down'
                      ? '\u2193'
                      : '\u2192'}
                  </span>
                </dd>
              </div>
            </div>
          </div>

          {/* Cap rates + vacancy rates table by property type (MARKET-02, D-08) */}
          <div className="bg-white rounded-lg border border-gray-200 p-4">
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-gray-200 text-left text-[#475569]">
                    <th className="py-2 pr-4 font-medium">Property Type</th>
                    <th className="py-2 pr-4 font-medium text-right">Cap Rate</th>
                    <th className="py-2 font-medium text-right">Vacancy</th>
                  </tr>
                </thead>
                <tbody>
                  {(market.data?.cap_rates ?? []).map((cr) => {
                    const vr = (market.data?.vacancy_rates ?? []).find(
                      (v) => v.property_type === cr.property_type
                    )
                    return (
                      <tr key={cr.property_type} className="border-b border-gray-100 text-[#1a3868]">
                        <td className="py-2 pr-4">{cr.property_type}</td>
                        <td className="py-2 pr-4 text-right">{Number(cr.value).toFixed(1)}%</td>
                        <td className="py-2 text-right">
                          {vr ? `${Number(vr.value).toFixed(1)}%` : '\u2013'}
                        </td>
                      </tr>
                    )
                  })}
                </tbody>
              </table>
            </div>
          </div>

        </div>
      </div>

    </div>
  )
}
