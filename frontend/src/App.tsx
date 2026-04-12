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
import ReCashFlowPage from './pages/ReCashFlowPage'
import ReOriginationPage from './pages/ReOriginationPage'
import CashFlow from './pages/CashFlow'
import ProtectedRoute from './components/ProtectedRoute'
import RoleGate from './components/RoleGate'
import Layout from './components/Layout'

const queryClient = new QueryClient()

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
          <Route path="re-dashboard" element={<RoleGate allowed={['admin', 'sales_team']}><ReDashboard /></RoleGate>}>
            <Route index element={<ReExecutiveSummaryPage />} />
            <Route path="portfolio" element={<RePortfolioPage />} />
            <Route path="credit" element={<ReCreditQualityPage />} />
            <Route path="cashflow" element={<ReCashFlowPage />} />
            <Route path="origination" element={<ReOriginationPage />} />
          </Route>
        </Route>
      </Routes>
    </AuthProvider>
    </QueryClientProvider>
  )
}

export default App
