import React, { useState, useEffect } from 'react'
import { C5AI_MOCK } from '../data/c5ai_mock.js'
import InputCompletenessCard from './inputs/InputCompletenessCard.jsx'
import { fetchC5AIRiskOverview, fetchDataQuality } from '../api/client.js'

const KH_SITES = ['KH_S01', 'KH_S02', 'KH_S03']

const DOMAIN_COLORS = {
  biological: '#059669', structural: '#2563EB',
  environmental: '#D97706', operational: '#7C3AED',
}

const DOMAIN_LABELS = {
  biological: 'Biologisk', structural: 'Strukturell',
  environmental: 'Miljø', operational: 'Operasjonell',
}

const EXPOSURE_LABELS = {
  semi_exposed: 'Semi-eksponert', sheltered: 'Skjermet', open: 'Eksponert',
}

function fmtM(v) { return `NOK ${(v / 1_000_000).toFixed(1)}M` }

function scoreClass(s) {
  if (s >= 65) return 'high'
  if (s >= 40) return 'medium'
  return 'low'
}

function RiskLevelBadge({ score }) {
  const level = score >= 65 ? 'HIGH' : score >= 40 ? 'MEDIUM' : 'LOW'
  const map = {
    HIGH:   { bg: '#FEE2E2', color: '#991B1B', border: '#FCA5A5' },
    MEDIUM: { bg: '#FEF9C3', color: '#713F12', border: '#FDE68A' },
    LOW:    { bg: '#F0FDF4', color: '#166534', border: '#BBF7D0' },
  }
  const s = map[level]
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
  const [riskOverview, setRiskOverview] = useState(null)
  const [dataQuality,  setDataQuality]  = useState([])
  const [loading,      setLoading]      = useState(true)

  useEffect(() => {
    Promise.all([
      fetchC5AIRiskOverview().catch(() => null),
      Promise.all(KH_SITES.map(id => fetchDataQuality(id).catch(() => null))),
    ]).then(([overview, dqResults]) => {
      if (overview) setRiskOverview(overview)
      setDataQuality(dqResults.filter(Boolean).map(d => ({
        ...d,
        site_name: d.locality_name,
        site_id:   d.locality_id,
      })))
    }).finally(() => setLoading(false))
  }, [])

  const overallScore    = riskOverview?.overall_risk_score ?? C5AI_MOCK.overall_risk_score
  const domainBreakdown = riskOverview?.domain_breakdown   ?? C5AI_MOCK.domain_breakdown
  const seaSites        = riskOverview?.sites              ?? []

  const totalEAL = Object.values(domainBreakdown).reduce((s, d) => s + (d.annual_loss_nok ?? 0), 0)

  const avgCompleteness = dataQuality.length > 0
    ? dataQuality.reduce((s, d) => s + d.overall_completeness, 0) / dataQuality.length
    : null

  const operatorName = C5AI_MOCK.metadata.operator_name
  const nSites       = C5AI_MOCK.sites.length
  const horizon      = C5AI_MOCK.metadata.forecast_horizon_years
  const modelVer     = C5AI_MOCK.metadata.model_version

  return (
    <div style={{ maxWidth: 1100 }}>
      <div style={{ fontWeight: 700, fontSize: 20, marginBottom: 4 }}>Portfolio Overview</div>
      <div style={{ fontSize: 13, color: 'var(--dark-grey)', marginBottom: 20 }}>
        {operatorName} · {nSites} sites · {horizon}-year horizon · Model {modelVer}
      </div>

      {/* ── Top KPI row ────────────────────────────────────────────────────── */}
      <div className="overview-kpi-row">
        <div className="overview-kpi-card">
          <div className="overview-kpi-label">Overall Risk Score</div>
          <div className={`risk-score-ring ${scoreClass(overallScore)}`} style={{ width: 64, height: 64, margin: '8px auto' }}>
            <span className="ring-value" style={{ fontSize: 20 }}>{Math.round(overallScore)}</span>
          </div>
          <div style={{ fontSize: 11, textAlign: 'center', color: 'var(--dark-grey)' }}>/ 100 · Live Risk</div>
        </div>
        <div className="overview-kpi-card">
          <div className="overview-kpi-label">E[Annual Loss]</div>
          <div className="overview-kpi-value" style={{ fontSize: 16 }}>{fmtM(totalEAL)}</div>
          <div style={{ fontSize: 11, color: 'var(--dark-grey)' }}>Alle domener · Live Risk</div>
        </div>
        <div className="overview-kpi-card">
          <div className="overview-kpi-label">Input Completeness</div>
          {avgCompleteness != null ? (
            <>
              <div className="overview-kpi-value">{Math.round(avgCompleteness * 100)}%</div>
              <div style={{ fontSize: 11, color: 'var(--dark-grey)' }}>Porteføljesnitt · Live Risk</div>
            </>
          ) : (
            <div style={{ fontSize: 13, color: 'var(--dark-grey)', marginTop: 8 }}>
              {loading ? 'Laster…' : '—'}
            </div>
          )}
        </div>
        <div className="overview-kpi-card">
          <div className="overview-kpi-label">Total Biomasse</div>
          <div className="overview-kpi-value" style={{ fontSize: 16 }}>
            {seaSites.reduce((s, si) => s + (si.biomass_tonnes ?? 0), 0).toLocaleString('nb-NO')} t
          </div>
          <div style={{ fontSize: 11, color: 'var(--dark-grey)' }}>
            {fmtM(seaSites.reduce((s, si) => s + (si.biomass_value_nok ?? 0), 0))} verdi
          </div>
        </div>
      </div>

      {/* ── Top Risk Sites (sea) ──────────────────────────────────────────── */}
      <div className="card">
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 10 }}>
          <div className="section-title" style={{ margin: 0 }}>Topp risikoanlegg — Sjølokaliteter</div>
          {onNavigate && (
            <button className="overview-link-btn" style={{ margin: 0 }} onClick={() => onNavigate('live_risk')}>
              Se alle anlegg →
            </button>
          )}
        </div>
        <div style={{ fontSize: 12, color: 'var(--dark-grey)', marginBottom: 12 }}>
          KH-portefølje rangert etter total risikoscore fra Live Risk-modellen.
        </div>
        {loading && <div style={{ fontSize: 13, color: 'var(--dark-grey)', padding: '12px 0' }}>Laster Live Risk…</div>}
        {!loading && seaSites.length === 0 && (
          <div style={{ fontSize: 13, color: 'var(--dark-grey)', padding: '12px 0' }}>
            Ingen lokalitetsdata — start backend for å laste Live Risk.
          </div>
        )}
        <div className="site-risk-cards-row">
          {[...seaSites]
            .sort((a, b) => b.risk_score - a.risk_score)
            .map((site, rank) => {
              const sc = scoreClass(site.risk_score)
              const domColor = DOMAIN_COLORS[site.dominant_risks?.[0]] || '#6B7280'
              const domLabel = DOMAIN_LABELS[site.dominant_risks?.[0]] || site.dominant_risks?.[0]
              return (
                <div
                  key={site.site_id}
                  className="site-risk-card"
                  onClick={() => onNavigate && onNavigate('live_risk')}
                  role="button" tabIndex={0}
                  onKeyDown={e => e.key === 'Enter' && onNavigate && onNavigate('live_risk')}
                >
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 6 }}>
                    <span className="site-rank-badge">#{rank + 1}</span>
                    <RiskLevelBadge score={site.risk_score} />
                  </div>
                  <div className="site-card-name">{site.site_name}</div>
                  <div style={{ fontSize: 11, color: 'var(--dark-grey)', marginBottom: 8 }}>
                    {EXPOSURE_LABELS[site.fjord_exposure] || site.fjord_exposure} · Sjø
                  </div>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 8 }}>
                    <div className={`risk-score-ring ${sc}`} style={{ width: 44, height: 44, flexShrink: 0 }}>
                      <span className="ring-value" style={{ fontSize: 13 }}>{Math.round(site.risk_score)}</span>
                    </div>
                    <div>
                      <div style={{ fontSize: 11, color: 'var(--dark-grey)' }}>Dom. domene</div>
                      <div style={{ fontSize: 12, fontWeight: 700, color: domColor }}>{domLabel}</div>
                    </div>
                  </div>
                  <div className="site-card-metrics">
                    <div className="site-card-metric">
                      <div className="site-card-metric-label">Biomasse</div>
                      <div className="site-card-metric-value">{site.biomass_tonnes?.toLocaleString('nb-NO')} t</div>
                    </div>
                    <div className="site-card-metric">
                      <div className="site-card-metric-label">Biomasseverdi</div>
                      <div className="site-card-metric-value">{fmtM(site.biomass_value_nok)}</div>
                    </div>
                  </div>
                  <div style={{ textAlign: 'right', marginTop: 8, fontSize: 11, color: 'var(--dark-grey)' }}>
                    {site.site_id}
                  </div>
                </div>
              )
            })}
        </div>
      </div>

      {/* ── Domain breakdown ──────────────────────────────────────────────── */}
      <div className="card">
        <div className="section-title" style={{ marginBottom: 10 }}>Domain Loss Breakdown</div>
        {Object.entries(domainBreakdown).map(([domain, d]) => (
          <div key={domain} className="domain-bar-row">
            <div className="domain-bar-label" style={{ textTransform: 'capitalize' }}>{domain}</div>
            <div className="domain-bar-track">
              <div className="domain-bar-fill" style={{ width: `${d.fraction * 100}%`, background: DOMAIN_COLORS[domain] }} />
            </div>
            <div className="domain-bar-pct" style={{ color: DOMAIN_COLORS[domain] }}>{(d.fraction * 100).toFixed(0)}%</div>
            <div className="domain-bar-nok">{fmtM(d.annual_loss_nok)}/yr</div>
          </div>
        ))}
      </div>

      {/* ── Input completeness ────────────────────────────────────────────── */}
      <div className="card">
        <div className="section-title" style={{ marginBottom: 10 }}>Input Data Completeness</div>
        {dataQuality.length > 0 ? (
          <div className="dq-completeness-row">
            {dataQuality.map(site => (
              <InputCompletenessCard key={site.site_id} site={site} />
            ))}
          </div>
        ) : (
          <div style={{ fontSize: 13, color: 'var(--dark-grey)', padding: '8px 0' }}>
            {loading ? 'Laster datakvalitet…' : 'Ingen datakvalitetsdata — start backend.'}
          </div>
        )}
        {onNavigate && (
          <button className="overview-link-btn" onClick={() => onNavigate('inputs')}>
            View full inputs →
          </button>
        )}
      </div>
    </div>
  )
}
