import React, { useState } from 'react'

const RISK_TYPE_COLORS = {
  hab:       '#D97706',
  lice:      '#2563EB',
  jellyfish: '#059669',
  pathogen:  '#DC2626',
}

function DeltaCell({ delta, triggered }) {
  const cls = triggered ? 'signal-delta-triggered' : 'signal-delta-ok'
  const sign = delta > 0 ? '+' : ''
  return <span className={`signal-delta ${cls}`}>{sign}{delta.toFixed(2)}</span>
}

export default function AlertSignalsPanel({ signals }) {
  const [siteFilter, setSiteFilter]   = useState('All')
  const [riskFilter, setRiskFilter]   = useState('All')
  const [showOnly, setShowOnly]       = useState(false)  // show only triggered

  if (!signals || signals.length === 0) return <div className="inputs-empty">No alert signals available.</div>

  const sites = ['All', ...new Set(signals.map(s => s.site_name))]
  const risks  = ['All', 'hab', 'lice', 'jellyfish', 'pathogen']

  const filtered = signals.filter(s => {
    if (siteFilter !== 'All' && s.site_name !== siteFilter) return false
    if (riskFilter !== 'All' && s.risk_type !== riskFilter) return false
    if (showOnly && !s.triggered) return false
    return true
  })

  return (
    <div>
      {/* Filters */}
      <div className="signal-filter-row">
        <select className="signal-select" value={siteFilter} onChange={e => setSiteFilter(e.target.value)}>
          {sites.map(s => <option key={s}>{s}</option>)}
        </select>
        <select className="signal-select" value={riskFilter} onChange={e => setRiskFilter(e.target.value)}>
          {risks.map(r => <option key={r}>{r === 'All' ? 'All risks' : r.charAt(0).toUpperCase() + r.slice(1)}</option>)}
        </select>
        <label className="signal-toggle">
          <input type="checkbox" checked={showOnly} onChange={e => setShowOnly(e.target.checked)} />
          {' '}Triggered only
        </label>
        <span style={{ marginLeft:'auto', fontSize:12, color:'var(--dark-grey)' }}>
          {filtered.length} / {signals.length} signals
        </span>
      </div>

      {/* Signals table */}
      <table className="signals-table">
        <thead>
          <tr>
            <th>Site</th>
            <th>Risk Type</th>
            <th>Signal</th>
            <th>Current</th>
            <th>Baseline</th>
            <th>Delta</th>
            <th>Threshold</th>
            <th>Unit</th>
            <th>Triggered</th>
          </tr>
        </thead>
        <tbody>
          {filtered.map((s, i) => (
            <tr key={i} className={s.triggered ? 'signal-row-triggered' : ''}>
              <td style={{ fontWeight: 600 }}>{s.site_name}</td>
              <td>
                <span className="rt-badge" style={{ background: RISK_TYPE_COLORS[s.risk_type] || '#666', color:'#fff' }}>
                  {s.risk_type.toUpperCase()}
                </span>
              </td>
              <td className="signal-name-cell">{s.signal_name}</td>
              <td><strong>{typeof s.current_value === 'number' ? s.current_value.toFixed(2) : s.current_value}</strong></td>
              <td style={{ color:'var(--dark-grey)' }}>{typeof s.baseline_value === 'number' ? s.baseline_value.toFixed(2) : s.baseline_value}</td>
              <td><DeltaCell delta={s.delta} triggered={s.triggered} /></td>
              <td style={{ color:'var(--dark-grey)' }}>{typeof s.threshold === 'number' ? s.threshold.toFixed(2) : s.threshold}</td>
              <td style={{ fontSize: 11, color:'var(--dark-grey)' }}>{s.unit}</td>
              <td>
                {s.triggered
                  ? <span className="triggered-yes">YES</span>
                  : <span className="triggered-no">no</span>}
              </td>
            </tr>
          ))}
        </tbody>
      </table>

      <div className="inputs-note">
        Signals are computed by the C5AI+ pattern detector. Triggered signals
        contribute to the precursor score and may elevate alert level.
      </div>
    </div>
  )
}
