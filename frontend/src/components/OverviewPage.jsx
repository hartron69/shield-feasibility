import React, { useState } from 'react'
import { C5AI_MOCK } from '../data/c5ai_mock.js'
import { MOCK_ALERTS } from '../data/mockAlertsData.js'
import { MOCK_DATA_QUALITY } from '../data/mockInputsData.js'
import { SMOLT_SITE_RISK, SMOLT_DOMAIN_META } from '../data/mockSmoltSiteRiskData.js'
import AlertSummaryCards from './alerts/AlertSummaryCards.jsx'
import InputCompletenessCard from './inputs/InputCompletenessCard.jsx'
import SiteRiskDetailPanel from './smolt/SiteRiskDetailPanel.jsx'

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

export default function OverviewPage({ onNavigate }) {
  const [selectedSmoltId, setSelectedSmoltId] = useState(null)
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

      {/* ── Top Risk Sites (smolt) ────────────────────────────────────────── */}
      <div className="card">
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 10 }}>
          <div className="section-title" style={{ margin: 0 }}>Topp risikoanlegg — Settefisk</div>
          {onNavigate && (
            <button className="overview-link-btn" style={{ margin: 0 }} onClick={() => onNavigate('c5ai')}>
              Se alle anlegg →
            </button>
          )}
        </div>
        <div style={{ fontSize: 12, color: 'var(--dark-grey)', marginBottom: 12 }}>
          Topp 3 settefiskanlegg rangert etter total risikoscore. Klikk et anlegg for å se detaljprofil.
        </div>
        <div className="site-risk-cards-row">
          {[...SMOLT_SITE_RISK]
            .sort((a, b) => b.total_risk_score - a.total_risk_score)
            .slice(0, 3)
            .map((site, rank) => {
              const domMeta = SMOLT_DOMAIN_META[site.dominant_domain] || { label: site.dominant_domain, color: '#6B7280' }
              const sc = site.total_risk_score >= 65 ? 'high' : site.total_risk_score >= 40 ? 'medium' : 'low'
              const isSelected = site.site_id === selectedSmoltId
              return (
                <div
                  key={site.site_id}
                  className={`site-risk-card ${isSelected ? 'site-risk-card-selected' : ''}`}
                  onClick={() => setSelectedSmoltId(isSelected ? null : site.site_id)}
                  role="button"
                  tabIndex={0}
                  onKeyDown={e => e.key === 'Enter' && setSelectedSmoltId(isSelected ? null : site.site_id)}
                >
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 6 }}>
                    <span className="site-rank-badge">#{rank + 1}</span>
                    <AlertBadge level={site.alert_level} />
                  </div>
                  <div className="site-card-name">{site.site_name}</div>
                  <div style={{ fontSize: 11, color: 'var(--dark-grey)', marginBottom: 8 }}>
                    {site.municipality} ·{' '}
                    <span style={{ color: site.production_type === 'RAS' ? '#0D9488' : '#6B7280', fontWeight: 600 }}>
                      {site.production_type}
                    </span>
                  </div>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 8 }}>
                    <div className={`risk-score-ring ${sc}`} style={{ width: 44, height: 44, flexShrink: 0 }}>
                      <span className="ring-value" style={{ fontSize: 13 }}>{site.total_risk_score}</span>
                    </div>
                    <div>
                      <div style={{ fontSize: 11, color: 'var(--dark-grey)' }}>Dom. domene</div>
                      <div style={{ fontSize: 12, fontWeight: 700, color: domMeta.color }}>{domMeta.label}</div>
                    </div>
                  </div>
                  <div className="site-card-metrics">
                    <div className="site-card-metric">
                      <div className="site-card-metric-label">EAL</div>
                      <div className="site-card-metric-value">
                        NOK {(site.expected_annual_loss_nok / 1_000_000).toFixed(2)}M
                      </div>
                    </div>
                    <div className="site-card-metric">
                      <div className="site-card-metric-label">SCR-bidrag</div>
                      <div className="site-card-metric-value">
                        NOK {(site.scr_contribution_nok / 1_000_000).toFixed(2)}M
                      </div>
                    </div>
                  </div>
                  <div style={{ display: 'flex', justifyContent: 'space-between', marginTop: 8, fontSize: 11 }}>
                    <span style={{ color: site.alerts_open > 0 ? '#DC2626' : 'var(--dark-grey)' }}>
                      {site.alerts_open > 0 ? `${site.alerts_open} varsler` : 'Ingen varsler'}
                    </span>
                    <span style={{ color: 'var(--dark-grey)' }}>
                      Konfidens {Math.round(site.data_confidence * 100)}%
                    </span>
                  </div>
                </div>
              )
            })}
        </div>
        {selectedSmoltId && (
          <div style={{ marginTop: 16 }}>
            <SiteRiskDetailPanel
              site={SMOLT_SITE_RISK.find(s => s.site_id === selectedSmoltId)}
              onClose={() => setSelectedSmoltId(null)}
            />
          </div>
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
