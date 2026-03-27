import React, { useState, useCallback } from 'react'

// Pure SVG time-series chart — one panel per parameter with independent Y-scale.
// Supports: gaps (null values), estimated segments (dashed), missing dots, threshold line, hover tooltip.

const MARGIN = { top: 16, right: 16, bottom: 32, left: 52 }
const W = 480
const PANEL_H = 130  // height of each chart panel

function formatDateLabel(ts) {
  const d = new Date(ts)
  return `${d.getDate()}. ${d.toLocaleString('nb-NO', { month: 'short' })}`
}

function formatTooltipDate(isoStr) {
  const d = new Date(isoStr)
  return d.toLocaleDateString('nb-NO', { day: '2-digit', month: 'short', year: 'numeric' })
}

function buildPath(pts, xScale, yScale) {
  if (pts.length === 0) return ''
  return pts
    .map((p, i) => `${i === 0 ? 'M' : 'L'}${xScale(p.x).toFixed(1)},${yScale(p.y).toFixed(1)}`)
    .join(' ')
}

// Render one series panel
function SeriesPanel({ s, tMin, tMax, showXAxis }) {
  const [tooltip, setTooltip] = useState(null)

  const innerW = W - MARGIN.left - MARGIN.right
  const innerH = PANEL_H - MARGIN.top - MARGIN.bottom

  const pts = (s.points || []).map(p => ({
    ...p,
    x: new Date(p.timestamp).getTime(),
    y: p.value,
  }))

  const nonNull = pts.filter(p => p.value != null)
  const yVals = nonNull.map(p => p.y)
  if (s.threshold != null) yVals.push(s.threshold)

  const rawMin = yVals.length ? Math.min(...yVals) : 0
  const rawMax = yVals.length ? Math.max(...yVals) : 1
  const pad = (rawMax - rawMin) * 0.15 || 0.5
  const yMin = rawMin - pad
  const yMax = rawMax + pad

  const xRange = tMax - tMin || 1
  const xScale = ts => ((ts - tMin) / xRange) * innerW
  const yScale = v  => innerH - ((v - yMin) / (yMax - yMin)) * innerH

  // Split into segments by quality
  const segments = []
  let seg = [], segQ = null
  pts.forEach(p => {
    if (p.value == null) {
      if (seg.length) segments.push({ pts: seg, q: segQ })
      seg = []; segQ = null; return
    }
    const q = p.quality || 'observed'
    if (seg.length && q !== segQ) {
      segments.push({ pts: [...seg, p], q: segQ })
      seg = [p]; segQ = q
    } else {
      seg.push(p); segQ = q
    }
  })
  if (seg.length) segments.push({ pts: seg, q: segQ })

  // Y-axis ticks (3 ticks)
  const yTicks = [yMin + (yMax - yMin) * 0.1, yMin + (yMax - yMin) * 0.5, yMin + (yMax - yMin) * 0.9]
    .map(v => Math.round(v * 10) / 10)

  // X-axis ticks (5 evenly spaced)
  const xTicks = Array.from({ length: 5 }, (_, i) => tMin + (i / 4) * (tMax - tMin))

  const handleMouseMove = useCallback(e => {
    const svg = e.currentTarget
    const rect = svg.getBoundingClientRect()
    const mx = (e.clientX - rect.left) * (W / rect.width) - MARGIN.left
    let best = null, bestD = Infinity
    nonNull.forEach(p => {
      const d = Math.abs(xScale(p.x) - mx)
      if (d < bestD) { bestD = d; best = p }
    })
    if (best && bestD < 28) {
      setTooltip({
        x: xScale(best.x) + MARGIN.left,
        y: yScale(best.y) + MARGIN.top,
        point: best,
      })
    } else {
      setTooltip(null)
    }
  }, [nonNull, xScale, yScale])

  const isTreatment = s.parameter === 'treatment'

  return (
    <div style={{ marginBottom: 4, userSelect: 'none' }}>
      {/* Parameter label above panel */}
      <div style={{ fontSize: 11, fontWeight: 700, color: s.color || '#374151', marginBottom: 2, paddingLeft: MARGIN.left }}>
        {s.label}
        {s.unit && <span style={{ fontWeight: 400, color: '#9ca3af', marginLeft: 4 }}>({s.unit})</span>}
        {s.threshold != null && (
          <span style={{ fontWeight: 400, color: '#dc2626', marginLeft: 8, fontSize: 10 }}>
            ⚠ grense {s.threshold} {s.unit}
          </span>
        )}
      </div>
      <svg
        viewBox={`0 0 ${W} ${PANEL_H}`}
        style={{ width: '100%', display: 'block' }}
        onMouseMove={handleMouseMove}
        onMouseLeave={() => setTooltip(null)}
      >
        {/* Y gridlines + labels */}
        {yTicks.map((v, i) => {
          const y = yScale(v) + MARGIN.top
          return (
            <g key={i}>
              <line x1={MARGIN.left} y1={y} x2={MARGIN.left + innerW} y2={y}
                stroke="#e5e7eb" strokeWidth={1} />
              <text x={MARGIN.left - 5} y={y + 3} textAnchor="end" fontSize={9} fill="#9ca3af">
                {v}
              </text>
            </g>
          )
        })}

        {/* X-axis ticks */}
        {showXAxis && xTicks.map((ts, i) => {
          const x = xScale(ts) + MARGIN.left
          return (
            <g key={i}>
              <line x1={x} y1={MARGIN.top} x2={x} y2={MARGIN.top + innerH}
                stroke="#f3f4f6" strokeWidth={1} />
              <text x={x} y={MARGIN.top + innerH + 13} textAnchor="middle" fontSize={9} fill="#6b7280">
                {formatDateLabel(ts)}
              </text>
            </g>
          )
        })}
        {!showXAxis && xTicks.map((ts, i) => {
          const x = xScale(ts) + MARGIN.left
          return <line key={i} x1={x} y1={MARGIN.top} x2={x} y2={MARGIN.top + innerH}
            stroke="#f3f4f6" strokeWidth={1} />
        })}

        {/* Axes */}
        <line x1={MARGIN.left} y1={MARGIN.top} x2={MARGIN.left} y2={MARGIN.top + innerH}
          stroke="#d1d5db" strokeWidth={1} />
        <line x1={MARGIN.left} y1={MARGIN.top + innerH} x2={MARGIN.left + innerW} y2={MARGIN.top + innerH}
          stroke="#d1d5db" strokeWidth={1} />

        {/* Threshold line */}
        {s.threshold != null && (
          <line
            x1={MARGIN.left} y1={yScale(s.threshold) + MARGIN.top}
            x2={MARGIN.left + innerW} y2={yScale(s.threshold) + MARGIN.top}
            stroke="#dc2626" strokeWidth={1} strokeDasharray="4,3"
          />
        )}

        {/* Shaded area under line for context */}
        {segments.length > 0 && nonNull.length > 1 && (() => {
          const allObs = nonNull.filter(p => p.quality !== 'missing')
          if (allObs.length < 2) return null
          const areaPath = [
            `M${(xScale(allObs[0].x) + MARGIN.left).toFixed(1)},${(MARGIN.top + innerH).toFixed(1)}`,
            ...allObs.map(p => `L${(xScale(p.x) + MARGIN.left).toFixed(1)},${(yScale(p.y) + MARGIN.top).toFixed(1)}`),
            `L${(xScale(allObs[allObs.length - 1].x) + MARGIN.left).toFixed(1)},${(MARGIN.top + innerH).toFixed(1)}`,
            'Z',
          ].join(' ')
          return <path d={areaPath} fill={s.color || '#3A86FF'} fillOpacity={0.07} />
        })()}

        {/* Line segments */}
        {segments.map((seg, segi) => {
          const d = buildPath(
            seg.pts,
            x => xScale(x) + MARGIN.left,
            v => yScale(v) + MARGIN.top,
          )
          return (
            <path key={segi} d={d} fill="none"
              stroke={s.color || '#3A86FF'} strokeWidth={1.8}
              strokeDasharray={seg.q === 'estimated' ? '5,3' : undefined}
              strokeLinejoin="round" strokeLinecap="round"
            />
          )
        })}

        {/* Missing dots */}
        {pts.filter(p => p.quality === 'missing' || (p.value == null && p.quality !== undefined)).map((p, pi) => (
          <circle key={pi}
            cx={xScale(p.x) + MARGIN.left} cy={MARGIN.top + innerH / 2}
            r={2.5} fill="#d1d5db"
          />
        ))}

        {/* Tooltip */}
        {tooltip && (() => {
          const tx = Math.min(tooltip.x + 8, W - 130)
          const ty = Math.max(tooltip.y - 30, MARGIN.top)
          const q = tooltip.point.quality || 'observed'
          const qLabel = q === 'estimated' ? ' (est.)' : q === 'missing' ? ' (mangler)' : ''
          return (
            <g>
              <line x1={tooltip.x} y1={MARGIN.top} x2={tooltip.x} y2={MARGIN.top + innerH}
                stroke="#6b7280" strokeWidth={1} strokeDasharray="3,2" />
              <circle cx={tooltip.x} cy={tooltip.y} r={4} fill={s.color || '#3A86FF'} />
              <rect x={tx} y={ty} width={128} height={40} rx={4}
                fill="white" stroke="#d1d5db" strokeWidth={1}
                filter="drop-shadow(0 1px 3px rgba(0,0,0,0.12))"
              />
              <text x={tx + 7} y={ty + 13} fontSize={9} fill="#6b7280">
                {formatTooltipDate(tooltip.point.timestamp)}
              </text>
              <text x={tx + 7} y={ty + 27} fontSize={11} fontWeight={700} fill="#111827">
                {tooltip.point.value != null ? `${tooltip.point.value} ${s.unit || ''}${qLabel}` : 'mangler'}
              </text>
            </g>
          )
        })()}
      </svg>

      {/* Forklaring for behandlingsparameter */}
      {isTreatment && (
        <div style={{
          paddingLeft: MARGIN.left,
          paddingRight: MARGIN.right,
          marginTop: 2,
          marginBottom: 6,
          fontSize: 11,
          color: '#6b7280',
          fontStyle: 'italic',
          lineHeight: 1.5,
        }}>
          Viser antall behandlingshendelser mot lakselus eller sykdom gjennomført
          de siste 30 dagene (rullerende sum). Høy verdi indikerer intensiv
          behandlingsperiode og økt operasjonell belastning.
        </div>
      )}
    </div>
  )
}

