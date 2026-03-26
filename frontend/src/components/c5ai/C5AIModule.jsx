import React, { useState, useEffect } from 'react'
import RiskOverviewTab from './RiskOverviewTab.jsx'
import BiologicalForecastTab from './BiologicalForecastTab.jsx'
import StructuralForecastTab from './StructuralForecastTab.jsx'
import EnvironmentalForecastTab from './EnvironmentalForecastTab.jsx'
import OperationalForecastTab from './OperationalForecastTab.jsx'
import LearningStatusTab from './LearningStatusTab.jsx'
import AlertTable from '../alerts/AlertTable.jsx'
import AlertDetailPanel from '../alerts/AlertDetailPanel.jsx'
import SmoltSiteRiskTab from '../smolt/SmoltSiteRiskTab.jsx'
import { MOCK_ALERTS } from '../../data/mockAlertsData.js'
import { fetchBWDataStatus } from '../../api/client.js'

const TABS = [
  { id: 'overview',      label: 'Risk Overview' },
  { id: 'biological',    label: 'Biological' },
  { id: 'structural',    label: 'Structural' },
  { id: 'environmental', label: 'Environmental' },
  { id: 'operational',   label: 'Operational' },
  { id: 'learning',      label: 'Learning Status' },
  { id: 'alerts',        label: 'Alerts' },
  { id: 'barentswatch',  label: 'BarentsWatch' },
  { id: 'sites',         label: 'Anlegg' },
]

const QUALITY_COLORS = {
  SUFFICIENT:  { bg: '#dcfce7', text: '#166534', label: 'TILSTREKKELIG' },
  LIMITED:     { bg: '#fef9c3', text: '#854d0e', label: 'BEGRENSET' },
  POOR:        { bg: '#fee2e2', text: '#991b1b', label: 'SVAK' },
  PRIOR_ONLY:  { bg: '#f1f5f9', text: '#475569', label: 'KUN PRIOR' },
}

function BWQualityBadge({ flag }) {
  const c = QUALITY_COLORS[flag] || QUALITY_COLORS.PRIOR_ONLY
  return (
    <span style={{
      background: c.bg, color: c.text,
      padding: '2px 8px', borderRadius: 4,
      fontSize: 11, fontWeight: 700, letterSpacing: 0.3,
    }}>
      {c.label}
    </span>
  )
}

function BWDataTab() {
  const [status, setStatus] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  useEffect(() => {
    fetchBWDataStatus()
      .then(d => { setStatus(d); setLoading(false) })
      .catch(e => { setError(e.message); setLoading(false) })
  }, [])

  if (loading) return <div style={{ padding: 24, color: 'var(--dark-grey)' }}>Laster BarentsWatch-data…</div>
  if (error)   return <div style={{ padding: 24, color: '#dc2626' }}>Feil: {error}</div>

  if (!status || !status.available) {
    return (
      <div style={{ padding: 24 }}>
        <div style={{ fontWeight: 600, marginBottom: 8 }}>Ingen BarentsWatch-data</div>
        <div style={{ fontSize: 13, color: 'var(--dark-grey)' }}>
          {status?.message || 'Ingen luse-/sykdomsfiler funnet. Kjør Prefetch fra Innstillinger for å hente data.'}
        </div>
      </div>
    )
  }

  const sites = status.sites || []

  return (
    <div style={{ padding: '16px 0' }}>
      <div style={{ marginBottom: 12 }}>
        <span style={{ fontWeight: 600 }}>{status.operator_name}</span>
        <span style={{ marginLeft: 8, fontSize: 12, color: 'var(--dark-grey)' }}>
          {sites.length} lokaliteter
        </span>
      </div>
      <div style={{ marginBottom: 10, fontSize: 12, color: 'var(--dark-grey)', fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.4px' }}>
        Kobling: BW-lokalitet &#8594; Shield-ID
      </div>
      <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13 }}>
        <thead>
          <tr style={{ borderBottom: '2px solid var(--border)' }}>
            <th style={{ textAlign: 'left', padding: '6px 8px', fontWeight: 600 }}>Lokalitet</th>
            <th style={{ textAlign: 'left', padding: '6px 8px', fontWeight: 600 }}>Shield-ID</th>
            <th style={{ textAlign: 'left', padding: '6px 8px', fontWeight: 600 }}>Kvalitet</th>
            <th style={{ textAlign: 'right', padding: '6px 8px', fontWeight: 600 }}>Rapporterte uker</th>
            <th style={{ textAlign: 'right', padding: '6px 8px', fontWeight: 600 }}>C5AI skala</th>
            <th style={{ textAlign: 'left', padding: '6px 8px', fontWeight: 600 }}>Dekning</th>
          </tr>
        </thead>
        <tbody>
          {sites.map(site => {
            const pct = Math.round((site.reported_weeks / (site.data_weeks || 52)) * 100)
            return (
              <tr key={site.site_id} style={{ borderBottom: '1px solid var(--border)' }}>
                <td style={{ padding: '8px 8px' }}>
                  <div style={{ fontWeight: 600 }}>{site.site_name}</div>
                  <div style={{ fontSize: 11, color: 'var(--dark-grey)' }}>{site.site_id}</div>
                </td>
                <td style={{ padding: '8px 8px', fontFamily: 'monospace', fontSize: 11 }}>{site.site_id}</td>
                <td style={{ padding: '8px 8px' }}>
                  <BWQualityBadge flag={site.data_quality_flag} />
                </td>
                <td style={{ textAlign: 'right', padding: '8px 8px' }}>
                  {site.reported_weeks} / {site.data_weeks || 52}
                </td>
                <td style={{ textAlign: 'right', padding: '8px 8px', fontWeight: 600 }}>
                  {site.c5ai_scale != null ? site.c5ai_scale.toFixed(3) + '×' : '—'}
                </td>
                <td style={{ padding: '8px 8px', minWidth: 120 }}>
                  <div style={{ background: '#e2e8f0', borderRadius: 4, height: 8, overflow: 'hidden' }}>
                    <div style={{
                      width: `${pct}%`, height: '100%', borderRadius: 4,
                      background: pct >= 80 ? '#22c55e' : pct >= 40 ? '#eab308' : '#ef4444',
                    }} />
                  </div>
                  <div style={{ fontSize: 10, color: 'var(--dark-grey)', marginTop: 2 }}>{pct}%</div>
                </td>
              </tr>
            )
          })}
        </tbody>
      </table>
      <div style={{ marginTop: 16, fontSize: 11, color: 'var(--dark-grey)' }}>
        Skala &lt;1.0 = lavere biologisk risiko enn statisk modell.
        TILSTREKKELIG ≥24 uker · BEGRENSET ≥12 · SVAK &gt;0 · KUN PRIOR = ingen data.
      </div>
    </div>
  )
}

