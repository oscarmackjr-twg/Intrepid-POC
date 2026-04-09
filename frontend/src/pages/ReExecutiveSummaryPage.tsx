import { useState } from 'react'
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

export default function ReExecutiveSummaryPage() {
  const { data, isLoading, isError } = useKPIs()
  const [highlightedDelinquency, setHighlightedDelinquency] = useState<string | null>(null)

  return (
    <>
      {isError && (
        <p className="text-sm text-red-600 mb-4">Failed to load KPI data.</p>
      )}

      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        {KPI_CARDS.map(({ key, label, format }) => {
          const isDelinquency = key.startsWith('delinquent_')
          const rawValue = data ? data[key] : null
          const displayValue = format(rawValue as number | null)

          return (
            <KPICard
              key={key}
              label={label}
              value={displayValue}
              isLoading={isLoading}
              isNoData={!isLoading && rawValue === null}
              isClickable={isDelinquency}
              isHighlighted={highlightedDelinquency === key}
              onClick={isDelinquency ? () => {
                setHighlightedDelinquency(prev => prev === key ? null : key)
              } : undefined}
            />
          )
        })}
      </div>
    </>
  )
}
