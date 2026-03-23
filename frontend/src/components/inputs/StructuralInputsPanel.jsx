import React, { useState } from 'react'
import InputSourceBadge from './InputSourceBadge.jsx'
import { MOCK_STRUCTURAL_INPUTS, STRUCTURAL_SITE_IDS } from '../../data/mockMultiDomainData.js'
import { SITE_REGISTRY } from '../../data/mockInputsData.js'

function deltaClass(current, baseline, adverse) {
  if (adverse) return 'delta-bad'
  if (typeof current === 'number' && typeof baseline === 'number') {
    return current >= baseline ? 'delta-good' : 'delta-bad'
  }
  return ''
}

function formatDelta(current, baseline) {
  if (typeof current !== 'number' || typeof baseline !== 'number') return '—'
  const d = current - baseline
  return (d >= 0 ? '+' : '') + d.toFixed(2)
}

export default function StructuralInputsPanel() {
  const [activeSite, setActiveSite] = useState(STRUCTURAL_SITE_IDS[0])
  const site = MOCK_STRUCTURAL_INPUTS[activeSite]

  return (
    <div className="bio-panel">
      {/* Site selector */}
      <div className="bio-site-row">
        {STRUCTURAL_SITE_IDS.map(sid => (
          <button
            key={sid}
            className={`bio-site-btn ${activeSite === sid ? 'active' : ''}`}
            onClick={() => setActiveSite(sid)}
          >
            {SITE_REGISTRY[sid] || sid}
          </button>
        ))}
      </div>

      {/* Header */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 12 }}>
        <span style={{ fontWeight: 600, fontSize: 13 }}>
          {site.site_name} — Structural Condition
        </span>
        <InputSourceBadge source={site.source} />
        <span style={{ marginLeft: 'auto', fontSize: 11, color: 'var(--dark-grey)' }}>
          Recorded: {new Date(site.recorded_at).toLocaleString('nb-NO')}
        </span>
      </div>

      {/* Table */}
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
              <td style={{ fontWeight: 600 }}>{typeof row.value === 'number' ? row.value.toFixed(typeof row.value === 'number' && row.value > 10 ? 1 : 2) : row.value}</td>
              <td style={{ color: 'var(--dark-grey)' }}>{typeof row.baseline === 'number' ? row.baseline.toFixed(typeof row.baseline > 10 ? 1 : 2) : row.baseline}</td>
              <td className={deltaClass(row.value, row.baseline, row.adverse)}>
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
