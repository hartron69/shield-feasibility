import React from 'react'

function completenessColor(v) {
  if (v >= 0.80) return '#16A34A'
  if (v >= 0.60) return '#D97706'
  return '#DC2626'
}

function confidenceLabel(c) {
  return { high: 'High', medium: 'Medium', low: 'Low' }[c] || c
}

export default function InputCompletenessCard({ site }) {
  const pct = Math.round(site.overall_completeness * 100)
  const color = completenessColor(site.overall_completeness)

  return (
    <div className="completeness-card">
      <div className="completeness-site-name">{site.site_name}</div>
      <div className="completeness-bar-wrap">
        <div className="completeness-bar-track">
          <div
            className="completeness-bar-fill"
            style={{ width: `${pct}%`, background: color }}
          />
        </div>
        <span className="completeness-pct" style={{ color }}>{pct}%</span>
      </div>
      <div className="completeness-conf">
        Confidence: <strong>{confidenceLabel(site.overall_confidence)}</strong>
      </div>
      <div className="completeness-flags">
        {Object.entries(site.risk_types).map(([rt, d]) => (
          <span key={rt} className={`dq-flag dq-flag-${d.flag}`}>
            {rt.charAt(0).toUpperCase() + rt.slice(1)}: {d.flag}
          </span>
        ))}
      </div>
    </div>
  )
}
