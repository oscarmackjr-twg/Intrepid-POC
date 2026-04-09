import { Routes, Route, Navigate } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { AuthProvider } from './contexts/AuthContext'
import Login from './pages/Login'
import Dashboard from './pages/Dashboard'
import Runs from './pages/Runs'
import RunDetail from './pages/RunDetail'
import Exceptions from './pages/Exceptions'
import RejectedLoans from './pages/RejectedLoans'
import FileManager from './pages/FileManager'
import ProgramRuns from './pages/ProgramRuns'
import HolidayMaintenance from './pages/HolidayMaintenance'
import ReDashboard from './pages/ReDashboard'
import ReExecutiveSummaryPage from './pages/ReExecutiveSummaryPage'
import RePortfolioPage from './pages/RePortfolioPage'
import ReCreditQualityPage from './pages/ReCreditQualityPage'
import CashFlow from './pages/CashFlow'
import ProtectedRoute from './components/ProtectedRoute'
import Layout from './components/Layout'

const queryClient = new QueryClient()

function ReStubPage() {
  return <p className="text-[#94a3b8] text-sm mt-8">Coming in a future phase.</p>
}

function App() {
  return (
    <QueryClientProvider client={queryClient}>
    <AuthProvider>
      <Routes>
        <Route path="/login" element={<Login />} />
        <Route
          path="/"
          element={
            <ProtectedRoute>
              <Layout />
            </ProtectedRoute>
          }
        >
          <Route index element={<Navigate to="/dashboard" replace />} />
          <Route path="dashboard" element={<Dashboard />} />
          <Route path="runs" element={<Runs />} />
          <Route path="runs/:runId" element={<RunDetail />} />
          <Route path="exceptions" element={<Exceptions />} />
          <Route path="rejected-loans" element={<RejectedLoans />} />
          <Route path="files" element={<FileManager />} />
          <Route path="cashflow" element={<CashFlow />} />
          <Route path="program-runs" element={<ProgramRuns />} />
          <Route path="holidays" element={<HolidayMaintenance />} />
          <Route path="re-dashboard" element={<ReDashboard />}>
            <Route index element={<ReExecutiveSummaryPage />} />
            <Route path="portfolio" element={<RePortfolioPage />} />
            <Route path="credit" element={<ReCreditQualityPage />} />
            <Route path="cashflow" element={<ReStubPage />} />
            <Route path="origination" element={<ReStubPage />} />
          </Route>
        </Route>
      </Routes>
    </AuthProvider>
    </QueryClientProvider>
  )
}

export default App
