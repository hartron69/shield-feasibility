import React from 'react'
import { SMOLT_DOMAIN_META } from '../../data/mockSmoltSiteRiskData.js'

// Pure SVG horizontal bar chart — EAL per smolt site, sorted highest to lowest
export default function SiteEALChart({ sites }) {
  const sorted = [...sites].sort((a, b) => b.expected_annual_loss_nok - a.expected_annual_loss_nok)
  const maxVal = sorted[0].expected_annual_loss_nok

  const BAR_H   = 26
  const GAP     = 8
  const LABEL_W = 130
  const VAL_W   = 80
  const BAR_W   = 300
  const PAD_TOP = 8
  const PAD_BOT = 8
  const totalH  = PAD_TOP + sorted.length * (BAR_H + GAP) - GAP + PAD_BOT
  const totalW  = LABEL_W + BAR_W + VAL_W + 12

  return (
    <div>
      <div className="site-chart-title">Forventet årstap (EAL) per anlegg</div>
      <div className="site-chart-subtitle">Sortert høyest til lavest · NOK</div>
      <svg width="100%" viewBox={`0 0 ${totalW} ${totalH}`} style={{ maxWidth: totalW, display: 'block' }}>
        {sorted.map((site, i) => {
          const y = PAD_TOP + i * (BAR_H + GAP)
          const barLen = Math.round((site.expected_annual_loss_nok / maxVal) * BAR_W)
          const domMeta = SMOLT_DOMAIN_META[site.dominant_domain] || { color: '#6B7280' }
          const valM = (site.expected_annual_loss_nok / 1_000_000).toFixed(2)
          return (
            <g key={site.site_id}>
              {/* Site label */}
              <text
                x={LABEL_W - 6}
                y={y + BAR_H / 2 + 4}
                textAnchor="end"
                fontSize={11}
                fill="#374151"
                fontWeight={i === 0 ? '700' : '400'}
              >
                {site.site_name}
              </text>
              {/* Background track */}
              <rect x={LABEL_W} y={y} width={BAR_W} height={BAR_H} rx={4} fill="#F3F4F6" />
              {/* Filled bar */}
              <rect
                x={LABEL_W}
                y={y}
                width={barLen}
                height={BAR_H}
                rx={4}
                fill={domMeta.color}
                opacity={0.80}
              />
              {/* Value label */}
              <text
                x={LABEL_W + BAR_W + 8}
                y={y + BAR_H / 2 + 4}
                fontSize={11}
                fill="#111827"
                fontWeight={i === 0 ? '700' : '400'}
              >
                {valM}M
              </text>
            </g>
          )
        })}
      </svg>
    </div>
  )
}
