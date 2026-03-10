/**
 * BioLineChart – Ren SVG linjegrafikk for biologisk tidsserie.
 *
 * Props:
 *   data       [{date: 'YYYY-MM', value: number}]  – 12 månedlige punkter
 *   baseline   number                               – stiplet grå referanselinje
 *   threshold  {value, direction, label} | null     – stiplet rød/amber varslingsgrense
 *   color      string                               – linjefargen
 *   unit       string                               – enhet for Y-akse
 *   label      string                               – parameternavn
 *   height     number                               – SVG-høyde (default 180)
 */

import React, { useState, useRef, useCallback } from 'react'

const MARGIN = { top: 18, right: 16, bottom: 34, left: 46 }

function formatMonth(ym) {
  const [year, month] = ym.split('-')
  const names = ['Jan','Feb','Mar','Apr','Mai','Jun','Jul','Aug','Sep','Okt','Nov','Des']
  return names[parseInt(month, 10) - 1] + (year !== '2025' ? ` '${year.slice(2)}` : '')
}

function linePath(points) {
  if (points.length === 0) return ''
  return points.map((p, i) => `${i === 0 ? 'M' : 'L'} ${p.x.toFixed(1)} ${p.y.toFixed(1)}`).join(' ')
}

// Smooth cubic bezier spline through all points (Catmull-Rom → cubic bezier)
function smoothPath(pts) {
  if (pts.length < 2) return linePath(pts)
  let d = `M ${pts[0].x.toFixed(1)} ${pts[0].y.toFixed(1)}`
  for (let i = 0; i < pts.length - 1; i++) {
    const p0 = pts[Math.max(i - 1, 0)]
    const p1 = pts[i]
    const p2 = pts[i + 1]
    const p3 = pts[Math.min(i + 2, pts.length - 1)]
    const cp1x = p1.x + (p2.x - p0.x) / 6
    const cp1y = p1.y + (p2.y - p0.y) / 6
    const cp2x = p2.x - (p3.x - p1.x) / 6
    const cp2y = p2.y - (p3.y - p1.y) / 6
    d += ` C ${cp1x.toFixed(1)} ${cp1y.toFixed(1)}, ${cp2x.toFixed(1)} ${cp2y.toFixed(1)}, ${p2.x.toFixed(1)} ${p2.y.toFixed(1)}`
  }
  return d
}

