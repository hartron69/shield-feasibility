import React, { useState } from 'react'
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

const TABS = [
  { id: 'overview',      label: 'Risk Overview' },
  { id: 'biological',    label: 'Biological' },
  { id: 'structural',    label: 'Structural' },
  { id: 'environmental', label: 'Environmental' },
  { id: 'operational',   label: 'Operational' },
  { id: 'learning',      label: 'Learning Status' },
  { id: 'alerts',        label: 'Alerts' },
  { id: 'sites',         label: 'Anlegg' },
]

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
      {activeTab === 'sites' && (
        <SmoltSiteRiskTab />
      )}
    </div>
  )
}
