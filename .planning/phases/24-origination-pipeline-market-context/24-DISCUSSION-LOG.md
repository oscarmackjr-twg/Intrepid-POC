# Phase 24: Origination Pipeline + Market Context - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-04-12
**Phase:** 24-origination-pipeline-market-context
**Areas discussed:** Page structure, Chart types & interactions, Market Context presentation, Net growth metric

---

## Page Structure

| Option | Description | Selected |
|--------|-------------|----------|
| Single page (Recommended) | One ReOriginationPage with origination panels on top and Market Context section below | ✓ |
| Two separate tabs | Origination at /origination and Market Context at /market — adds a new tab | |
| You decide | Claude picks the layout | |

**User's choice:** Single page
**Notes:** Matches ROADMAP scope (Phase 24 covers both). Keeps it simple.

---

## Origination Volume Chart Type

| Option | Description | Selected |
|--------|-------------|----------|
| Stacked bar (Recommended) | Each bar = one month, segments = property types stacked | ✓ |
| Grouped bar | Side-by-side bars per property type per month | |
| Line chart | One line per property type | |

**User's choice:** Stacked bar
**Notes:** Consistent with maturity profile chart in Portfolio page.

## Pipeline Funnel Chart Type

| Option | Description | Selected |
|--------|-------------|----------|
| Horizontal bar chart (Recommended) | 4 horizontal bars, widest at top, narrowing to funded | ✓ |
| Vertical stacked bar | Single tall bar with 4 colored segments | |
| You decide | Claude picks | |

**User's choice:** Horizontal bar chart
**Notes:** Shows count + UPB per stage.

## Vintage Analysis Display

| Option | Description | Selected |
|--------|-------------|----------|
| Table (Recommended) | Rows = vintage years, columns = loan count, UPB, avg LTV, avg DSCR, avg rate | ✓ |
| Grouped bar chart | Bars per vintage year showing UPB with LTV/DSCR overlaid line | |
| You decide | Claude picks | |

**User's choice:** Table
**Notes:** Matches TopExposuresTable pattern from Portfolio page.

## Click-to-Filter Scope

| Option | Description | Selected |
|--------|-------------|----------|
| Origination volume only (Recommended) | Click property type segment to filter. Other panels display-only. | ✓ |
| Volume + vintage | Also allow clicking vintage year rows to filter | |
| All panels | Every chart segment clickable | |

**User's choice:** Origination volume only
**Notes:** Pipeline funnel stages and vintage years don't map cleanly to useful filters.

---

## Market Context Presentation

| Option | Description | Selected |
|--------|-------------|----------|
| KPI cards + table (Recommended) | Two cards for Treasury/SOFR, then table for cap/vacancy rates | ✓ |
| All-table format | Everything in one table | |
| You decide | Claude picks | |

**User's choice:** KPI cards + table
**Notes:** Consistent with KPI card pattern from Executive Summary.

## Disclaimer Prominence

| Option | Description | Selected |
|--------|-------------|----------|
| Section subtitle (Recommended) | Muted text below heading: "Indicative values — not connected to live feeds" | ✓ |
| Per-card badge | Small 'STUB' badge on each card | |
| Banner alert | Yellow warning banner above section | |

**User's choice:** Section subtitle
**Notes:** Visible but not distracting.

---

## Net Growth Metric

| Option | Description | Selected |
|--------|-------------|----------|
| Single KPI card (Recommended) | Summary card showing gross origination volume. Payoffs deferred. | ✓ |
| Dual bar chart | Side-by-side originations vs payoffs per month. Requires schema addition. | |
| You decide | Claude picks simplest approach | |

**User's choice:** Single KPI card
**Notes:** Payoff tracking not in current schema. POC shows net origination volume only, clearly labeled.

---

## Claude's Discretion

- Color palette for stacked bar property type segments
- Grid gap/spacing between panels
- Loading and empty state patterns

## Deferred Ideas

None — discussion stayed within phase scope.
