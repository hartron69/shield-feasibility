import React from 'react'
import { SMOLT_DOMAIN_META } from '../../data/mockSmoltSiteRiskData.js'

function fmtM(v) {
  return `NOK ${(v / 1_000_000).toFixed(2)}M`
}

function scoreClass(s) {
  if (s >= 65) return 'high'
  if (s >= 40) return 'medium'
  return 'low'
}

function AlertBadge({ level }) {
  const map = {
    CRITICAL: { bg: '#FEE2E2', color: '#991B1B', border: '#FCA5A5' },
    WARNING:  { bg: '#FEF9C3', color: '#713F12', border: '#FDE68A' },
    WATCH:    { bg: '#DBEAFE', color: '#1E40AF', border: '#BFDBFE' },
    NORMAL:   { bg: '#F0FDF4', color: '#166534', border: '#BBF7D0' },
  }
  const s = map[level] || map.NORMAL
  return (
    <span style={{
      fontSize: 10, fontWeight: 700, padding: '2px 7px',
      borderRadius: 4, border: `1px solid ${s.border}`,
      background: s.bg, color: s.color, letterSpacing: '0.4px',
    }}>
      {level}
    </span>
  )
}

// Top 3 risk sites shown as cards
export default function SiteRiskSummaryCards({ sites, selectedId, onSelect }) {
  const top3 = [...sites].sort((a, b) => b.total_risk_score - a.total_risk_score).slice(0, 3)

  return (
    <div className="site-risk-cards-row">
      {top3.map((site, rank) => {
        const domMeta = SMOLT_DOMAIN_META[site.dominant_domain] || { label: site.dominant_domain, color: '#6B7280' }
        const sc = scoreClass(site.total_risk_score)
        const isSelected = site.site_id === selectedId
        return (
          <div
            key={site.site_id}
            className={`site-risk-card ${isSelected ? 'site-risk-card-selected' : ''}`}
            onClick={() => onSelect(isSelected ? null : site.site_id)}
            role="button"
            tabIndex={0}
            onKeyDown={e => e.key === 'Enter' && onSelect(isSelected ? null : site.site_id)}
          >
            {/* Rank + alert level */}
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 6 }}>
              <span className="site-rank-badge">#{rank + 1}</span>
              <AlertBadge level={site.alert_level} />
            </div>

            {/* Site name + type */}
            <div className="site-card-name">{site.site_name}</div>
            <div style={{ fontSize: 11, color: 'var(--dark-grey)', marginBottom: 8 }}>
              {site.municipality} ·{' '}
              <span style={{ color: site.production_type === 'RAS' ? '#0D9488' : '#6B7280', fontWeight: 600 }}>
                {site.production_type}
              </span>
            </div>

            {/* Risk score ring (inline) */}
            <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 8 }}>
              <div className={`risk-score-ring ${sc}`} style={{ width: 44, height: 44, flexShrink: 0 }}>
                <span className="ring-value" style={{ fontSize: 13 }}>{site.total_risk_score}</span>
              </div>
              <div>
                <div style={{ fontSize: 11, color: 'var(--dark-grey)' }}>Dominant domene</div>
                <div style={{ fontSize: 12, fontWeight: 700, color: domMeta.color }}>
                  {domMeta.label}
                </div>
              </div>
            </div>

            {/* EAL + SCR */}
            <div className="site-card-metrics">
              <div className="site-card-metric">
                <div className="site-card-metric-label">EAL</div>
                <div className="site-card-metric-value">{fmtM(site.expected_annual_loss_nok)}</div>
              </div>
              <div className="site-card-metric">
                <div className="site-card-metric-label">SCR-bidrag</div>
                <div className="site-card-metric-value">{fmtM(site.scr_contribution_nok)}</div>
              </div>
            </div>

            {/* Alerts + confidence */}
            <div style={{ display: 'flex', justifyContent: 'space-between', marginTop: 8, fontSize: 11 }}>
              <span style={{ color: site.alerts_open > 0 ? '#DC2626' : 'var(--dark-grey)' }}>
                {site.alerts_open > 0 ? `${site.alerts_open} åpne varsler` : 'Ingen åpne varsler'}
              </span>
              <span style={{ color: 'var(--dark-grey)' }}>
                Konfidens {Math.round(site.data_confidence * 100)}%
              </span>
            </div>

            {isSelected && (
              <div style={{ marginTop: 8, fontSize: 11, color: 'var(--teal)', fontWeight: 600, textAlign: 'center' }}>
                Detaljer vist under ↓
              </div>
            )}
          </div>
        )
      })}
    </div>
  )
}
