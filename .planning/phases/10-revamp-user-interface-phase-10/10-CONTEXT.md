# Phase 10: Revamp User Interface - Context

**Gathered:** 2026-03-13
**Status:** Ready for planning

<domain>
## Phase Boundary

Redesign the look, feel, and navigation of the existing ops dashboard to align with TWG Global brand guidelines. Covers all pages (Dashboard, Program Runs, Pipeline Runs, Exceptions, Rejected Loans, File Manager, Cash Flow, Holiday Maintenance, Login, Run Detail). Deliverables: new Layout component with left sidebar, TWG Global branding applied throughout, and updated navigation structure. No new data features or page capabilities — visual and structural changes only.

</domain>

<decisions>
## Implementation Decisions

### App name
- Rename from "Loan Engine" to **"Intrepid Loan Platform"** in the UI (nav header, page title, login page)

### Visual identity
- **Primary brand color:** TWG Global navy blue — `#1a3868` (sampled from TWG_logo_small.png)
- **Accent / interactive color:** Same navy `#1a3868` — monochromatic palette; no secondary accent
- **Background:** White (`#ffffff`) for content areas; very light gray (`#f8fafc`) for page background
- **Text:** Near-black (`#1e293b` / slate-900) for body; navy for headings and active states
- **Typography:** Gotham (Book + Bold) — per TWG_GLOBAL_Guidelines_v1.0_07072025.pdf. Use `font-family: 'Gotham', sans-serif` with web fallback `system-ui, -apple-system, sans-serif`
- **Logo:** TWG Global logo image — source from `C:/Users/omack/OneDrive - TWG/Pictures/TWG_logo_small.png`; copy into `frontend/src/assets/twg-logo.png` before execution

### Navigation structure
- **Layout:** Replace horizontal top nav with a **fixed-width left sidebar** (always expanded, not collapsible)
- **Sidebar nav items (in order):**
  1. Dashboard
  2. Program Runs
  3. **SG** (group label, non-clickable)
     - Final Funding SG
     - Cash Flow SG
  4. **CIBC** (group label, non-clickable)
     - Final Funding CIBC
     - Cash Flow CIBC
  5. File Manager
  6. *(admin only)* Cash Flow
  7. *(admin only)* Holiday Maintenance
- **Removed from nav:** Exceptions, Rejected Loans, Pipeline Runs
  - Pipeline Runs removed: redundant with Dashboard (all run history visible there)
  - Exceptions and Rejected Loans removed: no longer needed as standalone nav items
- **Active state:** Navy left border + navy text on active item; subtle gray bg on hover
- **TWG Global logo** at top of sidebar above nav items
- **User info + Logout** at bottom of sidebar

### StagingBanner
- Amber staging banner must remain — rendered above the sidebar/content, spanning full width

### Claude's Discretion
- Exact sidebar width (suggested: 220-240px)
- Icon choice for nav items (small icons optional, text-only acceptable)
- Whether to use a component library (shadcn/ui or raw Tailwind — Claude decides based on build complexity)
- Exact Gotham font loading strategy (Google Fonts approximation vs self-hosted if Gotham is unavailable as web font)
- Card shadow and border-radius values
- Spacing scale

</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets
- `frontend/src/components/Layout.tsx`: Current layout component — this is the primary file to replace. Horizontal nav becomes left sidebar here.
- `frontend/src/components/StagingBanner.tsx`: Amber banner — must be kept, position above sidebar
- `frontend/src/contexts/AuthContext.tsx`: Provides `user.role` for admin-only nav items — already wired
- `frontend/src/App.tsx`: Route definitions — routes for removed pages (Exceptions, Rejected Loans, Pipeline Runs) may remain but are removed from sidebar

### Established Patterns
- Tailwind CSS throughout — all styling is utility class-based
- `max-w-7xl mx-auto` content container — will change to full-width minus sidebar
- `bg-white shadow rounded-lg` card pattern used on all pages — consistent, keep it
- Admin-gated items already handled: `user?.role === 'admin'` conditional in Layout.tsx (line 19-27)

### Integration Points
- `frontend/src/components/Layout.tsx` → wraps all authenticated pages via React Router `<Outlet />`
- `frontend/src/pages/ProgramRuns.tsx` → will gain "SG" and "CIBC" sub-nav context (or separate Final Funding / Cash Flow pages — planner decides)
- No backend changes required — this is a pure frontend visual change

### Logo Asset
- Logo source: `C:/Users/omack/OneDrive - TWG/Pictures/TWG_logo_small.png`
- Destination: `frontend/src/assets/twg-logo.png`
- Used in: sidebar header in Layout.tsx

</code_context>

<specifics>
## Specific Ideas

- Logo is "TWG GLOBAL" in deep navy serif (TWG large, GLOBAL smaller with line separator beneath TWG) — should sit at top of sidebar, white background, with some padding
- Brand is conservative financial — clean spacing, no gradients, no drop shadows on sidebar itself
- The sidebar should feel like a Bloomberg or financial terminal sidebar — authoritative, not playful
- Active nav item: navy left-border highlight (4px) + navy text weight bump (font-semibold)

</specifics>

<deferred>
## Deferred Ideas

- Exceptions page and Rejected Loans page still exist as routes — could be re-added to nav in a future phase if needed
- Pipeline Runs page still exists as a route — accessible by direct URL even if removed from nav
- Collapsible/icon-only sidebar mode — deferred to future phase
- Dark mode — out of scope

</deferred>

---

*Phase: 10-revamp-user-interface-phase-10*
*Context gathered: 2026-03-13*
