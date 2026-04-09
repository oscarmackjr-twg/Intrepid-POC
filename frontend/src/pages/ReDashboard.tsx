import { ReDashboardFilterSidebar } from '../components/re/ReDashboardFilterSidebar'

export default function ReDashboard() {
  return (
    <div className="flex gap-6 min-h-[calc(100vh-theme(spacing.12))]">
      {/* Charts area — flex-1 takes remaining space */}
      <div className="flex-1 min-w-0">
        <h1 className="text-2xl font-bold text-[#1a3868] mb-4">RE Portfolio Dashboard</h1>
        <p className="text-sm text-[#475569]">Chart panels will appear here in Phase 20.</p>
      </div>

      {/* Filter panel — right side, always visible (D-01, D-02) */}
      <ReDashboardFilterSidebar />
    </div>
  )
}
