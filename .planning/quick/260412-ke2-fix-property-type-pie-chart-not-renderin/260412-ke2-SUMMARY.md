---
quick_id: 260412-ke2
one_liner: "Fixed property type Pie chart not rendering by disabling Recharts 3 animation and adding default fill"
status: complete
key_files:
  modified:
    - frontend/src/pages/RePortfolioPage.tsx
---

## What was done

The property type Pie chart on the RE Portfolio page showed the legend but no pie arcs. Root cause: Recharts 3.8.1's Pie component uses a new state-store architecture with `JavascriptAnimate` defaulting to `isAnimationActive: 'auto'`, `animationBegin: 400ms`, `animationDuration: 1500ms`. The animation pipeline fails to properly initialize sectors when combined with ResponsiveContainer dimension propagation through the Redux-like store.

**Fix:** Added `isAnimationActive={false}` to render sectors immediately (bypassing the animation pipeline) and `fill="#1a3868"` as a default fill color (safety net if Cell children aren't applied).

## Verification

- `npx tsc --noEmit` passes
- Commit: ce56e95
