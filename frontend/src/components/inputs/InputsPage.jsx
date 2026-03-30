import React, { useState, useEffect } from 'react'
import SiteProfileForm from './SiteProfileForm.jsx'
import BiologicalInputsPanel from './BiologicalInputsPanel.jsx'
import AlertSignalsPanel from './AlertSignalsPanel.jsx'
import DataQualityPanel from './DataQualityPanel.jsx'
import ScenarioOverridePanel from './ScenarioOverridePanel.jsx'
import StructuralInputsPanel from './StructuralInputsPanel.jsx'
import EnvironmentalInputsPanel from './EnvironmentalInputsPanel.jsx'
import OperationalInputsPanel from './OperationalInputsPanel.jsx'
import { MOCK_BIOLOGICAL_INPUTS } from '../../data/mockInputsData.js'
import { fetchInputsSnapshot } from '../../api/client.js'

const TABS = [
  { id: 'site',          label: 'Site Profile' },
  { id: 'bio',           label: 'Biological' },
  { id: 'structural',    label: 'Structural' },
  { id: 'environmental', label: 'Environmental' },
  { id: 'operational',   label: 'Operational' },
  { id: 'signals',       label: 'Alert Signals' },
  { id: 'quality',       label: 'Data Quality' },
  { id: 'scenario',      label: 'Scenario Inputs' },
]

const TAB_DESCRIPTIONS = {
  site:          'Static site information used as inputs to the risk model.',
  bio:           'Environmental and biological readings per site, recorded or simulated.',
  structural:    'Structural condition indicators derived from the Live Risk model (biofouling, wave load, treatment burden).',
  environmental: 'Environmental readings derived from the Live Risk feed (O₂, temperature, wave height).',
  operational:   'Operational indicators derived from treatment burden and operational risk score in the Live Risk model.',
  signals:       'Precursor pattern signals detected by the C5AI+ alert engine.',
  quality:       'Data completeness and confidence indicators per site and risk type.',
  scenario:      'Override baseline inputs to explore alternative risk scenarios.',
}

const KH_SITES = ['KH_S01', 'KH_S02', 'KH_S03']

export default function InputsPage({ operatorType = 'sea', operator }) {
  const [activeTab, setActiveTab] = useState('site')
  const [snapshots, setSnapshots] = useState({})
  const [snapshotsLoading, setSnapshotsLoading] = useState(false)

  useEffect(() => {
    setSnapshotsLoading(true)
    Promise.all(KH_SITES.map(id => fetchInputsSnapshot(id)))
      .then(results => {
        const map = {}
        results.forEach(s => { map[s.locality_id] = s })
        setSnapshots(map)
      })
      .catch(() => {})
      .finally(() => setSnapshotsLoading(false))
  }, [])

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
        {activeTab === 'site'          && <SiteProfileForm />}
        {activeTab === 'bio'           && <BiologicalInputsPanel bioInputs={MOCK_BIOLOGICAL_INPUTS} snapshots={snapshots} />}
        {activeTab === 'structural'    && <StructuralInputsPanel    snapshots={snapshots} loading={snapshotsLoading} />}
        {activeTab === 'environmental' && <EnvironmentalInputsPanel snapshots={snapshots} loading={snapshotsLoading} />}
        {activeTab === 'operational'   && <OperationalInputsPanel   snapshots={snapshots} loading={snapshotsLoading} />}
        {activeTab === 'signals'       && <AlertSignalsPanel />}
        {activeTab === 'quality'       && <DataQualityPanel />}
        {activeTab === 'scenario'      && <ScenarioOverridePanel operatorType={operatorType} operator={operator} />}
      </div>
    </div>
  )
}
