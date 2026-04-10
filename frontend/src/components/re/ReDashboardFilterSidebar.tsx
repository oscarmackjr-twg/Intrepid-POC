import { useReLoanFilters } from '../../hooks/useReLoanFilters'

const US_STATES = [
  'AL', 'AK', 'AZ', 'AR', 'CA', 'CO', 'CT', 'DE', 'FL', 'GA',
  'HI', 'ID', 'IL', 'IN', 'IA', 'KS', 'KY', 'LA', 'ME', 'MD',
  'MA', 'MI', 'MN', 'MS', 'MO', 'MT', 'NE', 'NV', 'NH', 'NJ',
  'NM', 'NY', 'NC', 'ND', 'OH', 'OK', 'OR', 'PA', 'RI', 'SC',
  'SD', 'TN', 'TX', 'UT', 'VT', 'VA', 'WA', 'WV', 'WI', 'WY', 'DC',
]

const LABEL_CLASS = 'text-xs font-semibold text-[#475569] uppercase tracking-wide mb-1 block'
const CONTROL_CLASS =
  'w-full rounded border border-gray-200 px-2 py-1.5 text-sm text-[#475569] focus:outline-none focus:border-[#1a3868]'

export function ReDashboardFilterSidebar() {
  const { filters, setFilter, clearFilters } = useReLoanFilters()

  return (
    <aside className="w-72 shrink-0 bg-white border-l border-gray-200 p-4">
      {/* Header */}
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-sm font-bold text-[#1a3868] uppercase tracking-wide">Filters</h2>
        <button
          onClick={clearFilters}
          className="text-xs text-[#1a3868] hover:underline"
        >
          Clear all
        </button>
      </div>

      <div className="space-y-4">
        {/* As-of Date */}
        <div>
          <label className={LABEL_CLASS}>As-of Date</label>
          <input
            type="date"
            className={CONTROL_CLASS}
            value={filters.as_of_date ?? ''}
            onChange={(e) => setFilter('as_of_date', e.target.value || null)}
          />
        </div>

        {/* Property Type */}
        <div>
          <label className={LABEL_CLASS}>Property Type</label>
          <select
            className={CONTROL_CLASS}
            value={filters.property_type ?? ''}
            onChange={(e) => setFilter('property_type', e.target.value || null)}
          >
            <option value="">All</option>
            <option value="multifamily">Multifamily</option>
            <option value="office">Office</option>
            <option value="retail">Retail</option>
            <option value="industrial">Industrial</option>
            <option value="mixed-use">Mixed-Use</option>
            <option value="hospitality">Hospitality</option>
          </select>
        </div>

        {/* State */}
        <div>
          <label className={LABEL_CLASS}>State</label>
          <select
            className={CONTROL_CLASS}
            value={filters.state ?? ''}
            onChange={(e) => setFilter('state', e.target.value || null)}
          >
            <option value="">All</option>
            {US_STATES.map((s) => (
              <option key={s} value={s}>
                {s}
              </option>
            ))}
          </select>
        </div>

        {/* MSA */}
        <div>
          <label className={LABEL_CLASS}>MSA</label>
          <select
            className={CONTROL_CLASS}
            value={filters.msa ?? ''}
            onChange={(e) => setFilter('msa', e.target.value || null)}
          >
            <option value="">All</option>
            <option value="New York">New York</option>
            <option value="Los Angeles">Los Angeles</option>
            <option value="Chicago">Chicago</option>
            <option value="Dallas">Dallas</option>
            <option value="Houston">Houston</option>
            <option value="Washington DC">Washington DC</option>
            <option value="Miami">Miami</option>
            <option value="Philadelphia">Philadelphia</option>
            <option value="Atlanta">Atlanta</option>
            <option value="Boston">Boston</option>
          </select>
        </div>

        {/* Loan Size (UPB) min/max pair */}
        <div>
          <label className={LABEL_CLASS}>Loan Size (UPB)</label>
          <div className="flex gap-2">
            <input
              type="number"
              placeholder="Min UPB"
              className={CONTROL_CLASS}
              value={filters.loan_size_min ?? ''}
              onChange={(e) =>
                setFilter('loan_size_min', e.target.value ? Number(e.target.value) : null)
              }
            />
            <input
              type="number"
              placeholder="Max UPB"
              className={CONTROL_CLASS}
              value={filters.loan_size_max ?? ''}
              onChange={(e) =>
                setFilter('loan_size_max', e.target.value ? Number(e.target.value) : null)
              }
            />
          </div>
        </div>

        {/* Risk Rating */}
        <div>
          <label className={LABEL_CLASS}>Risk Rating</label>
          <select
            className={CONTROL_CLASS}
            value={filters.risk_rating ?? ''}
            onChange={(e) => setFilter('risk_rating', e.target.value || null)}
          >
            <option value="">All</option>
            <option value="AAA">AAA</option>
            <option value="AA">AA</option>
            <option value="A">A</option>
            <option value="BBB">BBB</option>
            <option value="BB">BB</option>
            <option value="B">B</option>
            <option value="CCC">CCC</option>
          </select>
        </div>

        {/* Vintage Year */}
        <div>
          <label className={LABEL_CLASS}>Vintage Year</label>
          <select
            className={CONTROL_CLASS}
            value={filters.vintage_year ?? ''}
            onChange={(e) => setFilter('vintage_year', e.target.value || null)}
          >
            <option value="">All</option>
            <option value="2024">2024</option>
            <option value="2023">2023</option>
            <option value="2022">2022</option>
            <option value="2021">2021</option>
            <option value="2020">2020</option>
            <option value="2019">2019</option>
          </select>
        </div>

        {/* Borrower */}
        <div>
          <label className={LABEL_CLASS}>Borrower</label>
          <input
            type="text"
            placeholder="Search borrower..."
            className={CONTROL_CLASS}
            value={filters.borrower ?? ''}
            onChange={(e) => setFilter('borrower', e.target.value || null)}
          />
        </div>

        {/* Rate Type */}
        <div>
          <label className={LABEL_CLASS}>Rate Type</label>
          <select
            className={CONTROL_CLASS}
            value={filters.rate_type ?? ''}
            onChange={(e) => setFilter('rate_type', e.target.value || null)}
          >
            <option value="">All</option>
            <option value="Fixed">Fixed</option>
            <option value="Floating">Floating</option>
          </select>
        </div>
      </div>
    </aside>
  )
}
