import { create } from 'zustand'
import type { ReLoanFilters } from '../types/re'

interface FilterStore {
  filters: ReLoanFilters
  setFilters: (filters: ReLoanFilters) => void
  resetFilters: () => void
}

export const DEFAULT_FILTERS: ReLoanFilters = {
  as_of_date: null,
  property_type: null,
  state: null,
  msa: null,
  loan_size_min: null,
  loan_size_max: null,
  risk_rating: null,
  vintage_year: null,
  borrower: null,
  rate_type: null,
}

export const useFilterStore = create<FilterStore>()((set) => ({
  filters: DEFAULT_FILTERS,
  setFilters: (filters) => set({ filters }),
  resetFilters: () => set({ filters: DEFAULT_FILTERS }),
}))
