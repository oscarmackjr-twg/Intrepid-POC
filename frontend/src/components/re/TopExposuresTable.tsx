import { formatUPB, formatRate, formatDSCR } from '../../utils/formatKpi'
import type { TopExposure } from '../../types/re'

interface TopExposuresTableProps {
  exposures: TopExposure[]
}

export function TopExposuresTable({ exposures }: TopExposuresTableProps) {
  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b border-gray-200 text-left text-[#475569]">
            <th className="py-2 pr-4 font-medium">Loan #</th>
            <th className="py-2 pr-4 font-medium">Borrower</th>
            <th className="py-2 pr-4 font-medium text-right">UPB</th>
            <th className="py-2 pr-4 font-medium text-right">LTV</th>
            <th className="py-2 pr-4 font-medium text-right">DSCR</th>
            <th className="py-2 pr-4 font-medium">Property Type</th>
            <th className="py-2 font-medium">State</th>
          </tr>
        </thead>
        <tbody>
          {exposures.map((loan) => (
            <tr
              key={loan.loan_number}
              className="border-b border-gray-100 text-[#1a3868]"
              // TODO: Phase 25 — wire row click to loan detail side-panel
              onClick={undefined}
            >
              <td className="py-2 pr-4">{loan.loan_number}</td>
              <td className="py-2 pr-4">{loan.borrower_name}</td>
              <td className="py-2 pr-4 text-right">{formatUPB(loan.upb)}</td>
              <td className="py-2 pr-4 text-right">{formatRate(loan.ltv)}</td>
              <td className="py-2 pr-4 text-right">{formatDSCR(loan.dscr)}</td>
              <td className="py-2 pr-4">{loan.property_type}</td>
              <td className="py-2">{loan.state}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
