import React, { useState } from 'react'

const DOMAIN_COLOR = '#D97706'
const SITE_IDS = ['KH_S01', 'KH_S02', 'KH_S03']
const SITE_NAMES = {
  KH_S01: 'Kornstad',
  KH_S02: 'Leite',
  KH_S03: 'Hogsnes',
}
const RISK_LABELS = {
  oxygen_stress:       'Oksygenstress',
  temperature_extreme: 'Temperaturekstrem',
  current_storm:       'Strøm / Storm',
  ice:                 'Isrisiko',
  exposure_anomaly:    'Eksponeringsanomalier',
}

function fmtM(v) {
  if (v >= 1_000_000) return `NOK ${(v / 1_000_000).toFixed(1)}M`
  return `NOK ${Math.round(v / 1_000)}k`
}

function probColor(p) {
  if (p >= 0.30) return '#B91C1C'
  if (p >= 0.15) return '#D97706'
  return '#059669'
}

function ConfidenceBar({ score }) {
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
      <div style={{ flex: 1, height: 4, background: '#E5E7EB', borderRadius: 2 }}>
        <div style={{ width: `${score * 100}%`, height: '100%', background: DOMAIN_COLOR, borderRadius: 2 }} />
      </div>
      <span style={{ fontSize: 10, color: 'var(--dark-grey)', width: 28 }}>{(score * 100).toFixed(0)}%</span>
    </div>
  )
}

function RiskCard({ riskType, data }) {
  const label = RISK_LABELS[riskType] || riskType
  const prob = data.probability
  return (
    <div className="domain-forecast-card">
      <div className="domain-risk-label" style={{ borderLeftColor: DOMAIN_COLOR }}>
        {label}
      </div>
      <div style={{ display: 'flex', gap: 16, marginBottom: 8 }}>
        <div>
          <div style={{ fontSize: 10, color: 'var(--dark-grey)' }}>Sannsynlighet</div>
          <div style={{ fontWeight: 700, fontSize: 18, color: probColor(prob) }}>
            {(prob * 100).toFixed(1)}%
          </div>
        </div>
        <div>
          <div style={{ fontSize: 10, color: 'var(--dark-grey)' }}>Forv. tap</div>
          <div style={{ fontWeight: 600, fontSize: 14 }}>{fmtM(data.expected_loss_mean)}</div>
        </div>
        <div>
          <div style={{ fontSize: 10, color: 'var(--dark-grey)' }}>P90-tap</div>
          <div style={{ fontWeight: 600, fontSize: 14, color: 'var(--dark-grey)' }}>{fmtM(data.expected_loss_p90)}</div>
        </div>
      </div>
      <div style={{ marginBottom: 6 }}>
        <div style={{ fontSize: 10, color: 'var(--dark-grey)', marginBottom: 2 }}>Modellsikkerhet</div>
        <ConfidenceBar score={data.confidence} />
      </div>
      {data.drivers && data.drivers.length > 0 && (
        <div>
          <div style={{ fontSize: 10, color: 'var(--dark-grey)', marginBottom: 2 }}>Viktigste drivere</div>
          <ul style={{ margin: 0, paddingLeft: 14, fontSize: 11, color: 'var(--navy)' }}>
            {data.drivers.map((d, i) => <li key={i}>{d}</li>)}
          </ul>
        </div>
      )}
    </div>
  )
}

export default function EnvironmentalForecastTab({ data }) {
  const [activeSite, setActiveSite] = useState(SITE_IDS[0])
  const forecasts = data.environmental_forecast || []
  const siteForecast = forecasts.find(f => f.site_id === activeSite)

  return (
    <div>
      <div className="domain-forecast-header" style={{ borderLeftColor: DOMAIN_COLOR }}>
        <span style={{ fontWeight: 700, color: DOMAIN_COLOR }}>Miljørisikoprognose</span>
        <span style={{ fontSize: 12, color: 'var(--dark-grey)', marginLeft: 8 }}>
          Oksygenstress · Temperatur · Storm · Is · Eksponering
        </span>
      </div>

      <div className="bio-site-row" style={{ marginBottom: 16 }}>
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

      {siteForecast ? (
        <div className="domain-forecast-grid">
          {Object.entries(siteForecast.risks).map(([rt, rdata]) => (
            <RiskCard key={rt} riskType={rt} data={rdata} />
          ))}
        </div>
      ) : (
        <div style={{ color: 'var(--dark-grey)', fontSize: 13 }}>Ingen miljøprognosedata tilgjengelig.</div>
      )}
    </div>
  )
}
