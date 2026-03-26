import React, { useState, useEffect } from 'react'
import SummaryTab from './SummaryTab.jsx'
import ChartsTab from './ChartsTab.jsx'
import MitigationTab from './MitigationTab.jsx'
import RecommendationTab from './RecommendationTab.jsx'
import ReportTab from './ReportTab.jsx'
import AllocationTab from './AllocationTab.jsx'
import SmoltAllocationTab from './SmoltAllocationTab.jsx'
import LossHistoryTab from './LossHistoryTab.jsx'
import PoolingTab from './PoolingTab.jsx'
import SeaSiteLossTable from './SeaSiteLossTable.jsx'
import TraceabilityPanel from './TraceabilityPanel.jsx'
import C5AISiteTracePanel from './C5AISiteTracePanel.jsx'

const TABS = ['Summary', 'Charts', 'Mitigation', 'Recommendation', 'Allocation', 'Tapsanalyse', 'Loss History', 'Pooling', 'Report', 'Datagrunnlag']

export default function ResultPanel({ result, selectedMitigations, library, operatorType, smoltFacilities, initialTab, onNavigate }) {
  const [activeTab, setActiveTab] = useState(initialTab || 'Summary')

  useEffect(() => {
    if (initialTab) setActiveTab(initialTab)
  }, [initialTab])

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
  const c5aiMeta = result.c5ai_meta || null

  return (
    <div>
      {c5aiMeta && (
        <div className={`c5ai-trace-strip freshness-${c5aiMeta.freshness || 'missing'}`}>
          <div className="c5ai-trace-row">
            <div className="c5ai-trace-left">
              <span className={`c5ai-freshness-badge badge-${c5aiMeta.freshness || 'missing'}`}>
                {c5aiMeta.freshness === 'fresh' ? 'Oppdatert' : c5aiMeta.freshness === 'stale' ? 'Utdatert' : 'Ikke kjørt'}
              </span>
              <span className="c5ai-trace-label">Basert på C5AI+ kjøring</span>
              {c5aiMeta.run_id && <span className="c5ai-trace-runid">{c5aiMeta.run_id.slice(0, 8)}</span>}
              {c5aiMeta.generated_at && (
                <span className="c5ai-trace-ts">
                  {(() => { try { return new Date(c5aiMeta.generated_at).toLocaleString('nb-NO', {day:'2-digit',month:'2-digit',year:'numeric',hour:'2-digit',minute:'2-digit'}) } catch { return c5aiMeta.generated_at } })()}
                </span>
              )}
            </div>
            <div className="c5ai-trace-right">
              {c5aiMeta.site_count > 0 && (
                <span className="c5ai-trace-chip">Lokaliteter: {c5aiMeta.site_count}</span>
              )}
              {c5aiMeta.data_mode && (
                <span className="c5ai-trace-chip">
                  {c5aiMeta.data_mode === 'real' ? 'Reell data' : c5aiMeta.data_mode === 'mixed' ? 'Blandet' : 'Simulert'}
                </span>
              )}
              {c5aiMeta.domains_used && c5aiMeta.domains_used.length > 0 && (
                <span className="c5ai-trace-chip">{c5aiMeta.domains_used.length} domener</span>
              )}
              {c5aiMeta.c5ai_vs_static_ratio != null && (
                <span className="c5ai-trace-chip" title="C5AI+ biologisk skala vs. statisk modell">
                  Skala: {c5aiMeta.c5ai_vs_static_ratio.toFixed(2)}×
                </span>
              )}
            </div>
          </div>
          {(c5aiMeta.freshness === 'stale' || c5aiMeta.freshness === 'missing') && (
            <div className="c5ai-trace-warning">
              {c5aiMeta.freshness === 'stale'
                ? 'C5AI+-data er utdatert — resultatet kan avvike fra oppdatert risikoanalyse.'
                : 'C5AI+ ble ikke kjørt — risikovurderingen er basert på statisk modell.'}
            </div>
          )}
          {c5aiMeta.source_labels && c5aiMeta.source_labels.length > 0 && (
            <div className="c5ai-trace-sources">
              Datakilde: {c5aiMeta.source_labels.join(' · ')}
            </div>
          )}
        </div>
      )}
      {c5aiMeta && (c5aiMeta.site_trace || []).length > 0 && (
        <C5AISiteTracePanel
          siteTrace={c5aiMeta.site_trace}
          onNavigateToRisk={onNavigate}
        />
      )}
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
        <RecommendationTab baseline={baseline} mitigated={mitigated} />
      )}
      {activeTab === 'Allocation' && (
        operatorType === 'smolt'
          ? <SmoltAllocationTab allocationSummary={allocation} facilities={smoltFacilities} />
          : <AllocationTab allocation={allocation} />
      )}
      {activeTab === 'Tapsanalyse' && (
        <SeaSiteLossTable
          lossAnalysis={result.loss_analysis || null}
          baseline={baseline}
          mitigated={mitigated}
        />
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
      {activeTab === 'Datagrunnlag' && (
        <TraceabilityPanel
          traceability={result.traceability || null}
          onNavigateToRisk={onNavigate}
        />
      )}
    </div>
  )
}
