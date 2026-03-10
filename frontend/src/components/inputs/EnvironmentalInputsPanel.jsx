import React, { useState } from 'react'
import InputSourceBadge from './InputSourceBadge.jsx'
import { MOCK_ENVIRONMENTAL_INPUTS, ENVIRONMENTAL_SITE_IDS } from '../../data/mockMultiDomainData.js'

const SITE_NAMES = {
  DEMO_OP_S01: 'Frohavet North',
  DEMO_OP_S02: 'Sunndalsfjord',
  DEMO_OP_S03: 'Storfjorden South',
}

function formatVal(v) {
  if (typeof v === 'string') return v
  if (v === undefined || v === null) return '—'
  return typeof v === 'number' && v < 10 ? v.toFixed(2) : v.toFixed(1)
}

function formatDelta(current, baseline) {
  if (typeof current !== 'number' || typeof baseline !== 'number') return '—'
  const d = current - baseline
  return (d >= 0 ? '+' : '') + d.toFixed(2)
}

export default function EnvironmentalInputsPanel() {
  const [activeSite, setActiveSite] = useState(ENVIRONMENTAL_SITE_IDS[0])
  const site = MOCK_ENVIRONMENTAL_INPUTS[activeSite]

  return (
    <div className="bio-panel">
      <div className="bio-site-row">
        {ENVIRONMENTAL_SITE_IDS.map(sid => (
          <button
            key={sid}
            className={`bio-site-btn ${activeSite === sid ? 'active' : ''}`}
            onClick={() => setActiveSite(sid)}
          >
            {SITE_NAMES[sid]}
          </button>
        ))}
      </div>

      <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 12 }}>
        <span style={{ fontWeight: 600, fontSize: 13 }}>
          {site.site_name} — Environmental Conditions
        </span>
        <InputSourceBadge source={site.source} />
        <span style={{ marginLeft: 'auto', fontSize: 11, color: 'var(--dark-grey)' }}>
          Recorded: {new Date(site.recorded_at).toLocaleString('nb-NO')}
        </span>
      </div>

      <table className="bio-table">
        <thead>
          <tr>
            <th>Parameter</th>
            <th>Current</th>
            <th>Baseline</th>
            <th>Delta</th>
            <th>Unit</th>
            <th>Status</th>
          </tr>
        </thead>
        <tbody>
          {site.readings.map((row, i) => (
            <tr key={i} className={row.adverse ? 'bio-row-adverse' : ''}>
              <td style={{ fontWeight: 500 }}>
                {row.parameter}
                {row.description && (
                  <div style={{ fontSize: 10, color: 'var(--dark-grey)', marginTop: 2 }}>
                    {row.description}
                  </div>
                )}
              </td>
              <td style={{ fontWeight: 600 }}>{formatVal(row.value)}</td>
              <td style={{ color: 'var(--dark-grey)' }}>{formatVal(row.baseline)}</td>
              <td className={row.adverse ? 'delta-bad' : ''}>
                {formatDelta(row.value, row.baseline)}
              </td>
              <td style={{ color: 'var(--dark-grey)', fontSize: 11 }}>{row.unit}</td>
              <td>
                {row.adverse ? (
                  <span className="threshold-badge threshold-adverse">Adverse</span>
                ) : (
                  <span className="threshold-badge threshold-ok">OK</span>
                )}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
