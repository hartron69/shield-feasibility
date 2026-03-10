import React, { useState } from 'react'
import SiteProfileForm from './SiteProfileForm.jsx'
import BiologicalInputsPanel from './BiologicalInputsPanel.jsx'
import AlertSignalsPanel from './AlertSignalsPanel.jsx'
import DataQualityPanel from './DataQualityPanel.jsx'
import ScenarioOverridePanel from './ScenarioOverridePanel.jsx'
import {
  MOCK_SITE_PROFILES,
  MOCK_BIOLOGICAL_INPUTS,
  MOCK_ALERT_SIGNALS,
  MOCK_DATA_QUALITY,
} from '../../data/mockInputsData.js'

const TABS = [
  { id: 'site',      label: 'Site Profile' },
  { id: 'bio',       label: 'Biological Inputs' },
  { id: 'signals',   label: 'Alert Signals' },
  { id: 'quality',   label: 'Data Quality' },
  { id: 'scenario',  label: 'Scenario Inputs' },
]

const TAB_DESCRIPTIONS = {
  site:     'Static site information used as inputs to the risk model.',
  bio:      'Environmental and biological readings per site, recorded or simulated.',
  signals:  'Precursor pattern signals detected by the C5AI+ alert engine.',
  quality:  'Data completeness and confidence indicators per site and risk type.',
  scenario: 'Override baseline inputs to explore alternative risk scenarios.',
}

export default function InputsPage() {
  const [activeTab, setActiveTab] = useState('site')

  return (
    <div className="inputs-page">
      <div className="inputs-header">
        <div style={{ fontWeight: 700, fontSize: 18 }}>C5AI+ Input Data</div>
        <div style={{ fontSize: 13, color: 'var(--dark-grey)', marginTop: 2 }}>
          {TAB_DESCRIPTIONS[activeTab]}
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
      <div className="inputs-tab-content">
        {activeTab === 'site'     && <SiteProfileForm    sites={MOCK_SITE_PROFILES} />}
        {activeTab === 'bio'      && <BiologicalInputsPanel bioInputs={MOCK_BIOLOGICAL_INPUTS} />}
        {activeTab === 'signals'  && <AlertSignalsPanel  signals={MOCK_ALERT_SIGNALS} />}
        {activeTab === 'quality'  && <DataQualityPanel   qualityData={MOCK_DATA_QUALITY} />}
        {activeTab === 'scenario' && <ScenarioOverridePanel />}
      </div>
    </div>
  )
}
