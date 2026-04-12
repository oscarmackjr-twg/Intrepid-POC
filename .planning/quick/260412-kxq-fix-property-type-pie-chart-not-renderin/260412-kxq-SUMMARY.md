---
quick_id: 260412-kxq
one_liner: "Fixed PieChart not rendering by adding fallback width/height props for Recharts 3 NonResponsiveDiv initial render"
status: complete
key_files:
  modified:
    - frontend/src/pages/RePortfolioPage.tsx
---

## What was done

Follow-up to 260412-ke2 — the `isAnimationActive={false}` fix didn't resolve the issue. Root cause analysis of Recharts 3.8.1 internals revealed:

1. `PolarChart` (PieChart's base) defaults `responsive: false`
2. This makes `CategoricalChart` use `NonResponsiveDiv` wrapper
3. `NonResponsiveDiv` needs explicit numeric `width` AND `height` props to render SVG
4. `ResponsiveContainer` in Recharts 3 passes dimensions via React context only (NOT via cloneElement/props)
5. On initial render, context has `width: -1` (before ResizeObserver fires), `widthFromProps` is undefined
6. `NonResponsiveDiv` hits the "undefined dimensions" branch → renders no SVG
7. Legend still renders because `SetPiePayloadLegend` reads data directly, not via the store's dimension-dependent selectors
8. BarChart works because bar rendering doesn't depend on store-computed coordinates like Pie sectors do

**Fix:** Added `width={400} height={320}` as explicit props on `PieChart`. These serve as fallback dimensions in `RechartsWrapper` until `ResponsiveContainer`'s ResizeObserver fires and context provides actual measured width. After that, context values take precedence (the `> 0` check).

## Verification

- `npx tsc --noEmit` passes
- Commit: e759fbb
