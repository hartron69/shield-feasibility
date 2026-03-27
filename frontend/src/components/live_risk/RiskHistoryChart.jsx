import React, { useState, useCallback } from 'react'

// Pure SVG multi-line chart showing domain risk scores and total over time
// Domains: biological, structural, environmental, operational + total (black)

const MARGIN = { top: 20, right: 20, bottom: 40, left: 50 }
const W = 480
const H = 200

const DOMAIN_CONFIG = {
  biological:    { color: '#3A86FF', label: 'Biologisk' },
  structural:    { color: '#FF6B6B', label: 'Strukturell' },
  environmental: { color: '#36A271', label: 'Miljø' },
  operational:   { color: '#F4A620', label: 'Operasjonell' },
}
const TOTAL_COLOR = '#111827'

const innerW = W - MARGIN.left - MARGIN.right
const innerH = H - MARGIN.top - MARGIN.bottom

function formatDateLabel(isoStr) {
  const d = new Date(isoStr)
  return `${d.getDate()}. ${d.toLocaleString('nb-NO', { month: 'short' })}`
}

function formatTooltipDate(isoStr) {
  const d = new Date(isoStr)
  return d.toLocaleDateString('nb-NO', { day: '2-digit', month: 'short', year: 'numeric' })
}

export default function RiskHistoryChart({ history = [], period = '30d' }) {
  const [tooltip, setTooltip] = useState(null)

  if (!history || history.length === 0) {
    return (
      <div className="lr-chart-empty" style={{ height: H + 50, display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#888' }}>
        Ingen risikohistorikk tilgjengelig
      </div>
    )
  }

  const timestamps = history.map(p => new Date(p.timestamp).getTime())
  const tMin = Math.min(...timestamps)
  const tMax = Math.max(...timestamps)

  const xScale = (ts) => ((ts - tMin) / (tMax - tMin || 1)) * innerW + MARGIN.left
  const yScale = (v)  => MARGIN.top + innerH - (Math.max(0, Math.min(100, v)) / 100) * innerH

  // X-axis ticks
  const xTickCount = 5
  const xTicks = Array.from({ length: xTickCount }, (_, i) => tMin + (i / (xTickCount - 1)) * (tMax - tMin))

  // Y-axis ticks at 0, 25, 50, 75, 100
  const yTicks = [0, 25, 50, 75, 100]

  // Build path string for a given value accessor
  const buildPath = (accessor) => {
    return history
      .map((p, i) => {
        const v = accessor(p)
        if (v == null) return null
        const x = xScale(new Date(p.timestamp).getTime())
        const y = yScale(v)
        return `${i === 0 ? 'M' : 'L'}${x.toFixed(1)},${y.toFixed(1)}`
      })
      .filter(Boolean)
      .join(' ')
  }

  const domains = Object.keys(DOMAIN_CONFIG)

  const handleMouseMove = useCallback((e) => {
    const svg = e.currentTarget
    const rect = svg.getBoundingClientRect()
    const mx = (e.clientX - rect.left) * (W / rect.width)
    // Find nearest data point
    let best = null
    let bestDist = Infinity
    history.forEach(p => {
      const px = xScale(new Date(p.timestamp).getTime())
      const d = Math.abs(px - mx)
      if (d < bestDist) { bestDist = d; best = p }
    })
    if (best && bestDist < 30) {
      const px = xScale(new Date(best.timestamp).getTime())
      setTooltip({ x: px, point: best })
    } else {
      setTooltip(null)
    }
  }, [history, xScale])

  const legendH = 24

  return (
    <div className="lr-risk-history-chart" style={{ position: 'relative', userSelect: 'none' }}>
      <svg
        viewBox={`0 0 ${W} ${H + legendH}`}
        style={{ width: '100%', display: 'block' }}
        onMouseMove={handleMouseMove}
        onMouseLeave={() => setTooltip(null)}
      >
        {/* Y-axis gridlines and labels */}
        {yTicks.map((v) => {
          const y = yScale(v)
          return (
            <g key={v}>
              <line x1={MARGIN.left} y1={y} x2={MARGIN.left + innerW} y2={y} stroke="#e5e7eb" strokeWidth={1} />
              <text x={MARGIN.left - 6} y={y + 4} textAnchor="end" fontSize={10} fill="#6b7280">{v}</text>
            </g>
          )
        })}

        {/* X-axis ticks */}
        {xTicks.map((ts, i) => {
          const x = xScale(ts)
          return (
            <g key={i}>
              <text x={x} y={MARGIN.top + innerH + 14} textAnchor="middle" fontSize={10} fill="#6b7280">
                {formatDateLabel(new Date(ts).toISOString())}
              </text>
            </g>
          )
        })}

        {/* Axes */}
        <line x1={MARGIN.left} y1={MARGIN.top} x2={MARGIN.left} y2={MARGIN.top + innerH} stroke="#d1d5db" strokeWidth={1} />
        <line x1={MARGIN.left} y1={MARGIN.top + innerH} x2={MARGIN.left + innerW} y2={MARGIN.top + innerH} stroke="#d1d5db" strokeWidth={1} />

        {/* Domain lines */}
        {domains.map(domain => (
          <path
            key={domain}
            d={buildPath(p => p[domain])}
            fill="none"
            stroke={DOMAIN_CONFIG[domain].color}
            strokeWidth={1.8}
            strokeLinejoin="round"
            strokeLinecap="round"
          />
        ))}

        {/* Total risk line — thicker, dark */}
        <path
          d={buildPath(p => p.total)}
          fill="none"
          stroke={TOTAL_COLOR}
          strokeWidth={2.5}
          strokeLinejoin="round"
          strokeLinecap="round"
        />

        {/* Tooltip */}
        {tooltip && (() => {
          const p = tooltip.point
          const rows = [
            { label: 'Total', value: p.total, color: TOTAL_COLOR },
            ...domains.map(d => ({ label: DOMAIN_CONFIG[d].label, value: p[d], color: DOMAIN_CONFIG[d].color })),
          ].filter(r => r.value != null)

          const bw = 130
          const bh = 14 + rows.length * 14
          const bx = Math.min(tooltip.x + 8, W - bw - 4)
          const by = MARGIN.top + 4

          return (
            <g>
              <line x1={tooltip.x} y1={MARGIN.top} x2={tooltip.x} y2={MARGIN.top + innerH} stroke="#6b7280" strokeWidth={1} strokeDasharray="3,2" />
              <rect x={bx} y={by} width={bw} height={bh} rx={4} fill="white" stroke="#d1d5db" strokeWidth={1} filter="drop-shadow(0 1px 3px rgba(0,0,0,0.15))" />
              <text x={bx + 6} y={by + 12} fontSize={10} fill="#374151">{formatTooltipDate(p.timestamp)}</text>
              {rows.map((r, ri) => (
                <text key={ri} x={bx + 6} y={by + 12 + (ri + 1) * 13} fontSize={10} fill={r.color} fontWeight={r.label === 'Total' ? 700 : 400}>
                  {r.label}: {r.value != null ? Math.round(r.value) : '—'}
                </text>
              ))}
            </g>
          )
        })()}

        {/* Legend */}
        {[...domains, 'total'].map((key, i) => {
          const cfg = key === 'total' ? { color: TOTAL_COLOR, label: 'Total' } : DOMAIN_CONFIG[key]
          const lx = MARGIN.left + i * 88
          const ly = H + 10
          return (
            <g key={key}>
              <line x1={lx} y1={ly} x2={lx + 18} y2={ly}
                stroke={cfg.color}
                strokeWidth={key === 'total' ? 2.5 : 1.8}
              />
              <text x={lx + 22} y={ly + 4} fontSize={10} fill="#374151">{cfg.label}</text>
            </g>
          )
        })}
      </svg>
    </div>
  )
}
