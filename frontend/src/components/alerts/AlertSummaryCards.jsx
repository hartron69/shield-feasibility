import React from 'react'

export default function AlertSummaryCards({ alerts }) {
  if (!alerts || alerts.length === 0) return null

  const total    = alerts.length
  const critical = alerts.filter(a => a.alert_level === 'CRITICAL').length
  const warning  = alerts.filter(a => a.alert_level === 'WARNING').length
  const open     = alerts.filter(a => a.workflow_status === 'OPEN').length

  return (
    <div className="alert-kpi-grid">
      <div className="alert-kpi-card">
        <div className="alert-kpi-label">Total Alerts</div>
        <div className="alert-kpi-value">{total}</div>
      </div>
      <div className="alert-kpi-card alert-kpi-critical">
        <div className="alert-kpi-label">Critical</div>
        <div className="alert-kpi-value">{critical}</div>
      </div>
      <div className="alert-kpi-card alert-kpi-warning">
        <div className="alert-kpi-label">Warning</div>
        <div className="alert-kpi-value">{warning}</div>
      </div>
      <div className="alert-kpi-card">
        <div className="alert-kpi-label">Open</div>
        <div className="alert-kpi-value">{open}</div>
      </div>
    </div>
  )
}
