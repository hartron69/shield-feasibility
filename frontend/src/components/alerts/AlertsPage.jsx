import React, { useState, useMemo } from 'react'
import AlertSummaryCards from './AlertSummaryCards.jsx'
import AlertTable from './AlertTable.jsx'
import AlertDetailPanel from './AlertDetailPanel.jsx'

const LEVELS = ['All', 'CRITICAL', 'WARNING', 'WATCH', 'NORMAL']
const RISK_TYPES = ['All', 'hab', 'lice', 'jellyfish', 'pathogen']

export default function AlertsPage({ alertsData }) {
  const [levelFilter, setLevelFilter]     = useState('All')
  const [riskFilter, setRiskFilter]       = useState('All')
  const [selectedId, setSelectedId]       = useState(null)

  const alerts = alertsData || []

  const filtered = useMemo(() => {
    return alerts.filter(a => {
      if (levelFilter !== 'All' && a.alert_level !== levelFilter) return false
      if (riskFilter !== 'All' && a.risk_type !== riskFilter) return false
      return true
    })
  }, [alerts, levelFilter, riskFilter])

  const selectedAlert = useMemo(
    () => alerts.find(a => a.alert_id === selectedId) || null,
    [alerts, selectedId],
  )

  return (
    <div className="alerts-page">
      <div className="alerts-page-header">
        <div style={{ fontWeight: 700, fontSize: 18 }}>Early Warning / Alert Layer</div>
        <div style={{ fontSize: 13, color: 'var(--dark-grey)' }}>
          Real-time precursor detection and probability shift monitoring across all sites
        </div>
      </div>

      {/* ── KPI summary row ────────────────────────────────────────────────── */}
      <AlertSummaryCards alerts={alerts} />

      {/* ── Filter pills ───────────────────────────────────────────────────── */}
      <div className="alert-filter-row">
        <div className="alert-filter-group">
          <span className="alert-filter-label">Level:</span>
          {LEVELS.map(l => (
            <button
              key={l}
              className={`alert-filter-pill ${levelFilter === l ? 'active' : ''} ${l !== 'All' ? `pill-${l}` : ''}`}
              onClick={() => setLevelFilter(l)}
            >
              {l}
            </button>
          ))}
        </div>
        <div className="alert-filter-group">
          <span className="alert-filter-label">Risk type:</span>
          {RISK_TYPES.map(r => (
            <button
              key={r}
              className={`alert-filter-pill ${riskFilter === r ? 'active' : ''}`}
              onClick={() => setRiskFilter(r)}
            >
              {r === 'All' ? 'All' : r.charAt(0).toUpperCase() + r.slice(1)}
            </button>
          ))}
        </div>
        <div style={{ marginLeft: 'auto', fontSize: 12, color: 'var(--dark-grey)' }}>
          {filtered.length} of {alerts.length} alerts
        </div>
      </div>

      {/* ── Alert table ────────────────────────────────────────────────────── */}
      <div className="card" style={{ padding: 0 }}>
        <AlertTable alerts={filtered} selectedId={selectedId} onSelect={setSelectedId} />
      </div>

      {/* ── Detail panel ───────────────────────────────────────────────────── */}
      {selectedAlert && (
        <AlertDetailPanel
          alert={selectedAlert}
          onClose={() => setSelectedId(null)}
        />
      )}
    </div>
  )
}
