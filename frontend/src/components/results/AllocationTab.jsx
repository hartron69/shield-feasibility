import React from 'react'

function fmt(n, decimals = 0) {
  if (n == null) return '—'
  return n.toLocaleString('nb-NO', { maximumFractionDigits: decimals })
}

function fmtM(n) {
  if (n == null) return '—'
  return `NOK ${(n / 1e6).toFixed(1)} M`
}

function pct(n) {
  if (n == null) return '—'
  return `${(n * 100).toFixed(1)} %`
}

export default function AllocationTab({ allocation }) {
  if (!allocation) {
    return (
      <div className="tab-content" style={{ color: '#888', padding: 24 }}>
        Allocation data not available.
      </div>
    )
  }

  const { tiv_ratio, user_exposure_nok, template_exposure_nok,
          risk_severity_scaled, risk_events_scaled,
          financial_ratios, sites, warnings } = allocation

  return (
    <div className="tab-content">

      {/* ── Warnings ─────────────────────────────────────────────── */}
      {warnings && warnings.length > 0 && (
        <div style={{
          background: '#fff3cd', border: '1px solid #ffc107',
          borderRadius: 6, padding: '10px 14px', marginBottom: 18,
        }}>
          <strong style={{ fontSize: 13 }}>Allocation notices</strong>
          <ul style={{ margin: '6px 0 0 16px', padding: 0, fontSize: 13 }}>
            {warnings.map((w, i) => <li key={i}>{w}</li>)}
          </ul>
        </div>
      )}

      {/* ── Exposure scaling ──────────────────────────────────────── */}
      <div className="kpi-grid" style={{ marginBottom: 24 }}>
        <div className="kpi-card">
          <div className="kpi-label">TIV ratio (user / template)</div>
          <div className="kpi-value">{tiv_ratio != null ? tiv_ratio.toFixed(3) : '—'}</div>
          <div className="kpi-sub">Template biomass exposure: {fmtM(template_exposure_nok)}</div>
        </div>
        <div className="kpi-card">
          <div className="kpi-label">User biomass exposure</div>
          <div className="kpi-value">{fmtM(user_exposure_nok)}</div>
        </div>
        <div className="kpi-card">
          <div className="kpi-label">Scaled mean severity</div>
          <div className="kpi-value">{fmtM(risk_severity_scaled)}</div>
          <div className="kpi-sub">Per-event (used in MC)</div>
        </div>
        <div className="kpi-card">
          <div className="kpi-label">Scaled annual events</div>
          <div className="kpi-value">{risk_events_scaled != null ? risk_events_scaled.toFixed(2) : '—'}</div>
          <div className="kpi-sub">Poisson lambda (used in MC)</div>
        </div>
      </div>

      {/* ── Financial ratios ──────────────────────────────────────── */}
      {financial_ratios && (
        <>
          <h4 style={{ margin: '0 0 8px', fontSize: 13, color: '#555' }}>
            Financial ratios applied (derived from template)
          </h4>
          <div className="kpi-grid" style={{ marginBottom: 24 }}>
            {Object.entries(financial_ratios).map(([k, v]) => (
              <div className="kpi-card" key={k}>
                <div className="kpi-label">{k.replace(/_/g, ' ')}</div>
                <div className="kpi-value" style={{ fontSize: 20 }}>{pct(v)}</div>
              </div>
            ))}
          </div>
        </>
      )}

      {/* ── Biomass valuation ────────────────────────────────────── */}
      {allocation.biomass_valuation && (() => {
        const bv = allocation.biomass_valuation
        const diffPct = bv.suggested_biomass_value_per_tonne > 0
          ? Math.abs(bv.applied_biomass_value_per_tonne - bv.suggested_biomass_value_per_tonne)
            / bv.suggested_biomass_value_per_tonne
          : 0
        const materialDiff = diffPct > 0.20
        return (
          <div style={{ marginBottom: 24 }}>
            <h4 style={{ margin: '0 0 8px', fontSize: 13, color: '#555' }}>
              Biomass valuation
            </h4>

            {bv.user_overridden && (
              <div style={{
                background: materialDiff ? '#fff3cd' : '#f0f8ff',
                border: `1px solid ${materialDiff ? '#ffc107' : '#b8d0e8'}`,
                borderRadius: 6, padding: '7px 12px', marginBottom: 10, fontSize: 12,
              }}>
                {materialDiff
                  ? `Applied biomass value differs from suggestion by ${(diffPct * 100).toFixed(0)} % — verify input`
                  : 'Applied biomass value differs from system suggestion (manual override active)'}
              </div>
            )}

            <div className="kpi-grid">
              <div className="kpi-card">
                <div className="kpi-label">Reference price</div>
                <div className="kpi-value" style={{ fontSize: 20 }}>
                  {bv.reference_price_per_kg} NOK/kg
                </div>
              </div>
              <div className="kpi-card">
                <div className="kpi-label">Realisation factor</div>
                <div className="kpi-value" style={{ fontSize: 20 }}>
                  {(bv.realisation_factor * 100).toFixed(0)} %
                </div>
              </div>
              <div className="kpi-card">
                <div className="kpi-label">Prudence haircut</div>
                <div className="kpi-value" style={{ fontSize: 20 }}>
                  {(bv.prudence_haircut * 100).toFixed(0)} %
                </div>
              </div>
              <div className="kpi-card">
                <div className="kpi-label">Suggested value / tonne</div>
                <div className="kpi-value" style={{ fontSize: 18 }}>
                  {fmtM(bv.suggested_biomass_value_per_tonne * 1000)}
                </div>
                <div className="kpi-sub">per tonne</div>
              </div>
              <div className="kpi-card" style={bv.user_overridden
                ? { borderColor: '#ffc107', background: '#fffdf0' } : {}}>
                <div className="kpi-label">Applied value / tonne</div>
                <div className="kpi-value" style={{ fontSize: 18 }}>
                  {fmt(bv.applied_biomass_value_per_tonne)} NOK
                </div>
                <div className="kpi-sub">
                  {bv.user_overridden ? 'Manual override' : 'From suggestion'}
                </div>
              </div>
            </div>

            <p style={{ fontSize: 11, color: '#888', margin: '4px 0 0' }}>
              Formula: {bv.reference_price_per_kg} NOK/kg &times; 1&#8239;000 &times;{' '}
              {bv.realisation_factor} &times; (1 &minus; {bv.prudence_haircut})
              {' '}= {fmt(Math.round(bv.suggested_biomass_value_per_tonne))} NOK/t
            </p>
          </div>
        )
      })()}

      {/* ── Per-site breakdown ────────────────────────────────────── */}
      {sites && sites.length > 0 && (
        <>
          <h4 style={{ margin: '0 0 8px', fontSize: 13, color: '#555' }}>
            Site allocation breakdown
          </h4>
          <div style={{ overflowX: 'auto' }}>
            <table style={{
              width: '100%', borderCollapse: 'collapse',
              fontSize: 12, minWidth: 640,
            }}>
              <thead>
                <tr style={{ background: '#f0f4f8', textAlign: 'left' }}>
                  {['Site', 'Weight', 'Biomass (t)', 'Biomass value', 'Equipment', 'Infrastructure', 'Revenue', 'TIV'].map(h => (
                    <th key={h} style={{ padding: '6px 10px', borderBottom: '2px solid #ddd' }}>{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {sites.map((s, i) => (
                  <tr key={i} style={{ borderBottom: '1px solid #eee' }}>
                    <td style={{ padding: '5px 10px', fontWeight: 600 }}>{s.name}</td>
                    <td style={{ padding: '5px 10px' }}>{s.weight_pct} %</td>
                    <td style={{ padding: '5px 10px' }}>{fmt(s.biomass_tonnes)}</td>
                    <td style={{ padding: '5px 10px' }}>{fmtM(s.biomass_value_nok)}</td>
                    <td style={{ padding: '5px 10px' }}>{fmtM(s.equipment_value_nok)}</td>
                    <td style={{ padding: '5px 10px' }}>{fmtM(s.infrastructure_value_nok)}</td>
                    <td style={{ padding: '5px 10px' }}>{fmtM(s.annual_revenue_nok)}</td>
                    <td style={{ padding: '5px 10px' }}>{fmtM(s.tiv_nok)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <p style={{ fontSize: 11, color: '#888', marginTop: 8 }}>
            Equipment and infrastructure are derived from template ratios scaled by biomass exposure.
            Financial figures (EBITDA, equity, FCF, assets) are derived from revenue using Nordic Aqua
            benchmark ratios. Override in a full assessment.
          </p>
        </>
      )}
    </div>
  )
}
