import React from 'react'

function pct(v) { return v != null ? `${(v * 100).toFixed(0)} %` : '—' }
function nok(v) {
  if (v == null) return '—'
  const m = v / 1_000_000
  return m >= 1 ? `NOK ${m.toFixed(1)} M` : `NOK ${(v / 1_000).toFixed(0)} k`
}

const NO_NAMES = {
  stronger_nets:           'Sterkere nøter',
  stronger_anchors:        'Forsterket ankring',
  stronger_moorings:       'Fortøyningssystem',
  lice_barriers:           'Lusebeskyttelse',
  jellyfish_mitigation:    'Manettbarrierer',
  environmental_sensors:   'Miljøsensorer (O₂/temp)',
  storm_contingency_plan:  'Stormberedskap',
  staff_training_program:  'Personalkompetanse',
  deformation_monitoring:  'Deformasjonsovervåkning',
  ai_early_warning:        'AI-tidligvarsel',
  risk_manager_hire:       'Risikoleder',
  emergency_response_plan: 'Beredskapsplan',
}

function actionName(a) {
  return NO_NAMES[a.id] || a.name.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase())
}

export default function MitigationTab({ comparison, selected, library }) {
  const libMap = Object.fromEntries((library || []).map((a) => [a.id, a]))
  const actions = (selected || []).map((id) => libMap[id]).filter(Boolean)

  if (!actions.length) {
    return (
      <div className="card" style={{ textAlign: 'center', color: 'var(--dark-grey)', padding: 40 }}>
        Ingen tiltak valgt. Velg tiltak i Mitigation-panelet til venstre og kjør analysen på nytt.
      </div>
    )
  }

  return (
    <div>
      <div className="card">
        <div className="section-title">Valgte tiltak</div>
        <table className="data-table">
          <thead>
            <tr>
              <th>Tiltak</th>
              <th>Domene</th>
              <th>Frekvensred.</th>
              <th>Alvorlighetsred.</th>
              <th>Årskostnad</th>
            </tr>
          </thead>
          <tbody>
            {actions.map((a) => (
              <tr key={a.id}>
                <td style={{ fontWeight: 600 }}>{actionName(a)}</td>
                <td>{a.affected_domains.slice(0, 2).join(', ')}</td>
                <td>{pct(a.probability_reduction)}</td>
                <td>{pct(a.severity_reduction)}</td>
                <td>{nok(a.annual_cost_nok)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {comparison && (
        <div className="card">
          <div className="section-title">Porteføljeeffekt</div>
          <div className="kpi-grid" style={{ gridTemplateColumns: 'repeat(auto-fill, minmax(180px, 1fr))' }}>
            <div className="kpi-card">
              <div className="kpi-label">Forventet tapsdelta</div>
              <div className="kpi-value" style={{
                color: comparison.expected_loss_delta < 0 ? 'var(--success)' : 'var(--danger)',
                fontSize: 18,
              }}>
                {comparison.expected_loss_delta_pct.toFixed(1)} %
              </div>
            </div>
            <div className="kpi-card">
              <div className="kpi-label">SCR-endring</div>
              <div className="kpi-value" style={{
                color: comparison.scr_delta < 0 ? 'var(--success)' : 'var(--danger)',
                fontSize: 18,
              }}>
                {nok(comparison.scr_delta)}
              </div>
            </div>
            <div className="kpi-card">
              <div className="kpi-label">Netto besparelse/år</div>
              <div className="kpi-value" style={{
                color: comparison.annual_cost_saving > 0 ? 'var(--success)' : 'var(--danger)',
                fontSize: 18,
              }}>
                {nok(comparison.annual_cost_saving)}
              </div>
            </div>
            {comparison.composite_score_delta != null && (
              <div className="kpi-card">
                <div className="kpi-label">Composite Score-endring</div>
                <div className="kpi-value" style={{
                  color: comparison.composite_score_delta > 0 ? 'var(--success)' : comparison.composite_score_delta < 0 ? 'var(--danger)' : 'var(--dark-grey)',
                  fontSize: 18,
                }}>
                  {comparison.composite_score_delta > 0 ? '+' : ''}{comparison.composite_score_delta.toFixed(1)} pts
                </div>
              </div>
            )}
            <div className="kpi-card">
              <div className="kpi-label">Beste risikodomener</div>
              <div className="kpi-value" style={{ fontSize: 13, marginTop: 8 }}>
                {comparison.top_benefit_domains.join(', ')}
              </div>
            </div>
          </div>
          {comparison.mitigation_score_note && (
            <div style={{
              marginTop: 12, padding: '8px 12px', borderRadius: 6,
              background: '#F0F9FF', border: '1px solid #BAE6FD',
              fontSize: 12, color: '#0369A1',
            }}>
              {comparison.mitigation_score_note}
            </div>
          )}
          {comparison.narrative && (
            <div style={{ marginTop: 12, fontSize: 13, color: 'var(--dark-grey)' }}>
              {comparison.narrative}
            </div>
          )}
        </div>
      )}

      {comparison?.criterion_deltas?.length > 0 && (
        <div className="card">
          <div className="section-title">Kriterievis score-endring</div>
          <table className="data-table">
            <thead>
              <tr>
                <th>Kriterium</th>
                <th>Vekt</th>
                <th>Baseline</th>
                <th>Med tiltak</th>
                <th>Delta (vektet)</th>
              </tr>
            </thead>
            <tbody>
              {comparison.criterion_deltas.map((d) => (
                <tr key={d.name}>
                  <td style={{ fontWeight: 600 }}>{d.name}</td>
                  <td>{(d.weight * 100).toFixed(1)} %</td>
                  <td>{d.baseline_raw.toFixed(0)}</td>
                  <td>{d.mitigated_raw.toFixed(0)}</td>
                  <td style={{
                    fontWeight: 700,
                    color: d.delta_weighted > 0.05 ? 'var(--success)' : d.delta_weighted < -0.05 ? 'var(--danger)' : 'var(--dark-grey)',
                  }}>
                    {d.delta_weighted > 0 ? '+' : ''}{d.delta_weighted.toFixed(2)}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}
