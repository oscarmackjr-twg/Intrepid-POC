import { useState } from 'react'
import { ReDashboardFilterSidebar } from '../components/re/ReDashboardFilterSidebar'
import { KPICard } from '../components/re/KPICard'
import { useKPIs } from '../hooks/useKPIs'
import { formatUPB, formatRate, formatWAM, formatDSCR, formatCount } from '../utils/formatKpi'
import type { KPIResponse } from '../types/re'

const KPI_CARDS: {
  key: keyof KPIResponse
  label: string
  format: (value: number | null) => string
}[] = [
  { key: 'total_upb',         label: 'Total UPB',          format: formatUPB },
  { key: 'wac',               label: 'WAC',                format: formatRate },
  { key: 'wam',               label: 'WAM',                format: formatWAM },
  { key: 'wa_ltv',            label: 'WA LTV',             format: formatRate },
  { key: 'wa_dscr',           label: 'WA DSCR',            format: formatDSCR },
  { key: 'active_loan_count', label: 'Active Loan Count',  format: formatCount },
  { key: 'delinquent_30_upb', label: 'Delinquent 30 UPB',  format: formatUPB },
  { key: 'delinquent_60_upb', label: 'Delinquent 60 UPB',  format: formatUPB },
  { key: 'delinquent_90_upb', label: 'Delinquent 90+ UPB', format: formatUPB },
  { key: 'portfolio_yield',   label: 'Portfolio Yield',    format: formatRate },
]

export default function ReDashboard() {
  const { data, isLoading, isError } = useKPIs()
  const [highlightedDelinquency, setHighlightedDelinquency] = useState<string | null>(null)

  // No-data: active_loan_count === 0 means all cards show en-dash (per D-09)
  const isNoData = !isLoading && data !== undefined && data.active_loan_count === 0

  return (
    <div className="flex gap-6 min-h-[calc(100vh-theme(spacing.12))]">
      {/* Charts area — flex-1 takes remaining space */}
      <div className="flex-1 min-w-0">
        <h1 className="text-2xl font-bold text-[#1a3868] mb-4">RE Portfolio Dashboard</h1>

        {isError && (
          <p className="text-sm text-red-600 mb-4">Failed to load KPI data.</p>
        )}

        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
          {KPI_CARDS.map(({ key, label, format }) => {
            const isDelinquency = key.startsWith('delinquent_')
            const rawValue = data ? data[key] : null
            const displayValue = isNoData ? '\u2013' : format(rawValue as number | null)

            return (
              <KPICard
                key={key}
                label={label}
                value={displayValue}
                isLoading={isLoading}
                isNoData={isNoData || (!isLoading && rawValue === null)}
                isClickable={isDelinquency}
                isHighlighted={highlightedDelinquency === key}
                onClick={isDelinquency ? () => {
                  setHighlightedDelinquency(prev => prev === key ? null : key)
                } : undefined}
              />
            )
          })}
        </div>
      </div>

      {/* Filter panel — right side, always visible (D-01, D-02) */}
      <ReDashboardFilterSidebar />
    </div>
  )
}
