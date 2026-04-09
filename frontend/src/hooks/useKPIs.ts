import { useQuery } from '@tanstack/react-query'
import axios from 'axios'
import type { KPIResponse } from '../types/re'
import { useReLoanFilters } from './useReLoanFilters'

export function useKPIs() {
  const { filters } = useReLoanFilters()

  // Strip null/empty values before sending as query params
  const params = Object.fromEntries(
    Object.entries(filters).filter(([, v]) => v !== null && v !== '')
  )

  return useQuery({
    // Full filters object as key — any filter change triggers automatic refetch (per D-05)
    queryKey: ['re-kpis', filters],
    queryFn: async () => {
      const { data } = await axios.get<KPIResponse>('/api/re/kpis', { params })
      return data
    },
  })
}
