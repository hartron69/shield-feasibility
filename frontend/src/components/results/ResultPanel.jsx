import React, { useState } from 'react'
import SummaryTab from './SummaryTab.jsx'
import ChartsTab from './ChartsTab.jsx'
import MitigationTab from './MitigationTab.jsx'
import RecommendationTab from './RecommendationTab.jsx'
import ReportTab from './ReportTab.jsx'
import AllocationTab from './AllocationTab.jsx'
import LossHistoryTab from './LossHistoryTab.jsx'
import PoolingTab from './PoolingTab.jsx'

const TABS = ['Summary', 'Charts', 'Mitigation', 'Recommendation', 'Allocation', 'Loss History', 'Pooling', 'Report']

export default function ResultPanel({ result, selectedMitigations, library }) {
  const [activeTab, setActiveTab] = useState('Summary')

  if (!result) {
    return (
      <div className="result-placeholder">
        <div className="big-icon">🛡</div>
        <div style={{ fontSize: 16, fontWeight: 600 }}>Shield Risk Platform</div>
        <div style={{ fontSize: 13 }}>
          Fill in the operator profile on the left and click <strong>Run Feasibility</strong> to begin.
        </div>
      </div>
    )
  }

  const { baseline, mitigated, comparison, report, allocation, history, pooling } = result

  return (
    <div>
      <div className="tab-bar">
        {TABS.map((t) => (
          <button key={t} className={`tab-btn ${activeTab === t ? 'active' : ''}`} onClick={() => setActiveTab(t)}>
            {t}
          </button>
        ))}
      </div>

      {activeTab === 'Summary' && (
        <SummaryTab baseline={baseline} mitigated={mitigated} />
      )}
      {activeTab === 'Charts' && (
        <ChartsTab charts={baseline.charts} />
      )}
      {activeTab === 'Mitigation' && (
        <MitigationTab
          comparison={comparison}
          selected={selectedMitigations}
          library={library}
        />
      )}
      {activeTab === 'Recommendation' && (
        <RecommendationTab baseline={baseline} />
      )}
      {activeTab === 'Allocation' && (
        <AllocationTab allocation={allocation} />
      )}
      {activeTab === 'Loss History' && (
        <LossHistoryTab history={history} />
      )}
      {activeTab === 'Pooling' && (
        <PoolingTab pooling={pooling} />
      )}
      {activeTab === 'Report' && (
        <ReportTab report={report} />
      )}
    </div>
  )
}
