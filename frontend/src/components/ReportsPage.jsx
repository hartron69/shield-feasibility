import React from 'react'

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
    status: 'planned',
    action: 'Export planned — wiring to /api/inputs/audit in roadmap.',
    icon: '📊',
  },
]

const STATUS_STYLE = {
  available: { bg:'#D1FAE5', color:'#065F46', label:'Available' },
  planned:   { bg:'#F3F4F6', color:'#6B7280', label:'Planned'   },
}

export default function ReportsPage() {
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
                <div className="info-note" style={{ margin:0, fontSize:12 }}>
                  {r.action}
                </div>
              </div>
            </div>
          )
        })}
      </div>
    </div>
  )
}
