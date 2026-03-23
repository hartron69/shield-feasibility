import React from 'react'
import { SMOLT_DOMAIN_META } from '../../data/mockSmoltSiteRiskData.js'

function fmtM(v) {
  return `NOK ${(v / 1_000_000).toFixed(2)}M`
}

function ScoreBar({ score }) {
  const color = score >= 65 ? '#DC2626' : score >= 40 ? '#D97706' : '#059669'
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
      <div style={{ width: 60, height: 6, background: '#E5E7EB', borderRadius: 3, overflow: 'hidden' }}>
        <div style={{ width: `${score}%`, height: '100%', background: color, borderRadius: 3 }} />
      </div>
      <span style={{ fontWeight: 700, color, fontSize: 12 }}>{score}</span>
    </div>
  )
}

function AlertDot({ level }) {
  const colors = { CRITICAL: '#DC2626', WARNING: '#D97706', WATCH: '#2563EB', NORMAL: '#059669' }
  return (
    <span style={{
      display: 'inline-block', width: 8, height: 8, borderRadius: '50%',
      background: colors[level] || '#6B7280', marginRight: 5,
    }} />
  )
}

// Full ranked table of all smolt sites — used in the "Anlegg" tab
export default function TopRiskSitesTable({ sites, selectedId, onSelect, limit }) {
  const sorted = [...sites].sort((a, b) => b.total_risk_score - a.total_risk_score)
  const rows = limit ? sorted.slice(0, limit) : sorted

  return (
    <table className="data-table site-risk-table">
      <thead>
        <tr>
          <th>#</th>
          <th>Anlegg</th>
          <th>Type</th>
          <th>Kapasitet</th>
          <th>Risikoscore</th>
          <th>Dom. domene</th>
          <th>EAL</th>
          <th>SCR-bidrag</th>
          <th>SCR-andel</th>
          <th>Varsler</th>
        </tr>
      </thead>
      <tbody>
        {rows.map((site, i) => {
          const domMeta = SMOLT_DOMAIN_META[site.dominant_domain] || { label: site.dominant_domain, color: '#6B7280' }
          const isSelected = site.site_id === selectedId
          return (
            <tr
              key={site.site_id}
              className={`site-risk-row ${isSelected ? 'site-risk-row-selected' : ''}`}
              onClick={() => onSelect(isSelected ? null : site.site_id)}
              style={{ cursor: 'pointer' }}
            >
              <td style={{ color: 'var(--dark-grey)', fontWeight: 600 }}>{i + 1}</td>
              <td>
                <div style={{ fontWeight: 600, fontSize: 12 }}>{site.site_name}</div>
                <div style={{ fontSize: 10, color: 'var(--dark-grey)' }}>{site.municipality}</div>
              </td>
              <td>
                <span style={{
                  fontSize: 10, fontWeight: 700, padding: '2px 6px', borderRadius: 4,
                  background: site.production_type === 'RAS' ? '#CCFBF1' : '#F3F4F6',
                  color: site.production_type === 'RAS' ? '#0D9488' : '#374151',
                }}>
                  {site.production_type}
                </span>
              </td>
              <td style={{ fontSize: 12 }}>{site.capacity_msmolt} mill.</td>
              <td><ScoreBar score={site.total_risk_score} /></td>
              <td>
                <span style={{ fontSize: 11, fontWeight: 600, color: domMeta.color }}>
                  {domMeta.label}
                </span>
              </td>
              <td style={{ fontSize: 12 }}>{fmtM(site.expected_annual_loss_nok)}</td>
              <td style={{ fontSize: 12 }}>{fmtM(site.scr_contribution_nok)}</td>
              <td style={{ fontSize: 12 }}>{site.scr_share_pct.toFixed(1)}%</td>
              <td>
                <AlertDot level={site.alert_level} />
                <span style={{ fontSize: 11 }}>{site.alerts_open}</span>
              </td>
            </tr>
          )
        })}
      </tbody>
    </table>
  )
}
