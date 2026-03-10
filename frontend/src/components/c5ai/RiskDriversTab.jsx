import React, { useState } from 'react'

const DOMAIN_OF_RISK = {
  hab:       { label: 'HAB',       badgeClass: 'badge-environmental' },
  lice:      { label: 'Lice',      badgeClass: 'badge-biological' },
  jellyfish: { label: 'Jellyfish', badgeClass: 'badge-environmental' },
  pathogen:  { label: 'Pathogen',  badgeClass: 'badge-biological' },
}

function ImportanceBar({ value, max = 0.5 }) {
  const pct = Math.min(100, (value / max) * 100)
  return (
    <div>
      <div className="prob-bar-outer">
        <div className="prob-bar-inner" style={{ width: `${pct}%`, background: '#7C3AED' }} />
      </div>
      <div className="driver-imp-pct">{(value * 100).toFixed(0)}%</div>
    </div>
  )
}

export default function RiskDriversTab({ data }) {
  const drivers = data.risk_drivers
  const [selected, setSelected] = useState(0)

  const maxImp = Math.max(...drivers.map(d => d.importance))
  const selectedDriver = drivers[selected]

  return (
    <div>
      <div className="info-note">
        Feature importance is derived from the C5AI+ RandomForest and Bayesian probability
        models. Values represent the fractional contribution of each environmental or
        operational factor to the overall event probability estimate.
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 340px', gap: 20 }}>
        {/* ── Driver list ─────────────────────────────────────────────── */}
        <div className="card" style={{ padding: '12px 16px' }}>
          <div className="section-title">Top Risk Drivers</div>
          {drivers.map((d, i) => {
            const riskMeta = DOMAIN_OF_RISK[d.risk_type] || { label: d.risk_type, badgeClass: 'badge-operational' }
            return (
              <div
                key={i}
                className={`driver-row ${selected === i ? 'selected' : ''}`}
                onClick={() => setSelected(i)}
              >
                <div className="driver-rank">{d.rank}.</div>
                <div className="driver-body">
                  <div className="driver-name">{d.driver}</div>
                  <div className="driver-meta">
                    <span className={`badge ${riskMeta.badgeClass}`}>{riskMeta.label}</span>
                    {' '}
                    <span style={{ fontSize: 11, color: 'var(--dark-grey)' }}>{d.site}</span>
                    {' · '}
                    <span style={{
                      fontSize: 11, fontWeight: 600,
                      color: d.direction === 'positive' ? 'var(--danger)' : 'var(--success)',
                    }}>
                      {d.direction === 'positive' ? '↑ Risk amplifier' : '↓ Risk reducer'}
                    </span>
                  </div>
                </div>
                <div className="driver-imp-bar">
                  <ImportanceBar value={d.importance} max={maxImp} />
                </div>
              </div>
            )
          })}
        </div>

        {/* ── Explainability panel ────────────────────────────────────── */}
        <div>
          <div className="explainability-panel" style={{ position: 'sticky', top: 0 }}>
            <div className="ep-title">Explainability Panel</div>
            <div className="ep-driver-name">{selectedDriver.driver}</div>
            <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap', marginBottom: 10 }}>
              <span className={`badge ${(DOMAIN_OF_RISK[selectedDriver.risk_type] || {}).badgeClass || 'badge-operational'}`}>
                {selectedDriver.risk_type}
              </span>
              <span className="badge badge-cost">{selectedDriver.site}</span>
              <span className="badge" style={{
                background: selectedDriver.direction === 'positive' ? '#FEE2E2' : '#D1FAE5',
                color:      selectedDriver.direction === 'positive' ? '#991B1B' : '#065F46',
              }}>
                Importance: {(selectedDriver.importance * 100).toFixed(0)}%
              </span>
            </div>
            <div className="ep-text">{selectedDriver.description}</div>
          </div>

          {/* ── Summary stats ──────────────────────────────────────── */}
          <div className="card" style={{ marginTop: 16, padding: 14 }}>
            <div className="section-title" style={{ marginBottom: 8 }}>Driver Summary</div>
            <div style={{ fontSize: 12, color: 'var(--dark-grey)', lineHeight: 1.7 }}>
              <div><strong>{drivers.filter(d => d.direction === 'positive').length}</strong> risk amplifiers identified</div>
              <div><strong>{drivers.filter(d => d.direction === 'negative').length}</strong> risk reducer identified</div>
              <div><strong>{[...new Set(drivers.map(d => d.risk_type))].length}</strong> risk types represented</div>
              <div style={{ marginTop: 8, padding: '8px 10px', background: 'var(--light-grey)', borderRadius: 6 }}>
                Top driver (<em>{drivers[0]?.driver}</em>) accounts for{' '}
                <strong>{(drivers[0]?.importance * 100).toFixed(0)}%</strong> of{' '}
                {drivers[0]?.risk_type?.toUpperCase()} probability weighting at {drivers[0]?.site}.
              </div>
            </div>
          </div>

          {/* ── Mitigation pointer ─────────────────────────────────── */}
          <div className="warn-note">
            <strong>Mitigation connection:</strong> Address the top driver ({drivers[0]?.driver}) by
            selecting relevant actions in the <em>Mitigation</em> accordion on the Feasibility page.
            The C5AI+ scale factor will reflect improved biological risk controls.
          </div>
        </div>
      </div>
    </div>
  )
}