// ── Disease event-band panel ─────────────────────────────────────────────────
// Binary 0/1 disease presence rendered as a colored status bar with interval bands.
function EventBandPanel({ s, tMin, tMax, showXAxis }) {
  const BAND_H = 36
  const innerW = W - MARGIN.left - MARGIN.right
  const xRange = tMax - tMin || 1
  const xScale = ts => ((ts - tMin) / xRange) * innerW

  const pts = s.points || []
  const intervals = s.intervals || []

  // X-axis ticks (shared dates)
  const xTicks = Array.from({ length: 5 }, (_, i) => tMin + (i / 4) * (tMax - tMin))

  const anyActive = s.has_active || intervals.length > 0
  const diseaseName = s.disease_name || null

  return (
    <div style={{ marginBottom: 4 }}>
      {/* Header */}
      <div style={{ fontSize: 11, fontWeight: 700, color: '#B91C1C', marginBottom: 2, paddingLeft: MARGIN.left, display: 'flex', alignItems: 'center', gap: 8, flexWrap: 'wrap' }}>
        Sykdomsstatus
        <span style={{
          fontSize: 10, fontWeight: 600, padding: '1px 7px', borderRadius: 10,
          background: anyActive ? '#fee2e2' : '#dcfce7',
          color: anyActive ? '#991b1b' : '#166534',
        }}>
          {anyActive
            ? (diseaseName ? diseaseName : 'Aktiv i perioden')
            : 'Ingen registrert'}
        </span>
      </div>
      <svg viewBox={`0 0 ${W} ${BAND_H + (showXAxis ? 20 : 4)}`} style={{ width: '100%', display: 'block' }}>
        {/* Background track — healthy (green) */}
        <rect
          x={MARGIN.left} y={4}
          width={innerW} height={BAND_H - 8}
          rx={3} fill="#dcfce7"
        />
        {/* Active disease intervals (red bands) */}
        {intervals.map((iv, i) => {
          const x0 = xScale(new Date(iv.start).getTime()) + MARGIN.left
          const x1 = xScale(new Date(iv.end).getTime()) + MARGIN.left
          const w = Math.max(x1 - x0, 2)
          return (
            <g key={i}>
              <rect x={x0} y={4} width={w} height={BAND_H - 8} rx={2} fill="#fca5a5" />
              <rect x={x0} y={4} width={w} height={BAND_H - 8} rx={2}
                fill="none" stroke="#ef4444" strokeWidth={1} />
              {/* Onset marker */}
              <line x1={x0} y1={2} x2={x0} y2={BAND_H - 2}
                stroke="#dc2626" strokeWidth={1.5} />
              {w > 20 && (
                <text x={x0 + w / 2} y={BAND_H / 2 + 2}
                  textAnchor="middle" fontSize={9} fontWeight={700} fill="#991b1b">
                  {iv.disease_name ? iv.disease_name.split(' ')[0] : 'Syk'}
                </text>
              )}
            </g>
          )
        })}
        {/* Band border */}
        <rect x={MARGIN.left} y={4} width={innerW} height={BAND_H - 8}
          rx={3} fill="none" stroke="#d1d5db" strokeWidth={1} />
        {/* Left axis line */}
        <line x1={MARGIN.left} y1={4} x2={MARGIN.left} y2={BAND_H - 4}
          stroke="#d1d5db" strokeWidth={1} />
        {/* Y-axis label */}
        <text x={MARGIN.left - 5} y={BAND_H / 2 + 3} textAnchor="end" fontSize={9} fill="#9ca3af">
          {anyActive ? '●' : '○'}
        </text>

        {/* X-axis dates (only on last panel) */}
        {showXAxis && xTicks.map((ts, i) => {
          const x = xScale(ts) + MARGIN.left
          return (
            <text key={i} x={x} y={BAND_H + 12}
              textAnchor="middle" fontSize={9} fill="#6b7280">
              {formatDateLabel(ts)}
            </text>
          )
        })}
      </svg>
    </div>
  )
}

