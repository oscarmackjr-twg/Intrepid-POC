interface ChartCardProps {
  title: string
  isLoading: boolean
  isEmpty: boolean
  colSpan?: 'full'   // when set, card spans both grid columns
  children?: React.ReactNode
}

export function ChartCard({ title, isLoading, isEmpty, colSpan, children }: ChartCardProps) {
  const spanClass = colSpan === 'full' ? 'col-span-1 md:col-span-2' : ''
  return (
    <div className={`bg-white rounded-lg border border-gray-200 p-4 ${spanClass}`}>
      <h3 className="text-sm font-semibold text-[#1a3868] mb-3">{title}</h3>
      {isLoading ? (
        <div className="animate-pulse bg-gray-200 rounded h-48 w-full" />
      ) : isEmpty ? (
        <p className="text-[#94a3b8] text-sm text-center py-16">No data</p>
      ) : (
        children
      )}
    </div>
  )
}
