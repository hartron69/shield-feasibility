import React, { useState } from 'react'
import InputSourceBadge from './InputSourceBadge.jsx'
import { BIO_READING_LABELS } from '../../data/mockInputsData.js'

function deltaClass(key, delta) {
  // For oxygen, lower is worse (bad = positive delta means drop, but delta = current-baseline)
  // Actually delta = current - baseline; negative delta for oxygen means current < baseline = bad
  const lowerIsBad = ['dissolved_oxygen_mg_l', 'salinity_ppt']
  if (lowerIsBad.includes(key)) {
    if (delta < -0.5) return 'delta-bad'
    if (delta > 0.5)  return 'delta-good'
  } else {
    if (delta > 0)    return 'delta-warn'
    if (delta < 0)    return 'delta-good'
  }
  return ''
}

function fmtDelta(delta) {
  const sign = delta > 0 ? '+' : ''
  return `${sign}${delta.toFixed(2)}`
}

export default function BiologicalInputsPanel({ bioInputs }) {
  const [selectedSite, setSelectedSite] = useState(bioInputs?.[0]?.site_id || '')

  if (!bioInputs || bioInputs.length === 0) return <div className="inputs-empty">No biological inputs available.</div>

  const site = bioInputs.find(s => s.site_id === selectedSite) || bioInputs[0]
  const readings = site.readings

  return (
    <div>
      {/* Site selector */}
      <div className="bio-site-selector">
        {bioInputs.map(s => (
          <button
            key={s.site_id}
            className={`bio-site-btn ${selectedSite === s.site_id ? 'active' : ''}`}
            onClick={() => setSelectedSite(s.site_id)}
          >
            {s.site_name}
          </button>
        ))}
        <span className="bio-recorded-at">
          Recorded: {site.recorded_at ? new Date(site.recorded_at).toLocaleString('en-GB', { dateStyle: 'short', timeStyle: 'short' }) : '—'}
        </span>
        <InputSourceBadge source={site.data_source} />
      </div>

      {/* Readings table */}
      <table className="bio-table">
        <thead>
          <tr>
            <th>Parameter</th>
            <th>Current</th>
            <th>Baseline</th>
            <th>Delta</th>
            <th>Unit</th>
            <th>Source</th>
          </tr>
        </thead>
        <tbody>
          {Object.entries(readings).map(([key, r]) => {
            const delta = r.value - r.baseline
            const cls = deltaClass(key, delta)
            return (
              <tr key={key}>
                <td className="bio-param-name">{BIO_READING_LABELS[key] || key}</td>
                <td className="bio-current">
                  <strong>{typeof r.value === 'number' ? r.value.toFixed(typeof r.value === 'number' && r.value < 10 ? 2 : 1) : r.value}</strong>
                </td>
                <td className="bio-baseline" style={{ color: 'var(--dark-grey)' }}>
                  {typeof r.baseline === 'number' ? r.baseline.toFixed(r.baseline < 10 ? 2 : 1) : r.baseline}
                </td>
                <td className={`bio-delta ${cls}`}>{fmtDelta(delta)}</td>
                <td className="bio-unit">{r.unit}</td>
                <td><InputSourceBadge source={r.source} /></td>
              </tr>
            )
          })}
        </tbody>
      </table>

      <div className="inputs-note">
        Delta = Current − Baseline. Red = adverse deviation; green = improvement.
        Data source is simulated for all readings in demo mode.
      </div>
    </div>
  )
}
