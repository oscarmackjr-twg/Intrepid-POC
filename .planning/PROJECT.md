# Intrepid Loan Purchase Platform

## What This Is

An internal operations dashboard for processing loan purchase opportunities. The Ops team uses it to ingest loan spreadsheets, run suitability analysis, tag loans to counterparties, calculate cashflows, and generate wire instruction PDFs — all through a controlled, step-by-step UI backed by Python processing logic.

## Core Value

Ops can take a loan tape from email to executed wire instructions in a single, auditable workflow — replacing ad hoc scripts with a controlled, visible process.

## Requirements

### Validated

(None yet — ship to validate)

### Active

- [ ] Ops team can upload loan spreadsheets (2 files, ~500 loans each) downloaded from email
- [ ] Python workflow processes loans against rule-based suitability criteria
- [ ] Loans are tagged to up to two counterparties (prime and SFY)
- [ ] Cashflows are calculated per counterparty for eligible loans
- [ ] Wire instructions are generated as PDF documents
- [ ] PDFs are sent via email to the appropriate counterparty
- [ ] Ops team triggers each workflow step manually through the dashboard
- [ ] Full visibility into processing status at each stage

### Out of Scope

- Automated email ingestion (Ops manually downloads and uploads spreadsheets)
- Direct integration with banking APIs for wire execution (PDFs are the output)
- Counterparty portal / external user access — internal Ops tool only

## Context

- **Existing work:** Python scripts for suitability and cashflow logic already exist; the application wraps them with a React/Node UI layer
- **Frequency:** Runs approximately twice per working week when loan tapes arrive via email
- **Volume:** ~1,000 loans per processing run (two spreadsheets of ~500 each)
- **Counterparties:** Two — "prime" and "SFY" — loans may be tagged to one or both
- **Current pain:** No dashboard means no visibility into processing state; steps are run manually via scripts with no audit trail

## Constraints

- **Tech Stack:** React (frontend), Node.js (API/middleware), Python (processing logic), PostgreSQL (persistence) — stack is fixed
- **Infrastructure:** AWS via Terraform — deployment target is established
- **Processing:** Python workflow must remain the suitability/cashflow engine; Node orchestrates it
- **Users:** Internal Ops team only — no external access required for v1

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| React/Node/Python/Postgres stack | Pre-existing scaffolding | — Pending |
| AWS + Terraform deployment | Established infra approach | — Pending |
| Manual step-by-step UI control | Ops needs to review and approve at each stage | — Pending |
| PDF wire instructions via email | Existing counterparty process — no API integration needed | — Pending |

---
*Last updated: 2026-03-04 after initialization*
