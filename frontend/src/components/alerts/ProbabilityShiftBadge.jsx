import React from 'react'

export default function ProbabilityShiftBadge({ delta, current }) {
  if (delta == null) return null
  const isUp = delta > 0.005
  const isDown = delta < -0.005
  const sign = isUp ? '+' : ''
  const cls = isUp ? 'shift-up' : isDown ? 'shift-down' : 'shift-neutral'
  const arrow = isUp ? '\u2191' : isDown ? '\u2193' : '\u2192'

  return (
    <span className={`prob-shift-badge ${cls}`}>
      {arrow} {sign}{(delta * 100).toFixed(1)}pp
      {current != null && (
        <span className="prob-shift-current"> ({(current * 100).toFixed(0)}%)</span>
      )}
    </span>
  )
}