export default function BioLineChart({
  data = [],
  baseline,
  threshold = null,
  color = '#2563EB',
  unit = '',
  label = '',
  height = 180,
}) {
  const svgRef = useRef(null)
  const [tooltip, setTooltip] = useState(null) // { x, y, date, value }

  if (!data || data.length === 0) return null

  const W = 420
  const H = height
  const innerW = W - MARGIN.left - MARGIN.right
  const innerH = H - MARGIN.top - MARGIN.bottom

  // ── Skalaberegning ─────────────────────────────────────────────────────────
  const values = data.map(d => d.value)
  const allRef  = [baseline, threshold?.value].filter(v => v != null)
  const dataMin = Math.min(...values, ...allRef)
  const dataMax = Math.max(...values, ...allRef)
  const pad     = (dataMax - dataMin) * 0.15 || 0.5
  const yMin    = dataMin - pad
  const yMax    = dataMax + pad

  function xScale(i)   { return (i / (data.length - 1)) * innerW }
  function yScale(v)   { return innerH - ((v - yMin) / (yMax - yMin)) * innerH }

  const pts = data.map((d, i) => ({ x: xScale(i), y: yScale(d.value), ...d }))

  // ── Hover-håndtering ───────────────────────────────────────────────────────
  const handleMouseMove = useCallback((e) => {
    if (!svgRef.current) return
    const rect = svgRef.current.getBoundingClientRect()
    // SVG viewBox skaleres til faktisk bredde
    const scaleX = W / rect.width
    const relX   = (e.clientX - rect.left) * scaleX - MARGIN.left
    // Finn nærmeste punkt
    let nearest = 0
    let minDist = Infinity
    pts.forEach((p, i) => {
      const dist = Math.abs(p.x - relX)
      if (dist < minDist) { minDist = dist; nearest = i }
    })
    const p = pts[nearest]
    setTooltip({ x: p.x + MARGIN.left, y: p.y + MARGIN.top, date: p.date, value: p.value })
  }, [pts])

  const handleMouseLeave = useCallback(() => setTooltip(null), [])

  // ── Y-akse-ticker ──────────────────────────────────────────────────────────
  const nTicks = 4
  const ticks  = Array.from({ length: nTicks + 1 }, (_, i) => {
    const v = yMin + (i / nTicks) * (yMax - yMin)
    return { v, y: yScale(v) }
  })

  // ── X-akse-etiketter (annenhver) ───────────────────────────────────────────
  const xLabels = data
    .map((d, i) => ({ i, label: formatMonth(d.date) }))
    .filter((_, i) => i % 2 === 0 || i === data.length - 1)

  // ── Risikosonefyll (mellom terskel og aksetopp/bunn) ───────────────────────
  let riskFill = null
  if (threshold) {
    const ty = yScale(threshold.value)
    if (threshold.direction === 'above') {
      riskFill = `M 0 ${ty} L ${innerW} ${ty} L ${innerW} 0 L 0 0 Z`
    } else {
      riskFill = `M 0 ${ty} L ${innerW} ${ty} L ${innerW} ${innerH} L 0 ${innerH} Z`
    }
  }

  // ── Areafyll under linjen ──────────────────────────────────────────────────
  const areaPath = smoothPath(pts) +
    ` L ${pts[pts.length - 1].x.toFixed(1)} ${innerH} L 0 ${innerH} Z`

  return (
    <div className="bio-chart-wrap">
      {label && <div className="bio-chart-label">{label}</div>}
      <svg
        ref={svgRef}
        viewBox={`0 0 ${W} ${H}`}
        preserveAspectRatio="xMidYMid meet"
        style={{ width: '100%', height: H, display: 'block', overflow: 'visible' }}
        onMouseMove={handleMouseMove}
        onMouseLeave={handleMouseLeave}
      >
        <g transform={`translate(${MARGIN.left},${MARGIN.top})`}>

          {/* ── Rutenett ──────────────────────────────────────────────────── */}
          {ticks.map((t, i) => (
            <line key={i} x1={0} y1={t.y} x2={innerW} y2={t.y}
                  stroke="#E5E7EB" strokeWidth={1} />
          ))}

          {/* ── Risikosone ────────────────────────────────────────────────── */}
          {riskFill && (
            <path d={riskFill} fill="rgba(220,38,38,0.06)" />
          )}

          {/* ── Areafyll ──────────────────────────────────────────────────── */}
          <path d={areaPath} fill={color} fillOpacity={0.07} />

          {/* ── Basislinje (stiplet grå) ───────────────────────────────────── */}
          {baseline != null && (
            <line
              x1={0} y1={yScale(baseline)} x2={innerW} y2={yScale(baseline)}
              stroke="#9CA3AF" strokeWidth={1.2} strokeDasharray="5 4"
            />
          )}

          {/* ── Terskellinje (stiplet rød/amber) ──────────────────────────── */}
          {threshold && (
            <>
              <line
                x1={0} y1={yScale(threshold.value)} x2={innerW} y2={yScale(threshold.value)}
                stroke="#DC2626" strokeWidth={1.2} strokeDasharray="4 3"
              />
              <text
                x={innerW - 2} y={yScale(threshold.value) - 4}
                textAnchor="end" fontSize={9} fill="#DC2626"
              >
                {threshold.label} {threshold.value}{unit}
              </text>
            </>
          )}

          {/* ── Datalinje ─────────────────────────────────────────────────── */}
          <path d={smoothPath(pts)} fill="none" stroke={color} strokeWidth={2} strokeLinejoin="round" />

          {/* ── Datapunkter (små sirkler) ──────────────────────────────────── */}
          {pts.map((p, i) => {
            const isLast = i === pts.length - 1
            const isHovered = tooltip && tooltip.date === p.date
            return (
              <circle
                key={i}
                cx={p.x} cy={p.y}
                r={isLast ? 4 : isHovered ? 4 : 2.5}
                fill={isLast || isHovered ? color : '#fff'}
                stroke={color}
                strokeWidth={isLast ? 2 : 1.5}
              />
            )
          })}

          {/* ── X-akse ────────────────────────────────────────────────────── */}
          <line x1={0} y1={innerH} x2={innerW} y2={innerH} stroke="#D1D5DB" strokeWidth={1} />
          {xLabels.map(({ i, label }) => (
            <text
              key={i}
              x={xScale(i)} y={innerH + 14}
              textAnchor="middle" fontSize={9.5} fill="#6B7280"
            >
              {label}
            </text>
          ))}

          {/* ── Y-akse ────────────────────────────────────────────────────── */}
          <line x1={0} y1={0} x2={0} y2={innerH} stroke="#D1D5DB" strokeWidth={1} />
          {ticks.map((t, i) => (
            <text key={i} x={-5} y={t.y + 3.5}
                  textAnchor="end" fontSize={9.5} fill="#6B7280">
              {Math.abs(t.v) < 10 ? t.v.toFixed(1) : t.v.toFixed(0)}
            </text>
          ))}

          {/* ── Enhet Y-akse (vertikalt) ──────────────────────────────────── */}
          {unit && (
            <text
              x={-MARGIN.left + 8} y={innerH / 2}
              textAnchor="middle" fontSize={9} fill="#9CA3AF"
              transform={`rotate(-90, ${-MARGIN.left + 8}, ${innerH / 2})`}
            >
              {unit}
            </text>
          )}

          {/* ── Legender ──────────────────────────────────────────────────── */}
          <g transform={`translate(0, ${innerH + 24})`}>
            <line x1={0} y1={0} x2={18} y2={0} stroke={color} strokeWidth={2} />
            <text x={22} y={3.5} fontSize={9} fill="#4B5563">Målt verdi</text>
            <line x1={80} y1={0} x2={98} y2={0} stroke="#9CA3AF" strokeWidth={1.2} strokeDasharray="5 4" />
            <text x={102} y={3.5} fontSize={9} fill="#4B5563">Baseline</text>
            {threshold && (
              <>
                <line x1={155} y1={0} x2={173} y2={0} stroke="#DC2626" strokeWidth={1.2} strokeDasharray="4 3" />
                <text x={177} y={3.5} fontSize={9} fill="#4B5563">Terskel</text>
              </>
            )}
          </g>
        </g>

        {/* ── Tooltip ───────────────────────────────────────────────────────── */}
        {tooltip && (() => {
          const tx = tooltip.x
          const ty = tooltip.y
          const boxW = 90, boxH = 36
          const bx = Math.min(Math.max(tx - boxW / 2, 4), W - boxW - 4)
          const by = ty > MARGIN.top + 50 ? ty - boxH - 8 : ty + 10
          return (
            <g>
              <line x1={tooltip.x} y1={MARGIN.top} x2={tooltip.x} y2={H - MARGIN.bottom}
                    stroke="#CBD5E1" strokeWidth={1} strokeDasharray="3 2" />
              <rect x={bx} y={by} width={boxW} height={boxH}
                    rx={5} fill="rgba(15,23,42,0.88)" />
              <text x={bx + boxW / 2} y={by + 13}
                    textAnchor="middle" fontSize={10} fill="#F1F5F9" fontWeight={600}>
                {formatMonth(tooltip.date)}
              </text>
              <text x={bx + boxW / 2} y={by + 27}
                    textAnchor="middle" fontSize={11} fill="#fff" fontWeight={700}>
                {typeof tooltip.value === 'number'
                  ? (tooltip.value < 10 ? tooltip.value.toFixed(2) : tooltip.value.toFixed(1))
                  : tooltip.value} {unit}
              </text>
            </g>
          )
        })()}
      </svg>
    </div>
  )
}
