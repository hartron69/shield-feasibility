import React, { useState, useMemo } from 'react'
import AlertSummaryCards from './AlertSummaryCards.jsx'
import AlertTable from './AlertTable.jsx'
import AlertDetailPanel from './AlertDetailPanel.jsx'

const LEVELS = ['All', 'CRITICAL', 'WARNING', 'WATCH', 'NORMAL']
const RISK_TYPES = ['All', 'hab', 'lice', 'jellyfish', 'pathogen']
const DOMAINS = ['All', 'biological', 'structural', 'environmental', 'operational']

const RISK_TYPE_DOMAIN = {
  hab: 'biological', lice: 'biological', jellyfish: 'biological', pathogen: 'biological',
  mooring_failure: 'structural', net_integrity: 'structural', cage_structural: 'structural',
  deformation: 'structural', anchor_deterioration: 'structural',
  oxygen_stress: 'environmental', temperature_extreme: 'environmental',
  current_storm: 'environmental', ice: 'environmental', exposure_anomaly: 'environmental',
  human_error: 'operational', procedure_failure: 'operational',
  equipment_failure: 'operational', incident: 'operational', maintenance_backlog: 'operational',
}

const DOMAIN_COLORS = {
  biological: '#059669', structural: '#2563EB',
  environmental: '#D97706', operational: '#7C3AED',
}

export default function AlertsPage({ alertsData }) {
  const [levelFilter, setLevelFilter]   = useState('All')
  const [riskFilter, setRiskFilter]     = useState('All')
  const [domainFilter, setDomainFilter] = useState('All')
  const [selectedId, setSelectedId]     = useState(null)

  const alerts = alertsData || []

  const filtered = useMemo(() => {
    return alerts.filter(a => {
      if (levelFilter !== 'All' && a.alert_level !== levelFilter) return false
      if (riskFilter !== 'All' && a.risk_type !== riskFilter) return false
      if (domainFilter !== 'All') {
        const domain = a.domain || RISK_TYPE_DOMAIN[a.risk_type] || 'biological'
        if (domain !== domainFilter) return false
      }
      return true
    })
  }, [alerts, levelFilter, riskFilter, domainFilter])

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
        <div className="alert-filter-group">
          <span className="alert-filter-label">Domain:</span>
          {DOMAINS.map(d => (
            <button
              key={d}
              className={`alert-filter-pill ${domainFilter === d ? 'active' : ''}`}
              style={domainFilter === d && d !== 'All' ? { background: DOMAIN_COLORS[d], color: '#fff', borderColor: DOMAIN_COLORS[d] } : {}}
              onClick={() => setDomainFilter(d)}
            >
              {d === 'All' ? 'All' : d.charAt(0).toUpperCase() + d.slice(1)}
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
