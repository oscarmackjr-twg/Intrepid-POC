/**
 * Number formatting utilities for KPI cards.
 * All functions return an en-dash ("\u2013") for null inputs.
 */

/** Format a UPB (dollar) value: >=1B -> $X.XXB, >=1M -> $X.Xm, else $X,XXX */
export function formatUPB(value: number | null): string {
  if (value === null) return '\u2013'
  if (value >= 1_000_000_000) {
    return `$${(value / 1_000_000_000).toFixed(2)}B`
  }
  if (value >= 1_000_000) {
    return `$${(value / 1_000_000).toFixed(1)}m`
  }
  return `$${value.toLocaleString('en-US')}`
}

/** Format a rate or percentage: "x.xx%" */
export function formatRate(value: number | null): string {
  if (value === null) return '\u2013'
  return `${value.toFixed(2)}%`
}

/** Format a WAM in months: "xmo" */
export function formatWAM(value: number | null): string {
  if (value === null) return '\u2013'
  return `${Math.round(value)}mo`
}

/** Format a DSCR: "x.xxX" */
export function formatDSCR(value: number | null): string {
  if (value === null) return '\u2013'
  return `${value.toFixed(2)}x`
}

/** Format an integer count with comma separators */
export function formatCount(value: number | null): string {
  if (value === null) return '\u2013'
  return Math.round(value).toLocaleString('en-US')
}
