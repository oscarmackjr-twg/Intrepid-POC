import { useQuery } from '@tanstack/react-query'
import axios from 'axios'
import {
  PieChart,
  Pie,
  Cell,
  Tooltip,
  ResponsiveContainer,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
} from 'recharts'
import { useReLoanFilters } from '../hooks/useReLoanFilters'
import { ChartCard } from '../components/re/ChartCard'
import type { ConcentrationItem, ConcentrationResponse, DistributionsResponse, MaturityProfileResponse } from '../types/re'

// TWG brand palette for pie chart slices (per D-12, D-25)
const PIE_COLORS = ['#1a3868', '#2563eb', '#0ea5e9', '#7c3aed', '#db2777', '#d97706', '#059669', '#6366f1']

export default function RePortfolioPage() {
  const { filters, setFilter } = useReLoanFilters()

  // Strip null/empty values before sending as query params (same pattern as useKPIs)
  const params = Object.fromEntries(
    Object.entries(filters).filter(([, v]) => v !== null && v !== '')
  )

  // Three TanStack Query calls (per D-22)
  const concentration = useQuery({
    queryKey: ['re-concentration', filters],
    queryFn: async () => {
      const { data } = await axios.get<ConcentrationResponse>('/api/re/concentration', { params })
      return data
    },
  })

  const distributions = useQuery({
    queryKey: ['re-distributions', filters],
    queryFn: async () => {
      const { data } = await axios.get<DistributionsResponse>('/api/re/distributions', { params })
      return data
    },
  })

  const maturity = useQuery({
    queryKey: ['re-maturity-profile', filters],
    queryFn: async () => {
      const { data } = await axios.get<MaturityProfileResponse>('/api/re/maturity-profile', { params })
      return data
    },
  })

  // Derive top-10 states sorted descending by total_upb (per D-04)
  const topStates = (concentration.data?.state ?? [])
    .slice()
    .sort((a, b) => b.total_upb - a.total_upb)
    .slice(0, 10)

  // Derive maturity data with formatted X-axis labels (per D-14)
  const maturityData = (maturity.data?.periods ?? []).map(p => ({
    ...p,
    label: `${p.year} Q${p.quarter}`,
  }))

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 gap-6">

      {/* Panel 1: Property Type donut — top-left (per D-11, D-12) */}
      <ChartCard
        title="Property Type"
        isLoading={concentration.isLoading}
        isEmpty={!concentration.data?.property_type?.length}
      >
        <ResponsiveContainer width="100%" height={280}>
          <PieChart>
            <Pie
              data={concentration.data?.property_type ?? []}
              dataKey="total_upb"
              nameKey="category"
              cx="50%"
              cy="50%"
              innerRadius={60}
              outerRadius={100}
              onClick={(entry) => { if (entry && 'category' in entry) setFilter('property_type', (entry as unknown as ConcentrationItem).category) }}
              style={{ cursor: 'pointer' }}
            >
              {(concentration.data?.property_type ?? []).map((_, i) => (
                <Cell key={i} fill={PIE_COLORS[i % PIE_COLORS.length]} />
              ))}
            </Pie>
            <Tooltip />
          </PieChart>
        </ResponsiveContainer>
      </ChartCard>

      {/* Panel 2: Top States horizontal bar — top-right (per D-03, D-04, D-05) */}
      <ChartCard
        title="Top States by UPB"
        isLoading={concentration.isLoading}
        isEmpty={!topStates.length}
      >
        <ResponsiveContainer width="100%" height={280}>
          <BarChart data={topStates} layout="vertical" margin={{ left: 40 }}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis type="number" />
            <YAxis type="category" dataKey="category" tick={{ fontSize: 11 }} width={40} />
            <Tooltip />
            <Bar
              dataKey="total_upb"
              fill="#2563eb"
              onClick={(entry) => { if (entry && 'category' in entry) setFilter('state', (entry as unknown as ConcentrationItem).category) }}
              style={{ cursor: 'pointer' }}
            />
          </BarChart>
        </ResponsiveContainer>
      </ChartCard>

      {/* Panel 3: Loan Size histogram — middle-left (per D-11, D-13) */}
      <ChartCard
        title="Loan Size Distribution"
        isLoading={distributions.isLoading}
        isEmpty={!distributions.data?.loan_size_distribution?.length}
      >
        <ResponsiveContainer width="100%" height={280}>
          <BarChart data={distributions.data?.loan_size_distribution ?? []}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis dataKey="bucket" tick={{ fontSize: 11 }} />
            <YAxis />
            <Tooltip />
            <Bar dataKey="loan_count" fill="#1a3868" />
          </BarChart>
        </ResponsiveContainer>
      </ChartCard>

      {/* Panel 4: Maturity Profile stacked bar — middle-right (per D-11, D-14) */}
      <ChartCard
        title="Maturity Profile"
        isLoading={maturity.isLoading}
        isEmpty={!maturityData.length}
      >
        <ResponsiveContainer width="100%" height={280}>
          <BarChart data={maturityData}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis dataKey="label" tick={{ fontSize: 11 }} />
            <YAxis />
            <Tooltip />
            <Bar dataKey="total_upb" stackId="maturity" fill="#1a3868" />
          </BarChart>
        </ResponsiveContainer>
      </ChartCard>

      {/* Panel 5: Top-10 Exposures table — full width — Plan 03 */}
      <ChartCard title="Top-10 Exposures" isLoading={false} isEmpty={true} colSpan="full" />

      {/* Panel 6: Concentration Limits — full width — Plan 03 */}
      <ChartCard title="Concentration Limits" isLoading={false} isEmpty={true} colSpan="full" />

    </div>
  )
}
