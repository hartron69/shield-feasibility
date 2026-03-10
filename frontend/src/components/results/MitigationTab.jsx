import React from 'react'

function pct(v) { return v != null ? `${(v * 100).toFixed(0)}%` : '—' }
function nok(v) { if (v == null) return '—'; const m = v / 1_000_000; return m >= 1 ? `NOK ${m.toFixed(1)}M` : `NOK ${(v/1000).toFixed(0)}k` }

export default function MitigationTab({ comparison, selected, library }) {
  const libMap = Object.fromEntries((library || []).map((a) => [a.id, a]))
  const actions = (selected || []).map((id) => libMap[id]).filter(Boolean)

  if (!actions.length) {
    return (
      <div className="card" style={{ textAlign: 'center', color: 'var(--dark-grey)', padding: 40 }}>
        No mitigation actions selected. Enable actions in the Mitigation panel and re-run.
      </div>
    )
  }

  return (
    <div>
      <div className="card">
        <div className="section-title">Selected Actions</div>
        <table className="data-table">
          <thead>
            <tr>
              <th>Action</th>
              <th>Domain(s)</th>
              <th>Freq. Reduction</th>
              <th>Severity Reduction</th>
              <th>Annual Cost</th>
            </tr>
          </thead>
          <tbody>
            {actions.map((a) => (
              <tr key={a.id}>
                <td style={{ fontWeight: 600 }}>{a.name.replace(/_/g, ' ')}</td>
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
          <div className="section-title">Portfolio Impact</div>
          <div className="kpi-grid" style={{ gridTemplateColumns: 'repeat(auto-fill, minmax(180px, 1fr))' }}>
            <div className="kpi-card">
              <div className="kpi-label">Expected Loss Delta</div>
              <div className="kpi-value" style={{ color: comparison.expected_loss_delta < 0 ? 'var(--success)' : 'var(--danger)', fontSize: 18 }}>
                {comparison.expected_loss_delta_pct.toFixed(1)}%
              </div>
            </div>
            <div className="kpi-card">
              <div className="kpi-label">SCR Delta</div>
              <div className="kpi-value" style={{ color: comparison.scr_delta < 0 ? 'var(--success)' : 'var(--danger)', fontSize: 18 }}>
                {nok(comparison.scr_delta)}
              </div>
            </div>
            <div className="kpi-card">
              <div className="kpi-label">Top Benefit Domains</div>
              <div className="kpi-value" style={{ fontSize: 13, marginTop: 8 }}>
                {comparison.top_benefit_domains.join(', ')}
              </div>
            </div>
          </div>
          <div style={{ marginTop: 12, fontSize: 13, color: 'var(--dark-grey)' }}>
            {comparison.narrative}
          </div>
        </div>
      )}
    </div>
  )
}
