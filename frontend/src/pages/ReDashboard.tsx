import { NavLink, Outlet } from 'react-router-dom'
import { ReDashboardFilterSidebar } from '../components/re/ReDashboardFilterSidebar'

const TABS = [
  { label: 'Executive Summary', to: '/re-dashboard', end: true },
  { label: 'Portfolio',         to: '/re-dashboard/portfolio', end: false },
  { label: 'Credit Quality',    to: '/re-dashboard/credit', end: false },
  { label: 'Cash Flow',         to: '/re-dashboard/cashflow', end: false },
  { label: 'Origination',       to: '/re-dashboard/origination', end: false },
]

export default function ReDashboard() {
  return (
    <div className="flex gap-6 min-h-[calc(100vh-theme(spacing.12))]">
      <div className="flex-1 min-w-0">
        <h1 className="text-2xl font-bold text-[#1a3868] mb-4">RE Portfolio Dashboard</h1>

        {/* Tab strip (per D-26) */}
        <nav className="flex gap-6 border-b border-gray-200 mb-6">
          {TABS.map(({ label, to, end }) => (
            <NavLink
              key={to}
              to={to}
              end={end}
              className={({ isActive }) =>
                `pb-2 text-sm font-medium transition-colors ${
                  isActive
                    ? 'border-b-2 border-[#1a3868] text-[#1a3868]'
                    : 'text-[#475569] hover:text-[#1a3868]'
                }`
              }
            >
              {label}
            </NavLink>
          ))}
        </nav>

        {/* Child page content */}
        <Outlet />
      </div>

      {/* Filter panel — right side, always visible */}
      <ReDashboardFilterSidebar />
    </div>
  )
}
