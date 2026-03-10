import React, { useState } from 'react'
import RiskOverviewTab from './RiskOverviewTab.jsx'
import BiologicalForecastTab from './BiologicalForecastTab.jsx'
import RiskDriversTab from './RiskDriversTab.jsx'
import LearningStatusTab from './LearningStatusTab.jsx'

const TABS = [
  { id: 'overview',    label: 'Risk Overview' },
  { id: 'forecast',   label: 'Biological Forecast' },
  { id: 'drivers',    label: 'Risk Drivers' },
  { id: 'learning',   label: 'Learning Status' },
]

export default function C5AIModule({ c5aiData, feasibilityResult, operator }) {
  const [activeTab, setActiveTab] = useState('overview')
  const L = c5aiData.learning
  const status = L.status

  return (
    <div className="c5ai-module">
      {/* ── Module header ─────────────────────────────────────────────────── */}
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

      {/* ── Tab bar ───────────────────────────────────────────────────────── */}
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

      {/* ── Tab content ───────────────────────────────────────────────────── */}
      {activeTab === 'overview' && (
        <RiskOverviewTab data={c5aiData} feasibilityResult={feasibilityResult} />
      )}
      {activeTab === 'forecast' && (
        <BiologicalForecastTab data={c5aiData} />
      )}
      {activeTab === 'drivers' && (
        <RiskDriversTab data={c5aiData} />
      )}
      {activeTab === 'learning' && (
        <LearningStatusTab data={c5aiData} />
      )}
    </div>
  )
}
