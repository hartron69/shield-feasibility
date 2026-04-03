import React, { useState, useEffect } from 'react'
import RawDataChart from './RawDataChart.jsx'
import { fetchLiveRiskOcean } from '../../api/client.js'

// NorShelf-fane — viser havmiljøparametere: t_water, Hs, strøm u/v/fart

const DQI_CONFIG = {
  1: { label: 'Live BW (denne timen)', bg: '#e6f4ea', color: '#2e7d32', dot: '#2e7d32' },
  2: { label: 'Stale cache (>55 min)', bg: '#fff8e1', color: '#f57f17', dot: '#f9a825' },
  3: { label: 'Fallback (est.)',        bg: '#f3f4f6', color: '#6b7280', dot: '#9ca3af' },
}

function DqiBadge({ dqi }) {
  const cfg = DQI_CONFIG[dqi] || DQI_CONFIG[3]
  return (
    <span style={{
      display: 'inline-flex', alignItems: 'center', gap: 5,
      background: cfg.bg, color: cfg.color,
      border: `1px solid ${cfg.color}44`,
      borderRadius: 12, padding: '2px 10px', fontSize: 11, fontWeight: 600,
    }}>
      <span style={{ width: 7, height: 7, borderRadius: '50%', background: cfg.dot, display: 'inline-block' }} />
      NorShelf DQI={dqi} — {cfg.label}
    </span>
  )
}

function CurrentSnapshot({ norshelf }) {
  if (!norshelf) return null
  const speed = norshelf.current_speed ?? Math.sqrt(norshelf.u ** 2 + norshelf.v ** 2)
  // Direction in degrees clockwise from North
  const dirDeg = (Math.atan2(norshelf.u, norshelf.v) * 180 / Math.PI + 360) % 360

  return (
    <div style={{
      display: 'flex', gap: 12, flexWrap: 'wrap', marginBottom: 16,
      padding: '10px 14px',
      background: '#f0f9ff',
      border: '1px solid #bae6fd',
      borderRadius: 8,
      alignItems: 'center',
    }}>
      <div style={{ fontWeight: 700, fontSize: 12, color: '#0369a1' }}>NorShelf nå:</div>
      {[
        { label: 'T_water', value: `${norshelf.t_water.toFixed(1)} °C`, color: '#0ea5e9' },
        { label: 'Hs',      value: `${norshelf.hs.toFixed(2)} m`,       color: '#7c3aed' },
        { label: 'Fart',    value: `${speed.toFixed(3)} m/s`,            color: '#059669' },
        { label: 'u (Ø)',   value: `${norshelf.u.toFixed(3)} m/s`,       color: '#d97706' },
        { label: 'v (N)',   value: `${norshelf.v.toFixed(3)} m/s`,       color: '#db2777' },
      ].map(kpi => (
        <div key={kpi.label} style={{
          display: 'flex', flexDirection: 'column', alignItems: 'center',
          background: 'white', border: `1px solid ${kpi.color}33`,
          borderRadius: 6, padding: '4px 10px', minWidth: 72,
        }}>
          <span style={{ fontSize: 10, color: '#6b7280' }}>{kpi.label}</span>
          <span style={{ fontSize: 13, fontWeight: 700, color: kpi.color }}>{kpi.value}</span>
        </div>
      ))}

      {/* Current direction compass arrow */}
      <div title={`Strømretning: ${dirDeg.toFixed(0)}° (vindrose)`}
           style={{ marginLeft: 4, display: 'flex', flexDirection: 'column', alignItems: 'center' }}>
        <svg width={32} height={32} viewBox="-1 -1 2 2">
          <circle cx={0} cy={0} r={0.95} fill="none" stroke="#e5e7eb" strokeWidth={0.1} />
          {/* Arrow rotated to current direction */}
          <g transform={`rotate(${dirDeg})`}>
            <polygon points="0,-0.75 0.18,0.30 0,0.10 -0.18,0.30"
              fill="#059669" />
          </g>
        </svg>
        <span style={{ fontSize: 9, color: '#6b7280' }}>{dirDeg.toFixed(0)}°</span>
      </div>
    </div>
  )
}

export default function OceanDataTab({ localityId, period }) {
  const [data, setData]       = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError]     = useState(null)

  useEffect(() => {
    if (!localityId) return
    setLoading(true)
    setError(null)
    fetchLiveRiskOcean(localityId, period)
      .then(d => { setData(d); setLoading(false) })
      .catch(e => { setError(e.message); setLoading(false) })
  }, [localityId, period])

  if (loading) return (
    <div style={{ padding: 32, textAlign: 'center', color: '#9ca3af', fontSize: 13 }}>
      &#8987; Henter havmiljødata...
    </div>
  )
  if (error) return (
    <div style={{ background: '#fdecea', color: '#c62828', padding: '10px 14px', borderRadius: 8, fontSize: 13 }}>
      {error}
    </div>
  )
  if (!data) return null

  return (
    <div>
      {/* Header — DQI badge + NorShelf snapshot */}
      <div style={{ display: 'flex', gap: 10, alignItems: 'center', flexWrap: 'wrap', marginBottom: 10 }}>
        <DqiBadge dqi={data.norshelf_dqi} />
        <span style={{ fontSize: 11, color: '#9ca3af' }}>
          Tidsserie: syntetisk (historiske NorShelf-modellverdier). Siste punkt: live BW ved DQI≤2.
        </span>
      </div>

      {data.norshelf && <CurrentSnapshot norshelf={data.norshelf} />}

      <RawDataChart series={data.ocean_data || []} period={period} />
    </div>
  )
}
