import type { ConcentrationLimit } from '../../types/re'

interface ConcentrationLimitsProps {
  limits: ConcentrationLimit[]
}

function getBarColor(proximity: number): string {
  if (proximity >= 0.9) return 'bg-red-500'
  if (proximity >= 0.7) return 'bg-yellow-400'
  return 'bg-green-500'
}

export function ConcentrationLimits({ limits }: ConcentrationLimitsProps) {
  return (
    <div className="space-y-4">
      {limits.map((limit) => (
        <div key={limit.category}>
          <div className="flex justify-between text-sm mb-1">
            <span className="text-[#1a3868] font-medium">{limit.category}</span>
            <span className="text-[#475569]">
              {(limit.current_pct * 100).toFixed(1)}% / {(limit.limit_pct * 100).toFixed(1)}% limit
            </span>
          </div>
          <div className="w-full bg-gray-200 rounded h-2">
            <div
              className={`h-2 rounded ${getBarColor(limit.proximity)}`}
              style={{ width: `${Math.min(limit.proximity * 100, 100)}%` }}
            />
          </div>
        </div>
      ))}
    </div>
  )
}
