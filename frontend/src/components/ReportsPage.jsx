import React, { useState } from 'react'
import { fetchInputsAudit } from '../api/client'

const REPORT_TYPES = [
  {
    id: 'board_pdf',
    title: 'Board Risk Report (PDF)',
    description: 'Full 13-page board-level PDF: executive summary, Monte Carlo results, domain correlation, correlated risk scenarios, mitigation comparison, PCC suitability verdict.',
    status: 'available',
    action: 'Download via PCC Feasibility → run analysis → Report tab',
    icon: '📄',
  },
  {
    id: 'c5ai_summary',
    title: 'C5AI+ Biological Risk Summary',
    description: 'Forecasted event probabilities, risk drivers, and learning status for all sites. Suitable for operational team briefings.',
    status: 'planned',
    action: 'Export planned — wiring to /api/c5ai/export in roadmap.',
    icon: '🧬',
  },
  {
    id: 'alert_log',
    title: 'Alert History Log (CSV)',
    description: 'All alert records with explanations, triggered rules, recommended actions, and workflow status. Suitable for regulatory submission.',
    status: 'planned',
    action: 'Export planned — wiring to /api/alerts/export in roadmap.',
    icon: '⚠️',
  },
  {
    id: 'input_audit',
    title: 'Input Data Audit Report',
    description: 'Data completeness, confidence flags, source annotations, and missing field inventory per site and risk type.',
    status: 'available',
    action: null, // handled via custom component
    icon: '📊',
  },
]

const STATUS_STYLE = {
  available: { bg:'#D1FAE5', color:'#065F46', label:'Available' },
  planned:   { bg:'#F3F4F6', color:'#6B7280', label:'Planned'   },
}

const FLAG_STYLE = {
  SUFFICIENT: { bg:'#D1FAE5', color:'#065F46' },
  LIMITED:    { bg:'#FEF3C7', color:'#92400E' },
  POOR:       { bg:'#FEE2E2', color:'#991B1B' },
}

const FRESHNESS_STYLE = {
  fresh:   { bg:'#D1FAE5', color:'#065F46' },
  stale:   { bg:'#FEF3C7', color:'#92400E' },
  missing: { bg:'#FEE2E2', color:'#991B1B' },
}

function AuditSummaryPanel({ report }) {
  const { summary, c5ai_status, domain_coverage, model_limitations, sites, generated_at } = report
  const fs = FRESHNESS_STYLE[c5ai_status.freshness] || FRESHNESS_STYLE.missing

  return (
    <div className="audit-report-panel">
      {/* Header */}
      <div className="audit-report-header">
        <div>
          <div style={{ fontWeight: 700, fontSize: 14 }}>Input Data Audit Report</div>
          <div style={{ fontSize: 11, color: '#6b7280', marginTop: 2 }}>
            {report.operator} — generert {new Date(generated_at).toLocaleString('nb-NO')}
          </div>
        </div>
        <span className="audit-freshness-badge" style={{ background: fs.bg, color: fs.color }}>
          C5AI+: {c5ai_status.freshness}
        </span>
      </div>

      {/* Summary KPIs */}
      <div className="audit-kpi-row">
        <div className="audit-kpi">
          <div className="audit-kpi-value">{summary.total_sites}</div>
          <div className="audit-kpi-label">Anlegg</div>
        </div>
        <div className="audit-kpi">
          <div className="audit-kpi-value">{summary.total_risk_types_assessed}</div>
          <div className="audit-kpi-label">Risikotyper</div>
        </div>
        <div className="audit-kpi" style={{ color: '#065F46' }}>
          <div className="audit-kpi-value">{summary.sufficient_count}</div>
          <div className="audit-kpi-label">Tilstrekkelig</div>
        </div>
        <div className="audit-kpi" style={{ color: '#92400E' }}>
          <div className="audit-kpi-value">{summary.limited_count}</div>
          <div className="audit-kpi-label">Begrenset</div>
        </div>
        <div className="audit-kpi" style={{ color: '#991B1B' }}>
          <div className="audit-kpi-value">{summary.poor_count}</div>
          <div className="audit-kpi-label">Lav</div>
        </div>
        <div className="audit-kpi">
          <div className="audit-kpi-value">{Math.round(summary.portfolio_completeness * 100)}%</div>
          <div className="audit-kpi-label">Portefoljedekning</div>
        </div>
      </div>

      {/* Domain coverage */}
      <div style={{ marginBottom: 12 }}>
        <div style={{ fontWeight: 600, fontSize: 12, marginBottom: 6 }}>Domenekilde</div>
        <div className="audit-domain-grid">
          {Object.entries(domain_coverage).map(([domain, dc]) => {
            const isC5AI = dc.source === 'c5ai_plus'
            return (
              <div key={domain} className="audit-domain-cell">
                <span className="audit-domain-name">{domain}</span>
                <span
                  className="audit-domain-badge"
                  style={{
                    background: isC5AI ? '#dcfce7' : '#fef3c7',
                    color: isC5AI ? '#166534' : '#92400e',
                  }}
                  title={dc.note}
                >
                  {isC5AI ? 'C5AI+' : 'Estimert'}
                </span>
              </div>
            )
          })}
        </div>
      </div>

      {/* Per-site completeness */}
      <div style={{ marginBottom: 12 }}>
        <div style={{ fontWeight: 600, fontSize: 12, marginBottom: 6 }}>Per-anlegg dekning</div>
        {sites.map(site => (
          <div key={site.site_id} className="audit-site-row">
            <div style={{ flex: 1 }}>
              <div style={{ fontWeight: 600, fontSize: 12 }}>{site.site_name}</div>
              <div style={{ fontSize: 10, color: '#6b7280' }}>{site.site_id} · {site.fjord_exposure}</div>
            </div>
            <div className="audit-completeness-bar-wrap">
              <div
                className="audit-completeness-bar"
                style={{ width: `${Math.round(site.overall_completeness * 100)}%` }}
              />
            </div>
            <div style={{ width: 34, textAlign: 'right', fontSize: 12, fontWeight: 600 }}>
              {Math.round(site.overall_completeness * 100)}%
            </div>
          </div>
        ))}
      </div>

      {/* Model limitations */}
      <div className="audit-limitations-box">
        <div style={{ fontWeight: 600, fontSize: 12, marginBottom: 6 }}>Modellbegrensninger</div>
        <ul style={{ margin: 0, paddingLeft: 16 }}>
          {model_limitations.map((lim, i) => (
            <li key={i} style={{ fontSize: 11, color: '#374151', marginBottom: 4, lineHeight: 1.4 }}>{lim}</li>
          ))}
        </ul>
      </div>
    </div>
  )
}


