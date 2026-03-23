---
created: 2026-03-23T13:27:33.185Z
title: Integrate updated tagging allocation ratios and dynamic SG logic
area: general
files:
  - backend/scripts/tagging.py
  - backend/orchestration/tagging_runner.py
  - C:/Users/omack/Downloads/tagging_new.py
---

## Problem

The tagging step (splits loans into SG vs CIBC groups) has new requirements captured in `tagging_new.py` (external reference file). The current `backend/scripts/tagging.py` uses outdated allocation ratios and a hardcoded SG dict. Changes must be integrated, tested, and documented.

**Key differences (tagging_new.py vs current tagging.py):**

1. **Allocation ratios changed:**
   - PRIME ratio `p`: `0.30` → `0.325`
   - SFY ratio `s`: `0.60` → `0.50`

2. **SG dict now built dynamically:** New code iterates over `grouped_sum.keys()` and assigns ratios by tag group membership (PRIME set, SFY set, `_bd` set = 0). Current code hardcodes every expected tag key explicitly.

3. **Latent KeyError bug in tagging_new.py:** The allocation loop removes the `in sg` guard — tags that fall through `pass` in the dynamic build are absent from `sg` and would raise a `KeyError`. Must add a guard (`if tag in sg and sg[tag] > 0`) during integration.

4. **Hard-coded paths in tagging_new.py are ignored** — the app reads paths from environment variables (`FOLDER`, `PDATE`, `IRR_TARGET`).

## Solution

1. Update `backend/scripts/tagging.py`:
   - Change `p = 0.3` → `p = 0.325` and `s = 0.6` → `s = 0.5`
   - Replace hardcoded `sg` dict with dynamic loop over `grouped_sum.keys()`
   - Keep `if tag in sg and sg[tag] > 0` guard in allocation loop (fix the latent bug)
   - Remove `_tag_target` helper (no longer needed)

2. Update unit tests for the tagging logic (ratio assertions, dynamic tag handling)

3. Run regression tests to validate output against golden files (may need `--update-golden` if allocation outputs change)

4. Update developer reference documentation in `docs/`
