# Deferred Items — Phase 12

## Pre-existing test failures (out of scope for 12-01)

### test_enrichment.py::TestEnrichBuyDf::test_merge_with_loan_types

- **Status:** Pre-existing failure, present before plan 12-01 changes
- **File:** `backend/tests/test_enrichment.py` line 142
- **Error:** `assert 'type' in result.columns or 'platform' in result.columns`
- **Root cause:** `enrich_buy_df` merge with loan types does not produce a lowercase `platform` or `type` column in the result. The fixture `sample_loans_types_df` has both `Platform` (uppercase) and `platform` (lowercase) columns, but the merge result only carries the uppercase `Platform`. The assertion checks for the lowercase variant which is absent.
- **Scope:** This is in `test_enrichment.py`, not one of the 4 files targeted by plan 12-01. Will be addressed in plan 12-02 (new coverage expansion).