export default function ReportsPage() {
  const [auditReport, setAuditReport] = useState(null)
  const [auditLoading, setAuditLoading] = useState(false)
  const [auditError, setAuditError] = useState(null)

  async function handleDownloadAudit() {
    setAuditLoading(true)
    setAuditError(null)
    try {
      const data = await fetchInputsAudit()
      setAuditReport(data)
      // Trigger JSON download
      const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' })
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `input_audit_${new Date().toISOString().slice(0,10)}.json`
      a.click()
      URL.revokeObjectURL(url)
    } catch (err) {
      setAuditError(err.message)
    } finally {
      setAuditLoading(false)
    }
  }

  return (
    <div style={{ maxWidth: 800 }}>
      <div style={{ fontWeight: 700, fontSize: 18, marginBottom: 4 }}>Reports</div>
      <div style={{ fontSize: 13, color:'var(--dark-grey)', marginBottom: 20 }}>
        Export board-level and operational reports from the Shield Risk Platform.
      </div>

      <div style={{ display:'flex', flexDirection:'column', gap:16 }}>
        {REPORT_TYPES.map(r => {
          const st = STATUS_STYLE[r.status] || STATUS_STYLE.planned
          return (
            <div key={r.id} className="card" style={{ display:'flex', gap:16, alignItems:'flex-start' }}>
              <div style={{ fontSize:32, lineHeight:1 }}>{r.icon}</div>
              <div style={{ flex:1 }}>
                <div style={{ display:'flex', alignItems:'center', gap:10, marginBottom:4 }}>
                  <div style={{ fontWeight:700, fontSize:15 }}>{r.title}</div>
                  <span style={{ background:st.bg, color:st.color, padding:'2px 8px', borderRadius:10, fontSize:11, fontWeight:700 }}>
                    {st.label}
                  </span>
                </div>
                <div style={{ fontSize:13, color:'var(--dark-grey)', marginBottom:8, lineHeight:1.5 }}>
                  {r.description}
                </div>

                {r.id === 'input_audit' ? (
                  <div>
                    <button
                      className="audit-download-btn"
                      onClick={handleDownloadAudit}
                      disabled={auditLoading}
                    >
                      {auditLoading ? 'Laster...' : 'Last ned rapport (JSON)'}
                    </button>
                    {auditError && (
                      <div style={{ color:'#991b1b', fontSize:12, marginTop:6 }}>
                        Feil: {auditError}
                      </div>
                    )}
                    {!auditReport && !auditLoading && !auditError && (
                      <div
                        className="info-note"
                        style={{ margin: '8px 0 0', fontSize: 12, cursor: 'pointer', textDecoration: 'underline' }}
                        onClick={handleDownloadAudit}
                      >
                        Last ned rapporten for å se innholdet her.
                      </div>
                    )}
                    {auditReport && (
                      <div style={{ marginTop: 12 }}>
                        <AuditSummaryPanel report={auditReport} />
                      </div>
                    )}
                  </div>
                ) : (
                  <div className="info-note" style={{ margin:0, fontSize:12 }}>
                    {r.action}
                  </div>
                )}
              </div>
            </div>
          )
        })}
      </div>
    </div>
  )
}
