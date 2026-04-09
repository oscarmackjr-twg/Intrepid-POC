import { useCallback, useEffect } from 'react'
import { useSearchParams } from 'react-router-dom'
import { useFilterStore } from '../stores/filterStore'
import type { ReLoanFilters } from '../types/re'

function parseFiltersFromParams(searchParams: URLSearchParams): ReLoanFilters {
  return {
    as_of_date: searchParams.get('as_of_date'),
    property_type: searchParams.get('property_type'),
    state: searchParams.get('state'),
    msa: searchParams.get('msa'),
    loan_size_min: searchParams.has('loan_size_min')
      ? Number(searchParams.get('loan_size_min'))
      : null,
    loan_size_max: searchParams.has('loan_size_max')
      ? Number(searchParams.get('loan_size_max'))
      : null,
    risk_rating: searchParams.get('risk_rating'),
    vintage_year: searchParams.get('vintage_year'),
    borrower: searchParams.get('borrower'),
    rate_type: searchParams.get('rate_type'),
  }
}

export function useReLoanFilters() {
  const [searchParams, setSearchParams] = useSearchParams()
  const setFilters = useFilterStore((s) => s.setFilters)
  const resetFilters = useFilterStore((s) => s.resetFilters)

  // Derive filters from URL on every render — URL is authoritative (D-07)
  const filters = parseFiltersFromParams(searchParams)

  // Sync URL-derived filters into Zustand store (D-08)
  useEffect(() => {
    setFilters(filters)
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [searchParams, setFilters])

  // Set a single filter — updates URL, which triggers re-derive + Zustand sync (D-09)
  const setFilter = useCallback(
    (key: keyof ReLoanFilters, value: string | number | null) => {
      const next = new URLSearchParams(searchParams)
      if (value === null || value === '') {
        next.delete(key)
      } else {
        next.set(key, String(value))
      }
      setSearchParams(next)
    },
    [searchParams, setSearchParams]
  )

  // Clear all filters — reset URL and Zustand in one action (D-10)
  const clearFilters = useCallback(() => {
    setSearchParams({})
    resetFilters()
  }, [setSearchParams, resetFilters])

  return { filters, setFilter, clearFilters }
}
