import React from 'react'
import AlertSummaryCards from '../alerts/AlertSummaryCards.jsx'
import { MOCK_ALERTS } from '../../data/mockAlertsData.js'

const DOMAIN_COLORS = {
  biological:    '#059669',
  structural:    '#2563EB',
  environmental: '#D97706',
  operational:   '#7C3AED',
}

const EXPOSURE_LABELS = {
  open_coast:   'Open Coast',
  semi_exposed: 'Semi-Exposed',
  sheltered:    'Sheltered',
}

function fmtM(v) {
  if (v == null) return '—'
  return `NOK ${(v / 1_000_000).toFixed(1)}M`
}

function scoreClass(s) {
  if (s >= 65) return 'high'
  if (s >= 40) return 'medium'
  return 'low'
}

export default function RiskOverviewTab({ data, feasibilityResult }) {
  const overall = data.overall_risk_score
  const sites   = data.sites
  const domains = data.domain_breakdown
  const pcc     = data.pcc_integration

  const totalBioLoss = Object.values(data.biological_forecast).reduce((sum, sf) => {
    return sum + (sf.hab.expected_loss_mean + sf.lice.expected_loss_mean +
                  sf.jellyfish.expected_loss_mean + sf.pathogen.expected_loss_mean)
  }, 0)

  return (
    <div>
      {/* ── Alert summary cards ──────────────────────────────────────────── */}
      <AlertSummaryCards alerts={MOCK_ALERTS} />

      {/* ── Overall score + quick stats ─────────────────────────────────── */}
      <div className="card" style={{ display: 'flex', alignItems: 'center', gap: 24 }}>
        <div className={`risk-score-ring ${scoreClass(overall)}`}>
          <span className="ring-value">{overall}</span>
          <span className="ring-label">/ 100</span>
        </div>
        <div style={{ flex: 1 }}>
          <div style={{ fontWeight: 700, fontSize: 16, marginBottom: 4 }}>
            Overall Portfolio Risk Score
          </div>
          <div style={{ fontSize: 13, color: 'var(--dark-grey)', marginBottom: 8 }}>
            {overall >= 65 ? 'HIGH — Significant biological risk exposure across the portfolio.' :
             overall >= 40 ? 'MEDIUM — Moderate risk, concentrated in biological domain.' :
                             'LOW — Risk is within acceptable range.'}
          </div>
          <div style={{ display: 'flex', gap: 24, flexWrap: 'wrap' }}>
            <div>
              <div style={{ fontSize: 11, color: 'var(--dark-grey)', textTransform: 'uppercase', letterSpacing: '0.4px' }}>Sites</div>
              <div style={{ fontWeight: 700 }}>{sites.length}</div>
            </div>
            <div>
              <div style={{ fontSize: 11, color: 'var(--dark-grey)', textTransform: 'uppercase', letterSpacing: '0.4px' }}>Total Biomass</div>
              <div style={{ fontWeight: 700 }}>{(sites.reduce((s, x) => s + x.biomass_tonnes, 0)).toLocaleString()} t</div>
            </div>
            <div>
              <div style={{ fontSize: 11, color: 'var(--dark-grey)', textTransform: 'uppercase', letterSpacing: '0.4px' }}>E[Bio Loss]/yr</div>
              <div style={{ fontWeight: 700 }}>{fmtM(totalBioLoss)}</div>
            </div>
            {pcc.enriched && (
              <div>
                <div style={{ fontSize: 11, color: 'var(--dark-grey)', textTransform: 'uppercase', letterSpacing: '0.4px' }}>Scale Factor</div>
                <div style={{ fontWeight: 700, color: '#7C3AED' }}>{pcc.scale_factor.toFixed(2)}×</div>
              </div>
            )}
          </div>
        </div>
        {pcc.enriched && (
          <div style={{ textAlign: 'center', padding: '8px 12px', background: '#F5F3FF', borderRadius: 8, border: '1px solid #C4B5FD' }}>
            <div className="c5ai-pill" style={{ marginBottom: 4 }}>C5AI+</div>
            <div style={{ fontSize: 11, color: '#6D28D9', fontWeight: 600 }}>Enriched</div>
          </div>
        )}
      </div>

      {/* ── Domain Breakdown ────────────────────────────────────────────── */}
      <div className="card">
        <div className="section-title">Domain Loss Breakdown</div>
        {Object.entries(domains).map(([domain, d]) => (
          <div key={domain} className="domain-bar-row">
            <div className="domain-bar-label" style={{ textTransform: 'capitalize' }}>{domain}</div>
            <div className="domain-bar-track">
              <div
                className="domain-bar-fill"
                style={{ width: `${d.fraction * 100}%`, background: DOMAIN_COLORS[domain] }}
              />
            </div>
            <div className="domain-bar-pct" style={{ color: DOMAIN_COLORS[domain] }}>
              {(d.fraction * 100).toFixed(0)}%
            </div>
            <div className="domain-bar-nok">{fmtM(d.annual_loss_nok)}/yr</div>
          </div>
        ))}
      </div>

      {/* ── Site Risk Ranking ────────────────────────────────────────────── */}
      <div className="card">
        <div className="section-title">Site Risk Ranking</div>
        <table className="data-table">
          <thead>
            <tr>
              <th>#</th>
              <th>Site</th>
              <th>Exposure</th>
              <th>Biomass</th>
              <th>Risk Score</th>
              <th>Dominant Risks</th>
            </tr>
          </thead>
          <tbody>
            {[...sites].sort((a, b) => b.risk_score - a.risk_score).map((site, i) => {
              const sc = scoreClass(site.risk_score)
              return (
                <tr key={site.site_id}>
                  <td style={{ color: 'var(--dark-grey)', fontWeight: 600 }}>{i + 1}</td>
                  <td style={{ fontWeight: 600 }}>{site.name}</td>
                  <td>{EXPOSURE_LABELS[site.fjord_exposure] || site.fjord_exposure}</td>
                  <td>{site.biomass_tonnes.toLocaleString()} t</td>
                  <td>
                    <span
                      className={`site-score-bar site-score-${sc}`}
                      style={{ width: site.risk_score * 0.9 }}
                    />
                    <strong>{site.risk_score}</strong>/100
                  </td>
                  <td>
                    {site.dominant_risks.map(r => (
                      <span key={r} className={`badge badge-biological`}
                        style={{ marginRight: 4, textTransform: 'uppercase', letterSpacing: '0.3px' }}>
                        {r}
                      </span>
                    ))}
                  </td>
                </tr>
              )
            })}
          </tbody>
        </table>
      </div>

      {/* ── PCC Integration Panel ───────────────────────────────────────── */}
      <div className="card" style={{ borderLeft: '4px solid #7C3AED' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 12 }}>
          <div className="c5ai-pill">C5AI+</div>
          <div className="section-title" style={{ margin: 0 }}>PCC Feasibility Integration</div>
        </div>
        <div className="kpi-grid" style={{ marginBottom: 12 }}>
          <div className="kpi-card">
            <div className="kpi-label">C5AI+ Scale Factor</div>
            <div className="kpi-value" style={{ color: '#7C3AED' }}>{pcc.scale_factor.toFixed(2)}×</div>
            <div className="kpi-sub">vs. static {pcc.scale_factor_static.toFixed(2)}×</div>
          </div>
          <div className="kpi-card">
            <div className="kpi-label">Biological Loss Fraction</div>
            <div className="kpi-value">{(pcc.biological_loss_fraction * 100).toFixed(0)}%</div>
            <div className="kpi-sub">of total expected annual loss</div>
          </div>
          <div className="kpi-card">
            <div className="kpi-label">Bio Criterion Score</div>
            <div className="kpi-value">{pcc.suitability_impact.bio_criterion_score}/100</div>
            <div className="kpi-sub">weight {(pcc.suitability_impact.bio_criterion_weight * 100).toFixed(0)}% of composite</div>
          </div>
        </div>
        <div className="info-note" style={{ marginBottom: 0 }}>
          {pcc.suitability_impact.bio_criterion_finding}
        </div>
        {!feasibilityResult && (
          <div style={{ marginTop: 10, fontSize: 12, color: 'var(--dark-grey)' }}>
            Run the Feasibility analysis to see how C5AI+ results flow into the PCC suitability score.
          </div>
        )}
        {feasibilityResult && (
          <div style={{ marginTop: 10, fontSize: 12, color: '#065F46', fontWeight: 600 }}>
            Feasibility result available — C5AI+ enrichment applied. Switch to Feasibility page to review full suitability analysis.
          </div>
        )}
      </div>
    </div>
  )
}
