import React, { useState } from 'react'

// Translates locality risk deltas into indicative financial estimates.
// All numbers are approximations — see methodology section.

const DOMAINS = ['biological', 'structural', 'environmental', 'operational']

const DOMAIN_COLORS = {
  biological:    '#3A86FF',
  structural:    '#FF6B6B',
  environmental: '#36A271',
  operational:   '#F4A620',
}

const DOMAIN_LABELS = {
  biological:    'Biologisk',
  structural:    'Strukturell',
  environmental: 'Miljø',
  operational:   'Operasjonell',
}

function fmtNOKAbs(n) {
  if (n == null) return '—'
  if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(1)} M NOK`
  if (n >= 1_000)     return `${Math.round(n / 1_000)} k NOK`
  return `${Math.round(n)} NOK`
}

function fmtNOKDelta(n) {
  if (n == null) return '—'
  const abs = Math.abs(n)
  const sign = n > 0 ? '+' : n < 0 ? '−' : ''
  if (abs >= 1_000_000) return `${sign}${(abs / 1_000_000).toFixed(1)} M`
  if (abs >= 1_000)     return `${sign}${Math.round(abs / 1_000)} k`
  return `${sign}${Math.round(abs)}`
}

function DeltaArrow({ value }) {
  if (value > 0) return <span style={{ color: '#c62828' }}>▲</span>
  if (value < 0) return <span style={{ color: '#2e7d32' }}>▼</span>
  return <span style={{ color: '#6b7280' }}>●</span>
}

function KPICard({ label, value, sublabel, deltaValue }) {
  const hasDelta = deltaValue != null
  const deltaColor = deltaValue > 0 ? '#c62828' : deltaValue < 0 ? '#2e7d32' : '#6b7280'
  return (
    <div className="lr-econ-kpi-card">
      <div className="lr-econ-kpi-label">{label}</div>
      <div className="lr-econ-kpi-main">{value}</div>
      {sublabel && <div className="lr-econ-kpi-sub">{sublabel}</div>}
      {hasDelta && (
        <div className="lr-econ-kpi-delta" style={{ color: deltaColor }}>
          <DeltaArrow value={deltaValue} /> {fmtNOKDelta(deltaValue)} NOK denne perioden
        </div>
      )}
    </div>
  )
}

export default function EconomicsTab({ economics }) {
  const [showMethodology, setShowMethodology] = useState(false)

  if (!economics) {
    return <p style={{ color: '#9ca3af', fontStyle: 'italic', padding: '16px 0' }}>
      Ingen økonomidata tilgjengelig
    </p>
  }

  const {
    tiv_nok,
    biomass_tonnes,
    value_per_tonne_nok,
    current_risk_score,
    risk_delta,
    current_annual_el_nok,
    domain_el_delta_nok = {},
    total_el_delta_nok,
    current_scr_nok,
    scr_delta_nok,
    current_annual_premium_nok,
    premium_delta_nok,
    cage_attribution = [],
    methodology,
  } = economics

  const maxAbsDomainEl = Math.max(
    ...DOMAINS.map(d => Math.abs(domain_el_delta_nok[d] || 0)),
    1,
  )

  const totalRiskDelta = risk_delta?.total ?? 0

  return (
    <div className="lr-econ-panel">

      {/* ── Financial profile ─────────────────────────────────────────── */}
      <div className="lr-econ-section">
        <div className="lr-econ-section-title">Finansielt grunnlag</div>
        <div className="lr-econ-profile-grid">
          <div className="lr-econ-profile-item">
            <span className="lr-econ-profile-label">TIV</span>
            <span className="lr-econ-profile-value">{fmtNOKAbs(tiv_nok)}</span>
          </div>
          <div className="lr-econ-profile-item">
            <span className="lr-econ-profile-label">Biomasse</span>
            <span className="lr-econ-profile-value">{biomass_tonnes?.toLocaleString('nb-NO')} t</span>
          </div>
          <div className="lr-econ-profile-item">
            <span className="lr-econ-profile-label">Verdi / tonn</span>
            <span className="lr-econ-profile-value">{value_per_tonne_nok?.toLocaleString('nb-NO')} NOK</span>
          </div>
          <div className="lr-econ-profile-item">
            <span className="lr-econ-profile-label">Risiko nå</span>
            <span className="lr-econ-profile-value">{current_risk_score} pkt</span>
          </div>
        </div>
      </div>

      {/* ── Current annual estimates ───────────────────────────────────── */}
      <div className="lr-econ-section">
        <div className="lr-econ-section-title">Løpende årsestimat</div>
        <div className="lr-econ-kpi-row">
          <KPICard
            label="Forventet tap (EL)"
            value={fmtNOKAbs(current_annual_el_nok)}
            sublabel="per år"
            deltaValue={total_el_delta_nok}
          />
          <KPICard
            label="Solvenskapital (SCR)"
            value={fmtNOKAbs(current_scr_nok)}
            sublabel={`${methodology?.scr_loading ?? ''}× EL`}
            deltaValue={scr_delta_nok}
          />
          <KPICard
            label="Indikativ premie"
            value={fmtNOKAbs(current_annual_premium_nok)}
            sublabel={`${methodology?.premium_loading ?? ''}× EL`}
            deltaValue={premium_delta_nok}
          />
        </div>
      </div>

      {/* ── Period impact summary ──────────────────────────────────────── */}
      <div className="lr-econ-section">
        <div className="lr-econ-section-title">
          Periodens risikodelta
          <span style={{ fontWeight: 400, color: '#6b7280', marginLeft: 6 }}>
            {totalRiskDelta > 0 ? '+' : ''}{totalRiskDelta.toFixed(1)} pkt totalt
          </span>
        </div>

        <div className="lr-econ-domain-table">
          {DOMAINS.map(d => {
            const elDelta = domain_el_delta_nok[d] ?? 0
            const riskD   = risk_delta?.[d] ?? 0
            const pct     = Math.min(100, (Math.abs(elDelta) / maxAbsDomainEl) * 100)
            const color   = DOMAIN_COLORS[d]
            const isPos   = elDelta > 0
            const isNeg   = elDelta < 0
            const deltaColor = isPos ? '#c62828' : isNeg ? '#2e7d32' : '#9ca3af'
            return (
              <div key={d} className="lr-econ-domain-row" style={{ borderLeft: `3px solid ${color}` }}>
                <div className="lr-econ-domain-name" style={{ color }}>{DOMAIN_LABELS[d]}</div>
                <div className="lr-econ-domain-risk-delta" style={{
                  color: riskD > 0 ? '#c62828' : riskD < 0 ? '#2e7d32' : '#9ca3af',
                }}>
                  {riskD > 0 ? '▲ +' : riskD < 0 ? '▼ ' : '● '}{riskD.toFixed(1)} pkt
                </div>
                <div className="lr-econ-domain-bar-wrap">
                  <div
                    className="lr-econ-domain-bar"
                    style={{
                      width: `${pct}%`,
                      background: isPos ? '#fca5a5' : isNeg ? '#bbf7d0' : '#e5e7eb',
                      borderRight: `2px solid ${isPos ? '#ef4444' : isNeg ? '#16a34a' : '#d1d5db'}`,
                    }}
                  />
                </div>
                <div className="lr-econ-domain-el-delta" style={{ color: deltaColor }}>
                  {isPos ? '▲ +' : isNeg ? '▼ ' : '● '}{fmtNOKDelta(elDelta)} NOK
                </div>
              </div>
            )
          })}
        </div>
      </div>

      {/* ── Cage attribution ──────────────────────────────────────────── */}
      {cage_attribution.length > 0 && (
        <div className="lr-econ-section">
          <div className="lr-econ-section-title">
            EL-endring per merder
            <span style={{ fontWeight: 400, color: '#9ca3af', marginLeft: 6, fontSize: 11 }}>
              proporsjonal biomassevekt
            </span>
          </div>
          <div style={{ overflowX: 'auto' }}>
            <table className="lr-econ-cage-table">
              <thead>
                <tr>
                  <th>Merder</th>
                  <th>Andel</th>
                  <th>EL-endring</th>
                  <th style={{ color: DOMAIN_COLORS.biological }}>Bio</th>
                  <th style={{ color: DOMAIN_COLORS.structural }}>Str</th>
                  <th style={{ color: DOMAIN_COLORS.environmental }}>Mil</th>
                  <th style={{ color: DOMAIN_COLORS.operational }}>Ops</th>
                </tr>
              </thead>
              <tbody>
                {cage_attribution.map(c => {
                  const tot  = c.el_delta_nok
                  const tCol = tot > 0 ? '#c62828' : tot < 0 ? '#2e7d32' : '#6b7280'
                  return (
                    <tr key={c.cage_id}>
                      <td style={{ fontWeight: 700 }}>{c.cage_id}</td>
                      <td>{c.biomass_share?.toFixed(1)} %</td>
                      <td style={{ color: tCol, fontWeight: 700 }}>
                        {tot > 0 ? '+' : ''}{fmtNOKDelta(tot)} NOK
                      </td>
                      {DOMAINS.map(dom => {
                        const v = c.domain_el_delta_nok?.[dom] ?? 0
                        return (
                          <td key={dom} style={{
                            color: v > 0 ? '#c62828' : v < 0 ? '#2e7d32' : '#9ca3af',
                            fontSize: 11,
                          }}>
                            {v > 0 ? '+' : ''}{fmtNOKDelta(v)}
                          </td>
                        )
                      })}
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* ── Methodology disclosure ─────────────────────────────────────── */}
      <div className="lr-econ-section">
        <button
          className="lr-econ-method-toggle"
          onClick={() => setShowMethodology(v => !v)}
        >
          {showMethodology ? '▼' : '▶'} Metodebeskrivelse
        </button>
        {showMethodology && methodology && (
          <div className="lr-econ-method-body">
            <p>
              <strong>EL-elastisitet:</strong>{' '}
              {methodology.el_elasticity_per_point} per risikopoeng × TIV
              <br />
              <em>Ref:</em> {(methodology.base_el_rate_at_ref * 100).toFixed(1)} % av TIV
              ved {methodology.reference_risk_score} pkt — lineær skalering.
            </p>
            <p>
              <strong>SCR-faktor:</strong> EL × {methodology.scr_loading}
              <br />
              <em>Ref:</em> Empirisk VaR(99,5 %) / E[tap]-ratio for akvakultur.
            </p>
            <p>
              <strong>Premieindikasjon:</strong> EL × {methodology.premium_loading}
              <br />
              <em>Ref:</em> Markedsloading tilsvarende ~
              {(100 / methodology.premium_loading).toFixed(0)} % skadeverlighet.
            </p>
            <p>
              <strong>Domenvekter:</strong>{' '}
              {Object.entries(methodology.domain_weights || {})
                .map(([k, v]) => `${DOMAIN_LABELS[k] || k} ${(v * 100).toFixed(0)} %`)
                .join(' · ')}
            </p>
            <p className="lr-econ-method-disclaimer">
              {methodology.note}
            </p>
          </div>
        )}
      </div>

    </div>
  )
}
