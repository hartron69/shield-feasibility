import React, { useState, useEffect } from 'react'
import { fetchPatternSignals } from '../../api/client.js'

const KH_SITES = ['KH_S01', 'KH_S02', 'KH_S03']

const DOMAIN_COLORS = {
  biological:   '#7C3AED',
  structural:   '#B45309',
  environmental:'#0891B2',
  operational:  '#6B7280',
}

const RISK_TYPE_COLORS = {
  hab:             '#D97706',
  lice:            '#2563EB',
  jellyfish:       '#059669',
  pathogen:        '#DC2626',
  mooring_failure: '#92400E',
  oxygen_stress:   '#0891B2',
  human_error:     '#6B7280',
}

function DeltaCell({ delta, triggered }) {
  const cls = triggered ? 'signal-delta-triggered' : 'signal-delta-ok'
  const sign = delta > 0 ? '+' : ''
  return <span className={`signal-delta ${cls}`}>{sign}{delta.toFixed(2)}</span>
}

export default function AlertSignalsPanel() {
  const [signals, setSignals]     = useState([])
  const [loading, setLoading]     = useState(false)
  const [siteFilter, setSiteFilter]   = useState('All')
  const [domainFilter, setDomainFilter] = useState('All')
  const [showOnly, setShowOnly]   = useState(false)

  useEffect(() => {
    setLoading(true)
    Promise.all(KH_SITES.map(id => fetchPatternSignals(id)))
      .then(results => {
        const merged = results.flatMap(r => r.signals || [])
        setSignals(merged)
      })
      .catch(() => {})
      .finally(() => setLoading(false))
  }, [])

  if (loading) {
    return <div className="inputs-empty">Laster signaldata fra Live Risk…</div>
  }

  if (signals.length === 0) {
    return <div className="inputs-empty">Ingen signaldata tilgjengelig. Start backend for å laste Live Risk-data.</div>
  }

  const sites   = ['All', ...new Set(signals.map(s => s.site_name))]
  const domains = ['All', 'biological', 'structural', 'environmental', 'operational']

  const filtered = signals.filter(s => {
    if (siteFilter   !== 'All' && s.site_name !== siteFilter)  return false
    if (domainFilter !== 'All' && s.domain    !== domainFilter) return false
    if (showOnly && !s.triggered) return false
    return true
  })

  const triggeredTotal = signals.filter(s => s.triggered).length

  return (
    <div>
      {/* Summary bar */}
      <div style={{ display: 'flex', gap: 16, marginBottom: 12, flexWrap: 'wrap' }}>
        {domains.slice(1).map(d => {
          const count = signals.filter(s => s.domain === d && s.triggered).length
          return (
            <div key={d} style={{
              display: 'flex', alignItems: 'center', gap: 6,
              background: 'var(--panel-bg)', border: '1px solid var(--border)',
              borderRadius: 6, padding: '4px 10px', fontSize: 12,
            }}>
              <span style={{ width: 8, height: 8, borderRadius: '50%', background: DOMAIN_COLORS[d], display: 'inline-block' }} />
              <span style={{ textTransform: 'capitalize', color: 'var(--dark-grey)' }}>{d}</span>
              {count > 0
                ? <span style={{ fontWeight: 700, color: '#DC2626' }}>{count} triggered</span>
                : <span style={{ color: 'var(--dark-grey)' }}>OK</span>}
            </div>
          )
        })}
        <span style={{ marginLeft: 'auto', fontSize: 12, color: 'var(--dark-grey)', alignSelf: 'center' }}>
          {triggeredTotal} / {signals.length} triggered
        </span>
      </div>

      {/* Filters */}
      <div className="signal-filter-row">
        <select className="signal-select" value={siteFilter} onChange={e => setSiteFilter(e.target.value)}>
          {sites.map(s => <option key={s}>{s}</option>)}
        </select>
        <select className="signal-select" value={domainFilter} onChange={e => setDomainFilter(e.target.value)}>
          {domains.map(d => (
            <option key={d} value={d}>
              {d === 'All' ? 'Alle domener' : d.charAt(0).toUpperCase() + d.slice(1)}
            </option>
          ))}
        </select>
        <label className="signal-toggle">
          <input type="checkbox" checked={showOnly} onChange={e => setShowOnly(e.target.checked)} />
          {' '}Kun triggered
        </label>
        <span style={{ marginLeft: 'auto', fontSize: 12, color: 'var(--dark-grey)' }}>
          {filtered.length} / {signals.length} signaler
        </span>
      </div>

      {/* Signals table */}
      <table className="signals-table">
        <thead>
          <tr>
            <th>Lokalitet</th>
            <th>Domene</th>
            <th>Risikotype</th>
            <th>Signal</th>
            <th>Nåværende</th>
            <th>Baseline</th>
            <th>Delta</th>
            <th>Z-skår</th>
            <th>Triggered</th>
          </tr>
        </thead>
        <tbody>
          {filtered.map((s, i) => (
            <tr key={i} className={s.triggered ? 'signal-row-triggered' : ''}>
              <td style={{ fontWeight: 600 }}>{s.site_name}</td>
              <td>
                <span style={{
                  display: 'inline-flex', alignItems: 'center', gap: 4,
                  fontSize: 11, color: DOMAIN_COLORS[s.domain] || '#666',
                }}>
                  <span style={{
                    width: 6, height: 6, borderRadius: '50%',
                    background: DOMAIN_COLORS[s.domain] || '#666',
                    display: 'inline-block',
                  }} />
                  {s.domain}
                </span>
              </td>
              <td>
                <span className="rt-badge" style={{
                  background: RISK_TYPE_COLORS[s.risk_type] || '#666',
                  color: '#fff',
                }}>
                  {s.risk_type.replace(/_/g, ' ').toUpperCase()}
                </span>
              </td>
              <td className="signal-name-cell">{s.signal_name}</td>
              <td><strong>{typeof s.current_value === 'number' ? s.current_value.toFixed(3) : s.current_value}</strong></td>
              <td style={{ color: 'var(--dark-grey)' }}>{typeof s.baseline_value === 'number' ? s.baseline_value.toFixed(3) : s.baseline_value}</td>
              <td><DeltaCell delta={s.delta} triggered={s.triggered} /></td>
              <td style={{ fontSize: 11, color: s.triggered ? '#DC2626' : 'var(--dark-grey)', fontWeight: s.triggered ? 700 : 400 }}>
                {typeof s.z_score === 'number' ? s.z_score.toFixed(2) : '—'}
              </td>
              <td>
                {s.triggered
                  ? <span className="triggered-yes">JA</span>
                  : <span className="triggered-no">nei</span>}
              </td>
            </tr>
          ))}
        </tbody>
      </table>

      <div className="inputs-note">
        Signaler beregnet av C5AI+ PatternDetector med Live Risk-data som input (ikke hardkodet mock).
        Z-skår = (nåværende − baseline) / σ. Triggered ved |z| ≥ 1.5.
        Biologiske typer: hab, lice, jellyfish, pathogen (unike regler).
        Strukturell / miljø / operasjonell: én representativ type per domene.
        Oppdateres ved hvert Live Risk-kall.
      </div>
    </div>
  )
}
