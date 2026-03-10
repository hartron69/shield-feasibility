import React from 'react'
import InputSourceBadge from './InputSourceBadge.jsx'
import InputCompletenessCard from './InputCompletenessCard.jsx'

const FLAG_ORDER = { SUFFICIENT: 0, LIMITED: 1, POOR: 2, MISSING: 3 }

function FlagPill({ flag }) {
  return <span className={`dq-flag dq-flag-${flag}`}>{flag}</span>
}

function ConfidenceDot({ confidence }) {
  const color = { high:'#16A34A', medium:'#D97706', low:'#DC2626' }[confidence] || '#9CA3AF'
  return (
    <span style={{ display:'inline-flex', alignItems:'center', gap:5 }}>
      <span style={{ width:8, height:8, borderRadius:'50%', background:color, display:'inline-block' }} />
      <span style={{ textTransform:'capitalize' }}>{confidence}</span>
    </span>
  )
}

export default function DataQualityPanel({ qualityData }) {
  if (!qualityData || qualityData.length === 0) return <div className="inputs-empty">No data quality information available.</div>

  return (
    <div>
      {/* Completeness cards row */}
      <div className="dq-completeness-row">
        {qualityData.map(site => (
          <InputCompletenessCard key={site.site_id} site={site} />
        ))}
      </div>

      {/* Detailed quality table */}
      <div className="section-title" style={{ marginTop: 20, marginBottom: 10 }}>Per Risk Type Detail</div>
      <table className="dq-table">
        <thead>
          <tr>
            <th>Site</th>
            <th>Risk Type</th>
            <th>Source</th>
            <th>Completeness</th>
            <th>Confidence</th>
            <th>Quality Flag</th>
            <th>Observations</th>
            <th>Missing Fields</th>
          </tr>
        </thead>
        <tbody>
          {qualityData.flatMap(site =>
            Object.entries(site.risk_types)
              .sort((a, b) => FLAG_ORDER[a[1].flag] - FLAG_ORDER[b[1].flag])
              .map(([rt, d]) => (
                <tr key={`${site.site_id}-${rt}`}>
                  <td style={{ fontWeight: 600 }}>{site.site_name}</td>
                  <td style={{ textTransform: 'capitalize' }}>{rt}</td>
                  <td><InputSourceBadge source={d.source} /></td>
                  <td>
                    <div className="dq-completeness-inline">
                      <div className="dq-bar-track">
                        <div
                          className="dq-bar-fill"
                          style={{
                            width: `${d.completeness * 100}%`,
                            background: d.completeness >= 0.8 ? '#16A34A' : d.completeness >= 0.6 ? '#D97706' : '#DC2626',
                          }}
                        />
                      </div>
                      <span style={{ fontSize: 11 }}>{Math.round(d.completeness * 100)}%</span>
                    </div>
                  </td>
                  <td><ConfidenceDot confidence={d.confidence} /></td>
                  <td><FlagPill flag={d.flag} /></td>
                  <td>{d.n_obs}</td>
                  <td>
                    {d.missing_fields.length === 0
                      ? <span style={{ color:'#16A34A', fontSize:12 }}>None</span>
                      : <span style={{ fontSize:11, color:'var(--dark-grey)' }}>{d.missing_fields.join(', ')}</span>
                    }
                  </td>
                </tr>
              ))
          )}
        </tbody>
      </table>

      <div className="inputs-note">
        SUFFICIENT ≥ 80% complete | LIMITED 60–79% | POOR &lt; 60% | MISSING = no data.
        Confidence drives model selection (prior vs. ML). Improve completeness by uploading
        operator-reported environmental monitoring records.
      </div>
    </div>
  )
}
