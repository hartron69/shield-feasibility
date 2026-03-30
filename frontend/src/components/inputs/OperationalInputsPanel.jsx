import React, { useState } from 'react'
import InputSourceBadge from './InputSourceBadge.jsx'

const SITE_IDS   = ['KH_S01', 'KH_S02', 'KH_S03']
const SITE_NAMES = { KH_S01: 'Kornstad', KH_S02: 'Leite', KH_S03: 'Hogsnes' }

function formatVal(v) {
  if (v === null || v === undefined) return '—'
  if (typeof v === 'string') return v
  if (Number.isInteger(v))   return String(v)
  return v < 10 ? v.toFixed(2) : v.toFixed(1)
}

function formatDelta(current, baseline) {
  if (typeof current !== 'number' || typeof baseline !== 'number') return '—'
  const d = current - baseline
  return (d >= 0 ? '+' : '') + d.toFixed(2)
}

export default function OperationalInputsPanel({ snapshots, loading }) {
  const [activeSite, setActiveSite] = useState(SITE_IDS[0])

  if (loading) {
    return <div className="inputs-empty">Laster operasjonelle data fra Live Risk…</div>
  }

  const snap = snapshots[activeSite]
  if (!snap) {
    return <div className="inputs-empty">Ingen operasjonelle data tilgjengelig. Start backend for å laste Live Risk-data.</div>
  }

  const domain = snap.operational

  return (
    <div className="bio-panel">
      {/* Site selector */}
      <div className="bio-site-row">
        {SITE_IDS.map(sid => (
          <button
            key={sid}
            className={`bio-site-btn ${activeSite === sid ? 'active' : ''}`}
            onClick={() => setActiveSite(sid)}
          >
            {SITE_NAMES[sid]}
          </button>
        ))}
      </div>

      {/* Header */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 12 }}>
        <span style={{ fontWeight: 600, fontSize: 13 }}>
          {SITE_NAMES[activeSite]} — Operational Indicators
        </span>
        <InputSourceBadge source={domain.source} />
        <span style={{ marginLeft: 'auto', fontSize: 11, color: 'var(--dark-grey)' }}>
          Recorded: {new Date(snap.recorded_at).toLocaleString('nb-NO')}
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
          {domain.readings.map((row, i) => (
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
                {row.adverse
                  ? <span className="threshold-badge threshold-adverse">Adverse</span>
                  : <span className="threshold-badge threshold-ok">OK</span>}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
      <div className="inputs-note">
        Behandlingsbyrde er direkte fra Live Risk (rullerende 30d). Øvrige indikatorer er
        avledet fra operasjonell risikoskår. Bemanning og opplæring er ikke rapportert fra
        operatør — vises som estimater. Oppdateres ved hvert feed-kall.
      </div>
    </div>
  )
}
