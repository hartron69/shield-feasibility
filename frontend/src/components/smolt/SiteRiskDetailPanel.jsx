import React from 'react'
import { SMOLT_DOMAIN_META } from '../../data/mockSmoltSiteRiskData.js'

const SEVERITY_COLORS = { high: '#DC2626', medium: '#D97706', low: '#059669' }

function fmtM(v) {
  return `NOK ${(v / 1_000_000).toFixed(2)}M`
}

function AlertLevelBadge({ level }) {
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

function ConfidenceBar({ value }) {
  const pct = Math.round(value * 100)
  const color = pct >= 80 ? '#059669' : pct >= 60 ? '#D97706' : '#DC2626'
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
      <div style={{ flex: 1, height: 6, background: '#E5E7EB', borderRadius: 3 }}>
        <div style={{ width: `${pct}%`, height: '100%', background: color, borderRadius: 3 }} />
      </div>
      <span style={{ fontSize: 11, fontWeight: 700, color, minWidth: 28 }}>{pct}%</span>
    </div>
  )
}

export default function SiteRiskDetailPanel({ site, onClose }) {
  if (!site) return null

  const maxDomain = Math.max(...Object.values(site.domain_breakdown))

  return (
    <div className="site-detail-panel">
      {/* Header */}
      <div className="site-detail-header">
        <div>
          <div className="site-detail-name">{site.site_name}</div>
          <div className="site-detail-meta">
            {site.municipality} · {site.production_type} · {site.capacity_msmolt} mill. smolt/år
          </div>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <AlertLevelBadge level={site.alert_level} />
          <button className="site-detail-close" onClick={onClose} title="Lukk">✕</button>
        </div>
      </div>

      {/* KPI row */}
      <div className="site-detail-kpi-row">
        <div className="site-detail-kpi">
          <div className="site-detail-kpi-label">Risikoscore</div>
          <div className="site-detail-kpi-value"
            style={{ color: site.total_risk_score >= 65 ? '#DC2626' : site.total_risk_score >= 40 ? '#D97706' : '#059669' }}>
            {site.total_risk_score}<span style={{ fontSize: 11, fontWeight: 400, color: 'var(--dark-grey)' }}>/100</span>
          </div>
        </div>
        <div className="site-detail-kpi">
          <div className="site-detail-kpi-label">EAL (forventet)</div>
          <div className="site-detail-kpi-value">{fmtM(site.expected_annual_loss_nok)}</div>
        </div>
        <div className="site-detail-kpi">
          <div className="site-detail-kpi-label">SCR-bidrag</div>
          <div className="site-detail-kpi-value">{fmtM(site.scr_contribution_nok)}</div>
          <div style={{ fontSize: 10, color: 'var(--dark-grey)' }}>{site.scr_share_pct.toFixed(1)}% av total SCR</div>
        </div>
        <div className="site-detail-kpi">
          <div className="site-detail-kpi-label">Åpne varsler</div>
          <div className="site-detail-kpi-value"
            style={{ color: site.alerts_open > 0 ? '#DC2626' : '#059669' }}>
            {site.alerts_open}
          </div>
        </div>
      </div>

      {/* Domain breakdown */}
      <div style={{ marginBottom: 14 }}>
        <div className="site-detail-section-title">Risikofordeling per domene</div>
        {Object.entries(site.domain_breakdown)
          .sort((a, b) => b[1] - a[1])
          .map(([dom, frac]) => {
            const meta = SMOLT_DOMAIN_META[dom] || { label: dom, color: '#6B7280' }
            const isDominant = frac === maxDomain
            return (
              <div key={dom} className="domain-bar-row" style={{ marginBottom: 4 }}>
                <div className="domain-bar-label" style={{ color: isDominant ? meta.color : undefined, fontWeight: isDominant ? 700 : 400 }}>
                  {meta.label}
                  {isDominant && <span style={{ marginLeft: 4, fontSize: 9, color: meta.color }}>▲</span>}
                </div>
                <div className="domain-bar-track">
                  <div className="domain-bar-fill"
                    style={{ width: `${frac * 100}%`, background: meta.color, opacity: isDominant ? 1 : 0.65 }} />
                </div>
                <div className="domain-bar-pct" style={{ color: meta.color }}>{(frac * 100).toFixed(0)}%</div>
              </div>
            )
          })}
      </div>

      {/* Top drivers */}
      <div style={{ marginBottom: 14 }}>
        <div className="site-detail-section-title">Viktigste risikodrivere</div>
        {site.top_drivers.map((d, i) => (
          <div key={i} className="site-driver-row">
            <span className="site-driver-severity"
              style={{ background: SEVERITY_COLORS[d.severity] + '18', color: SEVERITY_COLORS[d.severity] }}>
              {d.severity.toUpperCase()}
            </span>
            <div>
              <div style={{ fontWeight: 600, fontSize: 12 }}>{d.driver}</div>
              <div style={{ fontSize: 11, color: 'var(--dark-grey)', marginTop: 1 }}>{d.description}</div>
            </div>
          </div>
        ))}
      </div>

      {/* Data confidence */}
      <div>
        <div className="site-detail-section-title">Datakvalitet og konfidensgrad</div>
        <ConfidenceBar value={site.data_confidence} />
        <div style={{ fontSize: 11, color: 'var(--dark-grey)', marginTop: 4 }}>
          {site.data_confidence >= 0.80
            ? 'Høy konfidensgrad — tilstrekkelig datagrunnlag for risikoestimering'
            : site.data_confidence >= 0.60
            ? 'Moderat konfidensgrad — noen datakilder mangler eller er utdaterte'
            : 'Lav konfidensgrad — estimatene er usikre, fyll inn manglende data'}
        </div>
      </div>
    </div>
  )
}
