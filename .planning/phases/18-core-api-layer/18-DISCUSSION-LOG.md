# Phase 18: Core API Layer — Discussion Log

**Session:** 2026-04-08
**Workflow:** /gsd-discuss-phase 18

---

## Areas Discussed

### Router Organization

**Q:** Where should the 11 /api/re/* endpoints live?
- Options: New re_routes.py / Add to existing routes.py
- **Answer:** New re_routes.py (dedicated file, register in main.py)

---

### Filter Query Params

**Q:** How should the global filter params be handled across all /api/re/* endpoints?
- Options: Shared FilterParams dependency / Individual Query() params per endpoint / You decide
- **Answer:** Shared FilterParams dependency

**Q:** Which filter fields should be included in the shared FilterParams?
- Options: Full set from REQUIREMENTS.md / Minimal set for Phase 18 / You decide
- **Answer:** Full set from REQUIREMENTS.md (as_of_date, property_type, state/MSA, loan_size_min/max, risk_rating, vintage_year, borrower, rate_type)

---

### Loans List Pagination

**Q:** How should /api/re/loans paginate the loan list?
- Options: offset/limit / Cursor-based / No pagination
- **Answer:** offset/limit

**Q:** What should the default page size be, and what metadata should the response include?
- Options: page_size=50 return total+items / page_size=25 return total+items / You decide
- **Answer:** page_size=50, return total + items (`{total, page, page_size, items}`)

---

### Aggregation Strategy

**Q:** Where should KPI metrics be computed?
- Options: SQL aggregations / Python post-processing / Hybrid
- **Answer:** SQL aggregations (SQLAlchemy func.sum/func.avg with UPB-weighting)

**Q:** Should Pydantic response models be in a shared schema file or inline in re_routes.py?
- Options: Shared re_schemas.py file / Inline in re_routes.py
- **Answer:** Shared re_schemas.py file (backend/api/re_schemas.py)

---

*For human reference only — not consumed by downstream agents*
