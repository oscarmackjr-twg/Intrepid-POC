interface KPICardProps {
  label: string
  value: string          // pre-formatted display string
  isLoading: boolean
  isNoData: boolean      // true when active_loan_count === 0 (per D-09)
  isClickable?: boolean  // default false (per D-12)
  isHighlighted?: boolean // visual highlight state for delinquency click
  onClick?: () => void
}

export function KPICard({
  label,
  value,
  isLoading,
  isNoData,
  isClickable = false,
  isHighlighted = false,
  onClick,
}: KPICardProps) {
  const containerClasses = [
    'bg-white rounded-lg border border-gray-200 p-4 flex flex-col items-start',
    isClickable ? 'cursor-pointer hover:ring-2 hover:ring-[#1a3868]/30' : '',
    isHighlighted ? 'ring-2 ring-[#1a3868]' : '',
  ]
    .filter(Boolean)
    .join(' ')

  return (
    <div
      className={containerClasses}
      onClick={isClickable ? onClick : undefined}
    >
      {isLoading ? (
        <>
          {/* Loading skeleton — same card dimensions, no layout shift (per D-07) */}
          <div className="animate-pulse bg-gray-200 rounded h-8 w-24 mb-1" />
          <span className="text-xs text-[#475569]">{label}</span>
        </>
      ) : isNoData ? (
        <>
          {/* No-data state — en-dash in muted slate (per D-08) */}
          <span className="text-2xl font-bold text-[#94a3b8]">{'\u2013'}</span>
          <span className="text-xs text-[#475569]">{label}</span>
        </>
      ) : (
        <>
          {/* Normal state */}
          <span className="text-2xl font-bold text-[#1a3868]">{value}</span>
          <span className="text-xs text-[#475569]">{label}</span>
        </>
      )}
      {isClickable && (
        // TODO: FILTER-01 — wire delinquency_bucket filter when ReLoanFilters schema supports it
        <></>
      )}
    </div>
  )
}