// ── Main export ───────────────────────────────────────────────────────────────
export default function RawDataChart({ series = [], period = '30d' }) {
  if (!series || series.length === 0) {
    return (
      <div style={{ padding: 32, textAlign: 'center', color: '#9ca3af', fontSize: 13 }}>
        Ingen rådata tilgjengelig
      </div>
    )
  }

  // Separate line series from event-band series
  const lineSeries = series.filter(s => s.chart_type !== 'event_band')
  const bandSeries = series.filter(s => s.chart_type === 'event_band')

  // Global time domain across all series
  const allTs = []
  series.forEach(s => (s.points || []).forEach(p => allTs.push(new Date(p.timestamp).getTime())))
  const tMin = allTs.length ? Math.min(...allTs) : 0
  const tMax = allTs.length ? Math.max(...allTs) : 1

  return (
    <div>
      {/* Quality encoding legend */}
      <div style={{ display: 'flex', gap: 16, fontSize: 11, color: '#6b7280', marginBottom: 10, paddingLeft: MARGIN.left, flexWrap: 'wrap' }}>
        <span>
          <svg width={20} height={10} style={{ verticalAlign: 'middle', marginRight: 4 }}>
            <line x1={0} y1={5} x2={20} y2={5} stroke="#374151" strokeWidth={2} />
          </svg>
          Observert
        </span>
        <span>
          <svg width={20} height={10} style={{ verticalAlign: 'middle', marginRight: 4 }}>
            <line x1={0} y1={5} x2={20} y2={5} stroke="#374151" strokeWidth={2} strokeDasharray="5,3" />
          </svg>
          Estimert
        </span>
        <span>
          <svg width={20} height={10} style={{ verticalAlign: 'middle', marginRight: 4 }}>
            <circle cx={10} cy={5} r={3} fill="#d1d5db" />
          </svg>
          Mangler
        </span>
        <span>
          <svg width={20} height={10} style={{ verticalAlign: 'middle', marginRight: 4 }}>
            <line x1={0} y1={5} x2={20} y2={5} stroke="#dc2626" strokeWidth={1} strokeDasharray="4,3" />
          </svg>
          Grenseverdi
        </span>
        <span>
          <svg width={24} height={10} style={{ verticalAlign: 'middle', marginRight: 4 }}>
            <rect x={0} y={1} width={24} height={8} rx={2} fill="#fca5a5" stroke="#ef4444" strokeWidth={1} />
          </svg>
          Sykdom aktiv
        </span>
      </div>

      {/* Line panels — every panel shows its own X-axis dates */}
      {lineSeries.map((s, i) => (
        <SeriesPanel
          key={s.parameter || i}
          s={s}
          tMin={tMin}
          tMax={tMax}
          showXAxis={true}
        />
      ))}

      {/* Event-band panels (disease etc.) */}
      {bandSeries.map((s, i) => (
        <EventBandPanel
          key={s.parameter || `band-${i}`}
          s={s}
          tMin={tMin}
          tMax={tMax}
          showXAxis={true}
        />
      ))}
    </div>
  )
}
