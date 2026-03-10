import React from 'react'
import AlertLevelBadge from './AlertLevelBadge.jsx'
import ProbabilityShiftBadge from './ProbabilityShiftBadge.jsx'

export default function AlertTable({ alerts, selectedId, onSelect }) {
  if (!alerts || alerts.length === 0) {
    return <div className="alert-empty">No alerts matching current filters.</div>
  }

  return (
    <table className="alert-table">
      <thead>
        <tr>
          <th>Level</th>
          <th>Site</th>
          <th>Risk Type</th>
          <th>Probability</th>
          <th>Shift</th>
          <th>Type</th>
          <th>Status</th>
          <th>Generated</th>
        </tr>
      </thead>
      <tbody>
        {alerts.map(a => (
          <tr
            key={a.alert_id}
            className={`alert-row${selectedId === a.alert_id ? ' selected' : ''}`}
            onClick={() => onSelect && onSelect(a.alert_id === selectedId ? null : a.alert_id)}
          >
            <td><AlertLevelBadge level={a.alert_level} /></td>
            <td style={{ fontWeight: 600 }}>{a.site_id}</td>
            <td style={{ textTransform: 'capitalize' }}>{a.risk_type}</td>
            <td>{(a.current_probability * 100).toFixed(1)}%</td>
            <td>
              <ProbabilityShiftBadge delta={a.probability_delta} />
            </td>
            <td style={{ fontSize: 11, color: 'var(--dark-grey)', textTransform: 'capitalize' }}>
              {a.alert_type.replace('_', ' ')}
            </td>
            <td>
              <span className={`workflow-badge workflow-${a.workflow_status}`}>
                {a.workflow_status}
              </span>
            </td>
            <td style={{ fontSize: 11, color: 'var(--dark-grey)' }}>
              {a.generated_at ? new Date(a.generated_at).toLocaleString('en-GB', { dateStyle: 'short', timeStyle: 'short' }) : '—'}
            </td>
          </tr>
        ))}
      </tbody>
    </table>
  )
}