export default function C5AIModule({ c5aiData, feasibilityResult, operator }) {
  const [activeTab, setActiveTab] = useState('overview')
  const [selectedAlertId, setSelectedAlertId] = useState(null)
  const L = c5aiData.learning
  const status = L.status
  const selectedAlert = MOCK_ALERTS.find(a => a.alert_id === selectedAlertId) || null

  return (
    <div className="c5ai-module">
      {/* Module header */}
      <div className="c5ai-header">
        <div style={{ flex: 1 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
            <div className="c5ai-header-title">C5AI+ Risk Intelligence</div>
            <span className={`c5ai-status-pill c5ai-status-${status}`}>{status.toUpperCase()}</span>
          </div>
          <div className="c5ai-header-sub">
            {c5aiData.metadata.operator_name}
            {' · '}
            {c5aiData.metadata.sites_included.length} sites
            {' · '}
            Horizon {c5aiData.metadata.forecast_horizon_years} years
            {' · '}
            Model {c5aiData.metadata.model_version}
          </div>
        </div>
        <div style={{ textAlign: 'right' }}>
          <div style={{ fontSize: 11, color: 'var(--dark-grey)', marginBottom: 4 }}>
            Cycles completed
          </div>
          <div style={{ fontSize: 22, fontWeight: 700, color: '#7C3AED' }}>
            {L.cycles_completed}
          </div>
        </div>
      </div>

      {/* Tab bar */}
      <div className="tab-bar">
        {TABS.map(t => (
          <button
            key={t.id}
            className={`tab-btn ${activeTab === t.id ? 'active' : ''}`}
            onClick={() => setActiveTab(t.id)}
          >
            {t.label}
          </button>
        ))}
      </div>

      {/* Tab content */}
      {activeTab === 'overview' && (
        <RiskOverviewTab data={c5aiData} feasibilityResult={feasibilityResult} />
      )}
      {activeTab === 'biological' && (
        <BiologicalForecastTab data={c5aiData} />
      )}
      {activeTab === 'structural' && (
        <StructuralForecastTab data={c5aiData} />
      )}
      {activeTab === 'environmental' && (
        <EnvironmentalForecastTab data={c5aiData} />
      )}
      {activeTab === 'operational' && (
        <OperationalForecastTab data={c5aiData} />
      )}
      {activeTab === 'learning' && (
        <LearningStatusTab data={c5aiData} />
      )}
      {activeTab === 'alerts' && (
        <div>
          <div style={{ marginBottom: 12, fontSize: 13, color: 'var(--dark-grey)' }}>
            Early warning signals for this operator's sites. Click a row for details.
          </div>
          <AlertTable
            alerts={MOCK_ALERTS}
            selectedId={selectedAlertId}
            onSelect={setSelectedAlertId}
          />
          {selectedAlert && (
            <AlertDetailPanel
              alert={selectedAlert}
              onClose={() => setSelectedAlertId(null)}
            />
          )}
        </div>
      )}
      {activeTab === 'barentswatch' && (
        <BWDataTab />
      )}
      {activeTab === 'sites' && (
        <SmoltSiteRiskTab />
      )}
    </div>
  )
}
