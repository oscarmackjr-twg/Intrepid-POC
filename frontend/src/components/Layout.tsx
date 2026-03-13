import { Outlet, Link, useLocation } from 'react-router-dom'
import { useAuth } from '../contexts/AuthContext'
import StagingBanner from './StagingBanner'
import twgLogo from '../assets/twg-logo.png'

export default function Layout() {
  const { user, logout } = useAuth()
  const location = useLocation()

  return (
    <div className="flex flex-col min-h-screen">
      <StagingBanner />
      <div className="flex flex-1">
        {/* Sidebar */}
        <aside className="w-60 min-h-full flex flex-col bg-white border-r border-gray-200 sticky top-0 h-screen">
          {/* Logo header */}
          <div className="px-5 py-5 border-b border-gray-200">
            <img src={twgLogo} alt="TWG Global" className="h-8 w-auto" />
            <p className="mt-1 text-xs font-semibold tracking-widest text-[#1a3868] uppercase">
              Intrepid Loan Platform
            </p>
          </div>

          {/* Nav list */}
          <nav className="flex-1 overflow-y-auto py-2">
            {/* Dashboard */}
            <Link
              to="/dashboard"
              className={`px-5 py-2 text-sm flex items-center gap-2 border-l-4 ${
                location.pathname.startsWith('/dashboard')
                  ? 'border-[#1a3868] text-[#1a3868] font-semibold bg-gray-50'
                  : 'border-transparent text-[#475569] hover:text-[#1a3868] hover:bg-gray-50'
              }`}
            >
              Dashboard
            </Link>

            {/* Program Runs */}
            <Link
              to="/program-runs"
              className={`px-5 py-2 text-sm flex items-center gap-2 border-l-4 ${
                location.pathname.startsWith('/program-runs') && !location.search.includes('type=')
                  ? 'border-[#1a3868] text-[#1a3868] font-semibold bg-gray-50'
                  : 'border-transparent text-[#475569] hover:text-[#1a3868] hover:bg-gray-50'
              }`}
            >
              Program Runs
            </Link>

            {/* SG group */}
            <span className="px-5 pt-4 pb-1 text-xs font-bold tracking-widest text-[#94a3b8] uppercase select-none block">
              SG
            </span>

            <Link
              to="/program-runs?type=sg"
              className={`pl-8 pr-5 py-2 text-sm flex items-center gap-2 border-l-4 ${
                location.pathname.startsWith('/program-runs') && location.search.includes('type=sg')
                  ? 'border-[#1a3868] text-[#1a3868] font-semibold bg-gray-50'
                  : 'border-transparent text-[#475569] hover:text-[#1a3868] hover:bg-gray-50'
              }`}
            >
              Final Funding SG
            </Link>

            <Link
              to="/cashflow?type=sg"
              className={`pl-8 pr-5 py-2 text-sm flex items-center gap-2 border-l-4 ${
                location.pathname.startsWith('/cashflow') && location.search.includes('type=sg')
                  ? 'border-[#1a3868] text-[#1a3868] font-semibold bg-gray-50'
                  : 'border-transparent text-[#475569] hover:text-[#1a3868] hover:bg-gray-50'
              }`}
            >
              Cash Flow SG
            </Link>

            {/* CIBC group */}
            <span className="px-5 pt-4 pb-1 text-xs font-bold tracking-widest text-[#94a3b8] uppercase select-none block">
              CIBC
            </span>

            <Link
              to="/program-runs?type=cibc"
              className={`pl-8 pr-5 py-2 text-sm flex items-center gap-2 border-l-4 ${
                location.pathname.startsWith('/program-runs') && location.search.includes('type=cibc')
                  ? 'border-[#1a3868] text-[#1a3868] font-semibold bg-gray-50'
                  : 'border-transparent text-[#475569] hover:text-[#1a3868] hover:bg-gray-50'
              }`}
            >
              Final Funding CIBC
            </Link>

            <Link
              to="/cashflow?type=cibc"
              className={`pl-8 pr-5 py-2 text-sm flex items-center gap-2 border-l-4 ${
                location.pathname.startsWith('/cashflow') && location.search.includes('type=cibc')
                  ? 'border-[#1a3868] text-[#1a3868] font-semibold bg-gray-50'
                  : 'border-transparent text-[#475569] hover:text-[#1a3868] hover:bg-gray-50'
              }`}
            >
              Cash Flow CIBC
            </Link>

            {/* File Manager */}
            <Link
              to="/files"
              className={`px-5 py-2 text-sm flex items-center gap-2 border-l-4 ${
                location.pathname.startsWith('/files')
                  ? 'border-[#1a3868] text-[#1a3868] font-semibold bg-gray-50'
                  : 'border-transparent text-[#475569] hover:text-[#1a3868] hover:bg-gray-50'
              }`}
            >
              File Manager
            </Link>

            {/* Admin-only items */}
            {user?.role === 'admin' && (
              <>
                <Link
                  to="/cashflow"
                  className={`px-5 py-2 text-sm flex items-center gap-2 border-l-4 ${
                    location.pathname.startsWith('/cashflow') && !location.search.includes('type=')
                      ? 'border-[#1a3868] text-[#1a3868] font-semibold bg-gray-50'
                      : 'border-transparent text-[#475569] hover:text-[#1a3868] hover:bg-gray-50'
                  }`}
                >
                  Cash Flow
                </Link>

                <Link
                  to="/holidays"
                  className={`px-5 py-2 text-sm flex items-center gap-2 border-l-4 ${
                    location.pathname.startsWith('/holidays')
                      ? 'border-[#1a3868] text-[#1a3868] font-semibold bg-gray-50'
                      : 'border-transparent text-[#475569] hover:text-[#1a3868] hover:bg-gray-50'
                  }`}
                >
                  Holiday Maintenance
                </Link>
              </>
            )}
          </nav>

          {/* User footer */}
          <div className="px-5 py-4 border-t border-gray-200 mt-auto">
            <p className="text-xs text-[#475569] truncate">{user?.username}</p>
            <p className="text-xs text-[#94a3b8] capitalize mb-3">{user?.role}</p>
            <button
              onClick={logout}
              className="text-xs text-[#475569] hover:text-[#1a3868] font-medium"
            >
              Sign out
            </button>
          </div>
        </aside>

        {/* Main content */}
        <main className="flex-1 bg-[#f8fafc] min-h-screen">
          <div className="p-6">
            <Outlet />
          </div>
        </main>
      </div>
    </div>
  )
}
