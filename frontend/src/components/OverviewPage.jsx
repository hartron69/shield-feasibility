import React from 'react'
import { C5AI_MOCK } from '../data/c5ai_mock.js'
import { MOCK_ALERTS } from '../data/mockAlertsData.js'
import { MOCK_DATA_QUALITY } from '../data/mockInputsData.js'
import AlertSummaryCards from './alerts/AlertSummaryCards.jsx'
import InputCompletenessCard from './inputs/InputCompletenessCard.jsx'

const DOMAIN_COLORS = {
  biological: '#059669', structural: '#2563EB',
  environmental: '#D97706', operational: '#7C3AED',
}

function fmtM(v) { return `NOK ${(v / 1_000_000).toFixed(1)}M` }

function scoreClass(s) {
  if (s >= 65) return 'high'
  if (s >= 40) return 'medium'
  return 'low'
}

export default function OverviewPage({ onNavigate }) {
  const overall = C5AI_MOCK.overall_risk_score
  const critCount = MOCK_ALERTS.filter(a => a.alert_level === 'CRITICAL').length
  const warnCount = MOCK_ALERTS.filter(a => a.alert_level === 'WARNING').length
  const avgCompleteness = MOCK_DATA_QUALITY.reduce((s, d) => s + d.overall_completeness, 0) / MOCK_DATA_QUALITY.length

  return (
    <div style={{ maxWidth: 1100 }}>
      <div style={{ fontWeight: 700, fontSize: 20, marginBottom: 4 }}>Portfolio Overview</div>
      <div style={{ fontSize: 13, color: 'var(--dark-grey)', marginBottom: 20 }}>
        Nordic Aqua Partners AS · {C5AI_MOCK.sites.length} sites · {C5AI_MOCK.metadata.forecast_horizon_years}-year horizon · Model {C5AI_MOCK.metadata.model_version}
      </div>

      {/* ── Top KPI row ────────────────────────────────────────────────────── */}
      <div className="overview-kpi-row">
        <div className="overview-kpi-card">
          <div className="overview-kpi-label">Overall Risk Score</div>
          <div className={`risk-score-ring ${scoreClass(overall)}`} style={{ width:64, height:64, margin:'8px auto' }}>
            <span className="ring-value" style={{ fontSize:20 }}>{overall}</span>
          </div>
          <div style={{ fontSize:11, textAlign:'center', color:'var(--dark-grey)' }}>/ 100</div>
        </div>
        <div className="overview-kpi-card overview-kpi-critical">
          <div className="overview-kpi-label">Critical Alerts</div>
          <div className="overview-kpi-value" style={{ color:'#B91C1C' }}>{critCount}</div>
          <div style={{ fontSize:11, color:'var(--dark-grey)' }}>{warnCount} warnings open</div>
        </div>
        <div className="overview-kpi-card">
          <div className="overview-kpi-label">Input Completeness</div>
          <div className="overview-kpi-value">{Math.round(avgCompleteness * 100)}%</div>
          <div style={{ fontSize:11, color:'var(--dark-grey)' }}>Portfolio average</div>
        </div>
        <div className="overview-kpi-card">
          <div className="overview-kpi-label">E[Annual Bio Loss]</div>
          <div className="overview-kpi-value" style={{ fontSize:16 }}>
            {fmtM(Object.values(C5AI_MOCK.domain_breakdown).reduce((s, d) => s + d.annual_loss_nok, 0))}
          </div>
          <div style={{ fontSize:11, color:'var(--dark-grey)' }}>All domains</div>
        </div>
        <div className="overview-kpi-card">
          <div className="overview-kpi-label">Learning Status</div>
          <div style={{ margin:'8px 0' }}>
            <span className={`c5ai-status-pill c5ai-status-${C5AI_MOCK.learning.status}`}>
              {C5AI_MOCK.learning.status.toUpperCase()}
            </span>
          </div>
          <div style={{ fontSize:11, color:'var(--dark-grey)' }}>Cycle {C5AI_MOCK.learning.cycles_completed} / 10</div>
        </div>
      </div>

      {/* ── Alert summary ─────────────────────────────────────────────────── */}
      <div className="card">
        <div className="section-title" style={{ marginBottom:10 }}>Active Alerts</div>
        <AlertSummaryCards alerts={MOCK_ALERTS} />
        {onNavigate && (
          <button className="overview-link-btn" onClick={() => onNavigate('alerts')}>
            View all alerts →
          </button>
        )}
      </div>

      {/* ── Domain breakdown ──────────────────────────────────────────────── */}
      <div className="card">
        <div className="section-title" style={{ marginBottom:10 }}>Domain Loss Breakdown</div>
        {Object.entries(C5AI_MOCK.domain_breakdown).map(([domain, d]) => (
          <div key={domain} className="domain-bar-row">
            <div className="domain-bar-label" style={{ textTransform:'capitalize' }}>{domain}</div>
            <div className="domain-bar-track">
              <div className="domain-bar-fill" style={{ width:`${d.fraction*100}%`, background:DOMAIN_COLORS[domain] }} />
            </div>
            <div className="domain-bar-pct" style={{ color:DOMAIN_COLORS[domain] }}>{(d.fraction*100).toFixed(0)}%</div>
            <div className="domain-bar-nok">{fmtM(d.annual_loss_nok)}/yr</div>
          </div>
        ))}
      </div>

      {/* ── Top alert per domain ──────────────────────────────────────────── */}
      <div className="card">
        <div className="section-title" style={{ marginBottom: 10 }}>Top Alert by Domain</div>
        <div style={{ display: 'flex', gap: 12, flexWrap: 'wrap' }}>
          {Object.entries(DOMAIN_COLORS).map(([domain, color]) => {
            const domainAlerts = MOCK_ALERTS.filter(a => {
              const d = a.domain || ({'hab':'biological','lice':'biological','jellyfish':'biological','pathogen':'biological'}[a.risk_type] || domain)
              return d === domain
            })
            const top = domainAlerts.sort((a, b) => {
              const order = { CRITICAL: 0, WARNING: 1, WATCH: 2, NORMAL: 3 }
              return (order[a.alert_level] ?? 4) - (order[b.alert_level] ?? 4)
            })[0]
            return (
              <div key={domain} style={{ flex: 1, minWidth: 180, padding: '10px 14px', border: `2px solid ${color}20`, borderRadius: 8, background: `${color}08` }}>
                <div style={{ fontSize: 11, fontWeight: 700, color, textTransform: 'capitalize', marginBottom: 4 }}>
                  {domain}
                </div>
                {top ? (
                  <>
                    <div style={{ fontSize: 12, fontWeight: 600 }}>{top.risk_type.replace(/_/g, ' ')}</div>
                    <div style={{ fontSize: 11, color: 'var(--dark-grey)' }}>
                      {top.alert_level} · {top.site_id}
                    </div>
                  </>
                ) : (
                  <div style={{ fontSize: 11, color: 'var(--dark-grey)' }}>No active alerts</div>
                )}
              </div>
            )
          })}
        </div>
      </div>

      {/* ── Input completeness ────────────────────────────────────────────── */}
      <div className="card">
        <div className="section-title" style={{ marginBottom:10 }}>Input Data Completeness</div>
        <div className="dq-completeness-row">
          {MOCK_DATA_QUALITY.map(site => (
            <InputCompletenessCard key={site.site_id} site={site} />
          ))}
        </div>
        {onNavigate && (
          <button className="overview-link-btn" onClick={() => onNavigate('inputs')}>
            View full inputs →
          </button>
        )}
      </div>
    </div>
  )
}
